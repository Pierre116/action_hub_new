from tests.conftest import AppTestCase


class VisibilityAndRoleTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login_admin()

    def _create_series_and_occurrence(self, series_title="Role Series", occurrence_title="Occurrence"):
        series_resp = self.client.post(
            "/api/meetings/series",
            json={"title": series_title, "topic_id": 1, "visibility": "public"},
        )
        self.assertEqual(series_resp.status_code, 201)
        series_id = series_resp.get_json()["data"]["mtg_id"]
        occurrence_resp = self.client.post(
            f"/api/meetings/series/{series_id}/occurrences",
            json={"title": occurrence_title, "date": "2026-03-18"},
        )
        self.assertEqual(occurrence_resp.status_code, 201)
        return series_id, occurrence_resp.get_json()["data"]["min_id"]

    def test_non_meeting_action_self_assignment_only(self):
        resp = self.client.post(
            "/api/actions",
            json={
                "title": "Standalone action",
                "topic_id": 1,
                "priority": "Medium",
                "deadline": "2026-12-31",
            },
        )
        self.assertEqual(resp.status_code, 201)
        action = resp.get_json()["data"]["action"]
        roles = set()
        for assignment in resp.get_json()["data"]["assignments"]:
            roles.update(part.strip() for part in str(assignment["asg_role"]).split(",") if part.strip())
        self.assertIn("Lead", roles)

        # Assigning another user as Lead should fail (action already has a Lead)
        assign_resp = self.client.post(
            f"/api/actions/{action['act_id']}/assign",
            json={"user_id": 2, "role": "Lead"},
        )
        self.assertEqual(assign_resp.status_code, 400)

    def test_meeting_action_assignment_requires_participant(self):
        _, occurrence_id = self._create_series_and_occurrence()
        action_resp = self.client.post(
            "/api/actions",
            json={
                "title": "Meeting action",
                "meeting_id": occurrence_id,
                "topic_id": 1,
                "priority": "Medium",
                "deadline": "2026-12-31",
            },
        )
        self.assertEqual(action_resp.status_code, 201)
        action_id = action_resp.get_json()["data"]["action"]["act_id"]

        assign_resp = self.client.post(
            f"/api/actions/{action_id}/assign",
            json={"user_id": 2, "role": "Lead"},
        )
        self.assertEqual(assign_resp.status_code, 400)

    def test_meeting_action_edit_forbidden_for_non_creator(self):
        _, occurrence_id = self._create_series_and_occurrence()
        action_resp = self.client.post(
            "/api/actions",
            json={
                "title": "Edit restricted action",
                "meeting_id": occurrence_id,
                "topic_id": 1,
                "priority": "Medium",
                "deadline": "2026-12-31",
            },
        )
        self.assertEqual(action_resp.status_code, 201)
        action_id = action_resp.get_json()["data"]["action"]["act_id"]

        self.login_user()
        update_resp = self.client.patch(
            f"/api/actions/{action_id}",
            json={"title": "Forbidden edit"},
        )
        self.assertEqual(update_resp.status_code, 403)

    def test_occurrence_participant_without_assignment_cannot_access_meeting_action_detail(self):
        series_resp = self.client.post(
            "/api/meetings/series",
            json={"title": "Participant Access Series", "topic_id": 1, "visibility": "public"},
        )
        self.assertEqual(series_resp.status_code, 201)
        series_id = series_resp.get_json()["data"]["mtg_id"]

        add_participant_resp = self.client.post(
            f"/api/meetings/series/{series_id}/participants",
            json={"user_id": 2, "kind": "Optional"},
        )
        self.assertEqual(add_participant_resp.status_code, 201)

        occurrence_resp = self.client.post(
            f"/api/meetings/series/{series_id}/occurrences",
            json={"title": "Participant Access Occurrence", "date": "2026-03-18"},
        )
        self.assertEqual(occurrence_resp.status_code, 201)
        occurrence_id = occurrence_resp.get_json()["data"]["min_id"]

        action_resp = self.client.post(
            "/api/actions",
            json={
                "title": "Participant Visible Action",
                "meeting_id": occurrence_id,
                "topic_id": 1,
                "priority": "Medium",
                "deadline": "2026-12-31",
            },
        )
        self.assertEqual(action_resp.status_code, 201)
        action_id = action_resp.get_json()["data"]["action"]["act_id"]

        self.login_user()
        detail_resp = self.client.get(f"/api/actions/{action_id}")
        self.assertEqual(detail_resp.status_code, 404)

        list_resp = self.client.get("/api/actions?search=Participant%20Visible%20Action")
        self.assertEqual(list_resp.status_code, 200)
        returned_ids = {item["act_id"] for item in list_resp.get_json()["data"]["items"]}
        self.assertIn(action_id, returned_ids)
