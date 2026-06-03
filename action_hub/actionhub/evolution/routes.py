"""Evolution (What's New) blueprint."""
from __future__ import annotations

from flask import Blueprint, jsonify, redirect, request

from actionhub.middleware.auth_middleware import admin_required, get_request_user, login_required
from actionhub.evolution.service import (
    CATEGORIES, create_entry, delete_entry, get_entry,
    list_entries, update_entry,
)

evolution_bp = Blueprint("evolution", __name__)


# ── Pages ─────────────────────────────────────────────────────────────────────

@evolution_bp.get("/whatsnew")
@login_required
def page_whatsnew():
    return redirect("/")


@evolution_bp.get("/admin/whatsnew")
@admin_required
def page_admin_whatsnew():
    return redirect("/")


# ── User API ──────────────────────────────────────────────────────────────────

@evolution_bp.get("/api/evolution")
@login_required
def api_list_entries():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 100)
    result = list_entries(page=page, per_page=per_page, published_only=True)
    return jsonify({"data": result["items"], "pagination": result["pagination"]})


@evolution_bp.get("/api/evolution/<int:evo_id>")
@login_required
def api_get_entry(evo_id: int):
    try:
        entry = get_entry(evo_id)
    except ValueError:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Entry not found"}}), 404
    return jsonify({"data": entry})


# ── Admin API ─────────────────────────────────────────────────────────────────

@evolution_bp.get("/api/admin/evolution")
@admin_required
def api_admin_list_entries():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 100)
    result = list_entries(page=page, per_page=per_page, published_only=False)
    return jsonify({"data": result["items"], "pagination": result["pagination"]})


@evolution_bp.post("/api/admin/evolution")
@admin_required
def api_create_entry():
    payload = request.get_json(silent=True) or {}
    author_id = get_request_user()["id"]
    try:
        entry = create_entry(author_id, payload)
    except ValueError as exc:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(exc)}}), 422
    return jsonify({"data": entry}), 201


@evolution_bp.patch("/api/admin/evolution/<int:evo_id>")
@admin_required
def api_update_entry(evo_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        entry = update_entry(evo_id, payload)
    except ValueError as exc:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(exc)}}), 422
    return jsonify({"data": entry})


@evolution_bp.delete("/api/admin/evolution/<int:evo_id>")
@admin_required
def api_delete_entry(evo_id: int):
    try:
        delete_entry(evo_id)
    except ValueError as exc:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(exc)}}), 404
    return jsonify({"data": {"message": "Entry deleted"}})
