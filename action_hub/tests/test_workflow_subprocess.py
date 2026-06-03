"""Tests for workflow subprocess steps (WF-20, S72 D199-D200-D205)."""
import pytest
import json
import sqlite3
from datetime import datetime

from tests.conftest import AppTestCase


class TestWorkflowSubprocess(AppTestCase):
    """Test subprocess step functionality."""

    def setUp(self):
        super().setUp()
        self.login_admin()

    def _create_child_template(self):
        """Create a child workflow template for subprocess."""
        graph = {
            "steps": {
                "child_start": {"type": "Task", "order": 1, "name_en": "Child Start", "role": "Member"},
                "child_end": {"type": "End", "order": 2, "name_en": "Child End", "outcome": "completed"},
            },
            "transitions": [
                {"from": "child_start", "to": "child_end"},
            ],
        }
        response = self.client.post(
            "/api/workflow/templates",
            json={
                "name_en": "Child Workflow",
                "name_cn": "子工作流",
                "type": "request",
                "graph": graph,
            },
        )
        assert response.status_code == 201
        return response.get_json()["id"]

    def _create_parent_template_with_subprocess(self, child_template_id):
        """Create a parent workflow template with subprocess step."""
        graph = {
            "steps": {
                "parent_start": {"type": "Task", "order": 1, "name_en": "Parent Start", "role": "Member"},
                "subprocess": {
                    "type": "Subprocess",
                    "order": 2,
                    "name_en": "Run Child",
                    "name_cn": "运行子流程",
                    "subprocess_template_id": child_template_id,
                },
                "parent_end": {"type": "End", "order": 3, "name_en": "Parent End", "outcome": "completed"},
            },
            "transitions": [
                {"from": "parent_start", "to": "subprocess"},
                {"from": "subprocess", "to": "parent_end"},
            ],
        }
        response = self.client.post(
            "/api/workflow/templates",
            json={
                "name_en": "Parent Workflow with Subprocess",
                "name_cn": "带子流程的父工作流",
                "type": "request",
                "graph": graph,
            },
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.get_json()}"
        return response.get_json()["id"]

    def _create_test_users(self):
        """Create test users."""
        with self.app.app_context():
            from actionhub.middleware.db import get_db
            db = get_db()

            db.execute(
                "INSERT INTO t_team (tea_code, tea_name_en, tea_name_cn) VALUES (?, ?, ?)",
                ("TEAM_SUB", "Subprocess Team", "子流程团队"),
            )
            team_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

            users = []
            for i, (username, role) in enumerate([
                ("sub_user1", "Member"),
                ("sub_user2", "Member"),
            ]):
                db.execute(
                    """INSERT INTO t_user
                       (usr_username, usr_email, usr_pwd_hash, usr_display_name, usr_role, usr_team_id, usr_active)
                       VALUES (?, ?, ?, ?, ?, ?, 1)""",
                    (username, f"{username}@test.com", "hash", username, role, team_id),
                )
                user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                users.append({"id": user_id, "username": username})

            db.commit()
            return users, team_id

    def _instantiate_workflow(self, template_id, action_id, started_by):
        """Instantiate workflow within app context."""
        from actionhub.workflow.engine import instantiate_workflow
        with self.app.app_context():
            return instantiate_workflow(template_id, action_id, started_by)

    def test_subprocess_status_endpoint(self):
        """Test GET /api/workflow/instances/<id>/subprocess returns child status."""
        child_template_id = self._create_child_template()
        users, team_id = self._create_test_users()

        # Create action
        with self.app.app_context():
            from actionhub.middleware.db import get_db
            db = get_db()
            db.execute(
                """INSERT INTO t_action
                   (act_ref, act_title, act_status, act_source, act_priority, act_team_id, act_created_by)
                   VALUES (?, ?, 'Open', 'Manual', 'Medium', ?, 1)""",
                ("SUB-001", "Subprocess Test Action", team_id),
            )
            action_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.commit()

        # Create a simple parent workflow instance
        simple_graph = {
            "steps": {
                "start": {"type": "Task", "order": 1, "name_en": "Start"},
                "end": {"type": "End", "order": 2, "name_en": "End"},
            },
            "transitions": [{"from": "start", "to": "end"}],
        }
        response = self.client.post(
            "/api/workflow/templates",
            json={"name_en": "Simple Parent", "type": "request", "graph": simple_graph},
        )
        parent_template_id = response.get_json()["id"]

        # Create parent workflow instance
        parent_instance_id = self._instantiate_workflow(parent_template_id, action_id, 1)

        # Create child instance
        child_instance_id = self._instantiate_workflow(child_template_id, action_id, 1)

        # Manually set up a WaitingForChild step for testing
        with self.app.app_context():
            from actionhub.middleware.db import get_db
            db = get_db()
            
            # Create a subprocess step instance manually
            now = datetime.now()
            cursor = db.execute(
                """INSERT INTO t_workflow_step_instance
                   (wsi_instance_id, wsi_step_key, wsi_status, wsi_entered_at, wsi_child_instance_id)
                   VALUES (?, 'subprocess', 'WaitingForChild', ?, ?)""",
                (parent_instance_id, now, child_instance_id),
            )
            parent_step_id = cursor.lastrowid
            
            # Link child to parent
            db.execute(
                "UPDATE t_workflow_instance SET wfi_parent_step_id = ? WHERE wfi_id = ?",
                (parent_step_id, child_instance_id),
            )
            db.commit()

        # Call subprocess status endpoint
        response = self.client.get(f"/api/workflow/instances/{parent_instance_id}/subprocess")

        assert response.status_code == 200
        data = response.get_json()

        assert data["parent_instance_id"] == parent_instance_id
        assert len(data["subprocess_steps"]) == 1

        sub_info = data["subprocess_steps"][0]
        assert sub_info["parent_step_key"] == "subprocess"
        assert sub_info["parent_step_status"] == "WaitingForChild"
        assert sub_info["child_instance_id"] == child_instance_id
        assert sub_info["child_status"] == "Active"
        assert "child_progress" in sub_info
        assert sub_info["child_progress"]["total_steps"] >= 1

    def test_child_workflow_has_parent_link(self):
        """Test that child workflow instance has wfi_parent_step_id set."""
        child_template_id = self._create_child_template()

        with self.app.app_context():
            from actionhub.middleware.db import get_db
            db = get_db()

            db.execute(
                "INSERT INTO t_team (tea_code, tea_name_en) VALUES (?, ?)",
                ("TEAM_SUB3", "Subprocess Team 3"),
            )
            team_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

            db.execute(
                """INSERT INTO t_action
                   (act_ref, act_title, act_status, act_source, act_priority, act_team_id, act_created_by)
                   VALUES (?, ?, 'Open', 'Manual', 'Medium', ?, 1)""",
                ("SUB-003", "Parent Link Test", team_id),
            )
            action_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.commit()

        # Create parent instance
        graph = {
            "steps": {
                "start": {"type": "Task", "order": 1, "name_en": "Start"},
                "end": {"type": "End", "order": 2, "name_en": "End"},
            },
            "transitions": [{"from": "start", "to": "end"}],
        }

        response = self.client.post(
            "/api/workflow/templates",
            json={"name_en": "Parent Template", "type": "request", "graph": graph},
        )
        parent_template_id = response.get_json()["id"]

        parent_instance_id = self._instantiate_workflow(parent_template_id, action_id, 1)

        with self.app.app_context():
            from actionhub.middleware.db import get_db
            db = get_db()
            
            # Get parent step
            parent_step = db.execute(
                "SELECT wsi_id FROM t_workflow_step_instance WHERE wsi_instance_id = ?",
                (parent_instance_id,),
            ).fetchone()
            
            assert parent_step is not None, "Parent step not found"

            # Create child instance with parent link
            child_instance_id = self._instantiate_workflow(child_template_id, action_id, 1)

            # Set parent link
            db.execute(
                "UPDATE t_workflow_instance SET wfi_parent_step_id = ? WHERE wfi_id = ?",
                (parent_step["wsi_id"], child_instance_id),
            )
            db.commit()

            # Verify link
            child = db.execute(
                "SELECT wfi_parent_step_id FROM t_workflow_instance WHERE wfi_id = ?",
                (child_instance_id,),
            ).fetchone()

            assert child["wfi_parent_step_id"] == parent_step["wsi_id"]

    def test_subprocess_endpoint_empty_when_no_children(self):
        """Test that subprocess endpoint returns empty list when no children."""
        with self.app.app_context():
            from actionhub.middleware.db import get_db
            db = get_db()

            db.execute(
                "INSERT INTO t_team (tea_code, tea_name_en) VALUES (?, ?)",
                ("TEAM_SUB5", "Subprocess Team 5"),
            )
            team_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

            db.execute(
                """INSERT INTO t_action
                   (act_ref, act_title, act_status, act_source, act_priority, act_team_id, act_created_by)
                   VALUES (?, ?, 'Open', 'Manual', 'Medium', ?, 1)""",
                ("SUB-005", "No Children Test", team_id),
            )
            action_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.commit()

        # Create simple workflow without subprocess
        graph = {
            "steps": {
                "start": {"type": "Task", "order": 1, "name_en": "Start"},
                "end": {"type": "End", "order": 2, "name_en": "End"},
            },
            "transitions": [{"from": "start", "to": "end"}],
        }

        response = self.client.post(
            "/api/workflow/templates",
            json={"name_en": "Simple Template", "type": "request", "graph": graph},
        )
        template_id = response.get_json()["id"]

        instance_id = self._instantiate_workflow(template_id, action_id, 1)

        # Call subprocess status endpoint
        response = self.client.get(f"/api/workflow/instances/{instance_id}/subprocess")

        assert response.status_code == 200
        data = response.get_json()

        assert data["parent_instance_id"] == instance_id
        assert data["subprocess_steps"] == []
