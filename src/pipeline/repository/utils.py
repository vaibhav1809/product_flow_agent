from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any


def guess_video_mime_type(video_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(video_path)
    return mime_type or "video/mp4"


def load_video_base64(video_path: str | Path) -> tuple[str, str]:
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")
    mime_type = guess_video_mime_type(str(path))
    video_base64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return mime_type, video_base64


def extract_json(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        fence = "```"
        start = cleaned.find(fence)
        end = cleaned.rfind(fence)
        if end > start:
            block = cleaned[start + len(fence) : end]
            block = block.lstrip()
            if block.startswith("json"):
                block = block[len("json") :]
            return block.strip()
    return cleaned


def coerce_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
