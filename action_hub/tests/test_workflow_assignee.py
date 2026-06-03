"""WF-16: Runtime assignee override + timeline UI tests."""
import json
import pytest
from tests.conftest import AppTestCase


class TestWorkflowAssignee(AppTestCase):
    """Tests for reassign_step and timeline endpoints (WF-16)."""

    def setUp(self):
        super().setUp()
        self.login_admin()

    def _setup_workflow(self):
        """Create a minimal workflow template, action, instance, and active step."""
        db = self.get_db()
        wf_graph = {
            "steps": {
                "start": {"type": "Task", "order": 1},
                "review": {"type": "Task", "order": 2},
                "end": {"type": "End"},
            },
            "transitions": [
                {"from": "start", "to": "review"},
                {"from": "review", "to": "end"},
            ],
        }
        db.execute(
            """INSERT INTO t_workflow_template
               (wft_id, wft_name_en, wft_graph, wft_type, wft_active,
                wft_created_by, wft_created_at, wft_updated_at)
               VALUES (9001, 'ReassignTest', ?, 'action', 1, 1,
                       datetime('now'), datetime('now'))""",
            [json.dumps(wf_graph)],
        )
        db.execute(
            """INSERT INTO t_action
               (act_id, act_ref, act_title, act_status, act_priority, act_created_by)
               VALUES (9001, 'REF9001', 'Reassign Test Action', 'Open', 'Medium', 1)"""
        )
        db.execute(
            """INSERT INTO t_workflow_instance
               (wfi_id, wfi_template_id, wfi_action_id, wfi_status)
               VALUES (9001, 9001, 9001, 'Active')"""
        )
        db.execute(
            """INSERT INTO t_workflow_step_instance
               (wsi_id, wsi_instance_id, wsi_step_key, wsi_status,
                wsi_assignee_id, wsi_entered_at)
               VALUES (9001, 9001, 'start', 'Pending', 1, datetime('now'))"""
        )
        db.commit()
        return {"instance_id": 9001, "step_id": 9001}

    def test_reassign_active_step(self):
        """PUT /api/workflow/steps/<id>/reassign updates assignee."""
        ids = self._setup_workflow()
        resp = self.client.put(
            f"/api/workflow/steps/{ids['step_id']}/reassign",
            json={"new_assignee_id": 2, "reason": "Override for test"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["step_id"] == ids["step_id"]
        assert data["new_assignee_id"] == 2
        assert data["status"] == "ok"
        # Verify in DB
        db = self.get_db()
        row = db.execute(
            "SELECT wsi_assignee_id FROM t_workflow_step_instance WHERE wsi_id = ?",
            (ids["step_id"],),
        ).fetchone()
        assert row["wsi_assignee_id"] == 2

    def test_reassign_audit_log(self):
        """Reassign writes an audit row to t_action_history."""
        ids = self._setup_workflow()
        self.client.put(
            f"/api/workflow/steps/{ids['step_id']}/reassign",
            json={"new_assignee_id": 2, "reason": "Audit log test"},
        )
        db = self.get_db()
        row = db.execute(
            """SELECT * FROM t_action_history
               WHERE ahi_action_id = ?
               ORDER BY ahi_changed_at DESC LIMIT 1""",
            (9001,),
        ).fetchone()
        assert row is not None
        assert "assignee:2" in row["ahi_new_value"]

    def test_reassign_requires_assignee_or_admin(self):
        """Non-admin users who are not the assignee cannot reassign a step."""
        ids = self._setup_workflow()
        self.login_user()
        resp = self.client.put(
            f"/api/workflow/steps/{ids['step_id']}/reassign",
            json={"new_assignee_id": 2, "reason": "Unauthorized override"},
        )
        assert resp.status_code == 403

    def test_timeline_returns_ordered_steps(self):
        """GET /api/workflow/instances/<id>/timeline returns ordered step list."""
        ids = self._setup_workflow()
        resp = self.client.get(
            f"/api/workflow/instances/{ids['instance_id']}/timeline"
        )
        assert resp.status_code == 200
        timeline = resp.get_json()["timeline"]
        assert isinstance(timeline, list)
        assert len(timeline) >= 1
        assert all("wsi_id" in s for s in timeline)
        # Verify ordering by entered_at
        entered_ats = [
            s.get("wsi_entered_at") or s.get("wsi_completed_at", "")
            for s in timeline
        ]
        assert entered_ats == sorted(entered_ats)

    def test_lookup_active_instance_by_action(self):
        """GET /api/workflow/actions/<action_id>/instance returns the linked active instance."""
        ids = self._setup_workflow()
        resp = self.client.get("/api/workflow/actions/9001/instance")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["id"] == ids["instance_id"]
        assert data["action_id"] == 9001
        assert data["status"] == "Active"

    def test_lookup_active_instance_by_action_returns_null_when_missing(self):
        """GET /api/workflow/actions/<action_id>/instance returns null when no instance is linked."""
        resp = self.client.get("/api/workflow/actions/9999/instance")
        assert resp.status_code == 200
        assert resp.get_json()["data"] is None
