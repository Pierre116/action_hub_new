"""Step field value CRUD and validation.

This module handles form field values for workflow steps, including
validation by field type (text, dropdown, date, number, checkbox, checklist).
"""
import json
from datetime import datetime
from typing import Any

from actionhub.middleware.db import get_db
from actionhub.workflow.graph import get_fields_for_step, get_step

# Valid field types as per R16 §5.3
VALID_FIELD_TYPES = {"text", "dropdown", "date", "number", "checkbox", "checklist"}


def validate_field_value(field_def: dict, value) -> str | None:
    """Validate a single field value against its definition.

    Returns error message or None if valid.

    Rules:
    - 'required' fields must not be empty/null
    - 'dropdown' value must be in field_def['options']
    - 'date' must be ISO format (YYYY-MM-DD)
    - 'number' must be numeric
    - 'checkbox' must be boolean
    - 'checklist' must be JSON list of strings, subset of options

    Args:
        field_def: Field definition from workflow graph.
        value: Value to validate.

    Returns:
        Error message string or None if valid.
    """
    field_type = field_def.get("type", "text")
    field_key = field_def.get("key", "unknown")

    # Check required
    if field_def.get("required", False):
        if value is None or (isinstance(value, str) and not value.strip()):
            return f"Field '{field_key}' is required"

    # Skip further validation if empty and not required
    if value is None or (isinstance(value, str) and not value.strip()):
        return None

    # Type-specific validation
    if field_type == "dropdown":
        options = field_def.get("options", [])
        if value not in options:
            return f"Field '{field_key}' value '{value}' not in allowed options: {options}"

    elif field_type == "date":
        # Check ISO format YYYY-MM-DD
        if isinstance(value, str):
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return f"Field '{field_key}' must be in YYYY-MM-DD format"
        else:
            return f"Field '{field_key}' must be a string date"

    elif field_type == "number":
        try:
            float(value)
        except (ValueError, TypeError):
            return f"Field '{field_key}' must be a number"

    elif field_type == "checkbox":
        if not isinstance(value, bool):
            return f"Field '{field_key}' must be a boolean"

    elif field_type == "checklist":
        options = field_def.get("options", [])
        if isinstance(value, str):
            try:
                value_list = json.loads(value)
            except json.JSONDecodeError:
                return f"Field '{field_key}' must be a JSON array"
        elif isinstance(value, list):
            value_list = value
        else:
            return f"Field '{field_key}' must be a list or JSON array"

        if not isinstance(value_list, list):
            return f"Field '{field_key}' must be a list"

        for item in value_list:
            if item not in options:
                return f"Field '{field_key}' item '{item}' not in allowed options: {options}"

    return None


def save_field_values(
    step_instance_id: int,
    field_values: dict,
    filled_by: int,
    graph: dict,
    step_key: str,
) -> list[str]:
    """Validate and save field values for a step instance.

    OP27 (S11): UPSERT via UNIQUE(sfv_step_inst_id, sfv_field_key).

    Args:
        step_instance_id: Step instance ID to save values for.
        field_values: Dictionary of {field_key: value}.
        filled_by: User ID filling the form.
        graph: Workflow graph dictionary.
        step_key: Step key for field lookup.

    Returns:
        List of validation error messages (empty = success).
    """
    db = get_db()
    now = datetime.now()

    # Get field definitions from graph
    field_defs = get_fields_for_step(graph, step_key)
    field_def_map = {f["key"]: f for f in field_defs}

    errors = []

    # Validate all fields first
    for field_key, value in field_values.items():
        field_def = field_def_map.get(field_key)
        if not field_def:
            errors.append(f"Unknown field key: {field_key}")
            continue

        error = validate_field_value(field_def, value)
        if error:
            errors.append(error)

    # If validation errors, return without saving
    if errors:
        return errors

    # Save all valid fields
    for field_key, value in field_values.items():
        if field_key not in field_def_map:
            continue

        # Convert checklist to JSON string
        if isinstance(value, list):
            value = json.dumps(value)

        # Upsert: INSERT OR REPLACE
        db.execute(
            """INSERT INTO t_workflow_step_field_value
               (sfv_step_inst_id, sfv_field_key, sfv_value, sfv_filled_by, sfv_filled_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(sfv_step_inst_id, sfv_field_key)
               DO UPDATE SET sfv_value = ?, sfv_filled_by = ?, sfv_filled_at = ?""",
            (
                step_instance_id,
                field_key,
                value,
                filled_by,
                now,
                value,
                filled_by,
                now,
            ),
        )

    db.commit()
    return []


def get_field_values(step_instance_id: int) -> dict:
    """Return {field_key: value} for all saved fields on a step instance.

    Args:
        step_instance_id: Step instance ID.

    Returns:
        Dictionary of field values.
    """
    db = get_db()

    rows = db.execute(
        """SELECT sfv_field_key, sfv_value FROM t_workflow_step_field_value
           WHERE sfv_step_inst_id = ?""",
        (step_instance_id,),
    ).fetchall()

    result = {}
    for row in rows:
        key = row["sfv_field_key"]
        value = row["sfv_value"]

        # Try to parse JSON for checklist type
        if value and value.startswith("["):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass

        result[key] = value

    return result


def get_field_values_for_instance(instance_id: int) -> dict:
    """Return {step_key: {field_key: value}} for ALL steps in a workflow instance.

    Used for cross-step data visibility (Q12: earlier step data visible to later steps).

    Args:
        instance_id: Workflow instance ID.

    Returns:
        Nested dictionary: {step_key: {field_key: value}}.
    """
    db = get_db()

    # Get all step instances for this workflow
    steps = db.execute(
        """SELECT wsi_id, wsi_step_key FROM t_workflow_step_instance
           WHERE wsi_instance_id = ?""",
        (instance_id,),
    ).fetchall()

    result = {}
    for step in steps:
        step_key = step["wsi_step_key"]
        step_instance_id = step["wsi_id"]

        # Get field values for this step
        field_values = get_field_values(step_instance_id)
        result[step_key] = field_values

    return result


def get_field_value(step_instance_id: int, field_key: str) -> Any:
    """Get a single field value.

    Args:
        step_instance_id: Step instance ID.
        field_key: Field key to retrieve.

    Returns:
        Field value or None if not found.
    """
    db = get_db()

    row = db.execute(
        """SELECT sfv_value FROM t_workflow_step_field_value
           WHERE sfv_step_inst_id = ? AND sfv_field_key = ?""",
        (step_instance_id, field_key),
    ).fetchone()

    if row:
        value = row["sfv_value"]
        # Try to parse JSON for checklist type
        if value and value.startswith("["):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        return value
    return None
