from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict, Field

from .base import Node, PipelineContext, PipelineError


logger = logging.getLogger(__name__)


class Pipeline(BaseModel):
    nodes: list[Node] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def run(self, context: PipelineContext) -> PipelineContext:
        order = self._resolve_order()
        context.metadata["execution_order"] = [node.name for node in order]
        total = len(order)
        logger.info("Starting pipeline with %s node(s).", total)
        for index, node in enumerate(order, start=1):
            logger.info("Running node %s/%s: %s", index, total, node.name)
            node.log_start(context)
            try:
                result = node.run(context)
            except Exception as exc:
                node.log_error(context, exc)
                raise
            node.log_end(context, result)
            context.set_artifact(node.name, result)
        logger.info("Pipeline complete.")
        return context

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
