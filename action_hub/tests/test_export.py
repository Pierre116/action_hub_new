from tests.conftest import AppTestCase


class ExportTests(AppTestCase):
    def test_export_actions_excel(self):
        self.login_admin()

        created = self.client.post(
            "/api/actions",
            json={
                "title": "Export action sample",
                "team_id": 1,
                "topic_id": 1,
                "priority": "Low",
                "deadline": "2026-03-12",
            },
        )
        self.assertEqual(created.status_code, 201)

        exported = self.client.get("/api/export/actions")
        self.assertEqual(exported.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            exported.headers.get("Content-Type", ""),
        )
        self.assertGreater(len(exported.data), 100)

