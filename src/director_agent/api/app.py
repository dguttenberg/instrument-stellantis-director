"""HTTP surface (spec §9):

POST /run                 -> walk a script for a lane, emit envelopes to the draft store
GET  /drafts              -> list draft records
GET  /drafts/{cell_id}    -> one draft record
POST /drafts/{cell_id}/approve -> approve a draft (human gate, spec §7)
"""

from __future__ import annotations

import io
from functools import lru_cache
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from ..bg import build_client
from ..config import get_settings
from ..director import Director
from ..draftstore import DraftRecord, DraftStore, build_draft_store
from ..outputs.substance_excel import SUBSTANCE_COLUMNS
from ..pipeline import PipelineRunner, RunResult
from ..schemas.cell import SubstanceRow
from ..schemas.dials import Dials, StylingInputs
from ..schemas.script import Script

app = FastAPI(title="Production Pipeline Agent", version="0.1.0")


@lru_cache(maxsize=1)
def _draft_store() -> DraftStore:
    return build_draft_store(get_settings())


def _runner() -> PipelineRunner:
    settings = get_settings()
    return PipelineRunner(
        bg_client=build_client(settings),
        director=Director(settings),
        draft_store=_draft_store(),
        substance_out_path=settings.substance_out_abspath,
    )


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script: Script
    lane: str
    dials: Optional[Dials] = None
    styling: StylingInputs
    season: str = "winter"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run", response_model=RunResult)
def run(req: RunRequest) -> RunResult:
    runner = _runner()
    runner.season = req.season
    return runner.run(
        script=req.script,
        lane=req.lane,
        dials=req.dials or Dials(),
        styling=req.styling,
    )


@app.get("/drafts", response_model=List[DraftRecord])
def list_drafts() -> List[DraftRecord]:
    return _draft_store().list()


@app.get("/drafts/{cell_id}", response_model=DraftRecord)
def get_draft(cell_id: str) -> DraftRecord:
    rec = _draft_store().get(cell_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"No draft for cell_id {cell_id}")
    return rec


@app.post("/drafts/{cell_id}/approve", response_model=DraftRecord)
def approve_draft(cell_id: str) -> DraftRecord:
    rec = _draft_store().approve(cell_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"No draft for cell_id {cell_id}")
    return rec


@app.get("/substance.xlsx")
def substance_xlsx(approved_only: bool = False):
    """Build the Substance workbook on the fly from the draft store (the local
    /tmp file is ephemeral on serverless). Optionally include approved rows only."""
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
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=substance_rows.xlsx"},
    )
