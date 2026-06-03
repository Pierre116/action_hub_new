"""Test for workflow V3 Gateway step (WF-11).

Covers decision table routing based on prior step field values.
"""
import pytest
import json
from actionhub.workflow.graph import load_graph
from actionhub.workflow import engine
from actionhub.workflow.gateway import evaluate_decision_table

def test_gateway_decision_table_routing(monkeypatch):
    # Minimal graph with Gateway and two possible outcomes
    graph = {
        "steps": {
            "start": {"type": "Task", "order": 1, "fields": []},
            "gateway": {
                "type": "Gateway", "order": 2,
                "decision_table": [
                    {"conditions": {"field1": "A"}, "next": "outcome_a"},
                    {"conditions": {"field1": "B"}, "next": "outcome_b"}
                ]
            },
            "outcome_a": {"type": "End", "order": 3},
            "outcome_b": {"type": "End", "order": 3}
        },
        "transitions": [
            {"from": "start", "to": "gateway"},
            {"from": "gateway", "to": "outcome_a"},
            {"from": "gateway", "to": "outcome_b"}
        ]
    }
    # Patch DB access to simulate field values
    class DummyDB:
        def execute(self, sql, params=None):
            if sql.strip().startswith("UPDATE") or sql.strip().startswith("INSERT") or sql.strip().startswith("COMMIT"):
                class DummyResult:
                    def fetchone(self): return None
                    def fetchall(self): return []
                    @property
                    def lastrowid(self): return 1
                return DummyResult()
            if "FROM t_workflow_step_instance" in sql:
                class DummyStepInst:
                    def fetchone(self):
                        return {"wsi_id": 1, "wsi_instance_id": 1, "wsi_step_key": "start", "wsi_status": "Accepted"}
                return DummyStepInst()
            elif "FROM t_workflow_instance" in sql:
                class DummyInstance:
                    def fetchone(self):
                        return {"wfi_id": 1, "wfi_template_id": 1, "wfi_action_id": 1}
                return DummyInstance()
            elif "FROM t_workflow_template" in sql:
                class DummyTemplate:
                    def fetchone(self):
                        return {"wft_graph": json.dumps(graph)}
                return DummyTemplate()
            elif "FROM t_workflow_step_field_value" in sql:
                class DummyFields:
                    def fetchall(self):
                        return [{"wsf_field_code": "field1", "wsf_value": "A"}]
                return DummyFields()
            else:
                raise Exception("Unexpected SQL: " + sql)
    # Patch get_db to return dummy DB
    monkeypatch.setattr(engine, "get_db", lambda: DummyDB())
    # Patch load_graph to use our test graph
    monkeypatch.setattr(engine, "load_graph", lambda _: graph)
    # Patch get_step to use our test graph
    monkeypatch.setattr(engine, "get_step", lambda g, k: g["steps"][k])
    # Patch get_next_steps to use our test graph
    monkeypatch.setattr(engine, "get_next_steps", lambda g, k: [t["to"] for t in g["transitions"] if t["from"] == k])
    # Patch resolve_join and complete_workflow to no-op
    monkeypatch.setattr(engine, "resolve_join", lambda *a, **kw: True)
    monkeypatch.setattr(engine, "complete_workflow", lambda *a, **kw: None)
    # Patch _create_step_instance to record activations
    activations = []
    monkeypatch.setattr(engine, "_create_step_instance", lambda db, iid, sk, st, aid, ent, sd: activations.append(sk))
    # Patch log_action_history to no-op
    monkeypatch.setattr(engine, "log_action_history", lambda *a, **kw: None)
    # Patch db.commit to no-op
    DummyDB.commit = lambda self: None
    # Prepare dummy step instance and instance
    monkeypatch.setattr(engine, "get_fields_for_step", lambda g, k: [])
    # Run advance_step (should activate outcome_a)
    result = engine.advance_step(1, 42, comment="Test gateway")
    assert "outcome_a" in activations
    assert result["activated"] == ["outcome_a"]
    assert result["workflow_completed"] is True
