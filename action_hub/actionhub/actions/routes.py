import sqlite3

from flask import Blueprint, jsonify, request

from actionhub.actions.comment_service import (
    create_comment,
    delete_comment,
    edit_comment,
    get_comments,
)
from actionhub.actions.queries import list_actions
from actionhub.actions.service import (
    archive_action,
    assign_user,
    create_action,
    _can_edit_action,
    get_action,
    remove_assignment,
    transition_status,
    update_assignment_hours,
    update_action,
)
from actionhub.actions.assignment_service import (
    get_assignment_history,
)
from actionhub.actions.feedback_service import (
    list_action_feedback,
    submit_feedback,
)
from actionhub.middleware.auth_middleware import get_request_user, login_required
from actionhub.meetings.service import get_action_related_meetings


actions_bp = Blueprint("actions", __name__, url_prefix="/api/actions")


def _actor_id() -> int:
    user = get_request_user()
    return int(user.get("id", 0))


def _is_admin() -> bool:
    return get_request_user().get("role") == "Admin"


def _check_meeting_status_permission(action_id: int) -> str | None:
    """Return an error message if the user cannot change the status of this action.
    Returns None when the change is allowed."""
    if _is_admin():
        return None
    from actionhub.middleware.db import get_db
    db = get_db()
    row = db.execute(
        "SELECT act_created_by, act_owner_id, act_meeting_inst_id FROM t_action WHERE act_id = ?", (action_id,)
    ).fetchone()
    if not row:
        return "Action not found"
    # Check whether this action belongs to a meeting
    if not row["act_meeting_inst_id"]:
        if int(row["act_owner_id"] or 0) == _actor_id():
            return None
        return "Only the action Lead can change this action"
    meeting_row = db.execute(
        "SELECT min_created_by FROM t_meeting_instance WHERE min_id = ?",
        (row["act_meeting_inst_id"],),
    ).fetchone()
    if int(row["act_owner_id"] or 0) == _actor_id():
        return None
    if meeting_row and int(meeting_row["min_created_by"] or 0) == _actor_id():
        return None
    return "Only the action Lead or meeting creator can change meeting action progress"


def _is_meeting_creator(meeting_id: int) -> bool:
    if _is_admin():
        return True
    from actionhub.middleware.db import get_db
    db = get_db()
    row = db.execute(
        "SELECT min_created_by FROM t_meeting_instance WHERE min_id = ?",
        (meeting_id,),
    ).fetchone()
    if not row:
        return False
    return int(row["min_created_by"] or 0) == _actor_id()


@actions_bp.get("")
@login_required
def actions_list():
    user = get_request_user()
    data = list_actions(
        {
            "status": request.args.get("status"),
            "status_family": request.args.get("status_family"),
            "status_not": request.args.get("status_not"),
            "status_family_not": request.args.get("status_family_not"),
            "team_id": request.args.get("team_id") or request.args.get("department_id"),
            "meeting_id": request.args.get("meeting_id"),
            "series_id": request.args.get("series_id"),
            "topic_id": request.args.get("topic_id"),
            "topic_code": request.args.get("topic_code"),
            "category_id": request.args.get("category_id"),
            "priority": request.args.get("priority"),
            "search": request.args.get("search"),
            "sort_by": request.args.get("sort_by", "deadline"),
            "sort_order": request.args.get("sort_order", "asc"),
            "page": request.args.get("page", 1),
            "per_page": request.args.get("per_page", 20),
            "current_user_id": user.get("id"),
            "current_user_role": user.get("role"),
            "owner_id": request.args.get("owner_id"),
            "lead_id": request.args.get("lead_id"),
            "lead_only": request.args.get("lead_only", ""),
        }
    )
    return jsonify({"data": data})


@actions_bp.get("/<int:action_id>")
@login_required
def action_detail(action_id: int):
    try:
        data = get_action(action_id)
        act = data["action"]
        # Add permission flag: can the current user change the status?
        err = _check_meeting_status_permission(action_id)
        act["can_change_status"] = err is None
        # Separate edit permission (owner/creator/admin can edit fields)
        act["can_edit"] = _can_edit_action(action_id, _actor_id(), _actor_role())
        # Creator-only flag: user is creator but NOT owner/admin
        uid = _actor_id()
        is_owner = int(act.get("act_owner_id") or 0) == uid
        is_admin = _actor_role() == "Admin"
        is_creator = int(act.get("act_created_by") or 0) == uid
        act["is_creator_only"] = is_creator and not is_owner and not is_admin
        return jsonify({"data": data})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


@actions_bp.post("")
@login_required
def action_create():
    payload = request.get_json(silent=True) or {}
    meeting_id = payload.get("meeting_id")
    if meeting_id not in (None, ""):
        try:
            meeting_id = int(meeting_id)
        except (TypeError, ValueError):
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "meeting_id must be an integer"}}), 400
        if not _is_meeting_creator(meeting_id):
            return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admin can create meeting actions"}}), 403
    try:
        result = create_action(payload, _actor_id())
        action = result.get("action") or {}
        response_data = {
            "id": action.get("act_id"),
            "ref": action.get("act_ref"),
            **result,
        }
        return jsonify({"data": response_data}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@actions_bp.patch("/<int:action_id>")
@login_required
def action_update(action_id: int):
    payload = request.get_json(silent=True) or {}
    if not _can_edit_action(action_id, _actor_id(), _actor_role()):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the action Lead or meeting creator can edit this action"}}), 403
    # Creator-only users may only change: title, description, status, deadline
    uid = _actor_id()
    role = _actor_role()
    if role != "Admin":
        from actionhub.middleware.db import get_db as _gdb
        _row = _gdb().execute(
            "SELECT act_owner_id, act_created_by FROM t_action WHERE act_id = ?", (action_id,)
        ).fetchone()
        if _row and int(_row["act_created_by"] or 0) == uid and int(_row["act_owner_id"] or 0) != uid:
            allowed_keys = {"title", "description", "status", "deadline", "cancel_reason", "hold_reason"}
            payload = {k: v for k, v in payload.items() if k in allowed_keys}
    # Guard: if status change is requested, check meeting owner permission
    if "status" in payload:
        err = _check_meeting_status_permission(action_id)
        if err:
            return jsonify({"error": {"code": "FORBIDDEN", "message": err}}), 403
    try:
        result = update_action(action_id, payload, _actor_id())
        return jsonify({"data": result})
    except ValueError as error:
        code = "NOT_FOUND" if str(error) == "action not found" else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@actions_bp.post("/<int:action_id>/status")
@login_required
def action_transition_status(action_id: int):
    if not _can_edit_action(action_id, _actor_id(), _actor_role()):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the action Lead or meeting creator can edit this action"}}), 403
    # Guard: check meeting owner permission
    err = _check_meeting_status_permission(action_id)
    if err:
        return jsonify({"error": {"code": "FORBIDDEN", "message": err}}), 403
    payload = request.get_json(silent=True) or {}
    status_value = payload.get("status")
    try:
        result = transition_status(action_id, status_value, _actor_id(), payload)
        return jsonify({"data": result})
    except ValueError as error:
        code = "NOT_FOUND" if str(error) == "action not found" else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@actions_bp.post("/<int:action_id>/assign")
@login_required
def action_assign_user(action_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        user_id = int(payload.get("user_id"))
        role = str(payload.get("role", "Lead"))
        estimated_hours = payload.get("estimated_hours")
        if not _can_edit_action(action_id, _actor_id(), _actor_role()):
            return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the action Lead or meeting creator can edit this action"}}), 403
        # Check BEFORE assigning whether the user already has any role on this action
        # so we only send ONE notification per (user, action) regardless of multi-role
        from actionhub.middleware.db import get_db as _get_db
        _db = _get_db()
        _already_assigned = _db.execute(
            "SELECT 1 FROM t_assignment WHERE asg_action_id=? AND asg_user_id=? LIMIT 1",
            (action_id, user_id),
        ).fetchone()
        result = assign_user(action_id, user_id, role, _actor_id(), estimated_hours)
        # Send assignment notification only once (first role for this user on this action)
        if not _already_assigned and user_id != _actor_id():
            from actionhub.notifications import create_notification as _ntf
            _action_row = _db.execute(
                "SELECT act_title FROM t_action WHERE act_id=?", (action_id,)
            ).fetchone()
            _actor = get_request_user()
            _ntf(
                user_id=user_id,
                event_type="assigned",
                title=f"You were assigned to: {(_action_row['act_title'] if _action_row else '')}",
                body=f"Assigned by {_actor.get('display_name', 'Someone')}",
                action_id=action_id,
            )
        return jsonify({"data": result}), 201
    except (TypeError, ValueError) as error:
        code = "NOT_FOUND" if str(error) == "action not found" else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@actions_bp.delete("/<int:action_id>/assign/<int:assignment_id>")
@login_required
def action_remove_assignment(action_id: int, assignment_id: int):
    try:
        if not _can_edit_action(action_id, _actor_id(), _actor_role()):
            return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the action Lead or meeting creator can edit this action"}}), 403
        remove_assignment(action_id, assignment_id, _actor_id())
        return jsonify({"data": {"deleted": True}})
    except ValueError as error:
        code = "NOT_FOUND" if str(error) in {"action not found", "assignment not found"} else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@actions_bp.patch("/<int:action_id>/assignments/<int:asg_id>")
@login_required
def action_update_assignment_hours(action_id: int, asg_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        result = update_assignment_hours(
            action_id,
            asg_id,
            payload.get("estimated_hours"),
            _actor_id(),
            get_request_user().get("role", "Member"),
        )
        return jsonify({"data": result})
    except PermissionError as error:
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(error)}}), 403
    except ValueError as error:
        code = "NOT_FOUND" if str(error) in {"action not found", "assignment not found"} else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


# ── Comments ──────────────────────────────────────────────────────────────────

def _actor_role() -> str:
    return get_request_user().get("role", "Member")


@actions_bp.get("/<int:action_id>/comments")
@login_required
def comments_list(action_id: int):
    return jsonify({"data": get_comments(act_id=action_id)})


@actions_bp.post("/<int:action_id>/comments")
@login_required
def comment_create(action_id: int):
    actor_id = _actor_id()
    actor_role = _actor_role()
    # Permission: Admin, creator, lead/assignee, or meeting participant
    if actor_role != "Admin":
        from actionhub.middleware.db import get_db
        db = get_db()
        action_row = db.execute(
            "SELECT act_created_by, act_owner_id, act_meeting_inst_id FROM t_action WHERE act_id = ?",
            (action_id,),
        ).fetchone()
        if not action_row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "action not found"}}), 404
        is_creator = int(action_row["act_created_by"] or 0) == actor_id
        is_owner = int(action_row["act_owner_id"] or 0) == actor_id
        is_assigned = bool(db.execute(
            "SELECT 1 FROM t_assignment WHERE asg_action_id = ? AND asg_user_id = ?",
            (action_id, actor_id),
        ).fetchone())
        meeting_inst_id = action_row["act_meeting_inst_id"]
        is_participant = False
        if meeting_inst_id:
            is_participant = bool(db.execute(
                """SELECT 1 FROM t_meeting_participant
                   WHERE mpa_instance_id = ? AND mpa_user_id = ?""",
                (meeting_inst_id, actor_id),
            ).fetchone())
            if not is_participant:
                # Also check meeting series participants
                series_row = db.execute(
                    "SELECT min_meeting_id FROM t_meeting_instance WHERE min_id = ?",
                    (meeting_inst_id,),
                ).fetchone()
                if series_row and series_row["min_meeting_id"]:
                    is_participant = bool(db.execute(
                        """SELECT 1 FROM t_meeting_series_participant
                           WHERE msp_meeting_id = ? AND msp_user_id = ?""",
                        (series_row["min_meeting_id"], actor_id),
                    ).fetchone())
            if not is_participant:
                # Also check meeting creator
                creator_row = db.execute(
                    "SELECT min_created_by FROM t_meeting_instance WHERE min_id = ?",
                    (meeting_inst_id,),
                ).fetchone()
                if creator_row and int(creator_row["min_created_by"] or 0) == actor_id:
                    is_participant = True
        if not (is_creator or is_owner or is_assigned or is_participant):
            return jsonify({"error": {"code": "FORBIDDEN", "message": "You do not have permission to comment on this action"}}), 403

    payload = request.get_json(silent=True) or {}
    payload["action_id"] = action_id
    if "meeting_inst_id" not in payload:
        from actionhub.middleware.db import get_db
        db = get_db()
        row = db.execute("SELECT act_meeting_inst_id FROM t_action WHERE act_id = ?", (action_id,)).fetchone()
        if row and row["act_meeting_inst_id"]:
            payload["meeting_inst_id"] = row["act_meeting_inst_id"]
    try:
        result = create_comment(payload, _actor_id())
        return jsonify({"data": result}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@actions_bp.patch("/comments/<int:cmt_id>")
@login_required
def comment_edit(cmt_id: int):
    payload = request.get_json(silent=True) or {}
    body = str(payload.get("body", ""))
    try:
        result = edit_comment(cmt_id, body, _actor_id(), _actor_role())
        return jsonify({"data": result})
    except PermissionError as error:
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(error)}}), 403
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@actions_bp.delete("/comments/<int:cmt_id>")
@login_required
def comment_delete(cmt_id: int):
    try:
        delete_comment(cmt_id, _actor_id(), _actor_role())
        return jsonify({"data": {"deleted": True}})
    except PermissionError as error:
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(error)}}), 403
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


@actions_bp.get("/<int:action_id>/meetings")
@login_required
def action_meetings(action_id: int):
    """Return meetings linked to this action (directly or via shared topic)."""
    return jsonify({"data": get_action_related_meetings(action_id)})


@actions_bp.get("/<int:action_id>/assignment-history")
@login_required
def action_assignment_history(action_id: int):
    """Return assignment history for an action."""
    return jsonify({"data": get_assignment_history(action_id)})


@actions_bp.delete("/<int:action_id>")
@login_required
def action_archive(action_id: int):
    """Soft-delete (archive) an action — Admin only."""
    user = get_request_user()
    if user.get("role") != "Admin":
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Admin only"}}), 403
    try:
        archive_action(action_id, int(user["id"]))
        return jsonify({"data": {"archived": True}})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


# ── Action Feedback (pre-meeting participant updates) ─────────────────────────

@actions_bp.get("/<int:action_id>/feedback")
@login_required
def action_feedback_list(action_id: int):
    """All feedback history for one action (visible to all meeting participants)."""
    items = list_action_feedback(action_id)
    return jsonify({"data": items})


@actions_bp.post("/<int:action_id>/feedback")
@login_required
def action_feedback_submit(action_id: int):
    """Submit a new feedback entry for an action."""
    err = _check_meeting_status_permission(action_id)
    if err:
        return jsonify({"error": {"code": "FORBIDDEN", "message": err}}), 403
    payload = request.get_json(silent=True) or {}
    meeting_inst_id = payload.get("meeting_inst_id")
    completion_pct  = payload.get("completion_pct")
    status          = payload.get("status") or None
    comment         = (payload.get("comment") or "").strip() or None
    est_date        = (payload.get("est_date") or "").strip() or None
    blockers        = (payload.get("blockers") or "").strip() or None
    try:
        if completion_pct is not None:
            completion_pct = int(completion_pct)
        entry = submit_feedback(
            action_id=action_id,
            user_id=_actor_id(),
            meeting_inst_id=int(meeting_inst_id) if meeting_inst_id else None,
            completion_pct=completion_pct,
            status=status,
            comment=comment,
            est_date=est_date,
            blockers=blockers,
        )
        return jsonify({"data": entry}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400
    except sqlite3.IntegrityError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400