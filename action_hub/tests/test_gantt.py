"""Tests for Gantt endpoints."""
import unittest

from tests.conftest import AppTestCase


class GanttTests(AppTestCase):
    """Tests for GET /api/gantt and /api/gantt/filters."""

    # 鈹€鈹€ main data endpoint 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_gantt_data_ok(self):
        self.login_admin()
        resp = self.client.get("/api/gantt")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("data", body)
        self.assertIn("total", body)
        self.assertIsInstance(body["data"], list)

    def test_gantt_data_unauthenticated(self):
        resp = self.client.get("/api/gantt")
        self.assertEqual(resp.status_code, 401)

    def test_gantt_filter_by_team(self):
        self.login_admin()
        resp = self.client.get("/api/gantt?team_id=1")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("data", resp.get_json())

    def test_gantt_filter_by_topic(self):
        self.login_admin()
        resp = self.client.get("/api/gantt?topic_id=1")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("data", resp.get_json())

    def test_gantt_filter_by_user(self):
        self.login_admin()
        resp = self.client.get("/api/gantt?user_id=1")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("data", resp.get_json())

    def test_gantt_filter_by_status(self):
        self.login_admin()
        resp = self.client.get("/api/gantt?statuses=Open,In+Progress")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("data", resp.get_json())

    # 鈹€鈹€ gantt shows actions with deadlines 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_gantt_returns_action_with_deadline(self):
        self.login_admin()
        # Create an action with a deadline so it appears in gantt
        create_resp = self.client.post(
            "/api/actions",
            json={
                "title": "Gantt Visible Action",
                "topic_id": 1,
                "priority": "High",
                "team_id": 1,
                "deadline": "2026-12-31",
            },
        )
        self.assertEqual(create_resp.status_code, 201)
        action_id = create_resp.get_json()["data"]["action"]["act_id"]

        resp = self.client.get("/api/gantt")
        ids = [item["id"] for item in resp.get_json()["data"]]
        self.assertIn(action_id, ids)

    # 鈹€鈹€ filters endpoint 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_gantt_filters_ok(self):
        self.login_admin()
        resp = self.client.get("/api/gantt/filters")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("data", body)
        self.assertIn("teams", body["data"])
        self.assertIn("topics", body["data"])
        self.assertIn("users", body["data"])
        self.assertIsInstance(body["data"]["teams"], list)
        self.assertGreater(len(body["data"]["teams"]), 0)

    def test_gantt_filters_unauthenticated(self):
        resp = self.client.get("/api/gantt/filters")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()

