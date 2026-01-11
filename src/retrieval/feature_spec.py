from __future__ import annotations

from pydantic import BaseModel, Field


class FeatureSpec(BaseModel):
    query: str
    user_role: str | None = None
    change_scale: str | None = None
    keywords: list[str] = Field(default_factory=list)
