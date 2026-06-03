from actionhub.utils.date_utils import parse_date


VALID_PRIORITIES = {"Critical", "High", "Medium", "Low"}
VALID_STATUSES = {"Open", "In Progress", "On Hold", "Done", "Cancelled"}
VALID_ASSIGNMENT_ROLES = {"Lead"}

# Finite State Machine for action status transitions.
# Terminal states (Done, Cancelled) have no outgoing transitions.
STATUS_TRANSITIONS: dict[str, set[str]] = {
    "Open":        {"In Progress", "On Hold", "Cancelled"},
    "In Progress": {"On Hold", "Done", "Cancelled"},
    "On Hold":     {"Open", "In Progress", "Cancelled"},
    "Done":        set(),
    "Cancelled":   set(),
}

# Legacy aliases accepted on input and mapped to canonical values.
_STATUS_ALIASES: dict[str, str] = {
    "Completed": "Done",
    "Closed": "Done",
    "Ongoing": "In Progress",
}


def validate_title(title: str) -> str:
    normalized = (title or "").strip()
    if len(normalized) < 5 or len(normalized) > 200:
        raise ValueError("title must be between 5 and 200 characters")
    return normalized


def validate_priority(priority: str | None) -> str:
    value = (priority or "Medium").strip()
    if value not in VALID_PRIORITIES:
        raise ValueError("priority must be one of: Critical, High, Medium, Low")
    return value


def validate_status(status: str) -> str:
    value = (status or "").strip()
    value = _STATUS_ALIASES.get(value, value)
    if value not in VALID_STATUSES:
        raise ValueError("invalid status value")
    return value


def validate_status_transition(current_status: str, new_status: str) -> None:
    """Raise ValueError if *current_status* → *new_status* is not allowed by the FSM."""
    allowed = STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ValueError(
            f"cannot transition from '{current_status}' to '{new_status}'; "
            f"allowed: {sorted(allowed) if allowed else 'none (terminal state)'}"
        )


def validate_deadline(deadline: str | None) -> str | None:
    if deadline is None:
        return None
    _ = parse_date(deadline)
    return deadline


def validate_assignment_role(role: str) -> str:
    value = (role or "").strip()
    # Backward compatibility: map legacy roles to Lead.
    if value in ("Delegate", "Decide", "Participate", "Assigned"):
        value = "Lead"
    if value not in VALID_ASSIGNMENT_ROLES:
        raise ValueError("role must be Lead")
    return value
