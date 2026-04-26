from __future__ import annotations

import base64
import threading
from contextlib import suppress
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from selenium_mcp_server.config import Settings
from selenium_mcp_server.models import BrowserState, ElementSummary, LocatorStrategy, ScreenshotResult


LOCATOR_MAP: dict[LocatorStrategy, str] = {
    "id": By.ID,
    "name": By.NAME,
    "css selector": By.CSS_SELECTOR,
    "xpath": By.XPATH,
    "link text": By.LINK_TEXT,
    "partial link text": By.PARTIAL_LINK_TEXT,
    "tag name": By.TAG_NAME,
    "class name": By.CLASS_NAME,
}


class BrowserError(RuntimeError):
    """Raised when a browser action cannot be completed."""


class BrowserManager:
    """Thread-safe lifecycle wrapper around one Selenium WebDriver session."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._driver: WebDriver | None = None
        self._lock = threading.RLock()

    def start(self) -> BrowserState:
        with self._lock:
            if self._driver is None:
                self._settings.default_download_dir.mkdir(parents=True, exist_ok=True)
                self._driver = self._create_driver()
                self._configure_driver(self._driver)
            return self.state()

    def stop(self) -> dict[str, bool]:
        with self._lock:
            if self._driver is not None:
                with suppress(WebDriverException):
                    self._driver.quit()
                self._driver = None
            return {"stopped": True}

    def reset(self) -> BrowserState:
        with self._lock:
            self.stop()
            return self.start()

    def state(self) -> BrowserState:
        with self._lock:
            if self._driver is None:
                return BrowserState(
                    session_id=None,
                    current_url=None,
                    title=None,
                    window_handles=[],
                    active_window_handle=None,
                )
            return BrowserState(
                session_id=str(self._driver.session_id),
                current_url=self._driver.current_url,
                title=self._driver.title,
                window_handles=list(self._driver.window_handles),
                active_window_handle=self._driver.current_window_handle,
            )

    def navigate(self, url: str) -> BrowserState:
        self._validate_url(url)
        with self._lock:
            driver = self._require_driver()
            try:
                driver.get(url)
            except TimeoutException as exc:
                raise BrowserError(f"Timed out loading {url}") from exc
            return self.state()

    def back(self) -> BrowserState:
        with self._lock:
            self._require_driver().back()
            return self.state()

    def forward(self) -> BrowserState:
        with self._lock:
            self._require_driver().forward()
            return self.state()

    def refresh(self) -> BrowserState:
        with self._lock:
            self._require_driver().refresh()
            return self.state()

    def set_window_size(self, width: int, height: int) -> BrowserState:
        with self._lock:
            self._require_driver().set_window_size(width, height)
            return self.state()

    def open_new_tab(self, url: str | None = None) -> BrowserState:
        if url is not None:
            self._validate_url(url)
        with self._lock:
            driver = self._require_driver()
            driver.switch_to.new_window("tab")
            if url is not None:
                driver.get(url)
            return self.state()

    def switch_window(self, handle: str) -> BrowserState:
        with self._lock:
            self._require_driver().switch_to.window(handle)
            return self.state()

    def close_window(self) -> BrowserState:
        with self._lock:
            driver = self._require_driver()
            driver.close()
            if driver.window_handles:
                driver.switch_to.window(driver.window_handles[-1])
                return self.state()
            self._driver = None
            return self.state()

    def find_element(
        self,
        strategy: LocatorStrategy,
        value: str,
        timeout_seconds: float | None = None,
    ) -> ElementSummary:
        with self._lock:
            element = self._wait_for_element(strategy, value, timeout_seconds)
            return self._summarize_element(element)

    def click(
        self,
        strategy: LocatorStrategy,
        value: str,
        timeout_seconds: float | None = None,
    ) -> BrowserState:
        with self._lock:
            element = self._wait_for_element(strategy, value, timeout_seconds, clickable=True)
            element.click()
            return self.state()

    def type_text(
        self,
        strategy: LocatorStrategy,
        value: str,
        text: str,
        clear_first: bool = True,
        timeout_seconds: float | None = None,
    ) -> ElementSummary:
        with self._lock:
            element = self._wait_for_element(strategy, value, timeout_seconds)
            if clear_first:
                element.clear()
            element.send_keys(text)
            return self._summarize_element(element)

    def get_text(
        self,
        strategy: LocatorStrategy,
        value: str,
        timeout_seconds: float | None = None,
    ) -> dict[str, str]:
        with self._lock:
            element = self._wait_for_element(strategy, value, timeout_seconds)
            return {"text": element.text}

    def get_attribute(
        self,
        strategy: LocatorStrategy,
        value: str,
        attribute: str,
        timeout_seconds: float | None = None,
    ) -> dict[str, str | None]:
        with self._lock:
            element = self._wait_for_element(strategy, value, timeout_seconds)
            return {"attribute": attribute, "value": element.get_attribute(attribute)}

    def execute_script(self, script: str, args: list[Any] | None = None) -> dict[str, Any]:
        with self._lock:
            result = self._require_driver().execute_script(script, *(args or []))
            return {"result": result}

    def scroll(self, x: int = 0, y: int = 0) -> dict[str, Any]:
        with self._lock:
            result = self._require_driver().execute_script(
                "window.scrollBy(arguments[0], arguments[1]);"
                "return {x: window.scrollX, y: window.scrollY};",
                x,
                y,
            )
            return {"position": result}

    def page_source(self) -> dict[str, str]:
        with self._lock:
            return {"html": self._require_driver().page_source}

    def screenshot(self) -> ScreenshotResult:
        with self._lock:
            png = self._require_driver().get_screenshot_as_png()
            return ScreenshotResult(base64_png=base64.b64encode(png).decode("ascii"))

    def save_screenshot(self, path: str) -> dict[str, str]:
        output_path = Path(path).expanduser().resolve()
        with self._lock:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self._require_driver().save_screenshot(str(output_path))
            return {"path": str(output_path)}

    def cookies(self) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            return {"cookies": self._require_driver().get_cookies()}

    def add_cookie(self, cookie: dict[str, Any]) -> dict[str, bool]:
        with self._lock:
            self._require_driver().add_cookie(cookie)
            return {"added": True}

    def delete_cookies(self) -> dict[str, bool]:
        with self._lock:
            self._require_driver().delete_all_cookies()
            return {"deleted": True}

    def wait_for_element(
        self,
        strategy: LocatorStrategy,
        value: str,
        timeout_seconds: float = 10,
        visible: bool = True,
    ) -> ElementSummary:
        with self._lock:
            element = self._wait_for_element(strategy, value, timeout_seconds, visible=visible)
            return self._summarize_element(element)

    def _create_driver(self) -> WebDriver:
        if self._settings.remote_url:
            return webdriver.Remote(
                command_executor=self._settings.remote_url,
                options=self._browser_options(),
            )

        if self._settings.browser == "chrome":
            return webdriver.Chrome(options=self._browser_options())
        if self._settings.browser == "firefox":
            return webdriver.Firefox(options=self._browser_options())
        if self._settings.browser == "edge":
            return webdriver.Edge(options=self._browser_options())
        raise BrowserError(f"Unsupported browser: {self._settings.browser}")

    def _browser_options(self) -> Any:
        if self._settings.browser == "chrome":
            options = webdriver.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument(f"--window-size={self._settings.window_width},{self._settings.window_height}")
            prefs = {
                "download.default_directory": str(self._settings.default_download_dir),
                "download.prompt_for_download": False,
            }
            options.add_experimental_option("prefs", prefs)
        elif self._settings.browser == "firefox":
            options = webdriver.FirefoxOptions()
            options.set_preference("browser.download.folderList", 2)
            options.set_preference("browser.download.dir", str(self._settings.default_download_dir))
        elif self._settings.browser == "edge":
            options = webdriver.EdgeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"--window-size={self._settings.window_width},{self._settings.window_height}")
        else:
            raise BrowserError(f"Unsupported browser: {self._settings.browser}")

        if self._settings.headless:
            if self._settings.browser == "firefox":
                options.add_argument("-headless")
            else:
                options.add_argument("--headless=new")
        return options

    def _configure_driver(self, driver: WebDriver) -> None:
        driver.implicitly_wait(self._settings.implicit_wait_seconds)
        driver.set_page_load_timeout(self._settings.page_load_timeout_seconds)
        driver.set_script_timeout(self._settings.script_timeout_seconds)
        with suppress(WebDriverException):
            driver.set_window_size(self._settings.window_width, self._settings.window_height)

    def _require_driver(self) -> WebDriver:
        if self._driver is None:
            return self.start_driver_only()
        return self._driver

    def start_driver_only(self) -> WebDriver:
        self.start()
        if self._driver is None:
            raise BrowserError("Browser session failed to start")
        return self._driver

    def _wait_for_element(
        self,
        strategy: LocatorStrategy,
        value: str,
        timeout_seconds: float | None,
        *,
        clickable: bool = False,
        visible: bool = True,
    ) -> WebElement:
        driver = self._require_driver()
        by = LOCATOR_MAP[strategy]
        timeout = timeout_seconds if timeout_seconds is not None else self._settings.page_load_timeout_seconds
        condition = EC.presence_of_element_located((by, value))
        if clickable:
            condition = EC.element_to_be_clickable((by, value))
        elif visible:
            condition = EC.visibility_of_element_located((by, value))
        try:
            return WebDriverWait(driver, timeout).until(condition)
        except TimeoutException as exc:
            raise BrowserError(f"Element not found: {strategy}={value}") from exc

    def _summarize_element(self, element: WebElement) -> ElementSummary:
        attributes = self._require_driver().execute_script(
            """
            const el = arguments[0];
            const attrs = {};
            for (const attr of el.attributes) attrs[attr.name] = attr.value;
            return attrs;
            """,
            element,
        )
        return ElementSummary(
            tag_name=element.tag_name,
            text=element.text,
            enabled=element.is_enabled(),
            displayed=element.is_displayed(),
            selected=element.is_selected(),
            attributes=attributes or {},
        )

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        allowed_schemes = {"http", "https"}
        if self._settings.allow_file_urls:
            allowed_schemes.add("file")
        if parsed.scheme not in allowed_schemes:
            raise BrowserError(f"URL scheme must be one of: {', '.join(sorted(allowed_schemes))}")
        if parsed.scheme in {"http", "https"} and not parsed.netloc:
            raise BrowserError("HTTP and HTTPS URLs must include a hostname")
