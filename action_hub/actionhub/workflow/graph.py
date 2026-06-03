"""Parse and validate wft_graph JSON structures.

This module provides pure functions for working with workflow graph definitions
stored in the wft_graph column of t_workflow_template. No database access.
"""
import json
from typing import Any


def load_graph(graph_json: str) -> dict:
    """Parse wft_graph TEXT column into dict.

    Args:
        graph_json: JSON string representing the workflow graph.

    Returns:
        Parsed dictionary with 'steps', 'transitions', and optionally 'bindings'.

    Raises:
        ValueError: If the JSON is invalid.
    """
    try:
        graph = json.loads(graph_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in workflow graph: {e}")
    return graph


def validate_graph(graph: dict) -> list[str]:
    """Return list of validation errors. Empty = valid.

    Rules:
    - Must have 'steps' dict with >= 2 entries
    - Must have 'transitions' list with >= 1 entry
    - Every transition 'from'/'to' must reference existing step keys
    - Exactly one step with type='End'
    - At least one step with order=1 (start step)
    - Join steps must have >= 2 incoming transitions
    - No orphan steps (every step reachable from start via transitions)

    Args:
        graph: Parsed workflow graph dictionary.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []

    # Check required top-level keys
    if not isinstance(graph.get("steps"), dict):
        errors.append("Graph must have a 'steps' object")
        return errors

    if not isinstance(graph.get("transitions"), list):
        errors.append("Graph must have a 'transitions' array")
        return errors

    steps = graph["steps"]
    transitions = graph["transitions"]

    # Must have at least 2 steps
    if len(steps) < 2:
        errors.append(f"Graph must have at least 2 steps, found {len(steps)}")

    # Must have at least 1 transition
    if len(transitions) < 1:
        errors.append(f"Graph must have at least 1 transition, found {len(transitions)}")

    step_keys = set(steps.keys())

    # Validate transitions reference existing steps
    for i, trans in enumerate(transitions):
        if not isinstance(trans, dict):
            errors.append(f"Transition {i} must be an object")
            continue
        from_key = trans.get("from")
        to_key = trans.get("to")
        if from_key not in step_keys:
            errors.append(f"Transition {i}: 'from' key '{from_key}' not found in steps")
        if to_key not in step_keys:
            errors.append(f"Transition {i}: 'to' key '{to_key}' not found in steps")

    # Must have at least one End step (V3 allows multiple End steps)
    end_steps = [k for k, v in steps.items() if v.get("type") == "End"]
    if len(end_steps) < 1:
        errors.append("Graph must have at least one End step")

    # Must have at least one start step (order=1)
    start_steps = [k for k, v in steps.items() if v.get("order") == 1]
    if len(start_steps) < 1:
        errors.append("Graph must have at least one step with order=1 (start step)")

    # Validate each step
    for step_key, step_def in steps.items():
        if not isinstance(step_def, dict):
            errors.append(f"Step '{step_key}' must be an object")
            continue

        # Validate step type
        valid_types = {"Task", "Approval", "Join", "End", "Gateway", "Service", "Notification", "Timer", "Subprocess"}
        step_type = step_def.get("type")
        if step_type not in valid_types:
            errors.append(f"Step '{step_key}' has invalid type '{step_type}'. Must be one of: {valid_types}")

        # Join steps require >= 2 incoming transitions
        if step_type == "Join":
            incoming = [t for t in transitions if t.get("to") == step_key]
            if len(incoming) < 2:
                errors.append(f"Join step '{step_key}' must have at least 2 incoming transitions, found {len(incoming)}")

    # Check for orphan steps (not reachable from start)
    if start_steps and step_keys:
        reachable = set()
        queue = list(start_steps)
        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)
            # Find outgoing transitions
            for trans in transitions:
                if trans.get("from") == current:
                    next_step = trans.get("to")
                    if next_step not in reachable:
                        queue.append(next_step)

        orphans = step_keys - reachable
        if orphans:
            errors.append(f"Orphan steps found (not reachable from start): {orphans}")

    return errors


def get_start_steps(graph: dict) -> list[str]:
    """Return step keys with order=1 (entry points).

    Args:
        graph: Parsed workflow graph dictionary.

    Returns:
        List of step keys that have order=1.
    """
    return [k for k, v in graph.get("steps", {}).items() if v.get("order") == 1]


def get_next_steps(graph: dict, current_step_key: str) -> list[str]:
    """Return step keys reachable via transitions from current_step_key.

    Args:
        graph: Parsed workflow graph dictionary.
        current_step_key: The step key to get next steps from.

    Returns:
        List of step keys that are reachable from the current step.
    """
    next_steps = []
    for trans in graph.get("transitions", []):
        if trans.get("from") == current_step_key:
            next_steps.append(trans.get("to"))
    return next_steps


def get_incoming_steps(graph: dict, step_key: str) -> list[str]:
    """Return step keys that have a transition TO step_key.

    Args:
        graph: Parsed workflow graph dictionary.
        step_key: The target step key.

    Returns:
        List of step keys that transition to the given step.
    """
    incoming = []
    for trans in graph.get("transitions", []):
        if trans.get("to") == step_key:
            incoming.append(trans.get("from"))
    return incoming


def is_fork(graph: dict, step_key: str) -> bool:
    """True if step has >1 outgoing transition (parallel dispatch).

    Args:
        graph: Parsed workflow graph dictionary.
        step_key: The step key to check.

    Returns:
        True if the step has multiple outgoing transitions.
    """
    outgoing = get_next_steps(graph, step_key)
    return len(outgoing) > 1


def is_join(graph: dict, step_key: str) -> bool:
    """True if step has type='Join'.

    Args:
        graph: Parsed workflow graph dictionary.
        step_key: The step key to check.

    Returns:
        True if the step is a Join type.
    """
    step = graph.get("steps", {}).get(step_key, {})
    return step.get("type") == "Join"


def get_step(graph: dict, step_key: str) -> dict:
    """Return step definition dict.

    Args:
        graph: Parsed workflow graph dictionary.
        step_key: The step key to retrieve.

    Returns:
        Step definition dictionary.

    Raises:
        KeyError: If step key not found.
    """
    step = graph.get("steps", {}).get(step_key)
    if step is None:
        raise KeyError(f"Step '{step_key}' not found in workflow graph")
    return step


def get_fields_for_step(graph: dict, step_key: str) -> list[dict]:
    """Return field definitions for a step.

    Args:
        graph: Parsed workflow graph dictionary.
        step_key: The step key to get fields for.

    Returns:
        List of field definition dictionaries (empty list if none).
    """
    step = get_step(graph, step_key)
    return step.get("fields", [])


def get_transition_label(graph: dict, from_step: str, to_step: str, lang: str = "en") -> str:
    """Get the transition label between two steps.

    Args:
        graph: Parsed workflow graph dictionary.
        from_step: Source step key.
        to_step: Target step key.
        lang: Language code ('en' or 'cn').

    Returns:
        Transition label, or empty string if not found.
    """
    label_key = f"label_{lang}"
    for trans in graph.get("transitions", []):
        if trans.get("from") == from_step and trans.get("to") == to_step:
            return trans.get(label_key, trans.get("label_en", ""))
    return ""


def get_step_name(graph: dict, step_key: str, lang: str = "en") -> str:
    """Get the localized step name.

    Args:
        graph: Parsed workflow graph dictionary.
        step_key: The step key.
        lang: Language code ('en' or 'cn').

    Returns:
        Step name in the requested language.
    """
    step = get_step(graph, step_key)
    name_key = f"name_{lang}"
    return step.get(name_key, step.get("name_en", step_key))
