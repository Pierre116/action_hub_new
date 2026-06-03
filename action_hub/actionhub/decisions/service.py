"""
Service layer for Meeting Decisions (P8, P11).
Handles CRUD operations, lifecycle transitions, FTS5 search, and dashboard counts.
Supports dual-category model (0..2 categories).
"""
import sqlite3
from typing import List, Dict, Any, Optional

from actionhub.middleware.db import get_db


class DecisionService:
    """Service class for Meeting Decision operations."""

    ACTIVE_STATUS = "Published"
    INACTIVE_STATUS = "Expired"
    STATUS_VALUES = {ACTIVE_STATUS, INACTIVE_STATUS}
    DB_ACTIVE_STATUS = "Proposed"
    DB_INACTIVE_STATUS = "Deleted"
    LEGACY_INACTIVE_STATUSES = {"Cancelled", "Rejected", "Withdrawn", "Obsolete", "Expired", "Deleted"}

    # Valid status transitions (FSM)
    STATUS_FSM = {
        ACTIVE_STATUS: [INACTIVE_STATUS],
        INACTIVE_STATUS: [],
    }

    @staticmethod
    def _table_columns(db, table_name: str) -> set[str]:
        return {row[1] for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()}

    @staticmethod
    def _normalize_tags(value) -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, (list, tuple, set)):
            raw_tags = [str(item or "") for item in value]

        else:
            raw_tags = str(value).replace("\n", ",").split(",")

        normalized_tags: list[str] = []
        seen: set[str] = set()
        for raw_tag in raw_tags:
            tag = str(raw_tag).strip().lstrip("#").upper()
            if not tag:
                continue
            if len(tag) > 120:
                tag = tag[:120]
            if tag in seen:
                continue
            seen.add(tag)
            normalized_tags.append(tag)
        return ", ".join(normalized_tags)

    @staticmethod
    def _decision_table_sql(db) -> str:
        row = db.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 't_meeting_decision'"
        ).fetchone()
        return row[0] if row and row[0] else ""

    @staticmethod
    def _rebuild_fts_artifacts(db) -> None:
        db.execute("DROP TRIGGER IF EXISTS t_meeting_decision_ai")
        db.execute("DROP TRIGGER IF EXISTS t_meeting_decision_ad")
        db.execute("DROP TRIGGER IF EXISTS t_meeting_decision_au")
        db.execute("DROP TRIGGER IF EXISTS trg_meeting_decision_fts")
        db.execute("DROP TRIGGER IF EXISTS trg_meeting_decision_fts_update")
        db.execute("DROP TRIGGER IF EXISTS trg_meeting_decision_fts_delete")
        db.execute("DROP TABLE IF EXISTS t_meeting_decision_fts")
        db.executescript(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS t_meeting_decision_fts USING fts5(
                mdc_title,
                mdc_body,
                mdc_context,
                mdc_reason,
                mdc_tags,
                content='t_meeting_decision',
                content_rowid='mdc_id'
            );

            CREATE TRIGGER IF NOT EXISTS t_meeting_decision_ai AFTER INSERT ON t_meeting_decision BEGIN
                INSERT INTO t_meeting_decision_fts(rowid, mdc_title, mdc_body, mdc_context, mdc_reason, mdc_tags)
                VALUES (new.mdc_id, new.mdc_title, new.mdc_body, new.mdc_context, new.mdc_reason, new.mdc_tags);
            END;

            CREATE TRIGGER IF NOT EXISTS t_meeting_decision_ad AFTER DELETE ON t_meeting_decision BEGIN
                INSERT INTO t_meeting_decision_fts(t_meeting_decision_fts, rowid, mdc_title, mdc_body, mdc_context, mdc_reason, mdc_tags)
                VALUES('delete', old.mdc_id, old.mdc_title, old.mdc_body, old.mdc_context, old.mdc_reason, old.mdc_tags);
            END;

            CREATE TRIGGER IF NOT EXISTS t_meeting_decision_au AFTER UPDATE ON t_meeting_decision BEGIN
                INSERT INTO t_meeting_decision_fts(t_meeting_decision_fts, rowid, mdc_title, mdc_body, mdc_context, mdc_reason, mdc_tags)
                VALUES('delete', old.mdc_id, old.mdc_title, old.mdc_body, old.mdc_context, old.mdc_reason, old.mdc_tags);
                INSERT INTO t_meeting_decision_fts(rowid, mdc_title, mdc_body, mdc_context, mdc_reason, mdc_tags)
                VALUES (new.mdc_id, new.mdc_title, new.mdc_body, new.mdc_context, new.mdc_reason, new.mdc_tags);
            END;
            """
        )
        db.execute("INSERT INTO t_meeting_decision_fts(t_meeting_decision_fts) VALUES ('rebuild')")

    @staticmethod
    def _is_malformed_error(error: BaseException) -> bool:
        return "malformed" in str(error).lower()

    @staticmethod
    def _ensure_schema(db) -> None:
        ddl = DecisionService._decision_table_sql(db)
        if not ddl:
            return

        columns = DecisionService._table_columns(db, "t_meeting_decision")
        normalized_ddl = " ".join(ddl.lower().split())
        legacy_category_is_action_type = "mdc_category_id integer references t_category(cat_id)" in normalized_ddl
        has_legacy_topic_code_fk = "references t_topic(top_code)" in normalized_ddl
        needs_rebuild = any(
            (
                "mdc_instance_id" not in columns,
                "mdc_action_type_id" not in columns,
                "mdc_deleted_at" not in columns,
                "mdc_business_theme_id" in columns,
                legacy_category_is_action_type,
                has_legacy_topic_code_fk,
            )
        )
        if not needs_rebuild:
            return

        legacy_columns = set(columns)

        def valid_fk_expr(column_name: str, table_name: str, pk_name: str) -> str:
            if column_name not in legacy_columns:
                return "NULL"
            return (
                f"CASE WHEN {column_name} IS NOT NULL AND EXISTS ("
                f"SELECT 1 FROM {table_name} WHERE {pk_name} = {column_name}"
                f") THEN {column_name} ELSE NULL END"
            )

        meeting_expr = "mdc_meeting_id" if "mdc_meeting_id" in legacy_columns else "NULL"
        instance_expr = "mdc_instance_id" if "mdc_instance_id" in legacy_columns else meeting_expr

        if "mdc_business_theme_id" in legacy_columns:
            category_expr = valid_fk_expr("mdc_business_theme_id", "t_topic", "top_id")
        elif legacy_category_is_action_type:
            category_expr = "NULL"
        else:
            category_expr = valid_fk_expr("mdc_category_id", "t_topic", "top_id")

        secondary_category_expr = valid_fk_expr("mdc_secondary_category_id", "t_topic", "top_id")
        if "mdc_action_type_id" in legacy_columns:
            action_type_expr = valid_fk_expr("mdc_action_type_id", "t_category", "cat_id")
        elif legacy_category_is_action_type:
            action_type_expr = valid_fk_expr("mdc_category_id", "t_category", "cat_id")
        else:
            action_type_expr = "NULL"

        linked_action_expr = valid_fk_expr("mdc_linked_action_id", "t_action", "act_id")

        db.execute("DROP TRIGGER IF EXISTS t_meeting_decision_ai")
        db.execute("DROP TRIGGER IF EXISTS t_meeting_decision_ad")
        db.execute("DROP TRIGGER IF EXISTS t_meeting_decision_au")
        db.execute("DROP TRIGGER IF EXISTS trg_meeting_decision_fts")
        db.execute("DROP TRIGGER IF EXISTS trg_meeting_decision_fts_update")
        db.execute("DROP TRIGGER IF EXISTS trg_meeting_decision_fts_delete")
        db.execute("DROP INDEX IF EXISTS idx_decision_secondary_category")
        db.execute("DROP TABLE IF EXISTS t_meeting_decision_fts")

        db.execute("ALTER TABLE t_meeting_decision RENAME TO t_meeting_decision_legacy")
        db.executescript(
            """
            CREATE TABLE t_meeting_decision (
                mdc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mdc_meeting_id INTEGER,
                mdc_instance_id INTEGER,
                mdc_title TEXT NOT NULL,
                mdc_body TEXT NOT NULL,
                mdc_context TEXT,
                mdc_reason TEXT,
                mdc_status TEXT NOT NULL DEFAULT 'Proposed'
                    CHECK (mdc_status IN ('Proposed', 'Accepted', 'Approved', 'Rejected', 'Implemented', 'Reversed', 'Deleted')),
                mdc_category_id INTEGER REFERENCES t_topic(top_id),
                mdc_secondary_category_id INTEGER REFERENCES t_topic(top_id),
                mdc_action_type_id INTEGER REFERENCES t_category(cat_id),
                mdc_linked_action_id INTEGER REFERENCES t_action(act_id),
                mdc_tags TEXT,
                mdc_decided_at TEXT,
                mdc_created_by INTEGER NOT NULL,
                mdc_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                mdc_updated_at TEXT,
                mdc_deleted_at TEXT,
                FOREIGN KEY (mdc_meeting_id) REFERENCES t_meeting_instance(min_id),
                FOREIGN KEY (mdc_instance_id) REFERENCES t_meeting_instance(min_id),
                FOREIGN KEY (mdc_created_by) REFERENCES t_user(usr_id)
            );
            """
        )
        db.execute(
            f"""
            INSERT INTO t_meeting_decision (
                mdc_id,
                mdc_meeting_id,
                mdc_instance_id,
                mdc_title,
                mdc_body,
                mdc_context,
                mdc_reason,
                mdc_status,
                mdc_category_id,
                mdc_secondary_category_id,
                mdc_action_type_id,
                mdc_linked_action_id,
                mdc_tags,
                mdc_decided_at,
                mdc_created_by,
                mdc_created_at,
                mdc_updated_at,
                mdc_deleted_at
            )
            SELECT
                mdc_id,
                {meeting_expr},
                {instance_expr},
                mdc_title,
                COALESCE(mdc_body, ''),
                {('mdc_context' if 'mdc_context' in legacy_columns else 'NULL')},
                {('mdc_reason' if 'mdc_reason' in legacy_columns else 'NULL')},
                COALESCE(mdc_status, 'Proposed'),
                {category_expr},
                {secondary_category_expr},
                {action_type_expr},
                {linked_action_expr},
                mdc_tags,
                mdc_decided_at,
                mdc_created_by,
                COALESCE(mdc_created_at, CURRENT_TIMESTAMP),
                mdc_updated_at,
                {('mdc_deleted_at' if 'mdc_deleted_at' in legacy_columns else 'NULL')}
            FROM t_meeting_decision_legacy
            """
        )
        db.execute("DROP TABLE t_meeting_decision_legacy")
        db.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_decision_secondary_category ON t_meeting_decision(mdc_secondary_category_id) WHERE mdc_secondary_category_id IS NOT NULL;

            CREATE VIRTUAL TABLE IF NOT EXISTS t_meeting_decision_fts USING fts5(
                mdc_title,
                mdc_body,
                mdc_context,
                mdc_reason,
                mdc_tags,
                content='t_meeting_decision',
                content_rowid='mdc_id'
            );

            CREATE TRIGGER IF NOT EXISTS t_meeting_decision_ai AFTER INSERT ON t_meeting_decision BEGIN
                INSERT INTO t_meeting_decision_fts(rowid, mdc_title, mdc_body, mdc_context, mdc_reason, mdc_tags)
                VALUES (new.mdc_id, new.mdc_title, new.mdc_body, new.mdc_context, new.mdc_reason, new.mdc_tags);
            END;

            CREATE TRIGGER IF NOT EXISTS t_meeting_decision_ad AFTER DELETE ON t_meeting_decision BEGIN
                INSERT INTO t_meeting_decision_fts(t_meeting_decision_fts, rowid, mdc_title, mdc_body, mdc_context, mdc_reason, mdc_tags)
                VALUES('delete', old.mdc_id, old.mdc_title, old.mdc_body, old.mdc_context, old.mdc_reason, old.mdc_tags);
            END;

            CREATE TRIGGER IF NOT EXISTS t_meeting_decision_au AFTER UPDATE ON t_meeting_decision BEGIN
                INSERT INTO t_meeting_decision_fts(t_meeting_decision_fts, rowid, mdc_title, mdc_body, mdc_context, mdc_reason, mdc_tags)
                VALUES('delete', old.mdc_id, old.mdc_title, old.mdc_body, old.mdc_context, old.mdc_reason, old.mdc_tags);
                INSERT INTO t_meeting_decision_fts(rowid, mdc_title, mdc_body, mdc_context, mdc_reason, mdc_tags)
                VALUES (new.mdc_id, new.mdc_title, new.mdc_body, new.mdc_context, new.mdc_reason, new.mdc_tags);
            END;
            """
        )
        db.execute("INSERT INTO t_meeting_decision_fts(t_meeting_decision_fts) VALUES ('rebuild')")

    @staticmethod
    def _decision_columns(db) -> set[str]:
        DecisionService._ensure_schema(db)
        columns = DecisionService._table_columns(db, "t_meeting_decision")
        if "mdc_expires_at" not in columns:
            db.execute("ALTER TABLE t_meeting_decision ADD COLUMN mdc_expires_at TEXT")
            columns.add("mdc_expires_at")
        if "mdc_status_changed_at" not in columns:
            db.execute("ALTER TABLE t_meeting_decision ADD COLUMN mdc_status_changed_at TEXT")
            columns.add("mdc_status_changed_at")
        if "mdc_context" not in columns:
            db.execute("ALTER TABLE t_meeting_decision ADD COLUMN mdc_context TEXT")
            columns.add("mdc_context")
        if "mdc_reason" not in columns:
            db.execute("ALTER TABLE t_meeting_decision ADD COLUMN mdc_reason TEXT")
            columns.add("mdc_reason")
        DecisionService._ensure_revision_table(db)
        if "mdc_machine_serial" in columns:
            rows = db.execute(
                "SELECT mdc_id, mdc_machine_serial, mdc_tags FROM t_meeting_decision WHERE COALESCE(mdc_machine_serial, '') <> ''"
            ).fetchall()
            for row in rows:
                merged_tags = DecisionService._normalize_tags(
                    [part for part in [row["mdc_tags"], row["mdc_machine_serial"]] if part not in (None, "")]
                )
                if merged_tags != (row["mdc_tags"] or ""):
                    db.execute("UPDATE t_meeting_decision SET mdc_tags = ? WHERE mdc_id = ?", (merged_tags, row["mdc_id"]))
        fts_row = db.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 't_meeting_decision_fts'"
        ).fetchone()
        fts_sql = str(fts_row[0] if fts_row else "").lower()
        if (
            "mdc_tags" not in fts_sql
            or "mdc_context" not in fts_sql
            or "mdc_reason" not in fts_sql
            or "mdc_machine_serial" in fts_sql
        ):
            DecisionService._rebuild_fts_artifacts(db)
        return columns

    @staticmethod
    def _ensure_revision_table(db) -> None:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS t_meeting_decision_revision (
                mdr_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mdr_decision_id INTEGER NOT NULL,
                mdr_title TEXT NOT NULL,
                mdr_body TEXT NOT NULL,
                mdr_updated_by INTEGER,
                mdr_updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mdr_decision_id) REFERENCES t_meeting_decision(mdc_id),
                FOREIGN KEY (mdr_updated_by) REFERENCES t_user(usr_id)
            )
            """
        )
        revision_cols = {row[1] for row in db.execute("PRAGMA table_info(t_meeting_decision_revision)").fetchall()}
        if "mdr_updated_by" not in revision_cols:
            db.execute("ALTER TABLE t_meeting_decision_revision ADD COLUMN mdr_updated_by INTEGER")
        if "mdr_updated_at" not in revision_cols:
            db.execute(
                "ALTER TABLE t_meeting_decision_revision ADD COLUMN mdr_updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
            )

    @staticmethod
    def _deleted_condition(db, alias: str = "", columns: Optional[set[str]] = None) -> str:
        cols = columns or DecisionService._decision_columns(db)
        if "mdc_deleted_at" not in cols:
            return "1 = 1"
        prefix = f"{alias}." if alias else ""
        return f"COALESCE({prefix}mdc_deleted_at, 0) = 0"

    @staticmethod
    def _ensure_deleted_column(db) -> set[str]:
        cols = DecisionService._decision_columns(db)
        if "mdc_deleted_at" not in cols:
            db.execute("ALTER TABLE t_meeting_decision ADD COLUMN mdc_deleted_at TEXT")
            cols.add("mdc_deleted_at")
        return cols

    @staticmethod
    def _meeting_expr(db, alias: str = "d") -> str:
        cols = DecisionService._decision_columns(db)
        prefix = f"{alias}." if alias else ""
        if {"mdc_meeting_id", "mdc_instance_id"}.issubset(cols):
            return f"COALESCE({prefix}mdc_meeting_id, {prefix}mdc_instance_id)"
        if "mdc_meeting_id" in cols:
            return f"{prefix}mdc_meeting_id"
        if "mdc_instance_id" in cols:
            return f"{prefix}mdc_instance_id"
        return "NULL"

    @staticmethod
    def _initial_status(db) -> str:
        """Return the status value supported by the current database schema."""
        ddl = DecisionService._decision_table_sql(db)
        return "Created" if "'Created'" in ddl else "Proposed"

    @staticmethod
    def _optional_column_expr(columns: set[str], column_name: str, alias: str = "d") -> str:
        return f"{alias}.{column_name}" if column_name in columns else f"NULL AS {column_name}"

    @staticmethod
    def _status_expr(columns: Optional[set[str]] = None, alias: str = "d") -> str:
        prefix = f"{alias}." if alias else ""
        inactive_values = ', '.join([repr(s) for s in sorted(DecisionService.LEGACY_INACTIVE_STATUSES | {DecisionService.INACTIVE_STATUS})])
        if columns and "mdc_deleted_at" in columns:
            return (
                f"CASE WHEN COALESCE({prefix}mdc_deleted_at, 0) <> 0 THEN '{DecisionService.INACTIVE_STATUS}' "
                f"WHEN {prefix}mdc_status IN ({inactive_values}) THEN '{DecisionService.INACTIVE_STATUS}' "
                f"ELSE '{DecisionService.ACTIVE_STATUS}' END"
            )
        return (
            f"CASE WHEN {prefix}mdc_status IN ({inactive_values}) THEN '{DecisionService.INACTIVE_STATUS}' "
            f"ELSE '{DecisionService.ACTIVE_STATUS}' END"
        )

    @staticmethod
    def _normalize_status(status: Optional[str]) -> str:
        normalized = str(status or DecisionService.ACTIVE_STATUS).strip().title()
        if normalized in DecisionService.STATUS_VALUES:
            return normalized
        if normalized in {"Cancelled", "Rejected", "Withdrawn", "Deleted", "Obsolete", "Expired"}:
            return DecisionService.INACTIVE_STATUS
        if normalized in {"Created", "Accepted", "Approved", "Implemented", "Reversed", "Posted", "Proposed"}:
            return DecisionService.ACTIVE_STATUS
        return DecisionService.ACTIVE_STATUS

    @staticmethod
    def _db_status(status: Optional[str]) -> str:
        normalized = DecisionService._normalize_status(status)
        return DecisionService.DB_ACTIVE_STATUS if normalized == DecisionService.ACTIVE_STATUS else DecisionService.DB_INACTIVE_STATUS

    @staticmethod
    def create_decision(data: Dict[str, Any], actor_id: int) -> int:
        """Create a new decision.
        
        Args:
            data: Dictionary with keys:
                - title (required)
                - body (optional)
                - status (optional, default 'Published')
                - meeting_id (required) - t_meeting_instance.min_id
                - category_id (optional) - primary category
                - secondary_category_id (optional) - secondary category
                - linked_action_id (optional)
                - tags (optional)
                - decided_at (optional)
                - created_by (legacy; ignored)
                
        Returns:
            Created decision ID.
            
        Raises:
            ValueError: If category validation fails.
        """
        db = get_db()
        cols = DecisionService._decision_columns(db)

        meeting_id = data.get("meeting_id")
        if meeting_id in (None, ""):
            raise ValueError("meeting_id is required")
        try:
            meeting_id = int(meeting_id)
        except (TypeError, ValueError):
            raise ValueError("meeting_id is required") from None
        
        # Validate secondary != primary if both provided
        category_id = data.get("category_id")
        secondary_category_id = data.get("secondary_category_id")
        if category_id and secondary_category_id and category_id == secondary_category_id:
            raise ValueError("Secondary category must differ from primary category")
        
        # Default category from meeting if not provided
        if not category_id:
            meeting_cols = {row[1] for row in db.execute("PRAGMA table_info(t_meeting_instance)").fetchall()}
            primary_expr = "COALESCE(min_category_id, min_topic_id) AS min_category_id" if {"min_category_id", "min_topic_id"}.intersection(meeting_cols) else ("min_category_id AS min_category_id" if "min_category_id" in meeting_cols else "min_topic_id AS min_category_id")
            secondary_expr = "min_secondary_category_id AS min_secondary_category_id" if "min_secondary_category_id" in meeting_cols else "NULL AS min_secondary_category_id"
            meeting = db.execute(
                f"SELECT {primary_expr}, {secondary_expr} FROM t_meeting_instance WHERE min_id = ?",
                (meeting_id,)
            ).fetchone()
            if meeting:
                category_id = meeting["min_category_id"]
                secondary_category_id = secondary_category_id or meeting["min_secondary_category_id"]
            else:
                raise ValueError("meeting not found")
        
        insert_columns = [
            "mdc_title", "mdc_body", "mdc_status", "mdc_meeting_id",
            "mdc_category_id", "mdc_secondary_category_id", "mdc_linked_action_id",
            "mdc_tags", "mdc_context", "mdc_reason", "mdc_decided_at", "mdc_expires_at", "mdc_created_by"
        ]
        insert_values = [
            data["title"],
            data.get("body", ""),
            DecisionService.DB_ACTIVE_STATUS,
            meeting_id,
            category_id,
            secondary_category_id,
            data.get("linked_action_id"),
            DecisionService._normalize_tags(data.get("tags", "")),
            data.get("context"),
            data.get("reason"),
            data.get("decided_at"),
            data.get("expires_at"),
            actor_id,
        ]
        if "mdc_instance_id" in cols:
            insert_columns.insert(4, "mdc_instance_id")
            insert_values.insert(4, meeting_id)

        query = """
        INSERT INTO t_meeting_decision ({columns}) VALUES ({placeholders})
        """.format(
            columns=", ".join(insert_columns),
            placeholders=", ".join(["?"] * len(insert_values)),
        )
        try:
            cursor = db.execute(query, insert_values)
        except sqlite3.DatabaseError as error:
            if not DecisionService._is_malformed_error(error):
                raise
            db.rollback()
            DecisionService._rebuild_fts_artifacts(db)
            cursor = db.execute(query, insert_values)
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_decision(decision_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a decision by ID with category info."""
        db = get_db()
        decision_cols = DecisionService._decision_columns(db)
        fields = [
            "d.mdc_id",
            "d.mdc_meeting_id",
            "d.mdc_title",
            "d.mdc_body",
            "d.mdc_context",
            "d.mdc_reason",
            "d.mdc_status AS mdc_status",
            "d.mdc_category_id",
            "d.mdc_secondary_category_id",
            DecisionService._optional_column_expr(decision_cols, "mdc_action_type_id"),
            "d.mdc_linked_action_id",
            "d.mdc_tags",
            "d.mdc_decided_at",
            "d.mdc_expires_at",
            "d.mdc_status_changed_at",
            "d.mdc_created_by",
            "d.mdc_created_at",
            "d.mdc_updated_at",
            "tp.top_name AS category_name",
            "tp2.top_name AS secondary_category_name",
            "u.usr_display_name AS creator_name",
            "(SELECT COUNT(*) FROM t_meeting_decision_revision rv WHERE rv.mdr_decision_id = d.mdc_id) AS revision_count",
            "(SELECT MAX(rv.mdr_updated_at) FROM t_meeting_decision_revision rv WHERE rv.mdr_decision_id = d.mdc_id) AS last_revised_at",
            "mi.min_title AS meeting_title",
            "COALESCE(mtg.mtg_title, mi.min_title) AS series_title",
            "mi.min_date AS occurrence_date",
        ]
        if "mdc_instance_id" in decision_cols:
            fields.insert(2, "d.mdc_instance_id")
        else:
            fields.insert(2, "NULL AS mdc_instance_id")
        if "mdc_deleted_at" in decision_cols:
            fields.append("d.mdc_deleted_at")
        else:
            fields.append("NULL AS mdc_deleted_at")
        meeting_expr = DecisionService._meeting_expr(db)
        query = f"""
        SELECT {', '.join(fields)}
        FROM t_meeting_decision d
             LEFT JOIN t_topic tp ON tp.top_id = d.mdc_category_id
             LEFT JOIN t_topic tp2 ON tp2.top_id = d.mdc_secondary_category_id
             LEFT JOIN t_user u ON u.usr_id = d.mdc_created_by
             LEFT JOIN t_meeting_instance mi ON mi.min_id = {meeting_expr}
             LEFT JOIN t_meeting mtg ON mtg.mtg_id = mi.min_meeting_id
        WHERE d.mdc_id = ?
        """
        row = db.execute(query, (decision_id,)).fetchone()
        if row:
            result = dict(row)
            result["mdc_status"] = DecisionService._normalize_status(result.get("mdc_status"))
            if result.get("mdc_deleted_at") not in (None, "", 0):
                result["mdc_status"] = DecisionService.INACTIVE_STATUS
            return result
        return None

    @staticmethod
    def list_decisions(
        search: Optional[str] = None,
        meeting_id: Optional[int] = None,
        series_id: Optional[int] = None,
        status: Optional[str] = None,
        action_id: Optional[int] = None,
        category_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        current_user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        include_total: bool = False,
    ) -> List[Dict[str, Any]] | tuple[List[Dict[str, Any]], int]:
        """List decisions with optional filters.
        
        Args:
            meeting_id: Filter by meeting instance
            series_id: Filter by meeting series (parent meeting id)
            status: Filter by status
            action_id: Filter by linked action
            category_id: Filter by category (matches primary OR secondary)
            owner_id: Filter by decision creator
            limit: Pagination limit
            offset: Pagination offset
            
        Returns:
            List of decision dictionaries.
        """
        db = get_db()
        decision_cols = DecisionService._decision_columns(db)
        meeting_expr = DecisionService._meeting_expr(db)
        join_params: list[object] = [current_user_id, current_user_id, current_user_id]
        select_parts = [
            "d.mdc_id",
            "d.mdc_meeting_id",
            "d.mdc_title",
            "d.mdc_body",
            "d.mdc_context",
            "d.mdc_reason",
            "d.mdc_status AS mdc_status",
            "d.mdc_category_id",
            "d.mdc_secondary_category_id",
            DecisionService._optional_column_expr(decision_cols, "mdc_action_type_id"),
            "d.mdc_linked_action_id",
            "d.mdc_tags",
            "d.mdc_decided_at",
            "d.mdc_expires_at",
            "d.mdc_status_changed_at",
            "d.mdc_created_by",
            "d.mdc_created_at",
            "d.mdc_updated_at",
            "a.act_team_id AS action_team_id",
            "tp.top_name AS category_name",
            "tp2.top_name AS secondary_category_name",
            "u.usr_display_name AS creator_name",
            "mi.min_title AS meeting_title",
            "COALESCE(mtg.mtg_title, mi.min_title) AS series_title",
            "CASE WHEN ? IS NOT NULL AND (d.mdc_created_by = ? OR mo.mow_user_id IS NOT NULL) THEN 1 ELSE 0 END AS can_manage",
            "(SELECT COUNT(*) FROM t_meeting_decision_revision rv WHERE rv.mdr_decision_id = d.mdc_id) AS revision_count",
            "(SELECT MAX(rv.mdr_updated_at) FROM t_meeting_decision_revision rv WHERE rv.mdr_decision_id = d.mdc_id) AS last_revised_at",
        ]
        if "mdc_instance_id" in decision_cols:
            select_parts.insert(2, "d.mdc_instance_id")
        else:
            select_parts.insert(2, "NULL AS mdc_instance_id")
        if "mdc_deleted_at" in decision_cols:
            select_parts.append("d.mdc_deleted_at")
        else:
            select_parts.append("NULL AS mdc_deleted_at")

        query = f"""
            SELECT {', '.join(select_parts)}
            FROM t_meeting_decision d
                 LEFT JOIN t_topic tp ON tp.top_id = d.mdc_category_id
                 LEFT JOIN t_topic tp2 ON tp2.top_id = d.mdc_secondary_category_id
                 LEFT JOIN t_user u ON u.usr_id = d.mdc_created_by
                 LEFT JOIN t_action a ON a.act_id = d.mdc_linked_action_id
                 LEFT JOIN t_meeting_instance mi ON mi.min_id = {meeting_expr}
                 LEFT JOIN t_meeting mtg ON mtg.mtg_id = mi.min_meeting_id
                 LEFT JOIN t_meeting_owner mo ON mo.mow_instance_id = mi.min_id AND mo.mow_user_id = ?
            WHERE {DecisionService._deleted_condition(db, columns=decision_cols)}
            ORDER BY d.mdc_created_at DESC
        """
        rows = [dict(row) for row in db.execute(query, join_params).fetchall()]

        # Pre-fetch series instance IDs if filtering by series
        series_instance_ids: set | None = None
        if series_id is not None:
            series_rows = db.execute(
                "SELECT min_id FROM t_meeting_instance WHERE min_meeting_id = ?",
                (series_id,),
            ).fetchall()
            series_instance_ids = {r["min_id"] for r in series_rows}

        search_term = str(search or "").strip().lower()

        def _matches(row: Dict[str, Any]) -> bool:
            row_status = DecisionService._normalize_status(row.get("mdc_status"))
            if row.get("mdc_deleted_at") not in (None, "", 0):
                row_status = DecisionService.INACTIVE_STATUS
            if meeting_id is not None:
                row_meeting_id = row.get("mdc_meeting_id") or row.get("mdc_instance_id")
                if row_meeting_id != meeting_id:
                    return False
            if series_instance_ids is not None:
                row_meeting_id = row.get("mdc_meeting_id") or row.get("mdc_instance_id")
                if row_meeting_id not in series_instance_ids:
                    return False
            if status is not None and row_status != DecisionService._normalize_status(status):
                return False
            if action_id is not None and row.get("mdc_linked_action_id") != action_id:
                return False
            if category_id is not None and row.get("mdc_category_id") != category_id and row.get("mdc_secondary_category_id") != category_id:
                return False
            if owner_id is not None and row.get("mdc_created_by") != owner_id:
                return False
            if search_term:
                haystack = " ".join(
                    str(row.get(key) or "")
                    for key in ("mdc_title", "mdc_body", "mdc_context", "mdc_reason", "mdc_tags")
                ).lower()
                if search_term not in haystack:
                    return False
            row["mdc_status"] = row_status
            return True

        filtered_rows = [row for row in rows if _matches(row)]
        total = len(filtered_rows)
        paged_rows = filtered_rows[offset: offset + limit]
        if include_total:
            return paged_rows, total
        return paged_rows

    @staticmethod
    def _update_decision_once(db, decision_id: int, data: Dict[str, Any], actor_id: Optional[int] = None) -> bool:
        cols = DecisionService._decision_columns(db)
        deleted_condition = DecisionService._deleted_condition(db)
        meeting_select = ["mdc_meeting_id"]
        if "mdc_instance_id" in cols:
            meeting_select.append("mdc_instance_id")
        current = db.execute(
            f"SELECT {', '.join(meeting_select)} FROM t_meeting_decision WHERE mdc_id = ? AND {deleted_condition}",
            (decision_id,),
        ).fetchone()
        if not current:
            return False

        meeting_id = data.get("meeting_id")
        
        # Validate secondary != primary if both provided
        category_id = data.get("category_id")
        secondary_category_id = data.get("secondary_category_id")
        if category_id and secondary_category_id and category_id == secondary_category_id:
            raise ValueError("Secondary category must differ from primary category")

        status = DecisionService._db_status(data.get("status")) if data.get("status") is not None else None
        existing = db.execute(
            f"SELECT mdc_title, mdc_body, mdc_tags, mdc_context, mdc_reason FROM t_meeting_decision WHERE mdc_id = ? AND {deleted_condition}",
            (decision_id,),
        ).fetchone()

        new_title = data.get("title") if data.get("title") is not None else (existing["mdc_title"] if existing else None)
        new_body = data.get("body") if data.get("body") is not None else (existing["mdc_body"] if existing else None)

        if not str(new_title or "").strip():
            raise ValueError("title is required")
        if new_body is None:
            raise ValueError("body is required")

        changed_content = bool(
            existing and (
                str(new_title) != str(existing["mdc_title"])
                or str(new_body) != str(existing["mdc_body"])
            )
        )

        if changed_content:
            db.execute(
                """
                INSERT INTO t_meeting_decision_revision
                    (mdr_decision_id, mdr_title, mdr_body, mdr_updated_by, mdr_updated_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (decision_id, existing["mdc_title"], existing["mdc_body"], actor_id),
            )

        tags = (
            DecisionService._normalize_tags(data.get("tags", ""))
            if "tags" in data
            else (DecisionService._normalize_tags(existing["mdc_tags"]) if existing else "")
        )
        
        assignments: list[str] = ["mdc_title = ?", "mdc_body = ?"]
        values: list[Any] = [new_title, new_body]

        if "status" in data:
            assignments.append("mdc_status = ?")
            values.append(status or DecisionService.DB_ACTIVE_STATUS)

        if "meeting_id" in data:
            assignments.append("mdc_meeting_id = ?")
            values.append(meeting_id)
            if "mdc_instance_id" in cols:
                assignments.append("mdc_instance_id = ?")
                values.append(meeting_id)

        if "category_id" in data:
            assignments.append("mdc_category_id = ?")
            values.append(category_id)

        if "secondary_category_id" in data:
            assignments.append("mdc_secondary_category_id = ?")
            values.append(secondary_category_id)

        if "linked_action_id" in data:
            assignments.append("mdc_linked_action_id = ?")
            values.append(data.get("linked_action_id"))

        if "tags" in data:
            assignments.append("mdc_tags = ?")
            values.append(tags)

        if "context" in data:
            assignments.append("mdc_context = ?")
            values.append(data.get("context"))

        if "reason" in data:
            assignments.append("mdc_reason = ?")
            values.append(data.get("reason"))

        if "decided_at" in data:
            assignments.append("mdc_decided_at = ?")
            values.append(data.get("decided_at"))

        if "expires_at" in data:
            assignments.append("mdc_expires_at = ?")
            values.append(data.get("expires_at"))

        assignments.append("mdc_updated_at = datetime('now')")
        query = f"UPDATE t_meeting_decision SET {', '.join(assignments)} WHERE mdc_id = ?"
        values.append(decision_id)

        cursor = db.execute(query, tuple(values))
        db.commit()
        return cursor.rowcount > 0

    @staticmethod
    def update_decision(decision_id: int, data: Dict[str, Any], actor_id: Optional[int] = None) -> bool:
        """Update an existing decision.

        Args:
            decision_id: Decision ID to update
            data: Dictionary with optional keys:
                - title, body, status
                - category_id, secondary_category_id
                - linked_action_id, tags, decided_at

        Returns:
            True if updated, False otherwise.

        Raises:
            ValueError: If category validation fails.
        """
        db = get_db()
        try:
            return DecisionService._update_decision_once(db, decision_id, data, actor_id=actor_id)
        except sqlite3.DatabaseError as error:
            if not DecisionService._is_malformed_error(error):
                raise
            db.rollback()
            DecisionService._rebuild_fts_artifacts(db)
            return DecisionService._update_decision_once(db, decision_id, data, actor_id=actor_id)

    @staticmethod
    def transition_status(decision_id: int, new_status: str, user_id: int) -> Dict[str, Any]:
        """Transition decision status following FSM rules.
        
        Args:
            decision_id: Decision ID
            new_status: Target status
            user_id: User performing the transition
            
        Returns:
            Dict with success status and error message if applicable.
        """
        db = get_db()
        
        # Get current decision
        decision = db.execute(
            f"SELECT mdc_status FROM t_meeting_decision WHERE mdc_id = ? AND {DecisionService._deleted_condition(db)}",
            (decision_id,)
        ).fetchone()
        
        if not decision:
            return {"success": False, "error": "Decision not found"}
        
        current_status = decision["mdc_status"]
        
        current_status = DecisionService._normalize_status(current_status)
        new_status = DecisionService._normalize_status(new_status)

        # Check FSM validity
        valid_transitions = DecisionService.STATUS_FSM.get(current_status, [])
        if new_status not in valid_transitions:
            return {
                "success": False,
                "error": f"Invalid transition from {current_status} to {new_status}",
                "valid_transitions": valid_transitions
            }
        
        # Apply transition
        status_db = DecisionService._db_status(new_status)
        try:
            if new_status == DecisionService.INACTIVE_STATUS:
                db.execute(
                    """
                    UPDATE t_meeting_decision
                    SET mdc_status = ?,
                        mdc_expires_at = COALESCE(mdc_expires_at, datetime('now')),
                        mdc_status_changed_at = datetime('now'),
                        mdc_updated_at = datetime('now')
                    WHERE mdc_id = ?
                    """,
                    (status_db, decision_id)
                )
            else:
                db.execute(
                    """
                    UPDATE t_meeting_decision
                    SET mdc_status = ?,
                        mdc_status_changed_at = datetime('now'),
                        mdc_updated_at = datetime('now')
                    WHERE mdc_id = ?
                    """,
                    (status_db, decision_id)
                )
        except sqlite3.DatabaseError as error:
            if not DecisionService._is_malformed_error(error):
                raise
            db.rollback()
            DecisionService._rebuild_fts_artifacts(db)
            if new_status == DecisionService.INACTIVE_STATUS:
                db.execute(
                    """
                    UPDATE t_meeting_decision
                    SET mdc_status = ?,
                        mdc_expires_at = COALESCE(mdc_expires_at, datetime('now')),
                        mdc_status_changed_at = datetime('now'),
                        mdc_updated_at = datetime('now')
                    WHERE mdc_id = ?
                    """,
                    (status_db, decision_id)
                )
            else:
                db.execute(
                    """
                    UPDATE t_meeting_decision
                    SET mdc_status = ?,
                        mdc_status_changed_at = datetime('now'),
                        mdc_updated_at = datetime('now')
                    WHERE mdc_id = ?
                    """,
                    (status_db, decision_id)
                )
        db.commit()
        
        return {"success": True, "new_status": new_status}

    @staticmethod
    def get_revisions(decision_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        db = get_db()
        DecisionService._ensure_revision_table(db)
        rows = db.execute(
            """
            SELECT
                rv.mdr_id,
                rv.mdr_decision_id,
                rv.mdr_title,
                rv.mdr_body,
                rv.mdr_updated_by,
                rv.mdr_updated_at,
                COALESCE(u.usr_display_name, '-') AS updated_by_name
            FROM t_meeting_decision_revision rv
            LEFT JOIN t_user u ON u.usr_id = rv.mdr_updated_by
            WHERE rv.mdr_decision_id = ?
            ORDER BY rv.mdr_updated_at DESC, rv.mdr_id DESC
            LIMIT ?
            """,
            (decision_id, max(1, min(int(limit), 200))),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def delete_decision(decision_id: int) -> bool:
        """Soft-delete a decision."""
        db = get_db()
        cols = DecisionService._ensure_deleted_column(db)
        if "mdc_deleted_at" in cols:
            db.execute(
                "UPDATE t_meeting_decision SET mdc_deleted_at = datetime('now') WHERE mdc_id = ?",
                (decision_id,)
            )
        else:
            db.execute(
                "UPDATE t_meeting_decision SET mdc_status = ? WHERE mdc_id = ?",
                (DecisionService.DB_INACTIVE_STATUS, decision_id)
            )
        db.commit()
        return True

    @staticmethod
    def search_decisions(query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search decisions using FTS5."""
        db = get_db()
        search_query = """
            SELECT fts.rowid as mdc_id, fts.mdc_title, fts.mdc_body, fts.mdc_context, fts.mdc_reason, fts.mdc_tags, d.mdc_status AS mdc_status
            FROM t_meeting_decision_fts fts
            JOIN t_meeting_decision d ON d.mdc_id = fts.rowid
            WHERE fts MATCH ? AND {deleted_condition}
            LIMIT ?
        """.format(deleted_condition=DecisionService._deleted_condition(db, columns=DecisionService._decision_columns(db)))
        rows = db.execute(search_query, (query, limit)).fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            result = dict(row)
            result["mdc_status"] = DecisionService._normalize_status(result.get("mdc_status"))
            results.append(result)
        return results

    @staticmethod
    def count_by_status() -> Dict[str, int]:
        """Count decisions grouped by status."""
        db = get_db()
        decision_cols = DecisionService._decision_columns(db)
        deleted_field = "d.mdc_deleted_at" if "mdc_deleted_at" in decision_cols else "NULL AS mdc_deleted_at"
        rows = db.execute(f"SELECT mdc_status, {deleted_field} FROM t_meeting_decision d").fetchall()
        counts: Dict[str, int] = {DecisionService.ACTIVE_STATUS: 0, DecisionService.INACTIVE_STATUS: 0}
        for row in rows:
            status = DecisionService._normalize_status(row["mdc_status"])
            if "mdc_deleted_at" in row.keys() and row["mdc_deleted_at"] not in (None, "", 0):
                status = DecisionService.INACTIVE_STATUS
            counts[status] = counts.get(status, 0) + 1
        return {key: value for key, value in counts.items() if value}

    @staticmethod
    def count_by_meeting(meeting_id: int) -> int:
        """Count decisions for a specific meeting."""
        db = get_db()
        meeting_cols = DecisionService._decision_columns(db)
        meeting_expr = "COALESCE(mdc_meeting_id, mdc_instance_id)" if {"mdc_meeting_id", "mdc_instance_id"}.issubset(meeting_cols) else ("mdc_meeting_id" if "mdc_meeting_id" in meeting_cols else "mdc_instance_id")
        query = f"SELECT COUNT(*) as cnt FROM t_meeting_decision WHERE {meeting_expr} = ? AND {DecisionService._deleted_condition(db)}"
        row = db.execute(query, (meeting_id,)).fetchone()
        return row["cnt"] if row else 0

    @staticmethod
    def count_by_category(category_id: int) -> int:
        """Count decisions for a specific category (primary or secondary)."""
        db = get_db()
        query = f"""
        SELECT COUNT(*) as cnt FROM t_meeting_decision 
        WHERE (mdc_category_id = ? OR mdc_secondary_category_id = ?) 
        AND {DecisionService._deleted_condition(db)}
        """
        row = db.execute(query, (category_id, category_id)).fetchone()
        return row["cnt"] if row else 0
