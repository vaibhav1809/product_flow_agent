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
    "You are a UX analyst extracting the exact sequence of screens shown in a demo "
    "video. Focus only on the screens and their order. "
    "{format_instructions}"
)

HUMAN_PROMPT = (
    "Analyze the demo video and list each screen in the order it appears. "
    "For each screen, provide a short description and the start/end timestamps in "
    "HH:MM:SS format. Use empty strings when timestamps are not clear."
)


class ScreenInfo(BaseModel):
    order: int
    name: str = ""
    description: str = ""
    start_timestamp: str = ""
    end_timestamp: str = ""
    key_elements: list[str] = Field(default_factory=list)


class ScreenExtractionResult(BaseModel):
    screens: list[ScreenInfo] = Field(default_factory=list)


class ScreenParser(BaseOutputParser[ScreenExtractionResult]):
    def get_format_instructions(self) -> str:
        return (
            "Return valid JSON with key: screens. "
            "screens: list of screen objects with keys: order, name, description, "
            "start_timestamp, end_timestamp, key_elements."
        )

    def parse(self, text: str) -> ScreenExtractionResult:
        payload = json.loads(extract_json(text))
        screens_payload = payload.get("screens") or []
        screens: list[ScreenInfo] = []
        if isinstance(screens_payload, list):
            for index, item in enumerate(screens_payload):
                if not isinstance(item, dict):
                    continue
                screens.append(
                    ScreenInfo(
                        order=_coerce_int(item.get("order"), index + 1),
                        name=coerce_str(item.get("name")),
                        description=coerce_str(item.get("description")),
                        start_timestamp=coerce_str(item.get("start_timestamp")),
                        end_timestamp=coerce_str(item.get("end_timestamp")),
                        key_elements=_coerce_str_list(item.get("key_elements")),
                    )
                )

        return ScreenExtractionResult(screens=screens)


class ScreenExtractor:
    def __init__(self) -> None:
        self.parser = ScreenParser()
        self.model = llm_client.SCREEN_EXTRACTOR_MODEL
        self.chain = self._build_chain()

    def extract(self, video_path: str | Path) -> ScreenExtractionResult:
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


class ScreenExtractorInputs(BaseModel):
    video_path: str


class ScreenExtractorNode(Node):
    name: str = "screen_extractor"
    depends_on: list[str] = ["split_video"]
    extractor: ScreenExtractor = Field(default_factory=ScreenExtractor)

    def run(self, context: PipelineContext) -> ScreenExtractionResult:
        inputs = ScreenExtractorInputs.model_validate(context.inputs)
        return self.extractor.extract(inputs.video_path)


def _coerce_int(value: Any, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return default


def _coerce_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [coerce_str(item) for item in value if item is not None]
    return []
