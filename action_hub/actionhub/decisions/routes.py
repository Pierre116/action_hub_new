"""
API routes for Meeting Decisions (P8).
Handles CRUD operations, lifecycle transitions, FTS5 search, and dashboard counts.
"""
import sqlite3

from flask import Blueprint, request, jsonify
from actionhub.decisions.service import DecisionService
from actionhub.middleware.auth_middleware import get_request_user, login_required
from actionhub.middleware.db import get_db

decisions_bp = Blueprint("decisions", __name__, url_prefix="/api/decisions")


def _database_error_response(error: sqlite3.DatabaseError):
    message = str(error)
    lowered = message.lower()
    if "database disk image is malformed" in lowered or "malformed" in lowered:
        return jsonify(
            {
                "error": {
                    "code": "DATABASE_CORRUPTION",
                    "message": "Database integrity issue detected. Please contact admin to run database recovery.",
                }
            }
        ), 503
    return jsonify({"error": {"code": "DATABASE_ERROR", "message": message}}), 500


def _is_admin() -> bool:
    return get_request_user().get("role") == "Admin"


def _extract_user_id(user: dict | None) -> int | None:
    payload = user or {}
    raw_user_id = payload.get("id")
    if raw_user_id in (None, ""):
        raw_user_id = payload.get("usr_id")
    if raw_user_id in (None, ""):
        raw_user_id = payload.get("user_id")
    if raw_user_id in (None, ""):
        return None
    try:
        return int(raw_user_id)
    except (TypeError, ValueError):
        return None


def _current_user_id() -> int:
    user_id = _extract_user_id(get_request_user())
    if user_id is None:
        raise RuntimeError("No authenticated user id in request context")
    return user_id


def _can_manage_decision(decision: dict) -> bool:
    user = get_request_user()
    if not user:
        return False
    if _is_admin():
        return True
    current_user_id = _extract_user_id(user) or 0
    if int(decision.get("mdc_created_by") or 0) == current_user_id:
        return True
    meeting_id = decision.get("mdc_meeting_id") or decision.get("mdc_instance_id")
    if not meeting_id:
        return False
    db = get_db()
    row = db.execute(
        "SELECT min_created_by FROM t_meeting_instance WHERE min_id = ?",
        (int(meeting_id),),
    ).fetchone()
    if row and int(row["min_created_by"] or 0) == current_user_id:
        return True
    owner_row = db.execute(
        "SELECT 1 FROM t_meeting_owner WHERE mow_instance_id = ? AND mow_user_id = ?",
        (int(meeting_id), current_user_id),
    ).fetchone()
    return bool(owner_row)


def _is_meeting_creator(meeting_id: int, user_id: int) -> bool:
    if _is_admin():
        return True
    db = get_db()
    row = db.execute(
        "SELECT min_created_by FROM t_meeting_instance WHERE min_id = ?",
        (meeting_id,),
    ).fetchone()
    return bool(row and int(row["min_created_by"] or 0) == int(user_id))


@decisions_bp.route("/", methods=["POST"])
@login_required
def create_decision():
    """Create a new decision."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "JSON body is required"}}), 400
    if not data.get("title"):
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "title is required"}}), 400

    actor = get_request_user()
    if not _is_admin():
        try:
            meeting_id = int(data.get("meeting_id"))
        except (TypeError, ValueError):
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "meeting_id is required"}}), 400
        if not meeting_id or not _is_meeting_creator(int(meeting_id), _current_user_id()):
            return jsonify({"error": {"code": "FORBIDDEN", "message": "Only meeting creators or admins can create decisions"}}), 403
    if not _is_admin() and data.get("expires_at"):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only admin can set decision expiration"}}), 403
    try:
        decision_id = DecisionService.create_decision(data, actor_id=_current_user_id())
        return jsonify({"data": {"id": decision_id}}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400
    except sqlite3.IntegrityError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400
    except sqlite3.OperationalError as error:
        return jsonify({"error": {"code": "SERVER_ERROR", "message": str(error)}}), 500
    except sqlite3.DatabaseError as error:
        return _database_error_response(error)


@decisions_bp.route("/", methods=["GET"])
@login_required
def list_decisions():
    """List decisions with optional filters."""
    search = request.args.get("search")
    meeting_id = request.args.get("meeting_id", type=int)
    series_id = request.args.get("series_id", type=int)
    status = request.args.get("status")
    action_id = request.args.get("action_id", type=int)
    category_id = request.args.get("category_id", type=int)
    owner_id = request.args.get("owner_id", type=int)
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 25, type=int), 1), 100)
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", type=int)
    if limit is None:
        limit = per_page
    if offset is None:
        offset = (page - 1) * per_page
    current_user = get_request_user()

    common_filters = {
        "search": search,
        "meeting_id": meeting_id,
        "series_id": series_id,
        "status": status,
        "action_id": action_id,
        "category_id": category_id,
        "owner_id": owner_id,
        "current_user_id": _extract_user_id(current_user),
    }

    decisions, total = DecisionService.list_decisions(
        **common_filters,
        limit=limit,
        offset=offset,
        include_total=True,
    )
    return jsonify(
        {
            "data": decisions,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
            },
        }
    )


@decisions_bp.route("/<int:decision_id>", methods=["GET"])
@login_required
def get_decision(decision_id):
    """Get a specific decision."""
    decision = DecisionService.get_decision(decision_id)
    if not decision:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Decision not found"}}), 404
    return jsonify({"data": decision})


@decisions_bp.route("/<int:decision_id>", methods=["PUT"])
@decisions_bp.route("/<int:decision_id>", methods=["PATCH"])
@login_required
def update_decision(decision_id):
    """Update an existing decision."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "JSON body is required"}}), 400
    decision = DecisionService.get_decision(decision_id)
    if not decision:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Decision not found"}}), 404
    if not _can_manage_decision(decision):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only meeting creators or admins can edit decisions"}}), 403
    if "status" in data and not _is_admin():
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only admin can change decision status"}}), 403
    if "expires_at" in data and not _is_admin():
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only admin can set decision expiration"}}), 403
    try:
        success = DecisionService.update_decision(decision_id, data, actor_id=_current_user_id())
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400
    except sqlite3.IntegrityError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400
    except sqlite3.OperationalError as error:
        return jsonify({"error": {"code": "SERVER_ERROR", "message": str(error)}}), 500
    except sqlite3.DatabaseError as error:
        return _database_error_response(error)
    if not success:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Update failed"}}), 400
    return jsonify({"data": {"success": True}})


@decisions_bp.route("/<int:decision_id>/revisions", methods=["GET"])
@login_required
def decision_revisions(decision_id):
    decision = DecisionService.get_decision(decision_id)
    if not decision:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Decision not found"}}), 404
    limit = request.args.get("limit", 20, type=int)
    return jsonify({"data": DecisionService.get_revisions(decision_id, limit=limit)})


@decisions_bp.route("/<int:decision_id>/status", methods=["PATCH", "POST"])
@login_required
def transition_decision_status(decision_id):
    """Transition decision status (lifecycle transition)."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "JSON body is required"}}), 400
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "status is required"}}), 400

    decision = DecisionService.get_decision(decision_id)
    if not decision:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Decision not found"}}), 404

    user_id = _current_user_id()

    if not _is_admin():
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only admin can change decision status"}}), 403

    try:
        result = DecisionService.transition_status(decision_id, new_status, user_id)
    except sqlite3.DatabaseError as error:
        return _database_error_response(error)
    if not result.get("success"):
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": result.get("error")}, "valid_transitions": result.get("valid_transitions")}), 400
    
    return jsonify({"data": result})


@decisions_bp.route("/<int:decision_id>", methods=["DELETE"])
@login_required
def delete_decision(decision_id):
    return jsonify({"error": {"code": "FORBIDDEN", "message": "Decision deletion is not allowed"}}), 403


@decisions_bp.route("/search", methods=["GET"])
@login_required
def search_decisions():
    """Search decisions using FTS5."""
    query = request.args.get("q", "")
    limit = request.args.get("limit", 50, type=int)
    if not query:
        return jsonify([])
    results = DecisionService.search_decisions(query, limit)
    return jsonify(results)


@decisions_bp.route("/counts", methods=["GET"])
@login_required
def count_decisions():
    """Get decision counts by status."""
    counts = DecisionService.count_by_status()
    return jsonify(counts)
