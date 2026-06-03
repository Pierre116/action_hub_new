import json
import sqlite3
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    db_path = repo_root / "action_hub" / "db" / "actionhub.db"
    print(json.dumps({"db_path": str(db_path)}))

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    integrity = conn.execute("PRAGMA integrity_check").fetchall()
    print(json.dumps({"integrity_check": [tuple(row) for row in integrity[:20]]}))

    objects = conn.execute(
        """
        SELECT type, name, tbl_name
        FROM sqlite_master
        WHERE name LIKE 't_meeting_decision%'
           OR tbl_name LIKE 't_meeting_decision%'
        ORDER BY type, name
        """
    ).fetchall()
    print(json.dumps({"decision_objects": [dict(row) for row in objects]}))

    matching = conn.execute(
        """
        SELECT mdc_id, mdc_title, substr(mdc_body, 1, 120) AS body_preview, mdc_updated_at
        FROM t_meeting_decision
        WHERE mdc_title LIKE ? OR mdc_body LIKE ?
        ORDER BY mdc_id DESC
        LIMIT 10
        """,
        ("%gdsgdfs%", "%gdfsgdfgfdgfdgdfgdsfgfdsgdfggdfgfdg%"),
    ).fetchall()
    print(json.dumps({"matching_rows": [dict(row) for row in matching]}))

    latest = conn.execute(
        "SELECT mdc_id, mdc_title FROM t_meeting_decision ORDER BY mdc_id DESC LIMIT 1"
    ).fetchone()
    print(json.dumps({"latest_decision": dict(latest) if latest else None}))

    if latest is None:
        return

    probe_result: dict[str, object]
    try:
        conn.execute("BEGIN")
        conn.execute(
            "UPDATE t_meeting_decision SET mdc_updated_at = COALESCE(mdc_updated_at, CURRENT_TIMESTAMP) WHERE mdc_id = ?",
            (latest["mdc_id"],),
        )
        conn.rollback()
        probe_result = {"update_probe": "ok", "decision_id": latest["mdc_id"]}
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        probe_result = {
            "update_probe": "error",
            "decision_id": latest["mdc_id"],
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    print(json.dumps(probe_result))

    if matching:
        target_id = matching[0]["mdc_id"]
        try:
            conn.execute("BEGIN")
            conn.execute(
                "UPDATE t_meeting_decision SET mdc_title = ?, mdc_body = ? WHERE mdc_id = ?",
                ("gdsgdfs", "gdfsgdfgfdgfdgdfgdsfgfdsgdfggdfgfdg", target_id),
            )
            conn.rollback()
            print(json.dumps({"matching_update_probe": "ok", "decision_id": target_id}))
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            print(
                json.dumps(
                    {
                        "matching_update_probe": "error",
                        "decision_id": target_id,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
            )


if __name__ == "__main__":
    main()