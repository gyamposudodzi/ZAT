from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime
from typing import Any

from app.errors import NotFoundError, ValidationError

VALID_ROLES = {"viewer", "analyst", "admin"}
VALID_STATUSES = {"active", "inactive"}
VALID_RECORD_TYPES = {"income", "expense"}


class UserService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def seed_defaults(self) -> None:
        if self.repository.count() > 0:
            return

        defaults = [
            {"name": "Admin User", "email": "admin@finance.local", "role": "admin", "status": "active", "api_token": "admin-token"},
            {"name": "Analyst User", "email": "analyst@finance.local", "role": "analyst", "status": "active", "api_token": "analyst-token"},
            {"name": "Viewer User", "email": "viewer@finance.local", "role": "viewer", "status": "active", "api_token": "viewer-token"},
            {"name": "Inactive User", "email": "inactive@finance.local", "role": "viewer", "status": "inactive", "api_token": "inactive-token"},
        ]
        for payload in defaults:
            self.repository.create(payload)

    def list_users(self) -> list[dict[str, Any]]:
        return self.repository.list_all()

    def get_user(self, user_id: int) -> dict[str, Any]:
        user = self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found.")
        return user

    def get_user_by_token(self, token: str) -> dict[str, Any] | None:
        return self.repository.get_by_token(token)

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        clean_payload = self._validate_user_payload(payload, partial=False)
        clean_payload.setdefault("api_token", secrets.token_urlsafe(24))
        try:
            return self.repository.create(clean_payload)
        except sqlite3.IntegrityError as error:
            raise ValidationError("User email or token already exists.") from error

    def update_user(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.repository.get_by_id(user_id):
            raise NotFoundError("User not found.")
        clean_payload = self._validate_user_payload(payload, partial=True)
        if not clean_payload:
            raise ValidationError("At least one updatable field is required.")
        try:
            updated = self.repository.update(user_id, clean_payload)
        except sqlite3.IntegrityError as error:
            raise ValidationError("User email or token already exists.") from error
        if not updated:
            raise NotFoundError("User not found.")
        return updated

    def _validate_user_payload(self, payload: dict[str, Any], *, partial: bool) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        required_fields = ("name", "email", "role", "status")
        if not partial:
            missing = [field for field in required_fields if field not in payload]
            if missing:
                raise ValidationError("Missing required user fields.", details={"missing": missing})

        if "name" in payload:
            value = str(payload["name"]).strip()
            if not value:
                raise ValidationError("User name must not be empty.")
            clean["name"] = value

        if "email" in payload:
            value = str(payload["email"]).strip().lower()
            if "@" not in value or value.startswith("@") or value.endswith("@"):
                raise ValidationError("User email must be valid.")
            clean["email"] = value

        if "role" in payload:
            value = str(payload["role"]).strip().lower()
            if value not in VALID_ROLES:
                raise ValidationError("User role must be viewer, analyst, or admin.")
            clean["role"] = value

        if "status" in payload:
            value = str(payload["status"]).strip().lower()
            if value not in VALID_STATUSES:
                raise ValidationError("User status must be active or inactive.")
            clean["status"] = value

        if "api_token" in payload:
            value = str(payload["api_token"]).strip()
            if len(value) < 8:
                raise ValidationError("API token must be at least 8 characters.")
            clean["api_token"] = value

        return clean


class RecordService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def list_records(self, filters: dict[str, Any]) -> dict[str, Any]:
        normalized_filters = {
            "type": filters.get("type"),
            "category": filters.get("category"),
            "start_date": filters.get("start_date"),
            "end_date": filters.get("end_date"),
            "limit": self._parse_positive_int(filters.get("limit", 50), "limit", default=50, maximum=200),
            "offset": self._parse_positive_int(filters.get("offset", 0), "offset", default=0),
            "sort_by": self._parse_sort_by(filters.get("sort_by", "date")),
            "sort_direction": self._parse_sort_direction(filters.get("sort_direction", "desc")),
        }
        if normalized_filters["type"] and normalized_filters["type"] not in VALID_RECORD_TYPES:
            raise ValidationError("Record type filter must be income or expense.")
        for key in ("start_date", "end_date"):
            if normalized_filters[key]:
                self._validate_date(normalized_filters[key], key)
        records = self.repository.list_filtered(normalized_filters)
        total = self.repository.count_filtered(normalized_filters)
        return {
            "data": records,
            "meta": {
                "count": len(records),
                "total": total,
                "limit": normalized_filters["limit"],
                "offset": normalized_filters["offset"],
                "sort_by": normalized_filters["sort_by"],
                "sort_direction": normalized_filters["sort_direction"],
            },
        }

    def get_record(self, record_id: int) -> dict[str, Any]:
        record = self.repository.get_by_id(record_id)
        if not record:
            raise NotFoundError("Financial record not found.")
        return record

    def create_record(self, payload: dict[str, Any], *, created_by: int) -> dict[str, Any]:
        clean_payload = self._validate_record_payload(payload, partial=False)
        clean_payload["created_by"] = created_by
        return self.repository.create(clean_payload)

    def update_record(self, record_id: int, payload: dict[str, Any], *, updated_by: int) -> dict[str, Any]:
        if not self.repository.get_by_id(record_id):
            raise NotFoundError("Financial record not found.")
        clean_payload = self._validate_record_payload(payload, partial=True)
        if not clean_payload:
            raise ValidationError("At least one updatable field is required.")
        clean_payload["updated_by"] = updated_by
        updated = self.repository.update(record_id, clean_payload)
        if not updated:
            raise NotFoundError("Financial record not found.")
        return updated

    def delete_record(self, record_id: int, *, deleted_by: int) -> None:
        deleted = self.repository.soft_delete(record_id, deleted_by=deleted_by)
        if not deleted:
            raise NotFoundError("Financial record not found.")

    def build_summary(self) -> dict[str, Any]:
        totals = self.repository.totals()
        totals["category_totals"] = self.repository.category_totals()
        totals["monthly_trends"] = self.repository.monthly_trends()
        totals["recent_activity"] = self.repository.recent_activity()
        return totals

    def seed_defaults(self, *, admin_user_id: int) -> None:
        if self.repository.recent_activity(limit=1):
            return

        defaults = [
            {"amount": 15000, "type": "income", "category": "Salary", "record_date": "2026-01-31", "notes": "January payroll"},
            {"amount": 1200, "type": "expense", "category": "Rent", "record_date": "2026-02-01", "notes": "Office rent"},
            {"amount": 4800, "type": "income", "category": "Consulting", "record_date": "2026-02-15", "notes": "Client retainer"},
            {"amount": 950, "type": "expense", "category": "Software", "record_date": "2026-02-18", "notes": "Tool subscriptions"},
            {"amount": 400, "type": "expense", "category": "Travel", "record_date": "2026-03-02", "notes": "Client visit"},
            {"amount": 15500, "type": "income", "category": "Salary", "record_date": "2026-03-31", "notes": "March payroll"},
        ]
        for payload in defaults:
            self.create_record(payload, created_by=admin_user_id)

    def _validate_record_payload(self, payload: dict[str, Any], *, partial: bool) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        required_fields = ("amount", "type", "category", "record_date")
        if not partial:
            missing = [field for field in required_fields if field not in payload]
            if missing:
                raise ValidationError("Missing required record fields.", details={"missing": missing})

        if "amount" in payload:
            try:
                amount = float(payload["amount"])
            except (TypeError, ValueError) as error:
                raise ValidationError("Record amount must be numeric.") from error
            if amount < 0:
                raise ValidationError("Record amount must be zero or greater.")
            clean["amount"] = round(amount, 2)

        if "type" in payload:
            value = str(payload["type"]).strip().lower()
            if value not in VALID_RECORD_TYPES:
                raise ValidationError("Record type must be income or expense.")
            clean["type"] = value

        if "category" in payload:
            value = str(payload["category"]).strip()
            if not value:
                raise ValidationError("Record category must not be empty.")
            clean["category"] = value

        if "record_date" in payload:
            value = str(payload["record_date"]).strip()
            self._validate_date(value, "record_date")
            clean["record_date"] = value

        if "notes" in payload:
            clean["notes"] = str(payload["notes"]).strip()
        elif not partial:
            clean["notes"] = ""

        return clean

    def _validate_date(self, value: str, field_name: str) -> None:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as error:
            raise ValidationError(f"{field_name} must use YYYY-MM-DD format.") from error

    def _parse_positive_int(self, value: Any, field_name: str, *, default: int, maximum: int | None = None) -> int:
        if value in (None, ""):
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError) as error:
            raise ValidationError(f"{field_name} must be an integer.") from error
        if parsed < 0:
            raise ValidationError(f"{field_name} must be zero or greater.")
        if maximum is not None and parsed > maximum:
            raise ValidationError(f"{field_name} must be {maximum} or less.")
        return parsed

    def _parse_sort_by(self, value: Any) -> str:
        normalized = str(value).strip().lower()
        allowed = {"date", "amount", "category", "created_at"}
        if normalized not in allowed:
            raise ValidationError("sort_by must be one of: date, amount, category, created_at.")
        return normalized

    def _parse_sort_direction(self, value: Any) -> str:
        normalized = str(value).strip().lower()
        if normalized not in {"asc", "desc"}:
            raise ValidationError("sort_direction must be asc or desc.")
        return normalized
