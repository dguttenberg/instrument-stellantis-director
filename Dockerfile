# Two-stage build: compile the Next.js front end to a static export, then serve
# it (and the API) from one FastAPI service. Single origin → no CORS, and the
# APP_PASSWORD gate covers the SPA and the API together.

# --- Stage 1: build the React/Next front end to a static export (web/out) ---
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
# STATIC_EXPORT=1 → next.config emits `output: "export"` and drops the dev rewrites.
# API base is unset here, so the client calls same-origin paths (/lanes, /run/cell…).
ENV STATIC_EXPORT=1
RUN npm run build

# --- Stage 2: the FastAPI app, serving the built SPA + the API ---
# Editable install keeps the src layout so REPO_ROOT, the bundled data/ fixtures,
# and static/index.html resolve.
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -e .
# Drop in the built SPA; app.py serves it at / (WEB_DIST) when present.
COPY --from=web /web/out /app/web/out

# Hosted defaults. Point the stateful stores at /data (mount a persistent volume there).
# ANTHROPIC_API_KEY and APP_PASSWORD are set as host env vars, never baked in.
ENV BG_MODE=fixture \
    DRAFT_STORE_BACKEND=local \
    DRAFT_STORE_PATH=/data/draftstore.sqlite \
    PROJECT_STORE_PATH=/data/project.json \
    SUBSTANCE_OUT_PATH=/tmp/substance_rows.xlsx \
    WEB_DIST=/app/web/out

EXPOSE 8000
# Hosts inject $PORT; default 8000 locally. mkdir keeps it working even without a volume.
CMD ["sh", "-c", "mkdir -p /data && uvicorn director_agent.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
