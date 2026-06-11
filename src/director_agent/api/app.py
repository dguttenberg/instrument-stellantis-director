"""HTTP surface — the local application.

GET  /                          -> DCP-branded workflow UI
POST /ingest                    -> upload a PDF/PPTX deck -> draft matrix (working project)
GET  /project                   -> the working script + dials
PUT  /project/scenes/{i}        -> edit a scene (cell_type, description, super, trim)
POST /run/cell                  -> run ONE cell of the working script (live matrix fill)
GET  /drafts · GET /drafts/{id} -> draft records
PUT  /drafts/{id}               -> edit what the director made (re-validate + re-flag)
POST /drafts/{id}/approve       -> approve (human gate, spec §7)
GET  /export/cgi.xlsx           -> CGI workbook (Substance + Env Refs)
GET  /export/twelvelabs.csv|json-> retrieval queries (footage + stock)
GET  /substance.xlsx            -> Substance-only sheet (legacy convenience)
"""

from __future__ import annotations

import io
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from ..bg import build_client
from ..config import DATA_DIR, get_settings
from ..director import Director
from ..draftstore import DraftRecord, DraftStore, build_draft_store
from ..ingest import DeckExtractor
from ..outputs import SUBSTANCE_COLUMNS, build_cgi_workbook, twelvelabs_csv
from ..outputs.exports import build_twelvelabs_rows
from ..pipeline import PipelineRunner, load_styling
from ..project import Project, ProjectStore
from ..schemas.bg import BGRequest
from ..schemas.cell import CellOutput, CellOutputEnvelope, ProvenanceEntry, SubstanceRow
from ..schemas.dials import Dials
from ..schemas.script import Scene
from ..validation import check_envelope

from .auth import PasswordGateMiddleware

app = FastAPI(title="Production Pipeline Agent", version="0.2.0")
# Shared-password gate (active only when APP_PASSWORD is set — see auth.py).
app.add_middleware(PasswordGateMiddleware)

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_DEMO_STYLING = DATA_DIR / "styling" / "year_end_demo.json"
# Built React SPA (web/out). When present, it's served at / and its assets fall
# through to the StaticFiles mount registered at the bottom of this module.
_WEB_DIST = Path(
    os.environ.get("WEB_DIST", Path(__file__).resolve().parents[3] / "web" / "out")
)

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@lru_cache(maxsize=1)
def _draft_store() -> DraftStore:
    return build_draft_store(get_settings())


def _project_store() -> ProjectStore:
    return ProjectStore()


def _runner() -> PipelineRunner:
    settings = get_settings()
    return PipelineRunner(
        bg_client=build_client(settings),
        director=Director(settings),
        draft_store=_draft_store(),
        substance_out_path=settings.substance_out_abspath,
    )


# --------------------------------------------------------------------------- #
# Page + health
# --------------------------------------------------------------------------- #
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


BUSINESS_CENTERS = [
    {"key": "great_lakes", "label": "Great Lakes", "abbrev": "GL"},
    {"key": "southwest", "label": "Southwest", "abbrev": "SW"},
    {"key": "northeast", "label": "Northeast", "abbrev": "NE"},
    {"key": "southeast", "label": "Southeast", "abbrev": "SE"},
    {"key": "midwest", "label": "Midwest", "abbrev": "MW"},
    {"key": "west", "label": "West", "abbrev": "W"},
]


@app.get("/lanes")
def lanes() -> dict:
    """The business centers the director can create for (all resolve via Brand Gravity:
    GL/SW have authored lane content; the rest resolve environmental_context per-lane
    and fall back to brand baselines for audience/creative)."""
    return {"lanes": BUSINESS_CENTERS}


@app.get("/twelvelabs-filters")
def twelvelabs_filters() -> dict:
    """The controlled TwelveLabs filter vocabulary, for the review-panel edit controls."""
    from ..twelvelabs import load_taxonomy

    return load_taxonomy()


@app.get("/recommendations")
def recommendations() -> dict:
    """The recommendation each cell type makes (headline, tool, primary/supporting),
    so the UI can show 'what are we recommending' clearly."""
    from ..recommendations import RECOMMENDATIONS, TOOL_LABEL

    return {"recommendations": RECOMMENDATIONS, "tool_label": TOOL_LABEL}


@app.get("/", include_in_schema=False)
def index():
    spa_index = _WEB_DIST / "index.html"
    if spa_index.is_file():
        return FileResponse(str(spa_index))
    return FileResponse(str(_STATIC_DIR / "index.html"))


# --------------------------------------------------------------------------- #
# Ingestion + working project
# --------------------------------------------------------------------------- #
@app.post("/ingest", response_model=Project)
async def ingest(file: UploadFile = File(...)) -> Project:
    content = await file.read()
    name = file.filename or "deck"
    if not name.lower().endswith((".pdf", ".pptx", ".ppt")):
        raise HTTPException(status_code=400, detail="Upload a .pdf or .pptx deck.")
    try:
        script = DeckExtractor(get_settings()).extract(name, content)
    except Exception as e:  # extraction is best-effort; surface the reason
        raise HTTPException(status_code=502, detail=f"Could not extract scenes: {e}")
    return _project_store().set_script(script)


@app.get("/project", response_model=Project)
def get_project() -> Project:
    return _project_store().load()


@app.post("/project/sample", response_model=Project)
def load_sample() -> Project:
    """Populate the matrix from the bundled South:15 (no-file demo fallback)."""
    return _project_store().load_sample()


class ScenePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell_type: Optional[str] = None
    scene_description: Optional[str] = None
    nameplate: Optional[str] = None
    trim_intent: Optional[str] = None
    color_intent_hint: Optional[str] = None
    camera_angles: Optional[List[str]] = None
    super_called: Optional[bool] = None
    super_intent: Optional[str] = None


@app.put("/project/scenes/{scene_index}", response_model=Scene)
def update_scene(scene_index: int, patch: ScenePatch) -> Scene:
    updated = _project_store().update_scene(scene_index, patch.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail=f"No scene_index {scene_index}")
    return updated


# --------------------------------------------------------------------------- #
# Run one cell of the working script
# --------------------------------------------------------------------------- #
class RunCellRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lane: str
    scene_index: int
    dials: Optional[Dials] = None
    prior_cell_resolved: Optional[dict] = None
    season: str = "winter"


class RunCellResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    envelope: CellOutputEnvelope
    record: DraftRecord


@app.post("/run/cell", response_model=RunCellResult)
def run_cell(req: RunCellRequest) -> RunCellResult:
    project = _project_store().load()
    scenes = [s for s in project.script.scenes if s.scene_index == req.scene_index]
    if not scenes:
        raise HTTPException(status_code=404, detail=f"No scene_index {req.scene_index}")
    runner = _runner()
    runner.season = req.season
    envelope, record = runner.run_cell(
        scene=scenes[0],
        script=project.script,
        lane=req.lane,
        dials=req.dials or project.dials,
        styling=load_styling(_DEMO_STYLING),
        prior_cell_resolved=req.prior_cell_resolved,
    )
    return RunCellResult(envelope=envelope, record=record)


# --------------------------------------------------------------------------- #
# Drafts: read, edit (approve-with-edit), approve
# --------------------------------------------------------------------------- #
@app.get("/drafts", response_model=List[DraftRecord])
def list_drafts() -> List[DraftRecord]:
    return _draft_store().list()


@app.get("/drafts/{cell_id}", response_model=DraftRecord)
def get_draft(cell_id: str) -> DraftRecord:
    rec = _draft_store().get(cell_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"No draft for cell_id {cell_id}")
    return rec


class EditDraftRequest(BaseModel):
    """Human-edited outputs replacing what the director made."""

    model_config = ConfigDict(extra="forbid")

    outputs: List[CellOutput]
    gaps_flagged: Optional[List[str]] = None


@app.put("/drafts/{cell_id}", response_model=DraftRecord)
def edit_draft(cell_id: str, req: EditDraftRequest) -> DraftRecord:
    existing = _draft_store().get(cell_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"No draft for cell_id {cell_id}")
    env = existing.envelope
    # Keep non-invariant gaps; re-derive invariant flags after the edit.
    base_gaps = req.gaps_flagged if req.gaps_flagged is not None else [
        g for g in env.get("gaps_flagged", []) if not g.startswith("invariant:")
    ]
    edited = CellOutputEnvelope(
        cell_id=existing.cell_id,
        cell_type=existing.cell_type,
        outputs=[o.model_dump() for o in req.outputs],
        gaps_flagged=base_gaps,
        provenance=[ProvenanceEntry.model_validate(p) for p in env.get("provenance", [])],
    )
    hexes, angles = _brand_catalog_constraints()
    for v in check_envelope(edited, available_hex=hexes, available_camera_angles=angles):
        edited.gaps_flagged.append(f"invariant: {v}")
    return _draft_store().put(edited)


@app.post("/drafts/{cell_id}/approve", response_model=DraftRecord)
def approve_draft(cell_id: str) -> DraftRecord:
    rec = _draft_store().approve(cell_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"No draft for cell_id {cell_id}")
    return rec


# --------------------------------------------------------------------------- #
# Exports
# --------------------------------------------------------------------------- #
@app.get("/export/cgi.xlsx")
def export_cgi(approved_only: bool = False):
    data = build_cgi_workbook(_draft_store().list(), approved_only=approved_only)
    return StreamingResponse(
        io.BytesIO(data), media_type=XLSX_MEDIA,
        headers={"Content-Disposition": "attachment; filename=cgi_substance.xlsx"},
    )


@app.get("/export/twelvelabs.csv")
def export_twelvelabs_csv(approved_only: bool = False):
    text = twelvelabs_csv(_draft_store().list(), approved_only=approved_only)
    return StreamingResponse(
        io.BytesIO(text.encode("utf-8")), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=twelvelabs_queries.csv"},
    )


@app.get("/export/twelvelabs.json")
def export_twelvelabs_json(approved_only: bool = False):
    return JSONResponse(build_twelvelabs_rows(_draft_store().list(), approved_only=approved_only))


@app.get("/substance.xlsx")
def substance_xlsx(approved_only: bool = False):
    """Legacy Substance-only sheet (kept for convenience; /export/cgi.xlsx is canonical)."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Variants"
    ws.append(SUBSTANCE_COLUMNS)
    for rec in _draft_store().list():
        if approved_only and not rec.approved:
            continue
        for out in rec.envelope.get("outputs", []):
            if out.get("type") == "substance_row":
                row = SubstanceRow.model_validate(out).row.model_dump(by_alias=True)
                ws.append([row[c] for c in SUBSTANCE_COLUMNS])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type=XLSX_MEDIA,
                             headers={"Content-Disposition": "attachment; filename=substance_rows.xlsx"})


# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _brand_catalog_constraints():
    """available_hex + camera angles from product_catalog (brand) for edit-time
    invariant checks. Cached — the brand catalog doesn't change within a run."""
    resp = build_client(get_settings()).resolve(
        BGRequest(
            request_id=str(uuid.uuid4()), brand="ram", lane="great_lakes",
            buckets_needed=[{"category": "patterns", "bucket": "product_catalog", "scope": "brand"}],
        )
    )
    for key, sl in resp.slices.items():
        if key.startswith("product_catalog") and isinstance(sl.content, dict):
            return sl.content.get("available_hex"), sl.content.get("available_camera_angles")
    return None, None


# --------------------------------------------------------------------------- #
# Serve the built React SPA (web/out) when present. Registered LAST so every API
# route above matches first; this mount then serves the SPA's static assets
# (/_next, /brand, /fonts, favicon) and index.html. No-op in dev when web/out
# doesn't exist (the Next dev server on :3000 is used then, proxying here).
# --------------------------------------------------------------------------- #
if _WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_WEB_DIST), html=True), name="spa")
