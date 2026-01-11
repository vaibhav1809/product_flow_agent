from __future__ import annotations

from pydantic import BaseModel, Field


class ToolRequest(BaseModel):
    query: str
    app_id: str | None = None


class ToolResult(BaseModel):
    matches: list[dict[str, str]] = Field(default_factory=list)
    notes: str = ""
