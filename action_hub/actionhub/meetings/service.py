"""Meeting instance service."""
from __future__ import annotations

from datetime import date
import sqlite3

from actionhub.middleware.db import get_db
from actionhub.middleware.auth_middleware import get_request_user
from actionhub.dashboard.service import (
    _build_week_buckets,
    _parse_iso_date,
    _spread_hours_into_buckets,
)


def _table_columns(db, table_name: str) -> set[str]:
    rows = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _ensure_meeting_optional_columns(db) -> set[str]:
    columns = _table_columns(db, "t_meeting_instance")
    optional_columns = [
        ("min_category_id", "INTEGER"),
        ("min_secondary_category_id", "INTEGER"),
        ("min_periodicity", "TEXT"),
        ("min_target", "TEXT"),
        ("min_planned_duration_min", "INTEGER"),
    ]
    for column_name, column_type in optional_columns:
        if column_name not in columns:
            db.execute(f"ALTER TABLE t_meeting_instance ADD COLUMN {column_name} {column_type}")
            columns.add(column_name)
    if "min_category_id" in columns and "min_topic_id" in columns:
        db.execute(
            "UPDATE t_meeting_instance SET min_category_id = COALESCE(min_category_id, min_topic_id) WHERE min_category_id IS NULL"
        )
    return columns


def _ensure_participant_kind_column(db) -> set[str]:
    columns = _table_columns(db, "t_meeting_participant")
    if "mpa_kind" not in columns:
        try:
            db.execute("ALTER TABLE t_meeting_participant ADD COLUMN mpa_kind TEXT NOT NULL DEFAULT 'Optional'")
            columns.add("mpa_kind")
        except sqlite3.OperationalError:
            columns = _table_columns(db, "t_meeting_participant")
    return columns


def _normalize_participant_ids(user_ids: list[int] | None) -> list[int]:
    normalized: list[int] = []
    seen: set[int] = set()
    for value in user_ids or []:
        try:
            user_id = int(value)
        except (TypeError, ValueError):
            continue
        if user_id in seen:
            continue
        seen.add(user_id)
        normalized.append(user_id)
    return normalized


def _normalize_participant_kind(kind: str | None) -> str:
    normalized = str(kind or "Optional").strip().title()
    return normalized if normalized in {"Compulsory", "Optional"} else "Optional"


def _normalize_visibility(value: str | None) -> str:
    normalized = str(value or "public").strip().lower()
    return normalized if normalized in {"public", "private"} else "public"


def _normalize_topic_id(value: object, *, required: bool, field_name: str = "topic_id") -> int | None:
    if value in (None, ""):
        if required:
            raise ValueError(f"{field_name} is required")
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} is required") from None


def _require_existing_topic(db, topic_id: object, *, field_name: str = "topic_id") -> int:
    normalized_topic_id = _normalize_topic_id(topic_id, required=True, field_name=field_name)
    row = db.execute("SELECT top_id FROM t_topic WHERE top_id = ?", (normalized_topic_id,)).fetchone()
    if not row:
        raise ValueError("topic not found")
    return normalized_topic_id


def _resolve_series_topic_id(db, mtg_id: int) -> int:
    row = db.execute("SELECT mtg_topic_id FROM t_meeting WHERE mtg_id = ?", (mtg_id,)).fetchone()
    if not row:
        raise ValueError("meeting series not found")
    topic_id = row["mtg_topic_id"]
    if topic_id not in (None, ""):
        return _require_existing_topic(db, topic_id)

    inherited_row = db.execute(
        """
        SELECT COALESCE(min_category_id, min_topic_id) AS topic_id
        FROM t_meeting_instance
        WHERE min_meeting_id = ? AND COALESCE(min_category_id, min_topic_id) IS NOT NULL
        ORDER BY min_date DESC, min_id DESC
        LIMIT 1
        """,
        (mtg_id,),
    ).fetchone()
    if inherited_row and inherited_row["topic_id"] not in (None, ""):
        topic_id = _require_existing_topic(db, inherited_row["topic_id"])
        db.execute("UPDATE t_meeting SET mtg_topic_id = ? WHERE mtg_id = ?", (topic_id, mtg_id))
        return topic_id

    raise ValueError("meeting series category is required")


def _get_series_occurrence_serials(db, mtg_id: int) -> dict[int, int]:
    rows = db.execute(
        """
        SELECT min_id
        FROM t_meeting_instance
        WHERE min_meeting_id = ?
        ORDER BY min_date ASC, COALESCE(min_created_at, min_date) ASC, min_id ASC
        """,
        (mtg_id,),
    ).fetchall()
    return {int(row["min_id"]): index for index, row in enumerate(rows, start=1)}


def _format_series_occurrence_display_id(mtg_id: int | None, serial: int | None) -> str | None:
    if not mtg_id or not serial:
        return None
    return f"{mtg_id}#{serial}"


def _current_user() -> dict:
    try:
        return get_request_user()
    except Exception:
        return {}


def _current_user_id() -> int | None:
    user = _current_user()
    try:
        return int(user.get("id")) if user.get("id") is not None else None
    except (TypeError, ValueError):
        return None


def _is_admin() -> bool:
    return _current_user().get("role") == "Admin"


def _is_team_lead() -> bool:
    return _current_user().get("role") == "TeamLead"


def _ensure_visibility_columns(db) -> None:
    meeting_cols = _table_columns(db, "t_meeting")
    if "mtg_visibility" not in meeting_cols:
        db.execute("ALTER TABLE t_meeting ADD COLUMN mtg_visibility TEXT NOT NULL DEFAULT 'public'")
    meeting_instance_cols = _table_columns(db, "t_meeting_instance")
    if "min_visibility" not in meeting_instance_cols:
        db.execute("ALTER TABLE t_meeting_instance ADD COLUMN min_visibility TEXT NOT NULL DEFAULT 'public'")
    action_cols = _table_columns(db, "t_action")
    if "act_visibility" not in action_cols:
        db.execute("ALTER TABLE t_action ADD COLUMN act_visibility TEXT NOT NULL DEFAULT 'public'")


def _ensure_series_participant_table(db) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS t_meeting_series_participant (
            msp_id INTEGER PRIMARY KEY AUTOINCREMENT,
            msp_meeting_id INTEGER NOT NULL REFERENCES t_meeting(mtg_id) ON DELETE CASCADE,
            msp_user_id INTEGER NOT NULL REFERENCES t_user(usr_id),
            msp_kind TEXT NOT NULL DEFAULT 'Compulsory' CHECK (msp_kind IN ('Compulsory', 'Optional')),
            msp_added_by INTEGER NOT NULL REFERENCES t_user(usr_id),
            msp_added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(msp_meeting_id, msp_user_id)
        )
        """
    )


def _ensure_meeting_owner_table(db) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS t_meeting_owner (
            mow_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            mow_instance_id INTEGER NOT NULL,
            mow_user_id     INTEGER NOT NULL,
            mow_granted_by  INTEGER NOT NULL,
            mow_granted_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(mow_instance_id, mow_user_id)
        )
        """
    )


def _meeting_participant_ids(min_id: int) -> set[int]:
    db = get_db()
    rows = db.execute("SELECT DISTINCT mpa_user_id FROM t_meeting_participant WHERE mpa_instance_id = ?", (min_id,)).fetchall()
    return {int(row[0]) for row in rows}


def _meeting_series_participant_ids(mtg_id: int) -> set[int]:
    db = get_db()
    _ensure_series_participant_table(db)
    rows = db.execute("SELECT DISTINCT msp_user_id FROM t_meeting_series_participant WHERE msp_meeting_id = ?", (mtg_id,)).fetchall()
    return {int(row[0]) for row in rows}


def _is_action_participant(action_id: int, user_id: int) -> bool:
    db = get_db()
    row = db.execute(
        "SELECT 1 FROM t_assignment WHERE asg_action_id = ? AND asg_user_id = ? LIMIT 1",
        (action_id, user_id),
    ).fetchone()
    return row is not None


def _can_view_private_meeting(min_id: int) -> bool:
    user_id = _current_user_id()
    if user_id is None:
        return False
    if is_meeting_owner(min_id, user_id):
        return True
    db = get_db()
    row = db.execute("SELECT min_meeting_id, COALESCE(min_visibility, 'public') AS min_visibility FROM t_meeting_instance WHERE min_id = ?", (min_id,)).fetchone()
    if not row:
        return False
    if _normalize_visibility(row["min_visibility"]) != "private":
        return True
    return user_id in _meeting_participant_ids(min_id)


def _can_view_series(mtg_id: int) -> bool:
    if _is_admin():
        return True
    user_id = _current_user_id()
    if user_id is None:
        return False
    db = get_db()
    _ensure_series_participant_table(db)
    row = db.execute(
        "SELECT mtg_created_by, COALESCE(mtg_visibility, 'public') AS mtg_visibility FROM t_meeting WHERE mtg_id = ?",
        (mtg_id,),
    ).fetchone()
    if not row:
        return False
    # Creator can always view their series
    if int(row["mtg_created_by"] or 0) == user_id:
        return True
    default_participant = db.execute(
        "SELECT 1 FROM t_meeting_series_participant WHERE msp_meeting_id = ? AND msp_user_id = ? LIMIT 1",
        (mtg_id, user_id),
    ).fetchone()
    if default_participant:
        return True
    rows = db.execute(
        "SELECT 1 FROM t_meeting_instance mi JOIN t_meeting_participant mp ON mp.mpa_instance_id = mi.min_id WHERE mi.min_meeting_id = ? AND mp.mpa_user_id = ? LIMIT 1",
        (mtg_id, user_id),
    ).fetchone()
    return rows is not None


# ── Meeting Owner helpers ─────────────────────────────────────────────────────

def get_meeting_owners(min_id: int) -> list[dict]:
    """Return all owners of a meeting instance."""
    db = get_db()
    _ensure_meeting_owner_table(db)
    rows = db.execute(
        """
        SELECT mow.mow_id, mow.mow_user_id, u.usr_display_name,
               mow.mow_granted_by, ug.usr_display_name AS granted_by_name,
               mow.mow_granted_at
        FROM t_meeting_owner mow
        JOIN t_user u  ON u.usr_id = mow.mow_user_id
        LEFT JOIN t_user ug ON ug.usr_id = mow.mow_granted_by
        WHERE mow.mow_instance_id = ?
        ORDER BY mow.mow_granted_at ASC
        """,
        (min_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def set_meeting_owners(min_id: int, user_ids: list[int], actor_id: int) -> list[dict]:
    """Replace the full owner list of a meeting instance."""
    db = get_db()
    _ensure_meeting_owner_table(db)
    # Validate meeting exists
    row = db.execute("SELECT min_id, min_meeting_id FROM t_meeting_instance WHERE min_id = ?", (min_id,)).fetchone()
    if not row:
        raise ValueError("meeting not found")
    if not user_ids:
        raise ValueError("at least one owner is required")
    # Remove old owners not in the new set
    db.execute(
        f"DELETE FROM t_meeting_owner WHERE mow_instance_id = ? AND mow_user_id NOT IN ({','.join('?' * len(user_ids))})",
        [min_id, *user_ids],
    )
    # Add new owners
    for uid in user_ids:
        db.execute(
            "INSERT OR IGNORE INTO t_meeting_owner (mow_instance_id, mow_user_id, mow_granted_by) VALUES (?, ?, ?)",
            (min_id, uid, actor_id),
        )
    db.commit()
    return get_meeting_owners(min_id)


def is_meeting_owner(min_id: int, user_id: int) -> bool:
    """Check whether a user is an owner of a given meeting instance."""
    db = get_db()
    _ensure_meeting_owner_table(db)
    row = db.execute(
        "SELECT 1 FROM t_meeting_owner WHERE mow_instance_id = ? AND mow_user_id = ?",
        (min_id, user_id),
    ).fetchone()
    return row is not None


def is_meeting_owner_for_action(action_id: int, user_id: int) -> bool:
    """Check whether a user is an owner of the meeting linked to an action."""
    db = get_db()
    _ensure_meeting_owner_table(db)
    row = db.execute(
        """
        SELECT 1
        FROM t_action a
        JOIN t_meeting_owner mow ON mow.mow_instance_id = a.act_meeting_inst_id
        WHERE a.act_id = ? AND mow.mow_user_id = ?
        """,
        (action_id, user_id),
    ).fetchone()
    return row is not None


# ── Meeting Participant helpers ───────────────────────────────────────────────


def is_meeting_participant(min_id: int, user_id: int) -> bool:
    """Check whether a user is a participant of a given meeting instance."""
    db = get_db()
    row = db.execute(
        "SELECT 1 FROM t_meeting_participant WHERE mpa_instance_id = ? AND mpa_user_id = ? LIMIT 1",
        (min_id, user_id),
    ).fetchone()
    return row is not None


def get_meeting_participants(min_id: int) -> list[dict]:
    """Return all participants of a meeting instance."""
    db = get_db()
    participant_columns = _ensure_participant_kind_column(db)
    participant_kind_expr = "COALESCE(mpa.mpa_kind, 'Optional')" if "mpa_kind" in participant_columns else "'Optional'"
    rows = db.execute(
        """
        SELECT mpa.mpa_id, mpa.mpa_user_id, u.usr_display_name,
               u.usr_email, mpa.mpa_added_at,
               {participant_kind_expr} AS mpa_kind
        FROM t_meeting_participant mpa
        JOIN t_user u ON u.usr_id = mpa.mpa_user_id
        WHERE mpa.mpa_instance_id = ?
        ORDER BY u.usr_display_name ASC
        """.format(participant_kind_expr=participant_kind_expr),
        (min_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def set_meeting_participants(min_id: int, user_ids: list[int], actor_id: int, kind: str = "Optional") -> list[dict]:
    """Replace the participant list of one participant kind for a meeting instance."""
    db = get_db()
    participant_columns = _ensure_participant_kind_column(db)
    has_participant_kind = "mpa_kind" in participant_columns
    row = db.execute("SELECT min_id, min_meeting_id, min_created_by FROM t_meeting_instance WHERE min_id = ?", (min_id,)).fetchone()
    if not row:
        raise ValueError("meeting not found")
    normalized_kind = _normalize_participant_kind(kind)
    normalized_ids = _normalize_participant_ids(user_ids)
    meeting_creator_id = int(row["min_created_by"] or 0)

    if row["min_meeting_id"]:
        allowed_participants = _meeting_series_participant_ids(int(row["min_meeting_id"]))
        # Meeting creator is always permitted and must remain in occurrence participants.
        allowed_participants.add(meeting_creator_id)
        if any(uid not in allowed_participants for uid in normalized_ids):
            raise ValueError("occurrence participants must come from the meeting series participant list")

    if normalized_kind == "Compulsory" and meeting_creator_id and meeting_creator_id not in normalized_ids:
        normalized_ids.append(meeting_creator_id)
    if normalized_kind != "Compulsory" and meeting_creator_id in normalized_ids:
        normalized_ids = [uid for uid in normalized_ids if uid != meeting_creator_id]
    if normalized_ids:
        placeholders = ",".join("?" * len(normalized_ids))
        if has_participant_kind:
            db.execute(
                f"DELETE FROM t_meeting_participant WHERE mpa_instance_id = ? AND COALESCE(mpa_kind, 'Optional') = ? AND mpa_user_id NOT IN ({placeholders})",
                [min_id, normalized_kind, *normalized_ids],
            )
        else:
            db.execute(
                f"DELETE FROM t_meeting_participant WHERE mpa_instance_id = ? AND mpa_user_id NOT IN ({placeholders})",
                [min_id, *normalized_ids],
            )
        for uid in normalized_ids:
            if has_participant_kind:
                db.execute(
                    """
                    INSERT INTO t_meeting_participant (mpa_instance_id, mpa_user_id, mpa_added_by, mpa_kind)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(mpa_instance_id, mpa_user_id)
                    DO UPDATE SET
                        mpa_added_by = excluded.mpa_added_by,
                        mpa_kind = excluded.mpa_kind,
                        mpa_added_at = CURRENT_TIMESTAMP
                    """,
                    (min_id, uid, actor_id, normalized_kind),
                )
            else:
                db.execute(
                    """
                    INSERT INTO t_meeting_participant (mpa_instance_id, mpa_user_id, mpa_added_by)
                    VALUES (?, ?, ?)
                    ON CONFLICT(mpa_instance_id, mpa_user_id)
                    DO UPDATE SET
                        mpa_added_by = excluded.mpa_added_by,
                        mpa_added_at = CURRENT_TIMESTAMP
                    """,
                    (min_id, uid, actor_id),
                )
    else:
        if has_participant_kind:
            db.execute(
                "DELETE FROM t_meeting_participant WHERE mpa_instance_id = ? AND COALESCE(mpa_kind, 'Optional') = ?",
                (min_id, normalized_kind),
            )
        else:
            db.execute("DELETE FROM t_meeting_participant WHERE mpa_instance_id = ?", (min_id,))
    db.commit()
    return get_meeting_participants(min_id)


def add_meeting_participant(min_id: int, user_id: int, actor_id: int, kind: str = "Optional") -> list[dict]:
    db = get_db()
    participant_columns = _ensure_participant_kind_column(db)
    row = db.execute("SELECT min_meeting_id, min_created_by FROM t_meeting_instance WHERE min_id = ?", (min_id,)).fetchone()
    if not row:
        raise ValueError("meeting not found")

    meeting_creator_id = int(row["min_created_by"] or 0)
    if row["min_meeting_id"]:
        allowed_participants = _meeting_series_participant_ids(int(row["min_meeting_id"]))
        allowed_participants.add(meeting_creator_id)
        if int(user_id) not in allowed_participants:
            raise ValueError("occurrence participants must come from the meeting series participant list")

    normalized_kind = _normalize_participant_kind(kind)
    if int(user_id) == meeting_creator_id:
        normalized_kind = "Compulsory"

    if "mpa_kind" in participant_columns:
        db.execute(
            """
            INSERT INTO t_meeting_participant (mpa_instance_id, mpa_user_id, mpa_added_by, mpa_kind)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(mpa_instance_id, mpa_user_id)
            DO UPDATE SET
                mpa_added_by = excluded.mpa_added_by,
                mpa_kind = excluded.mpa_kind,
                mpa_added_at = CURRENT_TIMESTAMP
            """,
            (min_id, user_id, actor_id, normalized_kind),
        )
    else:
        db.execute(
            """
            INSERT INTO t_meeting_participant (mpa_instance_id, mpa_user_id, mpa_added_by)
            VALUES (?, ?, ?)
            ON CONFLICT(mpa_instance_id, mpa_user_id)
            DO UPDATE SET
                mpa_added_by = excluded.mpa_added_by,
                mpa_added_at = CURRENT_TIMESTAMP
            """,
            (min_id, user_id, actor_id),
        )
    db.commit()
    return get_meeting_participants(min_id)


def remove_meeting_participant(min_id: int, user_id: int) -> list[dict]:
    db = get_db()
    row = db.execute("SELECT min_created_by FROM t_meeting_instance WHERE min_id = ?", (min_id,)).fetchone()
    if not row:
        raise ValueError("meeting not found")
    if int(user_id) == int(row["min_created_by"] or 0):
        raise ValueError("meeting creator cannot be removed from participants")
    db.execute(
        "DELETE FROM t_meeting_participant WHERE mpa_instance_id = ? AND mpa_user_id = ?",
        (min_id, user_id),
    )
    db.commit()
    return get_meeting_participants(min_id)


def list_meetings(category_id: int | None = None) -> list[dict]:
    """List meetings, optionally filtered by category (matches primary OR secondary)."""
    db = get_db()
    _ensure_visibility_columns(db)
    meeting_cols = _ensure_meeting_optional_columns(db)
    decision_cols = {row[1] for row in db.execute("PRAGMA table_info(t_meeting_decision)").fetchall()}
    topic_cols = {row[1] for row in db.execute("PRAGMA table_info(t_topic)").fetchall()}
    topic_filter_id: int | None = None
    if category_id not in (None, ""):
        try:
            topic_filter_id = int(category_id)
        except (TypeError, ValueError):
            topic_str = str(category_id).strip()
            if ":" in topic_str:
                suffix = topic_str.rsplit(":", 1)[-1].strip()
                if suffix.isdigit():
                    topic_filter_id = int(suffix)
            if topic_filter_id is None:
                row = db.execute(
                    "SELECT top_id FROM t_topic WHERE top_code = ? OR top_name = ? OR CAST(top_id AS TEXT) = ?",
                    (topic_str, topic_str, topic_str),
                ).fetchone()
                if row:
                    topic_filter_id = int(row["top_id"])

    primary_expr = "COALESCE(m.min_category_id, m.min_topic_id)" if {"min_category_id", "min_topic_id"}.issubset(meeting_cols) else (
        "m.min_category_id" if "min_category_id" in meeting_cols else ("m.min_topic_id" if "min_topic_id" in meeting_cols else "NULL")
    )
    secondary_expr = "m.min_secondary_category_id" if "min_secondary_category_id" in meeting_cols else "NULL"
    archived_expr = "COALESCE(m.min_archived, 0)" if "min_archived" in meeting_cols else "0"
    created_expr = "m.min_created_at" if "min_created_at" in meeting_cols else "m.min_date"
    periodicity_expr = "m.min_periodicity" if "min_periodicity" in meeting_cols else "NULL"
    target_expr = "m.min_target" if "min_target" in meeting_cols else "NULL"
    planned_duration_expr = "m.min_planned_duration_min" if "min_planned_duration_min" in meeting_cols else "NULL"
    status_expr = "CASE WHEN COALESCE(m.min_archived, 0) = 1 THEN 'Closed' ELSE 'Active' END AS meeting_status"
    decision_active_condition = "COALESCE(d.mdc_deleted_at, 0) = 0" if "mdc_deleted_at" in decision_cols else "1 = 1"
    decision_meeting_expr = "COALESCE(d.mdc_instance_id, d.mdc_meeting_id)" if {"mdc_instance_id", "mdc_meeting_id"}.issubset(decision_cols) else ("d.mdc_instance_id" if "mdc_instance_id" in decision_cols else "d.mdc_meeting_id")
    decision_count_sql = f"(SELECT COUNT(*) FROM t_meeting_decision d WHERE {decision_meeting_expr} = m.min_id AND {decision_active_condition}) AS decision_count"
    category_name_sql = "t.top_name AS category_name" if primary_expr != "NULL" and "top_name" in topic_cols else "NULL AS category_name"
    secondary_name_sql = "t2.top_name AS secondary_category_name" if secondary_expr != "NULL" and "top_name" in topic_cols else "NULL AS secondary_category_name"
    where_clause = f"WHERE {archived_expr} = 0"
    params: list[object] = []
    if topic_filter_id is not None:
        where_clause += f" AND ({primary_expr} = ? OR {secondary_expr} = ?)"
        params.extend([topic_filter_id, topic_filter_id])

    base_select = f"""
            SELECT m.*, 
                   {category_name_sql},
                   {secondary_name_sql},
               {status_expr},
                   {periodicity_expr} AS min_periodicity,
                   {target_expr} AS min_target,
                   {planned_duration_expr} AS min_planned_duration_min,
                   u.usr_display_name AS creator_name,
                   (SELECT COUNT(*) FROM t_action a WHERE a.act_meeting_inst_id = m.min_id AND a.act_status != 'Cancelled') AS action_count,
                   (SELECT MAX(mm.mmm_date) FROM t_meeting_memo mm WHERE mm.mmm_instance_id = m.min_id) AS latest_memo_date,
                   {decision_count_sql}
              FROM t_meeting_instance m
                  {('LEFT JOIN t_topic t ON t.top_id = ' + primary_expr) if primary_expr != 'NULL' else ''}
                  {('LEFT JOIN t_topic t2 ON t2.top_id = ' + secondary_expr) if secondary_expr != 'NULL' else ''}
            LEFT JOIN t_user u ON u.usr_id = m.min_created_by
            {where_clause}
    """
    order_sql = f" ORDER BY COALESCE(latest_memo_date, {created_expr}) DESC"
    limit_sql = "" if topic_filter_id is not None else " LIMIT 100"
    rows = db.execute(base_select + order_sql + limit_sql, params).fetchall()
    items: list[dict] = []
    user_id = _current_user_id()
    is_admin = _is_admin()
    # Pre-compute set of occurrence IDs the current user can access (non-admin only)
    accessible_ids: set[int] | None = None
    if not is_admin and user_id is not None:
        _ensure_series_participant_table(db)
        _ensure_meeting_owner_table(db)
        acc_rows = db.execute(
            """
            SELECT min_id FROM t_meeting_instance WHERE min_created_by = ?
            UNION
            SELECT mpa_instance_id FROM t_meeting_participant WHERE mpa_user_id = ?
            UNION
            SELECT mow_instance_id FROM t_meeting_owner WHERE mow_user_id = ?
            UNION
            SELECT mi.min_id FROM t_meeting_instance mi
              JOIN t_meeting mtg ON mtg.mtg_id = mi.min_meeting_id
             WHERE mtg.mtg_created_by = ?
            UNION
            SELECT mi.min_id FROM t_meeting_instance mi
              JOIN t_meeting_series_participant msp ON msp.msp_meeting_id = mi.min_meeting_id
             WHERE msp.msp_user_id = ?
            """,
            (user_id, user_id, user_id, user_id, user_id),
        ).fetchall()
        accessible_ids = {int(r["min_id"]) for r in acc_rows}
    for r in rows:
        row = dict(r)
        visibility = _normalize_visibility(row.get("min_visibility"))
        if visibility == "private" and not is_admin:
            if user_id is None:
                continue
            if int(row.get("min_created_by") or 0) != user_id and user_id not in _meeting_participant_ids(int(row["min_id"])):
                continue
        if is_admin:
            row["occurrence_access"] = True
        else:
            row["occurrence_access"] = accessible_ids is not None and int(row["min_id"]) in accessible_ids
        items.append(row)
    return items


def get_meeting(min_id: int) -> dict:
    """Get meeting by ID with both primary and secondary category info."""
    db = get_db()
    _ensure_visibility_columns(db)
    meeting_cols = _ensure_meeting_optional_columns(db)
    status_expr = "CASE WHEN COALESCE(m.min_archived, 0) = 1 THEN 'Closed' ELSE 'Active' END AS meeting_status"
    periodicity_expr = "m.min_periodicity" if "min_periodicity" in meeting_cols else "NULL AS min_periodicity"
    target_expr = "m.min_target" if "min_target" in meeting_cols else "NULL AS min_target"
    planned_duration_expr = "m.min_planned_duration_min" if "min_planned_duration_min" in meeting_cols else "NULL AS min_planned_duration_min"
    row = db.execute(
        """
        SELECT m.*, 
               t.top_name AS category_name,
               t2.top_name AS secondary_category_name,
               u.usr_display_name AS creator_name,
               CASE WHEN COALESCE(m.min_archived, 0) = 1 THEN 'Closed' ELSE 'Active' END AS meeting_status,
               {periodicity_expr},
               {target_expr},
               {planned_duration_expr}
        FROM t_meeting_instance m
         LEFT JOIN t_topic t ON t.top_id = COALESCE(m.min_category_id, m.min_topic_id)
         LEFT JOIN t_topic t2 ON t2.top_id = m.min_secondary_category_id
        LEFT JOIN t_user u ON u.usr_id = m.min_created_by
        WHERE m.min_id = ?
        """.format(
            periodicity_expr=periodicity_expr,
            target_expr=target_expr,
            planned_duration_expr=planned_duration_expr,
        ),
        (min_id,),
    ).fetchone()
    if not row:
        raise ValueError("meeting not found")
    meeting = dict(row)
    visibility = _normalize_visibility(meeting.get("min_visibility"))
    if visibility == "private" and not _can_view_private_meeting(min_id):
        raise ValueError("meeting not found")
    parent_series_id = meeting.get("min_meeting_id")
    if parent_series_id:
        serials = _get_series_occurrence_serials(db, int(parent_series_id))
        meeting_serial = serials.get(int(min_id))
        meeting["meeting_serial"] = meeting_serial
        meeting["meeting_display_id"] = _format_series_occurrence_display_id(int(parent_series_id), meeting_serial)
    participants = get_meeting_participants(min_id)
    meeting["participants"] = participants
    meeting["compulsory_participants"] = [p for p in participants if p.get("mpa_kind") == "Compulsory"]
    meeting["optional_participants"] = [p for p in participants if p.get("mpa_kind") != "Compulsory"]
    return meeting


def create_meeting(payload: dict, actor_id: int) -> dict:
    """Create a meeting instance with optional dual-category support.
    
    Args:
        payload: Dictionary with keys:
            - title (required)
            - category_id (optional) - primary category
            - secondary_category_id (optional) - secondary category
            - notes, meeting_id, date, type (all optional)
        actor_id: User ID creating the meeting
        
    Returns:
        Created meeting dictionary.
        
    Raises:
        ValueError: If validation fails.
    """
    db = get_db()
    _ensure_visibility_columns(db)
    meeting_cols = _ensure_meeting_optional_columns(db)
    _ensure_meeting_owner_table(db)
    title = str(payload.get("title", "")).strip()
    if len(title) < 2:
        raise ValueError("title must be at least 2 characters")

    meeting_date = payload.get("date") or payload.get("min_date")
    if not meeting_date:
        raise ValueError("date is required")

    category_id = payload.get("category_id") or payload.get("topic_id")
    secondary_category_id = payload.get("secondary_category_id")
    periodicity = (payload.get("periodicity") or payload.get("min_periodicity") or "").strip() or None
    target = str(payload.get("target") or payload.get("meeting_target") or payload.get("min_target") or "").strip() or None
    planned_duration_raw = payload.get("planned_duration_min") or payload.get("min_planned_duration_min")
    planned_duration_min = None
    if planned_duration_raw not in (None, ""):
        planned_duration_min = int(planned_duration_raw)
    status = (payload.get("status") or payload.get("meeting_status") or "Active").strip().title()
    archived = 1 if status == "Closed" else 0
    visibility = _normalize_visibility(payload.get("visibility") or payload.get("min_visibility") or payload.get("mtg_visibility"))
    
    # Validate secondary != primary
    if category_id and secondary_category_id and category_id == secondary_category_id:
        raise ValueError("Secondary category must differ from primary category")

    if "min_periodicity" not in meeting_cols:
        db.execute("ALTER TABLE t_meeting_instance ADD COLUMN min_periodicity TEXT")
        meeting_cols.add("min_periodicity")

    insert_columns = ["min_title", "min_topic_id", "min_category_id", "min_secondary_category_id", "min_notes", "min_visibility", "min_created_by", "min_meeting_id", "min_date", "min_type", "min_archived"]
    insert_values = [title, category_id, category_id, secondary_category_id, payload.get("notes") or None, visibility, actor_id, payload.get("meeting_id") or None, meeting_date, payload.get("type") or None, archived]
    if "min_periodicity" in meeting_cols:
        insert_columns.insert(8, "min_periodicity")
        insert_values.insert(8, periodicity)
    if "min_target" in meeting_cols:
        insert_columns.append("min_target")
        insert_values.append(target)
    if "min_planned_duration_min" in meeting_cols:
        insert_columns.append("min_planned_duration_min")
        insert_values.append(planned_duration_min)

    cur = db.execute(
        f"""
        INSERT INTO t_meeting_instance
            ({', '.join(insert_columns)})
        VALUES ({', '.join(['?'] * len(insert_values))})
        """,
        insert_values,
    )
    new_id = cur.lastrowid
    # Auto-add creator as meeting owner and compulsory participant.
    db.execute(
        "INSERT OR IGNORE INTO t_meeting_owner (mow_instance_id, mow_user_id, mow_granted_by) VALUES (?, ?, ?)",
        (new_id, actor_id, actor_id),
    )
    participant_columns = _ensure_participant_kind_column(db)
    if "mpa_kind" in participant_columns:
        db.execute(
            """
            INSERT OR IGNORE INTO t_meeting_participant (mpa_instance_id, mpa_user_id, mpa_added_by, mpa_kind)
            VALUES (?, ?, ?, 'Compulsory')
            """,
            (new_id, actor_id, actor_id),
        )
    else:
        db.execute(
            """
            INSERT OR IGNORE INTO t_meeting_participant (mpa_instance_id, mpa_user_id, mpa_added_by)
            VALUES (?, ?, ?)
            """,
            (new_id, actor_id, actor_id),
        )
    db.commit()
    return get_meeting(new_id)


def update_meeting(min_id: int, payload: dict, actor_id: int) -> dict:
    """Update a meeting instance.
    
    Args:
        min_id: Meeting instance ID
        payload: Dictionary with optional keys:
            - title, category_id, secondary_category_id
            - notes, archived, date, type
        actor_id: User ID performing the update
        
    Returns:
        Updated meeting dictionary.
        
    Raises:
        ValueError: If validation fails.
    """
    db = get_db()
    _ensure_visibility_columns(db)
    meeting_cols = _ensure_meeting_optional_columns(db)
    row = db.execute("SELECT min_id, min_meeting_id FROM t_meeting_instance WHERE min_id = ?", (min_id,)).fetchone()
    if not row:
        raise ValueError("meeting not found")

    # Validate secondary != primary if both provided
    if "category_id" in payload or "topic_id" in payload or "secondary_category_id" in payload:
        category_id = payload.get("category_id") if "category_id" in payload else payload.get("topic_id")
        secondary_category_id = payload.get("secondary_category_id")
        if category_id and secondary_category_id and category_id == secondary_category_id:
            raise ValueError("Secondary category must differ from primary category")

    updates: list[tuple[str, object]] = []
    if "title" in payload:
        updates.append(("min_title", payload.get("title") or None))
    if "notes" in payload:
        updates.append(("min_notes", payload.get("notes") or None))
    if "date" in payload:
        updates.append(("min_date", payload.get("date") or None))
    if "type" in payload:
        updates.append(("min_type", payload.get("type") or None))
    if "periodicity" in payload or "min_periodicity" in payload:
        if "min_periodicity" in meeting_cols:
            updates.append(("min_periodicity", payload.get("periodicity") or payload.get("min_periodicity") or None))
    if "target" in payload or "meeting_target" in payload or "min_target" in payload:
        if "min_target" in meeting_cols:
            updates.append(("min_target", str(payload.get("target") or payload.get("meeting_target") or payload.get("min_target") or "").strip() or None))
    parent_series_id = row["min_meeting_id"] if hasattr(row, "keys") and "min_meeting_id" in row.keys() else row[1]
    if "planned_duration_min" in payload or "min_planned_duration_min" in payload:
        if "min_planned_duration_min" in meeting_cols and not parent_series_id:
            planned_duration_value = payload.get("planned_duration_min") if "planned_duration_min" in payload else payload.get("min_planned_duration_min")
            updates.append(("min_planned_duration_min", int(planned_duration_value) if planned_duration_value not in (None, "") else None))
    if "status" in payload or "meeting_status" in payload:
        status = (payload.get("status") or payload.get("meeting_status") or "Active").strip().title()
        updates.append(("min_archived", 1 if status == "Closed" else 0))
    if "archived" in payload:
        updates.append(("min_archived", 1 if bool(payload.get("archived")) else 0))
    if "visibility" in payload or "min_visibility" in payload or "mtg_visibility" in payload:
        updates.append(("min_visibility", _normalize_visibility(payload.get("visibility") or payload.get("min_visibility") or payload.get("mtg_visibility"))))

    if "category_id" in payload or "topic_id" in payload:
        category_value = payload.get("category_id") if "category_id" in payload else payload.get("topic_id")
        updates.extend([("min_category_id", category_value or None), ("min_topic_id", category_value or None)])
    if "secondary_category_id" in payload:
        updates.append(("min_secondary_category_id", payload.get("secondary_category_id") or None))

    compulsory_participants = payload.get("compulsory_participant_ids")
    optional_participants = payload.get("optional_participant_ids")
    if compulsory_participants is not None or optional_participants is not None:
        compulsory_ids = _normalize_participant_ids(compulsory_participants)
        optional_ids = _normalize_participant_ids(optional_participants)
        compulsory_set = set(compulsory_ids)
        optional_ids = [uid for uid in optional_ids if uid not in compulsory_set]
        set_meeting_participants(min_id, compulsory_ids, actor_id, kind="Compulsory")
        set_meeting_participants(min_id, optional_ids, actor_id, kind="Optional")

    for col, value in updates:
        db.execute(f"UPDATE t_meeting_instance SET {col} = ? WHERE min_id = ?", (value, min_id))
    db.commit()
    return get_meeting(min_id)


def get_action_related_meetings(action_id: int) -> list[dict]:
    """Return meetings linked to an action, either directly or via shared topic."""
    db = get_db()
    rows = db.execute(
        """
        SELECT DISTINCT m.min_id, m.min_title, m.min_date, m.min_type,
               m.min_notes, t.top_name AS topic_name, u.usr_display_name AS creator_name,
               CASE WHEN a.act_meeting_inst_id = m.min_id THEN 1 ELSE 0 END AS is_direct
        FROM t_action a
        JOIN t_meeting_instance m
            ON (m.min_id = a.act_meeting_inst_id
                OR (a.act_topic_id IS NOT NULL AND COALESCE(m.min_category_id, m.min_topic_id) = a.act_topic_id)
                OR (a.act_secondary_topic_id IS NOT NULL AND COALESCE(m.min_category_id, m.min_topic_id) = a.act_secondary_topic_id))
        LEFT JOIN t_topic t ON t.top_id = COALESCE(m.min_category_id, m.min_topic_id)
        LEFT JOIN t_user u ON u.usr_id = m.min_created_by
        WHERE a.act_id = ?
        ORDER BY m.min_created_at DESC
        LIMIT 20
        """,
        (action_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_meeting_actions(min_id: int) -> list[dict]:
    db = get_db()
    _ensure_visibility_columns(db)
    if not _can_view_private_meeting(min_id):
        raise ValueError("meeting not found")
    rows = db.execute(
        """
        SELECT a.act_id,
               a.act_ref        AS act_ref,
               a.act_ref        AS act_ref_code,
               a.act_title, a.act_status, a.act_priority,
               a.act_desc,
               a.act_deadline   AS act_due_date,
               a.act_deadline   AS act_deadline,
               a.act_completion_pct, a.act_created_at,
               uc.usr_display_name AS creator_name,
               ul.usr_display_name AS lead_name,
               COALESCE(
                   (SELECT GROUP_CONCAT(t.tea_code, ', ')
                    FROM t_user_team ut
                    JOIN t_team t ON t.tea_id = ut.utm_team_id
                    WHERE ut.utm_user_id = ul.usr_id), '') AS team_codes,
            (SELECT COUNT(DISTINCT z.asg_user_id) FROM t_assignment z WHERE z.asg_action_id = a.act_id) AS asg_total,
            (SELECT GROUP_CONCAT(DISTINCT u2.usr_display_name)
             FROM t_assignment z JOIN t_user u2 ON u2.usr_id = z.asg_user_id
               WHERE z.asg_action_id = a.act_id) AS assignee_names
        FROM t_action a
        LEFT JOIN t_user uc ON uc.usr_id = a.act_created_by
        LEFT JOIN t_assignment asg ON asg.asg_action_id = a.act_id AND INSTR(',' || asg.asg_role || ',', ',Lead,') > 0
        LEFT JOIN t_user ul ON ul.usr_id = asg.asg_user_id
        WHERE a.act_meeting_inst_id = ?
          AND a.act_status != 'Cancelled'
        ORDER BY a.act_created_at ASC
        """,
        (min_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Parent Meeting (series) functions ─────────────────────────────────────────

def list_parent_meetings(topic_id: int | None = None, visibility: str | None = None) -> list[dict]:
    """Return all meeting series with their instance count."""
    db = get_db()
    _ensure_visibility_columns(db)
    _ensure_series_participant_table(db)
    if topic_id:
        rows = db.execute(
            """
            SELECT mtg.*, t.top_name AS topic_name, u.usr_display_name AS creator_name,
                   COUNT(mi.min_id) AS instance_count,
                   MAX(mi.min_date) AS last_occurrence_date,
                   (SELECT COUNT(*) FROM t_meeting_series_participant msp WHERE msp.msp_meeting_id = mtg.mtg_id) AS default_participant_count
            FROM t_meeting mtg
            LEFT JOIN t_topic t ON t.top_id = mtg.mtg_topic_id
            LEFT JOIN t_user u ON u.usr_id = mtg.mtg_created_by
            LEFT JOIN t_meeting_instance mi ON mi.min_meeting_id = mtg.mtg_id
            WHERE mtg.mtg_topic_id = ?
            GROUP BY mtg.mtg_id
            ORDER BY MAX(mi.min_date) DESC, mtg.mtg_created_at DESC
            """,
            (topic_id,),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT mtg.*, t.top_name AS topic_name, u.usr_display_name AS creator_name,
                 COUNT(mi.min_id) AS instance_count,
                 MAX(mi.min_date) AS last_occurrence_date,
                 (SELECT COUNT(*) FROM t_meeting_series_participant msp WHERE msp.msp_meeting_id = mtg.mtg_id) AS default_participant_count
            FROM t_meeting mtg
            LEFT JOIN t_topic t ON t.top_id = mtg.mtg_topic_id
            LEFT JOIN t_user u ON u.usr_id = mtg.mtg_created_by
            LEFT JOIN t_meeting_instance mi ON mi.min_meeting_id = mtg.mtg_id
            GROUP BY mtg.mtg_id
            ORDER BY MAX(mi.min_date) DESC, mtg.mtg_created_at DESC
            LIMIT 100
            """,
        ).fetchall()
    items: list[dict] = []
    user_id = _current_user_id()
    requested_visibility = _normalize_visibility(visibility) if visibility else None
    for row in rows:
        item = dict(row)
        if requested_visibility and _normalize_visibility(item.get("mtg_visibility")) != requested_visibility:
            continue
        item["series_access"] = bool(_can_view_series(int(item["mtg_id"])))
        items.append(item)
    return items


def get_parent_meeting(mtg_id: int) -> dict:
    db = get_db()
    _ensure_visibility_columns(db)
    _ensure_series_participant_table(db)
    row = db.execute(
        """
        SELECT mtg.*, t.top_name AS topic_name, u.usr_display_name AS creator_name,
               COUNT(mi.min_id) AS instance_count,
               MAX(mi.min_date) AS last_occurrence_date,
               (SELECT COUNT(*) FROM t_meeting_series_participant msp WHERE msp.msp_meeting_id = mtg.mtg_id) AS default_participant_count
        FROM t_meeting mtg
        LEFT JOIN t_topic t ON t.top_id = mtg.mtg_topic_id
        LEFT JOIN t_user u ON u.usr_id = mtg.mtg_created_by
        LEFT JOIN t_meeting_instance mi ON mi.min_meeting_id = mtg.mtg_id
        WHERE mtg.mtg_id = ?
        GROUP BY mtg.mtg_id
        """,
        (mtg_id,),
    ).fetchone()
    if not row:
        raise ValueError("meeting series not found")
    result = dict(row)
    if not _can_view_series(mtg_id):
        raise ValueError("meeting series not found")
    result["default_participants"] = get_series_participants(mtg_id)
    result["occurrences"] = list_instances_of_series(mtg_id)
    return result


def create_parent_meeting(payload: dict, actor_id: int) -> dict:
    """Create a meeting series (t_meeting parent record)."""
    db = get_db()
    _ensure_visibility_columns(db)
    title = str(payload.get("title", "")).strip()
    if len(title) < 2:
        raise ValueError("title must be at least 2 characters")
    visibility = _normalize_visibility(payload.get("visibility") or payload.get("mtg_visibility"))
    topic_id = _require_existing_topic(db, payload.get("topic_id"))
    cur = db.execute(
        """
        INSERT INTO t_meeting (mtg_title, mtg_description, mtg_topic_id, mtg_visibility, mtg_created_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title,
         payload.get("description") or None,
            topic_id,
         visibility,
         actor_id),
    )
    _ensure_series_participant_table(db)
    db.execute(
        """
        INSERT OR IGNORE INTO t_meeting_series_participant
            (msp_meeting_id, msp_user_id, msp_kind, msp_added_by)
        VALUES (?, ?, 'Compulsory', ?)
        """,
        (cur.lastrowid, actor_id, actor_id),
    )
    db.commit()
    return get_parent_meeting(cur.lastrowid)


def update_parent_meeting(mtg_id: int, payload: dict, actor_id: int) -> dict:
    db = get_db()
    _ensure_visibility_columns(db)
    row = db.execute("SELECT mtg_id FROM t_meeting WHERE mtg_id = ?", (mtg_id,)).fetchone()
    if not row:
        raise ValueError("meeting series not found")
    updates: list[tuple[str, object]] = []
    if "title" in payload:
        title = str(payload.get("title") or "").strip()
        if len(title) < 2:
            raise ValueError("title must be at least 2 characters")
        updates.append(("mtg_title", title))
    if "description" in payload:
        updates.append(("mtg_description", payload.get("description") or None))
    if "topic_id" in payload:
        updates.append(("mtg_topic_id", _require_existing_topic(db, payload.get("topic_id"))))
    if "visibility" in payload or "mtg_visibility" in payload:
        updates.append(("mtg_visibility", _normalize_visibility(payload.get("visibility") or payload.get("mtg_visibility"))))
    for col, value in updates:
        db.execute(f"UPDATE t_meeting SET {col} = ? WHERE mtg_id = ?", (value, mtg_id))
    db.commit()
    return get_parent_meeting(mtg_id)


def list_instances_of_series(mtg_id: int) -> list[dict]:
    """Return all meeting instances belonging to a parent meeting series."""
    db = get_db()
    _ensure_visibility_columns(db)
    _ensure_meeting_optional_columns(db)
    rows = db.execute(
        """
        SELECT m.*, t.top_name AS topic_name, u.usr_display_name AS creator_name,
               (SELECT COUNT(*) FROM t_action a WHERE a.act_meeting_inst_id = m.min_id AND a.act_status != 'Cancelled') AS action_count,
               (SELECT COUNT(*) FROM t_meeting_participant mp WHERE mp.mpa_instance_id = m.min_id) AS participant_count
        FROM t_meeting_instance m
         LEFT JOIN t_topic t ON t.top_id = COALESCE(m.min_category_id, m.min_topic_id)
        LEFT JOIN t_user u ON u.usr_id = m.min_created_by
        WHERE m.min_meeting_id = ?
        ORDER BY m.min_created_at DESC
        """,
        (mtg_id,),
    ).fetchall()
    items: list[dict] = []
    user_id = _current_user_id()
    is_admin = _is_admin()
    serials = _get_series_occurrence_serials(db, mtg_id)
    # Pre-compute series-level access for the current user (series creator or default participant)
    series_can_view = False
    if not is_admin and user_id is not None:
        _ensure_series_participant_table(db)
        parent = db.execute("SELECT mtg_created_by FROM t_meeting WHERE mtg_id = ?", (mtg_id,)).fetchone()
        if parent and int(parent["mtg_created_by"] or 0) == user_id:
            series_can_view = True
        else:
            sp = db.execute(
                "SELECT 1 FROM t_meeting_series_participant WHERE msp_meeting_id = ? AND msp_user_id = ? LIMIT 1",
                (mtg_id, user_id),
            ).fetchone()
            series_can_view = sp is not None
    for row in rows:
        item = dict(row)
        meeting_serial = serials.get(int(item["min_id"]))
        item["meeting_serial"] = meeting_serial
        item["meeting_display_id"] = _format_series_occurrence_display_id(mtg_id, meeting_serial)
        visibility = _normalize_visibility(item.get("min_visibility"))
        if visibility == "private" and not is_admin:
            if user_id is None:
                continue
            if int(item.get("min_created_by") or 0) != user_id and user_id not in _meeting_participant_ids(int(item["min_id"])):
                continue
        # Compute occurrence_access: can this user enter this meeting?
        if is_admin:
            item["occurrence_access"] = True
        elif user_id is None:
            item["occurrence_access"] = False
        else:
            occurrence_access = (
                series_can_view
                or int(item.get("min_created_by") or 0) == user_id
                or user_id in _meeting_participant_ids(int(item["min_id"]))
            )
            item["occurrence_access"] = occurrence_access
        # Fetch participant display names for this occurrence
        prows = db.execute(
            "SELECT u.usr_display_name FROM t_meeting_participant mp JOIN t_user u ON u.usr_id = mp.mpa_user_id WHERE mp.mpa_instance_id = ?",
            (item["min_id"],),
        ).fetchall()
        item["participant_names"] = [r["usr_display_name"] for r in prows]
        items.append(item)
    return items


def get_series_participants(mtg_id: int) -> list[dict]:
    db = get_db()
    _ensure_series_participant_table(db)
    rows = db.execute(
        """
        SELECT msp.msp_id, msp.msp_user_id, u.usr_username, u.usr_display_name,
               msp.msp_kind, msp.msp_added_by, adder.usr_display_name AS added_by_name,
               msp.msp_added_at
        FROM t_meeting_series_participant msp
        JOIN t_user u ON u.usr_id = msp.msp_user_id
        LEFT JOIN t_user adder ON adder.usr_id = msp.msp_added_by
        WHERE msp.msp_meeting_id = ?
        ORDER BY u.usr_display_name ASC
        """,
        (mtg_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _is_series_participant_used_in_attached_occurrences(mtg_id: int, user_id: int) -> bool:
    db = get_db()
    row = db.execute(
        """
        SELECT 1
        FROM t_meeting_instance mi
        JOIN t_meeting_participant mp
          ON mp.mpa_instance_id = mi.min_id
         AND mp.mpa_user_id = ?
        WHERE mi.min_meeting_id = ?
        LIMIT 1
        """,
        (user_id, mtg_id),
    ).fetchone()
    return row is not None


def set_series_participants(mtg_id: int, participants: list[dict], actor_id: int) -> list[dict]:
    db = get_db()
    _ensure_series_participant_table(db)
    db.execute("SELECT mtg_id FROM t_meeting WHERE mtg_id = ?", (mtg_id,)).fetchone() or (_ for _ in ()).throw(ValueError("meeting series not found"))
    existing_rows = db.execute(
        "SELECT msp_user_id FROM t_meeting_series_participant WHERE msp_meeting_id = ?",
        (mtg_id,),
    ).fetchall()
    existing_user_ids = {int(row["msp_user_id"]) for row in existing_rows}
    normalized: list[tuple[int, str]] = []
    seen: set[int] = set()
    for item in participants or []:
        user_id = int(item.get("user_id"))
        if user_id in seen:
            continue
        seen.add(user_id)
        normalized.append((user_id, _normalize_participant_kind(item.get("kind"))))
    removing_user_ids = existing_user_ids - seen
    blocked_user_ids = [
        uid for uid in sorted(removing_user_ids)
        if _is_series_participant_used_in_attached_occurrences(mtg_id, uid)
    ]
    if blocked_user_ids:
        raise ValueError(
            "cannot remove series participant while assigned to an attached meeting occurrence; remove from occurrence participants first"
        )
    db.execute("DELETE FROM t_meeting_series_participant WHERE msp_meeting_id = ?", (mtg_id,))
    for user_id, kind in normalized:
        db.execute(
            """
            INSERT INTO t_meeting_series_participant (msp_meeting_id, msp_user_id, msp_kind, msp_added_by)
            VALUES (?, ?, ?, ?)
            """,
            (mtg_id, user_id, kind, actor_id),
        )
    if actor_id not in seen:
        db.execute(
            """
            INSERT OR IGNORE INTO t_meeting_series_participant (msp_meeting_id, msp_user_id, msp_kind, msp_added_by)
            VALUES (?, ?, 'Compulsory', ?)
            """,
            (mtg_id, actor_id, actor_id),
        )
    db.commit()
    return get_series_participants(mtg_id)


def add_series_participant(mtg_id: int, user_id: int, kind: str, actor_id: int) -> list[dict]:
    db = get_db()
    _ensure_series_participant_table(db)
    db.execute(
        """
        INSERT INTO t_meeting_series_participant (msp_meeting_id, msp_user_id, msp_kind, msp_added_by)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(msp_meeting_id, msp_user_id)
        DO UPDATE SET msp_kind = excluded.msp_kind, msp_added_by = excluded.msp_added_by, msp_added_at = CURRENT_TIMESTAMP
        """,
        (mtg_id, user_id, _normalize_participant_kind(kind), actor_id),
    )
    db.commit()
    return get_series_participants(mtg_id)


def remove_series_participant(mtg_id: int, user_id: int) -> list[dict]:
    db = get_db()
    _ensure_series_participant_table(db)
    if _is_series_participant_used_in_attached_occurrences(mtg_id, user_id):
        raise ValueError(
            "cannot remove series participant while assigned to an attached meeting occurrence; remove from occurrence participants first"
        )
    db.execute("DELETE FROM t_meeting_series_participant WHERE msp_meeting_id = ? AND msp_user_id = ?", (mtg_id, user_id))
    db.commit()
    return get_series_participants(mtg_id)


def create_occurrence_from_series(mtg_id: int, payload: dict, actor_id: int) -> dict:
    db = get_db()
    _ensure_visibility_columns(db)
    _ensure_series_participant_table(db)
    _ensure_meeting_owner_table(db)
    participant_columns = _ensure_participant_kind_column(db)
    has_participant_kind = "mpa_kind" in participant_columns
    series = db.execute("SELECT mtg_id, mtg_title, mtg_visibility, mtg_topic_id, mtg_description FROM t_meeting WHERE mtg_id = ?", (mtg_id,)).fetchone()
    if not series:
        raise ValueError("meeting series not found")
    topic_id = _resolve_series_topic_id(db, mtg_id)
    meeting_date = str(payload.get("date") or payload.get("min_date") or date.today().isoformat()).strip()
    title = f"{series['mtg_title']} - {meeting_date}"
    visibility = _normalize_visibility(payload.get("visibility") or payload.get("min_visibility") or series["mtg_visibility"])
    cur = db.execute(
        """
        INSERT INTO t_meeting_instance (
            min_meeting_id, min_title, min_date, min_notes, min_visibility,
            min_topic_id, min_category_id, min_created_by, min_type, min_archived
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            mtg_id,
            title,
            meeting_date,
            payload.get("notes") or None,
            visibility,
            topic_id,
            topic_id,
            actor_id,
            payload.get("type") or None,
        ),
    )
    min_id = int(cur.lastrowid)
    participants = get_series_participants(mtg_id)
    for participant in participants:
        if has_participant_kind:
            db.execute(
                """
                INSERT OR IGNORE INTO t_meeting_participant (mpa_instance_id, mpa_user_id, mpa_added_by, mpa_kind)
                VALUES (?, ?, ?, ?)
                """,
                (min_id, participant["msp_user_id"], actor_id, participant["msp_kind"]),
            )
        else:
            db.execute(
                """
                INSERT OR IGNORE INTO t_meeting_participant (mpa_instance_id, mpa_user_id, mpa_added_by)
                VALUES (?, ?, ?)
                """,
                (min_id, participant["msp_user_id"], actor_id),
            )
    # Ensure the occurrence creator is always a participant.
    if has_participant_kind:
        db.execute(
            """
            INSERT OR IGNORE INTO t_meeting_participant (mpa_instance_id, mpa_user_id, mpa_added_by, mpa_kind)
            VALUES (?, ?, ?, 'Compulsory')
            """,
            (min_id, actor_id, actor_id),
        )
    else:
        db.execute(
            """
            INSERT OR IGNORE INTO t_meeting_participant (mpa_instance_id, mpa_user_id, mpa_added_by)
            VALUES (?, ?, ?)
            """,
            (min_id, actor_id, actor_id),
        )
    db.execute(
        "INSERT OR IGNORE INTO t_meeting_owner (mow_instance_id, mow_user_id, mow_granted_by) VALUES (?, ?, ?)",
        (min_id, actor_id, actor_id),
    )
    db.commit()
    return get_meeting(min_id)


def get_series_actions(mtg_id: int) -> list[dict]:
    db = get_db()
    _ensure_visibility_columns(db)
    rows = db.execute(
        """
        SELECT a.act_id, a.act_ref, a.act_title, a.act_desc, a.act_status, a.act_priority,
             a.act_visibility, a.act_created_at, a.act_meeting_inst_id,
             a.act_deadline,
             mi.min_title AS occurrence_title, mi.min_date AS occurrence_date,
             COALESCE(mi.min_visibility, 'public') AS occurrence_visibility,
             mi.min_created_by AS occurrence_created_by,
             creator.usr_display_name AS creator_name,
             lead.usr_display_name AS lead_name,
             (SELECT COUNT(DISTINCT z.asg_user_id) FROM t_assignment z WHERE z.asg_action_id = a.act_id) AS asg_total,
             (SELECT GROUP_CONCAT(DISTINCT u2.usr_display_name)
                FROM t_assignment z JOIN t_user u2 ON u2.usr_id = z.asg_user_id
               WHERE z.asg_action_id = a.act_id) AS assignee_names
        FROM t_action a
        JOIN t_meeting_instance mi ON mi.min_id = a.act_meeting_inst_id
        LEFT JOIN t_user creator ON creator.usr_id = a.act_created_by
        LEFT JOIN t_assignment asg ON asg.asg_action_id = a.act_id AND INSTR(',' || asg.asg_role || ',', ',Lead,') > 0
        LEFT JOIN t_user lead ON lead.usr_id = asg.asg_user_id
        WHERE mi.min_meeting_id = ? AND a.act_archived = 0
        ORDER BY mi.min_date DESC, a.act_created_at DESC
        """,
        (mtg_id,),
    ).fetchall()
    items: list[dict] = []
    user_id = _current_user_id()
    for row in rows:
        item = dict(row)
        occurrence_visibility = _normalize_visibility(item.get("occurrence_visibility"))
        if occurrence_visibility == "private" and not _is_admin():
            if user_id is None:
                continue
            if int(item.get("occurrence_created_by") or 0) != user_id and user_id not in _meeting_participant_ids(int(item["act_meeting_inst_id"])):
                continue
        if _normalize_visibility(item.get("act_visibility")) == "private" and not _is_admin():
            if user_id is None:
                continue
            if not _is_action_participant(int(item["act_id"]), user_id):
                continue
        items.append(item)
    return items


def get_series_decisions(mtg_id: int) -> list[dict]:
    db = get_db()
    _ensure_visibility_columns(db)
    from actionhub.decisions.service import DecisionService

    decision_cols = DecisionService._decision_columns(db)
    meeting_expr = DecisionService._meeting_expr(db, "d")
    deleted_condition = DecisionService._deleted_condition(db, "d", decision_cols)
    instance_id_expr = "d.mdc_instance_id" if "mdc_instance_id" in decision_cols else "NULL AS mdc_instance_id"
    meeting_id_expr = "d.mdc_meeting_id" if "mdc_meeting_id" in decision_cols else "NULL AS mdc_meeting_id"
    rows = db.execute(
        f"""
        SELECT d.mdc_id, d.mdc_title, d.mdc_body,
               {DecisionService._status_expr(decision_cols, 'd')} AS mdc_status,
               {meeting_id_expr}, {instance_id_expr},
               mi.min_title AS occurrence_title, mi.min_date AS occurrence_date,
               d.mdc_category_id, d.mdc_secondary_category_id,
               COALESCE(mi.min_visibility, 'public') AS occurrence_visibility,
               mi.min_created_by AS occurrence_created_by,
               tp.top_name AS category_name, tp2.top_name AS secondary_category_name,
               u.usr_display_name AS creator_name, d.mdc_created_at, d.mdc_created_by
        FROM t_meeting_decision d
        JOIN t_meeting_instance mi ON mi.min_id = {meeting_expr}
        LEFT JOIN t_topic tp ON tp.top_id = d.mdc_category_id
        LEFT JOIN t_topic tp2 ON tp2.top_id = d.mdc_secondary_category_id
        LEFT JOIN t_user u ON u.usr_id = d.mdc_created_by
        WHERE mi.min_meeting_id = ? AND {deleted_condition}
        ORDER BY d.mdc_created_at DESC
        """,
        (mtg_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_occurrence_comments(min_id: int) -> dict:
    db = get_db()
    _ensure_visibility_columns(db)
    comment_cols = _table_columns(db, "t_comment")
    meeting = db.execute("SELECT min_id, min_meeting_id, min_date, COALESCE(min_visibility, 'public') AS min_visibility FROM t_meeting_instance WHERE min_id = ?", (min_id,)).fetchone()
    if not meeting:
        raise ValueError("meeting not found")
    if _normalize_visibility(meeting["min_visibility"]) == "private" and not _can_view_private_meeting(min_id):
        raise ValueError("meeting not found")
    previous = db.execute(
        """
        SELECT min_id, min_date
        FROM t_meeting_instance
        WHERE min_meeting_id = ? AND min_date < ?
        ORDER BY min_date DESC, min_id DESC
        LIMIT 1
        """,
        (meeting["min_meeting_id"], meeting["min_date"]),
    ).fetchone()

    def _fetch_follow_up_rows(occurrence_id: int) -> list[dict]:
        try:
            rows = db.execute(
                """
                SELECT
                    f.afb_action_id AS action_id,
                    a.act_title AS action_title,
                    f.afb_completion_pct,
                    f.afb_status,
                    f.afb_comment,
                    f.afb_blockers,
                    f.afb_created_at,
                    f.afb_user_id,
                    u.usr_display_name
                FROM t_action_feedback f
                JOIN t_action a ON a.act_id = f.afb_action_id
                LEFT JOIN t_user u ON u.usr_id = f.afb_user_id
                WHERE f.afb_meeting_inst_id = ?
                  AND a.act_archived = 0
                  AND f.afb_id = (
                      SELECT f2.afb_id
                      FROM t_action_feedback f2
                      WHERE f2.afb_action_id = f.afb_action_id
                        AND f2.afb_meeting_inst_id = ?
                      ORDER BY f2.afb_created_at DESC, f2.afb_id DESC
                      LIMIT 1
                  )
                ORDER BY f.afb_created_at DESC, f.afb_id DESC
                """,
                (occurrence_id, occurrence_id),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [dict(r) for r in rows]

    if "cmt_meeting_inst_id" not in comment_cols:
        # Schema-compat fallback: older DBs may not store comment.meeting_inst_id.
        # Derive occurrence comments from action->meeting occurrence linkage.
        deleted_condition = "c.cmt_is_deleted = 0" if "cmt_is_deleted" in comment_cols else "1 = 1"

        def _fetch_rows_via_action_link(occurrence_id: int) -> list[dict]:
            rows = db.execute(
                f"""
                SELECT c.cmt_id AS comment_id, c.cmt_body AS body, c.cmt_created_at,
                       c.cmt_created_by, u.usr_display_name AS author,
                       a.act_meeting_inst_id AS meeting_inst_id,
                       a.act_id AS action_id, a.act_title AS action_title
                FROM t_comment c
                JOIN t_action a ON a.act_id = c.cmt_act_id
                LEFT JOIN t_user u ON u.usr_id = c.cmt_created_by
                WHERE a.act_meeting_inst_id = ? AND {deleted_condition}
                ORDER BY c.cmt_created_at ASC, c.cmt_id ASC
                """,
                (occurrence_id,),
            ).fetchall()
            return [dict(r) for r in rows]

        return {
            "current": _fetch_rows_via_action_link(min_id),
            "previous": _fetch_rows_via_action_link(int(previous["min_id"])) if previous else [],
            "follow_up_current": _fetch_follow_up_rows(min_id),
            "follow_up_previous": _fetch_follow_up_rows(int(previous["min_id"])) if previous else [],
            "previous_occurrence_id": int(previous["min_id"]) if previous else None,
        }

    deleted_condition = "c.cmt_is_deleted = 0" if "cmt_is_deleted" in comment_cols else "1 = 1"

    def _fetch_rows(occurrence_id: int) -> list[dict]:
        rows = db.execute(
            f"""
            SELECT c.cmt_id AS comment_id, c.cmt_body AS body, c.cmt_created_at,
                   c.cmt_created_by, u.usr_display_name AS author,
                   c.cmt_meeting_inst_id AS meeting_inst_id,
                   a.act_id AS action_id, a.act_title AS action_title
            FROM t_comment c
            LEFT JOIN t_user u ON u.usr_id = c.cmt_created_by
            LEFT JOIN t_action a ON a.act_id = c.cmt_act_id
            WHERE c.cmt_meeting_inst_id = ? AND {deleted_condition}
            ORDER BY c.cmt_created_at ASC, c.cmt_id ASC
            """,
            (occurrence_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    current_rows = _fetch_rows(min_id)
    previous_rows = _fetch_rows(int(previous["min_id"])) if previous else []
    current_follow_up = _fetch_follow_up_rows(min_id)
    previous_follow_up = _fetch_follow_up_rows(int(previous["min_id"])) if previous else []
    return {
        "current": current_rows,
        "previous": previous_rows,
        "follow_up_current": current_follow_up,
        "follow_up_previous": previous_follow_up,
        "previous_occurrence_id": int(previous["min_id"]) if previous else None,
    }


def get_all_meeting_series_summary() -> list[dict]:
    """Return all meeting series with aggregated action/decision/participant KPIs."""
    db = get_db()

    meeting_cols = _table_columns(db, "t_meeting")
    decision_cols = _table_columns(db, "t_meeting_decision") if "t_meeting_decision" in {
        row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    } else set()
    participant_table_exists = bool(
        db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='t_meeting_series_participant'"
        ).fetchone()
    )

    meeting_filter = "WHERE m.mtg_archived = 0" if "mtg_archived" in meeting_cols else ""
    participant_expr = (
        """
            (
                SELECT COUNT(DISTINCT msp.msp_user_id)
                FROM t_meeting_series_participant msp
                WHERE msp.msp_meeting_id = m.mtg_id
            )
        """
        if participant_table_exists
        else "0"
    )
    decision_join = ""
    decision_count_expr = "0"
    if decision_cols:
        decision_meeting_expr = "d.mdc_meeting_id = mi.min_id"
        if "mdc_instance_id" in decision_cols:
            decision_meeting_expr = f"({decision_meeting_expr} OR d.mdc_instance_id = mi.min_id)"
        deleted_filter = "COALESCE(d.mdc_deleted_at, 0) = 0" if "mdc_deleted_at" in decision_cols else "1 = 1"
        decision_join = (
            "LEFT JOIN t_meeting_decision d "
            f"ON {decision_meeting_expr} AND {deleted_filter}"
        )
        decision_count_expr = "COUNT(DISTINCT d.mdc_id)"

    rows = db.execute(
        f'''
        SELECT
            m.mtg_id AS series_id,
            m.mtg_title AS series_title,
            COUNT(DISTINCT a.act_id) AS total_actions,
            COUNT(DISTINCT CASE WHEN a.act_status NOT IN ('Done','Cancelled') THEN a.act_id END) AS open_actions,
            COUNT(DISTINCT CASE WHEN a.act_deadline < date('now') AND a.act_status NOT IN ('Done','Cancelled') THEN a.act_id END) AS overdue_actions,
            COUNT(DISTINCT CASE WHEN a.act_status = 'Done' THEN a.act_id END) AS done_actions,
            {decision_count_expr} AS decision_count,
            {participant_expr} AS participant_count
        FROM t_meeting m
        LEFT JOIN t_meeting_instance mi
            ON mi.min_meeting_id = m.mtg_id
           AND mi.min_archived = 0
        LEFT JOIN t_action a
            ON a.act_meeting_inst_id = mi.min_id
           AND a.act_archived = 0
        {decision_join}
        {meeting_filter}
        GROUP BY m.mtg_id, m.mtg_title
        ORDER BY total_actions DESC
        '''
    ).fetchall()
    return [dict(r) for r in rows]
