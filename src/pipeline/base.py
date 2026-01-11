from __future__ import annotations

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


class Node(BaseModel):
    name: str
    depends_on: list[str] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def run(self, context: PipelineContext) -> Any:
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
