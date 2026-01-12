from __future__ import annotations

from typing import Any

from src.pipeline.base import Node, PipelineContext


class PlaceholderNode(Node):
    def run(self, context: PipelineContext) -> dict[str, Any]:
        return {"status": "placeholder", "node": self.name}


class LoadRepositoryNode(PlaceholderNode):
    name: str = "load_repository"
    depends_on: list[str] = ["query_plan"]


class RetrieveEvidenceNode(PlaceholderNode):
    name: str = "retrieve_evidence"
    depends_on: list[str] = ["load_repository"]


class DecideDepthNode(PlaceholderNode):
    name: str = "decide_depth"
    depends_on: list[str] = ["retrieve_evidence"]


class ExpandEvidenceNode(PlaceholderNode):
    name: str = "expand_evidence"
    depends_on: list[str] = ["decide_depth"]


class ProjectResponseNode(PlaceholderNode):
    name: str = "project_response"
    depends_on: list[str] = ["expand_evidence"]


class FinalGuardrailsNode(PlaceholderNode):
    name: str = "final_guardrails"
    depends_on: list[str] = ["project_response"]
