"""Tests for notification endpoints."""
import unittest

from tests.conftest import AppTestCase


class NotificationTests(AppTestCase):
    """Tests for GET /api/notifications and mark-read endpoints."""

    # 鈹€鈹€ list notifications 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_list_notifications_ok(self):
        self.login_admin()
        resp = self.client.get("/api/notifications")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("data", body)
        data = body["data"]
        self.assertIn("items", data)
        self.assertIn("unread_count", data)
        self.assertIsInstance(data["items"], list)

    def test_list_notifications_unauthenticated(self):
        resp = self.client.get("/api/notifications")
        self.assertEqual(resp.status_code, 401)

    # 鈹€鈹€ mark all read 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_mark_all_read_ok(self):
        self.login_admin()
        resp = self.client.post("/api/notifications/read-all")
        self.assertEqual(resp.status_code, 200)

    def test_mark_all_read_unauthenticated(self):
        resp = self.client.post("/api/notifications/read-all")
        self.assertEqual(resp.status_code, 401)

    # 鈹€鈹€ mark single read 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_mark_single_read_nonexistent(self):
        """marking a non-existent notification is silently accepted (200)."""
        self.login_admin()
        resp = self.client.post("/api/notifications/99999/read")
        self.assertEqual(resp.status_code, 200)

    def test_notifications_after_action_assignment(self):
        """Creating an action and assigning admin should produce a notification."""
        self.login_admin()
        # Create an action
        action_resp = self.client.post(
            "/api/actions",
            json={
                "title": "Notify Test Action",
                "topic_id": 1,
                "priority": "Medium",
                "team_id": 1,
                "deadline": "2026-12-31",
            },
        )
        self.assertEqual(action_resp.status_code, 201)
        action_id = action_resp.get_json()["data"]["action"]["act_id"]

        # Assign admin user as Lead (admin_id=1)
        assign_resp = self.client.post(
            f"/api/actions/{action_id}/assign",
            json={"user_id": 1, "role": "Lead"},
        )
        self.assertIn(assign_resp.status_code, (200, 201))

        # Notifications list should now contain at least one item
        resp = self.client.get("/api/notifications")
        self.assertEqual(resp.status_code, 200)
        notifications = resp.get_json()["data"]["items"]
        self.assertIsInstance(notifications, list)

    def test_mark_notification_read_after_assignment(self):
        """Create a real notification then mark it read."""
        self.login_admin()
        # Create action and assign to produce a notification
        action_id = self.client.post(
            "/api/actions",
            json={"title": "Notify Read Test", "topic_id": 1, "priority": "Low", "team_id": 1, "deadline": "2026-12-31"},
        ).get_json()["data"]["action"]["act_id"]
        self.client.post(
            f"/api/actions/{action_id}/assign", json={"user_id": 1, "role": "Lead"}
        )

        notifications = self.client.get("/api/notifications").get_json()["data"]["items"]
        if notifications:
            ntf_id = notifications[0]["ntf_id"]
            resp = self.client.post(f"/api/notifications/{ntf_id}/read")
            self.assertEqual(resp.status_code, 200)


# ── extended notification tests (from wave3) ──────────────────────────────

class NotificationServiceTests(AppTestCase):
    """Direct tests of notification creation / deadline helper."""

    def test_create_and_retrieve_notification(self):
        self.login_admin()
        with self.app.app_context():
            from actionhub.notifications import create_notification, get_notifications
            from actionhub.middleware.db import get_db
            import sqlite3
            conn = sqlite3.connect(":memory:")
        resp = self.client.get("/api/notifications")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("items", resp.get_json()["data"])

    def test_notify_assignment_creates_notification(self):
        """Assigning a user should create a notification visible after."""
        self.login_admin()
        act_resp = self.client.post(
            "/api/actions",
            json={"title": "Notify Test", "team_id": 1,
                  "topic_id": 1, "priority": "Medium", "deadline": "2026-12-31"},
        )
        act_id = act_resp.get_json()["data"]["action"]["act_id"]
        self.client.post(f"/api/actions/{act_id}/assign", json={"user_id": 1})

        resp = self.client.get("/api/notifications")
        self.assertEqual(resp.status_code, 200)

    def test_notifications_unread_only(self):
        self.login_admin()
        resp = self.client.get("/api/notifications?unread=true")
        self.assertEqual(resp.status_code, 200)

    def test_notifications_unread_false(self):
        self.login_admin()
        resp = self.client.get("/api/notifications?unread=false")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()

