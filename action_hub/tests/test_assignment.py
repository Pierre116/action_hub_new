import pytest
import logging
logging.basicConfig(level=logging.DEBUG)
from actionhub.middleware.db import get_db
from actionhub.workflow.assignment import resolve_assignee

@pytest.fixture
def setup_round_robin(db):
    """Setup database state for round-robin tests."""
    db.execute("DELETE FROM t_user")
    db.execute("INSERT INTO t_user (usr_id, usr_team_id, usr_role, usr_active, usr_username, usr_pwd_hash, usr_email, usr_display_name) VALUES (1, 1, 'Member', 1, 'user1', 'hash1', 'user1@example.com', 'User One')")
    db.execute("INSERT INTO t_user (usr_id, usr_team_id, usr_role, usr_active, usr_username, usr_pwd_hash, usr_email, usr_display_name) VALUES (2, 1, 'Member', 1, 'user2', 'hash2', 'user2@example.com', 'User Two')")
    db.execute("DELETE FROM t_workflow_instance")
    db.execute("DELETE FROM t_workflow_template")
    db.execute("DELETE FROM t_action")
    db.execute(
        """INSERT INTO t_workflow_template
           (wft_id, wft_name_en, wft_name_cn, wft_graph, wft_type, wft_active, wft_created_by, wft_created_at)
           VALUES (1, 'Round Robin', 'Round Robin', '{}', 'action', 1, 1, datetime('now'))"""
    )
    db.execute(
        """INSERT INTO t_action
           (act_id, act_ref, act_title, act_topic_id, act_team_id, act_priority, act_status, act_created_by)
           VALUES (1, 'ACT-TEST-001', 'Round Robin Action', 1, 1, 'Medium', 'Open', 1)"""
    )
    db.execute(
        """INSERT INTO t_workflow_instance
           (wfi_id, wfi_template_id, wfi_action_id, wfi_status, wfi_started_by, wfi_started_at)
           VALUES (1, 1, 1, 'Active', 1, datetime('now'))"""
    )
    db.execute("DELETE FROM t_workflow_assignment_counter")
    db.execute("INSERT INTO t_workflow_assignment_counter (wrc_template_id, wrc_step_key, wrc_last_user_id) VALUES (1, 'step1', 1)")
    db.commit()

def test_round_robin_assignment(db, setup_round_robin):
    """Test round-robin assignment rule."""
    graph = {
        "steps": {
            "step1": {
                "assignment": {
                    "rules": [
                        {"type": "round_robin", "role": "Member", "team_source": "action_team"}
                    ]
                }
            }
        }
    }
    instance_id = 1
    step_key = "step1"

    # First call should assign to user 2
    user_id = resolve_assignee(instance_id, step_key, graph, db)
    print(f"First call assigned to user {user_id}")
    assert user_id == 2

    # Second call should assign back to user 1
    user_id = resolve_assignee(instance_id, step_key, graph, db)
    print(f"Second call assigned to user {user_id}")
    assert user_id == 1

    # Verify counter update
    counter = db.execute("SELECT wrc_last_user_id FROM t_workflow_assignment_counter WHERE wrc_template_id = 1 AND wrc_step_key = 'step1'").fetchone()
    print(f"Counter value: {counter}")
    assert counter["wrc_last_user_id"] == 1