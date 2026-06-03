from flask import Blueprint, jsonify, request

from actionhub.middleware.auth_middleware import login_required
from actionhub.middleware.db import get_db


gantt_bp = Blueprint("gantt", __name__, url_prefix="/api/gantt")

_STATUS_ORDER = [
    "Open", "In Progress", "On Hold",
    "Done", "Cancelled",
]


def _build_gantt_query(team_id, topic_id, user_id, statuses):
    """Build a parameterised SELECT for Gantt data."""
    params = []
    where_clauses = ["a.act_deadline IS NOT NULL AND a.act_deadline != ''"]

    if team_id:
        where_clauses.append("a.act_team_id = ?")
        params.append(team_id)

    if topic_id:
        where_clauses.append("(a.act_topic_id = ? OR a.act_secondary_topic_id = ?)")
        params.append(topic_id)
        params.append(topic_id)

    if user_id:
        where_clauses.append(
            "EXISTS (SELECT 1 FROM t_assignment ax "
            "WHERE ax.asg_action_id = a.act_id AND ax.asg_user_id = ?)"
        )
        params.append(user_id)

    if statuses:
        placeholders = ",".join("?" for _ in statuses)
        where_clauses.append(f"a.act_status IN ({placeholders})")
        params.extend(statuses)
    else:
        # Exclude Cancelled by default so they don't clutter the chart
        where_clauses.append("a.act_status != 'Cancelled'")

    where_sql = " AND ".join(where_clauses)
    sql = f"""
        SELECT
            a.act_id        AS id,
            a.act_ref       AS ref,
            a.act_title     AS title,
            a.act_status    AS status,
            a.act_priority  AS priority,
            COALESCE(a.act_start_date, DATE(a.act_created_at)) AS start_date,
            a.act_deadline  AS end_date,
            a.act_actual_date AS actual_date,
            tm.tea_name_en  AS team_name,
            tp.top_name  AS topic_name,
            tp2.top_name AS secondary_topic_name,
            u.usr_display_name AS lead_name
        FROM t_action a
        LEFT JOIN t_team tm ON tm.tea_id = a.act_team_id
        LEFT JOIN t_topic tp ON tp.top_id = a.act_topic_id
        LEFT JOIN t_topic tp2 ON tp2.top_id = a.act_secondary_topic_id
        LEFT JOIN t_assignment asg
            ON asg.asg_action_id = a.act_id AND INSTR(',' || asg.asg_role || ',', ',Lead,') > 0
        LEFT JOIN t_user u ON u.usr_id = asg.asg_user_id
        WHERE {where_sql}
        ORDER BY a.act_deadline ASC, a.act_priority DESC
        LIMIT 200
    """
    return sql, params


@gantt_bp.get("")
@login_required
def gantt_data():
    team_id = request.args.get("team_id", type=int)
    if not team_id:
        team_id = request.args.get("dept_id", type=int)
    topic_id = request.args.get("topic_id", type=int)
    user_id = request.args.get("user_id", type=int)
    raw_statuses = request.args.get("statuses", "")
    statuses = [s.strip() for s in raw_statuses.split(",") if s.strip()] if raw_statuses else []

    sql, params = _build_gantt_query(team_id, topic_id, user_id, statuses)
    db = get_db()
    rows = db.execute(sql, params).fetchall()

    items = [dict(row) for row in rows]
    return jsonify({"data": items, "total": len(items)})


@gantt_bp.get("/filters")
@login_required
def gantt_filters():
    """Return available team, topic, and user lists for filter dropdowns."""
    db = get_db()
    teams = db.execute(
        "SELECT tea_id AS id, tea_name_en AS name FROM t_team WHERE tea_active = 1 ORDER BY tea_name_en"
    ).fetchall()
    topics = db.execute(
        "SELECT top_id AS id, top_name AS name FROM t_topic WHERE top_active = 1 ORDER BY top_name"
    ).fetchall()
    users = db.execute(
        "SELECT usr_id AS id, usr_display_name AS name FROM t_user WHERE usr_active = 1 ORDER BY usr_display_name"
    ).fetchall()
    teams_data = [dict(r) for r in teams]
    return jsonify({
        "data": {
            "teams": teams_data,
            "departments": teams_data,
            "topics": [dict(r) for r in topics],
            "users": [dict(r) for r in users],
        }
    })
