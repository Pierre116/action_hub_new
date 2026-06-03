"""Comment service (Phase 2b) — Comment / Achievement / Roadblock."""
from __future__ import annotations

from actionhub.middleware.db import get_db

VALID_TYPES = {"Comment", "Achievement", "Roadblock"}


def _meeting_series_id_for_instance(db, meeting_inst_id: int) -> tuple[bool, int | None]:
    """Return (found, series_id).  found=False means the instance row doesn't exist."""
    row = db.execute(
        "SELECT min_meeting_id FROM t_meeting_instance WHERE min_id = ?",
        (meeting_inst_id,),
    ).fetchone()
    if not row:
        return False, None
    value = row["min_meeting_id"]
    return True, (int(value) if value is not None else None)


def _action_meeting_instance_id(db, action_id: int) -> int | None:
    row = db.execute(
        "SELECT act_meeting_inst_id FROM t_action WHERE act_id = ?",
        (action_id,),
    ).fetchone()
    if not row:
        raise ValueError("action not found")
    value = row["act_meeting_inst_id"]
    return int(value) if value else None


def _log_history(action_id: int, change_type: str, changed_by: int,
                  field: str | None, old_val: object, new_val: object) -> None:
    db = get_db()
    db.execute(
        """
        INSERT INTO t_action_history
            (ahi_action_id, ahi_change_type, ahi_field, ahi_old_value, ahi_new_value, ahi_changed_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (action_id, change_type, field,
         None if old_val is None else str(old_val),
         None if new_val is None else str(new_val),
         changed_by),
    )


def _resolve_root_action(cmt_act_id: int | None, _db) -> int | None:
    return cmt_act_id if cmt_act_id else None


def get_comments(act_id: int | None = None, meeting_inst_id: int | None = None) -> list[dict]:
    db = get_db()
    if act_id:
        rows = db.execute(
            """
            SELECT c.*, u.usr_display_name AS author_name,
                   e.usr_display_name AS editor_name
            FROM t_comment c
            LEFT JOIN t_user u ON u.usr_id = c.cmt_created_by
            LEFT JOIN t_user e ON e.usr_id = c.cmt_edited_by
            WHERE c.cmt_act_id = ?
            ORDER BY c.cmt_created_at ASC
            """,
            (act_id,),
        ).fetchall()
    elif meeting_inst_id:
        rows = db.execute(
            """
            SELECT c.*, u.usr_display_name AS author_name,
                   e.usr_display_name AS editor_name
            FROM t_comment c
            LEFT JOIN t_user u ON u.usr_id = c.cmt_created_by
            LEFT JOIN t_user e ON e.usr_id = c.cmt_edited_by
            WHERE c.cmt_meeting_inst_id = ?
            ORDER BY c.cmt_created_at ASC
            """,
            (meeting_inst_id,),
        ).fetchall()
    else:
        return []
    return [dict(r) for r in rows]


def create_comment(payload: dict, actor_id: int) -> dict:
    db = get_db()
    cmt_type = str(payload.get("type", "Comment"))
    if cmt_type not in VALID_TYPES:
        raise ValueError(f"type must be one of: {', '.join(sorted(VALID_TYPES))}")

    body = str(payload.get("body", "")).strip()
    if len(body) < 1:
        raise ValueError("body is required")
    if len(body) > 2000:
        raise ValueError("body must be ≤ 2000 characters")

    act_id = payload.get("action_id") or None
    meeting_inst_id = payload.get("meeting_inst_id") or None
    if meeting_inst_id not in (None, ""):
        meeting_inst_id = int(meeting_inst_id)
    else:
        meeting_inst_id = None
    if not act_id:
        raise ValueError("action_id required")

    linked_action_id = int(act_id)
    action_meeting_inst_id = None
    if linked_action_id:
        action_meeting_inst_id = _action_meeting_instance_id(db, linked_action_id)

    # Keep comment linkage coherent across action <-> meeting occurrence <-> meeting series.
    if meeting_inst_id is not None:
        found, target_series_id = _meeting_series_id_for_instance(db, meeting_inst_id)
        if not found:
            raise ValueError("meeting_inst_id not found")
        # target_series_id may be None for standalone meetings — that's fine
        if target_series_id is not None and action_meeting_inst_id is not None:
            _, action_series_id = _meeting_series_id_for_instance(db, action_meeting_inst_id)
            if action_series_id is not None and action_series_id != target_series_id:
                raise ValueError("meeting_inst_id must belong to the same meeting series as the action")
    elif action_meeting_inst_id is not None:
        # Default to the action's own occurrence when the action is meeting-linked.
        meeting_inst_id = action_meeting_inst_id

    # Check if cmt_meeting_inst_id column exists (may be missing in older DBs)
    comment_cols = {r["name"] for r in db.execute("PRAGMA table_info(t_comment)").fetchall()}
    if "cmt_meeting_inst_id" in comment_cols:
        cur = db.execute(
            """
            INSERT INTO t_comment (cmt_act_id, cmt_meeting_inst_id, cmt_type, cmt_body, cmt_created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (act_id, meeting_inst_id, cmt_type, body, actor_id),
        )
    else:
        cur = db.execute(
            """
            INSERT INTO t_comment (cmt_act_id, cmt_type, cmt_body, cmt_created_by)
            VALUES (?, ?, ?, ?)
            """,
            (act_id, cmt_type, body, actor_id),
        )
    cmt_id = cur.lastrowid
    db.commit()

    root_act = _resolve_root_action(act_id, db)
    if root_act:
        _log_history(root_act, "CommentAdded", actor_id, "CommentAdded",
                     None, f"#{cmt_id} [{cmt_type}]")
        db.commit()

    row = db.execute(
        """
        SELECT c.*, u.usr_display_name AS author_name, NULL AS editor_name
        FROM t_comment c
        LEFT JOIN t_user u ON u.usr_id = c.cmt_created_by
        WHERE c.cmt_id = ?
        """,
        (cmt_id,),
    ).fetchone()
    return dict(row)


def edit_comment(cmt_id: int, new_body: str, actor_id: int, actor_role: str) -> dict:
    db = get_db()
    row = db.execute("SELECT * FROM t_comment WHERE cmt_id = ?", (cmt_id,)).fetchone()
    if not row:
        raise ValueError("comment not found")
    cmt = dict(row)

    if cmt["cmt_is_deleted"]:
        raise ValueError("cannot edit a deleted comment")

    # Permission: Admin, TeamLead, or original author
    if actor_role not in ("Admin", "TeamLead") and cmt["cmt_created_by"] != actor_id:
        raise PermissionError("not authorised to edit this comment")

    new_body = new_body.strip()
    if len(new_body) < 1:
        raise ValueError("body cannot be empty")
    if len(new_body) > 2000:
        raise ValueError("body must be ≤ 2000 characters")

    db.execute(
        """
        UPDATE t_comment
        SET cmt_body = ?, cmt_edited_at = CURRENT_TIMESTAMP, cmt_edited_by = ?
        WHERE cmt_id = ?
        """,
        (new_body, actor_id, cmt_id),
    )
    db.commit()

    root_act = _resolve_root_action(cmt["cmt_act_id"], db)
    if root_act:
        _log_history(root_act, "CommentEdited", actor_id, "CommentEdited", str(cmt_id), None)
        db.commit()

    updated = db.execute(
        """
        SELECT c.*, u.usr_display_name AS author_name, e.usr_display_name AS editor_name
        FROM t_comment c
        LEFT JOIN t_user u ON u.usr_id = c.cmt_created_by
        LEFT JOIN t_user e ON e.usr_id = c.cmt_edited_by
        WHERE c.cmt_id = ?
        """,
        (cmt_id,),
    ).fetchone()
    return dict(updated)


def delete_comment(cmt_id: int, actor_id: int, actor_role: str) -> None:
    db = get_db()
    row = db.execute("SELECT * FROM t_comment WHERE cmt_id = ?", (cmt_id,)).fetchone()
    if not row:
        raise ValueError("comment not found")
    cmt = dict(row)

    if cmt["cmt_is_deleted"]:
        return  # idempotent

    if actor_role not in ("Admin", "TeamLead") and cmt["cmt_created_by"] != actor_id:
        raise PermissionError("not authorised to delete this comment")

    db.execute(
        "UPDATE t_comment SET cmt_is_deleted = 1 WHERE cmt_id = ?", (cmt_id,)
    )
    db.commit()

    root_act = _resolve_root_action(cmt["cmt_act_id"], db)
    if root_act:
        _log_history(root_act, "CommentDeleted", actor_id, "CommentDeleted", str(cmt_id), None)
        db.commit()
