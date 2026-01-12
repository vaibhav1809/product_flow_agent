from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field

from src.config import llm_client
from src.pipeline.base import Node, PipelineContext
from src.pipeline.repository.utils import coerce_str, extract_json

SYSTEM_PROMPT = (
    "You are a query planner for a product knowledge repository. "
    "Convert the user query into a structured QueryPlan JSON. "
    "Use repository-only evidence and avoid creativity. "
    "{format_instructions}"
)

HUMAN_PROMPT = (
    "Query: {query}\n"
    "App name (optional): {app_name}\n"
    "Return a QueryPlan that sets intent, target_level, depth, constraints, "
    "filters, and output_schema."
)


class QueryPlanFilters(BaseModel):
    feature_name_hint: str = ""
    screen_name_hint: str = ""
    flow_name_hint: str = ""
    must_include: list[str] = Field(default_factory=list)
    must_exclude: list[str] = Field(default_factory=list)


class QueryPlan(BaseModel):
    intent: str
    target_level: str
    depth: str
    constraints: list[str] = Field(default_factory=list)
    filters: QueryPlanFilters
    output_schema: str


class QueryPlanInputs(BaseModel):
    query: str
    app_name: str | None = None


class QueryPlanParser(BaseOutputParser[QueryPlan]):
    def get_format_instructions(self) -> str:
        return (
            "Return valid JSON with keys: intent, target_level, depth, constraints, "
            "filters, output_schema. intent must be one of: explain_existing, "
            "find_similar, navigation, components, ux_reference. target_level must "
            "be one of: feature, flow, screen, interaction. depth must be one of: "
            "shallow, down_to_screen, down_to_interaction. constraints must be a "
            "list of strings. filters must be an object with keys: "
            "feature_name_hint, screen_name_hint, flow_name_hint, must_include, "
            "must_exclude. output_schema must be a string."
        )

    def parse(self, text: str) -> QueryPlan:
        payload = json.loads(extract_json(text))
        filters_payload = payload.get("filters") if isinstance(payload, dict) else {}
        filters = _parse_filters(filters_payload)

        constraints = _coerce_list(
            payload.get("constraints") if isinstance(
                payload, dict) else None)
        if not constraints:
            constraints = ["use repository only", "no creativity"]

        return QueryPlan(
            intent=coerce_str(payload.get("intent") if isinstance(payload, dict) else ""),
            target_level=coerce_str(payload.get("target_level") if isinstance(payload, dict) else ""),
            depth=coerce_str(payload.get("depth") if isinstance(payload, dict) else ""),
            constraints=constraints,
            filters=filters,
            output_schema=coerce_str(payload.get("output_schema") if isinstance(payload, dict) else ""),
        )


class QueryPlanner:
    def __init__(self) -> None:
        self.parser = QueryPlanParser()
        self.model = llm_client.QUERY_PLANNER_MODEL
        self.chain: RunnableLambda = self._build_chain()

    def plan(self, query: str, app_name: str | None = None) -> QueryPlan:
        return self.chain.invoke({"query": query, "app_name": app_name or ""})

    async def aplan(self, query: str, app_name: str | None = None) -> QueryPlan:
        return await self.chain.ainvoke({"query": query, "app_name": app_name or ""})

    def _build_chain(self) -> Any:
        def build_messages(inputs: dict[str, str]) -> list[SystemMessage | HumanMessage]:
            system_text = SYSTEM_PROMPT.format(
                format_instructions=self.parser.get_format_instructions()
            )
            human_text = HUMAN_PROMPT.format(
                query=inputs["query"], app_name=inputs.get("app_name", "")
            )

            return [
                SystemMessage(content=system_text),
                HumanMessage(content=human_text),
            ]

        return RunnableLambda(build_messages) | self.model | self.parser


class QueryPlanNode(Node):
    name: str = "query_plan"
    depends_on: list[str] = []
    planner: QueryPlanner = Field(default_factory=QueryPlanner)

    def run(self, context: PipelineContext) -> QueryPlan:
        inputs = QueryPlanInputs.model_validate(context.inputs)
        return self.planner.plan(inputs.query, inputs.app_name)

    async def arun(self, context: PipelineContext) -> QueryPlan:
        inputs = QueryPlanInputs.model_validate(context.inputs)
        return await self.planner.aplan(inputs.query, inputs.app_name)


def _parse_filters(filters_payload: Any) -> QueryPlanFilters:
    if not isinstance(filters_payload, dict):
        return QueryPlanFilters()
    return QueryPlanFilters(
        feature_name_hint=coerce_str(filters_payload.get("feature_name_hint")),
        screen_name_hint=coerce_str(filters_payload.get("screen_name_hint")),
        flow_name_hint=coerce_str(filters_payload.get("flow_name_hint")),
        must_include=_coerce_list(filters_payload.get("must_include")),
        must_exclude=_coerce_list(filters_payload.get("must_exclude")),
    )


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [coerce_str(item) for item in value if coerce_str(item)]
    if isinstance(value, str):
        return [value] if value else []
    return []
