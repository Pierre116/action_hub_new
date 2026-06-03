from tests.conftest import AppTestCase


# ── helpers ────────────────────────────────────────────────────────────────

def _make_meeting(client, topic_id=1, title="Test Meeting"):
    resp = client.post("/api/meetings", json={"title": title, "topic_id": topic_id})
    return resp.get_json()["data"]["min_id"]


class DashboardTests(AppTestCase):
    def test_personal_and_team_dashboard(self):
        self.login_admin()
        created = self.client.post(
            "/api/actions",
            json={
                "title": "Dashboard action",
                "topic_id": 1,
                "priority": "Medium",
                "deadline": "2026-03-09",
            },
        )
        self.assertEqual(created.status_code, 201)

        personal = self.client.get("/api/dashboard/personal")
        self.assertEqual(personal.status_code, 200)
        self.assertIn("kpis", personal.get_json()["data"])

        team = self.client.get("/api/dashboard/team?team_id=1")
        self.assertEqual(team.status_code, 200)
        data = team.get_json()["data"]
        self.assertIn("status_distribution", data)
        self.assertIn("priority_distribution", data)

    def test_topic_dashboard(self):
        self.login_admin()
        self.client.post(
            "/api/actions",
            json={
                "title": "Topic dashboard action",
                "topic_id": 1,
                "priority": "High",
                "deadline": "2026-03-09",
            },
        )

        resp = self.client.get("/api/dashboard/topic?topic_id=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIn("kpis", data)
        self.assertIn("topic", data)
        kpis = data["kpis"]
        self.assertIn("open", kpis)
        self.assertIn("done", kpis)
        self.assertIn("overdue", kpis)
        self.assertIn("total", kpis)

    def test_topic_dashboard_not_found(self):
        self.login_admin()
        resp = self.client.get("/api/dashboard/topic?topic_id=99999")
        self.assertEqual(resp.status_code, 404)

    def test_topic_dashboard_missing_param(self):
        self.login_admin()
        resp = self.client.get("/api/dashboard/topic")
        self.assertEqual(resp.status_code, 400)


# ── extended dashboard topic tests (from wave3) ─────────────────────────────

class DashboardTopicTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login_admin()

    def test_topics_summary_ok(self):
        resp = self.client.get("/api/dashboard/topics/summary")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    def test_topics_summary_unauthenticated(self):
        with self.app.test_client() as fresh:
            resp = fresh.get("/api/dashboard/topics/summary")
        self.assertEqual(resp.status_code, 401)

    def test_topic_dashboard_ok(self):
        resp = self.client.get("/api/dashboard/topic?topic_id=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIn("kpis", data)
        self.assertIn("topic", data)

    def test_topic_dashboard_missing_topic_id(self):
        resp = self.client.get("/api/dashboard/topic")
        self.assertEqual(resp.status_code, 400)

    def test_topic_dashboard_not_found(self):
        resp = self.client.get("/api/dashboard/topic?topic_id=99999")
        self.assertEqual(resp.status_code, 404)

    def test_personal_dashboard_ok(self):
        resp = self.client.get("/api/dashboard/personal")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("data", resp.get_json())

    def test_Team_dashboard_ok(self):
        resp = self.client.get("/api/dashboard/team?team_id=1")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("data", resp.get_json())

    def test_Teams_summary_ok(self):
        resp = self.client.get("/api/dashboard/teams/summary")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json()["data"], list)

    def test_team_dashboard_excludes_private_meeting_series_actions(self):
        """Team dashboard must not count actions tied to private meetings/series."""
        self.login_admin()
        db = self.get_db()

        baseline_resp = self.client.get("/api/dashboard/team?team_id=1")
        self.assertEqual(baseline_resp.status_code, 200)
        baseline_total = baseline_resp.get_json()["data"]["kpis"]["total"]

        # Public non-meeting action (should be counted by team dashboard).
        db.execute(
            """
            INSERT INTO t_action
                (act_id, act_ref, act_title, act_desc, act_topic_id, act_created_by,
                 act_status, act_priority, act_deadline, act_meeting_inst_id, act_archived)
            VALUES
                (9001, 'ACT-009001', 'Public Baseline Action', 'A', 1, 1,
                 'Open', 'Medium', date('now','+2 day'), NULL, 0)
            """
        )

        # Private series + private instance + action (must be excluded)
        db.execute("INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by, mtg_topic_id, mtg_visibility) VALUES (9002, 'Private Series', 1, 1, 'private')")
        db.execute("INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by, min_visibility) VALUES (9002, 9002, 'Private Instance', 1, 1, 'private')")
        db.execute(
            """
            INSERT INTO t_action
                (act_id, act_ref, act_title, act_desc, act_topic_id, act_created_by,
                 act_status, act_priority, act_deadline, act_meeting_inst_id, act_archived)
            VALUES
                (9003, 'ACT-009003', 'Private Action', 'B', 1, 1,
                 'Open', 'Medium', date('now','+2 day'), 9002, 0)
            """
        )
        db.commit()

        resp = self.client.get("/api/dashboard/team?team_id=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]

        # Private action must not affect totals; public baseline action should.
        self.assertEqual(data["kpis"]["total"], baseline_total + 1)
        titles = {row["act_title"] for row in data["all_actions"]}
        self.assertIn("Public Baseline Action", titles)
        self.assertNotIn("Private Action", titles)

    def test_decisions_dashboard_personal_ok(self):
        resp = self.client.get("/api/dashboard/decisions?scope=personal")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIn("kpis", data)
        self.assertIn("recent", data)

    def test_decisions_dashboard_team_ok(self):
        resp = self.client.get("/api/dashboard/decisions?scope=team&team_id=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIn("kpis", data)
        self.assertIn("recent", data)

    def test_decisions_dashboard_team_forbidden_for_non_team_lead(self):
        self.login_user()
        resp = self.client.get("/api/dashboard/decisions?scope=team&team_id=1")
        self.assertEqual(resp.status_code, 403)

    def test_decisions_dashboard_team_uses_team_lead_scope(self):
        db = self.get_db()
        db.execute("UPDATE t_team SET tea_leader_user_id = 2 WHERE tea_id = 1")
        db.execute(
            "INSERT OR IGNORE INTO t_team (tea_id, tea_code, tea_name_en, tea_name_cn, tea_active) VALUES (99, 'T99', 'Team 99', 'Team 99', 1)"
        )
        db.execute("UPDATE t_team SET tea_leader_user_id = 1 WHERE tea_id = 99")
        db.commit()

        self.login_user()
        allowed = self.client.get("/api/dashboard/decisions?scope=team&team_id=1")
        self.assertEqual(allowed.status_code, 200)

        forbidden = self.client.get("/api/dashboard/decisions?scope=team&team_id=99")
        self.assertEqual(forbidden.status_code, 403)

    def test_decisions_dashboard_topic_ok(self):
        resp = self.client.get("/api/dashboard/decisions?scope=topic&topic_id=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIn("kpis", data)
        self.assertIn("recent", data)

    def test_decisions_dashboard_topic_missing_param(self):
        resp = self.client.get("/api/dashboard/decisions?scope=topic")
        self.assertEqual(resp.status_code, 400)

    def test_decisions_dashboard_recent_includes_owner_and_related_meeting(self):
        db = self.get_db()
        db.execute(
            """
            INSERT INTO t_meeting_decision (mdc_title, mdc_body, mdc_status, mdc_meeting_id, mdc_created_by)
            VALUES (?, ?, 'Proposed', ?, ?)
            """,
            ("Decision Owner Visible", "Ensure owner and meeting are returned", 1, 1),
        )
        db.commit()

        resp = self.client.get("/api/dashboard/decisions?scope=all&limit=10")
        self.assertEqual(resp.status_code, 200)
        recent = resp.get_json()["data"]["recent"]
        target = next((row for row in recent if row.get("mdc_title") == "Decision Owner Visible"), None)
        self.assertIsNotNone(target)
        self.assertTrue(target.get("creator_name"))
        self.assertIn("series_title", target)

    def test_decisions_dashboard_unauthenticated(self):
        with self.app.test_client() as fresh:
            resp = fresh.get("/api/dashboard/decisions?scope=personal")
        self.assertEqual(resp.status_code, 401)

    def test_personal_dashboard_is_self_only_and_creator_owned(self):
        db = self.get_db()
        db.execute(
            """
            INSERT INTO t_action
                (act_id, act_ref, act_title, act_desc, act_topic_id, act_created_by,
                 act_status, act_priority, act_deadline, act_archived)
            VALUES
                (9101, 'ACT-009101', 'Admin Owned Action', 'A', 1, 1,
                 'Open', 'Medium', date('now','+2 day'), 0)
            """
        )
        db.execute(
            """
            INSERT INTO t_action
                (act_id, act_ref, act_title, act_desc, act_topic_id, act_created_by,
                 act_status, act_priority, act_deadline, act_archived)
            VALUES
                (9102, 'ACT-009102', 'User Owned Action', 'B', 1, 2,
                 'Open', 'Medium', date('now','+2 day'), 0)
            """
        )
        db.commit()

        self.login_admin()
        baseline = self.client.get("/api/dashboard/personal")
        self.assertEqual(baseline.status_code, 200)
        baseline_refs = {row["act_ref"] for row in baseline.get_json()["data"].get("all_actions", [])}
        self.assertIn("ACT-009101", baseline_refs)
        self.assertNotIn("ACT-009102", baseline_refs)

        switched = self.client.get("/api/dashboard/personal?user_id=2")
        self.assertEqual(switched.status_code, 200)
        switched_refs = {row["act_ref"] for row in switched.get_json()["data"].get("all_actions", [])}
        self.assertIn("ACT-009101", switched_refs)
        self.assertNotIn("ACT-009102", switched_refs)

    def test_team_leader_dashboard_masks_private_actions_when_not_participant(self):
        db = self.get_db()

        db.execute("UPDATE t_team SET tea_leader_user_id = 2 WHERE tea_id = 1")
        db.execute("UPDATE t_user SET usr_team_id = 1 WHERE usr_id = 1")
        db.execute(
            "INSERT OR IGNORE INTO t_user_team (utm_user_id, utm_team_id) VALUES (1, 1)"
        )

        db.execute(
            "INSERT INTO t_meeting (mtg_id, mtg_title, mtg_created_by, mtg_topic_id, mtg_visibility) VALUES (9103, 'Leader Private Series', 1, 1, 'private')"
        )
        db.execute(
            "INSERT INTO t_meeting_instance (min_id, min_meeting_id, min_title, min_topic_id, min_created_by, min_visibility) VALUES (9103, 9103, 'Leader Private Instance', 1, 1, 'private')"
        )
        db.execute(
            """
            INSERT INTO t_action
                (act_id, act_ref, act_title, act_desc, act_topic_id, act_created_by,
                 act_status, act_priority, act_deadline, act_meeting_inst_id, act_archived)
            VALUES
                (9104, 'ACT-009104', 'Secret Action', 'Secret Description', 1, 1,
                 'Open', 'Medium', date('now','+2 day'), 9103, 0)
            """
        )
        db.commit()

        self.login_user()
        resp = self.client.get("/api/dashboard/team-lead?team_id=1")
        self.assertEqual(resp.status_code, 200)
        actions = resp.get_json()["data"].get("all_actions", [])
        target = next((row for row in actions if row.get("act_ref") == "ACT-009104"), None)
        self.assertIsNotNone(target)
        self.assertTrue(target.get("is_masked_private"))
        self.assertEqual(target.get("meeting_series_title"), "Leader Private Series")
        self.assertEqual(target.get("act_title"), "Private action")

    def test_team_leader_dashboard_filters_out_cross_team_non_lead_assignment_actions(self):
        """With Lead-only roles, any assignment is 'Lead'.
        A cross-team action where the team-1 user is assigned (Lead)
        SHOULD appear in the Team 1 dashboard because the user is a Lead."""
        db = self.get_db()

        # user1 becomes Team 1 leader; user2 belongs to Team 2.
        db.execute("UPDATE t_team SET tea_leader_user_id = 1 WHERE tea_id = 1")
        db.execute("UPDATE t_user SET usr_team_id = 1 WHERE usr_id = 1")
        db.execute("UPDATE t_user SET usr_team_id = 2 WHERE usr_id = 2")
        db.execute("INSERT OR IGNORE INTO t_user_team (utm_user_id, utm_team_id) VALUES (1, 1)")
        db.execute("INSERT OR IGNORE INTO t_user_team (utm_user_id, utm_team_id) VALUES (2, 2)")

        # Cross-team action: created by Team 2 user, with Team 1 user as Lead assignee.
        db.execute(
            """
            INSERT INTO t_action
                (act_id, act_ref, act_title, act_desc, act_topic_id, act_created_by,
                 act_status, act_priority, act_deadline, act_archived)
            VALUES
                (9201, 'ACT-009201', 'Cross Team Assignment Leak', 'Should appear because user is Lead', 1, 2,
                 'Open', 'Medium', date('now','-1 day'), 0)
            """
        )
        db.execute(
            """
            INSERT INTO t_assignment (asg_action_id, asg_user_id, asg_role, asg_assigned_by)
            VALUES (9201, 1, 'Lead', 2)
            """
        )
        db.commit()

        self.login_admin()
        resp = self.client.get("/api/dashboard/team-lead?team_id=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]

        # User 1 is Lead on this action, so it appears in team dashboard
        refs = {row.get("act_ref") for row in data.get("all_actions", [])}
        self.assertIn("ACT-009201", refs)
