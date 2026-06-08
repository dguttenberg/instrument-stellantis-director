"""HTTP surface (spec §9):

POST /run                 -> walk a script for a lane, emit envelopes to the draft store
GET  /drafts              -> list draft records
GET  /drafts/{cell_id}    -> one draft record
POST /drafts/{cell_id}/approve -> approve a draft (human gate, spec §7)
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from ..bg import build_client
from ..config import get_settings
from ..director import Director
from ..draftstore import DraftRecord, LocalDraftStore
from ..pipeline import PipelineRunner, RunResult
from ..schemas.dials import Dials, StylingInputs
from ..schemas.script import Script

app = FastAPI(title="Production Pipeline Agent", version="0.1.0")


@lru_cache(maxsize=1)
def _draft_store() -> LocalDraftStore:
    return LocalDraftStore(get_settings().draft_store_abspath)


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
