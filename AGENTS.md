# OpenCode AGENTS.md for qwen2API

## Architecture & Entrypoints
* **Monorepo Structure**: The repository contains both a FastAPI backend (`backend/`) and a React+Vite frontend (`frontend/`).
* **Main Entrypoint**: The script `start.py` in the root directory starts both the backend API (port `7860`) and the frontend Vite dev server (port `5174`).
* **Backend**: FastAPI application. The main entrypoint is `backend.main:app` (or `backend/main.py`). The backend exposes endpoints for Admin UI and proxies LLM requests.
* **Frontend**: React application built with Vite (`frontend/`). Uses `npm run dev` for the dev server.
* **Data Storage**: Local JSON files are used for persistence (stored in the `data/` directory). Settings and paths are loaded from `.env` and `backend.core.config`.

## Development Commands
* **Start Services**: `python start.py` (Runs both frontend and backend).
* **Frontend Dev**: `cd frontend && npm run dev`
* **Frontend Build**: `cd frontend && npm run build`
* **Backend Dev**: `cd backend && uvicorn backend.main:app --reload --port 7860` (Assuming `PYTHONPATH` includes the root directory).
* **Dependencies**:
  * Backend: `pip install -r backend/requirements.txt`
  * Frontend: `cd frontend && npm install`
* **Browser Requirement**: The backend requires `camoufox` for registration/activation which is installed via `python -m camoufox fetch`. (This is handled automatically by `start.py`).

## Environment & Configuration
* The project uses a `.env` file (copied from `.env.example`) to configure backend settings (ports, log levels, concurrency limits).
* Ensure `PYTHONPATH` is set to the workspace root when running python scripts inside `backend/`.

## Testing & Linting
* **Frontend Linting**: `cd frontend && npm run lint`
* No explicit backend testing or linting commands are specified in the provided files. Rely on standard Python tools (e.g., `flake8`, `pytest`) if added.

## Operational Quirks
* **Port Conflicts**: `start.py` includes a mechanism to kill existing processes on the backend port (default 7860) before starting.
* **Docker**: A `Dockerfile` and `docker-compose.yml` are provided in the root directory for containerized deployment. Use `docker-compose up -d`.
* **NPM Proxy Issue**: If the system has `HTTP_PROXY`/`HTTPS_PROXY` environment variables set, npm install will be extremely slow and may corrupt binary packages (like `@rollup/rollup-win32-x64-msvc`). `start.py` now automatically clears these env vars before running npm commands. If running npm manually, use: `$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; npm install`
* **aiofiles**: The backend uses `aiofiles` for async file I/O. Added to `backend/requirements.txt`.
* **Tool Call Retry Limits**: Qwen's server-side content filter detects obfuscated tool names (even with `u_` prefix) and blocks `##TOOL_CALL##` format. `blocked_tool_name` retries are capped at 1 (was unlimited). `repeated_same_tool` is capped at 1 retry. This prevents the `blocked -> retry -> tool_call -> retry -> blocked` infinite loop on complex tasks with MCP tools.
