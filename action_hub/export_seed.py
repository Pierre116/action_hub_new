"""
export_seed.py — Dump the current ActionHub database to a SQL seed file
========================================================================
Reads the live actionhub.db and writes INSERT OR IGNORE statements for
every table to  db/seed_current.sql  (relative to this script).

The generated file can be committed to git and used to reseed any machine:

    python init_db.py
    python reseed_from_export.py          # or: sqlite3 db/actionhub.db < db/seed_current.sql

Usage
-----
    python export_seed.py                          # default paths
    python export_seed.py path/to/actionhub.db     # explicit source
    python export_seed.py src.db out.sql           # explicit source + output
    python export_seed.py --exclude-secrets        # omit usr_pwd_hash column
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).parent
DEFAULT_DB   = SCRIPT_DIR / "db" / "actionhub.db"
DEFAULT_OUT  = SCRIPT_DIR / "db" / "seed_current.sql"

# Tables to export, in FK-safe insertion order.
# t_team is handled specially (circular FK with t_user).
TABLE_ORDER = [
    "t_department",
    "t_team",           # exported with tea_leader_user_id; applied after t_user
    "t_user",
    "t_topic",
    "t_category",
    "t_tag",
    "t_evolution",
    "t_meeting",
    "t_meeting_instance",
    "t_action",
    "t_assignment",
    "t_action_history",
    "t_action_feedback",
    "t_import_log",
    "t_action_tag",
    "t_comment",
    "t_meeting_memo",
    "t_meeting_summary",
    "t_meeting_owner",
    "t_meeting_participant",
    "t_meeting_decision",
    "t_meeting_decision_revision",
    "t_notification",
    "t_feedback",
    "t_user_team",
    "t_user_dept",
    "t_assignment_history",
    "t_workflow_template",
    "t_workflow_instance",
    "t_workflow_step_instance",
    "t_workflow_step_field_value",
    "t_workflow_approval",
    "t_workflow_step_attachment",
    "t_workflow_service_log",
    "t_workflow_assignment_counter",
]

# Columns that may be omitted when --exclude-secrets is passed
SENSITIVE_COLUMNS = {
    "t_user": {"usr_pwd_hash"},
}


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def _quote(value) -> str:
    """Return a SQL literal for *value*."""
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, bytes):
        # Store BLOBs as hex literals
        return "X'" + value.hex() + "'"
    # Escape single quotes by doubling them
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def dump_table(
    conn: sqlite3.Connection,
    table: str,
    out,
    exclude_cols: set[str],
    target_cols: list[str] | None = None,
) -> int:
    """Write INSERT OR IGNORE statements for *table* to *out*. Returns row count."""
    if not table_exists(conn, table):
        return 0

    all_cols = get_columns(conn, table)
    cols = [c for c in all_cols if c not in exclude_cols]
    if target_cols is not None:
        cols = [c for c in cols if c in target_cols]
    if not cols:
        return 0

    col_list = ", ".join(cols)
    rows = conn.execute(f"SELECT {col_list} FROM {table}").fetchall()
    if not rows:
        return 0

    out.write(f"\n-- {table} ({len(rows)} rows)\n")

    # Write in batches of up to 500 rows for readability
    BATCH = 500
    for batch_start in range(0, len(rows), BATCH):
        batch = rows[batch_start : batch_start + BATCH]
        out.write(f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES\n")
        for i, row in enumerate(batch):
            values = ", ".join(_quote(v) for v in row)
            suffix = "," if i < len(batch) - 1 else ";"
            out.write(f"  ({values}){suffix}\n")

    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export ActionHub DB data to a SQL seed file."
    )
    parser.add_argument(
        "source", nargs="?", default=str(DEFAULT_DB),
        help=f"Source SQLite database (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "output", nargs="?", default=str(DEFAULT_OUT),
        help=f"Output SQL file (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--exclude-secrets", action="store_true",
        help="Omit password hashes and other sensitive columns",
    )
    parser.add_argument(
        "--target-db", default=str(DEFAULT_DB),
        help="Reference DB used to filter columns to those that exist in the target schema (default: same as output DB)",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    output_path = Path(args.output)
    target_db_path = Path(args.target_db)

    if not source_path.exists():
        print(f"ERROR: database not found: {source_path}", file=sys.stderr)
        return 1

    # Build target column map for schema-aware filtering
    target_col_map: dict[str, list[str]] = {}
    if target_db_path.exists():
        try:
            tconn = sqlite3.connect(str(target_db_path))
            tconn.execute("PRAGMA foreign_keys = OFF")
            target_tables = [r[0] for r in tconn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for t in target_tables:
                target_col_map[t] = get_columns(tconn, t)
            tconn.close()
        except sqlite3.Error as exc:
            print(f"WARNING: could not read target DB for column filtering — {exc}", file=sys.stderr)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    src_uri = source_path.as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(src_uri, uri=True)
        conn.execute("PRAGMA foreign_keys = OFF")
    except sqlite3.Error as exc:
        print(f"ERROR: cannot open database — {exc}", file=sys.stderr)
        return 1

    total_rows = 0

    with open(output_path, "w", encoding="utf-8") as out:
        out.write(f"-- ActionHub seed export\n")
        out.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out.write(f"-- Source: {source_path.name}\n")
        out.write(f"-- Exclude secrets: {args.exclude_secrets}\n")
        out.write("--\n")
        out.write("-- Apply with:\n")
        out.write("--   python init_db.py\n")
        out.write("--   python reseed_from_export.py\n")
        out.write("--\n")
        out.write("PRAGMA foreign_keys = OFF;\n")
        out.write("BEGIN TRANSACTION;\n")

        for table in TABLE_ORDER:
            exclude = SENSITIVE_COLUMNS.get(table, set()) if args.exclude_secrets else set()
            target_cols = target_col_map.get(table)  # None if table not in target (will be skipped)
            count = dump_table(conn, table, out, exclude, target_cols)
            if count:
                print(f"  {table}: {count} rows")
                total_rows += count
            else:
                print(f"  {table}: (empty or missing)")

        out.write("\nCOMMIT;\n")
        out.write("PRAGMA foreign_keys = ON;\n")

    conn.close()

    print(f"\nExported {total_rows} rows → {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
