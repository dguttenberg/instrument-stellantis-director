"""Brand-rule invariants checked against a cell-output envelope (spec §3 rules,
copy_rules). Schema validity proves shape; these prove the director honored the
load-bearing brand rules. Used as golden assertions in tests and surfaced as
review flags on live output. Heuristic and conservative — a flag is a prompt to
review, not a hard reject."""

from __future__ import annotations

import re
from typing import List, Optional

from .schemas.cell import CellOutputEnvelope

CANONICAL_SPONSOR_SIGNOFF = "Sponsored by Ram trucks. Nothing Stops Ram."

# Person nouns that would imply casting (spec: no people in frame).
_PERSON_WORDS = re.compile(
    r"\b(person|people|man|men|woman|women|driver|drivers|pedestrian|crowd|family|child|children|kid|kids|human|humans|figure|figures)\b",
    re.IGNORECASE,
)
_NO_PEOPLE_PHRASES = re.compile(
    r"no people|no person|without people|no humans|no one|unoccupied|no figures|absent of people",
    re.IGNORECASE,
)
_ALLCAPS_RAM = re.compile(r"\bRAM\b")
_LOWER_RAM = re.compile(r"\bram\b")
_HURRICANE = re.compile(r"hurricane", re.IGNORECASE)
_CYLINDER_COUNT = re.compile(r"\b(six[- ]cylinder|6[- ]cylinder|inline[- ]?6|i6|straight[- ]six)\b", re.IGNORECASE)


def _text_fields(envelope: CellOutputEnvelope):
    """Yield (output_index, label, text) for every prose field worth checking."""
    for i, o in enumerate(envelope.outputs):
        t = o.type
        if t == "super_text":
            yield i, "super_text.content", o.content
        elif t == "cg_env_prompt":
            yield i, "cg_env_prompt.prompt", o.prompt
        elif t == "stock_search":
            yield i, "stock_search.natural_language_description", o.natural_language_description
        elif t == "twelvelabs_query":
            yield i, "twelvelabs_query.natural_language", o.query.natural_language
        elif t == "substance_row":
            yield i, "substance_row.ai_image_generator_prompt", o.row.ai_image_generator_prompt


def check_envelope(
    envelope: CellOutputEnvelope,
    available_hex: Optional[List[str]] = None,
    available_camera_angles: Optional[List[str]] = None,
) -> List[str]:
    violations: List[str] = []
    cid = envelope.cell_id

    for idx, label, text in _text_fields(envelope):
        if not text:
            continue
        # Brand name title case (allow the all-caps RAM wordmark only in logo context).
        if _ALLCAPS_RAM.search(text):
            violations.append(f"{cid}[{idx}] {label}: brand name in all-caps 'RAM' (use 'Ram' in authored text)")
        if _LOWER_RAM.search(text):
            violations.append(f"{cid}[{idx}] {label}: brand name lowercase 'ram' (use 'Ram')")
        # Hurricane cylinder-count rule.
        if _CYLINDER_COUNT.search(text) or (_HURRICANE.search(text) and "cylinder" in text.lower()):
            violations.append(f"{cid}[{idx}] {label}: emphasizes Hurricane cylinder count (copy_rules hard rule)")
        # No people in frame.
        if _PERSON_WORDS.search(text) and not _NO_PEOPLE_PHRASES.search(text):
            violations.append(f"{cid}[{idx}] {label}: implies people in frame with no 'no people' qualifier")
        # Sponsor sign-off must be verbatim when present.
        if "sponsored by" in text.lower() and CANONICAL_SPONSOR_SIGNOFF not in text:
            violations.append(f"{cid}[{idx}] {label}: sponsor sign-off not verbatim '{CANONICAL_SPONSOR_SIGNOFF}'")

    # Substance row: hex + camera angles must come from the product catalog.
    for i, o in enumerate(envelope.outputs):
        if o.type != "substance_row":
            continue
        if available_hex and o.row.color_preference_hex.upper() not in {h.upper() for h in available_hex}:
            violations.append(f"{cid}[{i}] substance_row: hex {o.row.color_preference_hex} not in product_catalog palette")
        if available_camera_angles:
            allowed = set(available_camera_angles)
            for ang in [a.strip() for a in o.row.camera_angles.split(",") if a.strip()]:
                if ang not in allowed:
                    violations.append(f"{cid}[{i}] substance_row: camera angle '{ang}' not in available_camera_angles")

    return violations
