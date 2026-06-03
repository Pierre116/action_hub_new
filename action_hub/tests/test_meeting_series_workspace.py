import io

from tests.conftest import AppTestCase


class MeetingSeriesWorkspaceTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login_admin()

    def _create_series(self, title="Weekly Ops", visibility="public"):
        resp = self.client.post(
            "/api/meetings/series",
            json={"title": title, "topic_id": 1, "visibility": visibility},
        )
        self.assertEqual(resp.status_code, 201)
        return resp.get_json()["data"]["mtg_id"]

    def _create_occurrence(self, series_id, title="Week 1", date="2026-03-18", visibility="public"):
        payload = {"date": date, "visibility": visibility}
        if title is not None:
            payload["title"] = title
        resp = self.client.post(
            f"/api/meetings/series/{series_id}/occurrences",
            json=payload,
        )
        self.assertEqual(resp.status_code, 201)
        return resp.get_json()["data"]["min_id"]

    def test_series_detail_includes_participants_and_occurrences(self):
        series_id = self._create_series("Series Detail Check")
        resp = self.client.get(f"/api/meetings/series/{series_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertEqual(data["mtg_id"], series_id)
        self.assertIn("default_participants", data)
        self.assertGreaterEqual(len(data["default_participants"]), 1)
        self.assertIn("occurrences", data)

    def test_occurrences_expose_series_based_meeting_display_id(self):
        series_id = self._create_series("Display Id Check")
        first_occurrence_id = self._create_occurrence(series_id, title="Week 1", date="2026-03-18")
        second_occurrence_id = self._create_occurrence(series_id, title="Week 2", date="2026-03-25")

        resp = self.client.get(f"/api/meetings/series/{series_id}")
        self.assertEqual(resp.status_code, 200)
        occurrences = resp.get_json()["data"]["occurrences"]
        by_id = {row["min_id"]: row for row in occurrences}
        self.assertEqual(by_id[first_occurrence_id]["meeting_display_id"], f"{series_id}#1")
        self.assertEqual(by_id[second_occurrence_id]["meeting_display_id"], f"{series_id}#2")

        meeting_resp = self.client.get(f"/api/meetings/{second_occurrence_id}")
        self.assertEqual(meeting_resp.status_code, 200)
        self.assertEqual(meeting_resp.get_json()["data"]["meeting_display_id"], f"{series_id}#2")

    def test_series_participants_and_occurrence_copy(self):
        series_id = self._create_series("Participant Copy")
        add_resp = self.client.post(
            f"/api/meetings/series/{series_id}/participants",
            json={"user_id": 2, "kind": "Optional"},
        )
        self.assertEqual(add_resp.status_code, 201)
        occurrence_id = self._create_occurrence(series_id, title="Week Copy")
        occ_resp = self.client.get(f"/api/meetings/{occurrence_id}")
        self.assertEqual(occ_resp.status_code, 200)
        participant_ids = {p["mpa_user_id"] for p in occ_resp.get_json()["data"]["participants"]}
        self.assertIn(2, participant_ids)

    def test_cannot_remove_default_series_participant_when_attached_occurrence_still_uses_user(self):
        series_id = self._create_series("Participant Removal Guard")
        add_resp = self.client.post(
            f"/api/meetings/series/{series_id}/participants",
            json={"user_id": 2, "kind": "Optional"},
        )
        self.assertEqual(add_resp.status_code, 201)
        self._create_occurrence(series_id, title="Week Guard")

        remove_resp = self.client.delete(f"/api/meetings/series/{series_id}/participants/2")
        self.assertEqual(remove_resp.status_code, 400)
        self.assertIn("attached meeting occurrence", remove_resp.get_json()["error"]["message"])

    def test_cannot_replace_series_participant_list_when_removing_attached_user(self):
        series_id = self._create_series("Participant Replace Guard")
        add_resp = self.client.post(
            f"/api/meetings/series/{series_id}/participants",
            json={"user_id": 2, "kind": "Optional"},
        )
        self.assertEqual(add_resp.status_code, 201)
        self._create_occurrence(series_id, title="Week Replace Guard")

        replace_resp = self.client.put(
            f"/api/meetings/series/{series_id}/participants",
            json={"participants": [{"user_id": 1, "kind": "Compulsory"}]},
        )
        self.assertEqual(replace_resp.status_code, 400)
        self.assertIn("attached meeting occurrence", replace_resp.get_json()["error"]["message"])

    def test_occurrence_comments_grouped_by_current_and_previous(self):
        series_id = self._create_series("Occurrence Comments")
        first_occurrence = self._create_occurrence(series_id, title="Week 1", date="2026-03-11")
        second_occurrence = self._create_occurrence(series_id, title="Week 2", date="2026-03-18")

        first_action = self.client.post(
            "/api/actions",
            json={
                "title": "First occurrence action",
                "meeting_id": first_occurrence,
                "topic_id": 1,
                "priority": "Medium",
                "deadline": "2026-12-31",
            },
        ).get_json()["data"]["action"]["act_id"]
        second_action = self.client.post(
            "/api/actions",
            json={
                "title": "Second occurrence action",
                "meeting_id": second_occurrence,
                "topic_id": 1,
                "priority": "Medium",
                "deadline": "2026-12-31",
            },
        ).get_json()["data"]["action"]["act_id"]

        self.client.post(f"/api/actions/{first_action}/comments", json={"body": "First comment"})
        self.client.post(f"/api/actions/{second_action}/comments", json={"body": "Second comment"})

        first_follow_up = self.client.post(
            f"/api/actions/{first_action}/feedback",
            json={
                "meeting_inst_id": first_occurrence,
                "completion_pct": 25,
                "status": "late",
                "comment": "Supplier delay unresolved",
            },
        )
        self.assertEqual(first_follow_up.status_code, 201)

        second_follow_up = self.client.post(
            f"/api/actions/{second_action}/feedback",
            json={
                "meeting_inst_id": second_occurrence,
                "completion_pct": 60,
                "status": "on_track",
                "comment": "Execution improving",
            },
        )
        self.assertEqual(second_follow_up.status_code, 201)

        resp = self.client.get(f"/api/meetings/{second_occurrence}/occurrence-comments")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertGreaterEqual(len(data["current"]), 1)
        self.assertGreaterEqual(len(data["previous"]), 1)
        self.assertGreaterEqual(len(data["follow_up_current"]), 1)
        self.assertGreaterEqual(len(data["follow_up_previous"]), 1)
        self.assertEqual(data["follow_up_current"][0]["action_id"], second_action)
        self.assertEqual(data["follow_up_current"][0]["afb_completion_pct"], 60)
        self.assertEqual(data["follow_up_previous"][0]["action_id"], first_action)
        self.assertEqual(data["follow_up_previous"][0]["afb_status"], "late")

    def test_comment_meeting_link_must_match_action_series(self):
        first_series = self._create_series("Series A")
        second_series = self._create_series("Series B")
        first_occurrence = self._create_occurrence(first_series, title="A1", date="2026-03-11")
        second_occurrence = self._create_occurrence(second_series, title="B1", date="2026-03-18")

        action_id = self.client.post(
            "/api/actions",
            json={
                "title": "Series-bound action",
                "meeting_id": first_occurrence,
                "topic_id": 1,
                "priority": "Medium",
                "deadline": "2026-12-31",
            },
        ).get_json()["data"]["action"]["act_id"]

        mismatch = self.client.post(
            f"/api/actions/{action_id}/comments",
            json={"body": "Wrong meeting link", "meeting_inst_id": second_occurrence},
        )
        self.assertEqual(mismatch.status_code, 400)
        self.assertIn("same meeting series", mismatch.get_json()["error"]["message"])

        matched = self.client.post(
            f"/api/actions/{action_id}/comments",
            json={"body": "Correct meeting link", "meeting_inst_id": first_occurrence},
        )
        self.assertEqual(matched.status_code, 201)

    def test_minutes_pdf_download(self):
        series_id = self._create_series("PDF Series")
        occurrence_id = self._create_occurrence(series_id, title="PDF Occurrence")
        resp = self.client.get(f"/api/meetings/{occurrence_id}/minutes/pdf")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("Content-Type"), "application/pdf")
        self.assertGreater(len(resp.data), 100)

    def test_occurrence_creation_defaults_title_from_series_and_date(self):
        series_id = self._create_series("Title Required")
        resp = self.client.post(
            f"/api/meetings/series/{series_id}/occurrences",
            json={"date": "2026-03-25"},
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()["data"]
        self.assertEqual(data["min_title"], "Title Required - 2026-03-25")

    def test_occurrence_creation_requires_series_topic(self):
        series_id = self._create_series("Missing Topic")
        db = self.get_db()
        db.execute("UPDATE t_meeting SET mtg_topic_id = NULL WHERE mtg_id = ?", (series_id,))
        db.commit()

        resp = self.client.post(
            f"/api/meetings/series/{series_id}/occurrences",
            json={"date": "2026-03-25"},
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"]["message"], "meeting series category is required")

    def test_occurrence_update_ignores_planned_duration(self):
        series_id = self._create_series("Inherited Duration")
        occurrence_id = self._create_occurrence(series_id, title="Duration Occurrence")
        resp = self.client.patch(
            f"/api/meetings/{occurrence_id}",
            json={"planned_duration_min": 45},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIsNone(data["min_planned_duration_min"])

    def test_series_list_exposes_p12_metadata(self):
        series_id = self._create_series("Metadata Series")
        self._create_occurrence(series_id, title="Week Meta", date="2026-03-18")
        resp = self.client.get("/api/meetings/series")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        row = next(item for item in data if item["mtg_id"] == series_id)
        self.assertIn("last_occurrence_date", row)
        self.assertIn("default_participant_count", row)

    def test_private_series_hidden_from_non_participant(self):
        series_id = self._create_series("Private Series", visibility="private")
        self.login_user()
        resp = self.client.get(f"/api/meetings/series/{series_id}")
        self.assertEqual(resp.status_code, 403)
        body = resp.get_json()
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertIn("meta", body)
        self.assertEqual(body["meta"]["mtg_id"], series_id)

    def test_public_series_hidden_from_non_participant(self):
        series_id = self._create_series("Public Series", visibility="public")
        self.login_user()
        resp = self.client.get(f"/api/meetings/series/{series_id}")
        self.assertEqual(resp.status_code, 403)
        body = resp.get_json()
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertIn("meta", body)

    def test_private_series_list_row_shows_locked_access_and_owner_for_non_participant(self):
        series_id = self._create_series("Private Listed Series", visibility="private")
        self.login_user()
        resp = self.client.get("/api/meetings/series")
        self.assertEqual(resp.status_code, 200)
        rows = resp.get_json()["data"]
        row = next(item for item in rows if item["mtg_id"] == series_id)
        self.assertFalse(bool(row.get("series_access")))
        self.assertTrue(bool(row.get("creator_name")))
