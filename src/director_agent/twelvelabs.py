"""TwelveLabs controlled filter vocabulary — the categories + allowed values the
TwelveLabs tool exposes (sourced from filter-options.xlsx → data/twelvelabs_filters.json).
Single source for: the director prompt (so it picks valid values), the UI edit
controls, and the export columns."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import List

from .config import DATA_DIR

_FILTERS_FILE = DATA_DIR / "twelvelabs_filters.json"

# Categorical filter keys, in display order (duration is handled via duration_min/max).
FILTER_KEYS: List[str] = [
    "brand", "project", "vehicle_type", "trim", "color", "framing",
    "camera_movement", "action", "environment", "mood",
]


@lru_cache(maxsize=1)
def load_taxonomy() -> dict:
    return json.loads(_FILTERS_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def prompt_vocab() -> str:
    """Compact vocabulary block for the director system prompt."""
    lines = []
    for cat in load_taxonomy()["categories"]:
        if cat["key"] == "duration":
            lines.append(f"  - Duration: numeric range ({cat.get('range_label', '')}) — use duration_min/duration_max.")
        else:
            vals = " | ".join(cat["values"])
            lines.append(f"  - {cat['label']} ({cat['key']}): {vals}")
    return "\n".join(lines)
