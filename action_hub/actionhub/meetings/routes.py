"""Meeting instance API routes."""
import sqlite3
from urllib.parse import quote

from flask import Blueprint, Response, jsonify, request

from actionhub.meetings.memo_service import delete_memo, get_memo_blob, get_memos, upload_memo
from actionhub.meetings.memo_text_service import (
    create_text_memo,
    delete_text_memo,
    list_text_memos,
    move_memo,
    update_text_memo,
)
from actionhub.meetings.service import (
    _can_view_series,
    add_meeting_participant,
    create_meeting,
    create_occurrence_from_series,
    create_parent_meeting,
    get_meeting,
    get_meeting_actions,
    get_meeting_owners,
    get_meeting_participants,
    get_parent_meeting,
    get_occurrence_comments,
    get_series_actions,
    get_series_decisions,
    get_series_participants,
    is_meeting_owner,
    list_instances_of_series,
    list_meetings,
    list_parent_meetings,
    remove_meeting_participant,
    add_series_participant,
    remove_series_participant,
    set_meeting_owners,
    set_meeting_participants,
    set_series_participants,
    update_parent_meeting,
    update_meeting,
)
from actionhub.meetings.pdf_service import generate_minutes_pdf
from actionhub.actions.feedback_service import get_meeting_feedback_summary
from actionhub.middleware.auth_middleware import admin_required, get_request_user, login_required


meetings_bp = Blueprint("meetings", __name__, url_prefix="/api/meetings")


def _actor_id() -> int:
    return int(get_request_user().get("id", 0))


def _is_admin() -> bool:
    return get_request_user().get("role") == "Admin"


def _is_admin_or_series_creator(mtg_id: int) -> bool:
    if _is_admin():
        return True
    try:
        series = get_parent_meeting(mtg_id)
    except ValueError:
        return False
    return int(series.get("mtg_created_by") or 0) == _actor_id()


def _is_admin_or_owner(min_id: int) -> bool:
    """Return True if the current user is Admin or a meeting owner."""
    if _is_admin():
        return True
    return is_meeting_owner(min_id, _actor_id())


def _is_admin_or_creator(min_id: int) -> bool:
    if _is_admin():
        return True
    try:
        meeting = get_meeting(min_id)
    except ValueError:
        return False
    return int(meeting.get("min_created_by") or 0) == _actor_id()


def _can_view_meeting(min_id: int) -> bool:
    if _is_admin():
        return True
    try:
        get_meeting(min_id)
        return True
    except ValueError:
        return False


def _can_view_meeting_content(min_id: int) -> bool:
    """Meeting content is accessible to: admin, series creator, series participants,
    occurrence creator, occurrence participants, or meeting owners."""
    if _is_admin():
        return True
    from actionhub.middleware.db import get_db
    from actionhub.meetings.service import _ensure_series_participant_table

    user_id = _actor_id()
    if user_id <= 0:
        return False
    if is_meeting_owner(min_id, user_id):
        return True
    db = get_db()
    row = db.execute(
        "SELECT min_id, min_meeting_id, min_created_by FROM t_meeting_instance WHERE min_id = ?",
        (min_id,),
    ).fetchone()
    if not row:
        return False
    # Occurrence creator can always view their own occurrence
    if int(row["min_created_by"] or 0) == user_id:
        return True
    # Occurrence-level participants
    if any(int(p.get("mpa_user_id") or 0) == user_id for p in get_meeting_participants(min_id)):
        return True
    # Series-level access: series creator or series default participant
    parent_id = row["min_meeting_id"]
    if parent_id:
        parent = db.execute(
            "SELECT mtg_created_by FROM t_meeting WHERE mtg_id = ?",
            (int(parent_id),),
        ).fetchone()
        if parent and int(parent["mtg_created_by"] or 0) == user_id:
            return True
        _ensure_series_participant_table(db)
        sp = db.execute(
            "SELECT 1 FROM t_meeting_series_participant WHERE msp_meeting_id = ? AND msp_user_id = ? LIMIT 1",
            (int(parent_id), user_id),
        ).fetchone()
        if sp:
            return True
    return False


def _meeting_exists(min_id: int) -> bool:
    from actionhub.middleware.db import get_db

    row = get_db().execute(
        "SELECT min_id FROM t_meeting_instance WHERE min_id = ?",
        (min_id,),
    ).fetchone()
    return row is not None


@meetings_bp.get("")
@login_required
def meetings_list():
    topic_value = request.args.get("topic_id") or request.args.get("category_id") or request.args.get("topic_code")
    return jsonify({"data": list_meetings(category_id=topic_value)})


@meetings_bp.get("/<int:min_id>")
@login_required
def meeting_detail(min_id: int):
    if not _can_view_meeting_content(min_id):
        if _meeting_exists(min_id):
            return jsonify({"error": {"code": "FORBIDDEN", "message": "meeting access denied"}}), 403
        return jsonify({"error": {"code": "NOT_FOUND", "message": "meeting not found"}}), 404
    try:
        meeting = get_meeting(min_id)
        meeting["owners"] = get_meeting_owners(min_id)
        meeting["is_owner"] = _is_admin_or_owner(min_id)
        meeting["is_creator"] = (meeting.get("min_created_by") == _actor_id())
        return jsonify({"data": meeting})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


@meetings_bp.post("")
@admin_required
def meeting_create():
    payload = request.get_json(silent=True) or {}
    try:
        result = create_meeting(payload, _actor_id())
        return jsonify({"data": result}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@meetings_bp.patch("/<int:min_id>")
@login_required
def meeting_update(min_id: int):
    if not _is_admin_or_creator(min_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admins can edit meetings"}}), 403
    payload = request.get_json(silent=True) or {}
    try:
        result = update_meeting(min_id, payload, _actor_id())
        return jsonify({"data": result})
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@meetings_bp.get("/<int:min_id>/actions")
@login_required
def meeting_actions(min_id: int):
    if not _can_view_meeting_content(min_id):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "meeting not found"}}), 404
    try:
        return jsonify({"data": get_meeting_actions(min_id)})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404

# ── Meeting Owners ─────────────────────────────────────────────────────────────

@meetings_bp.get("/<int:min_id>/owners")
@login_required
def owners_list(min_id: int):
    if not _can_view_meeting_content(min_id):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "meeting not found"}}), 404
    return jsonify({"data": get_meeting_owners(min_id)})


@meetings_bp.put("/<int:min_id>/owners")
@login_required
def owners_set(min_id: int):
    if not _is_admin_or_owner(min_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only meeting owners or admins can manage owners"}}), 403
    payload = request.get_json(silent=True) or {}
    user_ids = payload.get("user_ids", [])
    try:
        user_ids = [int(uid) for uid in user_ids]
        result = set_meeting_owners(min_id, user_ids, _actor_id())
        return jsonify({"data": result})
    except (TypeError, ValueError) as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


# ── Memos (blob upload/download) ──────────────────────────────────────────────

@meetings_bp.get("/<int:min_id>/memos")
@login_required
def memos_list(min_id: int):
    if not _can_view_meeting_content(min_id):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "meeting not found"}}), 404
    return jsonify({"data": get_memos(min_id)})


@meetings_bp.post("/<int:min_id>/memos")
@login_required
def memo_upload(min_id: int):
    if not _is_admin_or_creator(min_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admins can manage memos"}}), 403
    f = request.files.get("file")
    if not f:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "file is required"}}), 400
    try:
        result = upload_memo(min_id, f.filename or "upload", f.read(), _actor_id())
        return jsonify({"data": result}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@meetings_bp.get("/memos/<int:msm_id>/download")
@login_required
def memo_download(msm_id: int):
    blob = get_memo_blob(msm_id)
    if not blob:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "memo not found"}}), 404
    if not _can_view_meeting_content(int(blob["msm_instance_id"])):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "meeting not found"}}), 404
    return Response(
        blob["msm_file_data"],
        mimetype=blob["msm_file_mime"],
        headers={"Content-Disposition": f'attachment; filename="{blob["msm_filename"]}"'},
    )


@meetings_bp.delete("/memos/<int:msm_id>")
@login_required
def memo_delete(msm_id: int):
    from actionhub.middleware.db import get_db
    db = get_db()
    row = db.execute("SELECT msm_instance_id FROM t_meeting_summary WHERE msm_id = ?", (msm_id,)).fetchone()
    if not row:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "memo not found"}}), 404
    if not _is_admin_or_creator(int(row["msm_instance_id"])):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admins can manage memos"}}), 403
    delete_memo(msm_id)
    return jsonify({"data": {"ok": True}})


# ── Text memos (paste-from-Word, ordered) ─────────────────────────────────────

@meetings_bp.get("/<int:min_id>/text-memos")
@login_required
def text_memos_list(min_id: int):
    if not _can_view_meeting_content(min_id):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "meeting not found"}}), 404
    return jsonify({"data": list_text_memos(min_id)})


@meetings_bp.post("/<int:min_id>/text-memos")
@login_required
def text_memo_create(min_id: int):
    if not _is_admin_or_creator(min_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admins can manage memos"}}), 403
    payload = request.get_json(silent=True) or {}
    try:
        result = create_text_memo(
            min_id,
            payload.get("title", ""),
            payload.get("body", ""),
            _actor_id(),
            date=payload.get("date") or None,
        )
        return jsonify({"data": result}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@meetings_bp.patch("/text-memos/<int:mmm_id>")
@login_required
def text_memo_update(mmm_id: int):
    from actionhub.middleware.db import get_db
    db = get_db()
    row = db.execute("SELECT mmm_instance_id FROM t_meeting_memo WHERE mmm_id = ?", (mmm_id,)).fetchone()
    if not row:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "memo not found"}}), 404
    if not _is_admin_or_creator(int(row["mmm_instance_id"])):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admins can manage memos"}}), 403
    payload = request.get_json(silent=True) or {}
    try:
        result = update_text_memo(mmm_id, payload)
        return jsonify({"data": result})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


@meetings_bp.post("/text-memos/<int:mmm_id>/move")
@login_required
def text_memo_move(mmm_id: int):
    from actionhub.middleware.db import get_db
    db = get_db()
    row = db.execute("SELECT mmm_instance_id FROM t_meeting_memo WHERE mmm_id = ?", (mmm_id,)).fetchone()
    if not row:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "memo not found"}}), 404
    if not _is_admin_or_creator(int(row["mmm_instance_id"])):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admins can manage memos"}}), 403
    payload = request.get_json(silent=True) or {}
    direction = payload.get("direction", "up")
    try:
        result = move_memo(mmm_id, direction)
        return jsonify({"data": result})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


@meetings_bp.delete("/text-memos/<int:mmm_id>")
@login_required
def text_memo_delete(mmm_id: int):
    from actionhub.middleware.db import get_db
    db = get_db()
    row = db.execute("SELECT mmm_instance_id FROM t_meeting_memo WHERE mmm_id = ?", (mmm_id,)).fetchone()
    if not row:
        return jsonify({"data": {"ok": True}})
    if not _is_admin_or_creator(int(row["mmm_instance_id"])):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admins can manage memos"}}), 403
    try:
        delete_text_memo(mmm_id)
        return jsonify({"data": {"ok": True}})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


@meetings_bp.post("/<int:min_id>/text-memos/<int:mmm_id>/notify")
@login_required
def text_memo_notify(min_id: int, mmm_id: int):
    """Create in-app notifications for one memo to all meeting participants."""
    if not _is_admin_or_creator(min_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admins"}}), 403

    from actionhub.meetings.memo_text_service import list_text_memos
    from actionhub.notifications import create_notification

    try:
        meeting = get_meeting(min_id)
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404

    participants = get_meeting_participants(min_id)
    if not participants:
        return jsonify({"data": {"notified": 0, "message": "No participants to notify"}})

    memos = list_text_memos(min_id)
    memo = next((m for m in memos if int(m.get("mmm_id", 0)) == mmm_id), None)
    if not memo:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "memo not found"}}), 404

    mtg_title = meeting.get("min_title", "Meeting")
    memo_title = (memo.get("mmm_title") or "(untitled memo)").strip()
    actor_name = get_request_user().get("display_name", "Someone")
    body = f"Shared by {actor_name}\nMemo: {memo_title}"

    notified = 0
    for p in participants:
        uid = p["mpa_user_id"]
        create_notification(
            user_id=uid,
            event_type=f"meeting_memo:{min_id}",
            title=f"Memo update: {mtg_title}",
            body=body,
            action_id=mmm_id,
        )
        notified += 1

    return jsonify({"data": {"notified": notified, "memo_id": mmm_id}})


# ── Meeting Participants ─────────────────────────────────────────────────────

@meetings_bp.get("/<int:min_id>/participants")
@login_required
def participants_list(min_id: int):
    if not _can_view_meeting_content(min_id):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "meeting not found"}}), 404
    return jsonify({"data": get_meeting_participants(min_id)})


@meetings_bp.put("/<int:min_id>/participants")
@login_required
def participants_set(min_id: int):
    if not _is_admin_or_creator(min_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admins"}}), 403
    payload = request.get_json(silent=True) or {}
    user_ids = [int(uid) for uid in payload.get("user_ids", [])]
    try:
        result = set_meeting_participants(min_id, user_ids, _actor_id())
        return jsonify({"data": result})
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@meetings_bp.post("/<int:min_id>/participants")
@login_required
def participant_add(min_id: int):
    if not _is_admin_or_creator(min_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admins"}}), 403
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    if not user_id:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "user_id required"}}), 400
    try:
        result = add_meeting_participant(min_id, int(user_id), _actor_id())
        return jsonify({"data": result}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@meetings_bp.delete("/<int:min_id>/participants/<int:user_id>")
@login_required
def participant_remove(min_id: int, user_id: int):
    if not _is_admin_or_creator(min_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admins"}}), 403
    try:
        result = remove_meeting_participant(min_id, user_id)
        return jsonify({"data": result})
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@meetings_bp.post("/<int:min_id>/notify-memos")
@login_required
def notify_memos(min_id: int):
    """Create in-app notifications for all participants about meeting memos."""
    if not _is_admin_or_creator(min_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the meeting creator or admins"}}), 403
    from actionhub.meetings.memo_text_service import list_text_memos
    from actionhub.notifications import create_notification

    try:
        meeting = get_meeting(min_id)
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404

    participants = get_meeting_participants(min_id)
    if not participants:
        return jsonify({"data": {"notified": 0, "message": "No participants to notify"}})

    memos = list_text_memos(min_id)
    if not memos:
        return jsonify({"data": {"notified": 0, "message": "No memos to notify"}})

    mtg_title = meeting.get("min_title", "Meeting")
    actor_name = get_request_user().get("display_name", "Someone")

    body_prefix = f"Shared by {actor_name}"
    notified = 0
    for p in participants:
        uid = p["mpa_user_id"]
        for memo in memos:
            memo_title = (memo.get("mmm_title") or "(untitled memo)").strip()
            body = f"{body_prefix}\nMemo: {memo_title}"
            create_notification(
                user_id=uid,
                event_type=f"meeting_memo:{min_id}",
                title=f"Memo update: {mtg_title}",
                body=body,
                action_id=int(memo.get("mmm_id") or 0) or None,
            )
            notified += 1

    return jsonify({"data": {"notified": notified}})


# ── Meeting Series (parent t_meeting) endpoints ───────────────────────────────

@meetings_bp.get("/series")
@login_required
def series_list():
    topic_id = request.args.get("topic_id")
    visibility = request.args.get("visibility")
    return jsonify({"data": list_parent_meetings(int(topic_id) if topic_id else None, visibility=visibility)})


@meetings_bp.post("/series")
@login_required
def series_create():
    payload = request.get_json(silent=True) or {}
    try:
        result = create_parent_meeting(payload, _actor_id())
        return jsonify({"data": result}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@meetings_bp.get("/series/<int:mtg_id>")
@login_required
def series_detail(mtg_id: int):
    if not _can_view_series(mtg_id):
        # Return 403 with limited metadata so the frontend can display a lock screen
        from actionhub.middleware.db import get_db
        row = get_db().execute(
            "SELECT mtg.mtg_id, mtg.mtg_title, u.usr_display_name AS creator_name "
            "FROM t_meeting mtg LEFT JOIN t_user u ON u.usr_id = mtg.mtg_created_by "
            "WHERE mtg.mtg_id = ?",
            (mtg_id,),
        ).fetchone()
        if not row:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "meeting series not found"}}), 404
        return jsonify({"error": {"code": "FORBIDDEN", "message": "series access denied"}, "meta": {"mtg_id": row["mtg_id"], "mtg_title": row["mtg_title"], "creator_name": row["creator_name"]}}), 403
    try:
        return jsonify({"data": get_parent_meeting(mtg_id)})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


@meetings_bp.put("/series/<int:mtg_id>")
@login_required
def series_update(mtg_id: int):
    payload = request.get_json(silent=True) or {}
    if not _is_admin_or_series_creator(mtg_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the series creator or admins can edit series"}}), 403
    try:
        return jsonify({"data": update_parent_meeting(mtg_id, payload, _actor_id())})
    except ValueError as error:
        code = "NOT_FOUND" if "not found" in str(error) else "VALIDATION_ERROR"
        status = 404 if code == "NOT_FOUND" else 400
        return jsonify({"error": {"code": code, "message": str(error)}}), status


@meetings_bp.get("/series/<int:mtg_id>/instances")
@login_required
def series_instances(mtg_id: int):
    if not _can_view_series(mtg_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "series access denied"}}), 403
    try:
        return jsonify({"data": list_instances_of_series(mtg_id)})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


@meetings_bp.get("/series/<int:mtg_id>/participants")
@login_required
def series_participants_list(mtg_id: int):
    return jsonify({"data": get_series_participants(mtg_id)})


@meetings_bp.put("/series/<int:mtg_id>/participants")
@login_required
def series_participants_set(mtg_id: int):
    payload = request.get_json(silent=True) or {}
    participants = payload.get("participants") or []
    if not _is_admin_or_series_creator(mtg_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the series creator or admins can edit series participants"}}), 403
    try:
        return jsonify({"data": set_series_participants(mtg_id, participants, _actor_id())})
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@meetings_bp.post("/series/<int:mtg_id>/participants/replace")
@login_required
def series_participants_replace(mtg_id: int):
    payload = request.get_json(silent=True) or {}
    participants = payload.get("participants") or []
    if not _is_admin_or_series_creator(mtg_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the series creator or admins can edit series participants"}}), 403
    try:
        return jsonify({"data": set_series_participants(mtg_id, participants, _actor_id())})
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@meetings_bp.post("/series/<int:mtg_id>/participants")
@login_required
def series_participant_add(mtg_id: int):
    payload = request.get_json(silent=True) or {}
    if not _is_admin_or_series_creator(mtg_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the series creator or admins can edit series participants"}}), 403
    try:
        return jsonify({"data": add_series_participant(mtg_id, int(payload.get("user_id")), payload.get("kind", "Compulsory"), _actor_id())}), 201
    except (TypeError, ValueError) as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@meetings_bp.delete("/series/<int:mtg_id>/participants/<int:user_id>")
@login_required
def series_participant_remove(mtg_id: int, user_id: int):
    if not _is_admin_or_series_creator(mtg_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the series creator or admins can edit series participants"}}), 403
    try:
        return jsonify({"data": remove_series_participant(mtg_id, user_id)})
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@meetings_bp.post("/series/<int:mtg_id>/occurrences")
@login_required
def series_occurrence_create(mtg_id: int):
    payload = request.get_json(silent=True) or {}
    if not _is_admin_or_series_creator(mtg_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Only the series creator or admins can create occurrences"}}), 403
    try:
        return jsonify({"data": create_occurrence_from_series(mtg_id, payload, _actor_id())}), 201
    except ValueError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400
    except sqlite3.IntegrityError as error:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}), 400


@meetings_bp.get("/series/<int:mtg_id>/actions")
@login_required
def series_actions_list(mtg_id: int):
    if not _can_view_series(mtg_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "series access denied"}}), 403
    return jsonify({"data": get_series_actions(mtg_id)})


@meetings_bp.get("/series/<int:mtg_id>/decisions")
@login_required
def series_decisions_list(mtg_id: int):
    if not _can_view_series(mtg_id):
        return jsonify({"error": {"code": "FORBIDDEN", "message": "series access denied"}}), 403
    return jsonify({"data": get_series_decisions(mtg_id)})


@meetings_bp.get("/<int:min_id>/occurrence-comments")
@login_required
def occurrence_comments_list(min_id: int):
    if not _can_view_meeting_content(min_id):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "meeting not found"}}), 404
    try:
        return jsonify({"data": get_occurrence_comments(min_id)})
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404


@meetings_bp.get("/<int:min_id>/minutes/pdf")
@login_required
def minutes_pdf(min_id: int):
    try:
        if not _can_view_meeting_content(min_id):
            return jsonify({"error": {"code": "NOT_FOUND", "message": "meeting not found"}}), 404
        lang = request.args.get("lang", "en")
        pdf_bytes, filename = generate_minutes_pdf(min_id, lang=lang)
        # Use RFC 5987 encoding so non-ASCII characters (e.g. Chinese) are
        # transmitted safely without breaking HTTP header latin-1 encoding.
        encoded_name = quote(filename, safe="-_.")
        content_disposition = (
            f'attachment; filename="{encoded_name}"; filename*=UTF-8\'\'{encoded_name}'
        )
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": content_disposition},
        )
    except ValueError as error:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404
    except Exception:  # pylint: disable=broad-except
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": "Failed to generate PDF"}}), 500


# ── Meeting Feedback Summary ───────────────────────────────────────────────────

@meetings_bp.get("/<int:min_id>/feedback-summary")
@login_required
def meeting_feedback_summary(min_id: int):
    """Latest feedback per (action, participant) for all actions in this meeting."""
    if not _can_view_meeting_content(min_id):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "meeting not found"}}), 404
    rows = get_meeting_feedback_summary(min_id)
    return jsonify({"data": rows})


# ── Meeting Decisions (P8) ───────────────────────────────────────────────────

@meetings_bp.get("/<int:min_id>/decisions")
@login_required
def meeting_decisions(min_id: int):
    """Get all decisions for a specific meeting."""
    from actionhub.decisions.service import DecisionService
    if not _can_view_meeting_content(min_id):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "meeting not found"}}), 404
    decisions = DecisionService.list_decisions(meeting_id=min_id)
    return jsonify({"data": decisions})


# ── Series Summary ────────────────────────────────────────────────────────────

@meetings_bp.get("/series/summary")
@login_required
def meeting_series_summary():
    """Return KPI summary for all meeting series (for global dashboard)."""
    from actionhub.meetings.service import get_all_meeting_series_summary
    return jsonify({"data": get_all_meeting_series_summary()})
