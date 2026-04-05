from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.auth import ensure_active_user, extract_bearer_token, require_permission
from app.config import settings
from app.database import get_connection, initialize_database
from app.docs import build_openapi_spec
from app.errors import ApiError, NotFoundError, ValidationError
from app.repositories import RecordRepository, UserRepository
from app.services import RecordService, UserService


class AppContext:
    def __init__(self, database_path=settings.database_path) -> None:
        self.connection = get_connection(database_path)
        initialize_database(self.connection)
        self.user_service = UserService(UserRepository(self.connection))
        self.record_service = RecordService(RecordRepository(self.connection))
        self.user_service.seed_defaults()
        admin = self.user_service.get_user_by_token("admin-token")
        if admin:
            self.record_service.seed_defaults(admin_user_id=admin["id"])

    def close(self) -> None:
        self.connection.close()


def create_handler(context: AppContext):
    class FinanceRequestHandler(BaseHTTPRequestHandler):
        server_version = "FinanceBackend/1.0"

        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_POST(self) -> None:
            self._dispatch("POST")

        def do_PATCH(self) -> None:
            self._dispatch("PATCH")

        def do_DELETE(self) -> None:
            self._dispatch("DELETE")

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _dispatch(self, method: str) -> None:
            try:
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/") or "/"

                if path == "/health" and method == "GET":
                    self._send_json(200, {"status": "ok"})
                    return

                if path == "/openapi.json" and method == "GET":
                    self._send_json(200, build_openapi_spec())
                    return

                if path == "/users" and method == "GET":
                    user = self._authenticate("users:manage")
                    self._send_json(200, {"data": context.user_service.list_users(), "meta": {"requested_by": user["email"]}})
                    return

                if path == "/users" and method == "POST":
                    self._authenticate("users:manage")
                    payload = self._read_json_body()
                    user = context.user_service.create_user(payload)
                    self._send_json(201, {"data": user})
                    return

                if path.startswith("/users/") and method == "GET":
                    self._authenticate("users:manage")
                    user_id = self._extract_id(path, "/users/")
                    user = context.user_service.get_user(user_id)
                    self._send_json(200, {"data": user})
                    return

                if path.startswith("/users/") and method == "PATCH":
                    self._authenticate("users:manage")
                    user_id = self._extract_id(path, "/users/")
                    payload = self._read_json_body()
                    user = context.user_service.update_user(user_id, payload)
                    self._send_json(200, {"data": user})
                    return

                if path == "/records" and method == "GET":
                    self._authenticate("records:read")
                    filters = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
                    result = context.record_service.list_records(filters)
                    self._send_json(200, result)
                    return

                if path == "/records" and method == "POST":
                    user = self._authenticate("records:write")
                    payload = self._read_json_body()
                    record = context.record_service.create_record(payload, created_by=user["id"])
                    self._send_json(201, {"data": record})
                    return

                if path.startswith("/records/") and method == "GET":
                    self._authenticate("records:read")
                    record_id = self._extract_id(path, "/records/")
                    record = context.record_service.get_record(record_id)
                    self._send_json(200, {"data": record})
                    return

                if path.startswith("/records/") and method == "PATCH":
                    user = self._authenticate("records:write")
                    record_id = self._extract_id(path, "/records/")
                    payload = self._read_json_body()
                    record = context.record_service.update_record(record_id, payload, updated_by=user["id"])
                    self._send_json(200, {"data": record})
                    return

                if path.startswith("/records/") and method == "DELETE":
                    user = self._authenticate("records:write")
                    record_id = self._extract_id(path, "/records/")
                    context.record_service.delete_record(record_id, deleted_by=user["id"])
                    self._send_json(200, {"message": "Record deleted successfully."})
                    return

                if path == "/dashboard/summary" and method == "GET":
                    self._authenticate("dashboard:read")
                    summary = context.record_service.build_summary()
                    self._send_json(200, {"data": summary})
                    return

                raise NotFoundError("Endpoint not found.")
            except ApiError as error:
                self._send_json(error.status_code, {"error": error.message, "details": error.details})
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Request body must contain valid JSON."})
            except Exception:
                self._send_json(500, {"error": "Internal server error."})

        def _authenticate(self, permission: str) -> dict[str, Any]:
            token = extract_bearer_token(self.headers.get("Authorization"))
            user = ensure_active_user(context.user_service.get_user_by_token(token))
            require_permission(user, permission)
            return user

        def _extract_id(self, path: str, prefix: str) -> int:
            raw_value = path.replace(prefix, "", 1)
            try:
                return int(raw_value)
            except ValueError as error:
                raise ValidationError("Resource id must be an integer.") from error

        def _read_json_body(self) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                raise ValidationError("Request body is required.")
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValidationError("JSON body must be an object.")
            return payload

        def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return FinanceRequestHandler


def run_server() -> None:
    context = AppContext()
    handler = create_handler(context)
    with ThreadingHTTPServer((settings.host, settings.port), handler) as server:
        print(f"Serving on http://{settings.host}:{settings.port}")
        server.serve_forever()


if __name__ == "__main__":
    run_server()
