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
    "You are a product analyst extracting structured app information from a demo "
    "video. Use only what is shown or said without assumptions. "
    "{format_instructions}"
)

HUMAN_PROMPT = (
    "Analyze the demo video and extract the app details and the features discussed. "
    "Include start_timestamp and end_timestamp for each feature in HH:MM:SS format. "
    "Use empty strings when timestamps are not clear."
)


class AppInfo(BaseModel):
    id: str = ""
    name: str = ""
    description: str = ""


class FeatureInfo(BaseModel):
    id: str = ""
    name: str = ""
    description: str = ""
    start_timestamp: str = ""
    end_timestamp: str = ""


class ExtractionResult(BaseModel):
    app: AppInfo
    features: list[FeatureInfo] = Field(default_factory=list)


class AppFeaturesParser(BaseOutputParser[ExtractionResult]):
    def get_format_instructions(self) -> str:
        return (
            "Return valid JSON with keys: app, features. "
            "app: {id, name, description}. "
            "features: list of feature objects. "
            "Each feature has id, name, description, start_timestamp, end_timestamp."
        )

    def parse(self, text: str) -> ExtractionResult:
        payload = json.loads(extract_json(text))
        app_payload = payload.get("app") or {}
        app = AppInfo(
            id=coerce_str(app_payload.get("id")),
            name=coerce_str(app_payload.get("name")),
            description=coerce_str(app_payload.get("description")),
        )

        features_payload = payload.get("features") or []
        features: list[FeatureInfo] = []
        if isinstance(features_payload, list):
            for item in features_payload:
                if isinstance(item, dict):
                    features.append(
                        FeatureInfo(
                            id=coerce_str(item.get("id")),
                            name=coerce_str(item.get("name")),
                            description=coerce_str(item.get("description")),
                            start_timestamp=coerce_str(item.get("start_timestamp")),
                            end_timestamp=coerce_str(item.get("end_timestamp")),
                        )
                    )

        return ExtractionResult(app=app, features=features)


class FeatureExtractor:
    def __init__(self) -> None:
        self.parser = AppFeaturesParser()
        self.model = llm_client.FEATURE_EXTRACTOR_MODEL
        self.chain = self._build_chain()

    def extract(self, video_path: str | Path) -> ExtractionResult:
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


class FeatureExtractorInputs(BaseModel):
    video_path: str


class FeatureExtractorNode(Node):
    name: str = "feature_extractor"
    depends_on: list[str] = []
    extractor: FeatureExtractor = Field(default_factory=FeatureExtractor)

    def run(self, context: PipelineContext) -> ExtractionResult:
        inputs = FeatureExtractorInputs.model_validate(context.inputs)
        return self.extractor.extract(inputs.video_path)
