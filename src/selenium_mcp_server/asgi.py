from __future__ import annotations

import contextlib
import logging

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from selenium_mcp_server.config import get_settings
from selenium_mcp_server.server import browser, mcp

settings = get_settings()


async def healthz(request) -> JSONResponse:  # noqa: ANN001
    return JSONResponse({"status": "ok"})


async def readyz(request) -> JSONResponse:  # noqa: ANN001
    state = browser.state()
    return JSONResponse(
        {
            "status": "ready",
            "browser_started": state.session_id is not None,
            "browser": settings.browser,
            "remote": settings.remote_url is not None,
            "mcp_endpoint": "/mcp",
        }
    )


async def start_browser(request) -> JSONResponse:  # noqa: ANN001
    return JSONResponse(browser.start().model_dump())


async def stop_browser(request) -> JSONResponse:  # noqa: ANN001
    return JSONResponse(browser.stop())


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):  # noqa: ANN001
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Route("/healthz", healthz, methods=["GET"]),
        Route("/readyz", readyz, methods=["GET"]),
        Route("/browser/start", start_browser, methods=["POST"]),
        Route("/browser/stop", stop_browser, methods=["POST"]),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    uvicorn.run(app, host=settings.http_host, port=settings.http_port)


if __name__ == "__main__":
    main()
