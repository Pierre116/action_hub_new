from functools import wraps

from flask import current_app, jsonify, redirect, request

from actionhub.auth import jwt_service


def _is_api_request() -> bool:
    """True for /api/* routes."""
    return request.path.startswith("/api/")


def _get_user_from_jwt() -> dict | None:
    """Attempt to get user from JWT Bearer token.
    
    Returns:
        User dict if valid token, None otherwise
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]
    jwt_secret = current_app.config.get("JWT_SECRET_KEY", "jwt-dev-key-change-in-prod")
    
    payload = jwt_service.verify_access_token(token, jwt_secret)
    if payload is None:
        return None
    
    return {
        "id": int(payload["sub"]),
        "username": payload.get("username", ""),
        "role": payload.get("role", ""),
        "must_change_pwd": False,  # JWT auth doesn't enforce password change
    }


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        # SEP-4: JWT-only auth path
        user = _get_user_from_jwt()
        if user is None:
            if _is_api_request():
                return jsonify({"error": {"code": "AUTH_REQUIRED", "message": "Authentication required"}}), 401
            return redirect("/login")

        # Enforce first-login password change on HTML page routes
        if user.get("must_change_pwd") and not _is_api_request():
            # Allow the change-password route itself (avoid redirect loop)
            if request.path != "/api/auth/change-password":
                return redirect("/api/auth/change-password")

        # Store user info in request context for downstream access
        request._current_user = user
        
        return view_func(*args, **kwargs)

    return wrapped


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(*args, **kwargs):
        user = getattr(request, "_current_user", {})
        if user.get("role") != "Admin":
            if _is_api_request():
                return jsonify({"error": {"code": "FORBIDDEN", "message": "Admin role required"}}), 403
            return redirect("/")
        return view_func(*args, **kwargs)

    return wrapped




def get_request_user() -> dict:
    """Return authenticated user injected by login_required."""
    user = getattr(request, "_current_user", None)
    if not isinstance(user, dict):
        raise RuntimeError("No authenticated user in request context")
    return user
