from __future__ import annotations

from typing import Any


class App:
    id: str
    name: str
    description: str


class Screen:
    id: str
    name: str
    description: str


class Component:
    id: str
    name: str
    description: str


class Flow:
    id: str
    name: str
    description: str


class Integration:
    id: str
    name: str
    description: str


class Feature:
    id: str
    name: str
    description: str
    start_timestamp: str
    end_timestamp: str
    flows: list[Flow]
    screens: list[Screen]
    components: list[Component]
    entry_points: list[str]
    success_criteria: list[str]
    failure_criteria: list[str]


class Features:
    features: list[Feature]


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _extract_json(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        fence = "```"
        start = cleaned.find(fence)
        end = cleaned.rfind(fence)
        if end > start:
            block = cleaned[start + len(fence): end]
            block = block.lstrip()
            if block.startswith("json"):
                block = block[len("json"):]
            return block.strip()
    return cleaned


def _build_named_entities(items: Any, cls: type) -> list:
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        obj = cls()
        obj.id = _coerce_str(item.get("id"))
        obj.name = _coerce_str(item.get("name"))
        obj.description = _coerce_str(item.get("description"))
        result.append(obj)
    return result


def _build_feature(item: dict[str, Any]) -> Feature:
    feature = Feature()
    feature.id = _coerce_str(item.get("id"))
    feature.name = _coerce_str(item.get("name"))
    feature.description = _coerce_str(item.get("description"))
    feature.start_timestamp = _coerce_str(item.get("start_timestamp"))
    feature.end_timestamp = _coerce_str(item.get("end_timestamp"))
    feature.flows = _build_named_entities(item.get("flows"), Flow)
    feature.screens = _build_named_entities(item.get("screens"), Screen)
    feature.components = _build_named_entities(item.get("components"), Component)
    feature.entry_points = [
        _coerce_str(value)
        for value in (item.get("entry_points") or [])
        if value is not None
    ]
    feature.success_criteria = [
        _coerce_str(value)
        for value in (item.get("success_criteria") or [])
        if value is not None
    ]
    feature.failure_criteria = [
        _coerce_str(value)
        for value in (item.get("failure_criteria") or [])
        if value is not None
    ]
    return feature
