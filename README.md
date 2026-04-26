# Selenium MCP Server

Deployment-ready Python MCP server for Selenium browser automation. It supports local STDIO usage and production-style Streamable HTTP at `/mcp`, plus health endpoints for container platforms.

## Tools

- `browser_start`, `browser_stop`, `browser_reset`, `browser_state`
- `navigate`, `go_back`, `go_forward`, `refresh`
- `set_window_size`, `open_new_tab`, `switch_window`, `close_window`
- `find_element`, `wait_for_element`, `click`, `type_text`
- `get_text`, `get_attribute`, `execute_script`, `scroll`
- `page_source`, `screenshot`, `save_screenshot`
- `list_cookies`, `add_cookie`, `delete_cookies`

Locator strategies: `id`, `name`, `css selector`, `xpath`, `link text`, `partial link text`, `tag name`, `class name`.

## HTTP Endpoints

- `POST /mcp` and related Streamable HTTP MCP calls
- `GET /healthz`
- `GET /readyz`
- `POST /browser/start`
- `POST /browser/stop`

## Local Setup

### Windows Python Prerequisite

If PowerShell says `Python was not found`, install Python 3.11+ first. The quickest options are:

```powershell
winget install Python.Python.3.12
```

Then close and reopen PowerShell. If `python --version` still opens the Microsoft Store prompt, disable the `python.exe` and `python3.exe` app execution aliases in:

```text
Settings > Apps > Advanced app settings > App execution aliases
```

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Run as a local STDIO MCP server:

```bash
selenium-mcp
```

Run as a Streamable HTTP MCP server:

```bash
selenium-mcp-http
```

Then connect MCP clients to:

```text
http://localhost:8000/mcp
```

## Claude Desktop Example

```json
{
  "mcpServers": {
    "selenium": {
      "command": "selenium-mcp",
      "env": {
        "SELENIUM_BROWSER": "chrome",
        "SELENIUM_HEADLESS": "true"
      }
    }
  }
}
```

## Docker

Build and run with an in-container Chromium browser:

```bash
docker build -t selenium-mcp .
docker run --rm -p 8000:8000 selenium-mcp
```

Run with a dedicated Selenium Grid browser container:

```bash
docker compose up --build
```

## Configuration

Copy `.env.example` to `.env` and adjust:

```text
SELENIUM_BROWSER=chrome
SELENIUM_HEADLESS=true
SELENIUM_REMOTE_URL=
SELENIUM_IMPLICIT_WAIT_SECONDS=2
SELENIUM_PAGE_LOAD_TIMEOUT_SECONDS=30
SELENIUM_SCRIPT_TIMEOUT_SECONDS=30
SELENIUM_WINDOW_WIDTH=1440
SELENIUM_WINDOW_HEIGHT=1000
SELENIUM_ALLOW_FILE_URLS=false
SELENIUM_DEFAULT_DOWNLOAD_DIR=/tmp/selenium-downloads
SELENIUM_HTTP_HOST=0.0.0.0
SELENIUM_HTTP_PORT=8000
SELENIUM_MCP_TRANSPORT=stdio
```

For remote Selenium Grid, set:

```text
SELENIUM_REMOTE_URL=http://selenium:4444/wd/hub
```

## Security Notes

This server can browse the web, execute JavaScript, read page HTML, and save screenshots on the host. In production, run it in a locked-down container or VM, restrict outbound network access, keep `SELENIUM_ALLOW_FILE_URLS=false`, and put the HTTP MCP endpoint behind your platform authentication layer.

## Validation

```bash
ruff check .
pytest
```
