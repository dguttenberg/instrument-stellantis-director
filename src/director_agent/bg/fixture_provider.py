"""Fixture-backed Brand Gravity provider.

Serves slices from data/bg_fixtures, authored from the RAM Store Compilation.
Implements deepest-scope-wins resolution (lane override beats brand baseline),
light filter handling (product_catalog sku, environmental_context season), per-run
caching, and gap flagging when a requested bucket has no authored fixture.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import FIXTURES_DIR
from ..schemas.bg import BGRequest, BGResponse, BucketNeeded, Slice
from .cache import SliceCache


class FixtureBGProvider:
    def __init__(self, fixtures_dir: Optional[Path] = None) -> None:
        self.fixtures_dir = fixtures_dir or FIXTURES_DIR
        self._by_bucket: Dict[str, List[dict]] = {}
        self._cache = SliceCache()
        self._load()

    def _load(self) -> None:
        for path in sorted(self.fixtures_dir.rglob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            bucket = data["bucket"]
            self._by_bucket.setdefault(bucket, []).append(data)

    # ----------------------------------------------------------------- #
    def resolve(self, request: BGRequest) -> BGResponse:
        slices: Dict[str, Slice] = {}
        gaps: List[str] = []

        for need in request.buckets_needed:
            cache_key = SliceCache.key(
                request.brand, request.lane, need.bucket, need.scope, need.filters
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                key, sl = cached
                slices[key] = sl
                continue

            resolved = self._resolve_one(request, need)
            if resolved is None:
                gaps.append(f"{need.bucket}@{need.scope} (no authored fixture)")
                continue

            self._cache.put(cache_key, resolved)
            slices[resolved[0]] = resolved[1]

        return BGResponse(
            request_id=request.request_id,
            resolved_at=datetime.now(timezone.utc).isoformat(),
            slices=slices,
            gaps_flagged=gaps,
        )

    # ----------------------------------------------------------------- #
    def _resolve_one(self, request: BGRequest, need: BucketNeeded):
        candidates = self._by_bucket.get(need.bucket, [])
        if not candidates:
            return None

        fixture, scope_resolved = self._pick(candidates, request, need)
        if fixture is None:
            return None

        content = fixture.get("content")
        sku = None
        if need.filters:
            content, sku = self._apply_filters(need.bucket, content, need.filters)

        brand = fixture.get("brand")
        lane = fixture.get("lane")
        key = self._slice_key(need.bucket, brand, lane, scope_resolved, sku)
        sl = Slice(
            scope_resolved=scope_resolved,
            confidence=fixture.get("confidence", "medium"),
            content=content,
            provenance=fixture.get("provenance", []),
            notes_for_consumers=fixture.get("notes_for_consumers"),
        )
        return key, sl

    def _pick(self, candidates: List[dict], request: BGRequest, need: BucketNeeded):
        """Deepest-scope-wins. For a lane request, prefer a lane fixture matching
        the brand; fall back to the brand baseline (lane is null)."""

        def brand_ok(f: dict) -> bool:
            fb = f.get("brand")
            return fb is None or fb == request.brand

        if need.scope == "lane":
            for f in candidates:
                if f.get("lane") == request.lane and brand_ok(f):
                    return f, "lane"
            # fall back to brand baseline
            for f in candidates:
                if f.get("lane") is None and brand_ok(f):
                    return f, "brand"
            return None, ""

        # scope == "brand" (or anything else): brand-level fixture
        for f in candidates:
            if f.get("lane") is None and brand_ok(f):
                return f, "brand"
        # last resort: any candidate
        return (candidates[0], candidates[0].get("scope", "brand")) if candidates else (None, "")

    @staticmethod
    def _apply_filters(bucket: str, content: Any, filters: Dict[str, Any]):
        """Return (filtered_content, sku). Light, bucket-specific handling."""
        sku = None
        if bucket == "environmental_context" and "season" in filters and isinstance(content, dict):
            season = filters["season"]
            seasons = content.get("seasons", {})
            if season in seasons:
                content = {"lane_label": content.get("lane_label"), **seasons[season]}
        elif bucket == "product_catalog" and "sku" in filters and isinstance(content, dict):
            sku = filters["sku"]
            trim = content.get("trims", {}).get(sku)
            if trim is not None:
                # Trim-focused view: shared fields + the specific trim (spec §4 example).
                content = {
                    "nameplate": trim.get("nameplate") or content.get("nameplate"),
                    "sku": sku,
                    "trim_label": trim.get("trim_label"),
                    "specific_trim_request": trim.get("specific_trim_request"),
                    "available_hex": content.get("available_hex"),
                    "hex_names": content.get("hex_names"),
                    "available_camera_angles": content.get("available_camera_angles"),
                    "claims_hierarchy": content.get("claims_hierarchy"),
                    "legal_disclaimers": content.get("legal_disclaimers"),
                    "mandatory_sponsor_signoff": content.get("mandatory_sponsor_signoff"),
                    "hurricane_cylinder_rule": content.get("hurricane_cylinder_rule"),
                    "brand_truths": content.get("brand_truths"),
                }
        return content, sku

    @staticmethod
    def _slice_key(bucket: str, brand, lane, scope_resolved: str, sku) -> str:
        parts = [bucket]
        if scope_resolved == "lane" and lane:
            parts.append(lane)
        if brand:
            parts.append(brand)
        if sku:
            parts.append(sku)
        return ".".join(parts)
