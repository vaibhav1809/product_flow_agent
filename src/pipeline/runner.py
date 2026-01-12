from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Awaitable, Callable, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from .base import ConditionalNode, Node, PipelineContext, PipelineError


logger = logging.getLogger(__name__)


def _merge_contexts(
    left: PipelineContext | None, right: PipelineContext | None
) -> PipelineContext:
    if left is None and right is None:
        return PipelineContext()
    if left is None:
        return right # type: ignore
    if right is None or left is right:
        return left
    return PipelineContext(
        inputs={**left.inputs, **right.inputs},
        artifacts={**left.artifacts, **right.artifacts},
        metadata={**left.metadata, **right.metadata},
    )


class GraphState(TypedDict):
    context: Annotated[PipelineContext, _merge_contexts]


class Pipeline(BaseModel):
    nodes: list[Node] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def run(self, context: PipelineContext) -> PipelineContext:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(context))
        raise PipelineError(
            "Pipeline.run cannot be called from an active event loop; "
            "use `await arun(...)` instead."
        )

    async def arun(self, context: PipelineContext) -> PipelineContext:
        order = self._resolve_order()
        context.metadata["execution_order"] = [node.name for node in order]
        logger.info("Starting langgraph pipeline with %s node(s).", len(order))
        graph = self._build_graph(order)
        result_state = await graph.ainvoke({"context": context})
        logger.info("Langgraph pipeline complete.")
        return result_state["context"]

    def _build_graph(self, order: list[Node]):
        from langgraph.graph import END, START, StateGraph

        graph = StateGraph(GraphState)
        nodes_by_name = {node.name: node for node in order}
        conditional_nodes = {
            name: node
            for name, node in nodes_by_name.items()
            if isinstance(node, ConditionalNode)
        }
        dependents: dict[str, set[str]] = {name: set() for name in nodes_by_name}

        _validate_conditional_dependencies(nodes_by_name, conditional_nodes)

        for node in order:
            graph.add_node(node.name, _wrap_node(node))  # pyright: ignore[reportArgumentType]

        for node in order:
            if not node.depends_on:
                graph.add_edge(START, node.name)

            for dep in node.depends_on:
                if dep in conditional_nodes:
                    continue
                graph.add_edge(dep, node.name)
                dependents[dep].add(node.name)

        for name, node in conditional_nodes.items():
            if not node.route_map:
                raise PipelineError(f"Conditional node '{name}' has no route_map.")
            route_map = _normalize_route_map(node.route_map, nodes_by_name)

            graph.add_conditional_edges(name, _route(node), route_map)  # type: ignore
            for target in route_map.values():
                if target != END:
                    dependents[name].add(target)

        for node in order:
            if node.name in conditional_nodes:
                continue
            if not dependents[node.name]:
                graph.add_edge(node.name, END)

        return graph.compile()

    def _resolve_order(self) -> list[Node]:
        nodes_by_name = {node.name: node for node in self.nodes}
        if len(nodes_by_name) != len(self.nodes):
            raise PipelineError("Duplicate node names are not allowed.")

        missing = _missing_dependencies(nodes_by_name)
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise PipelineError(f"Missing dependencies: {missing_list}")

        indegree = {name: 0 for name in nodes_by_name}
        dependents: dict[str, list[str]] = {name: [] for name in nodes_by_name}
        for node in self.nodes:
            for dep in node.depends_on:
                indegree[node.name] += 1
                dependents[dep].append(node.name)

        queue = [name for name, degree in indegree.items() if degree == 0]
        order_names: list[str] = []

        while queue:
            name = queue.pop(0)
            order_names.append(name)
            for child in dependents[name]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)

        if len(order_names) != len(self.nodes):
            cycle_nodes = [name for name in nodes_by_name if name not in order_names]
            cycle_list = ", ".join(cycle_nodes)
            raise PipelineError(f"Dependency cycle detected among: {cycle_list}")

        return [nodes_by_name[name] for name in order_names]


def _missing_dependencies(nodes_by_name: dict[str, Node]) -> set[str]:
    missing: set[str] = set()
    for node in nodes_by_name.values():
        for dep in node.depends_on:
            if dep not in nodes_by_name:
                missing.add(dep)
    return missing


def _wrap_node(node: Node) -> Callable[[GraphState], Awaitable[GraphState]]:
    async def _runner(state: GraphState) -> GraphState:
        context = state["context"]
        node.log_start(context)
        try:
            result = await node.arun(context)
        except Exception as exc:
            node.log_error(context, exc)
            raise
        node.log_end(context, result)
        context.set_artifact(node.name, result)
        return {"context": context}

    return _runner


def _route(node: ConditionalNode) -> Callable[[GraphState], str]:
    def _router(state: GraphState) -> str:
        return node.route(state["context"])

    return _router


def _normalize_route_map(
    route_map: dict[str, str], nodes_by_name: dict[str, Node]
) -> dict[str, str]:
    from langgraph.graph import END

    normalized: dict[str, str] = {}
    for label, target in route_map.items():
        if not isinstance(target, str):
            raise PipelineError(
                f"Conditional route target for '{label}' must be a string."
            )
        if target in {"END", "__end__"}:
            normalized[label] = END
            continue
        if target not in nodes_by_name:
            raise PipelineError(f"Conditional route target '{target}' does not exist.")
        normalized[label] = target
    return normalized


def _validate_conditional_dependencies(
    nodes_by_name: dict[str, Node],
    conditional_nodes: dict[str, ConditionalNode],
) -> None:
    if not conditional_nodes:
        return

    for node in nodes_by_name.values():
        for dep in node.depends_on:
            conditional = conditional_nodes.get(dep)
            if not conditional:
                continue
            targets = set(conditional.route_map.values())
            if node.name not in targets:
                raise PipelineError(
                    f"Node '{node.name}' depends on conditional node '{dep}', "
                    "but is not listed in its route_map."
                )

    for conditional_name, conditional in conditional_nodes.items():
        for target in conditional.route_map.values():
            if target in {"END", "__end__"}:
                continue
            target_node = nodes_by_name.get(target)
            if target_node is None:
                continue
            if conditional_name not in target_node.depends_on:
                raise PipelineError(
                    f"Conditional route '{conditional_name} -> {target}' requires "
                    f"'{target}' to list '{conditional_name}' in depends_on."
                )
