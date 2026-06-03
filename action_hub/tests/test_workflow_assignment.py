"""
test_workflow_assignment.py — Tests for assignment rule resolver (WF-19)
"""
import sqlite3
import pytest
from actionhub.workflow.assignment import resolve_assignee

class DummyDB:
    """A minimal DB stub for assignment rule tests."""
    def __init__(self, users, instances, steps, counters):
        self.users = users
        self.instances = instances
        self.steps = steps
        self.counters = counters
        self.queries = []
    def execute(self, sql, params=()):
        self.queries.append((sql, params))
        # Simulate user queries
        if "FROM t_user" in sql:
            if "usr_id = ?" in sql:
                uid = params[0]
                for u in self.users:
                    if u["usr_id"] == uid and u["usr_active"]:
                        return DummyRow([u])
                return DummyRow([])
            if "usr_role = ?" in sql and "usr_team_id = ?" in sql:
                team_id, role = params
                return DummyRow([u for u in self.users if u["usr_team_id"] == team_id and u["usr_role"] == role and u["usr_active"]])
            if "usr_role = ?" in sql:
                role = params[0]
                return DummyRow([u for u in self.users if u["usr_role"] == role and u["usr_active"]])
            if "usr_role = 'Admin'" in sql:
                return DummyRow([u for u in self.users if u["usr_role"] == "Admin" and u["usr_active"]])
        if "FROM t_workflow_instance JOIN t_action ON wfi_action_id = act_id" in sql:
            # Simulate join to get act_team_id
            # Always return team_id=10 for test data
            return DummyRow([{"act_team_id": 10}])
        if "FROM t_workflow_instance" in sql:
            if "wfi_started_by" in sql:
                return DummyRow([{"wfi_started_by": self.instances[0]["wfi_started_by"]}])
            if "wfi_template_id" in sql:
                return DummyRow([{"wfi_template_id": self.instances[0]["wfi_template_id"]}])
        if "FROM t_workflow_assignment_counter" in sql:
            if "wrc_last_user_id" in sql:
                return DummyRow(self.counters)
        return DummyRow([])
    def commit(self):
        pass

class DummyRow:
    def __init__(self, rows):
        self.rows = rows
        self._idx = 0
    def fetchone(self):
        return self.rows[0] if self.rows else None
    def fetchall(self):
        return self.rows

@pytest.fixture
def sample_users():
    return [
        {"usr_id": 1, "usr_role": "Admin", "usr_team_id": 10, "usr_active": 1, "usr_display_name": "Alice"},
        {"usr_id": 2, "usr_role": "Quality_Engineer", "usr_team_id": 10, "usr_active": 1, "usr_display_name": "Bob"},
        {"usr_id": 3, "usr_role": "Quality_Engineer", "usr_team_id": 10, "usr_active": 1, "usr_display_name": "Carol"},
        {"usr_id": 4, "usr_role": "Inspector", "usr_team_id": 10, "usr_active": 1, "usr_display_name": "Dave"},
        {"usr_id": 5, "usr_role": "Inspector", "usr_team_id": 10, "usr_active": 0, "usr_display_name": "Eve"},
    ]

@pytest.fixture
def sample_instance():
    return [{"wfi_started_by": 1, "wfi_template_id": 100}]

@pytest.fixture
def sample_counters():
    return [{"wrc_last_user_id": 2}]

def test_static_user(sample_users, sample_instance):
    db = DummyDB(sample_users, sample_instance, [], [])
    rule = {"type": "static_user", "user_id": 2}
    graph = {"steps": {"review": {"assignment": {"rules": [rule]}}}}
    user_id = resolve_assignee(1, "review", graph, db)
    assert user_id == 2

def test_role_in_team(sample_users, sample_instance):
    db = DummyDB(sample_users, sample_instance, [], [])
    rule = {"type": "role_in_team", "role": "Quality_Engineer", "team_source": "action_team"}
    graph = {"steps": {"review": {"assignment": {"rules": [rule]}}}}
    user_id = resolve_assignee(1, "review", graph, db)
    assert user_id == 2

def test_workflow_creator(sample_users, sample_instance):
    db = DummyDB(sample_users, sample_instance, [], [])
    rule = {"type": "workflow_creator"}
    graph = {"steps": {"review": {"assignment": {"rules": [rule]}}}}
    user_id = resolve_assignee(1, "review", graph, db)
    assert user_id == 1

def test_round_robin(sample_users, sample_instance, sample_counters):
    db = DummyDB(sample_users, sample_instance, [], sample_counters)
    rule = {"type": "round_robin", "role": "Quality_Engineer", "team_source": "action_team"}
    graph = {"steps": {"review": {"assignment": {"rules": [rule]}}}}
    user_id = resolve_assignee(1, "review", graph, db)
    assert user_id == 3  # Next after 2 is 3

def test_fallback_to_admin(sample_users, sample_instance):
    db = DummyDB(sample_users, sample_instance, [], [])
    graph = {"steps": {"review": {"assignment": {"rules": [], "fallback": "admin"}}}}
    user_id = resolve_assignee(1, "review", graph, db)
    assert user_id == 1

def test_legacy_role(sample_users, sample_instance):
    db = DummyDB(sample_users, sample_instance, [], [])
    graph = {"steps": {"review": {"role": "Inspector"}}}
    user_id = resolve_assignee(1, "review", graph, db)
    assert user_id == 4
