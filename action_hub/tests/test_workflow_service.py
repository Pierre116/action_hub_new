import pytest
from tests.conftest import AppTestCase


class TestWorkflowServiceSteps(AppTestCase):
    def print_routes(self):
        print("\nRegistered routes:")
        for rule in self.app.url_map.iter_rules():
            print(f"{rule.methods} {rule}")

    def test_service_step_error_sets_paused(self):
        """Service step with missing handler sets step to Paused, not Error."""
        db = self.get_db()
        graph = {
            "steps": {
                "start": {"type": "Task", "order": 1},
                "svc": {"type": "Service", "handler": "not_a_real_handler"},
                "end": {"type": "End"}
            },
            "transitions": [
                {"from": "start", "to": "svc"},
                {"from": "svc", "to": "end"}
            ]
        }
        db.execute("INSERT INTO t_workflow_template (wft_id, wft_name_en, wft_graph, wft_type, wft_active, wft_created_by, wft_created_at, wft_updated_at) VALUES (1101, 'PausedTest', ?, 'action', 1, 1, datetime('now'), datetime('now'))", [self.json_dumps(graph)])
        db.execute("INSERT INTO t_action (act_id, act_ref, act_title, act_status, act_priority, act_created_by) VALUES (2101, 'REF2101', 'Test Action Paused', 'Open', 'Medium', 1)")
        db.execute("INSERT INTO t_workflow_instance (wfi_id, wfi_template_id, wfi_action_id, wfi_status) VALUES (3101, 1101, 2101, 'Active')")
        db.execute("INSERT INTO t_workflow_step_instance (wsi_id, wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id) VALUES (4101, 3101, 'start', 'Active', 1)")
        db.commit()
        resp = self.client.post("/api/workflow/steps/4101/advance", json={})
        assert resp.status_code == 200
        db2 = self.get_db()
        svc_step = db2.execute("SELECT wsi_status FROM t_workflow_step_instance WHERE wsi_instance_id=3101 AND wsi_step_key='svc'").fetchone()
        assert svc_step is not None
        assert svc_step["wsi_status"] == "Paused"

    def test_service_step_retry_endpoint(self):
        self.print_routes()
        """Admin can retry a Paused service step; retry updates status and log."""
        db = self.get_db()
        # Register a handler that will succeed
        from actionhub.workflow.service_executor import service_registry, ServiceHandler
        def always_add(inputs):
            a = inputs.get("a", 0)
            b = inputs.get("b", 0)
            try:
                a = int(a)
            except Exception:
                a = 0
            try:
                b = int(b)
            except Exception:
                b = 0
            return {"result": a + b}
        service_registry.register(ServiceHandler(
            name="always_add",
            func=always_add,
            input_schema={"a": "int", "b": "int"},
            output_schema={"result": "int"},
            description="Always adds a+b."
        ))
        graph = {
            "steps": {
                "start": {"type": "Task", "order": 1},
                "svc": {"type": "Service", "handler": "always_add"},
                "end": {"type": "End"}
            },
            "transitions": [
                {"from": "start", "to": "svc"},
                {"from": "svc", "to": "end"}
            ]
        }
        db.execute("INSERT INTO t_workflow_template (wft_id, wft_name_en, wft_graph, wft_type, wft_active, wft_created_by, wft_created_at, wft_updated_at) VALUES (1201, 'RetryTest', ?, 'action', 1, 1, datetime('now'), datetime('now'))", [self.json_dumps(graph)])
        db.execute("INSERT INTO t_action (act_id, act_ref, act_title, act_status, act_priority, act_created_by) VALUES (2201, 'REF2201', 'Test Action Retry', 'Open', 'Medium', 1)")
        db.execute("INSERT INTO t_workflow_instance (wfi_id, wfi_template_id, wfi_action_id, wfi_status) VALUES (3201, 1201, 2201, 'Active')")
        db.execute("INSERT INTO t_workflow_step_instance (wsi_id, wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id) VALUES (4201, 3201, 'start', 'Active', 1)")
        db.execute("INSERT INTO t_workflow_step_field_value (wsf_instance_id, wsf_step_key, wsf_field_code, wsf_value) VALUES (3201, 'svc', 'a', 7)")
        db.execute("INSERT INTO t_workflow_step_field_value (wsf_instance_id, wsf_step_key, wsf_field_code, wsf_value) VALUES (3201, 'svc', 'b', 8)")
        db.commit()
        # Manually create a Paused service step (simulate error)
        db.execute("INSERT INTO t_workflow_step_instance (wsi_id, wsi_instance_id, wsi_step_key, wsi_status) VALUES (4202, 3201, 'svc', 'Paused')")
        db.commit()
        # Retry as admin
        resp = self.client.post("/api/workflow/steps/4202/retry")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "Success"
        # Step should now be Completed
        db2 = self.get_db()
        svc_step = db2.execute("SELECT wsi_status FROM t_workflow_step_instance WHERE wsi_id=4202").fetchone()
        assert svc_step["wsi_status"] == "Completed"
        # Log should exist
        log = db2.execute("SELECT * FROM t_workflow_service_log WHERE wsl_instance_id=3201 AND wsl_step_key='svc' ORDER BY wsl_id DESC").fetchone()
        assert log is not None
        assert log["wsl_status"] == "Success"
        assert log["wsl_handler"] == "always_add"
        assert log["wsl_outputs"] is not None
        # Output field should be written
        out = db2.execute("SELECT wsf_value FROM t_workflow_step_field_value WHERE wsf_instance_id=3201 AND wsf_step_key='svc' AND wsf_field_code='result'").fetchone()
        assert out is not None
        assert int(out["wsf_value"]) == 15

    def test_service_step_retry_endpoint_nonadmin(self):
        self.print_routes()
        """Non-admin cannot retry a Paused service step."""
        db = self.get_db()
        graph = {
            "steps": {
                "start": {"type": "Task", "order": 1},
                "svc": {"type": "Service", "handler": "add_numbers"},
                "end": {"type": "End"}
            },
            "transitions": [
                {"from": "start", "to": "svc"},
                {"from": "svc", "to": "end"}
            ]
        }
        db.execute("INSERT INTO t_workflow_template (wft_id, wft_name_en, wft_graph, wft_type, wft_active, wft_created_by, wft_created_at, wft_updated_at) VALUES (1301, 'RetryNonAdmin', ?, 'action', 1, 1, datetime('now'), datetime('now'))", [self.json_dumps(graph)])
        db.execute("INSERT INTO t_action (act_id, act_ref, act_title, act_status, act_priority, act_created_by) VALUES (2301, 'REF2301', 'Test Action Retry NonAdmin', 'Open', 'Medium', 1)")
        db.execute("INSERT INTO t_workflow_instance (wfi_id, wfi_template_id, wfi_action_id, wfi_status) VALUES (3301, 1301, 2301, 'Active')")
        db.execute("INSERT INTO t_workflow_step_instance (wsi_id, wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id) VALUES (4301, 3301, 'start', 'Active', 1)")
        db.execute("INSERT INTO t_workflow_step_instance (wsi_id, wsi_instance_id, wsi_step_key, wsi_status) VALUES (4302, 3301, 'svc', 'Paused')")
        db.commit()
        self.login_user()
        resp = self.client.post("/api/workflow/steps/4302/retry")
        assert resp.status_code == 403
        data = resp.get_json()
        assert "error" in data

    def setUp(self):
        super().setUp()
        self.login_admin()

    def test_service_handler_registry_endpoint_admin(self):
        resp = self.client.get("/api/workflow/service-handlers")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "data" in data
        assert isinstance(data["data"], list)
        # Should include the example handler
        assert any(h["name"] == "add_numbers" for h in data["data"])

    def test_service_handler_registry_endpoint_nonadmin(self):
        # Downgrade to non-admin user
        self.login_user()
        resp = self.client.get("/api/workflow/service-handlers")
        assert resp.status_code == 403
        data = resp.get_json()
        assert "error" in data

    def test_service_step_autoexec_success(self):
        db = self.get_db()
        # Insert template with Service step (new graph format)
        graph = {
            "steps": {
                "start": {"type": "Task", "order": 1},
                "svc": {"type": "Service", "handler": "add_numbers"},
                "end": {"type": "End"}
            },
            "transitions": [
                {"from": "start", "to": "svc"},
                {"from": "svc", "to": "end"}
            ]
        }
        db.execute("INSERT INTO t_workflow_template (wft_id, wft_name_en, wft_graph, wft_type, wft_active, wft_created_by, wft_created_at, wft_updated_at) VALUES (1001, 'ServiceTest', ?, 'action', 1, 1, datetime('now'), datetime('now'))", [self.json_dumps(graph)])
        db.execute("INSERT INTO t_action (act_id, act_ref, act_title, act_status, act_priority, act_created_by) VALUES (2001, 'REF2001', 'Test Action', 'Open', 'Medium', 1)")
        db.execute("INSERT INTO t_workflow_instance (wfi_id, wfi_template_id, wfi_action_id, wfi_status) VALUES (3001, 1001, 2001, 'Active')")
        db.execute("INSERT INTO t_workflow_step_instance (wsi_id, wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id) VALUES (4001, 3001, 'start', 'Active', 1)")
        db.execute("INSERT INTO t_workflow_step_field_value (wsf_instance_id, wsf_step_key, wsf_field_code, wsf_value) VALUES (3001, 'svc', 'a', 2)")
        db.execute("INSERT INTO t_workflow_step_field_value (wsf_instance_id, wsf_step_key, wsf_field_code, wsf_value) VALUES (3001, 'svc', 'b', 3)")
        db.commit()
        # Advance 'start' step, which should auto-execute Service step
        resp = self.client.post("/api/workflow/steps/4001/advance", json={})
        assert resp.status_code == 200
        data = resp.get_json()
        # Check that Service step was completed and output field was written
        db2 = self.get_db()
        all_fields = db2.execute("SELECT * FROM t_workflow_step_field_value WHERE wsf_instance_id=3001").fetchall()
        print('All step field values:', [dict(row) for row in all_fields])
        all_steps = db2.execute("SELECT * FROM t_workflow_step_instance WHERE wsi_instance_id=3001").fetchall()
        print('All step instances:', [dict(row) for row in all_steps])
        out = db2.execute("SELECT wsf_value FROM t_workflow_step_field_value WHERE wsf_instance_id=3001 AND wsf_step_key='svc' AND wsf_field_code='result'").fetchone()
        assert out is not None
        assert int(out["wsf_value"]) == 5

    def test_service_step_autoexec_error(self):
        db = self.get_db()
        # Insert template with Service step (new graph format)
        graph = {
            "steps": {
                "start": {"type": "Task", "order": 1},
                "svc": {"type": "Service", "handler": "not_a_real_handler"},
                "end": {"type": "End"}
            },
            "transitions": [
                {"from": "start", "to": "svc"},
                {"from": "svc", "to": "end"}
            ]
        }
        db.execute("INSERT INTO t_workflow_template (wft_id, wft_name_en, wft_graph, wft_type, wft_active, wft_created_by, wft_created_at, wft_updated_at) VALUES (1002, 'ServiceErrorTest', ?, 'action', 1, 1, datetime('now'), datetime('now'))", [self.json_dumps(graph)])
        db.execute("INSERT INTO t_action (act_id, act_ref, act_title, act_status, act_priority, act_created_by) VALUES (2002, 'REF2002', 'Test Action 2', 'Open', 'Medium', 1)")
        db.execute("INSERT INTO t_workflow_instance (wfi_id, wfi_template_id, wfi_action_id, wfi_status) VALUES (3002, 1002, 2002, 'Active')")
        db.execute("INSERT INTO t_workflow_step_instance (wsi_id, wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id) VALUES (4002, 3002, 'start', 'Active', 1)")
        db.commit()
        # Advance 'start' step, which should attempt to auto-execute Service step and fail
        resp = self.client.post("/api/workflow/steps/4002/advance", json={})
        assert resp.status_code == 200
        # Check that Service step is in 'Paused' status (engine sets Paused on error)
        db2 = self.get_db()
        all_fields = db2.execute("SELECT * FROM t_workflow_step_field_value WHERE wsf_instance_id=3002").fetchall()
        print('All step field values:', [dict(row) for row in all_fields])
        all_steps = db2.execute("SELECT * FROM t_workflow_step_instance WHERE wsi_instance_id=3002").fetchall()
        print('All step instances:', [dict(row) for row in all_steps])
        svc_step = db2.execute("SELECT wsi_status FROM t_workflow_step_instance WHERE wsi_instance_id=3002 AND wsi_step_key='svc'").fetchone()
        assert svc_step is not None
        assert svc_step["wsi_status"] == "Paused"
