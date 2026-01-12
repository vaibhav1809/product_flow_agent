from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.pipeline.base import Node, PipelineContext, _to_jsonable


DEFAULT_EXPORT_DIR = Path("data/json/repo")


class ExportInputs(BaseModel):
    output_path: str | None = None


class ExportNode(Node):
    name: str = "export"
    depends_on: list[str] = [
        "screen_extractor",
        "flow_extractor",
        "interaction_extractor",
    ]

    def run(self, context: PipelineContext) -> dict[str, Any]:
        inputs = ExportInputs.model_validate(context.inputs)
        output_path = Path(inputs.output_path) if inputs.output_path else _default_output_path(context)

        payload = _build_export_payload(context)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return {"output_path": str(output_path)}


def _build_export_payload(context: PipelineContext) -> dict[str, Any]:
    feature_payload = _to_jsonable(context.get_artifact("feature_extractor"))
    split_payload = _to_jsonable(context.get_artifact("split_video"))
    screen_payload = _to_jsonable(context.get_artifact("screen_extractor"))
    flow_payload = _to_jsonable(context.get_artifact("flow_extractor"))
    interaction_payload = _to_jsonable(context.get_artifact("interaction_extractor"))

    return {
        "source": {
            "app_name": context.inputs.get("app_name", ""),
            "video_path": context.inputs.get("video_path", ""),
            "metadata": _to_jsonable(context.inputs.get("metadata", {})),
        },
        "app": _get_dict(feature_payload, "app"),
        "features": _get_list(feature_payload, "features"),
        "clips": _get_list(split_payload, "clips"),
        "screens": _get_list(screen_payload, "screens"),
        "flow": _get_flow(flow_payload),
        "interactions": _get_list(interaction_payload, "interactions"),
    }


def _default_output_path(context: PipelineContext) -> Path:
    video_path = context.inputs.get("video_path", "")
    if video_path:
        name = Path(str(video_path)).stem or "repository_context"
    else:
        name = "repository_context"
    return DEFAULT_EXPORT_DIR / f"{name}.json"


def _get_dict(payload: Any, key: str) -> dict[str, Any]:
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _get_list(payload: Any, key: str) -> list[Any]:
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _get_flow(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return {
            "flow_title": payload.get("flow_title", ""),
            "flow_goal": payload.get("flow_goal", ""),
            "steps": payload.get("steps", []) if isinstance(payload.get("steps"), list) else [],
        }
    return {"flow_title": "", "flow_goal": "", "steps": []}
