
from flask import Blueprint, jsonify, request

from actionhub.dashboard.service import (
    get_team_dashboard,
    get_personal_dashboard,
    get_all_teams_summary,
    get_all_teams_detail_summary,
    get_decision_dashboard,
    get_team_leader_dashboard,
)
from actionhub.dashboard.topic_service import get_topic_dashboard, get_all_topics_summary
from actionhub.middleware.auth_middleware import get_request_user, login_required
from actionhub.middleware.db import get_db



dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")




def _current_user() -> dict:
    return get_request_user()


@dashboard_bp.get("/personal")
@login_required
def personal_dashboard():
    user = _current_user()
    return jsonify({"data": get_personal_dashboard(int(user["id"]))})


@dashboard_bp.get("/team")
@login_required
def team_dashboard():
    user = _current_user()
    role = user.get("role", "Member")
    user_id = int(user["id"])

    team_id = request.args.get("team_id") or request.args.get("department_id")  # compat alias
    if not team_id:
        # Look up the user's primary team from t_user_team
        db = get_db()
        row = db.execute(
            """SELECT utm_team_id FROM t_user_team
               WHERE utm_user_id = ?
               ORDER BY utm_id ASC LIMIT 1""",
            (user_id,),
        ).fetchone()
        if row:
            team_id = row["utm_team_id"]
        if not team_id:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "team_id is required"}}), 400

    team_id = int(team_id)

    # Authorization: Admin can see any team; others must belong to the team
    if role != "Admin":
        db = get_db()
        member = db.execute(
            "SELECT utm_id FROM t_user_team WHERE utm_user_id = ? AND utm_team_id = ?",
            (user_id, team_id),
        ).fetchone()
        if not member:
            return jsonify({"error": {"code": "FORBIDDEN", "message": "you do not belong to this team"}}), 403

    try:
        return jsonify({"data": get_team_dashboard(team_id)})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


@dashboard_bp.get("/team-lead")
@login_required
def team_leader_dashboard():
    user = _current_user()
    role = user.get("role", "Member")
    user_id = int(user["id"])

    requested_team_id = request.args.get("team_id", type=int)
    db = get_db()
    led_rows = db.execute(
        "SELECT tea_id FROM t_team WHERE tea_active = 1 AND tea_leader_user_id = ? ORDER BY tea_id",
        (user_id,),
    ).fetchall()
    led_team_ids = [int(row["tea_id"]) for row in led_rows]

    if role != "Admin" and not led_team_ids:
        return jsonify({"error": {"code": "FORBIDDEN", "message": "insufficient permissions"}}), 403

    if role == "Admin":
        team_id = requested_team_id
        if not team_id and led_team_ids:
            team_id = led_team_ids[0]
        if not team_id:
            row = db.execute("SELECT tea_id FROM t_team WHERE tea_active = 1 ORDER BY tea_id LIMIT 1").fetchone()
            team_id = int(row["tea_id"]) if row else None
    else:
        if not led_team_ids:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "no led team found"}}), 400
        if requested_team_id and requested_team_id not in led_team_ids:
            return jsonify({"error": {"code": "FORBIDDEN", "message": "team_id is outside your scope"}}), 403
        team_id = requested_team_id or led_team_ids[0]

    if not team_id:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "team_id is required"}}), 400

    try:
        payload = get_team_leader_dashboard(int(team_id), user_id)
        return jsonify({"data": payload})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


@dashboard_bp.get("/teams/summary")
@login_required
def all_teams_summary():
    user = _current_user()
    if user.get("role") not in ("Admin", "TeamLead"):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "insufficient permissions"}}), 403
    return jsonify({"data": get_all_teams_summary()})


@dashboard_bp.get("/teams/detail-summary")
@login_required
def all_teams_detail_summary():
    return jsonify({"data": get_all_teams_detail_summary()})


@dashboard_bp.get("/topics/summary")
@login_required
def all_topics_summary():
    return jsonify({"data": get_all_topics_summary()})


@dashboard_bp.get("/topic")
@login_required
def topic_dashboard():
    topic_id = request.args.get("topic_id")
    topic_code = request.args.get("topic_code")
    if not topic_id and not topic_code:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "topic_id is required"}}), 400
    try:
        if not topic_id and topic_code:
            db = get_db()
            row = db.execute(
                "SELECT top_id FROM t_topic WHERE top_code = ? OR top_name = ? OR CAST(top_id AS TEXT) = ?",
                (topic_code, topic_code, topic_code),
            ).fetchone()
            if not row:
                return jsonify({"error": {"code": "NOT_FOUND", "message": "topic not found"}}), 404
            topic_id = row["top_id"]
        return jsonify({"data": get_topic_dashboard(int(topic_id))})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


@dashboard_bp.get("/decisions")
@login_required
def decisions_dashboard():
    user = _current_user()
    role = str(user.get("role") or "Member")
    user_id = int(user["id"])
    scope = (request.args.get("scope") or "personal").strip().lower()
    team_id = request.args.get("team_id", type=int)
    topic_id = request.args.get("topic_id", type=int)
    limit = request.args.get("limit", 8, type=int)

    if scope == "team":
        db = get_db()
        if role != "Admin":
            led_rows = db.execute(
                "SELECT tea_id FROM t_team WHERE tea_active = 1 AND tea_leader_user_id = ? ORDER BY tea_id",
                (user_id,),
            ).fetchall()
            led_team_ids = [int(row["tea_id"]) for row in led_rows]
            if not led_team_ids:
                return jsonify({"error": {"code": "FORBIDDEN", "message": "insufficient permissions"}}), 403
            if team_id and int(team_id) not in led_team_ids:
                return jsonify({"error": {"code": "FORBIDDEN", "message": "team_id is outside your scope"}}), 403
            team_id = int(team_id) if team_id else led_team_ids[0]
        elif not team_id:
            row = db.execute("SELECT tea_id FROM t_team WHERE tea_active = 1 ORDER BY tea_id LIMIT 1").fetchone()
            team_id = int(row["tea_id"]) if row else None

    try:
        payload = get_decision_dashboard(
            scope=scope,
            user_id=user_id,
            team_id=team_id,
            topic_id=topic_id,
            limit=limit,
        )
        return jsonify({"data": payload})
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400
