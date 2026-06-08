"""Shawn's draft-system HTTP adapter (thin stub).

When Shawn's draft system exposes an API, implement these calls against it; the
DraftStore protocol means the runner needs no changes. Unexercised for now —
the prototype uses LocalDraftStore.
"""

from __future__ import annotations

from typing import List, Optional

import httpx

from ..schemas.cell import CellOutputEnvelope
from .store import DraftRecord, compute_review_status


class ShawnHttpDraftStore:
    def __init__(self, base_url: str, api_key: str = "", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict:
        h = {"content-type": "application/json"}
        if self.api_key:
            h["authorization"] = f"Bearer {self.api_key}"
        return h

    def put(self, envelope: CellOutputEnvelope) -> DraftRecord:  # pragma: no cover - stub
        resp = httpx.post(
            f"{self.base_url}/drafts",
            json={
                "envelope": envelope.model_dump(),
                "review_status": compute_review_status(envelope),
            },
            headers=self._headers(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return DraftRecord.model_validate(resp.json())

    def get(self, cell_id: str) -> Optional[DraftRecord]:  # pragma: no cover - stub
        raise NotImplementedError("Wire to Shawn's draft system when its API lands.")

    def list(self) -> List[DraftRecord]:  # pragma: no cover - stub
        raise NotImplementedError("Wire to Shawn's draft system when its API lands.")

    def approve(self, cell_id: str) -> Optional[DraftRecord]:  # pragma: no cover - stub
        raise NotImplementedError("Wire to Shawn's draft system when its API lands.")
