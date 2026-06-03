"""Tests for taxonomy endpoints: teams, topics, and tags."""
import unittest

from tests.conftest import AppTestCase


class TaxonomyTests(AppTestCase):
    """Tests for read-only taxonomy lookup endpoints."""

    # 鈹€鈹€ removed endpoint guard 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_Teams_endpoint_removed(self):
        self.login_admin()
        resp = self.client.get("/api/Teams")
        self.assertEqual(resp.status_code, 404)

    # 鈹€鈹€ teams 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_teams_list_ok(self):
        self.login_admin()
        resp = self.client.get("/api/teams")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("data", body)

    def test_teams_filter_by_team(self):
        self.login_admin()
        resp = self.client.get("/api/teams?team_id=1")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("data", resp.get_json())

    def test_teams_unauthenticated(self):
        resp = self.client.get("/api/teams")
        self.assertEqual(resp.status_code, 401)

    # 鈹€鈹€ topics 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_topics_list_ok(self):
        self.login_admin()
        resp = self.client.get("/api/topics")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIsInstance(data, list)
        # seed contains topic id=1 "General"
        ids = [t.get("top_id") for t in data]
        self.assertIn(1, ids)

    def test_topics_unauthenticated(self):
        resp = self.client.get("/api/topics")
        self.assertEqual(resp.status_code, 401)

    # 鈹€鈹€ tags 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def test_tags_list_ok(self):
        self.login_admin()
        resp = self.client.get("/api/tags")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIsInstance(data, list)

    def test_tags_unauthenticated(self):
        resp = self.client.get("/api/tags")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()

