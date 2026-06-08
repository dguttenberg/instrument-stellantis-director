"""Per-cell-type contracts (spec §5): which BG buckets each cell requests, and
which output types its envelope may contain. The agent inherits the cell_type
from the script; it never decides it."""

from __future__ import annotations

from typing import List, Optional

from ..schemas.bg import BucketNeeded

# bucket spec tuples: (category, bucket, scope, needs_season, needs_sku)
_BUCKETS = {
    "regionalized_running_w_cgi_ai": [
        ("patterns", "environmental_context", "lane", True, False),
        ("human", "audience_resonance", "lane", False, False),
        ("patterns", "product_catalog", "brand", False, True),
        ("voice", "tone_of_voice", "brand", False, False),
        ("discipline_outputs", "creative_intent", "lane", False, False),
    ],
    "stock": [
        ("patterns", "environmental_context", "lane", True, False),
        ("human", "audience_resonance", "lane", False, False),
        ("voice", "tone_of_voice", "brand", False, False),
        ("discipline_outputs", "creative_intent", "lane", False, False),
    ],
    "existing_running_footage": [
        ("patterns", "environmental_context", "lane", True, False),
        ("human", "audience_resonance", "lane", False, False),
        ("patterns", "product_catalog", "brand", False, True),
    ],
    "regionalized_ai_scenes": [
        ("patterns", "environmental_context", "lane", True, False),
        ("human", "audience_resonance", "lane", False, False),
        ("patterns", "product_catalog", "brand", False, True),
        ("voice", "tone_of_voice", "brand", False, False),
        ("voice", "copy_rules", "lane", False, False),
        ("discipline_outputs", "creative_intent", "lane", False, False),
        ("discipline_outputs", "design_tokens", "brand", False, False),
    ],
}

# Allowed output types per cell type. super_text and gap_signal are allowed
# everywhere (a super is cross-cutting; a gap_signal is the universal failure mode).
_ALLOWED = {
    "regionalized_running_w_cgi_ai": ["twelvelabs_query", "cg_env_prompt", "super_text", "gap_signal"],
    "stock": ["stock_search", "super_text", "gap_signal"],
    "existing_running_footage": ["twelvelabs_query", "super_text", "gap_signal"],
    "regionalized_ai_scenes": ["substance_row", "super_text", "gap_signal"],
}

CELL_SPECS = {ct: {"buckets": _BUCKETS[ct], "allowed": _ALLOWED[ct]} for ct in _BUCKETS}


def buckets_for(
    cell_type: str, trim_intent: Optional[str], season: str
) -> List[BucketNeeded]:
    out: List[BucketNeeded] = []
    for category, bucket, scope, needs_season, needs_sku in CELL_SPECS[cell_type]["buckets"]:
        filters = {}
        if needs_season and season:
            filters["season"] = season
        if needs_sku and trim_intent:
            filters["sku"] = trim_intent
        out.append(
            BucketNeeded(
                category=category,
                bucket=bucket,
                scope=scope,
                filters=filters or None,
            )
        )
    return out


def allowed_output_types(cell_type: str) -> List[str]:
    return CELL_SPECS[cell_type]["allowed"]
