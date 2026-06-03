"""Action feedback service — pre-meeting participant progress updates."""
from __future__ import annotations

from actionhub.middleware.db import get_db

VALID_STATUSES = ("not_started", "on_track", "late", "done", "cancelled")
STATUS_LABELS = {
    "not_started": "Not started",
    "on_track":    "On-track",
    "late":        "Late",
    "done":        "Done",
    "cancelled":   "Cancelled",
}

FEEDBACK_TO_ACTION_STATUS = {
    "not_started": "Open",
    "on_track": "In Progress",
    "late": "On Hold",
    "done": "Done",
    "cancelled": "Cancelled",
}


def _ensure_action_feedback_table() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS t_action_feedback (
            afb_id              INTEGER PRIMARY KEY AUTOINCREMENT,
            afb_action_id       INTEGER NOT NULL,
            afb_meeting_inst_id INTEGER,
            afb_user_id         INTEGER NOT NULL,
            afb_completion_pct  INTEGER CHECK (afb_completion_pct BETWEEN 0 AND 100),
            afb_status          TEXT CHECK (afb_status IN ('not_started','on_track','late','done','cancelled')),
            afb_comment         TEXT,
            afb_est_date        TEXT,
            afb_blockers        TEXT,
            afb_created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (afb_action_id) REFERENCES t_action(act_id) ON DELETE CASCADE,
            FOREIGN KEY (afb_user_id) REFERENCES t_user(usr_id),
            FOREIGN KEY (afb_meeting_inst_id) REFERENCES t_meeting_instance(min_id)
        );

        CREATE INDEX IF NOT EXISTS idx_afb_action ON t_action_feedback (afb_action_id);
        CREATE INDEX IF NOT EXISTS idx_afb_user ON t_action_feedback (afb_user_id);
        CREATE INDEX IF NOT EXISTS idx_afb_meeting ON t_action_feedback (afb_meeting_inst_id);
        """
    )
    db.commit()


def submit_feedback(
    action_id: int,
    user_id: int,
    meeting_inst_id: int | None,
    completion_pct: int | None,
    status: str | None,
    comment: str | None,
    est_date: str | None,
    blockers: str | None,
) -> dict:
    """Insert a new feedback entry. Each call creates a new immutable row (full history)."""
    _ensure_action_feedback_table()
    if status and status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}")
    if completion_pct is not None and not (0 <= int(completion_pct) <= 100):
        raise ValueError("completion_pct must be between 0 and 100")
    db = get_db()
    if blockers is None:
        latest = db.execute(
            """
            SELECT afb_blockers
            FROM t_action_feedback
            WHERE afb_action_id = ?
            ORDER BY afb_created_at DESC, afb_id DESC
            LIMIT 1
            """,
            (action_id,),
        ).fetchone()
        if latest and latest["afb_blockers"]:
            blockers = str(latest["afb_blockers"])
    row = db.execute("SELECT act_id FROM t_action WHERE act_id = ?", (action_id,)).fetchone()
    if not row:
        raise ValueError("action not found")
    cur = db.execute(
        """
        INSERT INTO t_action_feedback
            (afb_action_id, afb_meeting_inst_id, afb_user_id,
             afb_completion_pct, afb_status, afb_comment, afb_est_date, afb_blockers)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (action_id, meeting_inst_id, user_id, completion_pct, status, comment, est_date, blockers),
    )

    # Latest follow-up status overrides the action status.
    latest_status_row = db.execute(
        """
        SELECT afb_status
        FROM t_action_feedback
        WHERE afb_action_id = ?
          AND afb_status IS NOT NULL
        ORDER BY afb_created_at DESC, afb_id DESC
        LIMIT 1
        """,
        (action_id,),
    ).fetchone()
    if latest_status_row and latest_status_row["afb_status"]:
        synced_status = FEEDBACK_TO_ACTION_STATUS.get(str(latest_status_row["afb_status"]))
        if synced_status:
            db.execute(
                """
                UPDATE t_action
                SET act_status = ?,
                    act_updated_at = CURRENT_TIMESTAMP
                WHERE act_id = ?
                """,
                (synced_status, action_id),
            )

    db.commit()
    return _get_entry(cur.lastrowid)


def list_action_feedback(action_id: int) -> list[dict]:
    """All feedback entries for one action, newest first."""
    _ensure_action_feedback_table()
    db = get_db()
    rows = db.execute(
        """
        SELECT f.afb_id, f.afb_action_id, f.afb_meeting_inst_id,
               f.afb_user_id, u.usr_display_name,
               f.afb_completion_pct, f.afb_status, f.afb_comment,
               f.afb_est_date, f.afb_blockers, f.afb_created_at,
               mi.min_title AS meeting_title,
               mi.min_date  AS meeting_date
        FROM   t_action_feedback f
        JOIN   t_user u ON u.usr_id = f.afb_user_id
        LEFT JOIN t_meeting_instance mi ON mi.min_id = f.afb_meeting_inst_id
        WHERE  f.afb_action_id = ?
        ORDER  BY f.afb_created_at DESC, f.afb_id DESC
        """,
        (action_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_meeting_feedback_summary(meeting_inst_id: int) -> list[dict]:
    """
    Return the *latest* feedback entry per (action, user) for every action
    linked to the given meeting instance.

    Result rows: act_id, act_ref, act_title, act_status,
                 afb_user_id, usr_display_name,
                 afb_completion_pct, afb_status, afb_comment,
                 afb_est_date, afb_blockers, afb_created_at
    Only actions that have at least one feedback entry are included.
    """
    _ensure_action_feedback_table()
    db = get_db()
    rows = db.execute(
        """
        SELECT
            a.act_id, a.act_ref, a.act_title, a.act_status AS action_status,
            f.afb_id, f.afb_user_id, u.usr_display_name,
            f.afb_completion_pct, f.afb_status, f.afb_comment,
            f.afb_est_date, f.afb_blockers, f.afb_created_at
        FROM   t_action a
        JOIN   t_action_feedback f ON f.afb_action_id = a.act_id
        JOIN   t_user u ON u.usr_id = f.afb_user_id
        WHERE  a.act_meeting_inst_id = ?
          AND  a.act_archived = 0
          AND  f.afb_id = (
              SELECT afb_id
              FROM   t_action_feedback f2
              WHERE  f2.afb_action_id = f.afb_action_id
                AND  f2.afb_user_id   = f.afb_user_id
              ORDER  BY f2.afb_created_at DESC
              LIMIT  1
          )
        ORDER  BY a.act_id, u.usr_display_name
        """,
        (meeting_inst_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_entry(afb_id: int) -> dict:
    _ensure_action_feedback_table()
    db = get_db()
    row = db.execute(
        """
        SELECT f.afb_id, f.afb_action_id, f.afb_meeting_inst_id,
               f.afb_user_id, u.usr_display_name,
               f.afb_completion_pct, f.afb_status, f.afb_comment,
               f.afb_est_date, f.afb_blockers, f.afb_created_at
        FROM   t_action_feedback f
        JOIN   t_user u ON u.usr_id = f.afb_user_id
        WHERE  f.afb_id = ?
        """,
        (afb_id,),
    ).fetchone()
    return dict(row) if row else {}
