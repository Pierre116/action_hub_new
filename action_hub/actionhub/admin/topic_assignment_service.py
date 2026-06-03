from __future__ import annotations

from actionhub.middleware.db import get_db


def _ensure_topic_assignment_table(db) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS t_topic_assignment (
            tpa_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tpa_topic_id    INTEGER NOT NULL REFERENCES t_topic(top_id),
            tpa_user_id     INTEGER NOT NULL REFERENCES t_user(usr_id),
            tpa_assigned_by INTEGER NOT NULL REFERENCES t_user(usr_id),
            tpa_assigned_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tpa_topic_id, tpa_user_id)
        )
        """
    )


def _topic_row(db, topic_id: int):
    return db.execute(
        "SELECT top_id, top_name FROM t_topic WHERE top_id = ?",
        (topic_id,),
    ).fetchone()


def _user_row(db, user_id: int):
    return db.execute(
        "SELECT usr_id, usr_display_name, usr_role FROM t_user WHERE usr_id = ?",
        (user_id,),
    ).fetchone()


def get_topic_leaders(topic_id: int) -> list[dict]:
    db = get_db()
    _ensure_topic_assignment_table(db)
    rows = db.execute(
        """
        SELECT
            tpa.tpa_id,
            tpa.tpa_topic_id,
            tpa.tpa_user_id,
            tpa.tpa_assigned_by,
            tpa.tpa_assigned_at,
            u.usr_display_name,
            u.usr_role,
            a.usr_display_name AS assigned_by_name
        FROM t_topic_assignment tpa
        JOIN t_user u ON u.usr_id = tpa.tpa_user_id
        LEFT JOIN t_user a ON a.usr_id = tpa.tpa_assigned_by
        WHERE tpa.tpa_topic_id = ?
        ORDER BY u.usr_display_name
        """,
        (topic_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def assign_topic_leader(topic_id: int, user_id: int, assigned_by: int) -> dict:
    db = get_db()
    _ensure_topic_assignment_table(db)

    if not _topic_row(db, topic_id):
        raise ValueError("topic not found")
    if not _user_row(db, user_id):
        raise ValueError("user not found")
    if not _user_row(db, assigned_by):
        raise ValueError("assigned_by user not found")

    cursor = db.execute(
        """
        INSERT OR IGNORE INTO t_topic_assignment (tpa_topic_id, tpa_user_id, tpa_assigned_by)
        VALUES (?, ?, ?)
        """,
        (topic_id, user_id, assigned_by),
    )
    db.commit()

    row = db.execute(
        """
        SELECT
            tpa.tpa_id,
            tpa.tpa_topic_id,
            tpa.tpa_user_id,
            tpa.tpa_assigned_by,
            tpa.tpa_assigned_at,
            u.usr_display_name,
            u.usr_role,
            a.usr_display_name AS assigned_by_name
        FROM t_topic_assignment tpa
        JOIN t_user u ON u.usr_id = tpa.tpa_user_id
        LEFT JOIN t_user a ON a.usr_id = tpa.tpa_assigned_by
        WHERE tpa.tpa_topic_id = ? AND tpa.tpa_user_id = ?
        LIMIT 1
        """,
        (topic_id, user_id),
    ).fetchone()
    if not row:
        raise ValueError("failed to assign topic leader")
    result = dict(row)
    result["created"] = bool(cursor.rowcount)
    return result


def remove_topic_leader(topic_id: int, user_id: int) -> dict:
    db = get_db()
    _ensure_topic_assignment_table(db)
    db.execute(
        "DELETE FROM t_topic_assignment WHERE tpa_topic_id = ? AND tpa_user_id = ?",
        (topic_id, user_id),
    )
    db.commit()
    return {"removed": True, "topic_id": topic_id, "user_id": user_id}