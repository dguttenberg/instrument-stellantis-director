"""Upstash Redis (REST) draft store for serverless (Vercel) deployments.

The local SQLite store can't persist across Vercel's ephemeral, read-only-FS
function invocations, so the hosted demo stores drafts here instead. REST-based
(no socket pooling), so it's safe to construct per request. Same DraftStore
protocol as LocalDraftStore — the runner/API don't change.

Layout: one key per record `draft:{cell_id}` -> DraftRecord JSON, plus a set
`drafts:index` of cell_ids for list().
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from ..schemas.cell import CellOutputEnvelope
from .store import DraftRecord, compute_review_status

_KEY = "draft:{}"
_INDEX = "drafts:index"


class UpstashDraftStore:
    def __init__(self, url: str, token: str, client=None):
        if client is not None:
            self._redis = client
        else:
            from upstash_redis import Redis

            self._redis = Redis(url=url, token=token)

    def put(self, envelope: CellOutputEnvelope) -> DraftRecord:
        status = compute_review_status(envelope)
        record = DraftRecord(
            cell_id=envelope.cell_id,
            cell_type=envelope.cell_type,
            review_status=status,
            approved=status == "auto_accept",
            envelope=envelope.model_dump(),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._redis.set(_KEY.format(envelope.cell_id), record.model_dump_json())
        self._redis.sadd(_INDEX, envelope.cell_id)
        return record

    def get(self, cell_id: str) -> Optional[DraftRecord]:
        raw = self._redis.get(_KEY.format(cell_id))
        return DraftRecord.model_validate_json(raw) if raw else None

    def list(self) -> List[DraftRecord]:
        ids = list(self._redis.smembers(_INDEX) or [])
        if not ids:
            return []
        raws = self._redis.mget(*[_KEY.format(i) for i in ids])
        records = [DraftRecord.model_validate_json(r) for r in raws if r]
        return sorted(records, key=lambda r: r.created_at)

    def approve(self, cell_id: str) -> Optional[DraftRecord]:
        record = self.get(cell_id)
        if record is None:
            return None
        record.approved = True
        self._redis.set(_KEY.format(cell_id), record.model_dump_json())
        return record
