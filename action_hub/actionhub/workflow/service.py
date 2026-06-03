"""Workflow template management and binding queries.

This module provides template CRUD operations and helper queries
for workflow instances and step assignments.
"""
import json
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional

from actionhub.middleware.db import get_db
from actionhub.workflow.graph import load_graph, validate_graph


# ---------------------------------------------------------------------------
# Template-graph LRU cache — keyed on (template_id, version).
# Avoids re-parsing the same JSON on repeated calls (e.g. get_template_for_scope).
# Call `invalidate_graph_cache()` after template create / update.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=64)
def _cached_load_graph(template_id: int, version: int, graph_json: str) -> dict:
    """Parse *and* cache a workflow-template graph.

    ``graph_json`` is part of the key so the cache auto-invalidates when the
    stored JSON changes (which happens on every new version).
    """
    return load_graph(graph_json)


def invalidate_graph_cache() -> None:
    """Clear the template-graph LRU cache (call after create/update)."""
    _cached_load_graph.cache_clear()


def has_workflow_template_table() -> bool:
    """Check whether the workflow template table exists in the current DB."""
    db = get_db()
    row = db.execute(
        """SELECT 1
           FROM sqlite_master
           WHERE type = 'table' AND name = 't_workflow_template'
           LIMIT 1"""
    ).fetchone()
    return bool(row)


def has_workflow_runtime_tables() -> bool:
    """Check whether runtime workflow tables are present in the current DB."""
    db = get_db()
    rows = db.execute(
        """SELECT name
           FROM sqlite_master
           WHERE type = 'table'
             AND name IN ('t_workflow_instance', 't_workflow_step_instance')"""
    ).fetchall()
    return len(rows) == 2


def create_template(
    name_en: str,
    name_cn: str,
    wft_type: str,
    graph: dict,
    created_by: int,
    desc: str = None,
    is_default: bool = False,
) -> int:
    """Insert new workflow template. Validate graph first.

    Template types: 'action' (bound to category/team) or 'request' (standalone).

    Args:
        name_en: English template name.
        name_cn: Chinese template name.
        wft_type: Template type ('action' or 'request').
        graph: Workflow graph dictionary.
        created_by: User ID creating the template.
        desc: Optional description.
        is_default: Whether this is the default template.

    Returns:
        Created template ID.

    Raises:
        ValueError: If graph validation fails or invalid type.
    """
    if not has_workflow_template_table():
        raise ValueError("Workflow template table is missing. Apply workflow migration first.")

    if wft_type not in ("action", "request"):
        raise ValueError(f"Invalid template type: {wft_type}")

    # Validate graph
    errors = validate_graph(graph)
    if errors:
        raise ValueError(f"Invalid workflow graph: {', '.join(errors)}")

    db = get_db()
    now = datetime.now()

    # If setting as default, unset any existing default
    if is_default:
        db.execute("UPDATE t_workflow_template SET wft_is_default = 0")

    cursor = db.execute(
        """INSERT INTO t_workflow_template
           (wft_name_en, wft_name_cn, wft_desc, wft_version, wft_is_default,
            wft_type, wft_active, wft_graph, wft_created_by, wft_created_at)
           VALUES (?, ?, ?, 1, ?, ?, 1, ?, ?, ?)""",
        (
            name_en,
            name_cn,
            desc,
            1 if is_default else 0,
            wft_type,
            json.dumps(graph),
            created_by,
            now,
        ),
    )
    db.commit()
    invalidate_graph_cache()
    return cursor.lastrowid


def update_template(template_id: int, graph: dict, updated_by: int) -> int:
    """Create new version of template. Old version stays for in-flight instances.

    D178/BR28: In-flight instances keep their original template version.

    Steps:
    1. Copy existing template row
    2. Increment wft_version
    3. Update wft_graph
    4. Set old version wft_active=0

    Args:
        template_id: Original template ID to update.
        graph: New workflow graph dictionary.
        updated_by: User ID making the update.

    Returns:
        New template row ID (new version).

    Raises:
        ValueError: If template not found or graph invalid.
    """
    if not has_workflow_template_table():
        raise ValueError("Workflow template table is missing. Apply workflow migration first.")

    # Validate graph
    errors = validate_graph(graph)
    if errors:
        raise ValueError(f"Invalid workflow graph: {', '.join(errors)}")

    db = get_db()

    # Get existing template
    existing = db.execute(
        "SELECT * FROM t_workflow_template WHERE wft_id = ?", (template_id,)
    ).fetchone()

    if not existing:
        raise ValueError(f"Template {template_id} not found")

    # Set old version inactive
    db.execute(
        "UPDATE t_workflow_template SET wft_active = 0 WHERE wft_id = ?",
        (template_id,),
    )

    # Create new version
    now = datetime.now()
    new_version = existing["wft_version"] + 1

    cursor = db.execute(
        """INSERT INTO t_workflow_template
           (wft_name_en, wft_name_cn, wft_desc, wft_version, wft_is_default,
            wft_type, wft_active, wft_graph, wft_created_by, wft_created_at,
            wft_updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
        (
            existing["wft_name_en"],
            existing["wft_name_cn"],
            existing["wft_desc"],
            new_version,
            existing["wft_is_default"],
            existing["wft_type"],
            json.dumps(graph),
            existing["wft_created_by"],
            existing["wft_created_at"],
            now,
        ),
    )
    db.commit()
    invalidate_graph_cache()
    return cursor.lastrowid


def get_template(template_id: int) -> dict | None:
    """Fetch template by ID.

    Args:
        template_id: Template ID.

    Returns:
        Template dictionary or None if not found.
    """
    if not has_workflow_template_table():
        return None

    db = get_db()
    template = db.execute(
        "SELECT * FROM t_workflow_template WHERE wft_id = ?", (template_id,)
    ).fetchone()

    if template:
        return dict(template)
    return None


def get_active_templates(wft_type: str = None) -> list[dict]:
    """List all active templates, optionally filtered by type.

    Args:
        wft_type: Optional filter ('action' or 'request').

    Returns:
        List of active template dictionaries.
    """
    if not has_workflow_template_table():
        return []

    db = get_db()

    if wft_type:
        templates = db.execute(
            """SELECT * FROM t_workflow_template
               WHERE wft_active = 1 AND wft_type = ?
               ORDER BY wft_name_en""",
            (wft_type,),
        ).fetchall()
    else:
        templates = db.execute(
            """SELECT * FROM t_workflow_template
               WHERE wft_active = 1
               ORDER BY wft_name_en"""
        ).fetchall()

    return [dict(t) for t in templates]


def get_default_template() -> dict | None:
    """Get the default workflow template.

    Returns:
        Default template dictionary or None.
    """
    if not has_workflow_template_table():
        return None

    db = get_db()
    template = db.execute(
        "SELECT * FROM t_workflow_template WHERE wft_is_default = 1 AND wft_active = 1"
    ).fetchone()

    if template:
        return dict(template)
    return None


def get_template_for_scope(
    team_id: int = None,
    topic_id: int = None,
) -> dict | None:
    """Find the active workflow template bound to a given scope.

    Checks wft_graph.bindings against scope_type/scope_id.
    Returns None if no binding -> action uses default Simple workflow.

    Priority: team > topic

    Args:
        team_id: Team ID to find binding for.
        topic_id: Topic ID to find binding for.

    Returns:
        Matching template dictionary or None.
    """
    if not has_workflow_template_table():
        return None

    db = get_db()

    # Get all active templates
    templates = db.execute(
        """SELECT wft_id, wft_version, wft_graph FROM t_workflow_template
           WHERE wft_active = 1 AND wft_type = 'action'"""
    ).fetchall()

    for row in templates:
        try:
            graph = _cached_load_graph(row["wft_id"], row["wft_version"], row["wft_graph"])
            bindings = graph.get("bindings", [])

            for binding in bindings:
                scope_type = binding.get("scope_type")
                scope_id = binding.get("scope_id")

                if scope_type == "team" and team_id is not None:
                    if scope_id is None or scope_id == team_id:
                        return get_template(row["wft_id"])

                if scope_type in ("topic", "category") and topic_id is not None:
                    if scope_id is None or scope_id == topic_id:
                        return get_template(row["wft_id"])

        except Exception:
            continue

    # No binding found, return default
    return get_default_template()


def get_workflow_history(instance_id: int) -> list[dict]:
    """Full timeline: all step instances with timestamps and field values.

    Args:
        instance_id: Workflow instance ID.

    Returns:
        List of step instance dictionaries with field values.
    """
    db = get_db()

    # Get all step instances for this workflow, ordered by entered_at
    steps = db.execute(
        """SELECT wsi_id, wsi_step_key, wsi_status, wsi_assignee_id,
                  wsi_entered_at, wsi_completed_at, wsi_sla_deadline, wsi_comment
           FROM t_workflow_step_instance
           WHERE wsi_instance_id = ?
           ORDER BY COALESCE(wsi_entered_at, wsi_completed_at)""",
        (instance_id,),
    ).fetchall()

    # Detect field-value column scheme (sfv_ vs wsf_)
    sfv_cols = {
        r[1]
        for r in db.execute(
            "PRAGMA table_info(t_workflow_step_field_value)"
        ).fetchall()
    }
    if "sfv_step_inst_id" in sfv_cols:
        id_col, key_col, val_col = "sfv_step_inst_id", "sfv_field_key", "sfv_value"
    elif "wsf_instance_id" in sfv_cols:
        id_col, key_col, val_col = "wsf_instance_id", "wsf_field_code", "wsf_value"
    else:
        id_col, key_col, val_col = None, None, None

    fields_by_step: dict = {}
    if id_col and key_col:
        try:
            field_values = db.execute(
                f"""SELECT {id_col}, {key_col}, {val_col}
                   FROM t_workflow_step_field_value
                   WHERE {id_col} IN (
                       SELECT wsi_id FROM t_workflow_step_instance
                       WHERE wsi_instance_id = ?
                   )""",
                (instance_id,),
            ).fetchall()
            for fv in field_values:
                step_id = fv[0]
                if step_id not in fields_by_step:
                    fields_by_step[step_id] = {}
                fields_by_step[step_id][fv[1]] = fv[2]
        except Exception:
            pass

    # Build result
    result = []
    for step in steps:
        step_dict = dict(step)
        step_dict["field_values"] = fields_by_step.get(step["wsi_id"], {})
        result.append(step_dict)

    return result


def get_instances_by_template(
    template_id: int, status: str = None, limit: int = 100
) -> list[dict]:
    """List workflow instances for a template, with action info joined.

    Args:
        template_id: Template ID.
        status: Optional status filter.
        limit: Maximum number of results.

    Returns:
        List of instance dictionaries with action info.
    """
    db = get_db()

    if status:
        instances = db.execute(
            """SELECT wfi.*, a.act_title, a.act_status as action_status
               FROM t_workflow_instance wfi
               LEFT JOIN t_action a ON wfi.wfi_action_id = a.act_id
               WHERE wfi.wfi_template_id = ? AND wfi.wfi_status = ?
               ORDER BY wfi.wfi_started_at DESC
               LIMIT ?""",
            (template_id, status, limit),
        ).fetchall()
    else:
        instances = db.execute(
            """SELECT wfi.*, a.act_title, a.act_status as action_status
               FROM t_workflow_instance wfi
               LEFT JOIN t_action a ON wfi.wfi_action_id = a.act_id
               WHERE wfi.wfi_template_id = ?
               ORDER BY wfi.wfi_started_at DESC
               LIMIT ?""",
            (template_id, limit),
        ).fetchall()

    return [dict(i) for i in instances]


def get_pending_steps_for_user(user_id: int) -> list[dict]:
    """All Pending/Accepted step instances assigned to a user, across all workflows.

    Args:
        user_id: User ID.

    Returns:
        List of step instance dictionaries with workflow and action info.
    """
    if not has_workflow_runtime_tables():
        return []

    db = get_db()

    steps = db.execute(
        """SELECT wsi.*, wfi.wfi_action_id, wfi.wfi_template_id,
                  a.act_title, a.act_status, a.act_priority, a.act_deadline,
                  wft.wft_name_en,
                  t.tea_name_en as team_name
           FROM t_workflow_step_instance wsi
           JOIN t_workflow_instance wfi ON wsi.wsi_instance_id = wfi.wfi_id
            LEFT JOIN t_action a ON wfi.wfi_action_id = a.act_id
           JOIN t_workflow_template wft ON wfi.wfi_template_id = wft.wft_id
           LEFT JOIN t_team t ON a.act_team_id = t.tea_id
           WHERE wsi.wsi_status IN ('Pending', 'Accepted', 'Active')
           AND wsi.wsi_assignee_id = ?
           ORDER BY wsi.wsi_sla_deadline""",
        (user_id,),
    ).fetchall()

    return [dict(s) for s in steps]


def get_all_active_instances() -> list[dict]:
    """Get all active workflow instances with summary info.

    Returns:
        List of active instance dictionaries.
    """
    db = get_db()

    instances = db.execute(
        """SELECT wfi.*, wft.wft_name_en, a.act_title, a.act_status as action_status,
                  (SELECT COUNT(*) FROM t_workflow_step_instance
               WHERE wsi_instance_id = wfi.wfi_id AND wsi_status IN ('Pending', 'Accepted', 'Active')) as active_steps
           FROM t_workflow_instance wfi
           JOIN t_workflow_template wft ON wfi.wfi_template_id = wft.wft_id
           LEFT JOIN t_action a ON wfi.wfi_action_id = a.act_id
           WHERE wfi.wfi_status = 'Active'
           ORDER BY wfi.wfi_started_at DESC"""
    ).fetchall()

    return [dict(i) for i in instances]


def get_step_instance(step_instance_id: int) -> dict | None:
    """Get a single step instance by ID.

    Args:
        step_instance_id: Step instance ID.

    Returns:
        Step instance dictionary or None.
    """
    db = get_db()
    step = db.execute(
        """SELECT wsi.*, wfi.wfi_action_id, wfi.wfi_template_id
           FROM t_workflow_step_instance wsi
           JOIN t_workflow_instance wfi ON wsi.wsi_instance_id = wfi.wfi_id
           WHERE wsi.wsi_id = ?""",
        (step_instance_id,),
    ).fetchone()

    if step:
        return dict(step)
    return None


def get_workflow_history(instance_id: int) -> list[dict]:
    """Get timeline/history for a workflow instance.

    Returns all step state changes in chronological order.

    Args:
        instance_id: Workflow instance ID.

    Returns:
        List of timeline entry dictionaries.
    """
    db = get_db()

    entries = db.execute(
        """
        SELECT
            wsi.wsi_id as step_id,
            wsi.wsi_step_key as step_key,
            wsi.wsi_status as status,
            wsi.wsi_entered_at as entered_at,
            wsi.wsi_accepted_at as accepted_at,
            wsi.wsi_completed_at as completed_at,
            wsi.wsi_comment as comment,
            u.usr_display_name as assignee_name,
            wft_step.value as step_def_json
        FROM t_workflow_step_instance wsi
        LEFT JOIN t_user u ON u.usr_id = wsi.wsi_assignee_id
        LEFT JOIN json_each(
            (SELECT json_extract(wft_graph, '$.steps') FROM t_workflow_template WHERE wft_id = (
                SELECT wfi_template_id FROM t_workflow_instance WHERE wfi_id = ?
            ))
        ) wft_step
        ON json_extract(wft_step.value, '$.key') = wsi.wsi_step_key
        WHERE wsi.wsi_instance_id = ?
        ORDER BY wsi.wsi_entered_at ASC
        """,
        (instance_id, instance_id),
    ).fetchall()

    result = []
    for entry in entries:
        step_def = json.loads(entry["step_def_json"]) if entry["step_def_json"] else {}
        result.append({
            "wsi_id": entry["step_id"],
            "wsi_step_key": entry["step_key"],
            "wsi_status": entry["status"],
            "wsi_entered_at": entry["entered_at"],
            "wsi_accepted_at": entry["accepted_at"],
            "wsi_completed_at": entry["completed_at"],
            "wsi_comment": entry["comment"],
            "wsi_assignee_name": entry["assignee_name"],
            "step_id": entry["step_id"],
            "step_key": entry["step_key"],
            "step_name": step_def.get("name_en", entry["step_key"]),
            "step_type": step_def.get("type", "Task"),
            "status": entry["status"],
            "assignee": entry["assignee_name"],
            "entered_at": entry["entered_at"],
            "accepted_at": entry["accepted_at"],
            "completed_at": entry["completed_at"],
            "comment": entry["comment"],
        })

    return result


def get_workbench_data(instance_id: int, current_user_id: int) -> Dict[str, Any]:
    """Get complete workbench data for a workflow instance.

    This is the main data-loading function for the workflow workbench.
    It returns all information needed to render the workbench UI in a single call.

    Args:
        instance_id: Workflow instance ID.
        current_user_id: ID of the user requesting the workbench.

    Returns:
        Dictionary containing:
        - workflow_summary: instance info with template name, status, outcome
        - current_step: active step card with assignee, status, deadlines
        - field_definitions: editable field schema from workflow graph
        - field_values: saved field values for all steps
        - context_fields: read-only context data from prior steps
        - attachments: list of attachments for current step
        - timeline: all step history for the instance
        - eligible_users: users eligible for delegation/reassignment

    Raises:
        ValueError: If instance not found or user not authorized.
    """
    db = get_db()

    # Get workflow instance with template info
    instance = db.execute(
        """
        SELECT
            wfi.wfi_id,
            wfi.wfi_template_id,
            wfi.wfi_action_id,
            wfi.wfi_status,
            wfi.wfi_started_at,
            wfi.wfi_completed_at,
            wfi.wfi_outcome,
            wft.wft_id,
            wft.wft_name_en,
            wft.wft_name_cn,
            wft.wft_type
        FROM t_workflow_instance wfi
        JOIN t_workflow_template wft ON wfi.wfi_template_id = wft.wft_id
        WHERE wfi.wfi_id = ?
        """,
        (instance_id,),
    ).fetchone()

    if not instance:
        raise ValueError("Workflow instance not found")

    instance_dict = dict(instance)

    # Get action info if bound
    action_info = None
    if instance_dict["wfi_action_id"]:
        action = db.execute(
            """
            SELECT act_id, act_title, act_status, act_priority
            FROM t_action
            WHERE act_id = ?
            """,
            (instance_dict["wfi_action_id"],),
        ).fetchone()
        if action:
            action_info = dict(action)

    # Get current active step(s)
    current_steps = db.execute(
        """
        SELECT
            wsi.wsi_id,
            wsi.wsi_step_key,
            wsi.wsi_status,
            wsi.wsi_assignee_id,
            wsi.wsi_entered_at,
            wsi.wsi_accepted_at,
            wsi.wsi_sla_deadline,
            wsi.wsi_comment,
            u.usr_display_name as assignee_name,
            wst.wst_name_en as step_name,
            wst.wst_type as step_type
        FROM t_workflow_step_instance wsi
        LEFT JOIN t_user u ON u.usr_id = wsi.wsi_assignee_id
        LEFT JOIN json_each(
            (SELECT wft_graph FROM t_workflow_template WHERE wft_id = ?)
        ) as step_json
        LEFT JOIN json_tree(step_json.value, '$.steps') as step_tree
        LEFT JOIN json_each(step_tree.value) as step_fields
        LEFT JOIN (
            SELECT
                json_extract(value, '$.key') as wst_key,
                json_extract(value, '$.type') as wst_type,
                json_extract(value, '$.name_en') as wst_name_en,
                json_extract(value, '$.name_cn') as wst_name_cn
            FROM json_each(
                (SELECT json_extract(wft_graph, '$.steps') FROM t_workflow_template WHERE wft_id = ?)
            )
        ) wst ON wst.wst_key = wsi.wsi_step_key
        WHERE wsi.wsi_instance_id = ?
          AND wsi.wsi_status IN ('Pending', 'Accepted', 'WaitingForChild')
        ORDER BY wsi.wsi_entered_at ASC
        """,
        (instance_id, instance_id, instance_id),
    ).fetchall()

    # Simpler approach: get step instances and extract step name from graph
    current_steps = db.execute(
        """
        SELECT
            wsi.wsi_id,
            wsi.wsi_step_key,
            wsi.wsi_status,
            wsi.wsi_assignee_id,
            wsi.wsi_entered_at,
            wsi.wsi_accepted_at,
            wsi.wsi_sla_deadline,
            wsi.wsi_comment,
            u.usr_display_name as assignee_name
        FROM t_workflow_step_instance wsi
        LEFT JOIN t_user u ON u.usr_id = wsi.wsi_assignee_id
        WHERE wsi.wsi_instance_id = ?
          AND wsi.wsi_status IN ('Pending', 'Accepted', 'WaitingForChild')
        ORDER BY wsi.wsi_entered_at ASC
        """,
        (instance_id,),
    ).fetchall()

    # Load graph to get step definitions
    import json
    from actionhub.workflow.graph import load_graph, get_step, get_fields_for_step

    graph_data = db.execute(
        "SELECT wft_graph FROM t_workflow_template WHERE wft_id = ?",
        (instance_dict["wft_id"],),
    ).fetchone()

    graph = load_graph(graph_data["wft_graph"]) if graph_data else {}

    current_steps_list = []
    for step in current_steps:
        step_dict = dict(step)
        step_def = get_step(graph, step_dict["wsi_step_key"])
        step_dict["step_name"] = step_def.get("name_en", step_dict["wsi_step_key"])
        step_dict["step_type"] = step_def.get("type", "Task")
        current_steps_list.append(step_dict)

    # Get field definitions and values
    field_definitions = []
    fields_by_step = {}
    sfv_cols = {
        row[1]
        for row in db.execute("PRAGMA table_info(t_workflow_step_field_value)").fetchall()
    }
    if "wsi_instance_id" in sfv_cols:
        field_id_col, field_step_col = "wsi_instance_id", "wsi_step_key"
    elif "wsf_instance_id" in sfv_cols:
        field_id_col, field_step_col = "wsf_instance_id", "wsf_step_key"
    elif "sfv_step_inst_id" in sfv_cols:
        field_id_col, field_step_col = "sfv_step_inst_id", None
    else:
        field_id_col, field_step_col = None, None

    for step in current_steps_list:
        step_def = get_step(graph, step["wsi_step_key"])
        step_fields = get_fields_for_step(graph, step["wsi_step_key"])
        for field in step_fields:
            field_definitions.append({
                "step_key": step["wsi_step_key"],
                "step_id": step["wsi_id"],
                **field,
            })

        # Get saved values for this step
        if field_id_col and field_step_col:
            field_values = db.execute(
                f"""
                SELECT wsf_field_code, wsf_value
                FROM t_workflow_step_field_value
                WHERE {field_id_col} = ? AND {field_step_col} = ?
                """,
                (instance_id, step["wsi_step_key"]),
            ).fetchall()
        elif field_id_col:
            field_values = db.execute(
                f"""
                SELECT wsf_field_code, wsf_value
                FROM t_workflow_step_field_value
                WHERE {field_id_col} = ?
                """,
                (instance_id,),
            ).fetchall()
        else:
            field_values = []
        fields_by_step[step["wsi_id"]] = {
            row["wsf_field_code"]: row["wsf_value"] for row in field_values
        }

    # Get attachments for current step (first active step)
    attachments = []
    if current_steps_list:
        from actionhub.workflow.attachments import get_step_attachments

        attachments = get_step_attachments(current_steps_list[0]["wsi_id"])

    # Get timeline
    from actionhub.workflow.service import get_workflow_history

    timeline = get_workflow_history(instance_id)

    # Get eligible users for current step (for delegation/reassignment)
    from actionhub.workflow.assignment import get_eligible_users

    eligible_users = []
    if current_steps_list:
        step_def = get_step(graph, current_steps_list[0]["wsi_step_key"])
        eligible_users = get_eligible_users(instance_id, current_steps_list[0]["wsi_step_key"], graph, db)

    return {
        "workflow_summary": {
            "id": instance_dict["wfi_id"],
            "template_id": instance_dict["wft_id"],
            "template_name": instance_dict["wft_name_en"],
            "template_name_cn": instance_dict["wft_name_cn"],
            "type": instance_dict["wft_type"],
            "status": instance_dict["wfi_status"],
            "outcome": instance_dict["wfi_outcome"],
            "started_at": instance_dict["wfi_started_at"],
            "completed_at": instance_dict["wfi_completed_at"],
            "action": action_info,
        },
        "current_steps": current_steps_list,
        "field_definitions": field_definitions,
        "field_values": fields_by_step,
        "attachments": attachments,
        "timeline": timeline,
        "eligible_users": eligible_users,
    }


def save_step_draft(
    step_instance_id: int,
    fields: List[Dict[str, str]],
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    """Save draft field values for a step without advancing workflow.

    Args:
        step_instance_id: Step instance ID.
        fields: List of {key, value} dictionaries.
        comment: Optional progress comment.

    Returns:
        Dict with success status and saved field count.

    Raises:
        ValueError: If step not found or not in valid status.
    """
    db = get_db()

    # Validate step exists and is in valid status
    step = get_step_instance(step_instance_id)
    if not step:
        raise ValueError("Step instance not found")

    if step["wsi_status"] not in ("Pending", "Accepted", "WaitingForChild"):
        raise ValueError(
            f"Cannot save draft for step in status {step['wsi_status']}"
        )

    # Upsert field values
    sfv_cols = {
        row[1]
        for row in db.execute("PRAGMA table_info(t_workflow_step_field_value)").fetchall()
    }
    has_compat_cols = "wsi_instance_id" in sfv_cols and "wsi_step_key" in sfv_cols
    saved_count = 0
    for field in fields:
        field_key = field.get("key")
        field_value = field.get("value")

        if not field_key:
            continue

        if has_compat_cols:
            db.execute(
                """
                INSERT INTO t_workflow_step_field_value
                (wsf_instance_id, wsf_step_key, wsf_field_code, wsf_value, wsi_instance_id, wsi_step_key)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(wsf_instance_id, wsf_step_key, wsf_field_code)
                DO UPDATE SET wsf_value = excluded.wsf_value,
                              wsi_instance_id = excluded.wsi_instance_id,
                              wsi_step_key = excluded.wsi_step_key
                """,
                (
                    step["wsi_instance_id"],
                    step["wsi_step_key"],
                    field_key,
                    field_value,
                    step["wsi_instance_id"],
                    step["wsi_step_key"],
                ),
            )
        else:
            db.execute(
                """
                INSERT INTO t_workflow_step_field_value
                (wsf_instance_id, wsf_step_key, wsf_field_code, wsf_value)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(wsf_instance_id, wsf_step_key, wsf_field_code)
                DO UPDATE SET wsf_value = excluded.wsf_value
                """,
                (
                    step["wsi_instance_id"],
                    step["wsi_step_key"],
                    field_key,
                    field_value,
                ),
            )
        saved_count += 1

    # Update comment if provided
    if comment:
        db.execute(
            """
            UPDATE t_workflow_step_instance
            SET wsi_comment = ?
            WHERE wsi_id = ?
            """,
            (comment, step_instance_id),
        )

    db.commit()

    return {
        "success": True,
        "step_id": step_instance_id,
        "fields_saved": saved_count,
        "comment_updated": bool(comment),
    }
