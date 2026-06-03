"""Workflow engine — instantiate, advance, resolve joins, complete.

This module contains the core workflow execution logic. All database
operations use get_db() for raw parameterized queries.
"""
import json
from datetime import datetime
from typing import Any

from actionhub.middleware.db import get_db
from actionhub.workflow.graph import (
    load_graph,
    get_start_steps,
    get_next_steps,
    is_fork,
    is_join,
    get_step,
    get_fields_for_step,
)

from actionhub.utils.history import log_action_history
from actionhub.workflow.assignment import resolve_assignee


def _get_instance_action_id(db: Any, instance_id: int) -> int | None:
    instance = db.execute(
        "SELECT wfi_action_id FROM t_workflow_instance WHERE wfi_id = ?",
        (instance_id,),
    ).fetchone()
    if not instance:
        return None
    return instance["wfi_action_id"]


def _log_action_history_if_bound(
    db: Any,
    instance_id: int,
    user_id: int,
    change_type: str,
    field_name: str,
    old_value: str | None,
    new_value: str | None,
) -> None:
    action_id = _get_instance_action_id(db, instance_id)
    if not action_id:
        return
    log_action_history(
        action_id=action_id,
        user_id=user_id,
        change_type=change_type,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
    )


def instantiate_workflow(
    template_id: int, 
    action_id: int | None,
    started_by: int,
    category_id: int = None,
    secondary_category_id: int = None
) -> int:
    """Create a workflow instance + initial step instances.

    Manual workflow creation only — never auto-triggered.

    Steps:
    1. Load template and parse wft_graph
    2. INSERT into t_workflow_instance (wfi_template_id, wfi_action_id)
    3. Get start steps from graph
    4. For each start step:
       - INSERT into t_workflow_step_instance (status='Active', entered_at=now)
       - If start step is a fork, also create step instances for all fork targets
    5. Log to t_action_history (change_type='WorkflowAdvance', field='workflow_start')
    6. Return: wfi_id

    Args:
        template_id: The workflow template ID to instantiate.
        action_id: Optional action ID this workflow is bound to.
        started_by: User ID who started the workflow.
        category_id: Optional primary category ID.
        secondary_category_id: Optional secondary category ID.

    Returns:
        The workflow instance ID.

    Raises:
        ValueError: If template not found, invalid, or category validation fails.
    """
    db = get_db()

    # Validate secondary != primary if both provided
    if category_id and secondary_category_id and category_id == secondary_category_id:
        raise ValueError("Secondary category must differ from primary category")

    # 1. Load template
    template = db.execute(
        "SELECT wft_id, wft_graph FROM t_workflow_template WHERE wft_id = ?",
        (template_id,),
    ).fetchone()

    if not template:
        raise ValueError(f"Template {template_id} not found")

    graph = load_graph(template["wft_graph"])
    start_step_keys = get_start_steps(graph)

    if not start_step_keys:
        raise ValueError("No start steps found in workflow graph")

    # 2. Create workflow instance (no category fields)
    now = datetime.now()
    cursor = db.execute(
        """INSERT INTO t_workflow_instance
           (wfi_template_id, wfi_action_id, wfi_status, wfi_started_by, wfi_started_at)
           VALUES (?, ?, 'Active', ?, ?)""",
        (template_id, action_id, started_by, now),
    )
    instance_id = cursor.lastrowid

    # 3 & 4. Create step instances (WF-10: all start as Pending, require accept)
    created_steps = []
    for start_key in start_step_keys:
        step_def = get_step(graph, start_key)
        # Use assignment rule for assignee if present
        assignee_id = resolve_assignee(instance_id, start_key, graph, db) or started_by
        _create_step_instance(
            db, instance_id, start_key, "Pending", assignee_id, None, step_def
        )
        created_steps.append(start_key)

        # If start step is a fork, also create step instances for all fork targets
        if is_fork(graph, start_key):
            next_keys = get_next_steps(graph, start_key)
            for next_key in next_keys:
                next_def = get_step(graph, next_key)
                assignee_id = resolve_assignee(instance_id, next_key, graph, db)
                _create_step_instance(
                    db, instance_id, next_key, "Pending", assignee_id, None, next_def
                )

    # 5. Log to history
    if action_id:
        log_action_history(
            action_id=action_id,
            user_id=started_by,
            change_type="WorkflowAdvance",
            field_name="workflow_start",
            old_value=None,
            new_value=f"Instance {instance_id} created",
        )

    db.commit()

    return instance_id


def _create_step_instance(
    db: Any,
    instance_id: int,
    step_key: str,
    status: str,
    assignee_id: int | None,
    entered_at: datetime | None,
    step_def: dict,
) -> int:
    """Create a step instance record.

    Args:
        db: Database connection.
        instance_id: Parent workflow instance ID.
        step_key: Step key from graph.
        status: Initial status (Pending/Active).
        assignee_id: Assigned user ID (None for Pending).
        entered_at: When step became active (None for Pending).
        step_def: Step definition from graph.

    Returns:
        Created step instance ID.
    """
    # Calculate SLA deadline if step has sla_hours and is becoming active/accepted
    sla_deadline = None
    if status in ("Active", "Accepted") and entered_at and step_def.get("sla_hours"):
        from datetime import timedelta

        sla_hours = step_def["sla_hours"]
        sla_deadline = entered_at + timedelta(hours=sla_hours)

    cursor = db.execute(
        """INSERT INTO t_workflow_step_instance
           (wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id,
            wsi_entered_at, wsi_sla_deadline)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (instance_id, step_key, status, assignee_id, entered_at, sla_deadline),
    )
    return cursor.lastrowid


def advance_step(step_instance_id: int, completed_by: int, comment: str = None, next_assignee_id: int = None) -> dict:
    """
    Complete current step and activate next step(s).

    OP26 (S11): User clicks "Done ✓".

    3-Phase Lifecycle (WF-10):
    - Pending -> Accept -> Accepted (work begins, SLA starts)
    - Accepted -> Advance -> Completed (work done)

    Steps:
    1. Load step instance, verify status='Accepted' (WF-10) or 'Active' (V2 backward compat)
    2. UPDATE step instance: status='Completed', completed_at=now, comment
    3. Load graph from template
    4. Get next steps from graph
    5. For each next step:
       a. If Join -> call resolve_join()
       b. If End -> call complete_workflow()
       c. If Task -> INSERT new step instance (status='Pending' for V3, 'Active' for V2)
       d. If fork from next step -> create multiple step instances
    6. Compute SLA deadline for new active steps (entered_at + sla_hours)
    7. Log to t_action_history
    8. Create notification for new assignee(s)
    Returns: {'completed': step_key, 'activated': [step_keys], 'workflow_completed': bool}

    Args:
        step_instance_id: The step instance ID to advance.
        completed_by: User ID completing the step.
        comment: Optional comment.

    Returns:
        Dictionary with keys: completed, activated, workflow_completed.

    Raises:
        ValueError: If step not found or not in Active/Accepted status.
    """
    db = get_db()
    timeline = []
    eligible_users = []

    # 1. Load step instance
    step_inst = db.execute(
        """SELECT wsi_id, wsi_instance_id, wsi_step_key, wsi_status
           FROM t_workflow_step_instance WHERE wsi_id = ?""",
        (step_instance_id,),
    ).fetchone()

    if not step_inst:
        raise ValueError(f"Step instance {step_instance_id} not found")

    if step_inst["wsi_status"] not in ("Active", "Accepted"):
        raise ValueError(
            f"Cannot advance step in '{step_inst['wsi_status']}' status. "
            "Only Accepted (or Active for V2 workflows) steps can be advanced."
        )

    # 2. Mark current step as completed
    now = datetime.now()
    db.execute(
        """UPDATE t_workflow_step_instance
           SET wsi_status = 'Completed', wsi_completed_at = ?, wsi_comment = ?
           WHERE wsi_id = ?""",
        (now, comment, step_instance_id),
    )

    # Load instance to get template and action
    instance = db.execute(
        """SELECT wfi_id, wfi_template_id, wfi_action_id
           FROM t_workflow_instance WHERE wfi_id = ?""",
        (step_inst["wsi_instance_id"],),
    ).fetchone()

    # Load template and graph
    template = db.execute(
        "SELECT wft_graph FROM t_workflow_template WHERE wft_id = ?",
        (instance["wfi_template_id"],),
    ).fetchone()

    graph = load_graph(template["wft_graph"])
    current_step_key = step_inst["wsi_step_key"]

    # 3. Get next raw steps from graph
    next_step_keys = get_next_steps(graph, current_step_key)

    # 4a. Check if current step is a Gateway — evaluate decision table
    current_def = get_step(graph, current_step_key)
    current_type = current_def.get("type", "Task")

    from actionhub.workflow.gateway import evaluate_decision_table

    if current_type == "Gateway":
        # Only activate the single chosen outcome
        decision_table = current_def.get("decision_table", [])
        db_fields = db.execute(
            """SELECT wsf_field_code, wsf_value
               FROM t_workflow_step_field_value
               WHERE wsf_instance_id = ?""",
            (instance["wfi_id"],)
        ).fetchall()
        field_values = {row["wsf_field_code"]: row["wsf_value"] for row in db_fields}
        chosen_next = evaluate_decision_table(decision_table, field_values)
        filtered_next_step_keys = [chosen_next] if chosen_next else []
    else:
        filtered_next_step_keys = next_step_keys

    activated = []
    workflow_completed = False
    errors = []

    # 5. Process each next step
    for next_key in filtered_next_step_keys:
        next_def = get_step(graph, next_key)
        step_type = next_def.get("type", "Task")

        # Gateway: evaluate decision table, activate only the chosen outcome
        if step_type == "Gateway":
            decision_table = next_def.get("decision_table", [])
            db_fields = db.execute(
                """SELECT wsf_field_code, wsf_value
                   FROM t_workflow_step_field_value WHERE wsf_instance_id = ?""",
                (instance["wfi_id"],)
            ).fetchall()
            field_values = {row["wsf_field_code"]: row["wsf_value"] for row in db_fields}
            chosen_next = evaluate_decision_table(decision_table, field_values)
            if chosen_next:
                chosen_def = get_step(graph, chosen_next)
                _create_step_instance(
                    db, instance["wfi_id"], chosen_next, "Pending",
                    chosen_def.get("assignee_id") or completed_by, None, chosen_def
                )
                activated.append(chosen_next)
                if chosen_def.get("type") == "End":
                    complete_workflow(instance["wfi_id"], db)
                    workflow_completed = True
            continue

        # Fork: create all parallel branch instances
        if is_fork(graph, next_key):
            fork_targets = get_next_steps(graph, next_key)
            for ft_key in fork_targets:
                ft_def = get_step(graph, ft_key)
                _create_step_instance(
                    db, instance["wfi_id"], ft_key, "Pending",
                    None, None, ft_def
                )
                activated.append(ft_key)
            continue

        # WF-12: Service step — auto-execute and log
        if step_type == "Service":
            from actionhub.workflow.service_executor import service_registry
            handler_name = next_def.get("handler")
            handler = None
            try:
                handler = service_registry.get(handler_name)
            except Exception:
                handler = None
            svc_step_id = _create_step_instance(
                db, instance["wfi_id"], next_key, "Active",
                None, None, next_def
            )
            db.commit()
            db_fields = db.execute(
                """SELECT wsf_field_code, wsf_value
                   FROM t_workflow_step_field_value WHERE wsf_instance_id = ?""",
                (instance["wfi_id"],)
            ).fetchall()
            all_field_values = {row["wsf_field_code"]: row["wsf_value"] for row in db_fields}
            input_schema = handler.input_schema if handler else {}
            inputs = {k: all_field_values.get(k) for k in input_schema.keys()} if input_schema else all_field_values
            now_service = datetime.now()
            outputs = {}
            error_msg = None
            svc_status = "Success"
            try:
                if not handler:
                    raise ValueError(f"Service handler '{handler_name}' not registered.")
                outputs = handler.execute(inputs)
                output_schema = handler.output_schema or {}
                for out_field in (output_schema.keys() if output_schema else outputs.keys()):
                    if out_field in outputs:
                        db.execute(
                            """INSERT INTO t_workflow_step_field_value
                               (wsf_instance_id, wsf_step_key, wsf_field_code, wsf_value)
                               VALUES (?, ?, ?, ?)
                               ON CONFLICT(wsf_instance_id, wsf_step_key, wsf_field_code)
                               DO UPDATE SET wsf_value=excluded.wsf_value""",
                            (instance["wfi_id"], next_key, out_field, outputs[out_field])
                        )
                db.execute(
                    """UPDATE t_workflow_step_instance
                       SET wsi_status = 'Completed', wsi_completed_at = ? WHERE wsi_id = ?""",
                    (now_service, svc_step_id)
                )
                db.commit()
                activated.append(next_key)
                db.execute(
                    """INSERT INTO t_workflow_service_log
                       (wsl_instance_id, wsl_step_key, wsl_handler, wsl_status,
                        wsl_inputs, wsl_outputs, wsl_error, wsl_started_at, wsl_completed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (instance["wfi_id"], next_key, handler_name, svc_status,
                     json.dumps(inputs), json.dumps(outputs), None,
                     now_service, datetime.now())
                )
                for nn_key in get_next_steps(graph, next_key):
                    nn_def = get_step(graph, nn_key)
                    _create_step_instance(db, instance["wfi_id"], nn_key, "Pending", None, None, nn_def)
                    activated.append(nn_key)
                    if nn_def.get("type") == "End":
                        complete_workflow(instance["wfi_id"], db)
                        workflow_completed = True
            except Exception as e:
                error_msg = str(e)
                svc_status = "Error"
                db.execute(
                    """UPDATE t_workflow_step_instance
                       SET wsi_status = 'Paused', wsi_completed_at = ? WHERE wsi_id = ?""",
                    (now_service, svc_step_id)
                )
                db.commit()
                activated.append(next_key)
                db.execute(
                    """INSERT INTO t_workflow_service_log
                       (wsl_instance_id, wsl_step_key, wsl_handler, wsl_status,
                        wsl_inputs, wsl_outputs, wsl_error, wsl_started_at, wsl_completed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (instance["wfi_id"], next_key, handler_name, svc_status,
                     json.dumps(inputs), json.dumps(outputs), error_msg,
                     now_service, datetime.now())
                )
            continue

        # WF-13: Notification step — render template, send, auto-advance
        if step_type == "Notification":
            from actionhub.notifications import create_notification
            now_notification = datetime.now()
            notification_conf = next_def.get("notification", {})
            db_fields = db.execute(
                """SELECT wsf_field_code, wsf_value
                   FROM t_workflow_step_field_value WHERE wsf_instance_id = ?""",
                (instance["wfi_id"],)
            ).fetchall()
            field_values = {row["wsf_field_code"]: row["wsf_value"] for row in db_fields}

            def _render(tmpl):
                if not tmpl:
                    return ""
                try:
                    return tmpl.format(**field_values)
                except Exception:
                    return tmpl

            title = _render(notification_conf.get("title_en") or notification_conf.get("title") or "Notification")
            body = _render(notification_conf.get("body_template") or "")
            target_role = notification_conf.get("target_role")
            if target_role:
                user_rows = db.execute(
                    "SELECT usr_id FROM t_user WHERE usr_role = ? AND usr_active = 1",
                    (target_role,)
                ).fetchall()
                for row in user_rows:
                    create_notification(row["usr_id"], "workflow_notification", title, body, instance["wfi_action_id"])
            _create_step_instance(db, instance["wfi_id"], next_key, "Completed", None, now_notification, next_def)
            activated.append(next_key)
            for nn_key in get_next_steps(graph, next_key):
                nn_def = get_step(graph, nn_key)
                _create_step_instance(db, instance["wfi_id"], nn_key, "Pending", None, None, nn_def)
                activated.append(nn_key)
                if nn_def.get("type") == "End":
                    complete_workflow(instance["wfi_id"], db)
                    workflow_completed = True
            db.commit()
            continue

        # WF-14: Timer step — set SLA deadline, handled by background checker
        if step_type == "Timer":
            duration_hours = next_def.get("duration_hours")
            now_timer = datetime.now()
            sla_deadline = None
            if duration_hours:
                from datetime import timedelta
                sla_deadline = now_timer + timedelta(hours=duration_hours)
            db.execute(
                """INSERT INTO t_workflow_step_instance
                   (wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id,
                    wsi_entered_at, wsi_sla_deadline)
                   VALUES (?, ?, 'Pending', NULL, ?, ?)""",
                (instance["wfi_id"], next_key, now_timer, sla_deadline)
            )
            activated.append(next_key)
            db.commit()
            continue

        # Subprocess step
        if step_type == "Subprocess":
            subprocess_template_id = next_def.get("subprocess_template_id")
            if not subprocess_template_id:
                raise ValueError(f"Subprocess step '{next_key}' missing 'subprocess_template_id'.")
            child_instance_id = instantiate_workflow(subprocess_template_id, instance["wfi_action_id"], completed_by)
            _create_step_instance(db, instance["wfi_id"], next_key, "Waiting", completed_by, None, next_def)
            activated.append(f"subprocess:{next_key}:{child_instance_id}")
            continue

        # Join: check if all incoming branches complete
        if is_join(graph, next_key):
            resolved = resolve_join(instance["wfi_id"], next_key, graph)
            if resolved:
                for nn_key in get_next_steps(graph, next_key):
                    nn_def = get_step(graph, nn_key)
                    _create_step_instance(db, instance["wfi_id"], nn_key, "Pending", completed_by, None, nn_def)
                    activated.append(nn_key)
                    if nn_def.get("type") == "End":
                        complete_workflow(instance["wfi_id"], db)
                        workflow_completed = True
            continue

        # End step
        if step_type == "End":
            outcome = next_def.get("outcome")
            _create_step_instance(db, instance["wfi_id"], next_key, "Completed", None, now, next_def)
            activated.append(next_key)
            complete_workflow(instance["wfi_id"], db, outcome=outcome)
            workflow_completed = True
            continue

        # Task / default: assign using assignment rule
        assignee_id = resolve_assignee(instance["wfi_id"], next_key, graph, db) or completed_by
        _create_step_instance(db, instance["wfi_id"], next_key, "Pending", assignee_id, None, next_def)
        activated.append(f"{next_key}:{assignee_id}")

    # 7. Log to history
    # Determine old status for logging (Accept is V3, Active is V2)
    old_status = "Accepted" if step_inst["wsi_status"] == "Accepted" else "Active"
    _log_action_history_if_bound(
        db,
        instance["wfi_id"],
        completed_by,
        "WorkflowAdvance",
        f"step:{current_step_key}",
        old_status,
        "Completed",
    )

    db.commit()

    return {
        "completed": current_step_key,
        "activated": activated,
        "workflow_completed": workflow_completed,
        "timeline": timeline,
        "eligible_users": eligible_users,
    }


def resolve_join(instance_id: int, join_step_key: str, graph: dict) -> bool:
    """

    OP29 (S11): Uses transaction for race condition safety.

    Steps:
    1. Get all incoming step keys for the join
    2. SELECT step instances for those keys WHERE instance_id matches
    3. If ALL are 'Completed':
       a. Mark join step instance as 'Completed'
       b. Get next steps after join
       c. Create new Active step instances
       d. Return True
    4. Else: Return False (still waiting for other branches)

    Args:
        instance_id: The workflow instance ID.
        join_step_key: The join step key to resolve.
        graph: Parsed workflow graph.

    Returns:
        True if join was resolved, False if still waiting.
    """
    from actionhub.workflow.graph import get_incoming_steps

    db = get_db()

    # Use BEGIN IMMEDIATE for race condition safety
    db.execute("BEGIN IMMEDIATE")

    try:
        # 1. Get incoming step keys
        incoming_keys = get_incoming_steps(graph, join_step_key)

        # 2. Check if all incoming steps are completed
        placeholders = ",".join("?" * len(incoming_keys))
        completed_count = db.execute(
            f"""SELECT COUNT(*) as cnt FROM t_workflow_step_instance
                WHERE wsi_instance_id = ?
                AND wsi_step_key IN ({placeholders})
                AND wsi_status = 'Completed'""",
            (instance_id, *incoming_keys),
        ).fetchone()["cnt"]

        if completed_count == len(incoming_keys):
            # 3a. Mark join as completed (if it exists as Pending/Active)
            existing_join = db.execute(
                """SELECT wsi_id FROM t_workflow_step_instance
                   WHERE wsi_instance_id = ? AND wsi_step_key = ?
                   AND wsi_status IN ('Pending', 'Active')""",
                (instance_id, join_step_key),
            ).fetchone()

            if existing_join:
                now = datetime.now()
                db.execute(
                    """UPDATE t_workflow_step_instance
                       SET wsi_status = 'Completed', wsi_completed_at = ?
                       WHERE wsi_id = ?""",
                    (now, existing_join["wsi_id"]),
                )

            db.commit()
            return True
        else:
            db.rollback()
            return False

    except Exception:
        db.rollback()
        raise


def complete_workflow(instance_id: int, db: Any = None, outcome: str = None) -> None:
    """Mark workflow instance as Completed when End step is reached. Optionally set outcome.

    OP31 (S11):
    1. UPDATE t_workflow_instance SET wfi_status='Completed', wfi_completed_at=now, wfi_outcome=outcome
    2. UPDATE t_action SET act_status='Done' (if not already)
    3. Log to t_action_history (change_type='StatusChange')

    Args:
        instance_id: The workflow instance ID.
        db: Optional database connection (for internal use).
        outcome: Optional outcome string to store.
    """
    close_conn = db is None
    if db is None:
        db = get_db()

    now = datetime.now()

    # 1. Mark instance as completed, set outcome if provided
    if outcome is not None:
        db.execute(
            """UPDATE t_workflow_instance
               SET wfi_status = 'Completed', wfi_completed_at = ?, wfi_outcome = ?
               WHERE wfi_id = ?""",
            (now, outcome, instance_id),
        )
    else:
        db.execute(
            """UPDATE t_workflow_instance
               SET wfi_status = 'Completed', wfi_completed_at = ?
               WHERE wfi_id = ?""",
            (now, instance_id),
        )

    # 2. Get action ID and mark action as Done
    instance = db.execute(
        "SELECT wfi_action_id FROM t_workflow_instance WHERE wfi_id = ?",
        (instance_id,),
    ).fetchone()

    if instance and instance["wfi_action_id"]:
        action_id = instance["wfi_action_id"]
        db.execute(
            """UPDATE t_action
                   SET act_status = 'Done'
                   WHERE act_id = ? AND act_status != 'Done'""",
            (action_id,),
        )

        # 3. Log to history
        log_action_history(
            action_id=action_id,
            user_id=1,  # System user
            change_type="StatusChange",
            field_name="act_status",
            old_value=None,
            new_value="Done",
        )

    db.commit()

    if close_conn:
        db.close()


def cancel_workflow(instance_id: int, cancelled_by: int, reason: str = None) -> None:
    """Cancel a workflow instance.

    All Active/Pending steps become Skipped.

    Args:
        instance_id: The workflow instance ID.
        cancelled_by: User ID cancelling the workflow.
        reason: Optional cancellation reason.
    """
    db = get_db()
    now = datetime.now()

    # Mark all Active/Pending steps as Skipped
    db.execute(
        """UPDATE t_workflow_step_instance
           SET wsi_status = 'Skipped', wsi_completed_at = ?, wsi_comment = ?
           WHERE wsi_instance_id = ?
           AND wsi_status IN ('Active', 'Pending')""",
        (now, reason, instance_id),
    )

    # Mark instance as Cancelled
    db.execute(
        """UPDATE t_workflow_instance
           SET wfi_status = 'Cancelled'
           WHERE wfi_id = ?""",
        (instance_id,),
    )

    # Get action ID and log to history
    instance = db.execute(
        "SELECT wfi_action_id FROM t_workflow_instance WHERE wfi_id = ?",
        (instance_id,),
    ).fetchone()

    if instance and instance["wfi_action_id"]:
        log_action_history(
            action_id=instance["wfi_action_id"],
            user_id=cancelled_by,
            change_type="WorkflowCancel",
            field_name="workflow",
            old_value="Active",
            new_value="Cancelled",
        )

    db.commit()


def get_active_steps(instance_id: int) -> list[dict]:
    """Return all Active step instances for a workflow instance.

    Args:
        instance_id: The workflow instance ID.

    Returns:
        List of step instance dictionaries with status='Active' or 'Accepted'.
    """
    db = get_db()
    steps = db.execute(
        """SELECT wsi_id, wsi_step_key, wsi_status, wsi_assignee_id,
                  wsi_entered_at, wsi_sla_deadline
           FROM t_workflow_step_instance
           WHERE wsi_instance_id = ? AND wsi_status IN ('Active', 'Accepted')
           ORDER BY wsi_entered_at""",
        (instance_id,),
    ).fetchall()
    return [dict(s) for s in steps]


def get_instance_for_action(action_id: int) -> dict | None:
    """Fetch workflow instance bound to an action, if any.

    Args:
        action_id: The action ID.

    Returns:
        Workflow instance dictionary or None if not found.
    """
    db = get_db()
    instance = db.execute(
        """SELECT wfi_id, wfi_template_id, wfi_action_id, wfi_status,
                  wfi_started_at, wfi_completed_at
           FROM t_workflow_instance
           WHERE wfi_action_id = ? AND wfi_status = 'Active'""",
        (action_id,),
    ).fetchone()

    if instance:
        return dict(instance)
    return None


def get_display_status(action_id: int) -> str:
    """Compute display_status: workflow step name if workflow-bound, else act_status.

    D-W7/D173: act_status stays canonical; display shows step name.

    Args:
        action_id: The action ID.

    Returns:
        Step name if workflow-bound, otherwise the action status.
    """
    db = get_db()

    # Check if action has an active workflow
    instance = get_instance_for_action(action_id)
    if not instance:
        # No workflow, return action status
        action = db.execute(
            "SELECT act_status FROM t_action WHERE act_id = ?",
            (action_id,),
        ).fetchone()
        return action["act_status"] if action else "Unknown"

    # Get active step(s) for this workflow
    active_steps = get_active_steps(instance["wfi_id"])
    if not active_steps:
        # No active steps, return instance status
        return instance["wfi_status"]

    # Load template for step name
    template = db.execute(
        "SELECT wft_graph FROM t_workflow_template WHERE wft_id = ?",
        (instance["wfi_template_id"],),
    ).fetchone()

    graph = load_graph(template["wft_graph"])

    # Return the name of the first active step
    active_step_key = active_steps[0]["wsi_step_key"]
    from actionhub.workflow.graph import get_step_name

    return get_step_name(graph, active_step_key, "en")


def get_workflow_status(action_id: int) -> str:
    """Get the workflow instance status for an action.

    Args:
        action_id: The action ID.

    Returns:
        Workflow instance status ('Active', 'Escalated', 'Completed', 'Cancelled', 'Suspended')
        or None if no workflow is bound.
    """
    instance = get_instance_for_action(action_id)
    if instance:
        return instance.get("wfi_status")
    return None



# Only the correct V3 advance_step implementation should be present here


def reject_step(step_instance_id: int, rejected_by: int, reason: str) -> dict:
    """Reject a step in Pending or Accepted status, transitioning to Rejected.

    OP36 (WF-10): Transitions step from Pending/Accepted to Rejected.
    Rejection is terminal within WF-10 scope - creates a rejected outcome.

    Args:
        step_instance_id: The step instance ID to reject.
        rejected_by: User ID rejecting the step.
        reason: Required rejection reason.

    Returns:
        Dictionary with step_id, new_status='Rejected'.

    """
    if not reason or not reason.strip():
        raise ValueError("Rejection reason is required")

    db = get_db()
    now = datetime.now()

    # 1. Load step instance
    step = db.execute(
        """SELECT wsi_id, wsi_instance_id, wsi_step_key, wsi_status
           FROM t_workflow_step_instance WHERE wsi_id = ?""",
        (step_instance_id,),
    ).fetchone()

    if not step:
        raise ValueError(f"Step instance {step_instance_id} not found")
    if step["wsi_status"] not in ("Pending", "Accepted", "Active"):
        raise ValueError(f"Cannot reject step in '{step['wsi_status']}' status.")

    # 2. Update step status to Rejected
    db.execute(
        """UPDATE t_workflow_step_instance
           SET wsi_status = 'Rejected', wsi_completed_at = ?, wsi_comment = ?
           WHERE wsi_id = ?""",
        (now, reason, step_instance_id),
    )

    # 3. Update workflow instance status
    db.execute(
        """UPDATE t_workflow_instance
           SET wfi_status = 'Cancelled'
           WHERE wfi_id = ?""",
        (step["wsi_instance_id"],),
    )

    # 4. Log to history
    instance = db.execute(
        "SELECT wfi_action_id FROM t_workflow_instance WHERE wfi_id = ?",
        (step["wsi_instance_id"],),
    ).fetchone()

    if instance and instance["wfi_action_id"]:
        # Update action status to Cancelled
        db.execute(
            "UPDATE t_action SET act_status = 'Cancelled' WHERE act_id = ?",
            (instance["wfi_action_id"],),
        )

        log_action_history(
            action_id=instance["wfi_action_id"],
            user_id=rejected_by,
            change_type="WorkflowReject",
            field_name=step["wsi_step_key"],
            old_value=step["wsi_status"],
            new_value="Rejected",
        )

    db.commit()

    return {
        "step_id": step_instance_id,
        "new_status": "Rejected",
        "reason": reason,
    }


def escalate_step(step_instance_id: int, escalated_by: int, reason: str, new_assignee_id: int = None) -> dict:
    """Escalate a step - reassign to supervisor/manager without bypassing auditability.

    OP37 (WF-10): Escalation reassigns responsibility while maintaining audit trail.
    Sets status to Escalated and optionally reassigns to new user.

    Args:
        step_instance_id: The step instance ID to escalate.
        escalated_by: User ID performing the escalation.
        reason: Required escalation reason.
        new_assignee_id: Optional new assignee ID.

    Returns:
        Dictionary with step_id, new_status='Escalated', new_assignee_id.

    Raises:
        ValueError: If step not found or reason missing.
        PermissionError: If not authorized.
    """
    if not reason or not reason.strip():
        raise ValueError("Escalation reason is required")

    db = get_db()
    now = datetime.now()

    # Validate new_assignee_id if provided
    if new_assignee_id:
        user = db.execute(
            "SELECT usr_id FROM t_user WHERE usr_id = ? AND usr_active = 1",
            (new_assignee_id,),
        ).fetchone()
        if not user:
            raise ValueError(f"New assignee user {new_assignee_id} not found or inactive")

    # 1. Load step instance
    step = db.execute(
        "SELECT wsi_id, wsi_status, wsi_instance_id, wsi_step_key, wsi_assignee_id FROM t_workflow_step_instance WHERE wsi_id = ?",
        (step_instance_id,),
    ).fetchone()

    if not step:
        raise ValueError(f"Step instance {step_instance_id} not found")

    # 2. Update step status to Escalated with escalation tracking
    if new_assignee_id:
        db.execute(
            """UPDATE t_workflow_step_instance
               SET wsi_status = 'Escalated', wsi_assignee_id = ?,
                   wsi_escalated_by = ?, wsi_escalated_at = ?, wsi_escalation_reason = ?
               WHERE wsi_id = ?""",
            (new_assignee_id, escalated_by, now, reason, step_instance_id),
        )
    else:
        db.execute(
            """UPDATE t_workflow_step_instance
               SET wsi_status = 'Escalated',
                   wsi_escalated_by = ?, wsi_escalated_at = ?, wsi_escalation_reason = ?
               WHERE wsi_id = ?""",
            (escalated_by, now, reason, step_instance_id),
        )

    # 3. Update workflow instance status to Escalated
    db.execute(
        """UPDATE t_workflow_instance
           SET wfi_status = 'Escalated'
           WHERE wfi_id = ?""",
        (step["wsi_instance_id"],),
    )

    # 4. Log to history
    instance = db.execute(
        "SELECT wfi_action_id FROM t_workflow_instance WHERE wfi_id = ?",
        (step["wsi_instance_id"],),
    ).fetchone()

    if instance and instance["wfi_action_id"]:
        old_assignee = step["wsi_assignee_id"]
        new_assignee = new_assignee_id if new_assignee_id else old_assignee
        
        log_action_history(
            action_id=instance["wfi_action_id"],
            user_id=escalated_by,
            change_type="WorkflowEscalate",
            field_name=step["wsi_step_key"],
            old_value=f"assignee:{old_assignee}",
            new_value=f"assignee:{new_assignee},reason:{reason}",
        )

    db.commit()

    return {
        "step_id": step_instance_id,
        "new_status": "Escalated",
        "reason": reason,
        "new_assignee_id": new_assignee_id if new_assignee_id else step["wsi_assignee_id"],
    }


def accept_step(step_instance_id: int, accepted_by: int, comment: str = None) -> dict:
    """Accept a step in Pending status, transitioning it to Accepted (WF-10)."""
    db = get_db()
    step_inst = db.execute(
        "SELECT * FROM t_workflow_step_instance WHERE wsi_id = ?",
        (step_instance_id,)
    ).fetchone()
    if not step_inst:
        raise ValueError(f"Step instance {step_instance_id} not found")
    if step_inst["wsi_status"] != "Pending":
        raise ValueError(
            f"Cannot accept step in '{step_inst['wsi_status']}' status. "
            "Only Pending steps can be accepted."
        )
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    db.execute(
        """UPDATE t_workflow_step_instance
           SET wsi_status = 'Accepted', wsi_accepted_at = ?, wsi_comment = ?
           WHERE wsi_id = ?""",
        (now, comment, step_instance_id)
    )
    _log_action_history_if_bound(
        db,
        step_inst["wsi_instance_id"],
        accepted_by,
        "Updated",
        "step_status",
        "Pending",
        "Accepted",
    )
    db.commit()
    updated = db.execute(
        "SELECT * FROM t_workflow_step_instance WHERE wsi_id = ?",
        (step_instance_id,)
    ).fetchone()
    return dict(updated)


def reassign_step(step_instance_id: int, new_assignee_id: int, changed_by: int, reason: str = None) -> dict:
    """WF-16: Override the assignee of an active step at runtime, with audit log."""
    db = get_db()
    step = db.execute(
        "SELECT * FROM t_workflow_step_instance WHERE wsi_id = ?",
        (step_instance_id,)
    ).fetchone()
    if not step:
        raise ValueError(f"Step instance {step_instance_id} not found")
    if step["wsi_status"] not in ("Pending", "Accepted", "Active"):
        raise ValueError(
            f"Cannot reassign step in '{step['wsi_status']}' status. "
            "Only Pending/Accepted/Active allowed."
        )
    old_assignee = step["wsi_assignee_id"]
    if old_assignee == new_assignee_id:
        raise ValueError("New assignee is the same as current assignee.")
    db.execute(
        """UPDATE t_workflow_step_instance
           SET wsi_assignee_id = ?
           WHERE wsi_id = ?""",
        (new_assignee_id, step_instance_id)
    )
    # Log to action history
    instance = db.execute(
        "SELECT wfi_action_id FROM t_workflow_instance WHERE wfi_id = ?",
        (step["wsi_instance_id"],)
    ).fetchone()
    if instance and instance["wfi_action_id"]:
        log_action_history(
            action_id=instance["wfi_action_id"],
            user_id=changed_by,
            change_type="Reassigned",
            field_name=step["wsi_step_key"],
            old_value=f"assignee:{old_assignee}",
            new_value=f"assignee:{new_assignee_id},reason:{reason}",
        )
    db.commit()
    return {
        "step_id": step_instance_id,
        "new_assignee_id": new_assignee_id,
        "status": "ok",
    }


def delegate_step(step_instance_id: int, delegate_id: int, delegated_by: int, reason: str) -> dict:
    """WF-20 (D202, D203): Delegate a step to another eligible user with audit trail.

    Creates a new step instance for the delegate, marks the original as 'Delegated'.

    Args:
        step_instance_id: The step instance ID to delegate.
        delegate_id: User ID to delegate to.
        delegated_by: User ID performing the delegation.
        reason: Required delegation reason.

    Returns:
        Dictionary with original_step_id, new_step_id, delegate info.

    Raises:
        ValueError: If step not found, invalid status, self-delegate, or delegate ineligible.
    """
    if not reason or not reason.strip():
        raise ValueError("Delegation reason is required")

    db = get_db()
    now = datetime.now()

    # 1. Load step instance
    step = db.execute(
        """SELECT wsi_id, wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id
           FROM t_workflow_step_instance WHERE wsi_id = ?""",
        (step_instance_id,),
    ).fetchone()

    if not step:
        raise ValueError(f"Step instance {step_instance_id} not found")

    # 2. Validate status
    if step["wsi_status"] not in ("Pending", "Accepted", "Active"):
        raise ValueError(
            f"Cannot delegate step in '{step['wsi_status']}' status. "
            "Only Pending/Accepted steps can be delegated."
        )

    # 3. Check self-delegation
    if step["wsi_assignee_id"] == delegate_id:
        raise ValueError("Cannot delegate to yourself")

    # 4. Validate delegate is active
    delegate_user = db.execute(
        "SELECT usr_id, usr_display_name, usr_role, usr_active FROM t_user WHERE usr_id = ?",
        (delegate_id,),
    ).fetchone()

    if not delegate_user:
        raise ValueError(f"Delegate user {delegate_id} not found")

    if not delegate_user["usr_active"]:
        raise ValueError(f"Delegate user {delegate_id} is not active")

    # 5. Check eligibility (admin can delegate to anyone)
    delegator = db.execute(
        "SELECT usr_role FROM t_user WHERE usr_id = ?",
        (delegated_by,),
    ).fetchone()

    is_admin = delegator and delegator["usr_role"] == "Admin"

    if not is_admin:
        # Check if delegate is in eligible users list
        # Get workflow instance and graph
        instance = db.execute(
            "SELECT wfi_id, wfi_template_id FROM t_workflow_instance WHERE wfi_id = ?",
            (step["wsi_instance_id"],),
        ).fetchone()

        template = db.execute(
            "SELECT wft_graph FROM t_workflow_template WHERE wft_id = ?",
            (instance["wfi_template_id"],),
        ).fetchone()

        graph = load_graph(template["wft_graph"])
        step_def = get_step(graph, step["wsi_step_key"])

        # Get eligible users for this step
        from actionhub.workflow.assignment import get_eligible_users
        eligible = get_eligible_users(step["wsi_instance_id"], step["wsi_step_key"], graph, db)

        if delegate_id not in [u["usr_id"] for u in eligible]:
            raise ValueError(
                f"Delegate must be in the eligible-users list for this step. "
                f"Eligible users: {[u['usr_display_name'] for u in eligible]}"
            )

    # 6. Update original step to Delegated
    db.execute(
        """UPDATE t_workflow_step_instance
           SET wsi_status = 'Delegated', wsi_completed_at = ?, wsi_comment = ?
           WHERE wsi_id = ?""",
        (now, reason, step_instance_id),
    )

    # 7. Get step definition for creating new step instance
    instance = db.execute(
        "SELECT wfi_id, wfi_template_id, wfi_action_id FROM t_workflow_instance WHERE wfi_id = ?",
        (step["wsi_instance_id"],),
    ).fetchone()

    template = db.execute(
        "SELECT wft_graph FROM t_workflow_template WHERE wft_id = ?",
        (instance["wfi_template_id"],),
    ).fetchone()

    graph = load_graph(template["wft_graph"])
    step_def = get_step(graph, step["wsi_step_key"])

    # 8. Create new step instance for delegate
    cursor = db.execute(
        """INSERT INTO t_workflow_step_instance
           (wsi_instance_id, wsi_step_key, wsi_status, wsi_assignee_id,
            wsi_entered_at, wsi_delegated_from_id)
           VALUES (?, ?, 'Pending', ?, ?, ?)""",
        (step["wsi_instance_id"], step["wsi_step_key"], delegate_id, now, step_instance_id),
    )
    new_step_id = cursor.lastrowid

    # 9. Log to action history
    old_assignee = db.execute(
        "SELECT usr_display_name FROM t_user WHERE usr_id = ?",
        (step["wsi_assignee_id"],),
    ).fetchone()

    if instance["wfi_action_id"]:
        log_action_history(
            action_id=instance["wfi_action_id"],
            user_id=delegated_by,
            change_type="StepDelegated",
            field_name=step["wsi_step_key"],
            old_value=old_assignee["usr_display_name"] if old_assignee else str(step["wsi_assignee_id"]),
            new_value=delegate_user["usr_display_name"],
        )

    # 10. Create notification for delegate
    from actionhub.notifications import create_notification
    create_notification(
        user_id=delegate_id,
        event_type="workflow_delegation",
        title=f"Step delegated to you",
        body=f"A workflow step '{step['wsi_step_key']}' has been delegated to you. Reason: {reason}",
        action_id=instance["wfi_action_id"],
    )

    db.commit()

    return {
        "original_step_id": step_instance_id,
        "original_status": "Delegated",
        "new_step_id": new_step_id,
        "delegate": {
            "id": delegate_id,
            "name": delegate_user["usr_display_name"],
        },
        "reason": reason,
    }

