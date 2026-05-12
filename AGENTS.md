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
docker compose up -d

# Or build locally
docker build -t wqwen2api .
docker compose up -d

# Deploy (from local to server)
# Local:
docker build -t movemama/wqwen2api:latest .
docker push movemama/wqwen2api:latest
# Server:
docker pull movemama/wqwen2api:latest && docker compose down && docker compose up -d
```
* `WORKERS` must stay `1` — AsyncJsonDB does not support multiprocess writes.
* On Windows with proxy (`HTTP_PROXY`), add `--build-arg HTTP_PROXY=http://host.docker.internal:PORT` to `docker build`.
* Server uses `docker compose` (no hyphen) — Docker Compose V2.

## Tool Calling (DSML Format)
* Qwen outputs tool calls in **`<|DSML|tool_calls>`** format (instead of `##TOOL_CALL##`) to bypass server-side filter.
* Parser: `backend/toolcall/formats_dsml.py`, integrated into `parser.py`.
* Tool names are obfuscated with `qt_` prefix (changed from `u_` which Qwen now detects).
* Alias matching is case-insensitive (both `bash` and `Bash` map to `shell_run`).
* **Stop Notice**: When 3+ valid tool results accumulate, a `[FINAL ANSWER REQUIRED]` note is injected into the prompt.
* **Retry Caps**: `request_max_attempts` = 2 (was 4). `blocked_tool_name` retries limited to 1.
* **Task/Agent forbidden**: Prompt explicitly tells Qwen not to delegate to `Task`/`Agent` tools.

## Tool Parameter Coercion (3 layers)
Qwen hallucinates wrong parameter names (e.g. `path` instead of `filePath`, `content` instead of `file_text`). Three-layer fix:

| Layer | File | Scope | Mechanism |
|-------|------|-------|-----------|
| **1. Hardcoded** | `tool_parser.py:_coerce_tool_input` | 8 priority tools (Read/Write/Edit/Bash/Grep/Glob/WebSearch/WebFetch) | Explicit alias loops per tool |
| **2. Static aliases** | `tool_arg_fixer.py:_PARAM_ALIASES` | Obfuscated names (`fs_put_file`, `shell_run`, etc.) | `fix_tool_call_arguments()` runs after coercion |
| **3. Auto-coercion** | `tool_parser.py:_auto_map_param_aliases` | **ALL tools** (any IDE) | Reads tool schema → maps missing required params from `_PARAM_ALIAS_RULES` |

**Critical**: Write/Edit/Read tools expect **camelCase** `filePath` (not `file_path`). Coercion maps all variants:
- `path` / `filepath` / `file_path` / `filePath` → `filePath`
- `file_text` / `text` / `data` → `content`
- `old_str` / `new_str` → `old_string` / `new_string`
- `query` / `search` → `pattern` (Grep)
- `cmd` / `script` → `command` (Bash)
- `q` / `search_query` → `query` (WebSearch)
- `link` / `fetch_url` → `url` (WebFetch)

## Refusal Text Cleaning (dual-layer)
Qwen hallucinates "Tool X does not exists" as context grows. Two-layer defense:

| Layer | File | Mechanism |
|-------|------|-----------|
| **Fragment-level** | `execution.py:554-563` | Strips toxic text from SSE fragments before accumulation. Prevents early/intermediate detection from triggering retry loops. |
| **Final cleanup** | `execution.py:484-501` | `_REFUSAL_TEXT` regex strips refusal lines from `answer_text` in `_finalize_result` BEFORE `extract_blocked_tool_names`. Empty `blocked_tool_names` avoids hard 1-retry stop, falls through to `empty_upstream_response` retry (2 attempts). |

Both layers use regex patterns matching: `Tool X does not exists?`, `I cannot execute this tool`, `工具不存在`, `无法调用...工具`, etc.

## Context Bloat Prevention
Qwen 3.6-plus degrades at ~13KB+ context and starts hallucinating. Mitigations:

| Setting | Old | New | Reason |
|---------|-----|-----|--------|
| `tool_result_limit` | 6000 chars | 2500 chars | 3 calls max 7.5KB vs 18KB |
| `MAX_HISTORY_TURNS` | 15 | 8 | Fewer old turns = less context |
| FORBIDDEN format block | 8 lines | 1 line | Saves ~500 chars/turn |
| `##TOOL_CALL##` reference | removed | `(supersedes ##TOOL_CALL##)` | Suppresses upstream filter warning |

## IDE Compatibility
Gateway exposes standard **OpenAI-compatible API** (`/v1/chat/completions`). Works with:
- OpenCode / Claude Code
- Cursor / Windsurf / Cline / Continue / Aider
- Any IDE with custom OpenAI endpoint

Auto-coercion (layer 3) makes it work for **any IDE's tools without per-IDE config**. Tool names are de-obfuscated before coercion, so all clients use original names internally.

## Key Files
| File | Role |
|------|------|
| `backend/runtime/execution.py` | Retry logic, refusal text cleaning (fragment + final), completion runner |
| `backend/services/prompt_builder.py` | Prompt construction, DSML format, context trimming, tool instructions |
| `backend/services/tool_parser.py` | Tool call parsing, `_coerce_tool_input` (3-layer param fixing), auto-coercion |
| `backend/services/tool_arg_fixer.py` | `_PARAM_ALIASES` static mapping, `fix_tool_call_arguments()` |
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
* **Qwen refuses tools**: Context > 13KB causes hallucination "Tool X does not exists". Fragment cleaning strips it. If persistent, reduce prompt size or restart conversation.
* **File write/edit fails with SchemaError**: Check `##TOOL_CALL##` warning — if absent, Qwen server may filter. If present, parameter names may need coercion (see Tool Parameter Coercion above).
* **Silent request death after stream end**: `parse_tool_calls_silent` crash. Check try-except at `execution.py:429`. Log shows `[Collect] 最终文本解析异常崩溃`.
