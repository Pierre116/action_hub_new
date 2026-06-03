"""Gateway step logic for workflow engine V3 (WF-11).

Evaluates decision tables for Gateway steps based on prior step field values.
"""
from typing import Any, Dict, List, Optional


def evaluate_decision_table(decision_table: List[Dict[str, Any]], field_values: Dict[str, Any]) -> Optional[str]:
    """
    Evaluate a decision table for a Gateway step.
    Args:
        decision_table: List of dicts, each representing a row with conditions and a 'next' key.
        field_values: Dict of field_code: value from prior steps.
    Returns:
        The key of the next step to take, or None if no match.
    """
    for row in decision_table:
        conditions = row.get('conditions', {})
        if all(field_values.get(k) == v for k, v in conditions.items()):
            return row.get('next')
    return None
