# syntax=docker/dockerfile:1.7

# Stage 1: Build frontend
FROM --platform=$BUILDPLATFORM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Runtime — minimal Alpine
FROM python:3.12-alpine
WORKDIR /workspace

ENV PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860 \
    WORKERS=1 \
    LOG_LEVEL=INFO \
    PYTHONPATH=/workspace

# Minimal system deps for healthcheck
RUN apk add --no-cache curl

# Install only needed Python deps (skip camoufox/oss2 for proxy-only mode)
RUN pip install fastapi uvicorn[standard] httpx[http2] pydantic-settings \
    python-dotenv python-multipart tiktoken curl_cffi aiofiles

COPY backend/ ./backend/
COPY start.py ./
COPY --from=frontend-builder /app/dist ./frontend/dist
RUN mkdir -p /workspace/data /workspace/logs /workspace/frontend

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-7860}/healthz" || exit 1

CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1"]
