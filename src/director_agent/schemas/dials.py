"""Dials and spot-level styling inputs passed to the director (spec §3)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Dials(BaseModel):
    """The four dials, all 0..1, default 0.5 (spec §3)."""

    model_config = ConfigDict(extra="forbid")

    styling_carry_over: float = Field(0.5, ge=0.0, le=1.0)
    regional_specificity: float = Field(0.5, ge=0.0, le=1.0)
    voice_adherence: float = Field(0.5, ge=0.0, le=1.0)
    narrative_continuity: float = Field(0.5, ge=0.0, le=1.0)


class StylingInputs(BaseModel):
    """Spot-level styling inputs (spec §3). Placeholder shape; refined with a creative."""

    model_config = ConfigDict(extra="forbid")

    tone_of_voice: str
    creative_intent: str
    direction: str
    lighting_aesthetic: str
    storytelling_flow: str
