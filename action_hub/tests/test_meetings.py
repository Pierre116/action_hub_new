"""Tests for meeting instance endpoints."""
import io
import unittest

from tests.conftest import AppTestCase


class MeetingTests(AppTestCase):
    """CRUD + memo tests for /api/meetings."""

    # ── helpers ──────────────────────────────────────────────────────────────

    def _create_meeting(self, title="Test Meeting", date="2026-03-01", topic_id=1):
        self.login_admin()
        resp = self.client.post(
            "/api/meetings",
            json={"title": title, "date": date, "topic_id": topic_id},
        )
        return resp

    # ── create ────────────────────────────────────────────────────────────────

    def test_create_meeting_ok(self):
        resp = self._create_meeting()
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()["data"]
        self.assertEqual(data["min_title"], "Test Meeting")
        self.assertEqual(data["min_date"], "2026-03-01")

    def test_create_meeting_adds_creator_as_compulsory_participant(self):
        resp = self._create_meeting(title="Creator Participant Default")
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()["data"]
        creator_id = int(data["min_created_by"])

        participants = data.get("participants") or []
        matching = [participant for participant in participants if int(participant.get("mpa_user_id") or 0) == creator_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].get("mpa_kind"), "Compulsory")

    def test_create_meeting_missing_title(self):
        self.login_admin()
        resp = self.client.post("/api/meetings", json={"date": "2026-03-01"})
        self.assertEqual(resp.status_code, 400)

    def test_create_meeting_missing_date(self):
        self.login_admin()
        resp = self.client.post("/api/meetings", json={"title": "No date"})
        self.assertEqual(resp.status_code, 400)

    def test_create_meeting_unauthenticated(self):
        resp = self.client.post("/api/meetings", json={"title": "X", "date": "2026-01-01"})
        self.assertEqual(resp.status_code, 401)

    # ── list ─────────────────────────────────────────────────────────────────

    def test_list_meetings_ok(self):
        self._create_meeting(title="Listed Meeting")
        resp = self.client.get("/api/meetings")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIsInstance(data, list)
        titles = [m["min_title"] for m in data]
        self.assertIn("Listed Meeting", titles)

    def test_list_meetings_filter_by_topic(self):
        self._create_meeting(title="Topic Filtered")
        resp = self.client.get("/api/meetings?topic_id=1")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("data", resp.get_json())

    def test_list_meetings_unauthenticated(self):
        resp = self.client.get("/api/meetings")
        self.assertEqual(resp.status_code, 401)

    # ── detail ────────────────────────────────────────────────────────────────

    def test_meeting_detail_ok(self):
        create_resp = self._create_meeting(title="Detail Check")
        mtg_id = create_resp.get_json()["data"]["min_id"]
        resp = self.client.get(f"/api/meetings/{mtg_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertEqual(data["min_id"], mtg_id)

    def test_meeting_detail_not_found(self):
        self.login_admin()
        resp = self.client.get("/api/meetings/99999")
        self.assertEqual(resp.status_code, 404)

    # ── update ────────────────────────────────────────────────────────────────

    def test_update_meeting_ok(self):
        mtg_id = self._create_meeting(title="Before Update").get_json()["data"]["min_id"]
        resp = self.client.patch(f"/api/meetings/{mtg_id}", json={"title": "After Update"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["min_title"], "After Update")

    def test_update_meeting_not_found(self):
        self.login_admin()
        resp = self.client.patch("/api/meetings/99999", json={"title": "X"})
        self.assertEqual(resp.status_code, 404)

    # ── actions linked to meeting ─────────────────────────────────────────────

    def test_meeting_actions_ok(self):
        mtg_id = self._create_meeting(title="Actions Meeting").get_json()["data"]["min_id"]
        resp = self.client.get(f"/api/meetings/{mtg_id}/actions")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    # ── text memos ────────────────────────────────────────────────────────────

    def test_list_text_memos_empty(self):
        mtg_id = self._create_meeting(title="Memo Meeting").get_json()["data"]["min_id"]
        resp = self.client.get(f"/api/meetings/{mtg_id}/text-memos")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    def test_create_text_memo(self):
        mtg_id = self._create_meeting(title="Memo Create").get_json()["data"]["min_id"]
        resp = self.client.post(
            f"/api/meetings/{mtg_id}/text-memos",
            json={"title": "Memo Title", "body": "First memo note"},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn("mmm_id", resp.get_json()["data"])


# ── blob memo tests (from wave3) ─────────────────────────────────────────────

class MeetingMemoTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login_admin()
        resp = self.client.post(
            "/api/meetings",
            json={"title": "Memo Test Meeting", "date": "2026-03-01", "topic_id": 1},
        )
        self.min_id = resp.get_json()["data"]["min_id"]

    def test_list_memos_empty(self):
        resp = self.client.get(f"/api/meetings/{self.min_id}/memos")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"], [])

    def test_upload_memo_ok(self):
        data = {"file": (io.BytesIO(b"sample file content"), "minutes.txt")}
        resp = self.client.post(
            f"/api/meetings/{self.min_id}/memos",
            data=data, content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 201)
        memo = resp.get_json()["data"]
        self.assertIn("msm_id", memo)
        self.assertEqual(memo["msm_filename"], "minutes.txt")

    def test_upload_memo_no_file(self):
        resp = self.client.post(f"/api/meetings/{self.min_id}/memos", data={})
        self.assertEqual(resp.status_code, 400)

    def test_download_memo_ok(self):
        self.client.post(
            f"/api/meetings/{self.min_id}/memos",
            data={"file": (io.BytesIO(b"hello"), "note.txt")},
            content_type="multipart/form-data",
        )
        memos = self.client.get(f"/api/meetings/{self.min_id}/memos").get_json()["data"]
        msm_id = memos[0]["msm_id"]
        resp = self.client.get(f"/api/meetings/memos/{msm_id}/download")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, b"hello")

    def test_download_memo_not_found(self):
        resp = self.client.get("/api/meetings/memos/99999/download")
        self.assertEqual(resp.status_code, 404)

    def test_delete_memo_ok(self):
        self.client.post(
            f"/api/meetings/{self.min_id}/memos",
            data={"file": (io.BytesIO(b"del"), "del.txt")},
            content_type="multipart/form-data",
        )
        memos = self.client.get(f"/api/meetings/{self.min_id}/memos").get_json()["data"]
        msm_id = memos[0]["msm_id"]
        resp = self.client.delete(f"/api/meetings/memos/{msm_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["data"]["ok"])
        memos_after = self.client.get(f"/api/meetings/{self.min_id}/memos").get_json()["data"]
        self.assertEqual(memos_after, [])


# ── text-memo extras (from wave3) ────────────────────────────────────────────

class TextMemoExtrasTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login_admin()
        resp = self.client.post(
            "/api/meetings",
            json={"title": "TextMemo Meeting", "date": "2026-03-01", "topic_id": 1},
        )
        self.min_id = resp.get_json()["data"]["min_id"]

    def _create_text_memo(self, title="Memo Title"):
        resp = self.client.post(
            f"/api/meetings/{self.min_id}/text-memos",
            json={"title": title, "body": "Body text"},
        )
        return resp.get_json()["data"]["mmm_id"]

    def test_update_text_memo_title(self):
        mmm_id = self._create_text_memo()
        resp = self.client.patch(
            f"/api/meetings/text-memos/{mmm_id}",
            json={"title": "Updated Title"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["mmm_title"], "Updated Title")

    def test_update_text_memo_body(self):
        mmm_id = self._create_text_memo()
        resp = self.client.patch(
            f"/api/meetings/text-memos/{mmm_id}",
            json={"body": "New body"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["mmm_body"], "New body")

    def test_update_text_memo_not_found(self):
        resp = self.client.patch(
            "/api/meetings/text-memos/99999",
            json={"title": "X"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_move_text_memo_down(self):
        id1 = self._create_text_memo("First")
        self._create_text_memo("Second")
        resp = self.client.post(
            f"/api/meetings/text-memos/{id1}/move",
            json={"direction": "down"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    def test_move_text_memo_up(self):
        self._create_text_memo("A")
        id2 = self._create_text_memo("B")
        resp = self.client.post(
            f"/api/meetings/text-memos/{id2}/move",
            json={"direction": "up"},
        )
        self.assertEqual(resp.status_code, 200)

    def test_move_text_memo_not_found(self):
        resp = self.client.post(
            "/api/meetings/text-memos/99999/move",
            json={"direction": "up"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_text_memo_ok(self):
        mmm_id = self._create_text_memo()
        resp = self.client.delete(f"/api/meetings/text-memos/{mmm_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["data"]["ok"])

    def test_delete_text_memo_idempotent(self):
        resp = self.client.delete("/api/meetings/text-memos/99999")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["data"]["ok"])


# ── meeting series (from wave3) ──────────────────────────────────────────────

class MeetingSeriesTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login_admin()

    def test_list_series_ok(self):
        resp = self.client.get("/api/meetings/series")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    def test_list_series_by_topic(self):
        resp = self.client.get("/api/meetings/series?topic_id=1")
        self.assertEqual(resp.status_code, 200)

    def test_create_series_ok(self):
        resp = self.client.post(
            "/api/meetings/series",
            json={"title": "Weekly Sync", "topic_id": 1},
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()["data"]
        self.assertIn("mtg_id", data)

    def test_create_series_non_admin_ok(self):
        self.login_user()
        resp = self.client.post(
            "/api/meetings/series",
            json={"title": "User Series", "topic_id": 1},
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()["data"]
        self.assertIn("mtg_id", data)

    def test_series_instances_ok(self):
        resp = self.client.post(
            "/api/meetings/series",
            json={"title": "Series With Instances", "topic_id": 1},
        )
        mtg_id = resp.get_json()["data"]["mtg_id"]
        resp2 = self.client.get(f"/api/meetings/series/{mtg_id}/instances")
        self.assertEqual(resp2.status_code, 200)
        self.assertIsInstance(resp2.get_json()["data"], list)

    def test_list_series_unauthenticated(self):
        with self.app.test_client() as fresh:
            resp = fresh.get("/api/meetings/series")
        self.assertEqual(resp.status_code, 401)


class MeetingVisibilityAndParticipantPolicyTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login_admin()

    def _create_series_and_occurrence(self, visibility="private"):
        s = self.client.post(
            "/api/meetings/series",
            json={"title": "Policy Series", "topic_id": 1, "visibility": visibility},
        )
        self.assertEqual(s.status_code, 201)
        series_id = s.get_json()["data"]["mtg_id"]
        o = self.client.post(
            f"/api/meetings/series/{series_id}/occurrences",
            json={"date": "2026-03-20", "visibility": visibility},
        )
        self.assertEqual(o.status_code, 201)
        return series_id, o.get_json()["data"]["min_id"]

    def test_private_occurrence_participants_endpoint_hidden_for_non_participant(self):
        _, occurrence_id = self._create_series_and_occurrence("private")
        self.login_user()
        resp = self.client.get(f"/api/meetings/{occurrence_id}/participants")
        self.assertEqual(resp.status_code, 404)

    def test_public_occurrence_participants_endpoint_hidden_for_non_participant(self):
        _, occurrence_id = self._create_series_and_occurrence("public")
        self.login_user()
        resp = self.client.get(f"/api/meetings/{occurrence_id}/participants")
        self.assertEqual(resp.status_code, 404)

    def test_public_occurrence_detail_hidden_for_non_participant(self):
        _, occurrence_id = self._create_series_and_occurrence("public")
        self.login_user()
        resp = self.client.get(f"/api/meetings/{occurrence_id}")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["error"]["code"], "FORBIDDEN")

    def test_occurrence_detail_visible_for_owner_even_if_not_participant(self):
        _, occurrence_id = self._create_series_and_occurrence("private")
        db = self.get_db()
        admin_row = db.execute("SELECT usr_id FROM t_user WHERE usr_username = ?", ("admin",)).fetchone()
        admin_id = int(admin_row["usr_id"])
        user_row = db.execute("SELECT usr_id FROM t_user WHERE usr_username = ?", ("user1",)).fetchone()
        user_id = int(user_row["usr_id"])

        set_owner_resp = self.client.put(
            f"/api/meetings/{occurrence_id}/owners",
            json={"user_ids": [admin_id, user_id]},
        )
        self.assertEqual(set_owner_resp.status_code, 200)

        db.execute(
            "DELETE FROM t_meeting_participant WHERE mpa_instance_id = ? AND mpa_user_id = ?",
            (occurrence_id, user_id),
        )
        db.commit()

        self.login_user()
        resp = self.client.get(f"/api/meetings/{occurrence_id}")
        self.assertEqual(resp.status_code, 200)

    def test_occurrence_participant_add_must_belong_to_series_default_participants(self):
        series_id, occurrence_id = self._create_series_and_occurrence("private")
        # Keep series default participants as-is (admin only). Attempt to add user1 should fail.
        _ = series_id
        resp = self.client.post(f"/api/meetings/{occurrence_id}/participants", json={"user_id": 2})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("series participant", resp.get_json()["error"]["message"])

    def test_occurrence_meeting_creator_cannot_be_removed_from_participants(self):
        _, occurrence_id = self._create_series_and_occurrence("private")
        resp = self.client.delete(f"/api/meetings/{occurrence_id}/participants/1")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("creator", resp.get_json()["error"]["message"].lower())


if __name__ == "__main__":
    unittest.main()
