from __future__ import annotations

import sqlite3
from typing import Any


class UserRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        cursor = self.connection.execute(
            """
            INSERT INTO users (name, email, role, status, api_token)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload["name"],
                payload["email"],
                payload["role"],
                payload["status"],
                payload["api_token"],
            ),
        )
        self.connection.commit()
        return self.get_by_id(cursor.lastrowid)

    def list_all(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT id, name, email, role, status, api_token, created_at
            FROM users
            ORDER BY id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT id, name, email, role, status, api_token, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_by_token(self, token: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT id, name, email, role, status, api_token, created_at
            FROM users
            WHERE api_token = ?
            """,
            (token,),
        ).fetchone()
        return dict(row) if row else None

    def update(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        fields = []
        values = []
        for key in ("name", "email", "role", "status", "api_token"):
            if key in payload:
                fields.append(f"{key} = ?")
                values.append(payload[key])

        if not fields:
            return self.get_by_id(user_id)

        values.append(user_id)
        self.connection.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        self.connection.commit()
        return self.get_by_id(user_id)

    def count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        return int(row["count"])


class RecordRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        cursor = self.connection.execute(
            """
            INSERT INTO financial_records (
                amount, type, category, record_date, notes, created_by, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["amount"],
                payload["type"],
                payload["category"],
                payload["record_date"],
                payload["notes"],
                payload["created_by"],
                payload["created_by"],
            ),
        )
        self.connection.commit()
        return self.get_by_id(cursor.lastrowid)

    def get_by_id(self, record_id: int, *, include_deleted: bool = False) -> dict[str, Any] | None:
        deleted_clause = "" if include_deleted else "AND fr.deleted_at IS NULL"
        row = self.connection.execute(
            f"""
            SELECT
                fr.id,
                fr.amount,
                fr.type,
                fr.category,
                fr.record_date,
                fr.notes,
                fr.created_by,
                fr.updated_by,
                fr.deleted_at,
                fr.deleted_by,
                fr.created_at,
                fr.updated_at,
                creator.name AS created_by_name,
                updater.name AS updated_by_name,
                deleter.name AS deleted_by_name
            FROM financial_records fr
            LEFT JOIN users creator ON creator.id = fr.created_by
            LEFT JOIN users updater ON updater.id = fr.updated_by
            LEFT JOIN users deleter ON deleter.id = fr.deleted_by
            WHERE fr.id = ? {deleted_clause}
            """,
            (record_id,),
        ).fetchone()
        return dict(row) if row else None

    def list_filtered(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        clauses = ["1 = 1"]
        values: list[Any] = []

        if filters.get("type"):
            clauses.append("type = ?")
            values.append(filters["type"])
        if filters.get("category"):
            clauses.append("LOWER(category) = LOWER(?)")
            values.append(filters["category"])
        if filters.get("start_date"):
            clauses.append("record_date >= ?")
            values.append(filters["start_date"])
        if filters.get("end_date"):
            clauses.append("record_date <= ?")
            values.append(filters["end_date"])

        order_by = self._build_order_by(filters["sort_by"], filters["sort_direction"])
        values.extend([filters["limit"], filters["offset"]])
        rows = self.connection.execute(
            f"""
            SELECT
                fr.id,
                fr.amount,
                fr.type,
                fr.category,
                fr.record_date,
                fr.notes,
                fr.created_by,
                fr.updated_by,
                fr.deleted_at,
                fr.deleted_by,
                fr.created_at,
                fr.updated_at,
                creator.name AS created_by_name,
                updater.name AS updated_by_name
            FROM financial_records fr
            LEFT JOIN users creator ON creator.id = fr.created_by
            LEFT JOIN users updater ON updater.id = fr.updated_by
            WHERE {' AND '.join(clauses)} AND fr.deleted_at IS NULL
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            values,
        ).fetchall()
        return [dict(row) for row in rows]

    def count_filtered(self, filters: dict[str, Any]) -> int:
        clauses = ["1 = 1", "deleted_at IS NULL"]
        values: list[Any] = []

        if filters.get("type"):
            clauses.append("type = ?")
            values.append(filters["type"])
        if filters.get("category"):
            clauses.append("LOWER(category) = LOWER(?)")
            values.append(filters["category"])
        if filters.get("start_date"):
            clauses.append("record_date >= ?")
            values.append(filters["start_date"])
        if filters.get("end_date"):
            clauses.append("record_date <= ?")
            values.append(filters["end_date"])

        row = self.connection.execute(
            f"SELECT COUNT(*) AS count FROM financial_records WHERE {' AND '.join(clauses)}",
            values,
        ).fetchone()
        return int(row["count"])

    def update(self, record_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        fields = []
        values = []
        for key in ("amount", "type", "category", "record_date", "notes", "updated_by"):
            if key in payload:
                fields.append(f"{key} = ?")
                values.append(payload[key])

        if not fields:
            return self.get_by_id(record_id)

        values.append(record_id)
        self.connection.execute(
            f"""
            UPDATE financial_records
            SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted_at IS NULL
            """,
            values,
        )
        self.connection.commit()
        return self.get_by_id(record_id)

    def soft_delete(self, record_id: int, *, deleted_by: int) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE financial_records
            SET deleted_at = CURRENT_TIMESTAMP, deleted_by = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (deleted_by, deleted_by, record_id),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def category_totals(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT category, type, ROUND(SUM(amount), 2) AS total_amount
            FROM financial_records
            WHERE deleted_at IS NULL
            GROUP BY category, type
            ORDER BY total_amount DESC, category ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def monthly_trends(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT SUBSTR(record_date, 1, 7) AS month,
                   ROUND(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 2) AS income,
                   ROUND(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 2) AS expense
            FROM financial_records
            WHERE deleted_at IS NULL
            GROUP BY SUBSTR(record_date, 1, 7)
            ORDER BY month ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def recent_activity(self, limit: int = 5) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                fr.id,
                fr.amount,
                fr.type,
                fr.category,
                fr.record_date,
                fr.notes,
                fr.created_by,
                fr.updated_by,
                fr.deleted_at,
                fr.deleted_by,
                fr.created_at,
                fr.updated_at,
                creator.name AS created_by_name,
                updater.name AS updated_by_name
            FROM financial_records fr
            LEFT JOIN users creator ON creator.id = fr.created_by
            LEFT JOIN users updater ON updater.id = fr.updated_by
            WHERE fr.deleted_at IS NULL
            ORDER BY fr.created_at DESC, fr.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def totals(self) -> dict[str, Any]:
        row = self.connection.execute(
            """
            SELECT
                ROUND(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 2) AS total_income,
                ROUND(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 2) AS total_expenses
            FROM financial_records
            WHERE deleted_at IS NULL
            """
        ).fetchone()
        total_income = float(row["total_income"] or 0)
        total_expenses = float(row["total_expenses"] or 0)
        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_balance": round(total_income - total_expenses, 2),
        }

    def _build_order_by(self, sort_by: str, sort_direction: str) -> str:
        allowed_columns = {
            "date": "fr.record_date",
            "amount": "fr.amount",
            "category": "fr.category",
            "created_at": "fr.created_at",
        }
        column = allowed_columns.get(sort_by, "fr.record_date")
        direction = "ASC" if sort_direction == "asc" else "DESC"
        return f"{column} {direction}, fr.id DESC"
