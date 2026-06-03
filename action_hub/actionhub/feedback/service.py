"""Feedback service — CRUD for t_feedback."""
from __future__ import annotations

import io
from datetime import datetime

from actionhub.middleware.db import get_db


# ── Pages known to the app (for the "page" dropdown) ─────────────────────────
KNOWN_PAGES = [
    ("dashboard", "My Dashboard / 我的工作台"),
    ("team_dashboard", "Team Dashboard / 团队看板"),
    ("topic_dashboard", "Category Dashboard / 类别看板"),
    ("actions_list", "Actions List / 行动列表"),
    ("action_detail", "Action Detail / 行动详情"),
    ("meetings", "Meetings / 会议"),
    ("gantt", "Gantt View / 甘特图"),
    ("admin_users", "Admin — Users / 管理员 — 用户"),
    ("admin_teams", "Admin — Teams / 管理员 — 团队"),
    ("admin_imports", "Admin — Import / 管理员 — 导入"),
    ("admin_topics", "Admin — Categories / 管理员 — 类别"),
    ("feedback", "Feedback / 反馈"),
    ("other", "Other / 其他"),
]

STATUSES = ["New", "Acknowledged", "In Progress", "Resolved", "Declined"]
CATEGORIES = ["Bug", "Feature", "Usability", "General"]
PRIORITIES = ["Low", "Medium", "High"]


def create_feedback(user_id: int, payload: dict, screenshot_data: bytes | None, screenshot_name: str | None) -> int:
    category = payload.get("category", "").strip()
    title = payload.get("title", "").strip()
    description = payload.get("description", "").strip()
    priority = payload.get("priority", "Medium").strip()
    page = payload.get("page", "").strip() or None

    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}")
    if not title or len(title) < 5:
        raise ValueError("title must be at least 5 characters")
    if not description:
        raise ValueError("description is required")
    if priority not in PRIORITIES:
        priority = "Medium"

    db = get_db()
    cur = db.execute(
        """
        INSERT INTO t_feedback
            (fbk_user_id, fbk_category, fbk_page, fbk_title, fbk_description,
             fbk_priority, fbk_screenshot, fbk_screenshot_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, category, page, title, description, priority, screenshot_data, screenshot_name),
    )
    db.commit()
    return int(cur.lastrowid)


def list_user_feedback(user_id: int) -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT f.fbk_id, f.fbk_category, f.fbk_page, f.fbk_title,
               f.fbk_priority, f.fbk_status, f.fbk_admin_response, f.fbk_created_at
        FROM t_feedback f
        WHERE f.fbk_user_id = ?
        ORDER BY f.fbk_created_at DESC
        """,
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_feedback(feedback_id: int, user_id: int | None = None) -> dict:
    """Load one feedback entry. If user_id given, must belong to that user (unless admin)."""
    db = get_db()
    row = db.execute(
        """
        SELECT f.*, u.usr_display_name AS submitter_name,
               u.usr_employee_id AS submitter_employee_id
        FROM t_feedback f
        JOIN t_user u ON u.usr_id = f.fbk_user_id
        WHERE f.fbk_id = ?
        """,
        (feedback_id,),
    ).fetchone()
    if not row:
        raise ValueError("feedback not found")
    entry = dict(row)
    if user_id is not None and entry["fbk_user_id"] != user_id:
        raise PermissionError("forbidden")
    # Don't return raw blob in listing
    entry.pop("fbk_screenshot", None)
    return entry


def list_all_feedback(
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    page: int = 1,
    per_page: int = 25,
) -> dict:
    db = get_db()
    where_clauses: list[str] = []
    params: list = []

    if status:
        where_clauses.append("f.fbk_status = ?")
        params.append(status)
    if category:
        where_clauses.append("f.fbk_category = ?")
        params.append(category)
    if priority:
        where_clauses.append("f.fbk_priority = ?")
        params.append(priority)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    total = db.execute(
        f"SELECT COUNT(*) FROM t_feedback f {where_sql}", params
    ).fetchone()[0]

    offset = (page - 1) * per_page
    rows = db.execute(
        f"""
        SELECT f.fbk_id, f.fbk_category, f.fbk_page, f.fbk_title,
               f.fbk_description, f.fbk_priority, f.fbk_status, f.fbk_admin_response,
               f.fbk_created_at, f.fbk_updated_at,
               u.usr_display_name AS submitter_name,
               u.usr_employee_id AS submitter_employee_id,
               CASE WHEN f.fbk_screenshot IS NOT NULL THEN 1 ELSE 0 END AS has_screenshot
        FROM t_feedback f
        JOIN t_user u ON u.usr_id = f.fbk_user_id
        {where_sql}
        ORDER BY f.fbk_created_at DESC
        LIMIT ? OFFSET ?
        """,
        [*params, per_page, offset],
    ).fetchall()

    return {
        "items": [dict(r) for r in rows],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        },
    }


def update_feedback_status(feedback_id: int, admin_user_id: int, payload: dict) -> dict:
    status = payload.get("status", "").strip()
    response = payload.get("admin_response", "")

    if status and status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")

    db = get_db()
    if not db.execute("SELECT fbk_id FROM t_feedback WHERE fbk_id = ?", (feedback_id,)).fetchone():
        raise ValueError("feedback not found")

    parts: list[str] = ["fbk_updated_at = CURRENT_TIMESTAMP"]
    vals: list = []

    if status:
        parts.append("fbk_status = ?")
        vals.append(status)
    if response is not None:
        parts.append("fbk_admin_response = ?")
        vals.append(response)
        parts.append("fbk_responded_by = ?")
        vals.append(admin_user_id)

    db.execute(
        f"UPDATE t_feedback SET {', '.join(parts)} WHERE fbk_id = ?",
        [*vals, feedback_id],
    )
    db.commit()
    return get_feedback(feedback_id)


def export_feedback_xlsx() -> bytes:
    """Export all feedback to Excel bytes."""
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("openpyxl is required for export")

    db = get_db()
    rows = db.execute(
        """
        SELECT f.fbk_id, u.usr_employee_id, u.usr_display_name,
               f.fbk_category, f.fbk_priority, f.fbk_status,
               f.fbk_title, f.fbk_description, f.fbk_page,
               f.fbk_admin_response, f.fbk_created_at, f.fbk_updated_at
        FROM t_feedback f
        JOIN t_user u ON u.usr_id = f.fbk_user_id
        ORDER BY f.fbk_created_at DESC
        """
    ).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Feedback"
    headers = ["ID", "Employee ID", "Name", "Category", "Priority", "Status",
               "Title", "Description", "Page", "Admin Response", "Created", "Updated"]
    ws.append(headers)
    for row in rows:
        ws.append(list(row))

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
