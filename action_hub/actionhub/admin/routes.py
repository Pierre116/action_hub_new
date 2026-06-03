from flask import Blueprint, jsonify, redirect, request

from actionhub.admin.actions_table_service import inline_update, list_actions_paged
from actionhub.middleware.db import get_db
from actionhub.admin.import_service import (
    execute_import,
    list_import_history,
    preview_import,
    rollback_import,
)
from actionhub.admin.topic_assignment_service import (
    assign_topic_leader,
    get_topic_leaders,
    remove_topic_leader,
)
from actionhub.admin.topic_service import create_topic, delete_topic, list_topics, update_topic
from actionhub.admin.category_service import create_category, list_categories, update_category
from actionhub.admin.user_service import (
    add_user_team,
    create_team,
    create_user_admin,
    get_user_teams,
    list_team_members,
    list_teams,
    list_users,
    remove_user_team,
    reset_password_admin,
    update_team,
    update_user_admin,
)
from actionhub.middleware.auth_middleware import admin_required, get_request_user, login_required


admin_bp = Blueprint("admin", __name__)


def _actor_id() -> int:
    user = get_request_user()
    return int(user.get("id", 0))


@admin_bp.get("/api/users")
@login_required
def users_list_light():
    """Light user list (id + display_name + team memberships) for any logged-in user (action form dropdowns)."""
    db = get_db()
    rows = db.execute(
        "SELECT usr_id, usr_display_name, usr_role, usr_team_id FROM t_user WHERE usr_active = 1 ORDER BY usr_display_name"
    ).fetchall()
    users = [dict(r) for r in rows]

    # Attach team IDs from t_user_team for multi-team filtering
    team_rows = db.execute(
        "SELECT utm_user_id, utm_team_id FROM t_user_team"
    ).fetchall()
    from collections import defaultdict
    teams_by_user: dict[int, list[int]] = defaultdict(list)
    for tr in team_rows:
        teams_by_user[tr["utm_user_id"]].append(tr["utm_team_id"])
    for user in users:
        user["team_ids"] = teams_by_user.get(user["usr_id"], [])

    return jsonify({"data": users})


# Public /api/departments routes are removed — use /api/teams instead.


@admin_bp.get("/api/admin/users")
@admin_required
def admin_users_list():
    return jsonify({"data": list_users()})


@admin_bp.post("/api/admin/users")
@admin_required
def admin_users_create():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"data": create_user_admin(payload)}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@admin_bp.patch("/api/admin/users/<int:user_id>")
@admin_required
def admin_users_update(user_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"data": update_user_admin(user_id, payload)})
    except ValueError as error:
        code = "NOT_FOUND" if str(error) == "user not found" else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@admin_bp.post("/api/admin/users/<int:user_id>/reset-password")
@admin_required
def admin_reset_password(user_id: int):
    payload = request.get_json(silent=True) or {}
    password = str(payload.get("password", ""))
    try:
        reset_password_admin(user_id, password)
        return jsonify({"data": {"reset": True}})
    except ValueError as error:
        code = "NOT_FOUND" if str(error) == "user not found" else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


# ── User team membership ─────────────────────────────────────────────────────

# Public /api/teams and /api/teams/<id>/members are served by taxonomy_bp.
# Admin -specific endpoints live under /api/admin/teams/*.


@admin_bp.get("/api/admin/teams")
@admin_required
def admin_teams_list():
    include_counts = request.args.get("counts", "false").lower() == "true"
    # Add can_delete property for each team
    teams = list_teams(include_counts=include_counts)
    db = get_db()
    for team in teams:
        tid = team["tea_id"]
        ref_count = db.execute("SELECT COUNT(1) FROM t_action WHERE act_team_id = ?", (tid,)).fetchone()[0]
        ref_count += db.execute("SELECT COUNT(1) FROM t_user WHERE usr_team_id = ?", (tid,)).fetchone()[0]
        ref_count += db.execute("SELECT COUNT(1) FROM t_user_team WHERE utm_team_id = ?", (tid,)).fetchone()[0]
        team["can_delete"] = ref_count == 0
    return jsonify({"data": teams})


@admin_bp.post("/api/admin/teams")
@admin_required
def admin_teams_create():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"data": create_team(payload)}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@admin_bp.delete("/api/admin/teams/<int:team_id>")
@admin_required
def admin_teams_delete(team_id: int):
    db = get_db()
    # Check for references in t_action, t_user, t_user_team
    ref_count = db.execute("SELECT COUNT(1) FROM t_action WHERE act_team_id = ?", (team_id,)).fetchone()[0]
    ref_count += db.execute("SELECT COUNT(1) FROM t_user WHERE usr_team_id = ?", (team_id,)).fetchone()[0]
    ref_count += db.execute("SELECT COUNT(1) FROM t_user_team WHERE utm_team_id = ?", (team_id,)).fetchone()[0]
    if ref_count > 0:
        return jsonify({"error": {"code": "CONFLICT", "message": "Team is referenced and cannot be deleted."}}), 409
    db.execute("DELETE FROM t_team WHERE tea_id = ?", (team_id,))
    db.commit()
    return jsonify({"data": {"deleted": True}})


@admin_bp.patch("/api/admin/teams/<int:team_id>")
@admin_required
def admin_teams_update(team_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"data": update_team(team_id, payload)})
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@admin_bp.get("/api/admin/teams/<int:team_id>/members")
@admin_required
def admin_team_members_list(team_id: int):
    return jsonify({"data": list_team_members(team_id)})


@admin_bp.post("/api/admin/teams/<int:team_id>/members")
@admin_required
def admin_team_members_add(team_id: int):
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    if not user_id:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "user_id is required"}}), 400
    try:
        add_user_team(int(user_id), team_id)
        return jsonify({"data": list_team_members(team_id)})
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@admin_bp.delete("/api/admin/teams/<int:team_id>/members/<int:user_id>")
@admin_required
def admin_team_members_remove(team_id: int, user_id: int):
    try:
        remove_user_team(user_id, team_id)
        return jsonify({"data": list_team_members(team_id)})
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@admin_bp.get("/api/admin/users/<int:user_id>/teams")
@admin_required
def admin_user_teams_list(user_id: int):
    return jsonify({"data": get_user_teams(user_id)})


@admin_bp.post("/api/admin/users/<int:user_id>/teams")
@admin_required
def admin_user_teams_add(user_id: int):
    payload = request.get_json(silent=True) or {}
    team_id = payload.get("team_id")
    if not team_id:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "team_id is required"}}), 400
    try:
        add_user_team(user_id, int(team_id))
        return jsonify({"data": get_user_teams(user_id)})
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


# --- User Deletion Endpoint ---
@admin_bp.delete("/api/admin/users/<int:user_id>")
@admin_required
def admin_users_delete(user_id: int):
    from actionhub.admin.user_service import delete_user_admin
    try:
        delete_user_admin(user_id)
        return jsonify({"data": {"deleted": True}})
    except ValueError as error:
        code = "CONFLICT" if "linked" in str(error) else "NOT_FOUND"
        status = 409 if code == "CONFLICT" else 404
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@admin_bp.delete("/api/admin/users/<int:user_id>/teams/<int:team_id>")
@admin_required
def admin_user_teams_remove(user_id: int, team_id: int):
    try:
        remove_user_team(user_id, team_id)
        return jsonify({"data": get_user_teams(user_id)})
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@admin_bp.post("/api/import/preview")
@admin_required
def admin_import_preview():
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "file is required"}}), 400
    try:
        data = preview_import(uploaded.read(), uploaded.filename or "import.xlsx")
        return jsonify({"data": data})
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@admin_bp.post("/api/import/execute")
@admin_required
def admin_import_execute():
    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token", "")).strip()
    owner_map = payload.get("owner_map") or {}
    team_map = payload.get("team_map") or payload.get("department_map") or {}
    skip_duplicates = bool(payload.get("skip_duplicates", True))
    if not token:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "token is required"}}), 400
    try:
        result = execute_import(token, owner_map, team_map, _actor_id(), skip_duplicates=skip_duplicates)
        return jsonify({"data": result})
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@admin_bp.get("/api/import/history")
@admin_required
def admin_import_history():
    return jsonify({"data": list_import_history()})


@admin_bp.delete("/api/import/<int:import_log_id>")
@admin_required
def admin_import_rollback(import_log_id: int):
    try:
        result = rollback_import(import_log_id)
        return jsonify({"data": result})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


# ── Topic admin ───────────────────────────────────────────────────────────────

@admin_bp.get("/api/admin/topics")
@login_required
def admin_topics_list():
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"
    return jsonify({"data": list_topics(include_inactive=include_inactive)})


@admin_bp.get("/api/admin/topics/<int:topic_id>/actions")
@login_required
def admin_topic_actions(topic_id: int):
    db = get_db()
    rows = db.execute(
        """
        SELECT a.act_id, a.act_ref, a.act_title, a.act_status, a.act_priority,
               a.act_deadline,
               tm.tea_name_en AS team_name
        FROM t_action a
        LEFT JOIN t_team tm ON tm.tea_id = a.act_team_id
        WHERE (a.act_topic_id = ? OR a.act_secondary_topic_id = ?)
        ORDER BY a.act_deadline ASC NULLS LAST, a.act_created_at DESC
        """,
        (topic_id, topic_id),
    ).fetchall()
    return jsonify({"data": [dict(r) for r in rows]})


@admin_bp.post("/api/admin/topics")
@admin_required
def admin_topics_create():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"data": create_topic(payload, _actor_id())}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@admin_bp.patch("/api/admin/topics/<int:topic_id>")
@admin_required
def admin_topics_update(topic_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"data": update_topic(topic_id, payload, _actor_id())})
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@admin_bp.delete("/api/admin/topics/<int:topic_id>")
@admin_required
def admin_topics_delete(topic_id: int):
    try:
        result = delete_topic(topic_id)
        return jsonify({"data": result})
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@admin_bp.delete("/api/admin/topics/<string:topic_code>")
@admin_required
def admin_topics_delete_by_code(topic_code: str):
    try:
        result = delete_topic(topic_code)
        return jsonify({"data": result})
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


# ── Topic leaders ─────────────────────────────────────────────────────────────

@admin_bp.get("/api/admin/topics/<int:topic_id>/leaders")
@login_required
def topic_leaders_list(topic_id: int):
    return jsonify({"data": get_topic_leaders(topic_id)})


@admin_bp.post("/api/admin/topics/<int:topic_id>/leaders")
@admin_required
def topic_leaders_add(topic_id: int):
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    if not user_id:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "user_id is required"}}), 400
    try:
        result = assign_topic_leader(topic_id, int(user_id), _actor_id())
        return jsonify({"data": result}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@admin_bp.delete("/api/admin/topics/<int:topic_id>/leaders/<int:user_id>")
@admin_required
def topic_leaders_remove(topic_id: int, user_id: int):
    remove_topic_leader(topic_id, user_id)
    return jsonify({"data": {"ok": True}})


# ── Admin inline actions table ────────────────────────────────────────────────

@admin_bp.get("/api/admin/actions")
@admin_required
def admin_actions_list():
    filters = {
        "status": request.args.get("status"),
        "team_id": request.args.get("team_id") or request.args.get("department_id"),
        "priority": request.args.get("priority"),
        "topic_id": request.args.get("topic_id"),
        "search": request.args.get("search"),
    }
    page = int(request.args.get("page", 1))
    return jsonify({"data": list_actions_paged(filters, page=page)})


@admin_bp.patch("/api/admin/actions/<int:act_id>")
@admin_required
def admin_actions_inline_update(act_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"data": inline_update(act_id, payload, _actor_id())})
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


# ── Category (Action Type) admin ─────────────────────────────────────────────

@admin_bp.get("/admin/categories")
@admin_required
def admin_categories_page():
    return redirect("/")


@admin_bp.get("/api/admin/categories")
@login_required
def admin_categories_list():
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"
    return jsonify({"data": list_categories(include_inactive=include_inactive)})


@admin_bp.post("/api/admin/categories")
@admin_required
def admin_categories_create():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"data": create_category(payload, _actor_id())}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@admin_bp.patch("/api/admin/categories/<int:category_id>")
@admin_required
def admin_categories_update(category_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"data": update_category(category_id, payload, _actor_id())})
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status
