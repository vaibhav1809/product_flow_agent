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
    "You are a UX analyst extracting detailed user interactions from a demo "
    "video. Focus only on the user's interactions and their purpose. "
    "{format_instructions}"
)

HUMAN_PROMPT = (
    "Analyze the demo video and list each user interaction in order. "
    "For every interaction, provide a clear name, interaction type, and the "
    "reason the user performs it at that point. Include a short description, "
    "UI context, and start/end timestamps in HH:MM:SS format. Use empty strings "
    "when timestamps are not clear."
)


class InteractionInfo(BaseModel):
    order: int
    name: str = ""
    interaction_type: str = ""
    rationale: str = ""
    description: str = ""
    user_action: str = ""
    ui_context: str = ""
    system_response: str = ""
    start_timestamp: str = ""
    end_timestamp: str = ""


class InteractionExtractionResult(BaseModel):
    interactions: list[InteractionInfo] = Field(default_factory=list)


class InteractionParser(BaseOutputParser[InteractionExtractionResult]):
    def get_format_instructions(self) -> str:
        return (
            "Return valid JSON with key: interactions. "
            "interactions: list of objects with keys: order, name, interaction_type, "
            "rationale, description, user_action, ui_context, system_response, "
            "start_timestamp, end_timestamp."
        )

    def parse(self, text: str) -> InteractionExtractionResult:
        payload = json.loads(extract_json(text))
        interactions_payload = payload.get("interactions") or []
        interactions: list[InteractionInfo] = []
        if isinstance(interactions_payload, list):
            for index, item in enumerate(interactions_payload):
                if not isinstance(item, dict):
                    continue
                interactions.append(
                    InteractionInfo(
                        order=_coerce_int(item.get("order"), index + 1),
                        name=coerce_str(item.get("name")),
                        interaction_type=coerce_str(item.get("interaction_type")),
                        rationale=coerce_str(item.get("rationale")),
                        description=coerce_str(item.get("description")),
                        user_action=coerce_str(item.get("user_action")),
                        ui_context=coerce_str(item.get("ui_context")),
                        system_response=coerce_str(item.get("system_response")),
                        start_timestamp=coerce_str(item.get("start_timestamp")),
                        end_timestamp=coerce_str(item.get("end_timestamp")),
                    )
                )

        return InteractionExtractionResult(interactions=interactions)


class InteractionExtractor:
    def __init__(self) -> None:
        self.parser = InteractionParser()
        self.model = llm_client.INTERACTION_EXTRACTOR_MODEL
        self.chain = self._build_chain()

    def extract(self, video_path: str | Path) -> InteractionExtractionResult:
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


class InteractionExtractorInputs(BaseModel):
    video_path: str


class InteractionExtractorNode(Node):
    name: str = "interaction_extractor"
    depends_on: list[str] = ["split_video"]
    extractor: InteractionExtractor = Field(default_factory=InteractionExtractor)

    def run(self, context: PipelineContext) -> InteractionExtractionResult:
        inputs = InteractionExtractorInputs.model_validate(context.inputs)
        return self.extractor.extract(inputs.video_path)


def _coerce_int(value: Any, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return default
