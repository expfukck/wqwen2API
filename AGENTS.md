# OpenCode AGENTS.md for wqwen2API

## Architecture
* **Backend** (`backend/`): FastAPI app, entry: `backend/main.py`, port `7860`
* **Frontend** (`frontend/`): React + Vite, dev on port `5174`
* **Startup**: `python start.py` starts both backend + frontend
* **Data**: JSON files under `data/`, loaded via `AsyncJsonDB` (async I/O with `aiofiles`)

## Docker
```bash
# Pull & run
docker pull movemama/wqwen2api:latest
docker-compose up -d

# Or build locally
docker build -t wqwen2api .
docker-compose up -d
```
* `WORKERS` must stay `1` — AsyncJsonDB does not support multiprocess writes.
* On Windows with proxy (`HTTP_PROXY`), add `--build-arg HTTP_PROXY=http://host.docker.internal:PORT` to `docker build`.

## Tool Calling (DSML Format)
* Qwen outputs tool calls in **`<|DSML|tool_calls>`** format (instead of `##TOOL_CALL##`) to bypass server-side filter.
* Parser: `backend/toolcall/formats_dsml.py`, integrated into `parser.py`.
* Tool names are obfuscated with `qt_` prefix (changed from `u_` which Qwen now detects).
* Alias matching is case-insensitive (both `bash` and `Bash` map to `shell_run`).
* **Stop Notice**: When 3+ valid tool results accumulate, a `[FINAL ANSWER REQUIRED]` note is injected into the prompt.
* **Retry Caps**: `request_max_attempts` = 2 (was 4). `blocked_tool_name` retries limited to 1.
* **Task/Agent forbidden**: Prompt explicitly tells Qwen not to delegate to `Task`/`Agent` tools.

## Key Files
| File | Role |
|------|------|
| `backend/runtime/execution.py` | Retry logic, tool marker cleanup, completion runner |
| `backend/services/prompt_builder.py` | Prompt construction, DSML format, stop notice, tool instructions |
| `backend/services/tool_name_obfuscation.py` | `qt_` prefix mapping, case-insensitive aliases |
| `backend/toolcall/formats_dsml.py` | `<|DSML|tool_calls>` parser |
| `backend/toolcall/parser.py` | Multi-format tool call detection (DSML > JSON > XML > textkv) |
| `backend/core/database.py` | AsyncJsonDB with `aiofiles` |
| `backend/core/config.py` | Pydantic V2 `model_config`, `WORKERS` default = 1 |

## Environment
* Copy `.env.example` to `.env`, configure `PORT`, `LOG_LEVEL`, `MAX_INFLIGHT`, admin key.
* `PYTHONPATH` must include project root when running scripts from `backend/`.

## Common Issues
* **NPM hangs**: System proxy env vars (`HTTP_PROXY`) slow npm. `start.py` clears them automatically.
* **Frontend 404**: Build frontend first: `cd frontend && npm run build`.
* **Docker apt-get fails**: Pass proxy build args to Docker.
