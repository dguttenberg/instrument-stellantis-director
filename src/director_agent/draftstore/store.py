"""DraftStore protocol + record + confidence-driven review status (spec §7)."""

from __future__ import annotations

from typing import List, Optional, Protocol

from pydantic import BaseModel, ConfigDict
from typing_extensions import Literal

from ..schemas.cell import CellOutputEnvelope

# Review status drives the human gate (spec §7):
#   auto_accept  -> all outputs high; visible in approve list, default-accepted
#   needs_approve-> some output medium; requires explicit approve
#   blocked      -> some output low; requires approve-with-edit or reject
ReviewStatus = Literal["auto_accept", "needs_approve", "blocked"]


def compute_review_status(envelope: CellOutputEnvelope) -> ReviewStatus:
    confidences = [getattr(o, "confidence", "high") for o in envelope.outputs]
    if any(c == "low" for c in confidences):
        return "blocked"
    if any(c == "medium" for c in confidences):
        return "needs_approve"
    return "auto_accept"


class DraftRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell_id: str
    cell_type: str
    review_status: ReviewStatus
    approved: bool
    envelope: dict
    created_at: str


class DraftStore(Protocol):
    def put(self, envelope: CellOutputEnvelope) -> DraftRecord: ...
    def get(self, cell_id: str) -> Optional[DraftRecord]: ...
    def list(self) -> List[DraftRecord]: ...
    def approve(self, cell_id: str) -> Optional[DraftRecord]: ...
