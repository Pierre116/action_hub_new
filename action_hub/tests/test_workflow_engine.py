"""Tests for the workflow module."""
import pytest
import json

from actionhub.workflow.graph import (
    load_graph,
    validate_graph,
    get_start_steps,
    get_next_steps,
    get_incoming_steps,
    is_fork,
    is_join,
    get_step,
    get_fields_for_step,
)
from actionhub.workflow.pilot import OT_USER_CREATION_GRAPH, SIMPLE_ACTION_GRAPH


class TestGraphParser:
    """Test graph parsing and validation."""

    def test_load_graph_valid(self):
        """Round-trip JSON parse."""
        graph_json = json.dumps(OT_USER_CREATION_GRAPH)
        graph = load_graph(graph_json)
        assert "steps" in graph
        assert "transitions" in graph

    def test_load_graph_invalid_json(self):
        """Raises ValueError on invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_graph("{invalid")

    def test_validate_graph_ok(self):
        """OT pilot graph passes validation."""
        errors = validate_graph(OT_USER_CREATION_GRAPH)
        assert errors == [], f"Validation errors: {errors}"

    def test_validate_graph_simple(self):
        """Simple action graph passes validation."""
        errors = validate_graph(SIMPLE_ACTION_GRAPH)
        assert errors == [], f"Validation errors: {errors}"

    def test_validate_graph_missing_end(self):
        """Error when no End step."""
        bad_graph = {
            "steps": {"step1": {"type": "Task", "order": 1}},
            "transitions": [],
        }
        errors = validate_graph(bad_graph)
        assert any("End" in e for e in errors)

    def test_validate_graph_orphan_step(self):
        """Error when orphan step exists."""
        bad_graph = {
            "steps": {
                "start": {"type": "Task", "order": 1},
                "orphan": {"type": "Task", "order": 2},
            },
            "transitions": [{"from": "start", "to": "orphan"}],
        }
        # Actually this is valid - orphan is reachable
        # Let's make a truly orphan step
        bad_graph2 = {
            "steps": {
                "start": {"type": "Task", "order": 1},
                "orphan": {"type": "Task", "order": 2},
            },
            "transitions": [],  # No transitions - start is orphan
        }
        errors = validate_graph(bad_graph2)
        assert any("orphan" in e.lower() or "reachable" in e.lower() for e in errors)

    def test_get_start_steps(self):
        """Returns ['request'] for OT pilot."""
        starts = get_start_steps(OT_USER_CREATION_GRAPH)
        assert "request" in starts

    def test_get_next_steps_fork(self):
        """request step has 2 outgoing transitions."""
        next_steps = get_next_steps(OT_USER_CREATION_GRAPH, "request")
        assert "facility" in next_steps
        assert "hse_validation" in next_steps

    def test_get_next_steps_linear(self):
        """finance step has 1 outgoing transition."""
        next_steps = get_next_steps(OT_USER_CREATION_GRAPH, "finance")
        assert "ot_admin" in next_steps
        assert len(next_steps) == 1

    def test_get_incoming_steps(self):
        """join step has 2 incoming steps."""
        incoming = get_incoming_steps(OT_USER_CREATION_GRAPH, "join")
        assert "facility" in incoming
        assert "hse_validation" in incoming
        assert len(incoming) == 2

    def test_is_fork(self):
        """request is a fork (2 outgoing)."""
        assert is_fork(OT_USER_CREATION_GRAPH, "request") is True
        assert is_fork(OT_USER_CREATION_GRAPH, "finance") is False

    def test_is_join(self):
        """join step is a Join type."""
        assert is_join(OT_USER_CREATION_GRAPH, "join") is True
        assert is_join(OT_USER_CREATION_GRAPH, "request") is False

    def test_get_step(self):
        """Get step definition by key."""
        step = get_step(OT_USER_CREATION_GRAPH, "facility")
        assert step["name_en"] == "Facility"
        assert step["role"] == "Facility"

    def test_get_step_not_found(self):
        """Raises KeyError for missing step."""
        with pytest.raises(KeyError):
            get_step(OT_USER_CREATION_GRAPH, "nonexistent")

    def test_get_fields_for_step(self):
        """request step has 4 fields."""
        fields = get_fields_for_step(OT_USER_CREATION_GRAPH, "request")
        assert len(fields) == 4
        field_keys = [f["key"] for f in fields]
        assert "employee_name" in field_keys
        assert "role" in field_keys
        assert "start_date" in field_keys
        assert "workshop_zone" in field_keys

    def test_get_fields_for_step_no_fields(self):
        """End step has no fields."""
        fields = get_fields_for_step(OT_USER_CREATION_GRAPH, "active")
        assert fields == []


class TestFieldValidation:
    """Test form field validation."""

    def test_validate_required_field_empty(self):
        """Error for missing required field."""
        from actionhub.workflow.forms import validate_field_value

        field_def = {"key": "name", "type": "text", "required": True}
        error = validate_field_value(field_def, None)
        assert error is not None
        assert "required" in error.lower()

    def test_validate_dropdown_valid(self):
        """Valid dropdown value passes."""
        from actionhub.workflow.forms import validate_field_value

        field_def = {
            "key": "role",
            "type": "dropdown",
            "options": ["Operator", "Technician", "Engineer"],
        }
        error = validate_field_value(field_def, "Operator")
        assert error is None

    def test_validate_dropdown_invalid(self):
        """Invalid dropdown value fails."""
        from actionhub.workflow.forms import validate_field_value

        field_def = {
            "key": "role",
            "type": "dropdown",
            "options": ["Operator", "Technician"],
        }
        error = validate_field_value(field_def, "Manager")
        assert error is not None
        assert "not in allowed options" in error.lower()

    def test_validate_date_valid(self):
        """Valid ISO date passes."""
        from actionhub.workflow.forms import validate_field_value

        field_def = {"key": "start_date", "type": "date"}
        error = validate_field_value(field_def, "2026-03-15")
        assert error is None

    def test_validate_date_invalid(self):
        """Invalid date format fails."""
        from actionhub.workflow.forms import validate_field_value

        field_def = {"key": "start_date", "type": "date"}
        error = validate_field_value(field_def, "15/03/2026")
        assert error is not None

    def test_validate_checkbox_valid(self):
        """Valid checkbox value passes."""
        from actionhub.workflow.forms import validate_field_value

        field_def = {"key": "card_printed", "type": "checkbox"}
        error = validate_field_value(field_def, True)
        assert error is None

    def test_validate_checkbox_invalid(self):
        """Invalid checkbox value fails."""
        from actionhub.workflow.forms import validate_field_value

        field_def = {"key": "card_printed", "type": "checkbox"}
        error = validate_field_value(field_def, "yes")
        assert error is not None



# ── parallel branch & multi-assignee graph tests (from test_workflow_engine_parallel.py) ──

def _make_graph_parallel():
    return {
        "steps": {
            "start": {"type": "Task", "order": 1},
            "fork": {"type": "Task", "order": 2},
            "a": {"type": "Task", "order": 3},
            "b": {"type": "Task", "order": 3},
            "join": {"type": "Join", "order": 4},
            "end": {"type": "End", "order": 5}
        },
        "transitions": [
            {"from": "start", "to": "fork"},
            {"from": "fork", "to": "a"},
            {"from": "fork", "to": "b"},
            {"from": "a", "to": "join"},
            {"from": "b", "to": "join"},
            {"from": "join", "to": "end"}
        ]
    }


def _make_graph_multiassignee():
    return {
        "steps": {
            "start": {"type": "Task", "order": 1},
            "review": {"type": "Task", "order": 2, "assignees": [1, 2]},
            "end": {"type": "End", "order": 3}
        },
        "transitions": [
            {"from": "start", "to": "review"},
            {"from": "review", "to": "end"}
        ]
    }


def test_parallel_branch_and_join(monkeypatch):
    graph = _make_graph_parallel()
    from actionhub.workflow.graph import is_fork, is_join, get_next_steps, get_incoming_steps
    assert is_fork(graph, "fork")
    assert set(get_next_steps(graph, "fork")) == {"a", "b"}
    assert is_join(graph, "join")
    assert set(get_incoming_steps(graph, "join")) == {"a", "b"}


def test_multiassignee_step(monkeypatch):
    graph = _make_graph_multiassignee()
    review = graph["steps"]["review"]
    assert "assignees" in review
    assert isinstance(review["assignees"], list)
    assert set(review["assignees"]) == {1, 2}
