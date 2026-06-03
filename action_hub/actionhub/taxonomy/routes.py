from flask import Blueprint, jsonify, request

from actionhub.middleware.auth_middleware import login_required
from actionhub.middleware.db import get_db


taxonomy_bp = Blueprint("taxonomy", __name__)


@taxonomy_bp.get("/api/teams")
@login_required
def teams():
    """Read-only team list with member counts for any logged-in user."""
    db = get_db()
    rows = db.execute(
        """
        SELECT t.tea_id, t.tea_code, t.tea_name_en, t.tea_name_cn,
               COUNT(DISTINCT utm.utm_user_id) AS member_count
        FROM t_team t
        LEFT JOIN t_user_team utm ON utm.utm_team_id = t.tea_id
        WHERE t.tea_active = 1
        GROUP BY t.tea_id
        ORDER BY t.tea_name_en
        """
    ).fetchall()
    return jsonify({"data": [dict(row) for row in rows]})


@taxonomy_bp.get("/api/teams/<int:team_id>/members")
@login_required
def team_members(team_id: int):
    """Read-only team members for any logged-in user."""
    db = get_db()
    rows = db.execute(
        """
        SELECT u.usr_id, u.usr_display_name, u.usr_role
        FROM t_user_team utm
        JOIN t_user u ON u.usr_id = utm.utm_user_id
        WHERE utm.utm_team_id = ? AND u.usr_active = 1
        ORDER BY u.usr_display_name
        """,
        (team_id,),
    ).fetchall()
    return jsonify({"data": [dict(row) for row in rows]})


@taxonomy_bp.get("/api/topics")
@login_required
def topics():
    db = get_db()
    rows = db.execute(
        "SELECT top_id, top_name FROM t_topic WHERE top_active = 1 ORDER BY top_name"
    ).fetchall()
    return jsonify({"data": [dict(row) for row in rows]})


@taxonomy_bp.get("/api/tags")
@login_required
def tags():
    db = get_db()
    rows = db.execute("SELECT tag_id, tag_name FROM t_tag ORDER BY tag_name").fetchall()
    return jsonify({"data": [dict(row) for row in rows]})
