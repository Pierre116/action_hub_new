"""Auth module - authentication and user management."""
from flask import request


def get_current_user_id() -> int:
    """Get the current authenticated user's ID from request context.

    Returns:
        User ID from request context.

    Raises:
        RuntimeError: If no user is logged in.
    """
    user = getattr(request, "_current_user", None)
    if user is None:
        raise RuntimeError("No user in request context")
    return user["id"]


def get_current_user() -> dict:
    """Get the current authenticated user's full record from request context.

    Returns:
        User dictionary from request context.
    """
    user = getattr(request, "_current_user", None)
    return user if isinstance(user, dict) else {}


def is_logged_in() -> bool:
    """Check if a user is authenticated for this request.

    Returns:
        True if user is in request context.
    """
    return isinstance(getattr(request, "_current_user", None), dict)
