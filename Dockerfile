# Persistent-container image (Render / Railway / Fly). Editable install keeps the
# src layout so REPO_ROOT, the bundled data/ fixtures, and static/index.html resolve.
FROM python:3.12-slim

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -e .

# Hosted defaults. Point the stateful stores at /data (mount a persistent volume there).
# ANTHROPIC_API_KEY and APP_PASSWORD are set as host env vars, never baked in.
ENV BG_MODE=fixture \
    DRAFT_STORE_BACKEND=local \
    DRAFT_STORE_PATH=/data/draftstore.sqlite \
    PROJECT_STORE_PATH=/data/project.json \
    SUBSTANCE_OUT_PATH=/tmp/substance_rows.xlsx

EXPOSE 8000
# Hosts inject $PORT; default 8000 locally. mkdir keeps it working even without a volume.
CMD ["sh", "-c", "mkdir -p /data && uvicorn director_agent.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
