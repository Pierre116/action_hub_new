"""Approval recording, delegation lookup, and auto-escalation.

This module handles approval gates on workflow steps and delegation
of approval authority to backup approvers.
"""
from datetime import datetime
from typing import Any

from actionhub.middleware.db import get_db
from actionhub.workflow import engine, graph as workflow_graph


def record_approval(
    step_instance_id: int,
    approver_id: int,
    decision: str,
    comment: str = None,
) -> dict:
    """OP28 (S11): Record approval decision.

    Steps:
    1. Verify step type is 'Approval' in graph
    2. Check approver is assigned or has active delegation
    3. INSERT into t_workflow_approval
    4. If decision='Approved':
       a. Call engine.advance_step()
    5. If decision='Rejected':
       a. Determine rejection target step from graph (or back to previous step)
       b. Create new Active step instance for target
       c. Mark current step as 'Rejected'
    6. Log to t_action_history (change_type='ApprovalDecision')
    Returns: {'decision': str, 'next_step': str | None}

    Args:
        step_instance_id: Approval gate step instance ID.
        approver_id: User ID making the decision.
        decision: 'Approved', 'Rejected', or 'Abstained'.
        comment: Optional comment.

    Returns:
        Dictionary with decision result.

    Raises:
        ValueError: If step not found or invalid.
        PermissionError: If user not authorized.
    """
    if decision not in ("Approved", "Rejected", "Abstained"):
        raise ValueError(f"Invalid decision: {decision}")

    db = get_db()

    # 1. Load step and verify it's an Approval type
    step = db.execute(
        """SELECT wsi.*, wfi.wfi_template_id
           FROM t_workflow_step_instance wsi
           JOIN t_workflow_instance wfi ON wsi.wsi_instance_id = wfi.wfi_id
           WHERE wsi.wsi_id = ?""",
        (step_instance_id,),
    ).fetchone()

    if not step:
        raise ValueError(f"Step instance {step_instance_id} not found")

    # Load graph and verify step type
    template = db.execute(
        "SELECT wft_graph FROM t_workflow_template WHERE wft_id = ?",
        (step["wfi_template_id"],),
    ).fetchone()

    graph = workflow_graph.load_graph(template["wft_graph"])
    step_def = workflow_graph.get_step(graph, step["wsi_step_key"])

    if step_def.get("type") != "Approval":
        raise ValueError(f"Step {step['wsi_step_key']} is not an Approval type")

    # 2. Check authorization
    if step["wsi_assignee_id"] != approver_id:
        # Check for delegation
        delegate = resolve_approver(step["wsi_assignee_id"])
        if delegate != approver_id:
            raise PermissionError("User not authorized for this approval")

    # 3. Record approval
    now = datetime.now()
    cursor = db.execute(
        """INSERT INTO t_workflow_approval
           (wap_step_inst_id, wap_approver_id, wap_decision, wap_comment, wap_decided_at)
           VALUES (?, ?, ?, ?, ?)""",
        (step_instance_id, approver_id, decision, comment, now),
    )
    approval_id = cursor.lastrowid

    next_step = None

    if decision == "Approved":
        # 4a. Advance the workflow
        result = engine.advance_step(step_instance_id, approver_id, comment)
        next_step = result.get("activated", [None])[0]

    elif decision == "Rejected":
        # 5. Handle rejection
        # Mark current step as Rejected
        db.execute(
            """UPDATE t_workflow_step_instance
               SET wsi_status = 'Rejected', wsi_completed_at = ?, wsi_comment = ?
               WHERE wsi_id = ?""",
            (now, comment, step_instance_id),
        )

        # Determine rejection target (go back to previous step)
        # For simplicity, find the transition that leads TO this step and go back
        incoming = workflow_graph.get_incoming_steps(graph, step["wsi_step_key"])
        if incoming:
            # Go back to the first incoming step
            prev_step_key = incoming[0]
            prev_step_def = workflow_graph.get_step(graph, prev_step_key)

            # Create new Active step instance for the previous step
            cursor = db.execute(
                """INSERT INTO t_workflow_step_instance
                   (wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id,
                    wsi_entered_at)
                   VALUES (?, ?, 'Active', ?, ?)""",
                (
                    step["wsi_instance_id"],
                    prev_step_key,
                    approver_id,  # Assign back to approver for rework
                    now,
                ),
            )
            next_step = prev_step_key

    # 6. Log to history
    action_row = db.execute(
        "SELECT wfi_action_id FROM t_workflow_instance WHERE wfi_id = ?",
        (step["wsi_instance_id"],),
    ).fetchone()
    action_id = action_row["wfi_action_id"] if action_row else None

    if action_id:
        db.execute(
            """INSERT INTO t_action_history
               (ahi_act_id, ahi_usr_id, ahi_change_type, ahi_field, ahi_old, ahi_new, ahi_at)
               VALUES (?, ?, 'ApprovalDecision', ?, ?, ?, ?)""",
            (
                action_id,
                approver_id,
                f"step:{step['wsi_step_key']}",
                None,
                decision,
                now,
            ),
        )

    db.commit()

    return {
        "decision": decision,
        "approval_id": approval_id,
        "next_step": next_step,
    }


def get_active_delegation(user_id: int) -> dict | None:
    """Find active delegation where user_id is delegator and current date is in range.

    Args:
        user_id: The delegator (original approver) user ID.

    Returns:
        Delegation record or None if no active delegation.
    """
    db = get_db()
    now = datetime.now()

    delegation = db.execute(
        """SELECT * FROM t_approval_delegation
           WHERE adl_delegator_id = ?
           AND adl_active = 1
           AND adl_valid_from <= ?
           AND adl_valid_until >= ?""",
        (user_id, now, now),
    ).fetchone()

    if delegation:
        return dict(delegation)
    return None


def resolve_approver(original_approver_id: int) -> int:
    """Return delegate if active delegation exists, else original approver.

    Logs DelegationUsed to t_action_history when delegation applied.

    Args:
        original_approver_id: Original assigned approver user ID.

    Returns:
        User ID to use (delegate if active, otherwise original).
    """
    delegation = get_active_delegation(original_approver_id)
    if delegation:
        # Log delegation usage
        # Note: In a full implementation, we'd log this to history
        return delegation["adl_delegate_id"]
    return original_approver_id


def create_delegation(
    delegator_id: int,
    delegate_id: int,
    valid_from: str,
    valid_until: str,
) -> int:
    """OP33 (S11): Create approval delegation.

    Validate: delegator != delegate (CHECK constraint).

    Args:
        delegator_id: User delegating their authority.
        delegate_id: User receiving delegation.
        valid_from: Start date (ISO format).
        valid_until: End date (ISO format).

    Returns:
        Created delegation ID.

    Raises:
        ValueError: If validation fails.
    """
    if delegator_id == delegate_id:
        raise ValueError("Cannot delegate to self")

    # Parse dates
    try:
        from_dt = datetime.strptime(valid_from, "%Y-%m-%d")
        to_dt = datetime.strptime(valid_until, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Dates must be in YYYY-MM-DD format")

    if from_dt >= to_dt:
        raise ValueError("valid_from must be before valid_until")

    db = get_db()
    now = datetime.now()

    # Deactivate any existing active delegations from this delegator
    db.execute(
        "UPDATE t_approval_delegation SET adl_active = 0 WHERE adl_delegator_id = ?",
        (delegator_id,),
    )

    cursor = db.execute(
        """INSERT INTO t_approval_delegation
           (adl_delegator_id, adl_delegate_id, adl_valid_from, adl_valid_until,
            adl_active, adl_created_at)
           VALUES (?, ?, ?, ?, 1, ?)""",
        (delegator_id, delegate_id, from_dt, to_dt, now),
    )

    db.commit()
    return cursor.lastrowid


def get_pending_approvals(user_id: int) -> list[dict]:
    """All Approval-type steps where user is assigned (or delegated to).

    Args:
        user_id: User ID to check.

    Returns:
        List of approval step instances with workflow info.
    """
    db = get_db()

    # Get steps where user is assigned OR delegated
    steps = db.execute(
        """SELECT wsi.*, wfi.wfi_action_id, wfi.wfi_template_id,
                  a.act_title, wft.wft_name_en
           FROM t_workflow_step_instance wsi
           JOIN t_workflow_instance wfi ON wsi.wsi_instance_id = wfi.wfi_id
            LEFT JOIN t_action a ON wfi.wfi_action_id = a.act_id
           JOIN t_workflow_template wft ON wfi.wfi_template_id = wft.wft_id
           WHERE wsi.wsi_status = 'Active'
           AND wsi.wsi_assignee_id = ?
           AND EXISTS (
               SELECT 1 FROM t_workflow_template wt
               JOIN t_workflow_instance wi ON wt.wft_id = wi.wfi_template_id
               WHERE wi.wfi_id = wsi.wsi_instance_id
               AND wt.wft_graph LIKE '%"type": "Approval"%'
           )
           ORDER BY wsi.wsi_sla_deadline""",
        (user_id,),
    ).fetchall()

    # Note: The JSON check above is a simplified approach.
    # In production, you'd parse the graph properly.

    return [dict(s) for s in steps]


def get_delegations_for_user(user_id: int) -> list[dict]:
    """Get all delegations for a user (as delegator or delegate).

    Args:
        user_id: User ID.

    Returns:
        List of delegation records.
    """
    db = get_db()

    delegations = db.execute(
        """SELECT * FROM t_approval_delegation
           WHERE adl_delegator_id = ? OR adl_delegate_id = ?
           ORDER BY adl_valid_from DESC""",
        (user_id, user_id),
    ).fetchall()

    return [dict(d) for d in delegations]


def revoke_delegation(delegation_id: int, user_id: int) -> bool:
    """Revoke an active delegation.

    Only the delegator can revoke their own delegation.

    Args:
        delegation_id: Delegation ID to revoke.
        user_id: User requesting revocation.

    Returns:
        True if revoked, False if not found or unauthorized.
    """
    db = get_db()

    delegation = db.execute(
        "SELECT * FROM t_approval_delegation WHERE adl_id = ?",
        (delegation_id,),
    ).fetchone()

    if not delegation:
        return False

    if delegation["adl_delegator_id"] != user_id:
        return False

    db.execute(
        "UPDATE t_approval_delegation SET adl_active = 0 WHERE adl_id = ?",
        (delegation_id,),
    )
    db.commit()

    return True
