from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL CHECK(role IN ('viewer', 'analyst', 'admin')),
            status TEXT NOT NULL CHECK(status IN ('active', 'inactive')),
            api_token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS financial_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL CHECK(amount >= 0),
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            category TEXT NOT NULL,
            record_date TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            created_by INTEGER NOT NULL,
            updated_by INTEGER,
            deleted_at TEXT,
            deleted_by INTEGER,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id),
            FOREIGN KEY (updated_by) REFERENCES users(id),
            FOREIGN KEY (deleted_by) REFERENCES users(id)
        );
        """
    )
    _ensure_column(connection, "financial_records", "updated_by", "INTEGER")
    _ensure_column(connection, "financial_records", "deleted_at", "TEXT")
    _ensure_column(connection, "financial_records", "deleted_by", "INTEGER")
    connection.commit()


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {row["name"] for row in rows}
    if column_name not in existing_columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
