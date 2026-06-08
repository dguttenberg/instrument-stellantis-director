"""The production-pipeline loop (spec §2): for each scene, compose a BG request,
resolve slices, call the director once, write any Substance rows, and post the
cell-output envelope to the draft store. Cells run sequentially so the room can
watch the matrix fill; each cell receives the prior cell's resolved envelope as
continuity context."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from ..director import Director
from ..director.cell_specs import buckets_for
from ..draftstore.store import DraftRecord, DraftStore
from ..outputs.substance_excel import append_substance_rows
from ..schemas.bg import BGRequest
from ..schemas.cell import CellInput, CellOutputEnvelope, ScriptPosition, SubstanceRow
from ..schemas.dials import Dials, StylingInputs
from ..schemas.script import Scene, Script
from ..bg.client import BGClient
from ..validation import check_envelope


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script_id: str
    lane: str
    season: str
    records: List[DraftRecord]
    envelopes: List[CellOutputEnvelope]


def _cell_input_from_scene(scene: Scene, script: Script, lane: str) -> CellInput:
    return CellInput(
        cell_id=f"{scene.cell_id}__{lane}",
        cell_type=scene.cell_type,
        scene_description=scene.scene_description,
        script_position=ScriptPosition(
            script_id=script.script_id,
            scene_index=scene.scene_index,
            total_scenes=script.total_scenes,
        ),
        brand="ram",
        lane=lane,
        nameplate=scene.nameplate,
        trim_intent=scene.trim_intent,
        color_intent_hint=scene.color_intent_hint,
        camera_angles=scene.camera_angles,
        super_called=scene.super_called,
        super_intent=scene.super_intent,
    )


def _catalog_constraints(slices):
    """Pull available_hex / available_camera_angles from the resolved product_catalog
    slice (if present) so invariant checks can validate the Substance row."""
    for key, sl in slices.slices.items():
        if key.startswith("product_catalog") and isinstance(sl.content, dict):
            return sl.content.get("available_hex"), sl.content.get("available_camera_angles")
    return None, None


class PipelineRunner:
    def __init__(
        self,
        bg_client: BGClient,
        director: Director,
        draft_store: DraftStore,
        substance_out_path: Path,
        season: str = "winter",
    ):
        self.bg_client = bg_client
        self.director = director
        self.draft_store = draft_store
        self.substance_out_path = Path(substance_out_path)
        self.season = season

    def run(
        self,
        script: Script,
        lane: str,
        dials: Dials,
        styling: StylingInputs,
        brand: str = "ram",
    ) -> RunResult:
        records: List[DraftRecord] = []
        envelopes: List[CellOutputEnvelope] = []
        prior_resolved: Optional[dict] = None

        for scene in script.scenes:
            cell = _cell_input_from_scene(scene, script, lane)
            needs = buckets_for(cell.cell_type, cell.trim_intent, self.season)
            request = BGRequest(
                request_id=str(uuid.uuid4()),
                brand=brand,
                lane=lane,
                buckets_needed=needs,
                context_hint=cell.scene_description,
            )
            slices = self.bg_client.resolve(request)
            envelope = self.director.run(cell, slices, dials, styling, prior_cell_resolved=prior_resolved)

            # Surface brand-rule invariant violations as review flags (spec §3 rules).
            hexes, angles = _catalog_constraints(slices)
            for v in check_envelope(envelope, available_hex=hexes, available_camera_angles=angles):
                envelope.gaps_flagged.append(f"invariant: {v}")

            sub_rows = [o for o in envelope.outputs if isinstance(o, SubstanceRow)]
            if sub_rows:
                append_substance_rows(sub_rows, self.substance_out_path)

            record = self.draft_store.put(envelope)
            records.append(record)
            envelopes.append(envelope)
            prior_resolved = envelope.model_dump()

        return RunResult(
            script_id=script.script_id,
            lane=lane,
            season=self.season,
            records=records,
            envelopes=envelopes,
        )


# --------------------------------------------------------------------------- #
# Config loaders
# --------------------------------------------------------------------------- #
def load_script(path: Path) -> Script:
    return Script.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def load_dials(path: Path) -> Dials:
    return Dials.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def load_styling(path: Path) -> StylingInputs:
    return StylingInputs.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
