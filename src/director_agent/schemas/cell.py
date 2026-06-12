"""Cell input and the typed cell-output envelope (spec §5, §6).

Output objects are a discriminated union on `type`. The envelope is what the
director must emit and what lands in the draft store. All models forbid extra
fields to honor the spec's "no extra fields, no missing fields" rule.
"""

from __future__ import annotations

from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated, Literal

from .common import CellType, Confidence


# --------------------------------------------------------------------------- #
# Cell input (spec §5) — what the agent assembles per scene.
# --------------------------------------------------------------------------- #
class CellInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell_id: str
    cell_type: CellType
    scene_description: str
    script_position: "ScriptPosition"
    brand: str
    lane: str
    nameplate: str = "Ram 1500"
    trim_intent: Optional[str] = None
    color_intent_hint: Optional[str] = None
    camera_angles: List[str] = Field(default_factory=list)
    super_called: bool = False
    super_intent: Optional[str] = None
    prior_cell_resolved: Optional[dict] = None


class ScriptPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script_id: str
    scene_index: int
    total_scenes: int


# --------------------------------------------------------------------------- #
# Output object types.
# --------------------------------------------------------------------------- #
class TwelveLabsFilters(BaseModel):
    """Controlled filters the TwelveLabs tool exposes (see data/twelvelabs_filters.json).
    All optional and sparse — the director selects ONLY the categories that apply;
    most queries use just a few. Values must come from the controlled vocabulary."""

    model_config = ConfigDict(extra="forbid")

    brand: Optional[List[str]] = None
    project: Optional[List[str]] = None
    vehicle_type: Optional[List[str]] = None
    trim: Optional[List[str]] = None
    color: Optional[List[str]] = None
    framing: Optional[List[str]] = None
    camera_movement: Optional[List[str]] = None
    action: Optional[List[str]] = None
    environment: Optional[List[str]] = None
    mood: Optional[List[str]] = None


class TwelveLabsQueryBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tags: List[str]
    natural_language: str
    duration_min: Optional[float] = None
    duration_max: Optional[float] = None
    filters: Optional[TwelveLabsFilters] = None


class TwelveLabsQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["twelvelabs_query"] = "twelvelabs_query"
    confidence: Confidence
    query: TwelveLabsQueryBody


class CgEnvPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["cg_env_prompt"] = "cg_env_prompt"
    confidence: Confidence
    for_pipeline: str  # e.g. "runway_env_refs_for_replacement"
    prompt: str


class StockSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["stock_search"] = "stock_search"
    confidence: Confidence
    natural_language_description: str
    tags_for_indexed_search: List[str] = Field(default_factory=list)


class SubstanceRowData(BaseModel):
    """Exact column shape of the demo spreadsheet (spec §5.4). Keys are the
    spreadsheet headers; the row drops straight into the Substance xlsx."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    nameplate: str = Field(alias="Nameplate")
    specific_trim_request: str = Field(alias="Specific Trim Request")
    location_variant: str = Field(alias="Location Variant")
    color_preference_hex: str = Field(alias="Color Preference (HEX)")
    camera_angles: str = Field(alias="Camera Angles")
    ai_image_generator_prompt: str = Field(alias="AI Image Generator Prompt")


class SubstanceRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["substance_row"] = "substance_row"
    confidence: Confidence
    row: SubstanceRowData
    director_notes: Optional[str] = None


class SuperText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["super_text"] = "super_text"
    confidence: Confidence
    content: str
    voice_tags: List[str] = Field(default_factory=list)
    legal_disclaimers: List[str] = Field(default_factory=list)
    source_claim: Optional[str] = None


class GapSignal(BaseModel):
    """Emitted when a cell cannot resolve (e.g. no usable footage), flagged for
    the future-shoot-needs tracker (spec §5.1, §5.3)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["gap_signal"] = "gap_signal"
    confidence: Confidence = "high"
    reason: str
    lane: str
    season: Optional[str] = None
    shot_type: Optional[str] = None


CellOutput = Annotated[
    Union[TwelveLabsQuery, CgEnvPrompt, StockSearch, SubstanceRow, SuperText, GapSignal],
    Field(discriminator="type"),
]


# --------------------------------------------------------------------------- #
# Envelope (spec §5) — one object per cell, draft=true until approved.
# --------------------------------------------------------------------------- #
class ProvenanceEntry(BaseModel):
    """What the director was 'directed from' — a resolved BG slice (spec §4)."""

    model_config = ConfigDict(extra="forbid")

    key: str
    bucket: str
    scope_resolved: str
    confidence: Confidence


class SceneIntelligence(BaseModel):
    """The three intelligences whose intersection drives the scene — each a short
    phrase the director pulls from the matching Brand Gravity slices. Shown on the
    matrix so the synthesis (synopsis) is visibly the product of brand × location ×
    audience."""

    model_config = ConfigDict(extra="forbid")

    brand: str = ""  # brand voice / positioning truth (tone_of_voice, creative_intent)
    location: str = ""  # region / environment texture (environmental_context)
    audience: str = ""  # audience segment / truth (audience_resonance)


class CellOutputEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell_id: str
    cell_type: CellType
    draft: bool = True
    # Director-written: one-sentence descriptor weaving audience + location + brand
    # voice from the resolved slices — the matrix's human-readable summary.
    synopsis: str = ""
    # The three intelligences behind the synopsis, kept separable for the UI.
    intelligence: SceneIntelligence = Field(default_factory=SceneIntelligence)
    outputs: List[CellOutput]
    gaps_flagged: List[str] = Field(default_factory=list)
    # Set by the runner (not the director): the slices this cell resolved against,
    # surfaced in the UI so review has something to check against.
    provenance: List[ProvenanceEntry] = Field(default_factory=list)


CellInput.model_rebuild()
