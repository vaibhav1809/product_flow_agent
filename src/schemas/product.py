from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NamedEntity(BaseModel):
    id: str
    name: str
    description: str = ""


class App(BaseModel):
    id: str
    name: str
    description: str = ""


class Screen(NamedEntity):
    pass


class Component(NamedEntity):
    pass


class Flow(NamedEntity):
    pass


class Integration(NamedEntity):
    pass


class Feature(BaseModel):
    id: str
    name: str
    description: str = ""
    start_timestamp: str = ""
    end_timestamp: str = ""
    flows: list[Flow] = Field(default_factory=list)
    screens: list[Screen] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    failure_criteria: list[str] = Field(default_factory=list)


class ProductContext(BaseModel):
    app: App | None = None
    features: list[Feature] = Field(default_factory=list)
    transcript: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
