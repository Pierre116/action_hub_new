"""Notification API routes."""
from flask import Blueprint, jsonify, request

from actionhub.notifications import (
    delete_notifications,
    get_notifications,
    get_unread_count,
    mark_read,
)
from actionhub.middleware.auth_middleware import get_request_user, login_required


notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


def _user_id() -> int:
    return int(get_request_user().get("id", 0))


@notifications_bp.get("")
@login_required
def list_notifications():
    uid = _user_id()
    unread_only = request.args.get("unread", "false").lower() == "true"
    items = get_notifications(uid, unread_only=unread_only, limit=50)
    count = get_unread_count(uid)
    return jsonify({"data": {"items": items, "unread_count": count}})


@notifications_bp.post("/<int:ntf_id>/read")
@login_required
def read_one(ntf_id: int):
    mark_read(_user_id(), ntf_id=ntf_id)
    return jsonify({"data": {"ok": True}})


@notifications_bp.post("/read-all")
@login_required
def read_all():
    mark_read(_user_id())
    return jsonify({"data": {"ok": True}})


@notifications_bp.delete("/<int:ntf_id>")
@login_required
def delete_one(ntf_id: int):
    deleted = delete_notifications(_user_id(), ntf_id=ntf_id)
    if deleted <= 0:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "notification not found"}}), 404
    return jsonify({"data": {"ok": True, "deleted": deleted}})


@notifications_bp.post("/delete-all")
@login_required
def delete_all():
    deleted = delete_notifications(_user_id())
    return jsonify({"data": {"ok": True, "deleted": deleted}})
