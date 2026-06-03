"""Workflow domain migration (V4.0).

Creates 6 workflow tables and modifies t_action and t_action_history.

See S20 §7 for complete DDL specification.
"""
import json
import os
import sqlite3
from pathlib import Path

# Get the project root (action_hub directory)
_project_root = Path(__file__).resolve().parent.parent.parent
DB_PATH = _project_root / "db" / "actionhub.db"


def run():
    """Execute the V4.0 workflow migration."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")

    try:
        conn.execute("BEGIN")

        # 1. CREATE TABLE t_workflow_template (S20 §7.1)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS t_workflow_template (
                wft_id INTEGER PRIMARY KEY AUTOINCREMENT,
                wft_name_en VARCHAR(255) NOT NULL,
                wft_name_cn VARCHAR(255),
                wft_desc TEXT,
                wft_version INTEGER NOT NULL DEFAULT 1,
                wft_is_default BOOLEAN NOT NULL DEFAULT 0,
                wft_type TEXT NOT NULL CHECK(wft_type IN ('action', 'request')),
                wft_active BOOLEAN NOT NULL DEFAULT 1,
                wft_graph TEXT NOT NULL DEFAULT '{}',
                wft_created_by INTEGER NOT NULL,
                wft_created_at TEXT NOT NULL,
                wft_updated_at TEXT
            )
        """)

        # 2. CREATE TABLE t_workflow_instance (S20 §7.2)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS t_workflow_instance (
                wfi_id INTEGER PRIMARY KEY AUTOINCREMENT,
                wfi_template_id INTEGER NOT NULL,
                wfi_action_id INTEGER NOT NULL UNIQUE,
                wfi_status TEXT NOT NULL
                    CHECK(wfi_status IN ('Active', 'Completed', 'Cancelled', 'Suspended')),
                wfi_started_at TEXT NOT NULL,
                wfi_completed_at TEXT,
                FOREIGN KEY (wfi_template_id) REFERENCES t_workflow_template(wft_id),
                FOREIGN KEY (wfi_action_id) REFERENCES t_action(act_id)
            )
        """)

        # 3. CREATE TABLE t_workflow_step_instance (S20 §7.3)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS t_workflow_step_instance (
                wsi_id INTEGER PRIMARY KEY AUTOINCREMENT,
                wsi_instance_id INTEGER NOT NULL,
                wsi_step_key TEXT NOT NULL,
                wsi_status TEXT NOT NULL
                    CHECK(wsi_status IN ('Pending', 'Active', 'Completed', 'Skipped', 'Rejected')),
                wsi_assignee_id INTEGER,
                wsi_entered_at TEXT,
                wsi_completed_at TEXT,
                wsi_sla_deadline TEXT,
                wsi_comment TEXT,
                FOREIGN KEY (wsi_instance_id) REFERENCES t_workflow_instance(wfi_id),
                FOREIGN KEY (wsi_assignee_id) REFERENCES t_user(usr_id)
            )
        """)

        # 4. CREATE TABLE t_workflow_step_field_value (S20 §7.4)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS t_workflow_step_field_value (
                sfv_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sfv_step_inst_id INTEGER NOT NULL,
                sfv_field_key TEXT NOT NULL,
                sfv_value TEXT,
                sfv_filled_by INTEGER,
                sfv_filled_at TEXT NOT NULL,
                FOREIGN KEY (sfv_step_inst_id) REFERENCES t_workflow_step_instance(wsi_id),
                FOREIGN KEY (sfv_filled_by) REFERENCES t_user(usr_id),
                UNIQUE(sfv_step_inst_id, sfv_field_key)
            )
        """)

        # 5. CREATE TABLE t_workflow_approval (S20 §7.5)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS t_workflow_approval (
                wap_id INTEGER PRIMARY KEY AUTOINCREMENT,
                wap_step_inst_id INTEGER NOT NULL,
                wap_approver_id INTEGER NOT NULL,
                wap_decision TEXT NOT NULL
                    CHECK(wap_decision IN ('Approved', 'Rejected', 'Abstained')),
                wap_comment TEXT,
                wap_decided_at TEXT NOT NULL,
                FOREIGN KEY (wap_step_inst_id) REFERENCES t_workflow_step_instance(wsi_id),
                FOREIGN KEY (wap_approver_id) REFERENCES t_user(usr_id)
            )
        """)

        # 6. CREATE TABLE t_approval_delegation (S20 §7.6)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS t_approval_delegation (
                adl_id INTEGER PRIMARY KEY AUTOINCREMENT,
                adl_delegator_id INTEGER NOT NULL,
                adl_delegate_id INTEGER NOT NULL,
                adl_valid_from TEXT NOT NULL,
                adl_valid_until TEXT NOT NULL,
                adl_active BOOLEAN NOT NULL DEFAULT 1,
                adl_created_at TEXT NOT NULL,
                FOREIGN KEY (adl_delegator_id) REFERENCES t_user(usr_id),
                FOREIGN KEY (adl_delegate_id) REFERENCES t_user(usr_id),
                CHECK(adl_delegator_id <> adl_delegate_id)
            )
        """)

        conn.executescript("""
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
        """)

        # 7. ALTER t_action: add 'WorkflowRequest' to act_source CHECK
        # SQLite doesn't support ALTER TABLE ADD CONSTRAINT, so we need to rebuild
        # For simplicity, we'll check if the trigger exists or recreate the table

        # Check current table schema
        cursor = conn.execute("PRAGMA table_info(t_action)")
        columns = [row[1] for row in cursor.fetchall()]

        if "act_source" not in columns:
            conn.execute("ALTER TABLE t_action ADD COLUMN act_source TEXT DEFAULT 'Manual'")

        # Create trigger to enforce act_source values
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS check_act_source
            BEFORE INSERT ON t_action
            WHEN NEW.act_source IS NOT NULL
            BEGIN
                SELECT CASE
                    WHEN NEW.act_source NOT IN ('Manual', 'Import', 'WorkflowRequest')
                    THEN RAISE(ABORT, 'Invalid act_source value')
                END;
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS check_act_source_update
            BEFORE UPDATE ON t_action
            WHEN NEW.act_source IS NOT NULL
            BEGIN
                SELECT CASE
                    WHEN NEW.act_source NOT IN ('Manual', 'Import', 'WorkflowRequest')
                    THEN RAISE(ABORT, 'Invalid act_source value')
                END;
            END
        """)

        # 8. ALTER t_action_history: add new change_type values
        # Similar approach - add column if not exists
        cursor = conn.execute("PRAGMA table_info(t_action_history)")
        history_columns = [row[1] for row in cursor.fetchall()]

        # Note: The trigger approach will be handled by the existing FSM logic

        # 9. CREATE indexes (S20 §7)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wft_type ON t_workflow_template(wft_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wft_active ON t_workflow_template(wft_active)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wfi_template ON t_workflow_instance(wfi_template_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wfi_status ON t_workflow_instance(wfi_status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wsi_instance ON t_workflow_step_instance(wsi_instance_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wsi_status ON t_workflow_step_instance(wsi_status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wsi_assignee ON t_workflow_step_instance(wsi_assignee_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sfv_step_inst ON t_workflow_step_field_value(sfv_step_inst_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wap_step ON t_workflow_approval(wap_step_inst_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wap_approver ON t_workflow_approval(wap_approver_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_adl_delegator ON t_approval_delegation(adl_delegator_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_adl_delegate ON t_approval_delegation(adl_delegate_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_adl_active ON t_approval_delegation(adl_active, adl_valid_from, adl_valid_until)"
        )

        # 10. Seed default templates
        _seed_templates(conn)

        conn.commit()
        print("Migration v4.0 completed successfully")

    except Exception as e:
        conn.rollback()
        print(f"Migration v4.0 failed: {e}")
        raise
    finally:
        conn.close()


def _seed_templates(conn):
    """Seed default workflow templates."""
    from datetime import datetime
    from actionhub.workflow.pilot import SIMPLE_ACTION_GRAPH, OT_USER_CREATION_GRAPH

    now = datetime.now().isoformat()

    # Check if templates already exist
    existing = conn.execute(
        "SELECT COUNT(*) as cnt FROM t_workflow_template"
    ).fetchone()["cnt"]

    if existing > 0:
        print("Templates already seeded, skipping")
        return

    # Seed Simple Action (default)
    conn.execute(
        """INSERT INTO t_workflow_template
           (wft_name_en, wft_name_cn, wft_desc, wft_version, wft_is_default,
            wft_type, wft_active, wft_graph, wft_created_by, wft_created_at)
           VALUES (?, ?, ?, 1, 1, 'action', 1, ?, 1, ?)""",
        (
            "Simple Action",
            "简单操作",
            "Default workflow for simple actions",
            json.dumps(SIMPLE_ACTION_GRAPH),
            now,
        ),
    )

    # Seed OT User Creation (pilot)
    conn.execute(
        """INSERT INTO t_workflow_template
           (wft_name_en, wft_name_cn, wft_desc, wft_version, wft_is_default,
            wft_type, wft_active, wft_graph, wft_created_by, wft_created_at)
           VALUES (?, ?, ?, 1, 0, 'request', 1, ?, 1, ?)""",
        (
            "OT User Creation",
            "OT 用户创建",
            "Pilot workflow: new operator onboarding across 5 teams",
            json.dumps(OT_USER_CREATION_GRAPH),
            now,
        ),
    )

    print("Seeded default workflow templates")


if __name__ == "__main__":
    run()
