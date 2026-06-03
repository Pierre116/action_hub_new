from io import BytesIO

from openpyxl import Workbook

from tests.conftest import AppTestCase


class ImportTests(AppTestCase):
    def test_preview_execute_and_rollback(self):
        self.login_admin()

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Action Log"
        sheet.append(["Title", "Owner", "Team", "Priority", "Status", "Deadline", "Description"])
        sheet.append(["Import row one", "admin", "FAC", "High", "Open", "2026-03-10", "Desc one"])
        sheet.append(["Import row two", "admin", "QA", "Critical", "In Progress", "2026-03-11", "Desc two"])

        stream = BytesIO()
        workbook.save(stream)
        stream.seek(0)

        preview = self.client.post(
            "/api/import/preview",
            data={"file": (stream, "test_import.xlsx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(preview.status_code, 200)
        token = preview.get_json()["data"]["token"]

        execute = self.client.post(
            "/api/import/execute",
            json={"token": token, "owner_map": {}, "team_map": {}, "skip_duplicates": True},
        )
        self.assertEqual(execute.status_code, 200)
        import_log_id = execute.get_json()["data"]["import_log_id"]

        history = self.client.get("/api/import/history")
        self.assertEqual(history.status_code, 200)
        self.assertGreaterEqual(len(history.get_json()["data"]), 1)

        rollback = self.client.delete(f"/api/import/{import_log_id}")
        self.assertEqual(rollback.status_code, 200)
        self.assertEqual(rollback.get_json()["data"]["status"], "Rolled Back")

