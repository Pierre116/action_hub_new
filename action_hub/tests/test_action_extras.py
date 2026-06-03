"""Tests for action sub-features: comments, sub-actions, assignments, archive, and core CRUD."""
import unittest

from tests.conftest import AppTestCase


# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# Helpers
# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

def _create_action(client, title="Test Action", team_id=1, topic_id=1, priority="Medium", deadline="2026-12-31"):
    resp = client.post(
        "/api/actions",
        json={"title": title, "team_id": team_id,
              "topic_id": topic_id, "priority": priority, "deadline": deadline},
    )
    assert resp.status_code == 201, f"action create failed: {resp.get_json()}"
    return resp.get_json()["data"]["action"]["act_id"]



# ── core action CRUD & transitions (from test_actions.py) ────────────────────

class ActionCRUDTests(AppTestCase):
    """Create, update, status transition, assignment, and filtered list."""

    def test_create_update_transition_assign(self):
        self.login_admin()

        created = self.client.post(
            "/api/actions",
            json={
                "title": "Action test create",
                "description": "Phase 5 test",
                "tags": "urgent, line3",
                "team_id": 1,
                "topic_id": 1,
                "priority": "High",
                "deadline": "2026-03-08",
            },
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.get_json()["data"]["action"]["act_tags"], "URGENT, LINE3")

    def test_actions_list_search_by_tags(self):
        self.login_admin()

        response = self.client.post(
            "/api/actions",
            json={
                "title": "Machine tracked action",
                "description": "Searchable by serial",
                "tags": "mc8800, tracked",
                "team_id": 1,
                "topic_id": 1,
                "priority": "Medium",
                "deadline": "2026-12-31",
            },
        )
        self.assertEqual(response.status_code, 201)

        search_response = self.client.get("/api/actions?search=MC8800")
        self.assertEqual(search_response.status_code, 200)
        self.assertTrue(any(item["act_tags"] == "MC8800, TRACKED" for item in search_response.get_json()["data"]["items"]))


class ActionWorkflowManualStartTests(AppTestCase):
    """Bound action templates do not auto-start when matching actions are created."""

    def setUp(self):
        super().setUp()
        self.login_admin()

    def _insert_bound_template(self, template_id, bindings):
        db = self.get_db()
        graph = {
            "steps": {
                "start": {"type": "Task", "order": 1, "role": "TeamLead", "fields": []},
                "end": {"type": "End", "order": 2, "fields": []},
            },
            "transitions": [
                {"from": "start", "to": "end"},
            ],
            "bindings": bindings,
        }
        db.execute(
            """INSERT INTO t_workflow_template
               (wft_id, wft_name_en, wft_name_cn, wft_graph, wft_type, wft_active,
                wft_created_by, wft_created_at, wft_updated_at)
               VALUES (?, ?, ?, ?, 'action', 1, 1, datetime('now'), datetime('now'))""",
            (template_id, f"Template {template_id}", f"Template {template_id}", self.json_dumps(graph)),
        )
        db.commit()

    def test_create_action_does_not_auto_start_team_bound_workflow(self):
        self._insert_bound_template(9101, [{"scope_type": "team", "scope_id": 1}])

        resp = self.client.post(
            "/api/actions",
            json={
                "title": "Team bound action",
                "team_id": 1,
                "topic_id": 1,
                "priority": "Medium",
                "deadline": "2026-12-31",
            },
        )

        self.assertEqual(resp.status_code, 201)
        action_id = resp.get_json()["data"]["action"]["act_id"]

        db = self.get_db()
        row = db.execute(
            "SELECT wfi_template_id FROM t_workflow_instance WHERE wfi_action_id = ?",
            (action_id,),
        ).fetchone()
        self.assertIsNone(row)

    def test_create_action_does_not_auto_start_action_type_bound_workflow(self):
        self._insert_bound_template(9102, [{"scope_type": "category", "scope_id": 1}])

        resp = self.client.post(
            "/api/actions",
            json={
                "title": "Category bound action",
                "team_id": 1,
                "topic_id": 1,
                "category_id": 1,
                "priority": "Medium",
                "deadline": "2026-12-31",
            },
        )

        self.assertEqual(resp.status_code, 201)
        action_id = resp.get_json()["data"]["action"]["act_id"]

        db = self.get_db()
        row = db.execute(
            "SELECT wfi_template_id FROM t_workflow_instance WHERE wfi_action_id = ?",
            (action_id,),
        ).fetchone()
        self.assertIsNone(row)


# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# Comments
# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

class CommentTests(AppTestCase):
    """Tests for GET/POST /api/actions/<id>/comments and PATCH/DELETE /api/actions/comments/<id>."""

    def setUp(self):
        super().setUp()
        self.login_admin()
        self.action_id = _create_action(self.client)

    # list (empty)
    def test_list_comments_empty(self):
        resp = self.client.get(f"/api/actions/{self.action_id}/comments")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    # create 鈥?valid
    def test_create_comment_ok(self):
        resp = self.client.post(
            f"/api/actions/{self.action_id}/comments",
            json={"body": "First comment", "type": "Comment"},
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()["data"]
        self.assertEqual(data["cmt_body"], "First comment")
        self.assertEqual(data["cmt_type"], "Comment")

    def test_create_achievement_ok(self):
        resp = self.client.post(
            f"/api/actions/{self.action_id}/comments",
            json={"body": "Hit the milestone!", "type": "Achievement"},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["data"]["cmt_type"], "Achievement")

    def test_create_roadblock_ok(self):
        resp = self.client.post(
            f"/api/actions/{self.action_id}/comments",
            json={"body": "Blocked by procurement", "type": "Roadblock"},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["data"]["cmt_type"], "Roadblock")

    # validation
    def test_create_comment_empty_body(self):
        resp = self.client.post(
            f"/api/actions/{self.action_id}/comments",
            json={"body": "", "type": "Comment"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_comment_invalid_type(self):
        resp = self.client.post(
            f"/api/actions/{self.action_id}/comments",
            json={"body": "hello", "type": "Note"},
        )
        self.assertEqual(resp.status_code, 400)

    # list after create
    def test_list_comments_after_create(self):
        self.client.post(
            f"/api/actions/{self.action_id}/comments",
            json={"body": "Listed comment", "type": "Comment"},
        )
        resp = self.client.get(f"/api/actions/{self.action_id}/comments")
        self.assertEqual(resp.status_code, 200)
        bodies = [c["cmt_body"] for c in resp.get_json()["data"]]
        self.assertIn("Listed comment", bodies)

    # edit
    def test_edit_comment_ok(self):
        cmt_id = self.client.post(
            f"/api/actions/{self.action_id}/comments",
            json={"body": "Original", "type": "Comment"},
        ).get_json()["data"]["cmt_id"]
        resp = self.client.patch(f"/api/actions/comments/{cmt_id}",
                                  json={"body": "Edited"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["cmt_body"], "Edited")

    def test_edit_comment_not_found(self):
        resp = self.client.patch("/api/actions/comments/99999", json={"body": "X"})
        self.assertEqual(resp.status_code, 404)

    # delete
    def test_delete_comment_ok(self):
        cmt_id = self.client.post(
            f"/api/actions/{self.action_id}/comments",
            json={"body": "To Delete", "type": "Comment"},
        ).get_json()["data"]["cmt_id"]
        resp = self.client.delete(f"/api/actions/comments/{cmt_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["data"]["deleted"])

    def test_delete_comment_not_found(self):
        resp = self.client.delete("/api/actions/comments/99999")
        self.assertEqual(resp.status_code, 404)

    # unauthenticated
    def test_comments_unauthenticated(self):
        with self.app.test_client() as fresh:
            resp = fresh.get(f"/api/actions/{self.action_id}/comments")
        self.assertEqual(resp.status_code, 401)


# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# Assignments (pending / respond / history)
# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

class AssignmentLifecycleTests(AppTestCase):
    """Tests for assignment creation, removal, and history."""

    def setUp(self):
        super().setUp()
        self.login_admin()
        self.action_id = _create_action(self.client, title="Assignment Lifecycle")

    def _assign(self, user_id=1, role="Lead"):
        return self.client.post(
            f"/api/actions/{self.action_id}/assign",
            json={"user_id": user_id, "role": role},
        )

    def test_assignment_history_empty(self):
        resp = self.client.get(f"/api/actions/{self.action_id}/assignment-history")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    def test_assignment_history_after_assign(self):
        self._assign(user_id=1, role="Lead")
        resp = self.client.get(f"/api/actions/{self.action_id}/assignment-history")
        self.assertEqual(resp.status_code, 200)
        events = [r["ash_event"] for r in resp.get_json()["data"]]
        self.assertIn("Assigned", events)

    def test_remove_assignment_ok(self):
        # Verify that removing the only Lead assignment is properly blocked.
        asg_id = self._assign(user_id=1, role="Lead").get_json()["data"]["asg_id"]
        resp = self.client.delete(f"/api/actions/{self.action_id}/assign/{asg_id}")
        # Cannot remove the only Lead assignment — expect 400
        self.assertEqual(resp.status_code, 400)
        self.assertIn("last Lead", resp.get_json()["error"]["message"])

    def test_remove_assignment_not_found(self):
        resp = self.client.delete(f"/api/actions/{self.action_id}/assign/99999")
        self.assertEqual(resp.status_code, 404)

    def test_action_meetings_linked(self):
        resp = self.client.get(f"/api/actions/{self.action_id}/meetings")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)


# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# Action detail & archive
# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

class ActionDetailTests(AppTestCase):
    """Tests for action detail and admin-only archive (soft-delete)."""

    def setUp(self):
        super().setUp()
        self.login_admin()
        self.action_id = _create_action(self.client, title="Archive-able Action")

    def test_action_detail_ok(self):
        resp = self.client.get(f"/api/actions/{self.action_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIn("action", data)
        self.assertEqual(data["action"]["act_id"], self.action_id)

    def test_action_detail_not_found(self):
        resp = self.client.get("/api/actions/99999")
        self.assertEqual(resp.status_code, 404)

    def test_actions_list_search(self):
        _create_action(self.client, title="UniqueSearchable99 Action")
        resp = self.client.get("/api/actions?search=UniqueSearchable99")
        self.assertEqual(resp.status_code, 200)
        total = resp.get_json()["data"]["pagination"]["total"]
        self.assertGreaterEqual(total, 1)

    def test_actions_list_pagination(self):
        resp = self.client.get("/api/actions?page=1&per_page=5")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()["data"]
        self.assertIn("pagination", body)
        self.assertIn("items", body)

    def test_actions_list_category_filter_matches_primary_or_secondary(self):
        db = self.get_db()
        topics = db.execute(
            "SELECT top_id, top_code FROM t_topic WHERE top_active = 1 ORDER BY top_id ASC LIMIT 2"
        ).fetchall()
        self.assertGreaterEqual(len(topics), 1)

        primary_topic = int(topics[0]["top_id"])
        secondary_topic = int(topics[1]["top_id"]) if len(topics) > 1 else primary_topic

        primary_action_id = _create_action(self.client, title="Primary Category Action", topic_id=primary_topic)
        secondary_action_id = _create_action(self.client, title="Secondary Category Action", topic_id=secondary_topic)

        if secondary_topic != primary_topic:
            db.execute(
                "UPDATE t_action SET act_secondary_topic_id = ? WHERE act_id = ?",
                (primary_topic, secondary_action_id),
            )
            db.commit()

        resp = self.client.get(f"/api/actions?topic_id={primary_topic}")
        self.assertEqual(resp.status_code, 200)
        items = resp.get_json()["data"]["items"]
        returned_ids = {item["act_id"] for item in items}
        self.assertIn(primary_action_id, returned_ids)
        self.assertIn(secondary_action_id, returned_ids)

        if topics[0]["top_code"]:
            resp_by_code = self.client.get(f"/api/actions?topic_code={topics[0]['top_code']}")
            self.assertEqual(resp_by_code.status_code, 200)
            returned_ids_by_code = {item["act_id"] for item in resp_by_code.get_json()["data"]["items"]}
            self.assertIn(primary_action_id, returned_ids_by_code)

    def test_action_update_description(self):
        resp = self.client.patch(
            f"/api/actions/{self.action_id}",
            json={"description": "Updated description"},
        )
        self.assertEqual(resp.status_code, 200)

    def test_action_update_not_found(self):
        resp = self.client.patch("/api/actions/99999", json={"description": "X"})
        self.assertEqual(resp.status_code, 404)

    def test_archive_action_ok(self):
        aid = _create_action(self.client, title="Archive Target")
        resp = self.client.delete(f"/api/actions/{aid}")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["data"]["archived"])

    def test_archive_action_not_found(self):
        resp = self.client.delete("/api/actions/99999")
        self.assertEqual(resp.status_code, 404)


class ActionFeedbackTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login_admin()
        self.action_id = _create_action(self.client, title="Progress Feedback Action")

    def test_submit_feedback_recreates_missing_table(self):
        db = self.get_db()
        db.execute("DROP TABLE IF EXISTS t_action_feedback")
        db.commit()

        response = self.client.post(
            f"/api/actions/{self.action_id}/feedback",
            json={
                "completion_pct": 40,
                "status": "on_track",
                "comment": "Initial progress",
                "blockers": "",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["data"]["afb_action_id"], self.action_id)

        recreated = db.execute(
            "SELECT COUNT(*) AS total FROM t_action_feedback WHERE afb_action_id = ?",
            (self.action_id,),
        ).fetchone()
        self.assertEqual(int(recreated["total"]), 1)

    def test_submit_feedback_carries_forward_blockers_when_blank(self):
        first = self.client.post(
            f"/api/actions/{self.action_id}/feedback",
            json={
                "completion_pct": 30,
                "status": "on_track",
                "comment": "Initial update",
                "blockers": "Need supplier response",
            },
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            f"/api/actions/{self.action_id}/feedback",
            json={
                "completion_pct": 40,
                "status": "on_track",
                "comment": "Follow-up update",
                "blockers": "",
            },
        )
        self.assertEqual(second.status_code, 201)

        latest = second.get_json()["data"]
        self.assertEqual(latest["afb_blockers"], "Need supplier response")

    def test_submit_feedback_syncs_action_status(self):
        response = self.client.post(
            f"/api/actions/{self.action_id}/feedback",
            json={
                "completion_pct": 55,
                "status": "late",
                "comment": "Blocked by dependency",
                "blockers": "Waiting for external API",
            },
        )
        self.assertEqual(response.status_code, 201)

        db = self.get_db()
        row = db.execute(
            "SELECT act_status FROM t_action WHERE act_id = ?",
            (self.action_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["act_status"], "On Hold")

    def test_submit_feedback_late_syncs_to_db_valid_action_status(self):
        response = self.client.post(
            f"/api/actions/{self.action_id}/feedback",
            json={
                "completion_pct": 60,
                "status": "late",
                "comment": "Risk identified",
                "blockers": "",
            },
        )
        self.assertEqual(response.status_code, 201)

        db = self.get_db()
        row = db.execute(
            "SELECT act_status FROM t_action WHERE act_id = ?",
            (self.action_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["act_status"], "On Hold")

    def test_latest_feedback_status_overwrites_action_status(self):
        first = self.client.post(
            f"/api/actions/{self.action_id}/feedback",
            json={
                "completion_pct": 20,
                "status": "on_track",
                "comment": "Work started",
                "blockers": "",
            },
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            f"/api/actions/{self.action_id}/feedback",
            json={
                "completion_pct": 100,
                "status": "done",
                "comment": "Completed",
                "blockers": "",
            },
        )
        self.assertEqual(second.status_code, 201)

        db = self.get_db()
        row = db.execute(
            "SELECT act_status FROM t_action WHERE act_id = ?",
            (self.action_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["act_status"], "Done")

    def test_non_owner_cannot_submit_feedback_for_non_meeting_action(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "user1", "password": "User@2026"},
        )
        self.assertEqual(response.status_code, 200)
        token = response.get_json()["data"]["access_token"]
        self.client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"

        forbidden = self.client.post(
            f"/api/actions/{self.action_id}/feedback",
            json={
                "completion_pct": 50,
                "status": "on_track",
                "comment": "I should not be allowed",
                "blockers": "",
            },
        )
        self.assertEqual(forbidden.status_code, 403)


class ActionListTeamLeaderVisibilityTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login_admin()
        db = self.get_db()
        admin = db.execute(
            "SELECT usr_id FROM t_user WHERE usr_username = ?",
            ("admin",),
        ).fetchone()
        leader = db.execute(
            "SELECT usr_id FROM t_user WHERE usr_username = ?",
            ("user1",),
        ).fetchone()
        self.assertIsNotNone(admin)
        self.assertIsNotNone(leader)

        self.admin_id = int(admin["usr_id"])
        self.leader_id = int(leader["usr_id"])

        db.execute("UPDATE t_team SET tea_leader_user_id = ? WHERE tea_id = 1", (self.leader_id,))
        db.execute("UPDATE t_user SET usr_team_id = 1 WHERE usr_id = ?", (self.admin_id,))
        db.execute(
            "INSERT OR IGNORE INTO t_user_team (utm_user_id, utm_team_id) VALUES (?, ?)",
            (self.admin_id, 1),
        )
        db.commit()

    def _login_team_leader(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "user1", "password": "User@2026"},
        )
        self.assertEqual(response.status_code, 200)
        token = response.get_json()["data"]["access_token"]
        self.client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    def test_team_leader_sees_public_team_action_in_actions_list(self):
        action_id = _create_action(self.client, title="Leader Team Visible")

        self._login_team_leader()
        response = self.client.get("/api/actions?search=Leader%20Team%20Visible")

        self.assertEqual(response.status_code, 200)
        returned_ids = {item["act_id"] for item in response.get_json()["data"]["items"]}
        self.assertIn(action_id, returned_ids)

    def test_team_leader_sees_private_meeting_action_as_masked_metadata(self):
        action_id = _create_action(self.client, title="Leader Team Private")
        db = self.get_db()
        db.execute(
            "INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by, mtg_topic_id, mtg_visibility) VALUES (9201, 'Leader Private Series', ?, 1, 'private')",
            (self.admin_id,),
        )
        db.execute(
            "INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by, min_visibility) VALUES (9201, 9201, 'Leader Private Instance', 1, ?, 'private')",
            (self.admin_id,),
        )
        db.execute(
            "UPDATE t_action SET act_visibility = 'private', act_meeting_inst_id = 9201 WHERE act_id = ?",
            (action_id,),
        )
        db.commit()

        self._login_team_leader()
        response = self.client.get("/api/actions?search=Leader%20Team%20Private")

        self.assertEqual(response.status_code, 200)
        rows = [item for item in response.get_json()["data"]["items"] if item["act_id"] == action_id]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row.get("is_masked_private"))
        self.assertEqual(row.get("act_title"), "Private action")
        self.assertEqual(row.get("meeting_title"), "Leader Private Instance")
        self.assertIsNotNone(row.get("owner_name"))
        self.assertIsNotNone(row.get("act_deadline"))


if __name__ == "__main__":
    unittest.main()

