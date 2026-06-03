"""Tests for SEP-1: JWT Auth (dual-mode with session).

Verifies:
- Login returns access_token and refresh_token
- /api/auth/me returns authenticated user info
- JWT-protected endpoints work with Bearer token
- Token refresh returns new access token
- Logout blacklists JWT token
"""
import unittest

from tests.conftest import AppTestCase


class TestJWTLogin(AppTestCase):
    """Test JWT token generation on login."""

    def test_login_returns_jwt_tokens(self):
        """POST /api/auth/login should return access_token and refresh_token."""
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Admin@2026"},
        )
        assert response.status_code == 200
        json_data = response.get_json()
        assert "data" in json_data
        assert "access_token" in json_data["data"]
        assert "refresh_token" in json_data["data"]
        assert "id" in json_data["data"]
        assert "username" in json_data["data"]


    def test_login_and_me_success(self):
        """POST /api/auth/login then GET /api/auth/me should return user info."""
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Admin@2026"},
        )
        assert response.status_code == 200
        json_data = response.get_json()
        access_token = json_data["data"]["access_token"]

        me = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me.status_code == 200
        payload = me.get_json()["data"]
        assert payload["username"] == "admin"

    def test_login_with_invalid_credentials_returns_error(self):
        """POST /api/auth/login with wrong password should return 401."""
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "WrongPassword"},
        )
        assert response.status_code == 401
        json_data = response.get_json()
        assert "error" in json_data


class TestJWTProtectedEndpoint(AppTestCase):
    """Test JWT token authentication on protected endpoints."""

    def test_jwt_protected_endpoint_with_bearer_token(self):
        """GET /api/actions with valid Bearer token should succeed."""
        # First login to get tokens
        login_response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Admin@2026"},
        )
        json_data = login_response.get_json()
        access_token = json_data["data"]["access_token"]

        # Make request with Bearer token
        response = self.client.get(
            "/api/actions",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200

    def test_jwt_protected_endpoint_without_token_returns_401(self):
        """GET /api/actions without auth should return 401."""
        response = self.client.get("/api/actions")
        # Without auth, should return 401 (API request)
        assert response.status_code == 401
        json_data = response.get_json()
        assert "error" in json_data

    def test_jwt_protected_endpoint_with_invalid_token_returns_401(self):
        """GET /api/actions with invalid Bearer token should return 401."""
        response = self.client.get(
            "/api/actions",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert response.status_code == 401


class TestJWTTokenRefresh(AppTestCase):
    """Test JWT token refresh endpoint."""

    def test_refresh_returns_new_access_token(self):
        """POST /api/auth/refresh with valid refresh token should return new access token."""
        # First login to get tokens
        login_response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Admin@2026"},
        )
        json_data = login_response.get_json()
        refresh_token = json_data["data"]["refresh_token"]

        # Refresh the token
        response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        json_data = response.get_json()
        assert "data" in json_data
        assert "access_token" in json_data["data"]

    def test_refresh_with_invalid_token_returns_401(self):
        """POST /api/auth/refresh with invalid token should return 401."""
        response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"},
        )
        assert response.status_code == 401

    def test_refresh_without_token_returns_400(self):
        """POST /api/auth/refresh without refresh_token should return 400."""
        response = self.client.post(
            "/api/auth/refresh",
            json={},
        )
        assert response.status_code == 400


class TestJWTLogout(AppTestCase):
    """Test JWT token blacklisting on logout."""

    def test_logout_blacklists_token(self):
        """DELETE /api/auth/logout with Bearer token should blacklist it."""
        # Login to get token
        login_response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Admin@2026"},
        )
        json_data = login_response.get_json()
        access_token = json_data["data"]["access_token"]

        # Verify token works before logout
        response = self.client.get(
            "/api/actions",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200

        # Logout with the token
        logout_response = self.client.delete(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_response.status_code == 200

        # Token should now be rejected
        response = self.client.get(
            "/api/actions",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 401

    def test_logout_without_token_still_returns_200(self):
        """DELETE /api/auth/logout without Bearer token should be idempotent."""
        response = self.client.delete("/api/auth/logout")
        assert response.status_code == 200
