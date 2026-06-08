"""Environment-driven settings for the production pipeline agent."""

from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = three levels up from this file (src/director_agent/config.py).
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
FIXTURES_DIR = DATA_DIR / "bg_fixtures"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Director (Anthropic)
    anthropic_api_key: str = ""
    director_model: str = "claude-opus-4-8"
    director_max_tokens: int = 4096

    # Brand Gravity client
    bg_mode: str = "fixture"  # "fixture" | "http"
    bg_base_url: str = "https://bg-admin.donercolle.dev"
    bg_api_key: str = ""

    # Draft store. "local" = SQLite (dev); "upstash" = Upstash Redis (serverless).
    draft_store_backend: str = "local"
    draft_store_path: str = "data/draftstore.sqlite"
    # Working-project file. Point both stores at a mounted volume (e.g. /data) when hosted.
    project_store_path: str = "data/project.json"
    # Upstash creds are auto-injected by the Vercel Upstash integration. The
    # integration may name them UPSTASH_REDIS_REST_* or KV_REST_API_* — accept both.
    upstash_redis_rest_url: str = Field(
        "", validation_alias=AliasChoices("UPSTASH_REDIS_REST_URL", "KV_REST_API_URL")
    )
    upstash_redis_rest_token: str = Field(
        "", validation_alias=AliasChoices("UPSTASH_REDIS_REST_TOKEN", "KV_REST_API_TOKEN")
    )

    # On Vercel the filesystem is read-only except /tmp; set SUBSTANCE_OUT_PATH=/tmp/...
    substance_out_path: str = "out/substance_rows.xlsx"

    @property
    def draft_store_abspath(self) -> Path:
        return _resolve(self.draft_store_path)

    @property
    def project_store_abspath(self) -> Path:
        return _resolve(self.project_store_path)

    @property
    def substance_out_abspath(self) -> Path:
        return _resolve(self.substance_out_path)


def _resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else REPO_ROOT / path


_settings: Settings | None = None


def get_settings() -> Settings:
    """Cached settings accessor."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
