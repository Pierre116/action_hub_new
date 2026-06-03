from flask import Blueprint, current_app, jsonify, redirect, request

from actionhub.auth.service import authenticate_user, force_change_password
from actionhub.auth import jwt_service
from actionhub.middleware.auth_middleware import get_request_user, login_required


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.get("/login")
def login_page():
    return redirect("/login")


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    # Accept "employee_id" (new) or "username" (legacy/admin)
    identifier = (payload.get("employee_id") or payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if not identifier or not password:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Employee ID and password are required"}}), 400

    try:
        user = authenticate_user(username=identifier, password=password)
    except ValueError as exc:
        code = str(exc)
        if code == "LOCKED":
            return jsonify({"error": {"code": "AUTH_LOCKED", "message": "Account locked. Try again in 30 minutes."}}), 423
        if code == "DISABLED":
            return jsonify({"error": {"code": "AUTH_DISABLED", "message": "Account is disabled."}}), 403
        return jsonify({"error": {"code": "AUTH_FAILED", "message": str(exc)}}), 401

    if not user:
        return jsonify({"error": {"code": "AUTH_FAILED", "message": "Invalid credentials"}}), 401

    # SEP-4: Generate JWT tokens (JWT-only auth)
    jwt_secret = current_app.config.get("JWT_SECRET_KEY", "jwt-dev-key-change-in-prod")
    access_expiry = current_app.config.get("JWT_ACCESS_EXPIRY", 900)
    refresh_expiry = current_app.config.get("JWT_REFRESH_EXPIRY", 604800)

    access_token = jwt_service.generate_access_token(user, jwt_secret, access_expiry)
    refresh_token = jwt_service.generate_refresh_token(user, jwt_secret, refresh_expiry)

    return jsonify({
        "data": {
            **user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    })


@auth_bp.get("/change-password")
def change_password_page():
    return redirect("/change-password")


@auth_bp.post("/change-password")
@login_required
def change_password():
    payload = request.get_json(silent=True) or {}
    new_password = payload.get("new_password") or ""
    confirm = payload.get("confirm_password") or ""

    if not new_password:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "new_password is required"}}), 400
    if new_password != confirm:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Passwords do not match"}}), 400

    user = get_request_user()
    try:
        force_change_password(user["id"], new_password)
    except ValueError as exc:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(exc)}}), 400
    return jsonify({"data": {"message": "Password updated successfully"}})


@auth_bp.post("/refresh")
def refresh():
    """Refresh access token using a valid refresh token."""
    payload = request.get_json(silent=True) or {}
    refresh_token = payload.get("refresh_token", "").strip()
    
    if not refresh_token:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "refresh_token is required"}}), 400

    jwt_secret = current_app.config.get("JWT_SECRET_KEY", "jwt-dev-key-change-in-prod")
    access_expiry = current_app.config.get("JWT_ACCESS_EXPIRY", 900)

    # Verify refresh token
    token_payload = jwt_service.verify_refresh_token(refresh_token, jwt_secret)
    if token_payload is None:
        return jsonify({"error": {"code": "AUTH_FAILED", "message": "Invalid or expired refresh token"}}), 401

    # Generate new access token
    user = {
        "id": int(token_payload["sub"]),
        "username": token_payload.get("username", ""),
        "role": token_payload.get("role", ""),
    }
    access_token = jwt_service.generate_access_token(user, jwt_secret, access_expiry)

    return jsonify({
        "data": {
            "access_token": access_token,
        }
    })


@auth_bp.delete("/logout")
def logout():
    """Logout: blacklist JWT token if provided."""
    # Check for JWT token to blacklist
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        jwt_service.blacklist_token(token)

    return jsonify({"data": {"message": "Logged out"}})


@auth_bp.get("/logout")
def logout_get():
    return redirect("/login")


@auth_bp.get("/me")
@login_required
def me():
    return jsonify({"data": getattr(request, "_current_user", None)})
