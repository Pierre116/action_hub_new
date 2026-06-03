"""Action history logging utilities.

This module provides utility functions for logging changes to actions
and related entities in the t_action_history table.
"""
from datetime import datetime

from actionhub.middleware.db import get_db


def _history_column_mapping(db) -> dict:
    """Resolve history table column names across schema versions."""
    cols = {row[1] for row in db.execute("PRAGMA table_info(t_action_history)").fetchall()}
    if "ahi_action_id" in cols:
        return {
            "action_id": "ahi_action_id",
            "user_id": "ahi_changed_by",
            "field": "ahi_field",
            "old": "ahi_old_value",
            "new": "ahi_new_value",
            "at": "ahi_changed_at",
        }
    return {
        "action_id": "ahi_act_id",
        "user_id": "ahi_usr_id",
        "field": "ahi_field",
        "old": "ahi_old",
        "new": "ahi_new",
        "at": "ahi_at",
    }


def _normalize_change_type(change_type: str, col: dict) -> str:
    """Keep history insert compatible with old CHECK constraints."""
    # Legacy schema only allows this subset.
    if col["action_id"] == "ahi_action_id":
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
        if change_type not in allowed:
            return "Updated"
    return change_type


def log_action_history(
    action_id: int,
    user_id: int,
    change_type: str,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
) -> int:
    """Log a change to an action's history.

    Args:
        action_id: The action ID being modified.
        user_id: The user who made the change (1 for system).
        change_type: Type of change (e.g., 'StatusChange', 'WorkflowAdvance', 'AssignmentChange').
        field_name: The field that changed (optional).
        old_value: Previous value (optional).
        new_value: New value (optional).

    Returns:
        The ID of the inserted history record.
    """
    db = get_db()
    now = datetime.now().isoformat()
    col = _history_column_mapping(db)
    normalized_change_type = _normalize_change_type(change_type, col)

    cursor = db.execute(
        f"""INSERT INTO t_action_history
           ({col['action_id']}, {col['user_id']}, ahi_change_type, {col['field']}, {col['old']}, {col['new']}, {col['at']})
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            action_id,
            user_id,
            normalized_change_type,
            field_name,
            str(old_value) if old_value is not None else None,
            str(new_value) if new_value is not None else None,
            now,
        ),
    )
    # Note: Caller should call db.commit()
    return cursor.lastrowid


def get_action_history(action_id: int, limit: int = 100) -> list[dict]:
    """Get history records for an action.

    Args:
        action_id: The action ID.
        limit: Maximum number of records to return.

    Returns:
        List of history record dictionaries.
    """
    db = get_db()
    col = _history_column_mapping(db)

    records = db.execute(
        f"""SELECT h.*, u.usr_display_name AS usr_name
           FROM t_action_history h
           LEFT JOIN t_user u ON h.{col['user_id']} = u.usr_id
           WHERE h.{col['action_id']} = ?
           ORDER BY h.{col['at']} DESC
           LIMIT ?""",
        (action_id, limit),
    ).fetchall()

    return [dict(r) for r in records]
