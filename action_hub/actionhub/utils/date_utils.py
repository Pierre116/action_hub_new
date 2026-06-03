from datetime import date, datetime


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text).date()
    except ValueError as error:
        raise ValueError("Invalid date format; expected YYYY-MM-DD") from error


def is_overdue(deadline: str | None, status: str) -> bool:
    if not deadline or status in {"Done", "Cancelled"}:
        return False
    due = parse_date(deadline)
    if not due:
        return False
    return due < date.today()


def sla_days(priority: str) -> int:
    mapping = {
        "Critical": 3,
        "High": 7,
        "Medium": 14,
        "Low": 30,
    }
    return mapping.get(priority, 14)


def sla_status(deadline: str | None, priority: str, status: str) -> str:
    if status in {"Done", "Cancelled"}:
        return "Closed"
    if not deadline:
        return "Unknown"
    due = parse_date(deadline)
    if not due:
        return "Unknown"
    today = date.today()
    if due < today:
        return "Overdue"
    remaining = (due - today).days
    if remaining <= max(1, sla_days(priority) // 3):
        return "At Risk"
    return "On Track"
