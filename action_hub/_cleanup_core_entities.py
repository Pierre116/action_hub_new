import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "db" / "actionhub.db"


def table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    row = cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def count_rows(cur: sqlite3.Cursor, table_name: str) -> int:
    if not table_exists(cur, table_name):
        return 0
    return int(cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def fetch_ids(cur: sqlite3.Cursor, table_name: str, id_column: str) -> list[int]:
    if not table_exists(cur, table_name):
        return []
    rows = cur.execute(f"SELECT {id_column} FROM {table_name}").fetchall()
    return [int(row[0]) for row in rows]


def delete_where_in(cur: sqlite3.Cursor, table_name: str, column_name: str, ids: list[int]) -> int:
    if not ids or not table_exists(cur, table_name):
        return 0
    placeholders = ",".join("?" for _ in ids)
    sql = f"DELETE FROM {table_name} WHERE {column_name} IN ({placeholders})"
    cur.execute(sql, ids)
    return cur.rowcount if cur.rowcount is not None else 0


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tables_to_report = [
        "t_action",
        "t_meeting_decision",
        "t_meeting_decision_revision",
        "t_meeting_instance",
        "t_meeting",
        "t_assignment",
        "t_assignment_history",
        "t_action_history",
        "t_action_feedback",
        "t_action_tag",
        "t_comment",
        "t_meeting_memo",
        "t_meeting_summary",
        "t_meeting_owner",
        "t_meeting_participant",
        "t_notification",
        "t_workflow_instance",
        "t_workflow_step_instance",
        "t_workflow_step_field_value",
        "t_workflow_approval",
        "t_workflow_step_attachment",
        "t_workflow_service_log",
    ]

    before = {table: count_rows(cur, table) for table in tables_to_report}

    action_ids = fetch_ids(cur, "t_action", "act_id")
    meeting_instance_ids = fetch_ids(cur, "t_meeting_instance", "min_id")
    decision_ids = fetch_ids(cur, "t_meeting_decision", "mdc_id")

    workflow_instance_ids: list[int] = []
    workflow_step_ids: list[int] = []
    if table_exists(cur, "t_workflow_instance") and action_ids:
        placeholders = ",".join("?" for _ in action_ids)
        rows = cur.execute(
            f"SELECT wfi_id FROM t_workflow_instance WHERE wfi_action_id IN ({placeholders})",
            action_ids,
        ).fetchall()
        workflow_instance_ids = [int(row[0]) for row in rows]

    if table_exists(cur, "t_workflow_step_instance") and workflow_instance_ids:
        placeholders = ",".join("?" for _ in workflow_instance_ids)
        rows = cur.execute(
            f"SELECT wsi_id FROM t_workflow_step_instance WHERE wsi_instance_id IN ({placeholders})",
            workflow_instance_ids,
        ).fetchall()
        workflow_step_ids = [int(row[0]) for row in rows]

    deleted_counts: dict[str, int] = {}

    cur.execute("PRAGMA foreign_keys = ON")
    conn.execute("BEGIN")

    deleted_counts["t_meeting_decision_revision"] = delete_where_in(
        cur, "t_meeting_decision_revision", "mdr_decision_id", decision_ids
    )

    deleted_counts["t_workflow_approval"] = delete_where_in(
        cur, "t_workflow_approval", "wap_step_inst_id", workflow_step_ids
    )
    deleted_counts["t_workflow_step_attachment_by_step"] = delete_where_in(
        cur, "t_workflow_step_attachment", "wsa_step_inst_id", workflow_step_ids
    )
    deleted_counts["t_workflow_step_attachment_by_action"] = delete_where_in(
        cur, "t_workflow_step_attachment", "wsa_action_id", action_ids
    )
    deleted_counts["t_workflow_service_log"] = delete_where_in(
        cur, "t_workflow_service_log", "wsl_instance_id", workflow_instance_ids
    )
    deleted_counts["t_workflow_step_field_value"] = delete_where_in(
        cur, "t_workflow_step_field_value", "wsf_instance_id", workflow_instance_ids
    )
    deleted_counts["t_workflow_step_instance"] = delete_where_in(
        cur, "t_workflow_step_instance", "wsi_instance_id", workflow_instance_ids
    )
    deleted_counts["t_workflow_instance"] = delete_where_in(
        cur, "t_workflow_instance", "wfi_id", workflow_instance_ids
    )

    if table_exists(cur, "t_assignment"):
        cur.execute("DELETE FROM t_assignment")
        deleted_counts["t_assignment"] = cur.rowcount if cur.rowcount is not None else 0

    if table_exists(cur, "t_assignment_history"):
        cur.execute("DELETE FROM t_assignment_history")
        deleted_counts["t_assignment_history"] = cur.rowcount if cur.rowcount is not None else 0

    if table_exists(cur, "t_action_history"):
        cur.execute("DELETE FROM t_action_history")
        deleted_counts["t_action_history"] = cur.rowcount if cur.rowcount is not None else 0

    if table_exists(cur, "t_action_feedback"):
        cur.execute("DELETE FROM t_action_feedback")
        deleted_counts["t_action_feedback"] = cur.rowcount if cur.rowcount is not None else 0

    if table_exists(cur, "t_action_tag"):
        cur.execute("DELETE FROM t_action_tag")
        deleted_counts["t_action_tag"] = cur.rowcount if cur.rowcount is not None else 0

    if table_exists(cur, "t_comment"):
        cur.execute("DELETE FROM t_comment")
        deleted_counts["t_comment"] = cur.rowcount if cur.rowcount is not None else 0
    deleted_counts["t_notification"] = delete_where_in(
        cur, "t_notification", "ntf_action_id", action_ids
    )

    if table_exists(cur, "t_meeting_memo"):
        cur.execute("DELETE FROM t_meeting_memo")
        deleted_counts["t_meeting_memo"] = cur.rowcount if cur.rowcount is not None else 0

    if table_exists(cur, "t_meeting_summary"):
        cur.execute("DELETE FROM t_meeting_summary")
        deleted_counts["t_meeting_summary"] = cur.rowcount if cur.rowcount is not None else 0

    if table_exists(cur, "t_meeting_owner"):
        cur.execute("DELETE FROM t_meeting_owner")
        deleted_counts["t_meeting_owner"] = cur.rowcount if cur.rowcount is not None else 0

    if table_exists(cur, "t_meeting_participant"):
        cur.execute("DELETE FROM t_meeting_participant")
        deleted_counts["t_meeting_participant"] = cur.rowcount if cur.rowcount is not None else 0

    if table_exists(cur, "t_meeting_decision"):
        cur.execute("DELETE FROM t_meeting_decision")
        deleted_counts["t_meeting_decision"] = cur.rowcount if cur.rowcount is not None else 0

    if table_exists(cur, "t_action"):
        cur.execute("DELETE FROM t_action")
        deleted_counts["t_action"] = cur.rowcount if cur.rowcount is not None else 0

    if table_exists(cur, "t_meeting_instance"):
        cur.execute("DELETE FROM t_meeting_instance")
        deleted_counts["t_meeting_instance"] = cur.rowcount if cur.rowcount is not None else 0

    if table_exists(cur, "t_meeting"):
        cur.execute("DELETE FROM t_meeting")
        deleted_counts["t_meeting"] = cur.rowcount if cur.rowcount is not None else 0

    conn.commit()

    after = {table: count_rows(cur, table) for table in tables_to_report}

    result = {
        "database": str(DB_PATH),
        "before": before,
        "deleted": deleted_counts,
        "after": after,
    }
    print(json.dumps(result, indent=2))

    conn.close()


if __name__ == "__main__":
    main()
