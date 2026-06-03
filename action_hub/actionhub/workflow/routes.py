import json
from flask import Blueprint, request, jsonify
from datetime import datetime

from actionhub.middleware.auth_middleware import login_required
from actionhub.auth import get_current_user_id
from actionhub.middleware.db import get_db
from actionhub.workflow import (
    engine,
    service,
    forms,
    graph,
)

# Define blueprint at the top so all routes use the same instance
workflow_bp = Blueprint("workflow", __name__, url_prefix="/api/workflow")


# --- Timeline Endpoint (WF-16) ---
@workflow_bp.get("/instances/<int:instance_id>/timeline")
@login_required
def workflow_timeline_route(instance_id: int):
    """WF-16: Return ordered list of all step state changes for a workflow instance."""
    from actionhub.workflow.service import get_workflow_history
    timeline = get_workflow_history(instance_id)
    return jsonify({"timeline": timeline})


@workflow_bp.get("/actions/<int:action_id>/instance")
@login_required
def workflow_instance_for_action_route(action_id: int):
    """Return the active workflow instance summary for an action, if one exists."""
    if not service.has_workflow_runtime_tables():
        return jsonify({"data": None})

    instance = engine.get_instance_for_action(action_id)
    if not instance:
        return jsonify({"data": None})

    return jsonify({
        "data": {
            "id": instance["wfi_id"],
            "template_id": instance["wfi_template_id"],
            "action_id": instance["wfi_action_id"],
            "status": instance["wfi_status"],
            "started_at": instance["wfi_started_at"],
            "completed_at": instance.get("wfi_completed_at"),
            "display_status": engine.get_display_status(action_id),
        }
    })


# --- Reassign Step Endpoint (WF-16) ---
@workflow_bp.put("/steps/<int:step_instance_id>/reassign")
@login_required
def reassign_step_route(step_instance_id: int):
    """WF-16: Override the assignee of an active step at runtime.

    Body:
        new_assignee_id: User ID to assign
        reason: Reason for reassignment (optional)

    Returns:
        JSON with step_id, new_assignee_id, status
    """
    try:
        _require_admin_or_step_assignee(step_instance_id)
        current_user = get_current_user_id()
        data = request.get_json(silent=True) or {}
        new_assignee_id = data.get("new_assignee_id")
        reason = data.get("reason", "Assignee override")
        if not new_assignee_id:
            return jsonify({"error": "Missing new_assignee_id"}), 400
        from actionhub.workflow.engine import reassign_step
        result = reassign_step(
            step_instance_id=step_instance_id,
            new_assignee_id=new_assignee_id,
            changed_by=current_user,
            reason=reason,
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# --- Delegate Step Endpoint (WF-20) ---
@workflow_bp.post("/steps/<int:step_instance_id>/delegate")
@login_required
def delegate_step_route(step_instance_id: int):
    """WF-20 (OP40): Delegate a step to another eligible user.

    Body:
        delegate_id: User ID to delegate to (required)
        reason: Reason for delegation (required)

    Returns:
        JSON with original_step_id, new_step_id, delegate info.
    """
    try:
        current_user = get_current_user_id()
        data = request.get_json(silent=True) or {}

        delegate_id = data.get("delegate_id")
        reason = data.get("reason")

        if not delegate_id:
            return jsonify({"error": {"code": "MISSING_DELEGATE", "message": "delegate_id is required"}}), 400

        if not reason or not reason.strip():
            return jsonify({"error": {"code": "REASON_REQUIRED", "message": "Delegation reason is required"}}), 400

        # Verify user is assignee or admin
        _require_admin_or_step_assignee(step_instance_id)

        from actionhub.workflow.engine import delegate_step
        result = delegate_step(
            step_instance_id=step_instance_id,
            delegate_id=delegate_id,
            delegated_by=current_user,
            reason=reason,
        )
        return jsonify(result)

    except ValueError as e:
        error_msg = str(e)
        if "self" in error_msg.lower():
            return jsonify({"error": {"code": "SELF_DELEGATE", "message": error_msg}}), 400
        elif "eligible" in error_msg.lower():
            return jsonify({"error": {"code": "INVALID_DELEGATE", "message": error_msg}}), 400
        elif "status" in error_msg.lower():
            return jsonify({"error": {"code": "CANNOT_DELEGATE", "message": error_msg}}), 400
        return jsonify({"error": {"code": "DELEGATION_ERROR", "message": error_msg}}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# --- Subprocess Status Endpoint (WF-20) ---
@workflow_bp.get("/instances/<int:instance_id>/subprocess")
@login_required
def get_subprocess_status_route(instance_id: int):
    """WF-20 (OP41): Get child subprocess status for a parent workflow instance.

    Returns:
        JSON with subprocess_steps list containing parent step info and child progress.
    """
    db = get_db()

    # Get all WaitingForChild steps for this instance
    waiting_steps = db.execute(
        """SELECT wsi_id, wsi_step_key, wsi_status, wsi_child_instance_id
           FROM t_workflow_step_instance
           WHERE wsi_instance_id = ? AND wsi_status = 'WaitingForChild'""",
        (instance_id,),
    ).fetchall()

    subprocess_steps = []
    for step in waiting_steps:
        child_instance_id = step["wsi_child_instance_id"]
        if not child_instance_id:
            continue

        # Get child instance info
        child = db.execute(
            """SELECT wfi_id, wfi_status, wfi_template_id
               FROM t_workflow_instance WHERE wfi_id = ?""",
            (child_instance_id,),
        ).fetchone()

        if not child:
            continue

        # Get template name
        template = db.execute(
            "SELECT wft_name_en FROM t_workflow_template WHERE wft_id = ?",
            (child["wfi_template_id"],),
        ).fetchone()

        # Get step count progress
        total_steps = db.execute(
            "SELECT COUNT(*) as cnt FROM t_workflow_step_instance WHERE wsi_instance_id = ?",
            (child_instance_id,),
        ).fetchone()["cnt"]

        completed_steps = db.execute(
            """SELECT COUNT(*) as cnt FROM t_workflow_step_instance
               WHERE wsi_instance_id = ? AND wsi_status = 'Completed'""",
            (child_instance_id,),
        ).fetchone()["cnt"]

        subprocess_steps.append({
            "parent_step_key": step["wsi_step_key"],
            "parent_step_id": step["wsi_id"],
            "parent_step_status": step["wsi_status"],
            "child_instance_id": child_instance_id,
            "child_status": child["wfi_status"],
            "child_template_name_en": template["wft_name_en"] if template else None,
            "child_progress": {
                "total_steps": total_steps,
                "completed_steps": completed_steps,
            },
        })

    return jsonify({
        "parent_instance_id": instance_id,
        "subprocess_steps": subprocess_steps,
    })


# --- Service Step Retry Endpoint (WF-12) ---
@workflow_bp.post("/steps/<int:step_instance_id>/retry")
@login_required
def retry_service_step(step_instance_id: int):
    """Admin-only: Retry a Paused service step (WF-12).

    Returns:
        JSON with result of retry attempt.
    """
    current_user = get_current_user_id()
    db = get_db()
    user = db.execute("SELECT usr_role FROM t_user WHERE usr_id = ?", (current_user,)).fetchone()
    if not user or user["usr_role"] != "Admin":
        return jsonify({"error": "Admin access required"}), 403

    # Get step instance and check status
    step = service.get_step_instance(step_instance_id)
    if not step:
        return jsonify({"error": "Step not found"}), 404
    if step["wsi_status"] != "Paused":
        return jsonify({"error": "Step is not in Paused status"}), 400

    # Get workflow instance and graph
    instance_id = step["wsi_instance_id"]
    instance = db.execute(
        "SELECT wfi_template_id FROM t_workflow_instance WHERE wfi_id = ?",
        (instance_id,)
    ).fetchone()
    if not instance:
        return jsonify({"error": "Workflow instance not found"}), 404
    template = db.execute(
        "SELECT wft_graph FROM t_workflow_template WHERE wft_id = ?",
        (instance["wfi_template_id"],)
    ).fetchone()
    if not template:
        return jsonify({"error": "Workflow template not found"}), 404
    from actionhub.workflow.graph import load_graph, get_step
    from actionhub.workflow.service_executor import service_registry
    graph = load_graph(template["wft_graph"])
    step_def = get_step(graph, step["wsi_step_key"])
    handler_name = step_def.get("handler")
    handler = None
    try:
        handler = service_registry.get(handler_name)
    except Exception:
        handler = None
    db_fields = db.execute(
        """
        SELECT wsf_field_code, wsf_value
        FROM t_workflow_step_field_value
        WHERE wsf_instance_id = ?
        """,
        (instance_id,)
    ).fetchall()
    all_field_values = {row["wsf_field_code"]: row["wsf_value"] for row in db_fields}
    input_schema = handler.input_schema if handler else {}
    inputs = {k: all_field_values.get(k) for k in input_schema.keys()} if input_schema else all_field_values
    now_service = datetime.now()
    outputs = {}
    error_msg = None
    status = "Success"
    try:
        if not handler:
            raise ValueError(f"Service handler '{handler_name}' not registered.")
        outputs = handler.execute(inputs)
        # Output mapping: only fields in output_schema
        output_schema = handler.output_schema or {}
        for out_field in (output_schema.keys() if output_schema else outputs.keys()):
            if out_field in outputs:
                db.execute(
                    """
                    INSERT INTO t_workflow_step_field_value
                    (wsf_instance_id, wsf_step_key, wsf_field_code, wsf_value)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(wsf_instance_id, wsf_step_key, wsf_field_code) DO UPDATE SET wsf_value=excluded.wsf_value
                    """,
                    (instance_id, step["wsi_step_key"], out_field, outputs[out_field])
                )
        # Mark step as Completed
        db.execute(
            """
            UPDATE t_workflow_step_instance
            SET wsi_status = 'Completed', wsi_completed_at = ?
            WHERE wsi_id = ?
            """,
            (datetime.now(), step_instance_id)
        )
        status = "Success"
    except Exception as e:
        error_msg = str(e)
        status = "Error"
        # Mark step as Paused again
        db.execute(
            """
            UPDATE t_workflow_step_instance
            SET wsi_status = 'Paused', wsi_completed_at = ?
            WHERE wsi_id = ?
            """,
            (datetime.now(), step_instance_id)
        )
    # Log service execution retry
    db.execute(
        """
        INSERT INTO t_workflow_service_log
        (wsl_instance_id, wsl_step_key, wsl_handler, wsl_status, wsl_inputs, wsl_outputs, wsl_error, wsl_started_at, wsl_completed_at, wsl_triggered_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            instance_id, step["wsi_step_key"], handler_name, status,
            json.dumps(inputs), json.dumps(outputs), error_msg,
            now_service, datetime.now(), current_user
        )
    )
    db.commit()
    return jsonify({"status": status, "outputs": outputs, "error": error_msg})


# --- Service Handler Registry Endpoint (WF-12) ---
from actionhub.workflow import service_executor

@workflow_bp.get("/service-handlers")
@login_required
def list_service_handlers():
    """Admin-only: List registered service step handlers (WF-12)."""
    current_user = get_current_user_id()
    db = get_db()
    user = db.execute("SELECT usr_role FROM t_user WHERE usr_id = ?", (current_user,)).fetchone()
    if not user or user["usr_role"] != "Admin":
        return jsonify({"error": "Admin access required"}), 403
    handlers = service_executor.list_handlers()
    return jsonify({"data": handlers})

# --- Helper functions ---

def _require_step_assignee(step_instance_id: int) -> dict:
    """Verify current user is assigned to the step.

    Returns step instance dict if authorized.

    Raises 403 if not authorized.
    """
    step = service.get_step_instance(step_instance_id)
    if not step:
        raise ValueError("Step not found")

    current_user = get_current_user_id()
    if step["wsi_assignee_id"] != current_user:
        # Also check if user is a delegate (V2.1)
        from actionhub.workflow.approval_service import resolve_approver

        actual_approver = resolve_approver(step["wsi_assignee_id"])
        if actual_approver != current_user:
            raise PermissionError("Not authorized to modify this step")

    return step


def _require_admin_or_step_assignee(step_instance_id: int) -> dict:
    """Allow an admin or the effective assignee to manage a step."""
    step = service.get_step_instance(step_instance_id)
    if not step:
        raise ValueError("Step not found")

    current_user = get_current_user_id()
    db = get_db()
    user = db.execute("SELECT usr_role FROM t_user WHERE usr_id = ?", (current_user,)).fetchone()
    if user and user["usr_role"] == "Admin":
        return step

    if step["wsi_assignee_id"] == current_user:
        return step

    from actionhub.workflow.approval_service import resolve_approver

    actual_approver = resolve_approver(step["wsi_assignee_id"])
    if actual_approver == current_user:
        return step

    raise PermissionError("Not authorized to modify this step")


# --- Template management ---

@workflow_bp.get("/templates")
@login_required
def list_templates():
    """List active workflow templates.

    Query params:
        type: Optional filter ('action' or 'request')

    Returns:
        JSON array of template summaries.
    """
    wft_type = request.args.get("type")
    templates = service.get_active_templates(wft_type)

    # Return simplified list
    return jsonify([
        {
            "id": t["wft_id"],
            "name_en": t["wft_name_en"],
            "name_cn": t["wft_name_cn"],
            "type": t["wft_type"],
            "is_default": bool(t["wft_is_default"]),
            "version": t["wft_version"],
        }
        for t in templates
    ])


@workflow_bp.get("/templates/<int:template_id>")
@login_required
def get_template(template_id: int):
    """Get a single template with full graph.

    Returns:
        JSON object with template and graph.
    """
    template = service.get_template(template_id)
    if not template:
        return jsonify({"error": "Template not found"}), 404

    return jsonify({
        "id": template["wft_id"],
        "name_en": template["wft_name_en"],
        "name_cn": template["wft_name_cn"],
        "desc": template["wft_desc"],
        "type": template["wft_type"],
        "is_default": bool(template["wft_is_default"]),
        "version": template["wft_version"],
        "active": bool(template["wft_active"]),
        "graph": json.loads(template["wft_graph"]),
        "created_at": template["wft_created_at"],
    })


@workflow_bp.post("/templates")
@login_required
def create_template():
    """Create a new workflow template.

    Body:
        name_en: English name (required)
        name_cn: Chinese name (optional)
        desc: Description (optional)
        type: 'action' or 'request' (required)
        graph: Workflow graph JSON (required)
        is_default: Set as default (optional, default false)

    Returns:
        JSON object with created template ID.
    """
    data = request.get_json()

    name_en = data.get("name_en")
    name_cn = data.get("name_cn", "")
    desc = data.get("desc")
    wft_type = data.get("type")
    graph_json = data.get("graph")
    is_default = data.get("is_default", False)

    if not name_en or not wft_type or not graph_json:
        return jsonify({"error": "Missing required fields"}), 400

    # Parse graph
    if isinstance(graph_json, str):
        graph_obj = graph.load_graph(graph_json)
    else:
        graph_obj = graph_json

    current_user = get_current_user_id()

    try:
        template_id = service.create_template(
            name_en=name_en,
            name_cn=name_cn,
            wft_type=wft_type,
            graph=graph_obj,
            created_by=current_user,
            desc=desc,
            is_default=is_default,
        )
        return jsonify({"id": template_id, "message": "Template created"}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@workflow_bp.put("/templates/<int:template_id>")
@login_required
def update_template(template_id: int):
    """Update a workflow template (creates new version).

    Body:
        graph: New workflow graph JSON (required)

    Returns:
        JSON object with new version ID.
    """
    data = request.get_json()
    graph_json = data.get("graph")

    if not graph_json:
        return jsonify({"error": "graph is required"}), 400

    # Parse graph
    if isinstance(graph_json, str):
        graph_obj = graph.load_graph(graph_json)
    else:
        graph_obj = graph_json

    current_user = get_current_user_id()

    try:
        new_version_id = service.update_template(
            template_id=template_id,
            graph=graph_obj,
            updated_by=current_user,
        )
        return jsonify({
            "id": new_version_id,
            "message": "Template updated to new version"
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# --- Instances ---

@workflow_bp.post("/instances")
@login_required
def start_workflow_on_action():
    """Start a workflow on an existing action with optional category attachment.

    Manual workflow creation only — never auto-triggered.

    Body:
        template_id: Workflow template ID (required)
        action_id: Action ID to bind workflow to (required)
        category_id: Primary category ID (optional)
        secondary_category_id: Secondary category ID (optional)

    Returns:
        JSON with instance_id, action_id.
    """
    data = request.get_json(silent=True) or {}

    template_id = data.get("template_id")
    action_id = data.get("action_id")
    category_id = data.get("category_id")
    secondary_category_id = data.get("secondary_category_id")

    if not template_id or not action_id:
        return jsonify({"error": "template_id and action_id required"}), 400

    # Validate secondary != primary
    if category_id and secondary_category_id and category_id == secondary_category_id:
        return jsonify({"error": "Secondary category must differ from primary category"}), 400

    # Validate template exists
    template = service.get_template(template_id)
    if not template:
        return jsonify({"error": "Template not found"}), 404

    # Validate action exists
    db = get_db()
    action = db.execute("SELECT act_id, act_status FROM t_action WHERE act_id = ?", (action_id,)).fetchone()
    if not action:
        return jsonify({"error": "Action not found"}), 404

    current_user = get_current_user_id()

    try:
        # Instantiate workflow with categories
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            action_id=action_id,
            started_by=current_user,
            category_id=category_id,
            secondary_category_id=secondary_category_id,
        )

        db.commit()

        return jsonify({
            "instance_id": instance_id,
            "action_id": action_id,
            "message": "Workflow started successfully",
        }), 201

    except ValueError as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to start workflow: {e}"}), 500


@workflow_bp.post("/requests")
@login_required
def create_workflow_request():
    """OP34: Create standalone workflow request.

    Manual workflow creation only — instantiates the workflow directly without
    forcing a supporting action record.

    Body:
        template_id: Request template ID (required)
        title: Request title (required)
        description: Request description (optional)
        owner_user_id: User ID to set as request owner (optional, default current user)
        category_id: Optional classification metadata
        secondary_category_id: Optional secondary classification metadata
        fields: Initial field values for start step (optional)

    Returns:
        JSON with instance_id, action_id, active_steps.
    """
    data = request.get_json(silent=True) or {}

    template_id = data.get("template_id")
    title = data.get("title")
    description = data.get("description", "")
    owner_user_id = data.get("owner_user_id")
    category_id = data.get("category_id")
    secondary_category_id = data.get("secondary_category_id")
    initial_fields = data.get("fields", {})

    if not template_id or not title:
        return jsonify({"error": "template_id and title required"}), 400
    if len(str(title).strip()) < 5:
        return jsonify({"error": "title must be at least 5 characters"}), 400

    # Validate secondary != primary
    if category_id and secondary_category_id and category_id == secondary_category_id:
        return jsonify({"error": "Secondary category must differ from primary category"}), 400

    # Validate template exists and is type='request'
    template = service.get_template(template_id)
    if not template:
        return jsonify({"error": "Template not found"}), 404
    if template["wft_type"] != "request":
        return jsonify({"error": "Template is not a request type"}), 400

    current_user = get_current_user_id()
    owner_user_id = int(owner_user_id) if owner_user_id else current_user
    db = get_db()

    owner_row = db.execute(
        "SELECT usr_id FROM t_user WHERE usr_id = ? AND usr_active = 1",
        (owner_user_id,),
    ).fetchone()
    if not owner_row:
        return jsonify({"error": "owner_user_id not found or inactive"}), 400

    try:
        # Instantiate workflow without forcing a supporting action row.
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            action_id=None,
            started_by=current_user,
            category_id=category_id,
            secondary_category_id=secondary_category_id,
        )

        # Save initial field values if provided
        current_steps = db.execute(
            """
            SELECT wsi_id, wsi_step_key
            FROM t_workflow_step_instance
            WHERE wsi_instance_id = ?
              AND wsi_status IN ('Pending', 'Accepted', 'Active')
            ORDER BY COALESCE(wsi_entered_at, wsi_accepted_at), wsi_id
            """,
            (instance_id,),
        ).fetchall()
        if current_steps and initial_fields:
            step_instance_id = current_steps[0]["wsi_id"]
            graph_obj = graph.load_graph(template["wft_graph"])
            step_key = current_steps[0]["wsi_step_key"]
            errors = forms.save_field_values(
                step_instance_id=step_instance_id,
                field_values=initial_fields,
                filled_by=current_user,
                graph=graph_obj,
                step_key=step_key,
            )
            if errors:
                db.rollback()
                return jsonify({"error": "; ".join(errors)}), 400

        db.commit()
    except ValueError as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Request creation failed: {e}"}), 500

    return jsonify({
        "instance_id": instance_id,
        "action_id": None,
        "active_steps": [
            {"id": s["wsi_id"], "key": s["wsi_step_key"]}
            for s in current_steps
        ],
    }), 201


@workflow_bp.get("/instances/<int:instance_id>")
def get_instance(instance_id: int):
    """Get workflow instance detail with all steps and field values.

    Returns:
        JSON object with instance, steps, and field values.
    """
    db = get_db()

    instance = db.execute(
        """SELECT wfi.*, wft.wft_name_en, wft.wft_graph
           FROM t_workflow_instance wfi
           JOIN t_workflow_template wft ON wfi.wfi_template_id = wft.wft_id
           WHERE wfi.wfi_id = ?""",
        (instance_id,),
    ).fetchone()

    if not instance:
        return jsonify({"error": "Instance not found"}), 404

    # Get step instances
    steps = db.execute(
        """SELECT * FROM t_workflow_step_instance
           WHERE wsi_instance_id = ?
           ORDER BY wsi_entered_at""",
        (instance_id,),
    ).fetchall()

    graph = graph.load_graph(instance["wft_graph"])

    # Get field values for each step
    step_data = []
    for step in steps:
        step_dict = dict(step)
        step_dict["fields"] = forms.get_field_values(step["wsi_id"])

        # Add step name from graph
        try:
            step_def = graph.get("steps", {}).get(step["wsi_step_key"], {})
            step_dict["name_en"] = step_def.get("name_en", step["wsi_step_key"])
            step_dict["name_cn"] = step_def.get("name_cn", step_def.get("name_en", ""))
            step_dict["step_type"] = step_def.get("type", "Task")
            step_dict["field_defs"] = step_def.get("fields", []) if isinstance(step_def.get("fields", []), list) else []
        except KeyError:
            step_dict["name_en"] = step["wsi_step_key"]
            step_dict["name_cn"] = step["wsi_step_key"]
            step_dict["step_type"] = "Task"
            step_dict["field_defs"] = []

        step_data.append(step_dict)

    return jsonify({
        "id": instance["wfi_id"],
        "template_id": instance["wfi_template_id"],
        "template_name": instance["wft_name_en"],
        "action_id": instance["wfi_action_id"],
        "status": instance["wfi_status"],
        "started_at": instance["wfi_started_at"],
        "completed_at": instance["wfi_completed_at"],
        "outcome": instance.get("wfi_outcome"),
        "steps": step_data,
    })


@workflow_bp.post("/instances/<int:instance_id>/cancel")
@login_required
def cancel_instance(instance_id: int):
    """Cancel a workflow instance.

    Body:
        reason: Cancellation reason (optional)

    Returns:
        JSON confirmation.
    """
    data = request.get_json() or {}
    reason = data.get("reason")

    current_user = get_current_user_id()

    try:
        engine.cancel_workflow(instance_id, current_user, reason)
        return jsonify({"message": "Workflow cancelled"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --- Steps ---

@workflow_bp.post("/steps/<int:step_instance_id>/advance")
@login_required
def advance_step(step_instance_id: int):
    """OP26: Advance step (Done button). Supports assignee override (WF-16).

    Body:
        comment: Optional comment
        next_assignee_id: Optional override for next step assignee

    Returns:
        JSON with completed step, activated next steps, timeline, eligible users.
    """
    data = request.get_json() or {}
    comment = data.get("comment")
    next_assignee_id = data.get("next_assignee_id")

    current_user = get_current_user_id()

    try:
        # Verify assignee
        step = _require_step_assignee(step_instance_id)

        result = engine.advance_step(
            step_instance_id=step_instance_id,
            completed_by=current_user,
            comment=comment,
            next_assignee_id=next_assignee_id,
        )
        return jsonify(result)
    except PermissionError as e:
        print(f"PermissionError in advance_step: {e}")
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        print(f"ValueError in advance_step: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        import traceback
        print(f"Exception in advance_step: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@workflow_bp.post("/steps/<int:step_instance_id>/fields")
@login_required
def save_step_fields(step_instance_id: int):
    """OP27: Save field values for a step.

    Body:
        fields: {field_key: value, ...}

    Returns:
        JSON with validation errors (empty if success).
    """
    data = request.get_json()
    fields = data.get("fields", {})

    if not fields:
        return jsonify({"error": "fields required"}), 400

    current_user = get_current_user_id()

    try:
        # Verify assignee
        step = _require_step_assignee(step_instance_id)

        # Get graph from template
        db = get_db()
        instance = db.execute(
            """SELECT wfi.wfi_template_id, wft.wft_graph
               FROM t_workflow_instance wfi
               JOIN t_workflow_template wft ON wfi.wfi_template_id = wft.wft_id
               WHERE wfi.wfi_id = ?""",
            (step["wsi_instance_id"],),
        ).fetchone()

        graph_obj = graph.load_graph(instance["wft_graph"])

        errors = forms.save_field_values(
            step_instance_id=step_instance_id,
            field_values=fields,
            filled_by=current_user,
            graph=graph_obj,
            step_key=step["wsi_step_key"],
        )

        if errors:
            return jsonify({"errors": errors}), 400

        return jsonify({"message": "Fields saved", "fields": fields})
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@workflow_bp.get("/steps/<int:step_instance_id>/fields")
@login_required
def get_step_fields(step_instance_id: int):
    """Get field values for a step.

    Returns:
        JSON with field values.
    """
    try:
        # Verify access (any user can view)
        step = service.get_step_instance(step_instance_id)
        if not step:
            return jsonify({"error": "Step not found"}), 404

        fields = forms.get_field_values(step_instance_id)
        return jsonify(fields)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- My work ---

@workflow_bp.get("/my-steps")
@login_required
def get_my_pending_steps():
    """Get pending steps assigned to current user.

    Returns:
        JSON array of step instances with workflow info.
    """
    current_user = get_current_user_id()
    steps = service.get_pending_steps_for_user(current_user)

    return jsonify([
        {
            "step_id": s["wsi_id"],
            "step_key": s["wsi_step_key"],
            "status": s["wsi_status"],
            "entered_at": s["wsi_entered_at"],
            "sla_deadline": s["wsi_sla_deadline"],
            "instance_id": s["wsi_instance_id"],
            "action_id": s["wfi_action_id"],
            "action_title": s["act_title"],
            "action_status": s.get("act_status"),
            "action_priority": s.get("act_priority"),
            "action_deadline": s.get("act_deadline"),
            "workflow_name": s["wft_name_en"],
            "team_name": s.get("team_name"),
        }
        for s in steps
    ])


# Import for create_workflow_request
from datetime import datetime

# Import dashboard service
from actionhub.workflow import dashboard_service


# --- Dashboard metrics ---

@workflow_bp.get("/dashboard/completion")
@login_required
def dashboard_completion():
    """Get completion rates by template."""
    template_id = request.args.get("template_id", type=int)
    rates = dashboard_service.get_completion_rates(template_id)
    return jsonify(rates)


@workflow_bp.get("/dashboard/lead-time")
@login_required
def dashboard_lead_time():
    """Get lead times by template."""
    template_id = request.args.get("template_id", type=int)
    times = dashboard_service.get_lead_times(template_id)
    return jsonify(times)


@workflow_bp.get("/dashboard/lead-time/<int:template_id>/steps")
@login_required
def dashboard_step_lead_time(template_id: int):
    """Get step-level lead times for a template."""
    times = dashboard_service.get_step_lead_times(template_id)
    return jsonify(times)


@workflow_bp.get("/dashboard/sla")
@login_required
def dashboard_sla():
    """Get SLA compliance metrics."""
    template_id = request.args.get("template_id", type=int)
    team_id = request.args.get("team_id", type=int)
    compliance = dashboard_service.get_sla_compliance(template_id, team_id)
    return jsonify(compliance)


@workflow_bp.get("/dashboard/bottlenecks")
@login_required
def dashboard_bottlenecks():
    """Get current bottlenecks (steps with most waiting items)."""
    limit = request.args.get("limit", 10, type=int)
    bottlenecks = dashboard_service.get_bottlenecks(limit)
    return jsonify(bottlenecks)


@workflow_bp.get("/dashboard/active")
@login_required
def dashboard_active():
    """Get active instance counts by template."""
    counts = dashboard_service.get_active_instance_counts()
    return jsonify(counts)


# Import yaml_builder
from actionhub.workflow import yaml_builder


# --- YAML Import/Export ---

@workflow_bp.post("/templates/import-yaml")
@login_required
def import_template_yaml():
    """Import workflow template from YAML.
    
    Body:
        yaml: YAML content (required)
        
    Returns:
        JSON with template_id on success.
    """
    data = request.get_json()
    yaml_text = data.get("yaml", "").strip()
    
    if not yaml_text:
        return jsonify({"error": "YAML content required"}), 400
    
    # Validate and parse YAML
    try:
        parsed = yaml_builder.parse_import_yaml(yaml_text)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    # Create template
    current_user = get_current_user_id()
    template_id = service.create_template(
        name_en=parsed["name_en"],
        name_cn=parsed["name_cn"],
        wft_type=parsed["type"],
        graph=parsed["graph"],
        created_by=current_user,
    )
    
    return jsonify({"template_id": template_id}), 201


@workflow_bp.get("/templates/<int:template_id>/export-yaml")
def export_template_yaml(template_id: int):
    """Export workflow template as YAML."""
    template = service.get_template(template_id)
    if not template:
        return jsonify({"error": "Template not found"}), 404
    
    import json
    graph = json.loads(template["wft_graph"])
    yaml_text = yaml_builder.graph_to_yaml(
        graph=graph,
        name_en=template["wft_name_en"],
        name_cn=template["wft_name_cn"],
        wft_type=template["wft_type"],
    )
    
    return yaml_text, 200, {"Content-Type": "text/plain; charset=utf-8"}


@workflow_bp.post("/templates/validate-yaml")
def validate_template_yaml():
    """Validate YAML without importing.
    
    Body:
        yaml: YAML content (required)
        
    Returns:
        JSON with is_valid and error message.
    """
    data = request.get_json()
    yaml_text = data.get("yaml", "").strip()
    
    if not yaml_text:
        return jsonify({"is_valid": False, "error": "YAML content required"}), 400
    
    is_valid, error = yaml_builder.validate_yaml(yaml_text)
    return jsonify({"is_valid": is_valid, "error": error})


# =============================================================================
# WF-10 Lifecycle Operations: Accept, Reject, Escalate
# =============================================================================

@workflow_bp.post("/steps/<int:step_instance_id>/accept")
@login_required
def accept_step_route(step_instance_id: int):
    """OP35: Accept a pending step.

    Body (optional):
        comment: Optional comment

    Returns:
        JSON with step_id, new_status='Accepted'.
    """
    try:
        # Verify assignee
        step = _require_step_assignee(step_instance_id)

        current_user = get_current_user_id()
        data = request.get_json(silent=True) or {}
        comment = data.get("comment")

        result = engine.accept_step(
            step_instance_id=step_instance_id,
            accepted_by=current_user,
            comment=comment,
        )

        return jsonify({"data": result})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@workflow_bp.post("/steps/<int:step_instance_id>/reject")
@login_required
def reject_step_route(step_instance_id: int):
    """OP36: Reject a pending or accepted step.

    Body (required):
        reason: Rejection reason (required)

    Returns:
        JSON with step_id, new_status='Rejected'.
    """
    try:
        # Verify assignee
        step = _require_step_assignee(step_instance_id)

        current_user = get_current_user_id()
        data = request.get_json(silent=True) or {}
        reason = data.get("reason")

        result = engine.reject_step(
            step_instance_id=step_instance_id,
            rejected_by=current_user,
            reason=reason,
        )

        return jsonify({"data": result})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@workflow_bp.post("/steps/<int:step_instance_id>/escalate")
@login_required
def escalate_step_route(step_instance_id: int):
    """OP37: Escalate a step - reassign with audit trail.

    Body:
        reason: Escalation reason (required)
        new_assignee_id: Optional new assignee user ID

    Returns:
        JSON with step_id, new_status='Escalated'.
    """
    try:
        # Verify assignee
        step = _require_step_assignee(step_instance_id)

        current_user = get_current_user_id()
        data = request.get_json(silent=True) or {}
        reason = data.get("reason")
        new_assignee_id = data.get("new_assignee_id")

        result = engine.escalate_step(
            step_instance_id=step_instance_id,
            escalated_by=current_user,
            reason=reason,
            new_assignee_id=new_assignee_id,
        )

        return jsonify({"data": result})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# ============================================================================
# WF-21: Workflow Workbench Backend APIs
# ============================================================================

@workflow_bp.get("/instances/<int:instance_id>/workbench")
@login_required
def get_workbench_route(instance_id: int):
    """WF-21 (OP27): Get complete workbench data for a workflow instance.

    Returns comprehensive data needed to render the workbench UI:
    - workflow_summary: instance info with template name, status, outcome
    - current_steps: active step cards with assignee, status, deadlines
    - field_definitions: editable field schema from workflow graph
    - field_values: saved field values for current steps
    - attachments: list of attachments for current step
    - timeline: all step history for the instance
    - eligible_users: users eligible for delegation/reassignment

    Returns:
        JSON with workbench data structure.
    """
    try:
        current_user = get_current_user_id()
        from actionhub.workflow.service import get_workbench_data
        workbench_data = get_workbench_data(instance_id, current_user)
        return jsonify({"data": workbench_data})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to load workbench: {str(e)}"}), 500


@workflow_bp.post("/steps/<int:step_instance_id>/draft")
@login_required
def save_draft_route(step_instance_id: int):
    """WF-21 (OP39): Save draft field values for a step.

    Persists partial work without advancing the workflow or changing step status.

    Body:
        fields: Array of {key, value} objects (required)
        comment: Optional progress note

    Returns:
        JSON with success status and saved field count.
    """
    try:
        current_user = get_current_user_id()
        data = request.get_json(silent=True) or {}

        fields = data.get("fields", [])
        comment = data.get("comment")

        if not fields:
            return jsonify({"error": "fields array is required"}), 400

        # Verify user is assignee or has permission
        _require_admin_or_step_assignee(step_instance_id)

        from actionhub.workflow.service import save_step_draft
        result = save_step_draft(
            step_instance_id=step_instance_id,
            fields=fields,
            comment=comment,
        )

        return jsonify({"data": result})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@workflow_bp.get("/steps/<int:step_instance_id>/attachments")
@login_required
def list_attachments_route(step_instance_id: int):
    """WF-21: List all active attachments for a step instance.

    Returns:
        JSON with attachments array.
    """
    try:
        from actionhub.workflow.service import get_step_instance

        step = get_step_instance(step_instance_id)
        if not step:
            return jsonify({"data": []})

        # Verify user has access to this step
        _require_admin_or_step_assignee(step_instance_id)

        from actionhub.workflow.attachments import get_step_attachments
        attachments = get_step_attachments(step_instance_id)

        return jsonify({"data": attachments})

    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": f"Failed to list attachments: {str(e)}"}), 500


@workflow_bp.post("/steps/<int:step_instance_id>/attachments")
@login_required
def upload_attachment_route(step_instance_id: int):
    """WF-21 (OP42): Upload a file attachment for a workflow step.

    Accepts multipart/form-data with:
        file: The file to upload (required)
        description: Optional description

    Policy enforcement:
        - Allowed extensions: pdf, docx, xlsx, pptx, csv, txt, png, jpg
        - Max file size: 25 MB
        - Max files per step: 10
        - Max cumulative per workflow: 100 MB

    Returns:
        JSON with attachment metadata on success.
    """
    try:
        current_user = get_current_user_id()

        # Verify user has access to this step
        _require_admin_or_step_assignee(step_instance_id)

        # Check if file was uploaded
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Get optional description
        description = request.form.get("description")

        # Read file data
        file_data = file.read()
        if not file_data:
            return jsonify({"error": "Empty file"}), 400

        # Upload attachment
        from actionhub.workflow.attachments import upload_attachment
        result = upload_attachment(
            step_instance_id=step_instance_id,
            filename=file.filename,
            file_data=file_data,
            mime_type=file.content_type,
            uploaded_by=current_user,
            description=description,
        )

        return jsonify({"data": result}), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@workflow_bp.delete("/steps/<int:step_instance_id>/attachments/<int:attachment_id>")
@login_required
def delete_attachment_route(step_instance_id: int, attachment_id: int):
    """WF-21: Soft-delete an attachment.

    Authorization: uploader, admin, or team lead can delete.

    Returns:
        JSON with success status.
    """
    try:
        current_user = get_current_user_id()

        # Verify user has access to this step
        _require_admin_or_step_assignee(step_instance_id)

        from actionhub.workflow.attachments import delete_attachment
        deleted = delete_attachment(attachment_id, current_user)

        if not deleted:
            return jsonify({"error": "Attachment not found or already deleted"}), 404

        return jsonify({"data": {"success": True, "attachment_id": attachment_id}})

    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": f"Delete failed: {str(e)}"}), 500


@workflow_bp.get("/attachments/<int:attachment_id>/download")
@login_required
def download_attachment_route(attachment_id: int):
    """WF-21: Download an attachment file.

    Returns:
        File response with appropriate content-type.
    """
    try:
        current_user = get_current_user_id()

        # Get attachment metadata
        from actionhub.workflow.attachments import get_attachment, get_attachment_file_path
        attachment = get_attachment(attachment_id)

        if not attachment:
            return jsonify({"error": "Attachment not found"}), 404

        # Verify user has access via step instance
        step = get_step_instance(attachment["wsa_step_inst_id"])
        if not step:
            return jsonify({"error": "Step not found"}), 404

        _require_admin_or_step_assignee(attachment["wsa_step_inst_id"])

        # Get file path
        file_path = get_attachment_file_path(attachment_id)
        if not file_path:
            return jsonify({"error": "File not found on disk"}), 404

        # Send file
        from flask import send_file
        return send_file(
            file_path,
            mimetype=attachment["wsa_mime_type"],
            as_attachment=True,
            download_name=attachment["wsa_filename"],
        )

    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


# Helper functions for authorization
def _require_admin_or_step_assignee(step_instance_id: int) -> dict:
    """Verify current user is admin or assignee of the step.

    Returns:
        Step instance dict if authorized.

    Raises:
        PermissionError: If not authorized.
        ValueError: If step not found.
    """
    from actionhub.auth import get_current_user_id
    current_user = get_current_user_id()
    db = get_db()

    step = db.execute(
        """
        SELECT wsi.*, wfi.wfi_action_id
        FROM t_workflow_step_instance wsi
        JOIN t_workflow_instance wfi ON wsi.wsi_instance_id = wfi.wfi_id
        WHERE wsi.wsi_id = ?
        """,
        (step_instance_id,),
    ).fetchone()

    if not step:
        raise ValueError("Step instance not found")

    user = db.execute(
        "SELECT usr_role FROM t_user WHERE usr_id = ?",
        (current_user,),
    ).fetchone()

    if not user:
        raise PermissionError("User not found")

    # Admin can access everything
    if user["usr_role"] == "Admin":
        return dict(step)

    # Check if user is assignee
    if step["wsi_assignee_id"] != current_user:
        raise PermissionError(
            "Access denied. Only the step assignee or admin can perform this action."
        )

    return dict(step)


def _require_step_assignee(step_instance_id: int) -> dict:
    """Verify current user is the assignee of the step.

    Returns:
        Step instance dict if authorized.

    Raises:
        PermissionError: If not assignee.
        ValueError: If step not found.
    """
    from actionhub.auth import get_current_user_id
    current_user = get_current_user_id()
    db = get_db()

    step = db.execute(
        """
        SELECT wsi.*, wfi.wfi_action_id
        FROM t_workflow_step_instance wsi
        JOIN t_workflow_instance wfi ON wsi.wsi_instance_id = wfi.wfi_id
        WHERE wsi.wsi_id = ?
        """,
        (step_instance_id,),
    ).fetchone()

    if not step:
        raise ValueError("Step instance not found")

    if step["wsi_assignee_id"] != current_user:
        raise PermissionError("Only the step assignee can perform this action")

    return dict(step)


def get_step_instance(step_instance_id: int) -> dict | None:
    """Get step instance by ID (helper for routes).

    Args:
        step_instance_id: Step instance ID.

    Returns:
        Step instance dict or None.
    """
    db = get_db()
    step = db.execute(
        """
        SELECT wsi.*, wfi.wfi_action_id, wfi.wfi_template_id
        FROM t_workflow_step_instance wsi
        JOIN t_workflow_instance wfi ON wsi.wsi_instance_id = wfi.wfi_id
        WHERE wsi.wsi_id = ?
        """,
        (step_instance_id,),
    ).fetchone()

    return dict(step) if step else None
