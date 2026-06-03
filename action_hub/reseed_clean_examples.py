from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import os
from pathlib import Path
import sys

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CONFIG_MAP
from actionhub.middleware.db import get_db
from actionhub.middleware.db import init_db as ensure_schema
from actionhub.utils.ref_generator import generate_action_ref
from actionhub.workflow.service import create_template, has_workflow_runtime_tables, has_workflow_template_table


PRESERVED_TABLES = {
    "t_user",
    "t_team",
    "t_category",
    "t_user_team",
}

SKIPPED_TABLE_PREFIXES = (
    "sqlite_",
    "t_meeting_decision_fts",
)

CLEAR_TABLE_ORDER = [
    "t_workflow_service_log",
    "t_workflow_approval",
    "t_workflow_step_field_value",
    "t_workflow_step_instance",
    "t_workflow_instance",
    "t_workflow_assignment_counter",
    "t_approval_delegation",
    "t_assignment_history",
    "t_action_tag",
    "t_assignment",
    "t_action_history",
    "t_comment",
    "t_notification",
    "t_import_log",
    "t_meeting_decision",
    "t_meeting_participant",
    "t_meeting_owner",
    "t_meeting_memo",
    "t_meeting_summary",
    "t_meeting_series_participant",
    "t_feedback",
    "t_evolution",
    "t_action",
    "t_meeting_instance",
    "t_meeting",
    "t_topic_assignment",
    "t_tag",
    "t_topic",
    "t_user_dept",
    "t_department",
    "t_workflow_template",
]


@dataclass(frozen=True)
class DemoAction:
    title: str
    description: str
    status: str
    priority: str
    deadline_offset_days: int
    progress_pct: int
    visibility: str = "public"


DEMO_TOPICS = [
    ("Operational Stability", "Examples that keep day-to-day delivery predictable."),
    ("Digital Enablement", "Examples for automation and internal tooling."),
    ("Quality Discipline", "Examples covering audit and corrective action work."),
    ("People Enablement", "Examples for onboarding, training, and adoption."),
]

DEMO_ACTIONS = [
    DemoAction(
        title="Stabilize monthly action review cadence",
        description="Create a consistent review agenda, track blockers, and publish decisions within one business day.",
        status="In Progress",
        priority="High",
        deadline_offset_days=10,
        progress_pct=45,
    ),
    DemoAction(
        title="Prepare vendor onboarding checklist refresh",
        description="Refresh mandatory fields, simplify approvals, and align the form with the current workflow templates.",
        status="Open",
        priority="Medium",
        deadline_offset_days=21,
        progress_pct=0,
    ),
    DemoAction(
        title="Close audit finding for packaging traceability",
        description="Resolve the open traceability gap and attach evidence for the next quality review meeting.",
        status="On Hold",
        priority="Critical",
        deadline_offset_days=5,
        progress_pct=60,
        visibility="private",
    ),
    DemoAction(
        title="Launch training pack for new team leads",
        description="Bundle dashboard walkthroughs, escalation rules, and meeting follow-up standards into one starter pack.",
        status="Done",
        priority="Medium",
        deadline_offset_days=-2,
        progress_pct=100,
    ),
    DemoAction(
        title="Retire duplicate status export workbook",
        description="Remove the duplicate export path and replace it with a single supported dashboard extract.",
        status="Cancelled",
        priority="Low",
        deadline_offset_days=14,
        progress_pct=20,
    ),
]


def _create_db_app() -> Flask:
    env_name = os.environ.get("ACTIONHUB_ENV", "development")
    app = Flask(
        "reseed_clean_examples",
        root_path=str(Path(__file__).resolve().parent / "actionhub"),
    )
    app.config.from_object(CONFIG_MAP.get(env_name, CONFIG_MAP["development"]))
    if os.environ.get("DATABASE"):
        app.config["DATABASE"] = os.environ["DATABASE"]
    return app


def _table_names(db) -> list[str]:
    rows = db.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()
    return [str(row["name"]) for row in rows]


def _has_table(db, table_name: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table_name,),
    ).fetchone()
    return bool(row)


def _table_columns(db, table_name: str) -> set[str]:
    rows = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}


def _pick_assignment_status(db) -> str:
    row = db.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 't_assignment'"
    ).fetchone()
    ddl = str(row["sql"]) if row and row["sql"] else ""
    if "'Assigned'" in ddl:
        return "Assigned"
    if "'Accepted'" in ddl:
        return "Accepted"
    if "'Pending'" in ddl:
        return "Pending"
    return "Assigned"


def _tables_to_clear(db) -> list[str]:
    existing = set(_table_names(db))
    clearable = [table_name for table_name in CLEAR_TABLE_ORDER if table_name in existing]
    extra_tables = sorted(
        table_name
        for table_name in existing
        if table_name not in PRESERVED_TABLES
        and table_name not in clearable
        and not table_name.startswith(SKIPPED_TABLE_PREFIXES)
    )
    return clearable + extra_tables


def _reset_sequences(db, table_names: list[str]) -> None:
    existing = {
        str(row["name"])
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_sequence'"
        ).fetchall()
    }
    if "sqlite_sequence" not in existing or not table_names:
        return
    placeholders = ",".join("?" for _ in table_names)
    db.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})", table_names)


def _clear_meeting_decisions(db) -> None:
    db.execute("DROP TRIGGER IF EXISTS t_meeting_decision_ai")
    db.execute("DROP TRIGGER IF EXISTS t_meeting_decision_ad")
    db.execute("DROP TRIGGER IF EXISTS t_meeting_decision_au")
    db.execute("DROP TRIGGER IF EXISTS trg_meeting_decision_fts")
    db.execute("DROP TRIGGER IF EXISTS trg_meeting_decision_fts_update")
    db.execute("DROP TRIGGER IF EXISTS trg_meeting_decision_fts_delete")
    db.execute("DROP TABLE IF EXISTS t_meeting_decision_fts")
    db.execute("DELETE FROM t_meeting_decision")


def _ensure_workflow_tables(db) -> None:
    db.execute(
        """
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
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_wft_type ON t_workflow_template(wft_type)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_wft_active ON t_workflow_template(wft_active)")
    db.execute(
        """
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
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS t_workflow_approval (
            wap_id INTEGER PRIMARY KEY AUTOINCREMENT,
            wap_step_inst_id INTEGER NOT NULL,
            wap_approver_id INTEGER NOT NULL,
            wap_decision TEXT NOT NULL CHECK(wap_decision IN ('Approved', 'Rejected', 'Abstained')),
            wap_comment TEXT,
            wap_decided_at TEXT NOT NULL,
            FOREIGN KEY (wap_step_inst_id) REFERENCES t_workflow_step_instance(wsi_id),
            FOREIGN KEY (wap_approver_id) REFERENCES t_user(usr_id)
        )
        """
    )
    db.execute(
        """
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
        """
    )


def _clear_mutable_data(db, dry_run: bool) -> list[str]:
    table_names = _tables_to_clear(db)
    if dry_run:
        return table_names

    db.execute("PRAGMA foreign_keys = OFF")
    try:
        for table_name in table_names:
            try:
                if table_name == "t_meeting_decision":
                    _clear_meeting_decisions(db)
                else:
                    db.execute(f"DELETE FROM {table_name}")
            except Exception as exc:
                raise RuntimeError(f"Failed clearing table {table_name}: {exc}") from exc
        _reset_sequences(db, table_names)
        db.commit()
    finally:
        db.execute("PRAGMA foreign_keys = ON")
    return table_names


def _pick_users(db) -> tuple[int, list[int]]:
    rows = db.execute(
        """
        SELECT usr_id, usr_role
        FROM t_user
        WHERE COALESCE(usr_active, 1) = 1
        ORDER BY CASE WHEN usr_role = 'Admin' THEN 0 ELSE 1 END, usr_id
        """
    ).fetchall()
    if not rows:
        raise RuntimeError("No active users found. Reseed requires preserved users.")

    creator_id = int(rows[0]["usr_id"])
    participant_ids = [int(row["usr_id"]) for row in rows[:4]]
    if creator_id not in participant_ids:
        participant_ids.insert(0, creator_id)
    return creator_id, participant_ids


def _pick_teams(db) -> list[int | None]:
    rows = db.execute(
        "SELECT tea_id FROM t_team WHERE COALESCE(tea_active, 1) = 1 ORDER BY tea_sort_order, tea_id"
    ).fetchall()
    if not rows:
        return [None]
    return [int(row["tea_id"]) for row in rows]


def _pick_categories(db) -> list[int | None]:
    rows = db.execute(
        "SELECT cat_id FROM t_category WHERE COALESCE(cat_active, 1) = 1 ORDER BY cat_sort, cat_id"
    ).fetchall()
    if not rows:
        return [None]
    return [int(row["cat_id"]) for row in rows]


def _insert_topics(db, creator_id: int) -> list[int]:
    topic_ids: list[int] = []
    for index, (name, description) in enumerate(DEMO_TOPICS, start=1):
        cursor = db.execute(
            """
            INSERT INTO t_topic (top_code, top_name, top_desc, top_active, top_is_global, top_sort, top_created_by)
            VALUES (?, ?, ?, 1, 1, ?, ?)
            """,
            (f"D{index:02d}", name, description, index, creator_id),
        )
        topic_ids.append(int(cursor.lastrowid))
    return topic_ids


def _insert_actions(db, creator_id: int, participant_ids: list[int], topic_ids: list[int]) -> list[int]:
    team_ids = _pick_teams(db)
    category_ids = _pick_categories(db)
    assignment_status = _pick_assignment_status(db)
    action_columns = {row[1] for row in db.execute("PRAGMA table_info(t_action)").fetchall()}
    if "act_tags" not in action_columns:
        db.execute("ALTER TABLE t_action ADD COLUMN act_tags TEXT")
    action_ids: list[int] = []
    today = date.today()

    for index, demo_action in enumerate(DEMO_ACTIONS):
        team_id = team_ids[index % len(team_ids)]
        category_id = category_ids[index % len(category_ids)]
        topic_id = topic_ids[index % len(topic_ids)] if topic_ids else None
        owner_id = participant_ids[index % len(participant_ids)]
        deadline = (today + timedelta(days=demo_action.deadline_offset_days)).isoformat()
        actual_date = today.isoformat() if demo_action.status == "Done" else None

        cursor = db.execute(
            """
            INSERT INTO t_action (
                act_ref,
                act_title,
                act_desc,
                act_tags,
                act_topic_id,
                act_category_id,
                act_team_id,
                act_priority,
                act_owner_id,
                act_status,
                act_deadline,
                act_actual_date,
                act_source,
                act_visibility,
                act_hold_reason,
                act_cancel_reason,
                act_completion_pct,
                act_created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Manual', ?, ?, ?, ?, ?)
            """,
            (
                generate_action_ref(),
                demo_action.title,
                demo_action.description,
                getattr(demo_action, "tags", None),
                topic_id,
                category_id,
                team_id,
                demo_action.priority,
                owner_id,
                demo_action.status,
                deadline,
                actual_date,
                demo_action.visibility,
                "Awaiting final confirmation from the owning function" if demo_action.status == "On Hold" else None,
                "Example cancellation after scope was consolidated elsewhere" if demo_action.status == "Cancelled" else None,
                demo_action.progress_pct,
                creator_id,
            ),
        )
        action_id = int(cursor.lastrowid)
        action_ids.append(action_id)

        db.execute(
            """
            INSERT INTO t_assignment (asg_action_id, asg_user_id, asg_role, asg_status, asg_assigned_by)
            VALUES (?, ?, 'Lead', ?, ?)
            """,
            (action_id, owner_id, assignment_status, creator_id),
        )
        db.execute(
            """
            INSERT INTO t_action_history (ahi_action_id, ahi_change_type, ahi_field, ahi_new_value, ahi_changed_by)
            VALUES (?, 'Created', 'act_status', ?, ?)
            """,
            (action_id, demo_action.status, creator_id),
        )
        db.execute(
            """
            INSERT INTO t_comment (cmt_act_id, cmt_type, cmt_body, cmt_created_by)
            VALUES (?, 'Comment', ?, ?)
            """,
            (
                action_id,
                "Example note: this record is part of the clean reseed baseline.",
                owner_id,
            ),
        )
    return action_ids


def _insert_tags(db, creator_id: int, action_ids: list[int]) -> None:
    if not action_ids:
        return
    tag_ids: list[int] = []
    for tag_name in ("baseline", "review", "demo"):
        cursor = db.execute(
            "INSERT INTO t_tag (tag_name, tag_created_by, tag_usage, tag_active) VALUES (?, ?, 1, 1)",
            (tag_name, creator_id),
        )
        tag_ids.append(int(cursor.lastrowid))
    for index, action_id in enumerate(action_ids[:3]):
        db.execute(
            "INSERT INTO t_action_tag (atg_action_id, atg_tag_id) VALUES (?, ?)",
            (action_id, tag_ids[index]),
        )


def _insert_meeting_examples(db, creator_id: int, participant_ids: list[int], topic_ids: list[int], action_ids: list[int]) -> None:
    required_tables = {
        "t_meeting",
        "t_meeting_instance",
        "t_meeting_owner",
        "t_meeting_participant",
    }
    if any(not _has_table(db, table_name) for table_name in required_tables):
        return
    topic_id = topic_ids[0] if topic_ids else None
    meeting_cursor = db.execute(
        """
        INSERT INTO t_meeting (mtg_title, mtg_description, mtg_topic_id, mtg_visibility, mtg_created_by)
        VALUES (?, ?, ?, 'public', ?)
        """,
        (
            "Operations governance review",
            "Baseline recurring review created by the clean reseed utility.",
            topic_id,
            creator_id,
        ),
    )
    meeting_id = int(meeting_cursor.lastrowid)
    instance_cursor = db.execute(
        """
        INSERT INTO t_meeting_instance (
            min_meeting_id,
            min_title,
            min_date,
            min_type,
            min_topic_id,
            min_category_id,
            min_secondary_category_id,
            min_notes,
            min_visibility,
            min_created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'public', ?)
        """,
        (
            meeting_id,
            "Operations governance review - baseline",
            date.today().isoformat(),
            "Monthly",
            topic_id,
            topic_id,
            topic_ids[1] if len(topic_ids) > 1 else topic_id,
            "Decisions from this baseline meeting are intentionally compact and reusable.",
            creator_id,
        ),
    )
    meeting_instance_id = int(instance_cursor.lastrowid)
    db.execute(
        "INSERT INTO t_meeting_owner (mow_instance_id, mow_user_id, mow_granted_by) VALUES (?, ?, ?)",
        (meeting_instance_id, creator_id, creator_id),
    )
    for user_id in participant_ids[:3]:
        db.execute(
            "INSERT INTO t_meeting_participant (mpa_instance_id, mpa_user_id, mpa_added_by) VALUES (?, ?, ?)",
            (meeting_instance_id, user_id, creator_id),
        )
    if action_ids and _has_table(db, "t_meeting_decision"):
        decision_columns = _table_columns(db, "t_meeting_decision")
        insert_columns = ["mdc_meeting_id", "mdc_title", "mdc_body", "mdc_status", "mdc_created_by"]
        insert_values: list[object] = [
            meeting_instance_id,
            "Publish the baseline governance pack",
            "Use the reseeded examples as the canonical starting point for manual QA and stakeholder demos.",
            "Accepted",
            creator_id,
        ]
        optional_pairs = [
            ("mdc_instance_id", meeting_instance_id),
            ("mdc_category_id", topic_id),
            ("mdc_secondary_category_id", topic_ids[1] if len(topic_ids) > 1 else topic_id),
            ("mdc_action_type_id", _pick_categories(db)[0]),
            ("mdc_linked_action_id", action_ids[0]),
            ("mdc_tags", "baseline,meeting"),
            ("mdc_decided_at", datetime.now().isoformat(timespec="seconds")),
        ]
        for column_name, column_value in optional_pairs:
            if column_name in decision_columns:
                insert_columns.append(column_name)
                insert_values.append(column_value)
        placeholders = ", ".join(["?"] * len(insert_columns))
        db.execute(
            f"INSERT INTO t_meeting_decision ({', '.join(insert_columns)}) VALUES ({placeholders})",
            tuple(insert_values),
        )


def _insert_supporting_examples(db, creator_id: int, participant_ids: list[int], topic_ids: list[int]) -> None:
    reviewer_id = participant_ids[1] if len(participant_ids) > 1 else creator_id
    if _has_table(db, "t_notification"):
        db.execute(
            """
            INSERT INTO t_notification (ntf_user_id, ntf_event_type, ntf_title, ntf_body, ntf_is_read)
            VALUES (?, 'system', ?, ?, 0)
            """,
            (
                reviewer_id,
                "Clean examples loaded",
                "The reseed utility rebuilt the baseline examples and preserved your users, teams, and categories.",
            ),
        )
    if _has_table(db, "t_feedback"):
        db.execute(
            """
            INSERT INTO t_feedback (fbk_user_id, fbk_category, fbk_page, fbk_title, fbk_description, fbk_priority, fbk_status)
            VALUES (?, 'Feature', '/dashboard', ?, ?, 'Medium', 'Acknowledged')
            """,
            (
                reviewer_id,
                "Example request for dashboard filters",
                "Keep one seeded feedback item so the admin queue is not empty after a reset.",
            ),
        )
    if _has_table(db, "t_evolution"):
        db.execute(
            """
            INSERT INTO t_evolution (evo_version, evo_title, evo_description, evo_category, evo_date, evo_is_published, evo_author_id)
            VALUES (?, ?, ?, 'Improvement', ?, 1, ?)
            """,
            (
                "Baseline",
                "Clean reseed baseline",
                "The system was reset and repopulated with a compact, review-friendly dataset.",
                date.today().isoformat(),
                creator_id,
            ),
        )
def _insert_workflow_examples(db, creator_id: int, participant_ids: list[int], action_ids: list[int]) -> None:
    if not action_ids:
        return
    _ensure_workflow_tables(db)
    if not has_workflow_template_table() or not has_workflow_runtime_tables():
        return
    if not _has_table(db, "t_workflow_service_log"):
        return
    graph = {
        "steps": {
            "intake": {"type": "Task", "label": "Intake", "order": 1},
            "review": {"type": "Task", "label": "Review", "order": 2},
            "done": {"type": "End", "label": "Done"},
        },
        "transitions": [
            {"from": "intake", "to": "review"},
            {"from": "review", "to": "done"},
        ],
    }
    template_id = create_template(
        name_en="Baseline Action Review",
        name_cn="Baseline Action Review",
        wft_type="action",
        graph=graph,
        created_by=creator_id,
        desc="Compact workflow created by reseed_clean_examples.py",
        is_default=True,
    )
    instance_cursor = db.execute(
        """
        INSERT INTO t_workflow_instance (wfi_template_id, wfi_action_id, wfi_status, wfi_started_by, wfi_started_at)
        VALUES (?, ?, 'Active', ?, CURRENT_TIMESTAMP)
        """,
        (template_id, action_ids[0], creator_id),
    )
    instance_id = int(instance_cursor.lastrowid)
    db.execute(
        """
        INSERT INTO t_workflow_step_instance (wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id, wsi_entered_at)
        VALUES (?, 'intake', 'Completed', ?, CURRENT_TIMESTAMP)
        """,
        (instance_id, creator_id),
    )
    next_assignee = participant_ids[1] if len(participant_ids) > 1 else creator_id
    db.execute(
        """
        INSERT INTO t_workflow_step_instance (wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id, wsi_entered_at)
        VALUES (?, 'review', 'Active', ?, CURRENT_TIMESTAMP)
        """,
        (instance_id, next_assignee),
    )
    db.execute(
        """
        INSERT INTO t_workflow_service_log (wsl_instance_id, wsl_step_key, wsl_handler, wsl_status, wsl_inputs, wsl_outputs)
        VALUES (?, 'review', 'baseline_handler', 'Success', '{"source":"reseed"}', '{"status":"queued"}')
        """,
        (instance_id,),
    )


def _seed_examples(db) -> dict[str, int]:
    creator_id, participant_ids = _pick_users(db)
    topic_ids = _insert_topics(db, creator_id)
    action_ids = _insert_actions(db, creator_id, participant_ids, topic_ids)
    _insert_tags(db, creator_id, action_ids)
    _insert_meeting_examples(db, creator_id, participant_ids, topic_ids, action_ids)
    _insert_supporting_examples(db, creator_id, participant_ids, topic_ids)
    _insert_workflow_examples(db, creator_id, participant_ids, action_ids)
    db.commit()
    return {
        "topics": len(topic_ids),
        "actions": len(action_ids),
        "workflow_templates": db.execute("SELECT COUNT(*) AS n FROM t_workflow_template").fetchone()["n"] if _has_table(db, "t_workflow_template") else 0,
        "workflow_instances": db.execute("SELECT COUNT(*) AS n FROM t_workflow_instance").fetchone()["n"] if _has_table(db, "t_workflow_instance") else 0,
        "users_preserved": db.execute("SELECT COUNT(*) AS n FROM t_user").fetchone()["n"],
        "teams_preserved": db.execute("SELECT COUNT(*) AS n FROM t_team").fetchone()["n"],
        "categories_preserved": db.execute("SELECT COUNT(*) AS n FROM t_category").fetchone()["n"],
    }


def run_reseed(dry_run: bool = False) -> None:
    app = _create_db_app()
    with app.app_context():
        ensure_schema()
        db = get_db()
        _ensure_workflow_tables(db)
        table_names = _clear_mutable_data(db, dry_run=dry_run)
        if dry_run:
            print("Dry run only. The following tables would be cleared:")
            for table_name in table_names:
                print(f"  - {table_name}")
            return

        ensure_schema()
        summary = _seed_examples(db)
        print("Reseed complete.")
        print(f"Preserved users: {summary['users_preserved']}")
        print(f"Preserved teams: {summary['teams_preserved']}")
        print(f"Preserved categories: {summary['categories_preserved']}")
        print(f"Inserted topics: {summary['topics']}")
        print(f"Inserted actions: {summary['actions']}")
        print(f"Inserted workflow templates: {summary['workflow_templates']}")
        print(f"Inserted workflow instances: {summary['workflow_instances']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clear mutable ActionHub data and rebuild clean examples while preserving users, teams, categories, and memberships."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the tables that would be cleared without modifying the database.",
    )
    args = parser.parse_args()
    run_reseed(dry_run=args.dry_run)


if __name__ == "__main__":
    main()