"""JWT token service for SEP-1 and SEP-4 API auth.

Provides token generation, decoding, validation, and blacklisting.
"""
import jwt
from datetime import datetime, timezone
from typing import Any

# In-memory token blacklist (for production, use Redis or database)
_token_blacklist: set[str] = set()


def generate_access_token(user: dict[str, Any], secret_key: str, expiry_seconds: int) -> str:
    """Generate a JWT access token for a user.
    
    Args:
        user: User dict with at least 'id', 'username', 'role'
        secret_key: JWT_SECRET_KEY from config
        expiry_seconds: Token lifetime in seconds (default 900 = 15 min)
    
    Returns:
        JWT access token string
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "username": user.get("username", ""),
        "role": user.get("role", ""),
        "lang": user.get("lang", "en"),
        "must_change_pwd": bool(user.get("must_change_pwd", False)),
        "exp": now.timestamp() + expiry_seconds,
        "iat": now.timestamp(),
        "type": "access",
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def generate_refresh_token(user: dict[str, Any], secret_key: str, expiry_seconds: int) -> str:
    """Generate a JWT refresh token for a user.
    
    Args:
        user: User dict with at least 'id', 'username', 'role'
        secret_key: JWT_SECRET_KEY from config
        expiry_seconds: Token lifetime in seconds (default 604800 = 7 days)
    
    Returns:
        JWT refresh token string
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "username": user.get("username", ""),
        "role": user.get("role", ""),
        "lang": user.get("lang", "en"),
        "exp": now.timestamp() + expiry_seconds,
        "iat": now.timestamp(),
        "type": "refresh",
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def decode_token(token: str, secret_key: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        secret_key: JWT_SECRET_KEY from config
    
    Returns:
        Decoded payload dict, or None if invalid/expired/blacklisted
    """
    # Check blacklist first
    if token in _token_blacklist:
        return None
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def is_token_blacklisted(token: str) -> bool:
    """Check if a token is blacklisted.
    
    Args:
        token: JWT token string
    
    Returns:
        True if token is blacklisted
    """
    return token in _token_blacklist


def blacklist_token(token: str) -> None:
    """Add a token to the blacklist (logout).
    
    Args:
        token: JWT token string to blacklist
    """
    _token_blacklist.add(token)


def verify_access_token(token: str, secret_key: str) -> dict[str, Any] | None:
    """Verify an access token (must be type='access', not blacklisted).
    
    Args:
        token: JWT access token string
        secret_key: JWT_SECRET_KEY from config
    
    Returns:
        Decoded payload if valid, None otherwise
    """
    payload = decode_token(token, secret_key)
    if payload is None:
        return None
    
    # Must be an access token, not refresh
    if payload.get("type") != "access":
        return None
    
    return payload


def verify_refresh_token(token: str, secret_key: str) -> dict[str, Any] | None:
    """Verify a refresh token (must be type='refresh', not blacklisted).
    
    Args:
        token: JWT refresh token string
        secret_key: JWT_SECRET_KEY from config
    
    Returns:
        Decoded payload if valid, None otherwise
    """
    payload = decode_token(token, secret_key)
    if payload is None:
        return None
    
    # Must be a refresh token
    if payload.get("type") != "refresh":
        return None
    
    return payload
