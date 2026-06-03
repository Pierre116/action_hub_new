"""Tests for admin topic CRUD and admin actions table."""
import unittest

from tests.conftest import AppTestCase


def _create_action(client, title="Action for Topics", topic_id=1, team_id=1, deadline="2026-12-31"):
    resp = client.post(
        "/api/actions",
        json={"title": title, "team_id": team_id,
              "topic_id": topic_id, "priority": "Medium", "deadline": deadline},
    )
    assert resp.status_code == 201, f"action create failed: {resp.get_json()}"
    return resp.get_json()["data"]["action"]["act_id"]


class AdminTopicTests(AppTestCase):
    """CRUD tests for /api/admin/topics."""

    _counter = 0

    def _unique(self, prefix="topic"):
        AdminTopicTests._counter += 1
        return f"{prefix}{AdminTopicTests._counter}"

    def _create_topic(self, name=None):
        name = name or self._unique("TestTopic")
        return self.client.post(
            "/api/admin/topics",
            json={"name": name},
        )

    # 鈹€鈹€ list 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_list_topics_ok(self):
        self.login_admin()
        resp = self.client.get("/api/admin/topics")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)  # seed has "General"

    def test_list_topics_include_inactive(self):
        self.login_admin()
        resp = self.client.get("/api/admin/topics?include_inactive=true")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    def test_list_topics_unauthenticated(self):
        resp = self.client.get("/api/admin/topics")
        self.assertEqual(resp.status_code, 401)

    # 鈹€鈹€ create 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_create_topic_ok(self):
        self.login_admin()
        resp = self._create_topic("NewTopicX")
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()["data"]
        self.assertIn("top_id", data)
        self.assertEqual(data["top_name"], "NewTopicX")

    def test_create_topic_short_name(self):
        self.login_admin()
        resp = self.client.post("/api/admin/topics", json={"name": "X"})
        self.assertEqual(resp.status_code, 400)

    def test_create_topic_duplicate(self):
        self.login_admin()
        self._create_topic("DupTopic")
        resp = self._create_topic("DupTopic")
        self.assertEqual(resp.status_code, 400)

    # 鈹€鈹€ update 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_update_topic_name(self):
        self.login_admin()
        topic_id = self._create_topic().get_json()["data"]["top_id"]
        resp = self.client.patch(
            f"/api/admin/topics/{topic_id}",
            json={"name": "UpdatedTopicName"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["top_name"], "UpdatedTopicName")

    def test_update_topic_deactivate(self):
        self.login_admin()
        topic_id = self._create_topic().get_json()["data"]["top_id"]
        resp = self.client.patch(
            f"/api/admin/topics/{topic_id}",
            json={"active": False},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["top_active"], 0)

    def test_update_topic_not_found(self):
        self.login_admin()
        resp = self.client.patch("/api/admin/topics/99999", json={"name": "X"})
        self.assertEqual(resp.status_code, 404)

    # 鈹€鈹€ actions by topic 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_topic_actions_list_ok(self):
        self.login_admin()
        # Use seed topic id=1
        resp = self.client.get("/api/admin/topics/1/actions")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)


class AdminActionsTableTests(AppTestCase):
    """Tests for /api/admin/actions (paged inline table) and inline update."""

    def setUp(self):
        super().setUp()
        self.login_admin()
        self.action_id = _create_action(self.client)

    def test_admin_actions_list_ok(self):
        resp = self.client.get("/api/admin/actions")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()["data"]
        self.assertIn("items", body)
        self.assertIsInstance(body["items"], list)

    def test_admin_actions_list_filter_status(self):
        resp = self.client.get("/api/admin/actions?status=Open")
        self.assertEqual(resp.status_code, 200)
        items = resp.get_json()["data"]["items"]
        for item in items:
            self.assertEqual(item["act_status"], "Open")

    def test_admin_actions_list_page(self):
        resp = self.client.get("/api/admin/actions?page=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIn("pagination", data)
        self.assertIn("total", data["pagination"])
        self.assertIn("page", data["pagination"])

    def test_admin_actions_inline_update_priority(self):
        resp = self.client.patch(
            f"/api/admin/actions/{self.action_id}",
            json={"priority": "High"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["act_priority"], "High")

    def test_admin_actions_inline_update_not_found(self):
        resp = self.client.patch("/api/admin/actions/99999", json={"priority": "Low"})
        self.assertEqual(resp.status_code, 404)

    def test_admin_actions_unauthenticated(self):
        # reset auth by re-creating a fresh unauthenticated client
        with self.app.test_client() as fresh:
            resp = fresh.get("/api/admin/actions")
            self.assertEqual(resp.status_code, 401)


class AdminUserTeamTests(AppTestCase):
    """Tests for user-team membership management."""

    def setUp(self):
        super().setUp()
        self.login_admin()

    def test_list_all_users_with_teams(self):
        resp = self.client.get("/api/admin/users")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    def test_list_teams_ok(self):
        resp = self.client.get("/api/admin/teams")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    def test_user_teams_list_empty(self):
        resp = self.client.get("/api/admin/users/1/teams")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    def test_unauthenticated_blocked_for_all_users(self):
        with self.app.test_client() as fresh:
            resp = fresh.get("/api/admin/users")
            self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()

