from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.pipeline.base import Node, PipelineContext, _to_jsonable
from src.pipeline.query.query_planner import QueryPlan

DEFAULT_EXPORT_DIR = Path("data/json/exports")


class QueryExportInputs(BaseModel):
    output_dir: str | None = None


class QueryExportNode(Node):
    name: str = "query_export"
    depends_on: list[str] = [
        "similar_feature_search",
        "similar_flow_search",
        "similar_screen_search",
        "similar_interaction_search",
    ]
    export_style: str = "default"
    output_dir: Path = Field(default_factory=lambda: DEFAULT_EXPORT_DIR)

    def run(self, context: PipelineContext) -> dict[str, Any]:
        inputs = QueryExportInputs.model_validate(context.inputs)
        output_dir = Path(inputs.output_dir) if inputs.output_dir else self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        payload = _build_export_payload(context, self.export_style, timestamp)
        filename = f"{payload['pipeline_type']}_{self.export_style}_{timestamp}.json"
        output_path = output_dir / filename
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"output_path": str(output_path), "timestamp": timestamp}


def _build_export_payload(
    context: PipelineContext, export_style: str, timestamp: str
) -> dict[str, Any]:
    pipeline_type = context.metadata.get("pipeline_type") or "query"
    if pipeline_type == "repository":
        return {
            "pipeline_type": "repository",
            "export_style": export_style,
            "timestamp": timestamp,
            "context": context.to_jsonable(),
        }

    plan = context.get_artifact("query_plan")
    plan_payload = _to_jsonable(plan) if isinstance(plan, QueryPlan) else {}
    search_result = _find_search_result(context)

    return {
        "pipeline_type": "query",
        "export_style": export_style,
        "timestamp": timestamp,
        "query": context.inputs.get("query", ""),
        "app_name": context.inputs.get("app_name", ""),
        "plan": plan_payload,
        "result": search_result,
    }


def _find_search_result(context: PipelineContext) -> dict[str, Any]:
    for name in (
        "similar_feature_search",
        "similar_flow_search",
        "similar_screen_search",
        "similar_interaction_search",
    ):
        result = context.get_artifact(name)
        if isinstance(result, dict):
            return {"node": name, **_to_jsonable(result)}
    return {}
