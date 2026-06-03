"""
assignment.py — Declarative assignment rule resolver (WF-19, S72)
"""
import sqlite3
from typing import Optional, Dict, Any

RULE_TYPES = {"static_user", "role_in_team", "prior_step_actor", "workflow_creator", "round_robin"}


def _get_action_team_id(instance_id: int, db: sqlite3.Connection) -> Optional[int]:
    row = db.execute(
        "SELECT act_team_id FROM t_workflow_instance JOIN t_action ON wfi_action_id = act_id WHERE wfi_id = ?",
        (instance_id,),
    ).fetchone()
    return row["act_team_id"] if row else None

# --- Main entry point ---
def resolve_assignee(instance_id: int, step_key: str, graph: dict, db: sqlite3.Connection) -> Optional[int]:
    """
    Resolves the assignee user_id for a workflow step using assignment rules.
    Returns user_id or None if no eligible user found.
    """
    step = graph["steps"].get(step_key) or {}
    assignment = step.get("assignment")
    if assignment and "rules" in assignment:
        for rule in assignment["rules"]:
            user_id = _resolve_rule(rule, instance_id, step_key, graph, db)
            if user_id:
                return user_id
        # Fallback
        fallback = assignment.get("fallback", "workflow_creator")
        if fallback == "workflow_creator":
            return _get_workflow_creator(instance_id, db)
        elif fallback == "admin":
            return _get_first_admin(db)
        return None
    # Legacy: role field
    if "role" in step:
        return _resolve_legacy_role(step["role"], instance_id, db)
    # Default: workflow creator
    return _get_workflow_creator(instance_id, db)

# --- Rule resolvers ---
def _resolve_rule(rule: Dict[str, Any], instance_id: int, step_key: str, graph: dict, db: sqlite3.Connection) -> Optional[int]:
    t = rule.get("type")
    if t == "static_user":
        return _static_user(rule, db)
    if t == "role_in_team":
        return _role_in_team(rule, instance_id, db)
    if t == "prior_step_actor":
        return _prior_step_actor(rule, instance_id, db)
    if t == "workflow_creator":
        return _get_workflow_creator(instance_id, db)
    if t == "round_robin":
        return _round_robin(rule, instance_id, step_key, db)
    return None

def _static_user(rule, db):
    user_id = rule.get("user_id")
    if not user_id:
        return None
    row = db.execute("SELECT usr_id FROM t_user WHERE usr_id = ? AND usr_active = 1", (user_id,)).fetchone()
    return row["usr_id"] if row else None

def _role_in_team(rule, instance_id, db):
    role = rule.get("role")
    team_source = rule.get("team_source", "action_team")
    if not role:
        return None
    # Get team_id
    if team_source == "action_team":
        team_id = _get_action_team_id(instance_id, db)
    elif team_source.startswith("step_field:"):
        # Not implemented: custom field source
        return None
    else:
        return None
    if not team_id:
        return None
    row = db.execute("SELECT usr_id FROM t_user WHERE usr_team_id = ? AND usr_role = ? AND usr_active = 1 ORDER BY usr_display_name LIMIT 1", (team_id, role)).fetchone()
    return row["usr_id"] if row else None

def _prior_step_actor(rule, instance_id, db):
    step_key = rule.get("step_key")
    if not step_key:
        return None
    row = db.execute("SELECT wsi_assignee_id FROM t_workflow_step_instance WHERE wsi_instance_id = ? AND wsi_step_key = ? AND wsi_status = 'Completed' ORDER BY wsi_completed_at DESC LIMIT 1", (instance_id, step_key)).fetchone()
    return row["wsi_assignee_id"] if row else None

def _get_workflow_creator(instance_id, db):
    row = db.execute(
        "SELECT wfi_started_by FROM t_workflow_instance WHERE wfi_id = ?",
        (instance_id,),
    ).fetchone()
    return row["wfi_started_by"] if row else None

def _get_first_admin(db):
    row = db.execute("SELECT usr_id FROM t_user WHERE usr_role = 'Admin' AND usr_active = 1 ORDER BY usr_id LIMIT 1").fetchone()
    return row["usr_id"] if row else None

def _resolve_legacy_role(role, instance_id, db):
    row = db.execute("SELECT usr_id FROM t_user WHERE usr_role = ? AND usr_active = 1 ORDER BY usr_display_name LIMIT 1", (role,)).fetchone()
    return row["usr_id"] if row else None

def _round_robin(rule, instance_id, step_key, db):
    role = rule.get("role")
    team_source = rule.get("team_source", "action_team")
    if not role:
        return None
    # Get team_id
    if team_source == "action_team":
        team_id = _get_action_team_id(instance_id, db)
    else:
        return None
    if not team_id:
        return None
    users = db.execute("SELECT usr_id, usr_display_name FROM t_user WHERE usr_team_id = ? AND usr_role = ? AND usr_active = 1 ORDER BY usr_display_name", (team_id, role)).fetchall()
    if not users:
        return None
    # Get last assigned user
    template_id_row = db.execute(
        "SELECT wfi_template_id FROM t_workflow_instance WHERE wfi_id = ?",
        (instance_id,),
    ).fetchone()
    template_id = template_id_row["wfi_template_id"] if template_id_row else None
    if not template_id:
        return None
    counter = db.execute("SELECT wrc_last_user_id FROM t_workflow_assignment_counter WHERE wrc_template_id = ? AND wrc_step_key = ?", (template_id, step_key)).fetchone()
    user_ids = [u["usr_id"] for u in users]
    # Determine next user in round-robin
    if counter and counter["wrc_last_user_id"] in user_ids:
        idx = user_ids.index(counter["wrc_last_user_id"])
        next_idx = (idx + 1) % len(user_ids)
    else:
        next_idx = 0  # Start with the first user if no counter exists

    next_user_id = user_ids[next_idx]

    # Update the counter
    if counter:
        db.execute(
            "UPDATE t_workflow_assignment_counter SET wrc_last_user_id = ? WHERE wrc_template_id = ? AND wrc_step_key = ?",
            (next_user_id, template_id, step_key),
        )
    else:
        db.execute(
            "INSERT INTO t_workflow_assignment_counter (wrc_template_id, wrc_step_key, wrc_last_user_id) VALUES (?, ?, ?)",
            (template_id, step_key, next_user_id),
        )

    return next_user_id


def get_eligible_users(instance_id: int, step_key: str, graph: dict, db: sqlite3.Connection) -> list[dict]:
    """Get list of eligible users for a step based on assignment rules.

    Used for delegation/reassignment validation.

    Args:
        instance_id: Workflow instance ID.
        step_key: Step key in the graph.
        graph: Parsed workflow graph.
        db: Database connection.

    Returns:
        List of user dicts with usr_id and usr_display_name.
    """
    step = graph["steps"].get(step_key) or {}
    assignment = step.get("assignment")

    # If no assignment block, use role-based lookup
    if not assignment or "rules" not in assignment:
        role = step.get("role")
        if not role:
            # No role constraint - all active users eligible
            rows = db.execute(
                "SELECT usr_id, usr_display_name FROM t_user WHERE usr_active = 1 ORDER BY usr_display_name"
            ).fetchall()
            return [dict(r) for r in rows]

        # Get team for role-based lookup
        team_id = _get_action_team_id(instance_id, db)

        if team_id:
            rows = db.execute(
                """SELECT usr_id, usr_display_name FROM t_user
                   WHERE usr_team_id = ? AND usr_role = ? AND usr_active = 1
                   ORDER BY usr_display_name""",
                (team_id, role),
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT usr_id, usr_display_name FROM t_user
                   WHERE usr_role = ? AND usr_active = 1
                   ORDER BY usr_display_name""",
                (role,),
            ).fetchall()
        return [dict(r) for r in rows]

    # Process assignment rules to determine eligible pool
    for rule in assignment.get("rules", []):
        rule_type = rule.get("type")

        if rule_type == "static_user":
            user_id = rule.get("user_id")
            if user_id:
                row = db.execute(
                    "SELECT usr_id, usr_display_name FROM t_user WHERE usr_id = ? AND usr_active = 1",
                    (user_id,),
                ).fetchone()
                if row:
                    return [dict(row)]

        elif rule_type == "role_in_team":
            role = rule.get("role")
            team_source = rule.get("team_source", "action_team")

            if team_source == "action_team":
                team_id = _get_action_team_id(instance_id, db)
            else:
                team_id = None

            if role and team_id:
                rows = db.execute(
                    """SELECT usr_id, usr_display_name FROM t_user
                       WHERE usr_team_id = ? AND usr_role = ? AND usr_active = 1
                       ORDER BY usr_display_name""",
                    (team_id, role),
                ).fetchall()
                return [dict(r) for r in rows]

        elif rule_type == "round_robin":
            role = rule.get("role")
            team_source = rule.get("team_source", "action_team")

            if team_source == "action_team":
                team_id = _get_action_team_id(instance_id, db)
            else:
                team_id = None

            if role and team_id:
                rows = db.execute(
                    """SELECT usr_id, usr_display_name FROM t_user
                       WHERE usr_team_id = ? AND usr_role = ? AND usr_active = 1
                       ORDER BY usr_display_name""",
                    (team_id, role),
                ).fetchall()
                return [dict(r) for r in rows]

    # Fallback: return empty list (caller should handle)
    return []
