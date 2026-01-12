from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PipelineContext(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def set_artifact(self, key: str, value: Any) -> None:
        self.artifacts[key] = value

    def get_artifact(self, key: str) -> Any:
        return self.artifacts.get(key)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "inputs": _to_jsonable(self.inputs),
            "artifacts": _to_jsonable(self.artifacts),
            "metadata": _to_jsonable(self.metadata),
        }


logger = logging.getLogger(__name__)


class Node(BaseModel):
    name: str
    depends_on: list[str] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def log_start(self, context: PipelineContext) -> None:
        logger.info("Starting node: %s", self.name)

    def log_end(self, context: PipelineContext, result: Any) -> None:
        logger.info("Finished node: %s", self.name)

    def log_error(self, context: PipelineContext, error: Exception) -> None:
        logger.exception("Node failed: %s", self.name)

    def run(self, context: PipelineContext) -> Any:
        raise NotImplementedError

    async def arun(self, context: PipelineContext) -> Any:
        return await asyncio.to_thread(self.run, context)


class ConditionalNode(Node):
    route_map: dict[str, str] = Field(default_factory=dict)

    def route(self, context: PipelineContext) -> str:
        raise NotImplementedError


class PipelineError(RuntimeError):
    pass


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return {key: _to_jsonable(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value
