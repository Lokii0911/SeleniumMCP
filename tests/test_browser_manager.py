from pathlib import Path

import pytest

from selenium_mcp_server.browser import BrowserError, BrowserManager
from selenium_mcp_server.config import Settings


def test_initial_state_without_browser() -> None:
    manager = BrowserManager(Settings(default_download_dir=Path("/tmp/selenium-test-downloads")))

    state = manager.state()

    assert state.session_id is None
    assert state.window_handles == []


def test_rejects_file_urls_by_default() -> None:
    manager = BrowserManager(Settings(default_download_dir=Path("/tmp/selenium-test-downloads")))

    with pytest.raises(BrowserError, match="URL scheme"):
        manager.navigate("file:///etc/passwd")


def test_rejects_http_url_without_hostname() -> None:
    manager = BrowserManager(Settings(default_download_dir=Path("/tmp/selenium-test-downloads")))

    with pytest.raises(BrowserError, match="hostname"):
        manager.navigate("https:///missing-host")


def test_allows_http_urls_before_driver_start() -> None:
    manager = BrowserManager(Settings(default_download_dir=Path("/tmp/selenium-test-downloads")))
    called = {}

    class FakeDriver:
        session_id = "session-1"
        current_url = "https://example.com"
        title = "Example"
        window_handles = ["window-1"]
        current_window_handle = "window-1"

        def get(self, url: str) -> None:
            called["url"] = url

    manager._driver = FakeDriver()  # type: ignore[assignment]

    state = manager.navigate("https://example.com")

    assert called["url"] == "https://example.com"
    assert state.current_url == "https://example.com"
