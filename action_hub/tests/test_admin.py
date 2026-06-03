"""Tests for admin user/Team management endpoints."""
import os
import shutil
import sqlite3
import tempfile
import unittest

from actionhub import create_app
from actionhub.middleware.db import init_db
from tests.conftest import AppTestCase


class AdminUserTests(AppTestCase):
    """Admin CRUD for users via /api/admin/users."""

    # 鈹€鈹€ helpers 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    _counter = 0

    def _unique(self, prefix="usr"):
        AdminUserTests._counter += 1
        return f"{prefix}{AdminUserTests._counter}"

    def _create_user(self, role="Member", team_id=1):
        name = self._unique("testuser")
        return self.client.post(
            "/api/admin/users",
            json={
                "username": name,
                "password": "Passw0rd!",
                "display_name": f"Test User {name}",
                "email": f"{name}@example.com",
                "role": role,
                "team_id": team_id,
            },
        )

    # 鈹€鈹€ list users 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_list_users_ok(self):
        self.login_admin()
        resp = self.client.get("/api/admin/users")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIsInstance(data, list)
        usernames = [u["usr_username"] for u in data]
        self.assertIn("admin", usernames)

    def test_list_users_unauthenticated(self):
        resp = self.client.get("/api/admin/users")
        self.assertEqual(resp.status_code, 401)

    # 鈹€鈹€ create user 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_create_user_ok(self):
        self.login_admin()
        resp = self._create_user()
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()["data"]
        self.assertIn("usr_id", data)
        self.assertEqual(data["usr_role"], "Member")

    def test_create_user_teamlead_role_ok(self):
        self.login_admin()
        resp = self._create_user(role="TeamLead")
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()["data"]
        self.assertEqual(data["usr_role"], "TeamLead")

    def test_create_user_missing_fields(self):
        self.login_admin()
        resp = self.client.post("/api/admin/users", json={"username": "incomplete"})
        self.assertEqual(resp.status_code, 400)

    def test_create_user_duplicate_username(self):
        self.login_admin()
        name = self._unique("dupuser")
        payload = {
            "username": name,
            "password": "Passw0rd!",
            "display_name": "Dup",
            "email": f"{name}@example.com",
            "role": "Member",
            "team_id": 1,
        }
        self.client.post("/api/admin/users", json=payload)
        resp = self.client.post("/api/admin/users", json=payload)
        self.assertEqual(resp.status_code, 400)

    # 鈹€鈹€ update user 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_update_user_display_name(self):
        self.login_admin()
        user_id = self._create_user().get_json()["data"]["usr_id"]
        resp = self.client.patch(
            f"/api/admin/users/{user_id}", json={"display_name": "Updated Name"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["usr_display_name"], "Updated Name")

    def test_update_user_not_found(self):
        self.login_admin()
        resp = self.client.patch("/api/admin/users/99999", json={"display_name": "X"})
        self.assertEqual(resp.status_code, 404)

    def test_update_user_role_to_teamlead_ok(self):
        self.login_admin()
        user_id = self._create_user().get_json()["data"]["usr_id"]
        resp = self.client.patch(
            f"/api/admin/users/{user_id}", json={"role": "TeamLead"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["usr_role"], "TeamLead")

    # 鈹€鈹€ reset password 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_reset_password_ok(self):
        self.login_admin()
        user_id = self._create_user().get_json()["data"]["usr_id"]
        resp = self.client.post(
            f"/api/admin/users/{user_id}/reset-password",
            json={"password": "NewPass@2026"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["data"]["reset"])

    def test_reset_password_not_found(self):
        self.login_admin()
        resp = self.client.post(
            "/api/admin/users/99999/reset-password", json={"password": "NewPass@2026"}
        )
        self.assertEqual(resp.status_code, 404)

    # 鈹€鈹€ non-admin access denied 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_non_admin_blocked_from_user_list(self):
        self.login_admin()
        # Create a regular Member user
        name = self._unique("member")
        self.client.post(
            "/api/admin/users",
            json={
                "username": name,
                "password": "Passw0rd!",
                "display_name": "Regular Member",
                "email": f"{name}@example.com",
                "role": "Member",
                "team_id": 1,
            },
        )
        # Login as that member
        login_resp = self.client.post(
            "/api/auth/login", json={"username": name, "password": "Passw0rd!"}
        )
        member_token = login_resp.get_json()["data"]["access_token"]
        resp = self.client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        self.assertEqual(resp.status_code, 403)


class AdminTeamTests(AppTestCase):
    """Admin CRUD for Teams via /api/admin/teams."""

    def test_list_Teams_ok(self):
        self.login_admin()
        resp = self.client.get("/api/admin/teams")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_create_Team_ok(self):
        self.login_admin()
        resp = self.client.post(
            "/api/admin/teams",
            json={"code": "TST", "name_en": "Test Team", "name_cn": "娴嬭瘯閮ㄩ棬"},
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()["data"]
        self.assertIn("tea_id", data)
        self.assertEqual(data["tea_code"], "TST")

    def test_create_Team_with_leader_ok(self):
        self.login_admin()
        resp = self.client.post(
            "/api/admin/teams",
            json={
                "code": "LDR",
                "name_en": "Leader Team",
                "name_cn": "棰嗗鍥㈤槦",
                "leader_id": 1,
            },
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()["data"]
        self.assertEqual(data["tea_leader_user_id"], 1)
        members = self.client.get(f"/api/admin/teams/{data['tea_id']}/members").get_json()["data"]
        self.assertTrue(any(member["usr_id"] == 1 for member in members))

    def test_update_Team_ok(self):
        self.login_admin()
        tea_id = self.client.post(
            "/api/admin/teams",
            json={"code": "UPD", "name_en": "Before", "name_cn": "涔嬪墠"},
        ).get_json()["data"]["tea_id"]
        resp = self.client.patch(
            f"/api/admin/teams/{tea_id}", json={"name_en": "After"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["tea_name_en"], "After")

    def test_update_Team_leader_ok(self):
        self.login_admin()
        tea_id = self.client.post(
            "/api/admin/teams",
            json={"code": "UPL", "name_en": "Before", "name_cn": "涔嬪墠"},
        ).get_json()["data"]["tea_id"]
        resp = self.client.patch(
            f"/api/admin/teams/{tea_id}", json={"leader_id": 1}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["tea_leader_user_id"], 1)
        members = self.client.get(f"/api/admin/teams/{tea_id}/members").get_json()["data"]
        self.assertTrue(any(member["usr_id"] == 1 for member in members))

    def test_list_team_users_ok(self):
        self.login_admin()
        resp = self.client.get("/api/admin/teams/1/members")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    def test_Teams_unauthenticated(self):
        resp = self.client.get("/api/admin/teams")
        self.assertEqual(resp.status_code, 401)


class TeamSchemaCompatTests(unittest.TestCase):
    def test_init_db_adds_team_leader_column(self):
        temp_dir = tempfile.mkdtemp(prefix="actionhub_team_schema_")
        db_path = os.path.join(temp_dir, "compat.db")
        previous_database = os.environ.get("DATABASE")
        previous_env = os.environ.get("ACTIONHUB_ENV")
        os.environ["DATABASE"] = db_path
        os.environ["ACTIONHUB_ENV"] = "development"

        try:
            app = create_app()
            with app.app_context():
                conn = sqlite3.connect(db_path)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS t_team (
                        tea_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tea_code TEXT UNIQUE,
                        tea_name_en TEXT NOT NULL,
                        tea_name_cn TEXT,
                        tea_active INTEGER NOT NULL DEFAULT 1,
                        tea_sort_order INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                conn.commit()
                conn.close()

                init_db()

                conn = sqlite3.connect(db_path)
                columns = [row[1] for row in conn.execute("PRAGMA table_info(t_team)").fetchall()]
                conn.close()

            self.assertIn("tea_leader_user_id", columns)
        finally:
            if previous_database is None:
                os.environ.pop("DATABASE", None)
            else:
                os.environ["DATABASE"] = previous_database
            if previous_env is None:
                os.environ.pop("ACTIONHUB_ENV", None)
            else:
                os.environ["ACTIONHUB_ENV"] = previous_env
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

