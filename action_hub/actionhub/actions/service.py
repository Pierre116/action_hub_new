from __future__ import annotations

from actionhub.middleware.db import get_db
from actionhub.utils.ref_generator import generate_action_ref
from actionhub.utils.validators import (
    validate_assignment_role,
    validate_deadline,
    validate_priority,
    validate_status,
    validate_status_transition,
    validate_title,
)

ASSIGNMENT_ROLE_ORDER = ("Lead",)


def get_initial_assignment_status() -> str:
    db = get_db()
    row = db.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 't_assignment'"
    ).fetchone()
    table_sql = str(row[0] if row else "").upper()
    if "PENDING" in table_sql and "ACCEPTED" in table_sql and "DECLINED" in table_sql:
        return "Accepted"
    return "Assigned"


def _roles_from_csv(value: str | None) -> list[str]:
    if not value:
        return []
    tokens = {"Lead" if part.strip() in ("Delegate", "Decide", "Participate") else part.strip() for part in str(value).split(",") if part and part.strip()}
    return [role for role in ASSIGNMENT_ROLE_ORDER if role in tokens]


def _roles_to_csv(roles: list[str] | set[str]) -> str:
    ordered = [role for role in ASSIGNMENT_ROLE_ORDER if role in set(roles)]
    if not ordered:
        raise ValueError("at least one role is required")
    return ",".join(ordered)


def _has_role(csv_roles: str | None, role: str) -> bool:
    return role in _roles_from_csv(csv_roles)


def _log_history(action_id: int, change_type: str, changed_by: int, field: str | None, old_value: object, new_value: object) -> None:
    db = get_db()
    allowed = {
        "Created",
        "Updated",
        "StatusChange",
        "Reassigned",
        "Closed",
        "CommentAdded",
        "CommentEdited",
        "CommentDeleted",
        "Archived",
    }
    effective_change_type = change_type if change_type in allowed else "Updated"
    db.execute(
        """
        INSERT INTO t_action_history (
            ahi_action_id, ahi_change_type, ahi_field, ahi_old_value, ahi_new_value, ahi_changed_by
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            action_id,
            effective_change_type,
            field,
            None if old_value is None else str(old_value),
            None if new_value is None else str(new_value),
            changed_by,
        ),
    )


def _log_asg_history(
    action_id: int, user_id: int, role: str, event: str,
    by_user_id: int | None = None, comment: str | None = None
) -> None:
    """Write one row to t_assignment_history."""
    db = get_db()
    db.execute(
        """
        INSERT INTO t_assignment_history
            (ash_action_id, ash_user_id, ash_role, ash_event, ash_by_user_id, ash_comment)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (action_id, user_id, role, event, by_user_id, comment),
    )


def _get_action_or_raise(action_id: int) -> dict:
    db = get_db()
    row = db.execute("SELECT * FROM t_action WHERE act_id = ?", (action_id,)).fetchone()
    if not row:
        raise ValueError("action not found")
    return dict(row)


def _get_action_context(action_id: int) -> dict:
    db = get_db()
    action_cols = {row[1] for row in db.execute("PRAGMA table_info(t_action)").fetchall()}
    if "act_visibility" not in action_cols:
        db.execute("ALTER TABLE t_action ADD COLUMN act_visibility TEXT NOT NULL DEFAULT 'public'")
        action_cols.add("act_visibility")
    row = db.execute(
        """
        SELECT a.act_id, a.act_created_by, a.act_owner_id, a.act_visibility, a.act_meeting_inst_id,
             m.min_created_by AS meeting_created_by,
             mtg.mtg_visibility,
             COALESCE(m.min_visibility, 'public') AS meeting_instance_visibility
        FROM t_action a
        LEFT JOIN t_meeting_instance m ON m.min_id = a.act_meeting_inst_id
        LEFT JOIN t_meeting mtg ON mtg.mtg_id = m.min_meeting_id
        WHERE a.act_id = ?
        """,
        (action_id,),
    ).fetchone()
    if not row:
        raise ValueError("action not found")
    return dict(row)


def _meeting_participant_ids(meeting_inst_id: int) -> set[int]:
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT mpa_user_id FROM t_meeting_participant WHERE mpa_instance_id = ?",
        (meeting_inst_id,),
    ).fetchall()
    return {int(row[0]) for row in rows}


def _can_edit_action(action_id: int, actor_user_id: int, actor_role: str) -> bool:
    if actor_role == "Admin":
        return True
    context = _get_action_context(action_id)
    uid = int(actor_user_id)
    # Creator and Lead (owner) can always edit their own action.
    if int(context.get("act_created_by") or 0) == uid:
        return True
    if int(context.get("act_owner_id") or 0) == uid:
        return True
    meeting_inst_id = context.get("act_meeting_inst_id")
    if meeting_inst_id:
        return int(context.get("meeting_created_by") or 0) == uid
    return False


def _is_action_participant(action_id: int, user_id: int) -> bool:
    db = get_db()
    row = db.execute(
        "SELECT 1 FROM t_assignment WHERE asg_action_id = ? AND asg_user_id = ? LIMIT 1",
        (action_id, user_id),
    ).fetchone()
    return row is not None


def _can_view_action(action_id: int, actor_user_id: int, actor_role: str, actor_team_id: int | None = None) -> bool:
    if actor_role == "Admin":
        return True
    context = _get_action_context(action_id)
    meeting_inst_id = context.get("act_meeting_inst_id")
    if meeting_inst_id:
        meeting_visibility = str(context.get("meeting_instance_visibility") or "public").strip().lower()
        if meeting_visibility == "private":
            if int(context.get("meeting_created_by") or 0) == int(actor_user_id):
                return True
            return _is_action_participant(action_id, actor_user_id)
        if _is_action_participant(action_id, actor_user_id):
            return True
        if int(context.get("meeting_created_by") or 0) == int(actor_user_id):
            return True
        db = get_db()
        row = db.execute(
            """
            SELECT 1
            FROM t_meeting_participant mp
            JOIN t_user pu ON pu.usr_id = mp.mpa_user_id
            JOIN t_team tt ON tt.tea_id = pu.usr_team_id
            WHERE mp.mpa_instance_id = ?
              AND tt.tea_leader_user_id = ?
            LIMIT 1
            """,
            (int(meeting_inst_id), int(actor_user_id)),
        ).fetchone()
        return row is not None

    visibility = str(context.get("act_visibility") or "public").strip().lower()
    if visibility == "private":
        return int(context.get("act_created_by") or 0) == int(actor_user_id) or _is_action_participant(action_id, actor_user_id)
    # Public non-meeting action: visible to creator, assignees, and creator's team leader only
    if int(context.get("act_created_by") or 0) == int(actor_user_id):
        return True
    if int(context.get("act_owner_id") or 0) == int(actor_user_id):
        return True
    if _is_action_participant(action_id, actor_user_id):
        return True
    # Team leader can see actions of any of their team members (creator, owner, or assignee)
    db = get_db()
    creator_id = int(context.get("act_created_by") or 0)
    owner_id = int(context.get("act_owner_id") or 0)
    row = db.execute(
        """
        SELECT 1 FROM t_team tt
        WHERE tt.tea_leader_user_id = ?
          AND (
              EXISTS (
                  SELECT 1 FROM t_user u
                  WHERE u.usr_id IN (?, ?) AND u.usr_team_id = tt.tea_id
              )
              OR EXISTS (
                  SELECT 1 FROM t_user_team ut
                  WHERE ut.utm_user_id IN (?, ?) AND ut.utm_team_id = tt.tea_id
              )
              OR EXISTS (
                  SELECT 1 FROM t_assignment ax
                  WHERE ax.asg_action_id = ?
                    AND (
                        EXISTS (SELECT 1 FROM t_user au WHERE au.usr_id = ax.asg_user_id AND au.usr_team_id = tt.tea_id)
                        OR EXISTS (SELECT 1 FROM t_user_team ut2 WHERE ut2.utm_user_id = ax.asg_user_id AND ut2.utm_team_id = tt.tea_id)
                    )
              )
          )
        LIMIT 1
        """,
        (actor_user_id, creator_id, owner_id, creator_id, owner_id, action_id),
    ).fetchone()
    if row is not None:
        return True
    return False



def _normalize_payload(payload: dict) -> dict:
    normalized = dict(payload)
    if "title" in normalized:
        normalized["title"] = validate_title(normalized["title"])
    if "tags" in normalized:
        normalized["tags"] = _normalize_tags(normalized.get("tags"))
    if "priority" in normalized:
        normalized["priority"] = validate_priority(normalized["priority"])
    if "deadline" in normalized:
        normalized["deadline"] = validate_deadline(normalized["deadline"])
    return normalized


def _normalize_tags(value) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (list, tuple, set)):
        raw_tags = [str(item or "") for item in value]
    else:
        raw_tags = str(value).replace("\n", ",").split(",")

    normalized_tags: list[str] = []
    seen: set[str] = set()
    for raw_tag in raw_tags:
        tag = str(raw_tag).strip().lstrip("#").upper()
        if not tag:
            continue
        if len(tag) > 120:
            tag = tag[:120]
        if tag in seen:
            continue
        seen.add(tag)
        normalized_tags.append(tag)
    return ", ".join(normalized_tags) or None


def _ensure_action_tags_column() -> None:
    db = get_db()
    columns = {row[1] for row in db.execute("PRAGMA table_info(t_action)").fetchall()}
    if "act_tags" not in columns:
        db.execute("ALTER TABLE t_action ADD COLUMN act_tags TEXT")
        columns.add("act_tags")
    if "act_machine_serial" in columns:
        rows = db.execute(
            "SELECT act_id, act_machine_serial, act_tags FROM t_action WHERE COALESCE(act_machine_serial, '') <> ''"
        ).fetchall()
        for row in rows:
            merged_tags = _normalize_tags(
                [part for part in [row["act_tags"], row["act_machine_serial"]] if part not in (None, "")]
            )
            if merged_tags != row["act_tags"]:
                db.execute("UPDATE t_action SET act_tags = ? WHERE act_id = ?", (merged_tags, row["act_id"]))


def _normalize_estimated_hours(value):
    if value is None or value == "":
        return None
    try:
        hours = float(value)
    except (TypeError, ValueError):
        raise ValueError("estimated_hours must be a number")
    if hours < 0:
        raise ValueError("estimated_hours must be >= 0")
    return round(hours, 2)


def get_action(action_id: int) -> dict:
    _ensure_action_tags_column()
    db = get_db()
    actor = {}
    try:
        from actionhub.middleware.auth_middleware import get_request_user

        actor = get_request_user() or {}
    except Exception:
        actor = {}
    actor_user_id = int(actor.get("id") or 0)
    actor_role = str(actor.get("role") or "Member")
    actor_team_id = None
    try:
        actor_team_id = int(actor.get("team_id")) if actor.get("team_id") not in (None, "") else None
    except (TypeError, ValueError):
        actor_team_id = None

    if not _can_view_action(action_id, actor_user_id, actor_role, actor_team_id):
        raise ValueError("action not found")

    action = _get_action_or_raise(action_id)

    assignments = db.execute(
        """
        SELECT a.asg_id, a.asg_user_id, u.usr_display_name, a.asg_role,
               a.asg_status, a.asg_assigned_date,
             a.asg_estimated_hours
        FROM t_assignment a
        JOIN t_user u ON u.usr_id = a.asg_user_id
        WHERE a.asg_action_id = ?
        ORDER BY CASE
            WHEN INSTR(',' || a.asg_role || ',', ',Lead,') > 0 THEN 1
            ELSE 2
        END, a.asg_id
        """,
        (action_id,),
    ).fetchall()

    history = db.execute(
        """
        SELECT h.ahi_id, h.ahi_change_type, h.ahi_field, h.ahi_old_value, h.ahi_new_value,
               h.ahi_changed_by, h.ahi_changed_at,
               u.usr_display_name AS changed_by_name
        FROM t_action_history h
        LEFT JOIN t_user u ON u.usr_id = h.ahi_changed_by
        WHERE h.ahi_action_id = ?
        ORDER BY h.ahi_changed_at DESC, h.ahi_id DESC
        """,
        (action_id,),
    ).fetchall()

    import re as _re
    history_list = [dict(row) for row in history]
    for entry in history_list:
        if entry.get("ahi_change_type") == "CommentAdded":
            m = _re.match(r"#(\d+)", entry.get("ahi_new_value") or "")
            if m:
                cmt = db.execute(
                    "SELECT cmt_body, cmt_type FROM t_comment WHERE cmt_id = ?",
                    (m.group(1),),
                ).fetchone()
                if cmt:
                    entry["ahi_comment_body"] = cmt["cmt_body"]
                    entry["ahi_comment_type"] = cmt["cmt_type"]

    # Enrich history: resolve user IDs and topic IDs to human-readable names
    _user_id_pool: set[int] = set()
    _topic_id_pool: set[int] = set()
    for entry in history_list:
        ctype = entry.get("ahi_change_type")
        field = entry.get("ahi_field") or ""
        for val in (entry.get("ahi_old_value"), entry.get("ahi_new_value")):
            if not val:
                continue
            if ctype in ("Reassigned", "Assign"):
                # values may be "Role:uid" or plain uid string
                uid_str = val.split(":", 1)[1] if ":" in str(val) else str(val)
                if uid_str.isdigit():
                    _user_id_pool.add(int(uid_str))
            elif ctype == "Updated" and field in ("act_topic_id", "act_secondary_topic_id"):
                if str(val).isdigit():
                    _topic_id_pool.add(int(val))

    _umap: dict[int, str] = {}
    if _user_id_pool:
        ph = ",".join("?" * len(_user_id_pool))
        for row in db.execute(
            f"SELECT usr_id, usr_display_name FROM t_user WHERE usr_id IN ({ph})",
            list(_user_id_pool),
        ).fetchall():
            _umap[row["usr_id"]] = row["usr_display_name"]

    _tmap: dict[int, str] = {}
    if _topic_id_pool:
        ph = ",".join("?" * len(_topic_id_pool))
        for row in db.execute(
            f"SELECT top_id, top_name FROM t_topic WHERE top_id IN ({ph})",
            list(_topic_id_pool),
        ).fetchall():
            _tmap[row["top_id"]] = row["top_name"]

    def _resolve_user_val(val: str | None) -> str | None:
        if not val:
            return val
        if ":" in str(val):
            role, uid_str = str(val).split(":", 1)
            name = _umap.get(int(uid_str), uid_str) if uid_str.isdigit() else uid_str
            return f"{role}: {name}"
        if str(val).isdigit():
            return _umap.get(int(val), val)
        return val

    for entry in history_list:
        ctype = entry.get("ahi_change_type")
        field = entry.get("ahi_field") or ""
        if ctype in ("Reassigned", "Assign"):
            entry["ahi_old_value"] = _resolve_user_val(entry.get("ahi_old_value"))
            entry["ahi_new_value"] = _resolve_user_val(entry.get("ahi_new_value"))
        elif ctype == "Updated" and field in ("act_topic_id", "act_secondary_topic_id"):
            for k in ("ahi_old_value", "ahi_new_value"):
                v = entry.get(k)
                if v and str(v).isdigit():
                    entry[k] = _tmap.get(int(v), v)

    # Enrich action with creator display name
    if action.get("act_created_by"):
        creator_row = db.execute(
            "SELECT usr_display_name FROM t_user WHERE usr_id = ?",
            (action["act_created_by"],),
        ).fetchone()
        action["creator_name"] = creator_row["usr_display_name"] if creator_row else None
    else:
        action["creator_name"] = None

    # Enrich action with owner display name. Fallback to lead assignment owner when legacy rows
    # don't have act_owner_id populated yet.
    owner_name = None
    if action.get("act_owner_id"):
        owner_row = db.execute(
            "SELECT usr_display_name FROM t_user WHERE usr_id = ?",
            (action["act_owner_id"],),
        ).fetchone()
        owner_name = owner_row["usr_display_name"] if owner_row else None
    if not owner_name:
        lead_row = db.execute(
            """
            SELECT u.usr_display_name, a.asg_user_id
            FROM t_assignment a
            JOIN t_user u ON u.usr_id = a.asg_user_id
            WHERE a.asg_action_id = ?
            ORDER BY CASE
                WHEN INSTR(',' || a.asg_role || ',', ',Lead,') > 0 THEN 0
                ELSE 1
            END, a.asg_id
            LIMIT 1
            """,
            (action_id,),
        ).fetchone()
        if lead_row:
            owner_name = lead_row["usr_display_name"]
            if not action.get("act_owner_id"):
                action["act_owner_id"] = lead_row["asg_user_id"]
    action["owner_name"] = owner_name

    # Enrich action with topic name
    if action.get("act_topic_id"):
        topic_row = db.execute(
            "SELECT top_name FROM t_topic WHERE top_id = ?",
            (action["act_topic_id"],),
        ).fetchone()
        action["topic_name"] = topic_row["top_name"] if topic_row else None
    else:
        action["topic_name"] = None

    # Enrich action with secondary topic name
    if action.get("act_secondary_topic_id"):
        sec_topic_row = db.execute(
            "SELECT top_name FROM t_topic WHERE top_id = ?",
            (action["act_secondary_topic_id"],),
        ).fetchone()
        action["secondary_topic_name"] = sec_topic_row["top_name"] if sec_topic_row else None
    else:
        action["secondary_topic_name"] = None

    # Enrich action with linked meeting (if any)
    if action.get("act_meeting_inst_id"):
        meeting_row = db.execute(
            "SELECT min_title, min_date FROM t_meeting_instance WHERE min_id = ?",
            (action["act_meeting_inst_id"],),
        ).fetchone()
        action["meeting_title"] = meeting_row["min_title"] if meeting_row else None
        action["meeting_date"] = meeting_row["min_date"] if meeting_row else None
    else:
        action["meeting_title"] = None
        action["meeting_date"] = None

    # Compute total assigned hours (excluding declined assignments)
    assigned_hours_list = [
        row["asg_estimated_hours"]
        for row in assignments
        if row["asg_estimated_hours"] is not None
    ]
    action["total_assigned_hours"] = sum(assigned_hours_list) if assigned_hours_list else None

    return {
        "action": action,
        "assignments": [dict(row) for row in assignments],
        "history": history_list,
    }


def create_action(payload: dict, actor_user_id: int) -> dict:
    _ensure_action_tags_column()
    db = get_db()
    if not actor_user_id:
        raise ValueError("creator is required to create an action")
    data = _normalize_payload(payload)

    title = validate_title(data.get("title", ""))
    priority = validate_priority(data.get("priority", "Medium"))
    deadline = validate_deadline(data.get("deadline"))
    if not deadline:
        raise ValueError("deadline (end date) is required")

    # Derive topic from meeting if not explicitly set
    topic_id = data.get("topic_id")
    meeting_id = data.get("meeting_id")
    if not topic_id and meeting_id:
        m_row = db.execute(
            "SELECT COALESCE(min_category_id, min_topic_id) AS meeting_topic_id FROM t_meeting_instance WHERE min_id = ?",
            (meeting_id,),
        ).fetchone()
        if m_row:
            topic_id = m_row["meeting_topic_id"]

    if not topic_id:
        fallback_topic = db.execute(
            "SELECT top_id FROM t_topic WHERE top_active = 1 ORDER BY top_id ASC LIMIT 1"
        ).fetchone()
        if fallback_topic:
            topic_id = fallback_topic["top_id"]

    if not topic_id:
        raise ValueError("topic_id is required — every action must belong to a topic")

    secondary_topic_id = data.get("secondary_topic_id") or None
    if secondary_topic_id:
        secondary_topic_id = int(secondary_topic_id)
        if secondary_topic_id == int(topic_id):
            raise ValueError("secondary_topic_id must differ from topic_id")

    visibility = str(data.get("act_visibility") or data.get("visibility") or "public").strip().lower()
    if visibility not in {"public", "private"}:
        visibility = "public"
    if meeting_id:
        meeting_visibility_row = db.execute(
            "SELECT COALESCE(min_visibility, 'public') AS min_visibility FROM t_meeting_instance WHERE min_id = ?",
            (meeting_id,),
        ).fetchone()
        if meeting_visibility_row and not data.get("act_visibility") and not data.get("visibility"):
            visibility = str(meeting_visibility_row["min_visibility"] or "public").strip().lower() or "public"

    # Team linkage is deprecated for newly created actions.
    team_id = None
    lead_user_id = int(data["lead_user_id"]) if data.get("lead_user_id") else None
    owner_user_id = lead_user_id or actor_user_id
    start_date = data.get("start_date")

    if meeting_id:
        meeting_participants = _meeting_participant_ids(int(meeting_id))
        if not meeting_participants:
            raise ValueError("meeting actions require at least one meeting participant")
        if lead_user_id is None:
            lead_user_id = actor_user_id if actor_user_id in meeting_participants else next(iter(sorted(meeting_participants)))
            owner_user_id = lead_user_id
        if lead_user_id is not None and lead_user_id not in meeting_participants:
            raise ValueError("meeting action assignees must be selected from the current meeting participant list")
    else:
        if lead_user_id not in (None, actor_user_id):
            raise ValueError("non-meeting actions can only be assigned to the creator")
        lead_user_id = actor_user_id

    ref = generate_action_ref()
    cursor = db.execute(
        """
        INSERT INTO t_action (
            act_ref, act_title, act_desc, act_tags, act_topic_id, act_secondary_topic_id,
            act_team_id, act_owner_id, act_priority, act_status,
            act_deadline, act_start_date, act_meeting_inst_id, act_visibility, act_source,
            act_created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Open', ?, ?, ?, ?, 'Manual', ?)
        """,
        (
            ref,
            title,
            data.get("description"),
            data.get("tags"),
            topic_id,
            secondary_topic_id,
            team_id,
            owner_user_id,
            priority,
            deadline,
            start_date,
            meeting_id,
            visibility,
            actor_user_id,
        ),
    )
    action_id = int(cursor.lastrowid)

    _log_history(action_id, "Created", actor_user_id, "act_id", None, action_id)

    if lead_user_id:
        assign_user(action_id, int(lead_user_id), "Lead", actor_user_id)
    else:
        assign_user(action_id, actor_user_id, "Lead", actor_user_id)

    if lead_user_id is None:
        db.execute("UPDATE t_action SET act_owner_id = ? WHERE act_id = ?", (actor_user_id, action_id))

    db.commit()
    return get_action(action_id)


def _sync_assignments(action_id: int, lead_user_id: int | None,
                      actor_user_id: int) -> None:
    """Sync Lead assignment for an action (edit mode)."""
    db = get_db()
    action = _get_action_or_raise(action_id)
    requested_ids = [uid for uid in ([lead_user_id] if lead_user_id is not None else []) if uid is not None]
    if not action.get("act_meeting_inst_id"):
        allowed_id = int(action.get("act_created_by") or 0)
        if any(int(uid) != allowed_id for uid in requested_ids):
            raise ValueError("non-meeting actions can only be assigned to the creator")
    else:
        participant_ids = _meeting_participant_ids(int(action["act_meeting_inst_id"]))
        for uid in requested_ids:
            if int(uid) not in participant_ids:
                raise ValueError("meeting action assignees must be selected from the current meeting participant list")

    def _get_row(user_id: int):
        return db.execute(
            """
            SELECT asg_id, asg_user_id, asg_role, asg_status
            FROM t_assignment
            WHERE asg_action_id = ? AND asg_user_id = ?
            """,
            (action_id, user_id),
        ).fetchone()

    def _set_roles(user_id: int, roles: list[str], default_status: str | None = None) -> None:
        existing = _get_row(user_id)
        effective_status = default_status or get_initial_assignment_status()
        if existing:
            if roles:
                db.execute(
                    "UPDATE t_assignment SET asg_role = ? WHERE asg_id = ?",
                    (_roles_to_csv(roles), existing["asg_id"]),
                )
            else:
                db.execute("DELETE FROM t_assignment WHERE asg_id = ?", (existing["asg_id"],))
        elif roles:
            db.execute(
                """
                INSERT INTO t_assignment (asg_action_id, asg_user_id, asg_role, asg_status, asg_assigned_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (action_id, user_id, _roles_to_csv(roles), effective_status, actor_user_id),
            )

    def _add_role(user_id: int, role: str) -> None:
        existing = _get_row(user_id)
        if existing:
            current_roles = _roles_from_csv(existing["asg_role"])
            if role in current_roles:
                return
            _set_roles(user_id, [*current_roles, role])
        else:
            _set_roles(user_id, [role])
        _log_asg_history(action_id, user_id, role, "Assigned", actor_user_id)

    def _remove_role(user_id: int, role: str) -> None:
        existing = _get_row(user_id)
        if not existing:
            return
        current_roles = _roles_from_csv(existing["asg_role"])
        if role not in current_roles:
            return
        remaining = [r for r in current_roles if r != role]
        _set_roles(user_id, remaining)
        _log_asg_history(action_id, user_id, role, "Removed", actor_user_id)

    if lead_user_id is not None:
        current_lead = db.execute(
            """
            SELECT asg_user_id
            FROM t_assignment
            WHERE asg_action_id = ? AND INSTR(',' || asg_role || ',', ',Lead,') > 0
            LIMIT 1
            """,
            (action_id,),
        ).fetchone()
        previous_lead_user_id = current_lead["asg_user_id"] if current_lead else None
        if previous_lead_user_id != lead_user_id:
            if previous_lead_user_id is not None:
                _remove_role(previous_lead_user_id, "Lead")
            _add_role(lead_user_id, "Lead")
            db.execute("UPDATE t_action SET act_owner_id = ? WHERE act_id = ?", (lead_user_id, action_id))
            _log_history(action_id, "Assign", actor_user_id, "Lead", previous_lead_user_id, lead_user_id)


def update_action(action_id: int, payload: dict, actor_user_id: int) -> dict:
    _ensure_action_tags_column()
    db = get_db()
    current = _get_action_or_raise(action_id)
    data = _normalize_payload(payload)

    mapping = {
        "title": "act_title",
        "description": "act_desc",
        "tags": "act_tags",
        "topic_id": "act_topic_id",
        "secondary_topic_id": "act_secondary_topic_id",
        "act_visibility": "act_visibility",
        "visibility": "act_visibility",
        "priority": "act_priority",
        "deadline": "act_deadline",
        "start_date": "act_start_date",
        "completion_pct": "act_completion_pct",
        "last_comment": "act_last_comment",
        "meeting_id": "act_meeting_inst_id",
    }

    set_parts: list[str] = []
    set_values: list[object] = []

    for key, field in mapping.items():
        if key not in data:
            continue
        new_value = data.get(key)
        if key == "topic_id" and not new_value:
            raise ValueError("topic_id cannot be removed — every action must belong to a topic")
        # secondary_topic_id: allow explicit None to clear it; validate != topic_id when set
        if key == "secondary_topic_id":
            new_value = int(new_value) if new_value else None
            resolved_primary = int(data.get("topic_id") or current.get("act_topic_id") or 0)
            if new_value and new_value == resolved_primary:
                raise ValueError("secondary_topic_id must differ from topic_id")
        old_value = current.get(field)
        if str(old_value) == str(new_value):
            continue
        set_parts.append(f"{field} = ?")
        set_values.append(new_value)
        _log_history(action_id, "Updated", actor_user_id, field, old_value, new_value)

    if set_parts:
        set_parts.append("act_updated_at = CURRENT_TIMESTAMP")
        db.execute(
            f"UPDATE t_action SET {', '.join(set_parts)} WHERE act_id = ?",
            [*set_values, action_id],
        )

    # Handle status change with full transition validation
    if "status" in data:
        new_status = validate_status(data["status"])
        current_status = current.get("act_status", "Open")
        if new_status != current_status:
            validate_status_transition(current_status, new_status)
            extra_set: list[str] = ["act_status = ?", "act_updated_at = CURRENT_TIMESTAMP"]
            extra_vals: list[object] = [new_status]
            if new_status == "On Hold":
                reason = (data.get("hold_reason") or "").strip()
                if not reason:
                    raise ValueError("hold_reason is required when status is On Hold")
                extra_set.append("act_hold_reason = ?")
                extra_vals.append(reason)
            if new_status == "Cancelled":
                reason = (data.get("cancel_reason") or "").strip()
                if not reason:
                    raise ValueError("cancel_reason is required when status is Cancelled")
                extra_set.append("act_cancel_reason = ?")
                extra_vals.append(reason)
            if new_status == "Done":
                extra_set.append("act_actual_date = COALESCE(act_actual_date, date('now'))")
            db.execute(
                f"UPDATE t_action SET {', '.join(extra_set)} WHERE act_id = ?",
                [*extra_vals, action_id],
            )
            _log_history(action_id, "StatusChange", actor_user_id, "act_status", current_status, new_status)

    # Sync assignments if provided; update team when lead changes
    if "lead_user_id" in data:
        lead_id = int(data["lead_user_id"]) if data.get("lead_user_id") else None
        _sync_assignments(action_id, lead_id, actor_user_id)
    db.commit()
    return get_action(action_id)


def transition_status(action_id: int, new_status: str, actor_user_id: int, payload: dict | None = None) -> dict:
    db = get_db()
    details = payload or {}
    status = validate_status(new_status)
    current = _get_action_or_raise(action_id)
    current_status = current["act_status"]

    if status == current_status:
        return get_action(action_id)

    validate_status_transition(current_status, status)

    extra_set: list[str] = []
    extra_vals: list[object] = []

    if status == "On Hold":
        reason = (details.get("hold_reason") or "").strip()
        if not reason:
            raise ValueError("hold_reason is required when status is On Hold")
        extra_set.append("act_hold_reason = ?")
        extra_vals.append(reason)

    if status == "Cancelled":
        reason = (details.get("cancel_reason") or "").strip()
        if not reason:
            raise ValueError("cancel_reason is required when status is Cancelled")
        extra_set.append("act_cancel_reason = ?")
        extra_vals.append(reason)

    if status == "Done":
        extra_set.append("act_actual_date = COALESCE(act_actual_date, date('now'))")

    set_clause = ["act_status = ?", "act_updated_at = CURRENT_TIMESTAMP", *extra_set]
    db.execute(
        f"UPDATE t_action SET {', '.join(set_clause)} WHERE act_id = ?",
        [status, *extra_vals, action_id],
    )

    _log_history(action_id, "StatusChange", actor_user_id, "act_status", current_status, status)
    db.commit()
    return get_action(action_id)


def assign_user(action_id: int, user_id: int, role: str, actor_user_id: int, estimated_hours=None) -> dict:
    db = get_db()
    action = _get_action_or_raise(action_id)
    normalized_role = validate_assignment_role(role)
    normalized_hours = _normalize_estimated_hours(estimated_hours)

    if not action.get("act_meeting_inst_id") and int(action.get("act_created_by") or 0) != int(user_id):
        raise ValueError("non-meeting actions can only be assigned to the creator")
    if action.get("act_meeting_inst_id"):
        participant_ids = _meeting_participant_ids(int(action["act_meeting_inst_id"]))
        if int(user_id) not in participant_ids:
            raise ValueError("meeting action assignees must be selected from the current meeting participant list")

    existing = db.execute(
        """
        SELECT asg_id, asg_role, asg_estimated_hours
        FROM t_assignment
        WHERE asg_action_id = ? AND asg_user_id = ?
        """,
        (action_id, user_id),
    ).fetchone()
    if existing and _has_role(existing["asg_role"], normalized_role):
        return {"asg_id": int(existing["asg_id"]), "estimated_hours": existing["asg_estimated_hours"]}

    if normalized_role == "Lead":
        lead = db.execute(
            """
            SELECT asg_id
            FROM t_assignment
            WHERE asg_action_id = ?
              AND asg_user_id != ?
              AND INSTR(',' || asg_role || ',', ',Lead,') > 0
            """,
            (action_id, user_id),
        ).fetchone()
        if lead:
            raise ValueError("action already has a Lead")

    if existing:
        merged_roles = _roles_to_csv([*_roles_from_csv(existing["asg_role"]), normalized_role])
        db.execute(
            "UPDATE t_assignment SET asg_role = ? WHERE asg_id = ?",
            (merged_roles, existing["asg_id"]),
        )
        asg_id = int(existing["asg_id"])
        effective_hours = existing["asg_estimated_hours"]
    else:
        initial_status = get_initial_assignment_status()
        cursor = db.execute(
            """
            INSERT INTO t_assignment (
                asg_action_id, asg_user_id, asg_role, asg_status, asg_assigned_by, asg_estimated_hours
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (action_id, user_id, normalized_role, initial_status, actor_user_id, normalized_hours),
        )
        asg_id = int(cursor.lastrowid)
        effective_hours = normalized_hours

    _log_history(action_id, "Reassigned", actor_user_id, "assignment", None, f"{normalized_role}:{user_id}")
    _log_asg_history(action_id, user_id, normalized_role, "Assigned", actor_user_id)
    if normalized_role == "Lead":
        db.execute("UPDATE t_action SET act_owner_id = ? WHERE act_id = ?", (user_id, action_id))
    db.commit()
    return {"asg_id": asg_id, "estimated_hours": effective_hours}


def update_assignment_hours(action_id: int, asg_id: int, estimated_hours, actor_user_id: int, actor_role: str) -> dict:
    db = get_db()
    row = db.execute(
        """
        SELECT asg_id, asg_action_id, asg_user_id, asg_estimated_hours
        FROM t_assignment
        WHERE asg_id = ? AND asg_action_id = ?
        """,
        (asg_id, action_id),
    ).fetchone()
    if not row:
        raise ValueError("assignment not found")

    is_admin = actor_role in ("Admin", "TeamLead")
    is_self = int(row["asg_user_id"]) == int(actor_user_id)

    if not (is_admin or is_self):
        raise PermissionError("forbidden")

    new_hours = _normalize_estimated_hours(estimated_hours)
    old_hours = row["asg_estimated_hours"]

    db.execute(
        "UPDATE t_assignment SET asg_estimated_hours = ? WHERE asg_id = ?",
        (new_hours, asg_id),
    )
    _log_history(action_id, "Updated", actor_user_id, "asg_estimated_hours", old_hours, new_hours)
    db.commit()
    return {"asg_id": int(asg_id), "estimated_hours": new_hours}


def remove_assignment(action_id: int, assignment_id: int, actor_user_id: int) -> None:
    db = get_db()
    row = db.execute(
        "SELECT asg_id, asg_role, asg_user_id FROM t_assignment WHERE asg_id = ? AND asg_action_id = ?",
        (assignment_id, action_id),
    ).fetchone()
    if not row:
        raise ValueError("assignment not found")

    # Prevent removing the last Lead on the action
    if _has_role(row["asg_role"], "Lead"):
        other_lead = db.execute(
            """SELECT asg_id FROM t_assignment
               WHERE asg_action_id = ? AND asg_id != ?
                 AND INSTR(',' || asg_role || ',', ',Lead,') > 0""",
            (action_id, assignment_id),
        ).fetchone()
        if not other_lead:
            raise ValueError("cannot remove the last Lead assignment; reassign Lead first")

    db.execute("DELETE FROM t_assignment WHERE asg_id = ?", (assignment_id,))
    _log_history(action_id, "Reassigned", actor_user_id, "assignment", f"{row['asg_role']}:{row['asg_user_id']}", None)
    _log_asg_history(action_id, row["asg_user_id"], row["asg_role"], "Removed", actor_user_id)
    db.commit()


def archive_action(action_id: int, actor_user_id: int) -> None:
    """Soft-delete: sets act_archived=1 so the action is hidden everywhere."""
    db = get_db()
    row = db.execute("SELECT act_id, act_ref FROM t_action WHERE act_id = ?", (action_id,)).fetchone()
    if not row:
        raise ValueError("action not found")
    db.execute(
        """
        UPDATE t_action
        SET act_archived = 1,
            act_archived_by = ?,
            act_archived_at = CURRENT_TIMESTAMP,
            act_updated_at  = CURRENT_TIMESTAMP
        WHERE act_id = ?
        """,
        (actor_user_id, action_id),
    )
    _log_history(action_id, "Archived", actor_user_id, "act_archived", "0", "1")
    db.commit()
