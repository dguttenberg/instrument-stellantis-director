"""Brand Gravity agent-side contract (spec §4).

The agent sends a structured request listing the buckets it needs; Brand Gravity
returns shaped JSON slices, deepest scope wins, each tagged with confidence and
provenance. Per spec §3, each slice also carries a `notes_for_consumers` field
addressing the director directly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import Confidence


class BucketNeeded(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str  # center | human | voice | discipline_outputs | patterns
    bucket: str
    scope: str  # brand | lane | campaign
    filters: Optional[Dict[str, Any]] = None


class BGRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    caller: str = "production_pipeline_agent"
    purpose: str = "cell_resolve"
    brand: str
    lane: str
    buckets_needed: List[BucketNeeded]
    context_hint: str = ""


class Slice(BaseModel):
    """One resolved slice. `content` is bucket-shaped JSON (varies by bucket)."""

    model_config = ConfigDict(extra="forbid")

    scope_resolved: str
    confidence: Confidence
    content: Any
    provenance: List[str] = Field(default_factory=list)
    # Addresses the director directly: how this slice should be used (spec §3).
    notes_for_consumers: Optional[str] = None


class BGResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    resolved_at: str
    slices: Dict[str, Slice]
    gaps_flagged: List[str] = Field(default_factory=list)
