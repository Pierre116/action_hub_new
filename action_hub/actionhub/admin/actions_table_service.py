"""Admin inline actions table service — paginated list + inline update."""
from __future__ import annotations

from math import ceil

from actionhub.middleware.db import get_db


def list_actions_paged(filters: dict, page: int = 1, per_page: int = 25) -> dict:
    db = get_db()
    page = max(1, int(page))
    per_page = min(100, max(1, int(per_page)))

    where_parts: list[str] = []
    params: list[object] = []

    if filters.get("status"):
        where_parts.append("a.act_status = ?")
        params.append(filters["status"])
    if filters.get("team_id") or filters.get("department_id"):
        where_parts.append("a.act_team_id = ?")
        params.append(int(filters.get("team_id") or filters["department_id"]))
    if filters.get("priority"):
        where_parts.append("a.act_priority = ?")
        params.append(filters["priority"])
    if filters.get("topic_id") or filters.get("topic_code"):
        topic_value = filters.get("topic_id") or filters.get("topic_code")
        where_parts.append("(a.act_topic_id = ? OR a.act_secondary_topic_id = ?)")
        params.append(topic_value)
        params.append(topic_value)
    if filters.get("search"):
        where_parts.append("(a.act_title LIKE ? OR a.act_ref LIKE ?)")
        term = f"%{str(filters['search']).strip()}%"
        params.extend([term, term])

    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    total = int(
        db.execute(f"SELECT COUNT(*) FROM t_action a {where_sql}", params).fetchone()[0]
    )
    offset = (page - 1) * per_page

    rows = db.execute(
        f"""
        SELECT
            a.act_id, a.act_ref, a.act_title, a.act_status,
            a.act_priority, a.act_deadline, a.act_topic_id, a.act_secondary_topic_id,
            m.min_title AS meeting_title,
            m.min_date  AS meeting_date,
            tm.tea_name_en AS team_name,
               t.top_name AS topic_name,
               tp2.top_name AS secondary_topic_name,
            (SELECT u2.usr_display_name FROM t_assignment sg2
             JOIN t_user u2 ON u2.usr_id = sg2.asg_user_id
             WHERE sg2.asg_action_id = a.act_id AND INSTR(',' || sg2.asg_role || ',', ',Lead,') > 0 LIMIT 1) AS lead_name,
            (SELECT COUNT(*) FROM t_assignment z WHERE z.asg_action_id = a.act_id) AS asg_total
        FROM t_action a
        LEFT JOIN t_meeting_instance m ON m.min_id = a.act_meeting_inst_id
        LEFT JOIN t_team tm ON tm.tea_id = a.act_team_id
        LEFT JOIN t_topic t ON t.top_id = a.act_topic_id
        LEFT JOIN t_topic tp2 ON tp2.top_id = a.act_secondary_topic_id
        {where_sql}
        ORDER BY a.act_updated_at DESC, a.act_id DESC
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
            "total_pages": max(1, ceil(total / per_page)),
        },
    }


def inline_update(act_id: int, payload: dict, actor_id: int) -> dict:
    """Allow inline edit of: title, status, priority, deadline, topic_id."""
    db = get_db()
    allowed = {
        "title": "act_title",
        "status": "act_status",
        "priority": "act_priority",
        "deadline": "act_deadline",
        "topic_id": "act_topic_id",
    }

    set_parts: list[str] = []
    set_vals: list[object] = []
    for key, col in allowed.items():
        if key in payload:
            val = payload[key] if payload[key] != "" else None
            if key == "topic_id" and not val:
                raise ValueError("topic_id cannot be removed — every action must belong to a topic")
            set_parts.append(f"{col} = ?")
            set_vals.append(val)

    if not set_parts:
        raise ValueError("nothing to update")

    set_parts.append("act_updated_at = CURRENT_TIMESTAMP")
    db.execute(
        f"UPDATE t_action SET {', '.join(set_parts)} WHERE act_id = ?",
        [*set_vals, act_id],
    )
    db.commit()

    row = db.execute(
        """
        SELECT a.act_id, a.act_ref, a.act_title, a.act_status, a.act_priority,
             a.act_deadline, a.act_topic_id, a.act_secondary_topic_id,
               m.min_title AS meeting_title,
               m.min_date  AS meeting_date,
               tm.tea_name_en AS team_name,
               t.top_name AS topic_name,
               tp2.top_name AS secondary_topic_name,
               (SELECT u2.usr_display_name FROM t_assignment sg2
                JOIN t_user u2 ON u2.usr_id = sg2.asg_user_id
                WHERE sg2.asg_action_id = a.act_id AND INSTR(',' || sg2.asg_role || ',', ',Lead,') > 0 LIMIT 1) AS lead_name,
            (SELECT COUNT(*) FROM t_assignment z WHERE z.asg_action_id = a.act_id) AS asg_total
        FROM t_action a
        LEFT JOIN t_meeting_instance m ON m.min_id = a.act_meeting_inst_id
        LEFT JOIN t_team tm ON tm.tea_id = a.act_team_id
        LEFT JOIN t_topic t ON t.top_id = a.act_topic_id
        LEFT JOIN t_topic tp2 ON tp2.top_id = a.act_secondary_topic_id
        WHERE a.act_id = ?
        """,
        (act_id,),
    ).fetchone()
    if not row:
        raise ValueError("action not found")
    return dict(row)
