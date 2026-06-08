"""BGClient protocol + factory.

Brand Gravity is a live consumer-grade service consumed via /v1/context. The RAM
buckets are not yet connected, so the default provider serves slices from local
fixtures authored from the RAM Store Compilation. The HTTP provider hits the live
endpoint and is selected by config when the buckets come online. Both satisfy the
same contract; the downstream consumer cannot tell which path produced a response.
"""

from __future__ import annotations

from typing import Protocol

from ..config import Settings, get_settings
from ..schemas.bg import BGRequest, BGResponse


class BGClient(Protocol):
    def resolve(self, request: BGRequest) -> BGResponse:
        """Resolve the requested buckets into shaped slices (deepest scope wins)."""
        ...


def build_client(settings: Settings | None = None) -> BGClient:
    settings = settings or get_settings()
    if settings.bg_mode == "http":
        from .http_provider import HttpBGProvider

        return HttpBGProvider(base_url=settings.bg_base_url, api_key=settings.bg_api_key)
    # default: fixtures
    from .fixture_provider import FixtureBGProvider

    return FixtureBGProvider()
