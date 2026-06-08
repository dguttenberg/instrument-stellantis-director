"""Fixture provider: scope resolution, filters, gaps, caching."""

import uuid

from director_agent.bg import build_client
from director_agent.schemas.bg import BGRequest


def _req(buckets):
    return BGRequest(request_id=str(uuid.uuid4()), brand="ram", lane="great_lakes", buckets_needed=buckets)


def test_season_filter_selects_winter_block():
    resp = build_client().resolve(
        _req([{"category": "patterns", "bucket": "environmental_context", "scope": "lane", "filters": {"season": "winter"}}])
    )
    sl = resp.slices["environmental_context.great_lakes"]
    assert sl.scope_resolved == "lane"
    assert sl.content["season_focus"] == "winter"
    assert "snow whites" in sl.content["palette_hints"]


def test_product_catalog_sku_filter_gives_trim_view():
    resp = build_client().resolve(
        _req([{"category": "patterns", "bucket": "product_catalog", "scope": "brand", "filters": {"sku": "D28H91"}}])
    )
    sl = resp.slices["product_catalog.ram.D28H91"]
    assert sl.content["specific_trim_request"] == "D28H91 - Tradesman (Base)"
    # Nameplate must be the real nameplate, NOT the SKU (regression: trim-string split bug).
    assert sl.content["nameplate"] == "Ram 1500"
    assert "#B61A22" in sl.content["available_hex"]


def test_lane_request_falls_back_to_brand_baseline():
    # copy_rules has no great_lakes fixture -> resolves to brand baseline.
    resp = build_client().resolve(
        _req([{"category": "voice", "bucket": "copy_rules", "scope": "lane"}])
    )
    sl = resp.slices["copy_rules.ram"]
    assert sl.scope_resolved == "brand"


def test_missing_bucket_is_flagged_as_gap():
    resp = build_client().resolve(
        _req([{"category": "patterns", "bucket": "nonexistent_bucket", "scope": "lane"}])
    )
    assert not resp.slices
    assert any("nonexistent_bucket" in g for g in resp.gaps_flagged)


def test_notes_for_consumers_present_on_slices():
    resp = build_client().resolve(
        _req([{"category": "voice", "bucket": "tone_of_voice", "scope": "brand"}])
    )
    assert resp.slices["tone_of_voice.ram"].notes_for_consumers
