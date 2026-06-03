import sqlite3
import os
from pathlib import Path

from flask import current_app, g, has_app_context


def get_db() -> sqlite3.Connection:
    if has_app_context():
        if "db" not in g:
            db_path = Path(current_app.config["DATABASE"])
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA temp_store = MEMORY")
            # Use ~64 MB page cache; negative value = KiB
            conn.execute("PRAGMA cache_size = -65536")
            # Memory-map 256 MB of the DB file for faster reads
            conn.execute("PRAGMA mmap_size = 268435456")
            conn.execute("PRAGMA wal_autocheckpoint = 1000")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 5000")
            g.db = conn
        return g.db

    db_path_str = os.environ.get("DATABASE")
    if not db_path_str:
        raise RuntimeError("DATABASE is not configured")
    db_path = Path(db_path_str)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def close_db(_error=None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def _table_exists(db: sqlite3.Connection, table_name: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table_name,),
    ).fetchone()
    return bool(row)


def _find_subaction_root_action(db: sqlite3.Connection, subaction_id: int | None) -> int | None:
    current_id = int(subaction_id) if subaction_id else None
    visited: set[int] = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        row = db.execute(
            "SELECT sac_parent_act_id, sac_parent_sac_id FROM t_subaction WHERE sac_id = ?",
            (current_id,),
        ).fetchone()
        if not row:
            return None
        if row["sac_parent_act_id"]:
            return int(row["sac_parent_act_id"])
        current_id = int(row["sac_parent_sac_id"]) if row["sac_parent_sac_id"] else None
    return None


def _remove_subaction_readiness_and_delegation_schema(db: sqlite3.Connection) -> None:
    if _table_exists(db, "t_comment"):
        comment_columns = {
            row["name"] if isinstance(row, sqlite3.Row) else row[1]
            for row in db.execute("PRAGMA table_info(t_comment)").fetchall()
        }
        if "cmt_sac_id" in comment_columns:
            if _table_exists(db, "t_subaction"):
                rows = db.execute(
                    "SELECT cmt_id, cmt_sac_id FROM t_comment WHERE cmt_act_id IS NULL AND cmt_sac_id IS NOT NULL"
                ).fetchall()
                for row in rows:
                    root_action_id = _find_subaction_root_action(db, row["cmt_sac_id"])
                    if root_action_id:
                        db.execute(
                            "UPDATE t_comment SET cmt_act_id = ? WHERE cmt_id = ?",
                            (root_action_id, row["cmt_id"]),
                        )
            db.executescript(
                """
                ALTER TABLE t_comment RENAME TO t_comment_legacy_subaction;

                CREATE TABLE t_comment (
                    cmt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cmt_act_id INTEGER,
                    cmt_type TEXT NOT NULL DEFAULT 'Comment'
                        CHECK (cmt_type IN ('Comment','Achievement','Roadblock')),
                    cmt_body TEXT NOT NULL CHECK (length(cmt_body) BETWEEN 1 AND 2000),
                    cmt_created_by INTEGER NOT NULL,
                    cmt_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    cmt_edited_at TEXT,
                    cmt_edited_by INTEGER,
                    cmt_meeting_inst_id INTEGER,
                    cmt_is_deleted INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (cmt_act_id) REFERENCES t_action(act_id) ON DELETE CASCADE,
                    FOREIGN KEY (cmt_meeting_inst_id) REFERENCES t_meeting_instance(min_id) ON DELETE CASCADE,
                    FOREIGN KEY (cmt_created_by) REFERENCES t_user(usr_id),
                    FOREIGN KEY (cmt_edited_by) REFERENCES t_user(usr_id)
                );

                INSERT INTO t_comment (
                    cmt_id,
                    cmt_act_id,
                    cmt_type,
                    cmt_body,
                    cmt_created_by,
                    cmt_created_at,
                    cmt_edited_at,
                    cmt_edited_by,
                    cmt_meeting_inst_id,
                    cmt_is_deleted
                )
                SELECT
                    cmt_id,
                    cmt_act_id,
                    cmt_type,
                    cmt_body,
                    cmt_created_by,
                    cmt_created_at,
                    cmt_edited_at,
                    cmt_edited_by,
                    cmt_meeting_inst_id,
                    cmt_is_deleted
                FROM t_comment_legacy_subaction
                WHERE cmt_act_id IS NOT NULL;

                DROP TABLE t_comment_legacy_subaction;
                """
            )

    db.execute("DROP TABLE IF EXISTS t_readiness_assessment")
    db.execute("DROP TABLE IF EXISTS t_assessed_object")
    db.execute("DROP TABLE IF EXISTS t_readiness_dimension")
    db.execute("DROP TABLE IF EXISTS t_subaction")
    db.execute("DROP TABLE IF EXISTS t_approval_delegation")


def init_db() -> None:
    db = get_db()
    def _table_columns(table_name: str) -> set[str]:
        rows = db.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row[1] for row in rows}

    def _add_column_if_missing(table_name: str, column_name: str, column_ddl: str) -> None:
        table_names = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if table_name in table_names and column_name not in _table_columns(table_name):
            db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_ddl}")

    schema_path = Path(current_app.root_path).parent / "db" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as file_handle:
        db.executescript(file_handle.read())

    db.execute("PRAGMA foreign_keys = OFF")
    try:
        _remove_subaction_readiness_and_delegation_schema(db)
    finally:
        db.execute("PRAGMA foreign_keys = ON")

    # Compatibility bridge for databases created before later schema rollouts.
    _add_column_if_missing("t_meeting_instance", "min_category_id", "min_category_id INTEGER")
    _add_column_if_missing("t_meeting_instance", "min_secondary_category_id", "min_secondary_category_id INTEGER")
    _add_column_if_missing("t_meeting_decision", "mdc_category_id", "mdc_category_id INTEGER REFERENCES t_topic(top_id)")
    _add_column_if_missing("t_meeting_decision", "mdc_secondary_category_id", "mdc_secondary_category_id INTEGER REFERENCES t_topic(top_id)")
    _add_column_if_missing("t_meeting_decision", "mdc_instance_id", "mdc_instance_id INTEGER REFERENCES t_meeting_instance(min_id)")
    _add_column_if_missing("t_meeting_decision", "mdc_context", "mdc_context TEXT")
    _add_column_if_missing("t_meeting_decision", "mdc_reason", "mdc_reason TEXT")
    _add_column_if_missing("t_meeting_decision", "mdc_action_type_id", "mdc_action_type_id INTEGER REFERENCES t_category(cat_id)")
    _add_column_if_missing("t_meeting_decision", "mdc_deleted_at", "mdc_deleted_at TEXT")
    if "t_meeting_decision" in {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }:
        from actionhub.decisions.service import DecisionService

        DecisionService._ensure_schema(db)
        DecisionService._decision_columns(db)
    try:
        db.execute("ALTER TABLE t_team ADD COLUMN tea_leader_user_id INTEGER")
    except sqlite3.OperationalError as error:
        if "duplicate column name" not in str(error).lower():
            raise
    db.commit()


def init_app(app) -> None:
    with app.app_context():
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

            CREATE INDEX IF NOT EXISTS idx_afb_action ON t_action_feedback(afb_action_id);
            CREATE INDEX IF NOT EXISTS idx_afb_user ON t_action_feedback(afb_user_id);
            CREATE INDEX IF NOT EXISTS idx_afb_meeting ON t_action_feedback(afb_meeting_inst_id);
            """
        )
        table_names = {
            row["name"]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if "t_action" in table_names:
            db.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_action_archived_created
                ON t_action(act_archived, act_created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_action_archived_status_deadline
                ON t_action(act_archived, act_status, act_deadline);
                """
            )
            action_columns = {
                row["name"]
                for row in db.execute("PRAGMA table_info(t_action)").fetchall()
            }
            if "act_team_id" in action_columns:
                db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_action_archived_team
                    ON t_action(act_archived, act_team_id)
                    """
                )
        if "t_user_team" in table_names:
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_team_team
                ON t_user_team(utm_team_id)
                """
            )
        db.commit()

        # Run pending migrations for production sync
        from actionhub.migrations import run_pending_migrations
        run_pending_migrations(db)

    app.teardown_appcontext(close_db)
