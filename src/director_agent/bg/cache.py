"""Per-run slice cache, keyed by (brand, lane, bucket, scope, filters_hash).

Most cells in the same script pull the same environmental_context slice, so the
cache makes resolves sub-second after the first call (spec §4 caching guidance).
Director responses are never cached — every cell is unique.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional, Tuple

from ..schemas.bg import Slice

# Cached value is the resolved (slice_key, Slice) so a cache hit reproduces the
# exact response entry without re-deriving the key from a key-less Slice.
CachedSlice = Tuple[str, Slice]


def filters_hash(filters: Optional[Dict[str, Any]]) -> str:
    if not filters:
        return "none"
    canonical = json.dumps(filters, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]


class SliceCache:
    def __init__(self) -> None:
        self._store: Dict[tuple, CachedSlice] = {}

    @staticmethod
    def key(brand: str, lane: str, bucket: str, scope: str, filters: Optional[Dict[str, Any]]) -> tuple:
        return (brand, lane, bucket, scope, filters_hash(filters))

    def get(self, key: tuple) -> Optional[CachedSlice]:
        return self._store.get(key)

    def put(self, key: tuple, value: CachedSlice) -> None:
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()
