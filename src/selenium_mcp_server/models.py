from typing import Any, Literal

from pydantic import BaseModel, Field


LocatorStrategy = Literal[
    "id",
    "name",
    "css selector",
    "xpath",
    "link text",
    "partial link text",
    "tag name",
    "class name",
]


class BrowserState(BaseModel):
    session_id: str | None
    current_url: str | None
    title: str | None
    window_handles: list[str]
    active_window_handle: str | None


class ElementSummary(BaseModel):
    tag_name: str
    text: str
    enabled: bool
    displayed: bool
    selected: bool
    attributes: dict[str, Any] = Field(default_factory=dict)


class ScreenshotResult(BaseModel):
    mime_type: str = "image/png"
    base64_png: str
