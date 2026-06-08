"""Draft store: confidence-driven review gate behind a swappable adapter."""

from __future__ import annotations

from ..config import Settings, get_settings
from .store import DraftRecord, DraftStore, compute_review_status
from .local_store import LocalDraftStore
from .upstash_store import UpstashDraftStore

__all__ = [
    "DraftRecord",
    "DraftStore",
    "compute_review_status",
    "LocalDraftStore",
    "UpstashDraftStore",
    "build_draft_store",
]


def build_draft_store(settings: Settings | None = None) -> DraftStore:
    """Select the draft store backend from config: 'upstash' for serverless
    (Vercel) deploys, 'local' SQLite for development (default)."""
    settings = settings or get_settings()
    if settings.draft_store_backend == "upstash":
        return UpstashDraftStore(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token,
        )
    return LocalDraftStore(settings.draft_store_abspath)
