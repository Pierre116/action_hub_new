"""Migration: align feedback statuses with business display statuses.

Replaces old at_risk/blocked values with the new aligned statuses,
then recreates the table with the updated CHECK constraint.
"""
from __future__ import annotations

import sqlite3

VERSION = 1
DESCRIPTION = "Align feedback statuses: remove at_risk/blocked, add not_started/late/cancelled"


def up(db: sqlite3.Connection) -> None:
    # Check if the table exists
    exists = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='t_action_feedback'"
    ).fetchone()
    if not exists:
        return  # Table will be created with new constraint by init_app

    # Check if the old constraint is present (skip if already migrated or fresh DB)
    ddl_row = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='t_action_feedback'"
    ).fetchone()
    ddl = str(ddl_row[0]) if ddl_row else ""
    if "at_risk" not in ddl and "blocked" not in ddl:
        return  # Already has new constraint or no old values — nothing to do

    # Also ensure referenced tables exist (skip during fresh DB init where
    # init_app() runs before init_db() creates the core schema).
    ref_tables = {"t_action", "t_user", "t_meeting_instance"}
    existing_tables = {
        row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if not ref_tables.issubset(existing_tables):
        return  # Core tables not yet created; migration unnecessary for fresh DBs

    # SQLite cannot ALTER CHECK constraints, so recreate the table first
    # with the new constraint, mapping old statuses during the INSERT.
    db.execute("PRAGMA foreign_keys = OFF")
    db.execute(
        """
        CREATE TABLE t_action_feedback_new (
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
        )
        """
    )
    # Copy data, mapping old status values to new ones in the same step
    db.execute(
        """
        INSERT INTO t_action_feedback_new
            (afb_id, afb_action_id, afb_meeting_inst_id, afb_user_id,
             afb_completion_pct, afb_status, afb_comment, afb_est_date,
             afb_blockers, afb_created_at)
        SELECT afb_id, afb_action_id, afb_meeting_inst_id, afb_user_id,
               afb_completion_pct,
               CASE afb_status
                   WHEN 'at_risk' THEN 'late'
                   WHEN 'blocked' THEN 'late'
                   ELSE afb_status
               END,
               afb_comment, afb_est_date,
               afb_blockers, afb_created_at
        FROM t_action_feedback
        """
    )
    db.execute("DROP TABLE t_action_feedback")
    db.execute("ALTER TABLE t_action_feedback_new RENAME TO t_action_feedback")

    # Recreate indexes
    db.execute("CREATE INDEX IF NOT EXISTS idx_afb_action ON t_action_feedback(afb_action_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_afb_user ON t_action_feedback(afb_user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_afb_meeting ON t_action_feedback(afb_meeting_inst_id)")

    db.execute("PRAGMA foreign_keys = ON")
    db.commit()
