from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from ..pipeline.base import PipelineContext


class JsonStore(BaseModel):
    path: Path

    def save_context(self, context: PipelineContext) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = context.to_jsonable()
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_context(self) -> PipelineContext:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Stored context must be a JSON object.")
        return PipelineContext.model_validate(payload)
