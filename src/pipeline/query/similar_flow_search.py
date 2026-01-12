from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field

from src.config import llm_client
from src.pipeline.base import ConditionalNode, PipelineContext
from src.pipeline.query.query_planner import QueryPlan
from src.pipeline.query.utils import (
    DEFAULT_REPOSITORY_PATH,
    DEFAULT_TOP_K,
    build_candidate_key,
    collect_matches,
    get_query_plan,
    load_repository,
    sanitize_top_k,
    summarize_steps,
)
from src.pipeline.repository.utils import coerce_str, extract_json

SYSTEM_PROMPT = (
    "You are a retrieval assistant selecting the most relevant repository items. "
    "Only choose from the provided candidates. No creativity."
    "{format_instructions}"
)

HUMAN_PROMPT = (
    "Query: {query}\n"
    "Target level: flow\n"
    "Constraints: {constraints}\n"
    "Filters: {filters}\n"
    "Return up to {top_k} keys from the candidates in relevance order.\n"
    "Candidates:\n{candidates}"
)


class SimilarFlowSearchInputs(BaseModel):
    query: str
    repository_path: str | None = None
    top_k: int | None = None


class SimilarFlowKeysParser(BaseOutputParser[list[str]]):
    def get_format_instructions(self) -> str:
        return "Return valid JSON with key 'keys' as a list of candidate keys."

    def parse(self, text: str) -> list[str]:
        payload = json.loads(extract_json(text))
        if isinstance(payload, list):
            keys = payload
        elif isinstance(payload, dict):
            keys = payload.get("keys") or []
        else:
            keys = []
        return [coerce_str(key) for key in keys if coerce_str(key)]


class SimilarFlowSearchEngine:
    def __init__(self) -> None:
        self.parser = SimilarFlowKeysParser()
        self.model = llm_client.QUERY_SEARCH_MODEL
        self.chain = self._build_chain()

    def search(
        self,
        query: str,
        plan: QueryPlan | None,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[str]:
        return self.chain.invoke(
            {
                "query": query,
                "plan": plan,
                "candidates": candidates,
                "top_k": top_k,
            }
        )

    async def asearch(
        self,
        query: str,
        plan: QueryPlan | None,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[str]:
        return await self.chain.ainvoke(
            {
                "query": query,
                "plan": plan,
                "candidates": candidates,
                "top_k": top_k,
            }
        )

    def _build_chain(self) -> Any:
        def build_messages(inputs: dict[str, Any]) -> list[SystemMessage | HumanMessage]:
            system_text = SYSTEM_PROMPT.format(
                format_instructions=self.parser.get_format_instructions()
            )
            plan = inputs.get("plan")
            filters = {}
            constraints: list[str] = []
            if isinstance(plan, QueryPlan):
                filters = plan.filters.model_dump()
                constraints = plan.constraints
            human_text = HUMAN_PROMPT.format(
                query=inputs["query"],
                constraints=json.dumps(constraints, ensure_ascii=True),
                filters=json.dumps(filters, ensure_ascii=True),
                top_k=inputs["top_k"],
                candidates=json.dumps(inputs["candidates"], ensure_ascii=True),
            )
            return [SystemMessage(content=system_text), HumanMessage(content=human_text)]

        return RunnableLambda(build_messages) | self.model | self.parser


class SimilarFlowSearchNode(ConditionalNode):
    name: str = "similar_flow_search"
    depends_on: list[str] = ["query_plan"]
    route_map: dict[str, str] = Field(default_factory=lambda: {"export": "query_export"})
    engine: SimilarFlowSearchEngine = Field(default_factory=SimilarFlowSearchEngine)

    def run(self, context: PipelineContext) -> dict[str, Any]:
        inputs = SimilarFlowSearchInputs.model_validate(context.inputs)
        repository_path = Path(inputs.repository_path) if inputs.repository_path else DEFAULT_REPOSITORY_PATH
        payload = load_repository(repository_path)
        plan = get_query_plan(context)
        candidates, mapping = _build_candidates(payload)
        top_k = sanitize_top_k(inputs.top_k, DEFAULT_TOP_K)
        keys = self.engine.search(inputs.query, plan, candidates, top_k)
        matches = collect_matches(keys, mapping)
        return {"keys": keys, "matches": matches}

    async def arun(self, context: PipelineContext) -> dict[str, Any]:
        inputs = SimilarFlowSearchInputs.model_validate(context.inputs)
        repository_path = Path(inputs.repository_path) if inputs.repository_path else DEFAULT_REPOSITORY_PATH
        payload = load_repository(repository_path)
        plan = get_query_plan(context)
        candidates, mapping = _build_candidates(payload)
        top_k = sanitize_top_k(inputs.top_k, DEFAULT_TOP_K)
        keys = await self.engine.asearch(inputs.query, plan, candidates, top_k)
        matches = collect_matches(keys, mapping)
        return {"keys": keys, "matches": matches}

    def route(self, context: PipelineContext) -> str:
        return "export"


def _build_candidates(
    payload: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    mapping: dict[str, dict[str, Any]] = {}
    flows = payload.get("flows") if isinstance(payload, dict) else None
    flow_items: list[dict[str, Any]] = []
    if isinstance(flows, list):
        flow_items = [flow for flow in flows if isinstance(flow, dict)]
    else:
        flow = payload.get("flow") if isinstance(payload, dict) else None
        if isinstance(flow, dict):
            flow_items = [flow]

    for index, flow in enumerate(flow_items, start=1):
        raw_key = coerce_str(flow.get("flow_title") or flow.get("flow_goal") or f"flow_{index}")
        key = build_candidate_key(flow, raw_key)
        if not key:
            continue
        entry = {
            "key": key,
            "name": coerce_str(flow.get("flow_title")),
            "description": coerce_str(flow.get("flow_goal")),
            "steps": summarize_steps(flow.get("steps")),
        }
        candidates.append(entry)
        mapping[key] = flow
    return candidates, mapping
