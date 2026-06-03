"""Text-based meeting memo service (paste-from-Word, ordered list)."""
from __future__ import annotations

from datetime import datetime

from actionhub.middleware.db import get_db


def list_text_memos(meeting_id: int) -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT m.mmm_id, m.mmm_instance_id, m.mmm_title, m.mmm_body,
               m.mmm_date, m.mmm_sort_order, m.mmm_created_at, m.mmm_updated_at,
               n.last_notified_at AS mmm_last_notified_at,
               u.usr_display_name AS created_by_name
        FROM t_meeting_memo m
        LEFT JOIN t_user u ON u.usr_id = m.mmm_created_by
        LEFT JOIN (
            SELECT ntf_action_id, MAX(ntf_created_at) AS last_notified_at
            FROM t_notification
            WHERE ntf_event_type LIKE 'meeting_memo:%'
              AND ntf_action_id IS NOT NULL
            GROUP BY ntf_action_id
        ) n ON n.ntf_action_id = m.mmm_id
        WHERE m.mmm_instance_id = ?
        ORDER BY m.mmm_sort_order ASC, m.mmm_created_at ASC
        """,
        (meeting_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def create_text_memo(meeting_id: int, title: str, body: str, actor_id: int, date: str | None = None) -> dict:
    db = get_db()
    meeting = db.execute(
        "SELECT min_title, COALESCE(min_created_at, CURRENT_TIMESTAMP) AS min_created_at FROM t_meeting_instance WHERE min_id = ?",
        (meeting_id,),
    ).fetchone()
    if not meeting:
        raise ValueError("meeting not found")

    memo_date = (date or "").strip() or datetime.now().strftime("%Y-%m-%d")

    row = db.execute(
        "SELECT COALESCE(MAX(mmm_sort_order), 0) + 1 AS next_order FROM t_meeting_memo WHERE mmm_instance_id = ?",
        (meeting_id,),
    ).fetchone()
    sort_order = row["next_order"]

    auto_title = f"{sort_order} - {meeting['min_title']} - {memo_date}"
    title = (title or "").strip() or auto_title

    cur = db.execute(
        """INSERT INTO t_meeting_memo
           (mmm_instance_id, mmm_title, mmm_body, mmm_date, mmm_sort_order, mmm_created_by)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (meeting_id, title, body or "", memo_date, sort_order, actor_id),
    )
    db.commit()
    return _get_one(cur.lastrowid)


def update_text_memo(mmm_id: int, payload: dict) -> dict:
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM t_meeting_memo WHERE mmm_id = ?", (mmm_id,)
    ).fetchone():
        raise ValueError("memo not found")

    if "title" in payload:
        db.execute(
            "UPDATE t_meeting_memo SET mmm_title = ?, mmm_updated_at = CURRENT_TIMESTAMP WHERE mmm_id = ?",
            ((payload["title"] or "").strip(), mmm_id),
        )
    if "body" in payload:
        db.execute(
            "UPDATE t_meeting_memo SET mmm_body = ?, mmm_updated_at = CURRENT_TIMESTAMP WHERE mmm_id = ?",
            (payload["body"] or "", mmm_id),
        )
    if "date" in payload:
        db.execute(
            "UPDATE t_meeting_memo SET mmm_date = ?, mmm_updated_at = CURRENT_TIMESTAMP WHERE mmm_id = ?",
            (payload["date"] or None, mmm_id),
        )
    if "sort_order" in payload:
        db.execute(
            "UPDATE t_meeting_memo SET mmm_sort_order = ? WHERE mmm_id = ?",
            (int(payload["sort_order"]), mmm_id),
        )
    db.commit()
    return _get_one(mmm_id)


def move_memo(mmm_id: int, direction: str) -> list[dict]:
    """Swap sort_order with the previous or next memo. direction: 'up' or 'down'."""
    db = get_db()
    current = db.execute(
        "SELECT mmm_id, mmm_instance_id, mmm_sort_order FROM t_meeting_memo WHERE mmm_id = ?",
        (mmm_id,),
    ).fetchone()
    if not current:
        raise ValueError("memo not found")

    meeting_id = current["mmm_instance_id"]
    current_order = current["mmm_sort_order"]

    if direction == "up":
        neighbour = db.execute(
            """SELECT mmm_id, mmm_sort_order FROM t_meeting_memo
               WHERE mmm_instance_id = ? AND mmm_sort_order < ?
               ORDER BY mmm_sort_order DESC LIMIT 1""",
            (meeting_id, current_order),
        ).fetchone()
    else:
        neighbour = db.execute(
            """SELECT mmm_id, mmm_sort_order FROM t_meeting_memo
               WHERE mmm_instance_id = ? AND mmm_sort_order > ?
               ORDER BY mmm_sort_order ASC LIMIT 1""",
            (meeting_id, current_order),
        ).fetchone()

    if neighbour:
        db.execute(
            "UPDATE t_meeting_memo SET mmm_sort_order = ? WHERE mmm_id = ?",
            (neighbour["mmm_sort_order"], mmm_id),
        )
        db.execute(
            "UPDATE t_meeting_memo SET mmm_sort_order = ? WHERE mmm_id = ?",
            (current_order, neighbour["mmm_id"]),
        )
        db.commit()

    return list_text_memos(meeting_id)


def delete_text_memo(mmm_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM t_meeting_memo WHERE mmm_id = ?", (mmm_id,))
    db.commit()


def _get_one(mmm_id: int) -> dict:
    db = get_db()
    row = db.execute(
        """
        SELECT m.mmm_id, m.mmm_instance_id, m.mmm_title, m.mmm_body,
               m.mmm_date, m.mmm_sort_order, m.mmm_created_at, m.mmm_updated_at,
               n.last_notified_at AS mmm_last_notified_at,
               u.usr_display_name AS created_by_name
        FROM t_meeting_memo m
        LEFT JOIN t_user u ON u.usr_id = m.mmm_created_by
        LEFT JOIN (
            SELECT ntf_action_id, MAX(ntf_created_at) AS last_notified_at
            FROM t_notification
            WHERE ntf_event_type LIKE 'meeting_memo:%'
              AND ntf_action_id IS NOT NULL
            GROUP BY ntf_action_id
        ) n ON n.ntf_action_id = m.mmm_id
        WHERE m.mmm_id = ?
        """,
        (mmm_id,),
    ).fetchone()
    return dict(row)
