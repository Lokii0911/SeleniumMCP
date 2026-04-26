from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from selenium_mcp_server.browser import BrowserError, BrowserManager
from selenium_mcp_server.config import get_settings
from selenium_mcp_server.models import LocatorStrategy

logger = logging.getLogger(__name__)
settings = get_settings()
browser = BrowserManager(settings)
mcp = FastMCP(
    "selenium-mcp-server",
    host=settings.http_host,
    port=settings.http_port,
    json_response=True,
)


def _as_dict(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _run(action: str, func: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return _as_dict(func(*args, **kwargs))
    except BrowserError:
        logger.exception("Browser action failed: %s", action)
        raise
    except Exception as exc:
        logger.exception("Unexpected Selenium MCP error during %s", action)
        raise BrowserError(f"{action} failed: {exc}") from exc


@mcp.tool()
def browser_start() -> dict[str, Any]:
    """Start a Selenium browser session if one is not already running."""
    return _run("browser_start", browser.start)


@mcp.tool()
def browser_stop() -> dict[str, bool]:
    """Stop the current Selenium browser session."""
    return _run("browser_stop", browser.stop)


@mcp.tool()
def browser_reset() -> dict[str, Any]:
    """Restart the Selenium browser session."""
    return _run("browser_reset", browser.reset)


@mcp.tool()
def browser_state() -> dict[str, Any]:
    """Return session id, URL, title, and window information."""
    return _run("browser_state", browser.state)


@mcp.tool()
def navigate(url: str) -> dict[str, Any]:
    """Navigate the browser to an http, https, or allowed file URL."""
    return _run("navigate", browser.navigate, url)


@mcp.tool()
def go_back() -> dict[str, Any]:
    """Navigate one step back in browser history."""
    return _run("go_back", browser.back)


@mcp.tool()
def go_forward() -> dict[str, Any]:
    """Navigate one step forward in browser history."""
    return _run("go_forward", browser.forward)


@mcp.tool()
def refresh() -> dict[str, Any]:
    """Refresh the current page."""
    return _run("refresh", browser.refresh)


@mcp.tool()
def set_window_size(width: int, height: int) -> dict[str, Any]:
    """Set the browser window size."""
    return _run("set_window_size", browser.set_window_size, width, height)


@mcp.tool()
def open_new_tab(url: str | None = None) -> dict[str, Any]:
    """Open a new browser tab and optionally navigate it to a URL."""
    return _run("open_new_tab", browser.open_new_tab, url)


@mcp.tool()
def switch_window(handle: str) -> dict[str, Any]:
    """Switch to a browser window or tab by Selenium window handle."""
    return _run("switch_window", browser.switch_window, handle)


@mcp.tool()
def close_window() -> dict[str, Any]:
    """Close the active browser window or tab."""
    return _run("close_window", browser.close_window)


@mcp.tool()
def find_element(
    strategy: LocatorStrategy,
    value: str,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Find an element and return a compact summary of it."""
    return _run("find_element", browser.find_element, strategy, value, timeout_seconds)


@mcp.tool()
def click(
    strategy: LocatorStrategy,
    value: str,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Click an element located by CSS selector, XPath, id, name, text, tag, or class."""
    return _run("click", browser.click, strategy, value, timeout_seconds)


@mcp.tool()
def type_text(
    strategy: LocatorStrategy,
    value: str,
    text: str,
    clear_first: bool = True,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Type text into an element, optionally clearing it first."""
    return _run("type_text", browser.type_text, strategy, value, text, clear_first, timeout_seconds)


@mcp.tool()
def get_text(
    strategy: LocatorStrategy,
    value: str,
    timeout_seconds: float | None = None,
) -> dict[str, str]:
    """Return the visible text for an element."""
    return _run("get_text", browser.get_text, strategy, value, timeout_seconds)


@mcp.tool()
def get_attribute(
    strategy: LocatorStrategy,
    value: str,
    attribute: str,
    timeout_seconds: float | None = None,
) -> dict[str, str | None]:
    """Return one DOM attribute for an element."""
    return _run("get_attribute", browser.get_attribute, strategy, value, attribute, timeout_seconds)


@mcp.tool()
def wait_for_element(
    strategy: LocatorStrategy,
    value: str,
    timeout_seconds: float = 10,
    visible: bool = True,
) -> dict[str, Any]:
    """Wait until an element exists, or until it is visible when requested."""
    return _run(
        "wait_for_element",
        browser.wait_for_element,
        strategy,
        value,
        timeout_seconds,
        visible,
    )


@mcp.tool()
def execute_script(script: str, args: list[Any] | None = None) -> dict[str, Any]:
    """Execute JavaScript in the active page and return the JSON-serializable result."""
    return _run("execute_script", browser.execute_script, script, args)


@mcp.tool()
def scroll(x: int = 0, y: int = 0) -> dict[str, Any]:
    """Scroll the current page by the given x and y offsets."""
    return _run("scroll", browser.scroll, x, y)


@mcp.tool()
def page_source() -> dict[str, str]:
    """Return the current page HTML."""
    return _run("page_source", browser.page_source)


@mcp.tool()
def screenshot() -> dict[str, str]:
    """Return a PNG screenshot as base64."""
    return _run("screenshot", browser.screenshot)


@mcp.tool()
def save_screenshot(path: str) -> dict[str, str]:
    """Save a PNG screenshot to a server-local path and return the path."""
    return _run("save_screenshot", browser.save_screenshot, path)


@mcp.tool()
def list_cookies() -> dict[str, list[dict[str, Any]]]:
    """Return browser cookies for the current domain."""
    return _run("list_cookies", browser.cookies)


@mcp.tool()
def add_cookie(cookie: dict[str, Any]) -> dict[str, bool]:
    """Add a Selenium cookie dict to the current domain."""
    return _run("add_cookie", browser.add_cookie, cookie)


@mcp.tool()
def delete_cookies() -> dict[str, bool]:
    """Delete all browser cookies."""
    return _run("delete_cookies", browser.delete_cookies)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if settings.mcp_transport == "stdio":
        mcp.run()
    elif settings.mcp_transport == "streamable-http":
        mcp.run(transport="streamable-http", host=settings.http_host, port=settings.http_port)
    else:
        mcp.run(transport="sse", host=settings.http_host, port=settings.http_port)


if __name__ == "__main__":
    main()
