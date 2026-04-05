from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.server import AppContext, create_handler
from http.server import ThreadingHTTPServer


class FinanceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(cls.temp_dir.name) / "test-finance.db"
        cls.context = AppContext(database_path=database_path)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(cls.context))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.context.close()
        cls.temp_dir.cleanup()

    def request(self, method: str, path: str, *, token: str | None = None, body: dict | None = None):
        url = f"http://127.0.0.1:{self.port}{path}"
        headers = {}
        data = None
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        request = Request(url, method=method, headers=headers, data=data)
        try:
            with urlopen(request) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))

    def test_health_check(self) -> None:
        status, payload = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_openapi_document_is_available(self) -> None:
        status, payload = self.request("GET", "/openapi.json")
        self.assertEqual(status, 200)
        self.assertEqual(payload["openapi"], "3.0.3")

    def test_viewer_can_read_dashboard_but_not_records(self) -> None:
        status, payload = self.request("GET", "/dashboard/summary", token="viewer-token")
        self.assertEqual(status, 200)
        self.assertIn("total_income", payload["data"])

        status, payload = self.request("GET", "/records", token="viewer-token")
        self.assertEqual(status, 403)
        self.assertIn("error", payload)

    def test_analyst_can_read_records(self) -> None:
        status, payload = self.request(
            "GET",
            "/records?type=income&limit=2&sort_by=amount&sort_direction=asc",
            token="analyst-token",
        )
        self.assertEqual(status, 200)
        self.assertLessEqual(payload["meta"]["count"], 2)
        self.assertGreaterEqual(payload["meta"]["total"], payload["meta"]["count"])
        self.assertEqual(payload["meta"]["sort_by"], "amount")
        self.assertEqual(payload["meta"]["sort_direction"], "asc")
        amounts = [record["amount"] for record in payload["data"]]
        self.assertEqual(amounts, sorted(amounts))
        for record in payload["data"]:
            self.assertEqual(record["type"], "income")

    def test_admin_can_create_and_update_user(self) -> None:
        create_status, create_payload = self.request(
            "POST",
            "/users",
            token="admin-token",
            body={"name": "Ops Manager", "email": "ops@finance.local", "role": "analyst", "status": "active"},
        )
        self.assertEqual(create_status, 201)
        user_id = create_payload["data"]["id"]

        update_status, update_payload = self.request(
            "PATCH",
            f"/users/{user_id}",
            token="admin-token",
            body={"role": "viewer"},
        )
        self.assertEqual(update_status, 200)
        self.assertEqual(update_payload["data"]["role"], "viewer")

        detail_status, detail_payload = self.request("GET", f"/users/{user_id}", token="admin-token")
        self.assertEqual(detail_status, 200)
        self.assertEqual(detail_payload["data"]["id"], user_id)

    def test_admin_can_create_update_and_delete_record(self) -> None:
        create_status, create_payload = self.request(
            "POST",
            "/records",
            token="admin-token",
            body={
                "amount": 2500,
                "type": "expense",
                "category": "Marketing",
                "record_date": "2026-04-01",
                "notes": "Campaign spend",
            },
        )
        self.assertEqual(create_status, 201)
        record_id = create_payload["data"]["id"]

        detail_status, detail_payload = self.request("GET", f"/records/{record_id}", token="analyst-token")
        self.assertEqual(detail_status, 200)
        self.assertEqual(detail_payload["data"]["created_by_name"], "Admin User")

        update_status, update_payload = self.request(
            "PATCH",
            f"/records/{record_id}",
            token="admin-token",
            body={"amount": 2300, "notes": "Adjusted campaign spend"},
        )
        self.assertEqual(update_status, 200)
        self.assertEqual(update_payload["data"]["amount"], 2300.0)
        self.assertEqual(update_payload["data"]["updated_by_name"], "Admin User")

        delete_status, _ = self.request("DELETE", f"/records/{record_id}", token="admin-token")
        self.assertEqual(delete_status, 200)

        missing_status, _ = self.request("GET", f"/records/{record_id}", token="analyst-token")
        self.assertEqual(missing_status, 404)

    def test_rejects_invalid_record_payload(self) -> None:
        status, payload = self.request(
            "POST",
            "/records",
            token="admin-token",
            body={"amount": -10, "type": "income", "category": "Bonus", "record_date": "2026-04-01"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_rejects_invalid_sort_and_inactive_user(self) -> None:
        status, payload = self.request("GET", "/records?sort_by=bogus", token="analyst-token")
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

        inactive_status, inactive_payload = self.request("GET", "/dashboard/summary", token="inactive-token")
        self.assertEqual(inactive_status, 403)
        self.assertIn("error", inactive_payload)


if __name__ == "__main__":
    unittest.main()
