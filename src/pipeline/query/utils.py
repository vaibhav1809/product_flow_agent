from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from src.pipeline.base import PipelineContext
from src.pipeline.query.query_planner import QueryPlan
from src.pipeline.repository.utils import coerce_str

DEFAULT_REPOSITORY_PATH = Path("data/json/repo")
DEFAULT_TOP_K = 5


def load_repository(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Repository context not found: {path}")
    if path.is_dir():
        payloads = []
        for json_path in sorted(path.glob("*.json")):
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payloads.append((payload, json_path))
        if not payloads:
            raise FileNotFoundError(f"No repository JSON files found in: {path}")
        return _merge_repository_payloads(payloads)
    return json.loads(path.read_text(encoding="utf-8"))


def get_query_plan(context: PipelineContext) -> QueryPlan | None:
    plan = context.get_artifact("query_plan")
    return plan if isinstance(plan, QueryPlan) else None


def sanitize_top_k(value: int | None, default_top_k: int = DEFAULT_TOP_K) -> int:
    if value is None:
        return default_top_k
    return max(1, min(value, 10))


def collect_matches(
    keys: list[str], mapping: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for key in keys:
        item = mapping.get(coerce_str(key))
        if item is not None:
            matches.append(item)
    return matches


def key_from_order_or_name(item: dict[str, Any]) -> str:
    order = item.get("order")
    if isinstance(order, int):
        return str(order)
    return coerce_str(item.get("name"))


def summarize_steps(steps: Any) -> list[str]:
    if not isinstance(steps, list):
        return []
    summaries: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        title = coerce_str(step.get("title"))
        if title:
            summaries.append(title)
    return summaries


def build_candidate_key(item: dict[str, Any], base_key: str) -> str:
    source_file = coerce_str(item.get("source_file"))
    if source_file and base_key:
        return f"{source_file}:{base_key}"
    return base_key or source_file


def _merge_repository_payloads(
    payloads: Iterable[tuple[dict[str, Any], Path]]
) -> dict[str, Any]:
    combined: dict[str, Any] = {
        "features": [],
        "clips": [],
        "screens": [],
        "interactions": [],
        "flows": [],
    }
    for payload, source_path in payloads:
        source_id = source_path.stem
        if "source" in payload and "source" not in combined:
            combined["source"] = payload.get("source")
        if "app" in payload and "app" not in combined:
            combined["app"] = payload.get("app")
        _extend_with_source(combined["features"], payload.get("features"), source_id)
        _extend_with_source(combined["clips"], payload.get("clips"), source_id)
        _extend_with_source(combined["screens"], payload.get("screens"), source_id)
        _extend_with_source(combined["interactions"], payload.get("interactions"), source_id)
        _extend_flows(combined["flows"], payload, source_id)

    if combined["flows"] and "flow" not in combined:
        combined["flow"] = combined["flows"][0]

    return combined


def _extend_flows(target: list[dict[str, Any]], payload: dict[str, Any], source_id: str) -> None:
    flow = payload.get("flow")
    flows = payload.get("flows")
    if isinstance(flow, dict):
        target.append(_with_source(flow, source_id))
    if isinstance(flows, list):
        _extend_with_source(target, flows, source_id)


def _extend_with_source(target: list[dict[str, Any]], items: Any, source_id: str) -> None:
    if not isinstance(items, list):
        return
    for item in items:
        if isinstance(item, dict):
            target.append(_with_source(item, source_id))


def _with_source(item: dict[str, Any], source_id: str) -> dict[str, Any]:
    if item.get("source_file") == source_id:
        return item
    updated = dict(item)
    updated.setdefault("source_file", source_id)
    return updated
