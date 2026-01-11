from __future__ import annotations

from typing import Any

from .feature_spec import FeatureSpec


def search(spec: FeatureSpec, index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not spec.query:
        return []
    results = []
    query_lower = spec.query.lower()
    for item in index:
        text = str(item.get("name", ""))
        if query_lower in text.lower():
            results.append(item)
    return results
