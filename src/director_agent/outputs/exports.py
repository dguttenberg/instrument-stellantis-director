"""Per-tool exports built from draft records (so they include human edits).

- CGI workbook: Sheet 1 = Substance Variants (the 6-col Substance format from
  substance_row); Sheet 2 = Env Refs (cg_env_prompt). One file = the CG/AI pipeline.
- TwelveLabs: retrieval rows from twelvelabs_query + stock_search, content-search
  formatted.
"""

from __future__ import annotations

import csv
import io
from typing import Iterable, List

from openpyxl import Workbook

from ..draftstore.store import DraftRecord
from ..recommendations import output_role, recommendation_for
from .substance_excel import SUBSTANCE_COLUMNS

ENV_REF_COLUMNS = ["Cell", "Lane", "Recommendation", "For Pipeline", "AI / Runway Env Prompt"]
TWELVELABS_FIELDS = [
    "cell_id", "lane", "role", "recommendation", "query_type",
    "tags", "natural_language", "duration_min", "duration_max",
]


def _lane_of(cell_id: str) -> str:
    return cell_id.split("__")[-1] if "__" in cell_id else ""


def _rows(records: Iterable[DraftRecord], approved_only: bool):
    for rec in records:
        if approved_only and not rec.approved:
            continue
        for out in rec.envelope.get("outputs", []):
            yield rec, out


# --------------------------------------------------------------------------- #
def build_cgi_workbook(records: Iterable[DraftRecord], approved_only: bool = False) -> bytes:
    records = list(records)
    wb = Workbook()
    sub = wb.active
    sub.title = "Substance Variants"
    sub.append(SUBSTANCE_COLUMNS)
    env = wb.create_sheet("Env Refs")
    env.append(ENV_REF_COLUMNS)

    for rec, out in _rows(records, approved_only):
        if out.get("type") == "substance_row":
            row = out.get("row", {})
            sub.append([_row_val(row, c) for c in SUBSTANCE_COLUMNS])
        elif out.get("type") == "cg_env_prompt":
            headline = recommendation_for(rec.cell_type).get("headline", "")
            env.append([rec.cell_id, _lane_of(rec.cell_id), headline,
                        out.get("for_pipeline", ""), out.get("prompt", "")])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# Map Substance header -> python field name (records store python names).
_SUB_PY = {
    "Nameplate": "nameplate",
    "Specific Trim Request": "specific_trim_request",
    "Location Variant": "location_variant",
    "Color Preference (HEX)": "color_preference_hex",
    "Camera Angles": "camera_angles",
    "AI Image Generator Prompt": "ai_image_generator_prompt",
}


def _row_val(row: dict, header: str):
    return row.get(header, row.get(_SUB_PY[header], ""))


# --------------------------------------------------------------------------- #
def build_twelvelabs_rows(records: Iterable[DraftRecord], approved_only: bool = False) -> List[dict]:
    rows: List[dict] = []
    for rec, out in _rows(records, approved_only):
        t = out.get("type")
        if t not in ("twelvelabs_query", "stock_search"):
            continue
        headline = recommendation_for(rec.cell_type).get("headline", "")
        role = output_role(rec.cell_type, t)  # primary (core/stock) vs supporting (base plate)
        common = {"cell_id": rec.cell_id, "lane": _lane_of(rec.cell_id), "role": role, "recommendation": headline}
        if t == "twelvelabs_query":
            q = out.get("query", {})
            rows.append({**common, "query_type": "footage",
                         "tags": ", ".join(q.get("tags", [])), "natural_language": q.get("natural_language", ""),
                         "duration_min": q.get("duration_min", ""), "duration_max": q.get("duration_max", "")})
        else:
            rows.append({**common, "query_type": "stock",
                         "tags": ", ".join(out.get("tags_for_indexed_search", [])),
                         "natural_language": out.get("natural_language_description", ""),
                         "duration_min": "", "duration_max": ""})
    return rows


def twelvelabs_csv(records: Iterable[DraftRecord], approved_only: bool = False) -> str:
    rows = build_twelvelabs_rows(records, approved_only)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=TWELVELABS_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
