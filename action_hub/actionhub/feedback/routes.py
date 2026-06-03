"""Feedback blueprint — user feedback submission and admin management."""
from __future__ import annotations

from flask import Blueprint, jsonify, redirect, request, send_file
import io

from actionhub.middleware.auth_middleware import admin_required, get_request_user, login_required
from actionhub.feedback.service import (
    CATEGORIES, KNOWN_PAGES, PRIORITIES, STATUSES,
    create_feedback, export_feedback_xlsx, get_feedback,
    list_all_feedback, list_user_feedback, update_feedback_status,
)

feedback_bp = Blueprint("feedback", __name__)


# ── User-facing pages ─────────────────────────────────────────────────────────

@feedback_bp.get("/feedback")
@login_required
def page_feedback_list():
    return redirect("/")


@feedback_bp.get("/feedback/new")
@login_required
def page_feedback_form():
    return redirect("/")


# ── Admin pages ───────────────────────────────────────────────────────────────

@feedback_bp.get("/admin/feedback")
@admin_required
def page_admin_feedback():
    return redirect("/")


# ── User API ──────────────────────────────────────────────────────────────────

@feedback_bp.get("/api/feedback")
@login_required
def api_list_own_feedback():
    user_id = get_request_user()["id"]
    items = list_user_feedback(user_id)
    return jsonify({"data": items})


@feedback_bp.post("/api/feedback")
@login_required
def api_create_feedback():
    user_id = get_request_user()["id"]
    payload = request.form.to_dict()

    try:
        fbk_id = create_feedback(user_id, payload, None, None)
    except ValueError as exc:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(exc)}}), 422

    return jsonify({"data": {"id": fbk_id, "message": "Feedback submitted"}}), 201


@feedback_bp.get("/api/feedback/<int:feedback_id>")
@login_required
def api_get_feedback(feedback_id: int):
    user = get_request_user()
    # Admin can view any; regular user only their own
    owner_id = None if user["role"] == "Admin" else user["id"]
    try:
        entry = get_feedback(feedback_id, user_id=owner_id)
    except ValueError:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Feedback not found"}}), 404
    except PermissionError:
        return jsonify({"error": {"code": "FORBIDDEN", "message": "Not your feedback"}}), 403
    return jsonify({"data": entry})


# ── Admin API ─────────────────────────────────────────────────────────────────

@feedback_bp.get("/api/admin/feedback")
@admin_required
def api_admin_list_feedback():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 25)), 100)
    status = request.args.get("status") or None
    category = request.args.get("category") or None
    priority = request.args.get("priority") or None

    result = list_all_feedback(status=status, category=category, priority=priority,
                               page=page, per_page=per_page)
    return jsonify({"data": result["items"], "pagination": result["pagination"]})


@feedback_bp.patch("/api/admin/feedback/<int:feedback_id>")
@admin_required
def api_admin_update_feedback(feedback_id: int):
    admin_id = get_request_user()["id"]
    payload = request.get_json(silent=True) or {}
    try:
        entry = update_feedback_status(feedback_id, admin_id, payload)
    except ValueError as exc:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(exc)}}), 422
    return jsonify({"data": entry})


@feedback_bp.get("/api/admin/feedback/export")
@admin_required
def api_admin_export_feedback():
    try:
        xlsx_bytes = export_feedback_xlsx()
    except RuntimeError as exc:
        return jsonify({"error": {"code": "EXPORT_ERROR", "message": str(exc)}}), 500
    return send_file(
        io.BytesIO(xlsx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="feedback_export.xlsx",
    )
