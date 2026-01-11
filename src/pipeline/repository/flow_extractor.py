from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field

from src.config import llm_client
from src.pipeline.base import Node, PipelineContext

from .utils import coerce_str, extract_json, load_video_base64

SYSTEM_PROMPT = (
    "You are a UX analyst extracting a detailed user flow from a demo "
    "video. Focus only on the user flow without describing app or features. "
    "{format_instructions}"
)

HUMAN_PROMPT = (
    "Analyze the demo video and produce a detailed, step-by-step user flow. "
    "Capture each step with user actions, UI context, and system responses. "
    "Include start_timestamp and end_timestamp for each step in HH:MM:SS format. "
    "Use empty strings when timestamps are not clear."
)


class FlowStep(BaseModel):
    step_number: int
    title: str = ""
    description: str = ""
    user_action: str = ""
    ui_context: str = ""
    system_response: str = ""
    start_timestamp: str = ""
    end_timestamp: str = ""


class FlowExtractionResult(BaseModel):
    flow_title: str = ""
    flow_goal: str = ""
    steps: list[FlowStep] = Field(default_factory=list)


class FlowParser(BaseOutputParser[FlowExtractionResult]):
    def get_format_instructions(self) -> str:
        return (
            "Return valid JSON with keys: flow_title, flow_goal, steps. "
            "steps: list of step objects with keys: step_number, title, description, "
            "user_action, ui_context, system_response, start_timestamp, end_timestamp."
        )

    def parse(self, text: str) -> FlowExtractionResult:
        payload = json.loads(extract_json(text))
        flow_title = coerce_str(payload.get("flow_title"))
        flow_goal = coerce_str(payload.get("flow_goal"))

        steps_payload = payload.get("steps") or []
        steps: list[FlowStep] = []
        if isinstance(steps_payload, list):
            for index, item in enumerate(steps_payload):
                if not isinstance(item, dict):
                    continue
                steps.append(
                    FlowStep(
                        step_number=_coerce_int(item.get("step_number"), index + 1),
                        title=coerce_str(item.get("title")),
                        description=coerce_str(item.get("description")),
                        user_action=coerce_str(item.get("user_action")),
                        ui_context=coerce_str(item.get("ui_context")),
                        system_response=coerce_str(item.get("system_response")),
                        start_timestamp=coerce_str(item.get("start_timestamp")),
                        end_timestamp=coerce_str(item.get("end_timestamp")),
                    )
                )

        return FlowExtractionResult(flow_title=flow_title, flow_goal=flow_goal, steps=steps)


class FlowExtractor:
    def __init__(self) -> None:
        self.parser = FlowParser()
        self.model = llm_client.FLOW_EXTRACTOR_MODEL
        self.chain = self._build_chain()

    def extract(self, video_path: str | Path) -> FlowExtractionResult:
        return self.chain.invoke({"video_path": str(video_path)})

    def _build_chain(self) -> Any:
        def build_messages(inputs: dict[str, str]) -> list[SystemMessage | HumanMessage]:
            video_path = inputs["video_path"]
            mime_type, video_base64 = load_video_base64(video_path)
            system_text = SYSTEM_PROMPT.format(
                format_instructions=self.parser.get_format_instructions()
            )

            return [
                SystemMessage(content=system_text),
                HumanMessage(
                    content=[
                        {"type": "text", "text": HUMAN_PROMPT},
                        {
                            "type": "file",
                            "source_type": "base64",
                            "mime_type": mime_type,
                            "data": video_base64,
                        },
                    ]
                ),
            ]

        return RunnableLambda(build_messages) | self.model | self.parser


class FlowExtractorInputs(BaseModel):
    video_path: str


class FlowExtractorNode(Node):
    name: str = "flow_extractor"
    depends_on: list[str] = ["split_video"]
    extractor: FlowExtractor = Field(default_factory=FlowExtractor)

    def run(self, context: PipelineContext) -> FlowExtractionResult:
        inputs = FlowExtractorInputs.model_validate(context.inputs)
        return self.extractor.extract(inputs.video_path)


def _coerce_int(value: Any, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return default
