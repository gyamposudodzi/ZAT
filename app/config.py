from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path("finance.db")
    host: str = "127.0.0.1"
    port: int = 8000


settings = Settings()
