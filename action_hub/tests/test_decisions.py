"""Tests for Meeting Decisions API (P8)."""
import sqlite3
from unittest.mock import patch

from actionhub.decisions.service import DecisionService
from tests.conftest import AppTestCase


class TestDecisionsAPI(AppTestCase):
    """Test cases for decisions endpoints."""

    def setUp(self):
        super().setUp()
        self.login_admin()

    def test_create_decision(self):
        """Test creating a new decision."""
        # First create a meeting instance to link the decision to
        db = self.get_db()
        admin_row = db.execute("SELECT usr_id FROM t_user WHERE usr_username = ?", ("admin",)).fetchone()
        admin_id = int(admin_row["usr_id"])
        primary_topic_id = db.execute("""
            INSERT INTO t_topic (top_code, top_name)
            VALUES ('AAA', 'Category A')
        """).lastrowid
        secondary_topic_id = db.execute("""
            INSERT INTO t_topic (top_code, top_name)
            VALUES ('BBB', 'Category B')
        """).lastrowid
        db.execute(
            "INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by) VALUES (?, ?, ?)",
            (1, "Test Meeting", admin_id),
        )
        db.execute(
            "INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "Test Meeting Instance", 1, admin_id),
        )
        db.commit()

        # Create a decision
        data = {
            "title": "Test Decision",
            "body": "This is a test decision body",
            "context": "Supplier delay trend in Q1",
            "reason": "Reduce lead time risk",
            "meeting_id": 1,
            "tags": "test, decision",
            "status": "Published",
            "category_id": primary_topic_id,
            "secondary_category_id": secondary_topic_id,
        }
        response = self.client.post("/api/decisions/", json=data)
        self.assertEqual(response.status_code, 201)
        self.assertIn("data", response.json)
        self.assertIn("id", response.json["data"])

        row = db.execute(
            "SELECT mdc_created_by, mdc_category_id, mdc_secondary_category_id, mdc_tags, mdc_context, mdc_reason FROM t_meeting_decision WHERE mdc_id = ?",
            (response.json["data"]["id"],),
        ).fetchone()
        self.assertEqual(row["mdc_created_by"], admin_id)
        self.assertEqual(row["mdc_category_id"], primary_topic_id)
        self.assertEqual(row["mdc_secondary_category_id"], secondary_topic_id)
        self.assertEqual(row["mdc_tags"], "TEST, DECISION")
        self.assertEqual(row["mdc_context"], "Supplier delay trend in Q1")
        self.assertEqual(row["mdc_reason"], "Reduce lead time risk")

    def test_get_decision(self):
        """Test retrieving a specific decision."""
        # Create test data
        db = self.get_db()
        db.execute("""
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by)
            VALUES (1, 'Test Meeting', 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by)
            VALUES (1, 1, 'Test Meeting Instance', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Test Decision', 'Body', 'Proposed', 1, 1)
        """)
        db.commit()

        # Get the decision
        response = self.client.get("/api/decisions/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["mdc_title"], "Test Decision")
        self.assertEqual(response.json["data"]["mdc_status"], "Published")

    def test_list_decisions(self):
        """Test listing decisions with filters."""
        # Create test data
        db = self.get_db()
        db.execute("""
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by)
            VALUES (1, 'Test Meeting', 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by)
            VALUES (1, 1, 'Test Meeting Instance', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_owner (mow_instance_id, mow_user_id, mow_granted_by)
            VALUES (1, 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Decision 1', 'Body 1', 'Proposed', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Decision 2', 'Body 2', 'Deleted', 1, 1)
        """)
        db.commit()

        # List all decisions
        response = self.client.get("/api/decisions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["data"]), 2)

        # Filter by status
        response = self.client.get("/api/decisions/?status=Published")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["data"]), 1)
        self.assertEqual(response.json["data"][0]["mdc_status"], "Published")

    def test_list_decisions_searches_tags(self):
        db = self.get_db()
        db.execute("""
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by)
            VALUES (1, 'Test Meeting', 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by)
            VALUES (1, 1, 'Test Meeting Instance', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_tags, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Decision 1', 'Body 1', 'MAINTENANCE, LINE3', 'Proposed', 1, 1)
        """)
        db.commit()

        response = self.client.get("/api/decisions/?search=LINE3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["data"]), 1)
        self.assertEqual(response.json["data"][0]["mdc_tags"], "MAINTENANCE, LINE3")

    def test_list_decisions_searches_context_and_reason(self):
        db = self.get_db()
        db.execute("""
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by)
            VALUES (1, 'Test Meeting', 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by)
            VALUES (1, 1, 'Test Meeting Instance', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (
                mdc_title, mdc_body, mdc_context, mdc_reason, mdc_status, mdc_meeting_id, mdc_created_by
            )
            VALUES (
                'Decision 1',
                'Body 1',
                'Quarterly supplier delays in East region',
                'Switching vendor improves reliability despite small cost increase',
                'Proposed',
                1,
                1
            )
        """)
        db.commit()

        response_context = self.client.get("/api/decisions/?search=East")
        self.assertEqual(response_context.status_code, 200)
        self.assertEqual(len(response_context.json["data"]), 1)
        self.assertEqual(response_context.json["data"][0]["mdc_context"], "Quarterly supplier delays in East region")

        response_reason = self.client.get("/api/decisions/?search=reliability")
        self.assertEqual(response_reason.status_code, 200)
        self.assertEqual(len(response_reason.json["data"]), 1)
        self.assertEqual(
            response_reason.json["data"][0]["mdc_reason"],
            "Switching vendor improves reliability despite small cost increase",
        )

    def test_update_decision(self):
        """Test updating a decision."""
        # Create test data
        db = self.get_db()
        primary_topic_id = db.execute("""
            INSERT INTO t_topic (top_code, top_name)
            VALUES ('AAA', 'Category A')
        """).lastrowid
        secondary_topic_id = db.execute("""
            INSERT INTO t_topic (top_code, top_name)
            VALUES ('BBB', 'Category B')
        """).lastrowid
        db.execute("""
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by)
            VALUES (1, 'Test Meeting', 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by)
            VALUES (1, 1, 'Test Meeting Instance', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Test Decision', 'Body', 'Proposed', 1, 1)
        """)
        db.commit()

        # Update the decision
        data = {
            "title": "Updated Title",
            "body": "Body",
            "context": "Updated operational context",
            "reason": "Updated rationale",
            "tags": "late, production",
            "status": "Expired",
            "category_id": primary_topic_id,
            "secondary_category_id": secondary_topic_id,
        }
        response = self.client.put("/api/decisions/1", json=data)
        self.assertEqual(response.status_code, 200)

        # Verify update
        response = self.client.get("/api/decisions/1")
        self.assertEqual(response.json["data"]["mdc_title"], "Updated Title")
        self.assertEqual(response.json["data"]["mdc_category_id"], primary_topic_id)
        self.assertEqual(response.json["data"]["mdc_secondary_category_id"], secondary_topic_id)
        self.assertEqual(response.json["data"]["mdc_tags"], "LATE, PRODUCTION")
        self.assertEqual(response.json["data"]["mdc_context"], "Updated operational context")
        self.assertEqual(response.json["data"]["mdc_reason"], "Updated rationale")

    def test_update_decision_accepts_usr_id_when_id_is_missing(self):
        """Update should not 500 when auth payload carries usr_id instead of id."""
        db = self.get_db()
        db.execute("""
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by)
            VALUES (1, 'Auth Shape Meeting', 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by)
            VALUES (1, 1, 'Auth Shape Instance', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Auth Shape Decision', 'Body', 'Proposed', 1, 1)
        """)
        db.commit()

        with patch("actionhub.decisions.routes.get_request_user", return_value={"id": None, "usr_id": 1, "role": "Admin"}):
            response = self.client.patch("/api/decisions/1", json={"title": "Updated by usr_id"})

        self.assertEqual(response.status_code, 200)
        updated = self.client.get("/api/decisions/1")
        self.assertEqual(updated.get_json()["data"]["mdc_title"], "Updated by usr_id")

    def test_update_decision_handles_database_malformed_error(self):
        """Update should return structured DB corruption error instead of generic 500."""
        db = self.get_db()
        db.execute(
            """
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by)
            VALUES (1, 'Test Meeting', 1)
            """
        )
        db.execute(
            """
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by)
            VALUES (1, 1, 'Test Meeting Instance', 1, 1)
            """
        )
        db.execute(
            """
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Test Decision', 'Body', 'Proposed', 1, 1)
            """
        )
        db.commit()

        with patch(
            "actionhub.decisions.routes.DecisionService.update_decision",
            side_effect=sqlite3.DatabaseError("database disk image is malformed"),
        ):
            response = self.client.patch("/api/decisions/1", json={"title": "Updated"})

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertEqual(payload["error"]["code"], "DATABASE_CORRUPTION")

    def test_delete_decision_forbidden(self):
        """Decision deletion is forbidden by policy."""
        # Create test data
        db = self.get_db()
        db.execute("""
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by)
            VALUES (1, 'Test Meeting', 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by)
            VALUES (1, 1, 'Test Meeting Instance', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Test Decision', 'Body', 'Proposed', 1, 1)
        """)
        db.commit()

        # Delete the decision
        response = self.client.delete("/api/decisions/1")
        self.assertEqual(response.status_code, 403)

    def test_decision_status_transition(self):
        """Test decision status lifecycle transition."""
        # Create test data
        db = self.get_db()
        db.execute("""
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by)
            VALUES (1, 'Test Meeting', 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by)
            VALUES (1, 1, 'Test Meeting Instance', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Test Decision', 'Body', 'Proposed', 1, 1)
        """)
        db.commit()

        # Valid transition: Published -> Expired
        response = self.client.patch("/api/decisions/1/status", json={"status": "Expired", "user_id": 1})
        self.assertEqual(response.status_code, 200)

        # Verify transition
        response = self.client.get("/api/decisions/1")
        self.assertEqual(response.json["data"]["mdc_status"], "Expired")

    def test_decision_status_invalid_transition(self):
        """Test that invalid status transitions are rejected."""
        # Create test data
        db = self.get_db()
        db.execute("""
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by)
            VALUES (1, 'Test Meeting', 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by)
            VALUES (1, 1, 'Test Meeting Instance', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Test Decision', 'Body', 'Proposed', 1, 1)
        """)
        db.commit()

        # Invalid transition: Published -> Published (not allowed)
        response = self.client.patch("/api/decisions/1/status", json={"status": "Published", "user_id": 1})
        self.assertEqual(response.status_code, 400)

    def test_meeting_decisions_endpoint(self):
        """Test meeting-scoped decisions endpoint."""
        # Create test data
        db = self.get_db()
        admin_row = db.execute("SELECT usr_id FROM t_user WHERE usr_username = ?", ("admin",)).fetchone()
        admin_id = int(admin_row["usr_id"])
        db.execute("""
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by)
            VALUES (1, 'Test Meeting', 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by)
            VALUES (1, 1, 'Test Meeting Instance', 1, 1)
        """)
        db.execute(
            "INSERT INTO t_meeting_owner (mow_instance_id, mow_user_id, mow_granted_by) VALUES (?, ?, ?)",
            (1, admin_id, admin_id),
        )
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Decision 1', 'Body 1', 'Proposed', 1, 1)
        """)
        db.commit()

        # Get decisions for meeting
        response = self.client.get("/api/meetings/1/decisions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["data"]), 1)

    def test_decision_counts(self):
        """Test decision counts endpoint."""
        # Create test data
        db = self.get_db()
        db.execute("""
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by)
            VALUES (1, 'Test Meeting', 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by)
            VALUES (1, 1, 'Test Meeting Instance', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Decision 1', 'Body 1', 'Proposed', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Decision 2', 'Body 2', 'Proposed', 1, 1)
        """)
        db.execute("""
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES ('Decision 3', 'Body 3', 'Deleted', 1, 1)
        """)
        db.commit()

        # Get counts
        response = self.client.get("/api/decisions/counts")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["Published"], 2)
        self.assertEqual(response.json["Expired"], 1)

    def test_create_decision_repairs_legacy_category_fk_schema(self):
        """Creating a decision should repair legacy decision category FK drift."""
        db = self.get_db()
        db.execute("DROP TRIGGER IF EXISTS t_meeting_decision_ai")
        db.execute("DROP TRIGGER IF EXISTS t_meeting_decision_ad")
        db.execute("DROP TRIGGER IF EXISTS t_meeting_decision_au")
        db.execute("DROP TRIGGER IF EXISTS trg_meeting_decision_fts")
        db.execute("DROP TRIGGER IF EXISTS trg_meeting_decision_fts_update")
        db.execute("DROP TRIGGER IF EXISTS trg_meeting_decision_fts_delete")
        db.execute("DROP INDEX IF EXISTS idx_decision_secondary_category")
        db.execute("DROP TABLE IF EXISTS t_meeting_decision_fts")
        db.execute("DROP TABLE IF EXISTS t_meeting_decision")
        db.execute(
            """
            CREATE TABLE t_meeting_decision (
                mdc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mdc_title TEXT NOT NULL,
                mdc_body TEXT NOT NULL,
                mdc_status TEXT NOT NULL DEFAULT 'Proposed',
                mdc_meeting_id INTEGER NOT NULL REFERENCES t_meeting_instance(min_id),
                mdc_business_theme_id INTEGER REFERENCES t_topic(top_id),
                mdc_linked_action_id INTEGER REFERENCES t_action(act_id),
                mdc_tags TEXT,
                mdc_decided_at DATETIME DEFAULT NULL,
                mdc_created_by INTEGER NOT NULL REFERENCES t_user(usr_id),
                mdc_created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                mdc_updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
                mdc_category_id INTEGER REFERENCES t_category(cat_id),
                mdc_secondary_category_id INTEGER REFERENCES t_topic(top_id),
                UNIQUE(mdc_meeting_id, mdc_title)
            )
            """
        )
        db.execute(
            """
            INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by, mtg_topic_id)
            VALUES (1, 'Legacy Meeting', 1, 1)
            """
        )
        db.execute(
            """
            INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_category_id, min_created_by)
            VALUES (1, 1, 'Legacy Meeting Instance', 1, 1, 1)
            """
        )
        db.commit()

        response = self.client.post(
            "/api/decisions/",
            json={"title": "Decision From Occurrence", "body": "Body", "meeting_id": 1},
        )

        self.assertEqual(response.status_code, 201)

        fks = {
            (row[3], row[2], row[4])
            for row in db.execute("PRAGMA foreign_key_list(t_meeting_decision)").fetchall()
        }
        self.assertIn(("mdc_category_id", "t_topic", "top_id"), fks)
        self.assertIn(("mdc_action_type_id", "t_category", "cat_id"), fks)

        row = db.execute(
            "SELECT mdc_meeting_id, mdc_instance_id, mdc_category_id FROM t_meeting_decision WHERE mdc_id = ?",
            (response.json["data"]["id"],),
        ).fetchone()
        self.assertEqual(row["mdc_meeting_id"], 1)
        self.assertEqual(row["mdc_instance_id"], 1)
        self.assertEqual(row["mdc_category_id"], 1)

    def test_list_decisions_filters_by_owner_id(self):
        """List endpoint should support owner_id filter (decision creator)."""
        db = self.get_db()
        user1 = db.execute("SELECT usr_id FROM t_user WHERE usr_username = ?", ("user1",)).fetchone()
        self.assertIsNotNone(user1)
        user1_id = int(user1["usr_id"])

        db.execute("INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by) VALUES (1, 'Owner Filter Meeting', 1)")
        db.execute("INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by) VALUES (1, 1, 'Owner Filter Instance', 1, 1)")
        db.execute("INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by) VALUES ('By Admin', 'A', 'Proposed', 1, 1)")
        db.execute("INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by) VALUES ('By User1', 'B', 'Proposed', 1, ?)", (user1_id,))
        db.commit()

        response = self.client.get(f"/api/decisions/?owner_id={user1_id}")
        self.assertEqual(response.status_code, 200)
        items = response.get_json()["data"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["mdc_title"], "By User1")

    def test_list_decisions_team_projects_only_param_ignored(self):
        """team_projects_only param is no longer supported; all decisions are returned regardless."""
        db = self.get_db()
        user1 = db.execute("SELECT usr_id FROM t_user WHERE usr_username = ?", ("user1",)).fetchone()
        self.assertIsNotNone(user1)
        user1_id = int(user1["usr_id"])
        user2_id = db.execute(
            """
            INSERT INTO t_user (usr_username, usr_employee_id, usr_pwd_hash, usr_display_name, usr_email, usr_role, usr_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            ("outsider_decision", "999901", "hash", "Outsider Decision", "outsider_decision@example.com", "Member"),
        ).lastrowid

        team_id = db.execute(
            "INSERT INTO t_team (tea_code, tea_name_en, tea_active) VALUES (?, ?, 1)",
            ("TMP", "Temp Team"),
        ).lastrowid
        db.execute("INSERT OR IGNORE INTO t_user_team (utm_user_id, utm_team_id) VALUES (?, ?)", (user1_id, team_id))
        db.execute("INSERT OR IGNORE INTO t_user_team (utm_user_id, utm_team_id) VALUES (?, ?)", (1, team_id))

        db.execute("INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by) VALUES (1, 'Team Scope Meeting', 1)")
        db.execute("INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by) VALUES (1, 1, 'Team Scope Instance', 1, 1)")

        db.execute(
            "INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by) VALUES ('Team Decision', 'A', 'Proposed', 1, ?)",
            (user1_id,),
        )
        db.execute(
            "INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by) VALUES ('Other Team Decision', 'B', 'Proposed', 1, ?)",
            (user2_id,),
        )
        db.commit()

        # team_projects_only is now ignored — all decisions visible
        response = self.client.get("/api/decisions/?team_projects_only=true")
        self.assertEqual(response.status_code, 200)
        items = response.get_json()["data"]
        titles = {item["mdc_title"] for item in items}
        self.assertIn("Team Decision", titles)
        self.assertIn("Other Team Decision", titles)

    def test_non_admin_cannot_mark_decision_expired(self):
        """Only Admin can transition decision status."""
        db = self.get_db()
        user1 = db.execute("SELECT usr_id FROM t_user WHERE usr_username = ?", ("user1",)).fetchone()
        self.assertIsNotNone(user1)
        user1_id = int(user1["usr_id"])

        db.execute("INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by) VALUES (1, 'Obsolete Permission Meeting', 1)")
        db.execute("INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by) VALUES (1, 1, 'Obsolete Permission Instance', 1, 1)")
        db.execute("INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by) VALUES ('Status Guard', 'A', 'Proposed', 1, ?)", (user1_id,))
        db.commit()

        self.login_user()
        response = self.client.patch("/api/decisions/1/status", json={"status": "Expired"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("Only admin", response.get_json()["error"]["message"])

    def test_decision_body_update_creates_revision(self):
        """Decision owner can revise body/title and the previous snapshot is tracked."""
        db = self.get_db()
        db.execute("INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by) VALUES (1, 'Revision Meeting', 1)")
        db.execute("INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by) VALUES (1, 1, 'Revision Instance', 1, 1)")
        db.execute("INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by) VALUES ('Original Title', 'Original Body', 'Proposed', 1, 1)")
        db.commit()

        response = self.client.put("/api/decisions/1", json={"title": "Updated Title", "body": "Updated Body"})
        self.assertEqual(response.status_code, 200)

        updated = db.execute("SELECT mdc_title, mdc_body, mdc_updated_at FROM t_meeting_decision WHERE mdc_id = 1").fetchone()
        self.assertEqual(updated["mdc_title"], "Updated Title")
        self.assertEqual(updated["mdc_body"], "Updated Body")
        self.assertIsNotNone(updated["mdc_updated_at"])

        revision = db.execute(
            "SELECT mdr_title, mdr_body FROM t_meeting_decision_revision WHERE mdr_decision_id = ? ORDER BY mdr_id DESC LIMIT 1",
            (1,),
        ).fetchone()
        self.assertIsNotNone(revision)
        self.assertEqual(revision["mdr_title"], "Original Title")
        self.assertEqual(revision["mdr_body"], "Original Body")

    def test_update_decision_repairs_legacy_revision_table_columns(self):
        """Updating a decision should succeed even if legacy revision table misses audit columns."""
        db = self.get_db()
        db.execute("DROP TABLE IF EXISTS t_meeting_decision_revision")
        db.execute(
            """
            CREATE TABLE t_meeting_decision_revision (
                mdr_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mdr_decision_id INTEGER NOT NULL,
                mdr_title TEXT NOT NULL,
                mdr_body TEXT NOT NULL,
                FOREIGN KEY (mdr_decision_id) REFERENCES t_meeting_decision(mdc_id)
            )
            """
        )
        db.execute("INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by) VALUES (1, 'Legacy Revision Meeting', 1)")
        db.execute("INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by) VALUES (1, 1, 'Legacy Revision Instance', 1, 1)")
        db.execute("INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by) VALUES ('Original Title', 'Original Body', 'Proposed', 1, 1)")
        db.commit()

        response = self.client.patch("/api/decisions/1", json={"title": "Updated Title", "body": "Updated Body"})
        self.assertEqual(response.status_code, 200)

        revision_cols = {row["name"] for row in db.execute("PRAGMA table_info(t_meeting_decision_revision)").fetchall()}
        self.assertIn("mdr_updated_by", revision_cols)
        self.assertIn("mdr_updated_at", revision_cols)

    def test_update_decision_rebuilds_fts_after_malformed_error(self):
        """Malformed decision search artifacts should be rebuilt and the update retried once."""
        db = self.get_db()
        db.execute("INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by) VALUES (1, 'Repair Meeting', 1)")
        db.execute("INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by) VALUES (1, 1, 'Repair Instance', 1, 1)")
        db.execute("INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by) VALUES ('Original Title', 'Original Body', 'Proposed', 1, 1)")
        db.commit()

        with self.app.app_context():
            with patch.object(
                DecisionService,
                "_update_decision_once",
                side_effect=[sqlite3.DatabaseError("database disk image is malformed"), True],
            ) as mocked_update:
                with patch.object(DecisionService, "_rebuild_fts_artifacts") as mocked_rebuild:
                    result = DecisionService.update_decision(1, {"title": "Updated Title", "body": "Updated Body"}, actor_id=1)

        self.assertTrue(result)
        self.assertEqual(mocked_update.call_count, 2)
        mocked_rebuild.assert_called_once()

    def test_get_decision_repairs_legacy_revision_table_columns(self):
        """Reading a decision should repair legacy revision columns before revision metadata is queried."""
        db = self.get_db()
        db.execute("DROP TABLE IF EXISTS t_meeting_decision_revision")
        db.execute(
            """
            CREATE TABLE t_meeting_decision_revision (
                mdr_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mdr_decision_id INTEGER NOT NULL,
                mdr_title TEXT NOT NULL,
                mdr_body TEXT NOT NULL,
                FOREIGN KEY (mdr_decision_id) REFERENCES t_meeting_decision(mdc_id)
            )
            """
        )
        db.execute("INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by) VALUES (1, 'Legacy Read Meeting', 1)")
        db.execute("INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by) VALUES (1, 1, 'Legacy Read Instance', 1, 1)")
        db.execute("INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by) VALUES ('Original Title', 'Original Body', 'Proposed', 1, 1)")
        db.commit()

        response = self.client.get("/api/decisions/1")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        self.assertEqual(payload["revision_count"], 0)
        self.assertIsNone(payload["last_revised_at"])

        revision_cols = {row["name"] for row in db.execute("PRAGMA table_info(t_meeting_decision_revision)").fetchall()}
        self.assertIn("mdr_updated_by", revision_cols)
        self.assertIn("mdr_updated_at", revision_cols)

    def test_revisions_endpoint_returns_previous_snapshots(self):
        """Revision history endpoint should return previous title/body snapshots newest first."""
        db = self.get_db()
        db.execute("INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by) VALUES (1, 'Revision API Meeting', 1)")
        db.execute("INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by) VALUES (1, 1, 'Revision API Instance', 1, 1)")
        db.execute("INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by) VALUES ('Original Title', 'Original Body', 'Proposed', 1, 1)")
        db.commit()

        first_update = self.client.patch("/api/decisions/1", json={"title": "Title v2", "body": "Body v2"})
        self.assertEqual(first_update.status_code, 200)
        second_update = self.client.patch("/api/decisions/1", json={"title": "Title v3", "body": "Body v3"})
        self.assertEqual(second_update.status_code, 200)

        response = self.client.get("/api/decisions/1/revisions")
        self.assertEqual(response.status_code, 200)
        revisions = response.get_json()["data"]
        self.assertEqual(len(revisions), 2)
        self.assertEqual(revisions[0]["mdr_title"], "Title v2")
        self.assertEqual(revisions[0]["mdr_body"], "Body v2")
        self.assertEqual(revisions[1]["mdr_title"], "Original Title")
        self.assertEqual(revisions[1]["mdr_body"], "Original Body")
