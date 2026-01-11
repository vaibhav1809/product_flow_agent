from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.pipeline.base import Node, PipelineContext
from src.utils.ffmpeg import is_available


CLIPS_DIR = Path("data/clips")
CLIPS_DIR.mkdir(parents=True, exist_ok=True)


class SplitVideoInputs(BaseModel):
    video_path: str


class SplitVideoNode(Node):
    name: str = "split_video"
    depends_on: list[str] = ["feature_extractor"]

    def run(self, context: PipelineContext) -> dict[str, Any]:
        if not is_available():
            raise RuntimeError("ffmpeg is not available in PATH.")

        inputs = SplitVideoInputs.model_validate(context.inputs)
        feature_payload = context.get_artifact("feature_extractor")

        video_path = Path(inputs.video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        

        clips: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for index, feature in enumerate(_iter_features(feature_payload)):
            name = _get_feature_field(feature, "name") or f"feature_{index + 1}"
            feature_id = _get_feature_field(feature, "id") or _slugify(name)
            start = _get_feature_field(feature, "start_timestamp")
            end = _get_feature_field(feature, "end_timestamp")

            start_ts = _normalize_timestamp(start)
            end_ts = _normalize_timestamp(end)

            if not start_ts or not end_ts:
                skipped.append(
                    {
                        "feature_id": feature_id,
                        "feature_name": name,
                        "start_timestamp": start or "",
                        "end_timestamp": end or "",
                        "reason": "missing timestamps",
                    }
                )
                continue

            file_name = f"{index + 1:02d}_{_slugify(name)}.mp4"
            output_path = CLIPS_DIR / file_name

            try:
                _run_ffmpeg(video_path, start_ts, end_ts, output_path)
                clips.append(
                    {
                        "feature_id": feature_id,
                        "feature_name": name,
                        "start_timestamp": start_ts,
                        "end_timestamp": end_ts,
                        "clip_path": str(output_path),
                    }
                )
            except subprocess.CalledProcessError as exc:
                errors.append(
                    {
                        "feature_id": feature_id,
                        "feature_name": name,
                        "start_timestamp": start_ts,
                        "end_timestamp": end_ts,
                        "error": exc.stderr.strip() if exc.stderr else str(exc),
                    }
                )

        return {
            "clips": clips,
            "skipped": skipped,
            "errors": errors,
            "clips_dir": str(CLIPS_DIR),
        }


def _iter_features(payload: Any) -> list[Any]:
    if payload is None:
        return []
    if hasattr(payload, "features"):
        return list(getattr(payload, "features"))
    if isinstance(payload, dict):
        features = payload.get("features") or []
        if isinstance(features, list):
            return features
    return []


def _get_feature_field(feature: Any, field_name: str) -> str:
    if hasattr(feature, field_name):
        value = getattr(feature, field_name)
        return "" if value is None else str(value)
    if isinstance(feature, dict):
        value = feature.get(field_name)
        return "" if value is None else str(value)
    return ""


def _normalize_timestamp(value: str) -> str:
    if not value:
        return ""
    if value.isdigit():
        return _seconds_to_timestamp(int(value))
    if re.match(r"^\d{1,2}:\d{2}:\d{2}$", value):
        return value
    if re.match(r"^\d{1,2}:\d{2}$", value):
        return f"00:{value}"
    return ""


def _seconds_to_timestamp(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _run_ffmpeg(input_path: Path, start: str, end: str, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ss",
        start,
        "-to",
        end,
        "-c",
        "copy",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    cleaned = cleaned.strip("_")
    return cleaned or "clip"
