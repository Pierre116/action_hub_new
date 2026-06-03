"""Assignment history service."""
from __future__ import annotations
from actionhub.middleware.db import get_db


def get_assignment_history(action_id: int) -> list[dict]:
    """Return the full assignment lifecycle history for an action."""
    db = get_db()
    rows = db.execute(
        """
        SELECT
            h.ash_id, h.ash_event, h.ash_role, h.ash_created_at, h.ash_comment,
            u_who.usr_display_name AS user_name,
            u_by.usr_display_name  AS by_name
        FROM t_assignment_history h
        LEFT JOIN t_user u_who ON u_who.usr_id = h.ash_user_id
        LEFT JOIN t_user u_by  ON u_by.usr_id  = h.ash_by_user_id
        WHERE h.ash_action_id = ?
        ORDER BY h.ash_created_at ASC
        """,
        (action_id,),
    ).fetchall()
    return [dict(r) for r in rows]
