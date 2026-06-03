"""SLA monitoring — APScheduler periodic check (D180).

This module provides background job functionality for checking SLA breaches
on workflow step instances and creating notifications.
"""
import logging
from datetime import datetime, timedelta
from typing import Any

from actionhub.middleware.db import get_db
from actionhub.notifications import create_notification

logger = logging.getLogger(__name__)


def check_sla_breaches():
    """OP30 (S11): Periodic check for SLA breaches.

    Runs periodically to:
    1. SELECT from t_workflow_step_instance
       WHERE wsi_status = 'Active' AND wsi_sla_deadline < CURRENT_TIMESTAMP
    2. For each breached step:
       a. Create in-app notification for assignee
       b. Create notification for team lead
       c. Log to t_action_history (change_type='SLABreach')
    3. Do NOT re-notify if already notified (check existing notification)

    Note: This is called by APScheduler. In test mode, call directly.
    """
    db = get_db()
    now = datetime.now()


    # Find breached steps (Active/Accepted) and Timer steps (Pending) past deadline
    breached_steps = db.execute(
        """SELECT wsi.*, wfi.wfi_action_id, wft.wft_name_en
           FROM t_workflow_step_instance wsi
           JOIN t_workflow_instance wfi ON wsi.wsi_instance_id = wfi.wfi_id
           JOIN t_workflow_template wft ON wfi.wfi_template_id = wft.wft_id
           WHERE ((wsi.wsi_status = 'Active' AND wsi.wsi_sla_deadline IS NOT NULL)
                  OR (wsi.wsi_status = 'Pending' AND wsi.wsi_sla_deadline IS NOT NULL))
           AND wsi.wsi_sla_deadline < ?""",
        (now,),
    ).fetchall()

    if not breached_steps:
        logger.info("No SLA or Timer breaches detected")
        return

    logger.info(f"Found {len(breached_steps)} SLA/Timer breaches")

    from actionhub.workflow.engine import get_step, load_graph
    from actionhub.workflow.timer import handle_timer_expiry

    for step in breached_steps:
        # Determine if this is a Timer step (Pending, type=Timer in graph)
        if step["wsi_status"] == "Pending":
            # Load workflow graph and step definition
            template = db.execute(
                "SELECT wft_graph FROM t_workflow_template WHERE wft_id = ?",
                (step["wfi_template_id"],)
            ).fetchone()
            if template:
                graph = load_graph(template["wft_graph"])
                step_def = get_step(graph, step["wsi_step_key"])
                if step_def and step_def.get("type") == "Timer":
                    logger.info(f"Timer step expired: {step['wsi_id']}")
                    handle_timer_expiry(step["wsi_id"])
                    continue
        # Otherwise, handle as SLA breach
        _handle_sla_breach(db, step)

    db.commit()


def _handle_sla_breach(db: Any, step: dict):
    """Handle a single SLA breach.

    Creates notifications for assignee and team lead.
    """
    step_id = step["wsi_id"]
    action_id = step["wfi_action_id"]
    workflow_name = step["wft_name_en"]
    assignee_id = step["wsi_assignee_id"]
    step_key = step["wsi_step_key"]

    # Check if already notified recently (within last hour) - use correct column names
    recent_notification = db.execute(
        """SELECT ntf_id FROM t_notification
           WHERE ntf_action_id = ?
           AND ntf_event_type LIKE 'sla_%'
           AND ntf_created_at > datetime('now', '-1 hour')""",
        (action_id,),
    ).fetchone()

    if recent_notification:
        logger.debug(f"Step {step_id} already notified recently, skipping")
        return

    # Create notification for assignee
    if assignee_id:
        create_notification(
            user_id=assignee_id,
            event_type="sla_breach",
            title=f"SLA Breach: {workflow_name} - {step_key}",
            body=f"Step '{step_key}' has exceeded its SLA deadline",
            action_id=action_id,
        )

    # Get team lead for the action
    team_lead = db.execute(
        """SELECT asg.asg_user_id FROM t_assignment asg
           WHERE asg.asg_action_id = ? AND asg.asg_role = 'Lead'""",
        (action_id,),
    ).fetchone()

    if team_lead and team_lead["aas_usr_id"] != assignee_id:
        create_notification(
            user_id=team_lead["aas_usr_id"],
            event_type="sla_breach_alert",
            title=f"SLA Breach Alert: {workflow_name}",
            body=f"Team member overdue on step '{step_key}'",
            action_id=action_id,
        )

    # Log to action history
    db.execute(
        """INSERT INTO t_action_history
           (ahi_act_id, ahi_usr_id, ahi_change_type, ahi_field, ahi_old, ahi_new, ahi_at)
           VALUES (?, 1, 'SLABreach', ?, NULL, ?, ?)""",
        (action_id, f"step:{step_key}", "breached", now),
    )

    logger.info(f"SLA breach handled for step {step_id}")


def init_sla_scheduler(app):
    """Initialize APScheduler with SLA check job.

    Call from create_app() in __init__.py.
    Only runs in non-testing, non-frozen environments.

    Args:
        app: Flask application instance.
    """
    if app.config.get("TESTING"):
        logger.info("SLA scheduler disabled in test mode")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            check_sla_breaches,
            "interval",
            minutes=15,
            id="sla_check",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("SLA scheduler started (runs every 15 minutes)")

        # Shut down scheduler when app context ends
        import atexit

        atexit.register(lambda: scheduler.shutdown())

    except ImportError:
        logger.warning("APScheduler not installed, SLA monitoring disabled")
    except Exception as e:
        logger.error(f"Failed to start SLA scheduler: {e}")


def get_sla_status(step_instance_id: int) -> dict:
    """Get SLA status for a step instance.

    Args:
        step_instance_id: Step instance ID.

    Returns:
        Dictionary with SLA status information.
    """
    db = get_db()

    step = db.execute(
        """SELECT wsi_status, wsi_entered_at, wsi_sla_deadline
           FROM t_workflow_step_instance
           WHERE wsi_id = ?""",
        (step_instance_id,),
    ).fetchone()

    if not step:
        return {"error": "Step not found"}

    if step["wsi_status"] != "Active":
        return {"status": "not_active", "message": "Step is not active"}

    if not step["wsi_sla_deadline"]:
        return {"status": "no_sla", "message": "No SLA set for this step"}

    now = datetime.now()
    deadline = step["wsi_sla_deadline"]

    if now > deadline:
        # Calculate how overdue
        overdue = now - deadline
        hours_overdue = overdue.total_seconds() / 3600
        return {
            "status": "breached",
            "hours_overdue": round(hours_overdue, 1),
            "deadline": deadline.isoformat(),
        }
    else:
        # Calculate time remaining
        remaining = deadline - now
        hours_remaining = remaining.total_seconds() / 3600
        return {
            "status": "on_track",
            "hours_remaining": round(hours_remaining, 1),
            "deadline": deadline.isoformat(),
        }
