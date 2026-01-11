from __future__ import annotations

from typing import Any


def rank(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(results, key=lambda item: item.get("score", 0), reverse=True)
