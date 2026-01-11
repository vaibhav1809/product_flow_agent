from __future__ import annotations

import argparse
import json
from typing import Any


import src.config

from .base import PipelineContext, PipelineError
from .runner import Pipeline

from src.pipeline.repository import *


def build_repository_pipeline() -> Pipeline:
    return Pipeline(
        nodes=[
            FeatureExtractorNode(),
            # SplitVideoNode(),
            # ScreenExtractorNode(),
            # FlowExtractorNode(),
            # InteractionExtractorNode()
        ]
    )


def build_query_pipeline() -> Pipeline:
    return Pipeline(
        nodes=[
            # QueryInputNode(),
            # QueryLoadRepositoryNode(),
            # QuerySearchNode(),
            # QueryRankNode(),
        ]
    )


def run_pipeline(inputs: dict[str, Any], pipeline_type: str) -> PipelineContext:
    pipeline = _select_pipeline(pipeline_type)
    context = PipelineContext(inputs=inputs)
    return pipeline.run(context)


def _select_pipeline(pipeline_type: str) -> Pipeline:
    if pipeline_type == "repository":
        return build_repository_pipeline()
    if pipeline_type == "query":
        return build_query_pipeline()
    raise PipelineError(f"Unsupported pipeline type: {pipeline_type}")


def _load_inputs(args: argparse.Namespace) -> dict[str, Any]:
    if args.pipeline_type == "query":
        return {
            "query": args.query,
            "temperature": args.temperature if 'temperature' in args else 0
        }
    elif args.pipeline_type == "repository":
        return {
            "app_name": args.app_name,
            "video_path": args.video_path,
            "metadata": {"source": "cli"},
        }
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the product pipeline.")
    parser.add_argument("--pipeline-type", choices=["repository", "query"], default="repository")
    parser.add_argument("--app-name")
    parser.add_argument("--video_path")
    args = parser.parse_args()

    context = run_pipeline(_load_inputs(args), args.pipeline_type)

    print(json.dumps(context.to_jsonable(), indent=2))


if __name__ == "__main__":
    main()
