# ── Build stage ──
FROM python:3.12-slim AS builder

WORKDIR /app

# Install git (needed for GitPython)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Copy backend
COPY backend/ ./backend/

# Install dependencies (server + llm, no local sentence-transformers)
RUN pip install --no-cache-dir ./backend[server,llm]

# ── Runtime stage ──
FROM python:3.12-slim

WORKDIR /app

# Install git runtime
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/backend /app/backend

# Create data directory
RUN mkdir -p /data/repomemory

# Environment
ENV REPOMEMORY_DATA_DIR=/data/repomemory \
    REPOMEMORY_EMBEDDING_PROVIDER=huggingface \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "repomemory.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
