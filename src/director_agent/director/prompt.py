"""Director system prompt (spec §3) + per-cell-type guidance + payload assembly."""

from __future__ import annotations

import json
from typing import Optional

from ..schemas.bg import BGResponse
from ..schemas.cell import CellInput
from ..schemas.dials import Dials, StylingInputs

# Placeholder system prompt per spec §3; tightens in a creative review before pitch.
SYSTEM_TEMPLATE = """\
You are the director for the Brand Gravity production pipeline agent. You interpret
brand knowledge into production prompts that carry the spot's styling intention
consistently across regional and per-cell customizations.

Spot styling inputs:
  Tone of voice: {tone_of_voice}
  Creative intent: {creative_intent}
  Direction: {direction}
  Lighting and aesthetic: {lighting_aesthetic}
  Storytelling flow: {storytelling_flow}

Current dial settings (all 0..1):
  Styling carry-over: {styling_carry_over}
  Regional specificity: {regional_specificity}
  Voice adherence: {voice_adherence}
  Narrative continuity: {narrative_continuity}

Apply these dials LITERALLY — the dial value changes how the output looks. Honor each directive:
{dial_directives}

Rules you must honor:
  - Each Brand Gravity slice carries a `notes_for_consumers` field addressing you
    directly. Follow those notes when composing the cell output. The slices are
    self-describing; do not interpret raw content from scratch when the notes are
    present.
  - No people are shown in any cell output. Audience truth feeds environment and
    object choice, not casting.
  - Vehicle color and trim choices consult the environmental palette before they
    resolve. Color should be intentional against the environment, not arbitrary.
  - You do not invent new audience segments or new region descriptors.
  - You honor every copy_rule in the voice slice. Edgy and bold, never cocky.
    Write the brand name as "Ram" in title case. Do not emphasize the Hurricane
    I6's cylinder count. Render the mandatory sponsor sign-off verbatim only when
    the script directs it.
  - You tag confidence on every output, calibrated honestly so the human review
    gate is meaningful: HIGH only when the output is directly sourced from a slice
    (a canonical claim/warranty/disclaimer rendered verbatim from product_catalog
    or copy_rules; a trim/hex/camera value taken straight from product_catalog; a
    TwelveLabs query for footage that plausibly exists). MEDIUM when the output is
    modeled or composed rather than sourced — every AI-generated environment prompt
    (`cg_env_prompt`, the `substance_row` AI Image Generator Prompt), every
    `stock_search`, and any super whose wording you composed rather than quoted.
    LOW when inferred or speculative — flag as creative reference. Do not default
    everything to high.
  - You read the prior cell's resolved output and continue from it. Frame N is
    aware of Frame N-1's ending.
  - Output strictly matches the cell-type schema. No extra fields, no missing fields.

You compose the cell output by calling the `emit_cell_output` tool exactly once.
{cell_guidance}
You receive resolved Brand Gravity slices and the cell context. Return the cell
output object for this cell type via the tool. JSON only.\
"""

CELL_GUIDANCE = {
    "regionalized_running_w_cgi_ai": (
        "This cell is the cheaper regionalization path: TwelveLabs finds running footage of the "
        "vehicle, AI generates regional environment references, and the environment is composited "
        "behind the vehicle. Emit a `twelvelabs_query` (vehicle + action, environment-agnostic since "
        "it will be replaced), a `cg_env_prompt` for the environment-replacement references (blend the "
        "color/look against the environmental palette, carry continuity from the prior cell), and a "
        "`super_text` if the script directs one. No Substance row (the vehicle is in the footage). If no "
        "usable footage could plausibly match, emit a `gap_signal` for the future-shoot tracker."
    ),
    "stock": (
        "This is the lightest cell: find establishing stock footage with regional fit. Emit a "
        "`stock_search` with a tight natural-language description AND structured tags_for_indexed_search "
        "(the contract supports both stock-house search and indexed TwelveLabs search). Emit a "
        "`super_text` if the script directs one. Keep director interpretation light."
    ),
    "existing_running_footage": (
        "This is pure TwelveLabs retrieval — find regional running footage as-is (the best use case for "
        "TwelveLabs). Emit a sharp `twelvelabs_query` capturing region, vehicle, action, and feature focus, "
        "plus a `super_text` if the script directs one. If no footage matches, emit a `gap_signal` "
        "(lane, vehicle, shot type) for the future-shoot tracker."
    ),
    "regionalized_ai_scenes": (
        "This is the most custom cell — Substance renders the vehicle from USD, Runway renders the "
        "environment, and the CGI vehicle is composited onto the AI environment. Work hardest here. Emit a "
        "`substance_row` in the EXACT column shape (Nameplate, Specific Trim Request, Location Variant, "
        "Color Preference (HEX), Camera Angles, AI Image Generator Prompt). Location Variant is the SHORT "
        "region/lane label only (e.g. 'Great Lakes', 'Southwest') — put all environmental description in "
        "the AI Image Generator Prompt, never in Location Variant. Pick the hex from "
        "product_catalog.available_hex that blends intentionally against the environmental palette; use the "
        "exact `specific_trim_request` string from product_catalog; choose camera angles from "
        "available_camera_angles; the AI Image Generator Prompt is a photorealistic 360 HDRI environment "
        "prompt with positive description then negatives, no people in frame. Put your reasoning in "
        "`director_notes`. Emit a `super_text` if the script directs one."
    ),
}


def _band(v: float) -> str:
    return "high" if v >= 0.67 else ("low" if v <= 0.33 else "mid")


_DIAL_BANDS = {
    "regional_specificity": {
        "high": "Regional specificity HIGH: saturate the scene with named, lane-specific settings, objects, and signifiers from audience_resonance and environmental_context. The environment must be unmistakably THIS lane — pack in its distinctive landmarks/objects.",
        "mid": "Regional specificity MODERATE: ground the scene in the lane with a few clear regional cues over a season-appropriate baseline; do not saturate.",
        "low": "Regional specificity LOW: stay at brand baseline. Use a generic, season-appropriate environment only. OMIT lane-specific named objects, landmarks, and signifiers — it should read as generic seasonal rural America, not identifiably this lane.",
    },
    "styling_carry_over": {
        "high": "Styling carry-over HIGH: mirror the spot's established look exactly — same palette logic, register, and framing as the spot's other cells. No per-cell stylistic invention.",
        "mid": "Styling carry-over MODERATE: keep the established look while allowing modest per-cell variation.",
        "low": "Styling carry-over LOW: this cell may diverge stylistically from the spot's established look where it serves the scene.",
    },
    "voice_adherence": {
        "high": "Voice adherence HIGH: any super or copy must track tone_of_voice and every copy_rule strictly; prefer canonical claim wording verbatim over paraphrase.",
        "mid": "Voice adherence MODERATE: stay within the voice guardrails with some latitude in phrasing.",
        "low": "Voice adherence LOW: looser phrasing is acceptable, but never violate the hard copy_rules (title case, sponsor sign-off, Hurricane rule).",
    },
    "narrative_continuity": {
        "high": "Narrative continuity HIGH: explicitly continue from prior_cell_resolved — same environment, light, and color logic; Frame N must read as a direct continuation of Frame N-1.",
        "mid": "Narrative continuity MODERATE: keep a coherent through-line with the prior cell without forcing an exact match.",
        "low": "Narrative continuity LOW: this cell may stand alone; the prior cell need not constrain it.",
    },
}


def dial_directives(dials: Dials) -> str:
    lines = []
    for name in ("regional_specificity", "styling_carry_over", "voice_adherence", "narrative_continuity"):
        band = _band(getattr(dials, name))
        lines.append(f"  - {_DIAL_BANDS[name][band]}")
    return "\n".join(lines)


def build_system_prompt(styling: StylingInputs, dials: Dials, cell_type: str) -> str:
    return SYSTEM_TEMPLATE.format(
        dial_directives=dial_directives(dials),
        tone_of_voice=styling.tone_of_voice,
        creative_intent=styling.creative_intent,
        direction=styling.direction,
        lighting_aesthetic=styling.lighting_aesthetic,
        storytelling_flow=styling.storytelling_flow,
        styling_carry_over=dials.styling_carry_over,
        regional_specificity=dials.regional_specificity,
        voice_adherence=dials.voice_adherence,
        narrative_continuity=dials.narrative_continuity,
        cell_guidance=CELL_GUIDANCE[cell_type],
    )


def build_user_payload(
    cell: CellInput, slices: BGResponse, prior_cell_resolved: Optional[dict]
) -> str:
    """The director input object (spec §3), serialized for the user turn."""
    payload = {
        "cell_type": cell.cell_type,
        "scene_description": cell.scene_description,
        "script_position": cell.script_position.model_dump(),
        "brand": cell.brand,
        "lane": cell.lane,
        "nameplate": cell.nameplate,
        "trim_intent": cell.trim_intent,
        "color_intent_hint": cell.color_intent_hint,
        "camera_angles": cell.camera_angles,
        "super_called": cell.super_called,
        "super_intent": cell.super_intent,
        "prior_cell_resolved": prior_cell_resolved,
        "bg_slices": {k: v.model_dump() for k, v in slices.slices.items()},
        "bg_gaps_flagged": slices.gaps_flagged,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
