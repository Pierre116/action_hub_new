"""
import_db.py — ActionHub database migration / clean-import tool
===============================================================
Copies all data from a (potentially malformed/synced) source SQLite database
into a freshly initialised target database built from schema.sql.

Usage
-----
  python import_db.py                          # uses default paths
  python import_db.py SOURCE.db TARGET.db      # explicit paths
  python import_db.py SOURCE.db TARGET.db --skip-errors  # keep going on row errors

Options
-------
  --skip-errors   Continue importing rows even when individual rows fail
                  integrity checks.  Skipped rows are written to import_db.log.
  --no-backup     Do not create a .bak copy of the source database first.

Exit codes
----------
  0  Success (all rows imported, or --skip-errors was set and errors were logged)
  1  Fatal error (missing files, schema failure, etc.)
"""

import argparse
import os
import shutil
import sqlite3
import sys
import textwrap
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults (relative to this script's location)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
DEFAULT_SOURCE = SCRIPT_DIR / "action_hub" / "db" / "actionhub.db"
DEFAULT_TARGET = SCRIPT_DIR / "action_hub" / "db" / "actionhub_imported.db"
SCHEMA_FILE    = SCRIPT_DIR / "action_hub" / "db" / "schema.sql"
LOG_FILE       = SCRIPT_DIR / "import_db.log"

# ---------------------------------------------------------------------------
# Table copy order — respects FK dependencies.
#
# Special case: t_team <-> t_user circular dependency is handled manually:
#   1. Insert teams with tea_leader_user_id = NULL
#   2. Insert users
#   3. Patch teams: restore tea_leader_user_id from source
# ---------------------------------------------------------------------------
TABLE_ORDER = [
    "t_department",
    # t_team inserted specially (step 1 below)
    # t_user inserted after teams (step 2)
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
    # Workflow tables
    "t_workflow_template",
    "t_workflow_instance",
    "t_workflow_step_instance",
    "t_workflow_step_field_value",
    "t_workflow_approval",
    "t_workflow_step_attachment",
    "t_workflow_service_log",
    "t_workflow_assignment_counter",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str, file=None):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if file:
        file.write(line + "\n")
        file.flush()


def get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """Return column names for *table* (skips rowid-only cols)."""
    cur = conn.execute(f"PRAGMA table_info({table})")  # table name is not user input
    return [row[1] for row in cur.fetchall()]


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def copy_table(
    src: sqlite3.Connection,
    dst: sqlite3.Connection,
    table: str,
    skip_errors: bool,
    logfile,
) -> tuple[int, int]:
    """
    Copy all rows from *table* in src → dst.
    Returns (inserted, skipped).
    """
    if not table_exists(src, table):
        log(f"  SKIP  {table} — not found in source", logfile)
        return 0, 0
    if not table_exists(dst, table):
        log(f"  SKIP  {table} — not found in target (schema mismatch?)", logfile)
        return 0, 0

    src_cols = get_columns(src, table)
    dst_cols = get_columns(dst, table)

    # Only copy columns that exist in both source and target
    common_cols = [c for c in src_cols if c in dst_cols]
    if not common_cols:
        log(f"  SKIP  {table} — no common columns", logfile)
        return 0, 0

    col_list = ", ".join(common_cols)
    placeholders = ", ".join(["?"] * len(common_cols))
    insert_sql = f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})"

    rows = src.execute(f"SELECT {col_list} FROM {table}").fetchall()
    inserted = 0
    skipped = 0

    for row in rows:
        try:
            dst.execute(insert_sql, row)
            inserted += 1
        except sqlite3.IntegrityError as exc:
            skipped += 1
            if not skip_errors:
                raise RuntimeError(
                    f"Integrity error in {table}: {exc}\nRow: {dict(zip(common_cols, row))}"
                ) from exc
            log(f"  WARN  {table} row skipped — {exc} | row={dict(zip(common_cols, row))}", logfile)
        except sqlite3.Error as exc:
            skipped += 1
            if not skip_errors:
                raise RuntimeError(f"DB error in {table}: {exc}") from exc
            log(f"  WARN  {table} row error — {exc}", logfile)

    return inserted, skipped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Import ActionHub source DB into a fresh target DB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(__doc__),
    )
    parser.add_argument(
        "source", nargs="?", default=str(DEFAULT_SOURCE),
        help=f"Path to source SQLite database (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "target", nargs="?", default=str(DEFAULT_TARGET),
        help=f"Path for new target SQLite database (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--skip-errors", action="store_true",
        help="Log bad rows and continue rather than aborting on the first error",
    )
    parser.add_argument(
        "--no-backup", action="store_true",
        help="Skip creating a .bak backup of the source database",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    target_path = Path(args.target)

    # --- Validate source ---
    if not source_path.exists():
        print(f"ERROR: Source database not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    if not SCHEMA_FILE.exists():
        print(f"ERROR: Schema file not found: {SCHEMA_FILE}", file=sys.stderr)
        sys.exit(1)

    # --- Backup source ---
    if not args.no_backup:
        backup_path = source_path.with_suffix(".bak")
        shutil.copy2(source_path, backup_path)
        print(f"Backup created: {backup_path}")

    # --- Remove existing target ---
    if target_path.exists():
        target_path.unlink()
        print(f"Removed existing target: {target_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)

    with open(LOG_FILE, "w", encoding="utf-8") as logfile:
        log(f"Source : {source_path}", logfile)
        log(f"Target : {target_path}", logfile)
        log(f"Schema : {SCHEMA_FILE}", logfile)
        log("", logfile)

        # ----------------------------------------------------------------
        # Step 0 — Build fresh target schema
        # ----------------------------------------------------------------
        log("Building target schema …", logfile)
        schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
        dst = sqlite3.connect(str(target_path))
        dst.execute("PRAGMA journal_mode = WAL")
        dst.execute("PRAGMA foreign_keys = OFF")   # OFF during bulk load
        try:
            dst.executescript(schema_sql)
        except sqlite3.Error as exc:
            log(f"FATAL: schema creation failed — {exc}", logfile)
            dst.close()
            sys.exit(1)
        log("Schema ready.", logfile)

        # ----------------------------------------------------------------
        # Step 1 — Open source (read-only via URI to avoid locking issues)
        # ----------------------------------------------------------------
        src_uri = source_path.as_uri() + "?mode=ro"
        try:
            src = sqlite3.connect(src_uri, uri=True)
            src.execute("PRAGMA foreign_keys = OFF")
        except sqlite3.Error as exc:
            log(f"FATAL: cannot open source DB — {exc}", logfile)
            dst.close()
            sys.exit(1)

        total_inserted = 0
        total_skipped  = 0

        # ----------------------------------------------------------------
        # Step 2 — Insert t_team WITHOUT the leader FK (circular dep)
        # ----------------------------------------------------------------
        log("Copying t_team (leader FK deferred) …", logfile)
        if table_exists(src, "t_team"):
            src_cols  = get_columns(src, "t_team")
            dst_cols  = get_columns(dst, "t_team")
            # Exclude the FK column for now
            safe_cols = [c for c in src_cols if c in dst_cols and c != "tea_leader_user_id"]
            col_list  = ", ".join(safe_cols)
            ph        = ", ".join(["?"] * len(safe_cols))
            ins_sql   = f"INSERT OR IGNORE INTO t_team ({col_list}) VALUES ({ph})"
            rows = src.execute(f"SELECT {col_list} FROM t_team").fetchall()
            for row in rows:
                try:
                    dst.execute(ins_sql, row)
                    total_inserted += 1
                except sqlite3.Error as exc:
                    total_skipped += 1
                    if not args.skip_errors:
                        log(f"FATAL: t_team row error — {exc}", logfile)
                        src.close(); dst.close(); sys.exit(1)
                    log(f"  WARN  t_team row skipped — {exc}", logfile)
            dst.commit()
            log(f"  t_team: {len(rows)} rows loaded (leader FK pending)", logfile)

        # ----------------------------------------------------------------
        # Step 3 — Insert t_user
        # ----------------------------------------------------------------
        log("Copying t_user …", logfile)
        ins, skp = copy_table(src, dst, "t_user", args.skip_errors, logfile)
        dst.commit()
        log(f"  t_user: {ins} inserted, {skp} skipped", logfile)
        total_inserted += ins
        total_skipped  += skp

        # ----------------------------------------------------------------
        # Step 4 — Patch t_team.tea_leader_user_id
        # ----------------------------------------------------------------
        log("Patching t_team leader FK …", logfile)
        if table_exists(src, "t_team") and "tea_leader_user_id" in get_columns(src, "t_team"):
            rows = src.execute("SELECT tea_id, tea_leader_user_id FROM t_team WHERE tea_leader_user_id IS NOT NULL").fetchall()
            patched = 0
            for tea_id, leader_id in rows:
                try:
                    dst.execute(
                        "UPDATE t_team SET tea_leader_user_id = ? WHERE tea_id = ?",
                        (leader_id, tea_id),
                    )
                    patched += 1
                except sqlite3.Error as exc:
                    if not args.skip_errors:
                        log(f"FATAL: t_team leader patch failed — {exc}", logfile)
                        src.close(); dst.close(); sys.exit(1)
                    log(f"  WARN  t_team leader patch skipped for tea_id={tea_id} — {exc}", logfile)
            dst.commit()
            log(f"  Patched {patched} team leader FK(s)", logfile)

        # ----------------------------------------------------------------
        # Step 5 — All remaining tables in FK-safe order
        # ----------------------------------------------------------------
        for table in TABLE_ORDER:
            log(f"Copying {table} …", logfile)
            ins, skp = copy_table(src, dst, table, args.skip_errors, logfile)
            dst.commit()
            log(f"  {table}: {ins} inserted, {skp} skipped", logfile)
            total_inserted += ins
            total_skipped  += skp

        # ----------------------------------------------------------------
        # Step 6 — Rebuild FTS5 index for meeting decisions
        # ----------------------------------------------------------------
        log("Rebuilding FTS5 index (t_meeting_decision_fts) …", logfile)
        try:
            dst.execute("INSERT INTO t_meeting_decision_fts(t_meeting_decision_fts) VALUES('rebuild')")
            dst.commit()
            log("  FTS5 rebuild OK", logfile)
        except sqlite3.Error as exc:
            log(f"  WARN  FTS5 rebuild failed (non-fatal) — {exc}", logfile)

        # ----------------------------------------------------------------
        # Finalise
        # ----------------------------------------------------------------
        src.close()
        dst.execute("PRAGMA foreign_keys = ON")
        dst.execute("PRAGMA integrity_check")
        dst.close()

        log("", logfile)
        log("=" * 60, logfile)
        log(f"DONE — {total_inserted} rows inserted, {total_skipped} rows skipped", logfile)
        log(f"Target database: {target_path}", logfile)
        if total_skipped:
            log(f"Review skipped rows in: {LOG_FILE}", logfile)
        log("=" * 60, logfile)

    print(f"\nLog written to: {LOG_FILE}")
    return 0 if (total_skipped == 0 or args.skip_errors) else 1


if __name__ == "__main__":
    sys.exit(main())
