from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BrowserName = Literal["chrome", "firefox", "edge"]
McpTransport = Literal["stdio", "streamable-http", "sse"]


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="SELENIUM_", env_file=".env", extra="ignore")

    browser: BrowserName = "chrome"
    headless: bool = True
    remote_url: str | None = None
    implicit_wait_seconds: float = Field(default=2, ge=0, le=60)
    page_load_timeout_seconds: float = Field(default=30, ge=1, le=300)
    script_timeout_seconds: float = Field(default=30, ge=1, le=300)
    window_width: int = Field(default=1440, ge=320, le=7680)
    window_height: int = Field(default=1000, ge=240, le=4320)
    allow_file_urls: bool = False
    default_download_dir: Path = Path("/tmp/selenium-downloads")
    http_host: str = "0.0.0.0"
    http_port: int = Field(default=8000, ge=1, le=65535)
    mcp_transport: McpTransport = "stdio"

    @field_validator("remote_url", mode="before")
    @classmethod
    def normalize_remote_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
