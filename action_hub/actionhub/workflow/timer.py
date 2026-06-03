"""Timer step expiry handler for Workflow V3 (WF-14)."""
from datetime import datetime, timedelta
from actionhub.middleware.db import get_db
from actionhub.notifications import create_notification
from actionhub.workflow.engine import get_active_steps, complete_workflow, get_next_steps, get_step


def handle_timer_expiry(step_instance_id: int) -> dict:
    """
    Handles Timer step expiry:
    - If on_expire == 'escalate': reassign preceding human step to team lead, notify, log.
    - If on_expire == 'advance': mark timer Completed, activate next step.
    """
    db = get_db()
    # 1. Load timer step instance and definition
    timer_step = db.execute(
        "SELECT wsi_id, wsi_instance_id, wsi_step_key, wsi_status, wsi_completed_at FROM t_workflow_step_instance WHERE wsi_id = ?",
        (step_instance_id,)
    ).fetchone()
    if not timer_step:
        return {"error": "Timer step instance not found"}
    if timer_step["wsi_status"] == "Completed":
        return {"status": "Already completed"}
    # Load workflow graph
    instance = db.execute(
        "SELECT wfi_template_id, wfi_action_id FROM t_workflow_instance WHERE wfi_id = ?",
        (timer_step["wsi_instance_id"],)
    ).fetchone()
    template = db.execute(
        "SELECT wft_graph FROM t_workflow_template WHERE wft_id = ?",
        (instance["wfi_template_id"],)
    ).fetchone()
    import json
    graph = json.loads(template["wft_graph"])
    step_def = get_step(graph, timer_step["wsi_step_key"])
    timer_conf = step_def or {}
    on_expire = timer_conf.get("on_expire", "escalate")
    now = datetime.now()
    # 2. Handle expiry action
    if on_expire == "advance":
        # Mark timer as completed
        db.execute(
            "UPDATE t_workflow_step_instance SET wsi_status = 'Completed', wsi_completed_at = ? WHERE wsi_id = ?",
            (now, step_instance_id)
        )
        # Activate next step(s)
        next_keys = get_next_steps(graph, timer_step["wsi_step_key"])
        for next_key in next_keys:
            next_def = get_step(graph, next_key)
            db.execute(
                "INSERT INTO t_workflow_step_instance (wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id, wsi_entered_at) VALUES (?, ?, 'Pending', NULL, ?)",
                (timer_step["wsi_instance_id"], next_key, now)
            )
            if next_def.get("type") == "End":
                complete_workflow(timer_step["wsi_instance_id"], db)
        db.commit()
        return {"status": "Timer advanced"}
    # Default: escalate
    # Find preceding human step (last Completed before timer)
    prev_step = db.execute(
        """
        SELECT wsi_id, wsi_step_key, wsi_assignee_id FROM t_workflow_step_instance
        WHERE wsi_instance_id = ? AND wsi_completed_at IS NOT NULL AND wsi_id < ?
        ORDER BY wsi_completed_at DESC LIMIT 1
        """,
        (timer_step["wsi_instance_id"], step_instance_id)
    ).fetchone()
    if not prev_step:
        return {"error": "No preceding human step found for escalation"}
    # Find team lead for escalation
    action = db.execute(
        "SELECT act_team_id FROM t_action WHERE act_id = ?",
        (instance["wfi_action_id"],)
    ).fetchone()
    team_lead = db.execute(
        "SELECT usr_id FROM t_user WHERE usr_team_id = ? AND usr_role = 'TeamLead' AND usr_active = 1",
        (action["act_team_id"],)
    ).fetchone()
    if not team_lead:
        return {"error": "No team lead found for escalation"}
    # Reassign previous step to team lead
    db.execute(
        "UPDATE t_workflow_step_instance SET wsi_assignee_id = ?, wsi_status = 'Escalated', wsi_escalated_at = ? WHERE wsi_id = ?",
        (team_lead["usr_id"], now, prev_step["wsi_id"])
    )
    # Mark timer as completed
    db.execute(
        "UPDATE t_workflow_step_instance SET wsi_status = 'Completed', wsi_completed_at = ? WHERE wsi_id = ?",
        (now, step_instance_id)
    )
    # Create escalation notification
    create_notification(team_lead["usr_id"], "workflow_timer_escalation", f"Timer expired: {step_def.get('name_en', timer_step['wsi_step_key'])}", f"Step escalated due to timer expiry.", instance["wfi_action_id"])
    db.commit()
    return {"status": "Timer escalated to team lead"}
