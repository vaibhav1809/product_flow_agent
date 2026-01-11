from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

__all__ = ["CONFIG"]


class Config:
    _instance: Optional["Config"] = None
    _initialized = False

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self.__class__._initialized:
            return
        self.__class__._initialized = True

        self.name: Optional[str] = None

        self.postgres_host: Optional[str] = None
        self.postgres_port: Optional[int] = None
        self.postgres_user: Optional[str] = None
        self.postgres_password: Optional[str] = None
        self.postgres_db: Optional[str] = None

        self._load_env()

    def _load_env(self) -> None:
        env_path = Path(__file__).resolve().parents[2] / ".env"
        data: Dict[str, Any] = {}
        if env_path.exists():
            data.update(_parse_env_file(env_path))

        for key in list(data.keys()):
            if key in os.environ:
                data[key] = _coerce_value(os.environ[key])

        self.project_name: str = data.get("project_name") or "Ticket API"
        self.version: str = data.get("version") or "0.1.0"
        self.description: str = data.get("description") or "API documentation"
        self.api_v1_str: str = data.get("api_v1_str") or "/api/v1"
        self.seat_lock_ttl_seconds: int = data.get("seat_lock_ttl_seconds") or 600

        self.postgres_host = data.get("postgres_host")
        self.postgres_port = data.get("postgres_port")
        self.postgres_user = data.get("postgres_user")
        self.postgres_password = data.get("postgres_password")
        self.postgres_db = data.get("postgres_db")

        self.redis_host = data.get("redis_host")
        self.redis_port = data.get("redis_port")
        self.redis_password = data.get("redis_password")

def _parse_env_file(path: Path) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_quotes(value.strip())
        values[key] = _coerce_value(value)
    return values


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _coerce_value(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"none", "null"}:
        return None
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    return value


CONFIG = Config()
