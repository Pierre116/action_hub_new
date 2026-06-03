"""Notification service — create and query in-app notifications."""
from __future__ import annotations

from actionhub.middleware.db import get_db


def create_notification(user_id: int, event_type: str, title: str,
                         body: str | None = None, action_id: int | None = None) -> None:
    db = get_db()
    db.execute(
        """
        INSERT INTO t_notification (ntf_user_id, ntf_event_type, ntf_title, ntf_body, ntf_action_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, event_type, title, body, action_id),
    )
    db.commit()


def get_notifications(user_id: int, unread_only: bool = False, limit: int = 20) -> list[dict]:
    db = get_db()
    sql = """
        SELECT ntf_id, ntf_event_type, ntf_title, ntf_body,
               ntf_action_id, ntf_is_read, ntf_created_at
        FROM t_notification
        WHERE ntf_user_id = ?
    """
    params: list = [user_id]
    if unread_only:
        sql += " AND ntf_is_read = 0"
    sql += f" ORDER BY ntf_created_at DESC LIMIT {int(limit)}"
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_unread_count(user_id: int) -> int:
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) AS n FROM t_notification WHERE ntf_user_id = ? AND ntf_is_read = 0",
        (user_id,),
    ).fetchone()
    return int(row["n"])


def mark_read(user_id: int, ntf_id: int | None = None) -> None:
    """Mark one or all notifications read for the user."""
    db = get_db()
    if ntf_id:
        db.execute(
            "UPDATE t_notification SET ntf_is_read = 1 WHERE ntf_id = ? AND ntf_user_id = ?",
            (ntf_id, user_id),
        )
    else:
        db.execute(
            "UPDATE t_notification SET ntf_is_read = 1 WHERE ntf_user_id = ?",
            (user_id,),
        )
    db.commit()


def delete_notifications(user_id: int, ntf_id: int | None = None) -> int:
    """Delete one or all notifications for the user. Returns affected row count."""
    db = get_db()
    if ntf_id:
        cur = db.execute(
            "DELETE FROM t_notification WHERE ntf_id = ? AND ntf_user_id = ?",
            (ntf_id, user_id),
        )
    else:
        cur = db.execute(
            "DELETE FROM t_notification WHERE ntf_user_id = ?",
            (user_id,),
        )
    db.commit()
    return int(cur.rowcount or 0)


def notify_assignment(action_id: int, action_title: str, actor_name: str,
                       assignee_user_id: int) -> None:
    create_notification(
        user_id=assignee_user_id,
        event_type="assigned",
        title=f"You were assigned to: {action_title}",
        body=f"Assigned by {actor_name}",
        action_id=action_id,
    )


def generate_deadline_notifications() -> int:
    """
    Called periodically (or on each request cheaply).
    Creates 'deadline_soon' notifications for actions due within 3 days.
    Avoids duplicates: only once per action per user per day.
    Returns count of notifications created.
    """
    from datetime import date, timedelta

    db = get_db()
    cutoff = (date.today() + timedelta(days=3)).isoformat()
    today = date.today().isoformat()

    # Find actions due in ≤3 days, not done/cancelled
    actions = db.execute(
        """
        SELECT a.act_id, a.act_title, a.act_deadline, a.act_owner_id,
               ag.asg_user_id AS lead_user_id
        FROM t_action a
        LEFT JOIN t_assignment ag
                        ON ag.asg_action_id = a.act_id AND INSTR(',' || ag.asg_role || ',', ',Lead,') > 0
        WHERE a.act_deadline <= ? AND a.act_deadline >= ?
          AND a.act_status NOT IN ('Done','Cancelled')
        """,
        (cutoff, today),
    ).fetchall()

    created = 0
    for row in actions:
        for uid in {row["act_owner_id"], row["lead_user_id"]}:
            if not uid:
                continue
            # Skip if already notified today
            exists = db.execute(
                """
                SELECT 1 FROM t_notification
                WHERE ntf_user_id = ? AND ntf_action_id = ? AND ntf_event_type = 'deadline_soon'
                  AND date(ntf_created_at) = date('now')
                """,
                (uid, row["act_id"]),
            ).fetchone()
            if not exists:
                db.execute(
                    """
                    INSERT INTO t_notification
                        (ntf_user_id, ntf_event_type, ntf_title, ntf_body, ntf_action_id)
                    VALUES (?, 'deadline_soon', ?, ?, ?)
                    """,
                    (uid,
                     f"Due soon: {row['act_title']}",
                     f"Deadline: {row['act_deadline']}",
                     row["act_id"]),
                )
                created += 1
    if created:
        db.commit()
    return created
