"""Local SQLite draft store. Stands in for Shawn's draft system for the prototype;
a ShawnHttpDraftStore can replace it behind the same DraftStore protocol."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from ..schemas.cell import CellOutputEnvelope
from .store import DraftRecord, compute_review_status


class LocalDraftStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Single-process server → serialize writers so concurrent /run/cell calls (many
        # regions at once) never collide on the SQLite write lock and drop a cell.
        self._write_lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        # timeout/busy_timeout = writers WAIT for the lock instead of failing fast with
        # "database is locked". WAL is set once in _init_db (not per-connect — switching
        # journal mode on every concurrent connection itself contends).
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_db(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("PRAGMA journal_mode=WAL")  # persistent; set once
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS drafts (
                    cell_id       TEXT PRIMARY KEY,
                    cell_type     TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    approved      INTEGER NOT NULL DEFAULT 0,
                    envelope_json TEXT NOT NULL,
                    created_at    TEXT NOT NULL
                )
                """
            )

    def put(self, envelope: CellOutputEnvelope) -> DraftRecord:
        status = compute_review_status(envelope)
        approved = status == "auto_accept"  # high-confidence default-accepted (spec §7)
        created_at = datetime.now(timezone.utc).isoformat()
        envelope_json = envelope.model_dump_json()
        with self._write_lock, closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO drafts (cell_id, cell_type, review_status, approved, envelope_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cell_id) DO UPDATE SET
                    cell_type=excluded.cell_type,
                    review_status=excluded.review_status,
                    approved=excluded.approved,
                    envelope_json=excluded.envelope_json,
                    created_at=excluded.created_at
                """,
                (envelope.cell_id, envelope.cell_type, status, int(approved), envelope_json, created_at),
            )
        return DraftRecord(
            cell_id=envelope.cell_id,
            cell_type=envelope.cell_type,
            review_status=status,
            approved=approved,
            envelope=json.loads(envelope_json),
            created_at=created_at,
        )

    def get(self, cell_id: str) -> Optional[DraftRecord]:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM drafts WHERE cell_id = ?", (cell_id,)).fetchone()
        return _row_to_record(row) if row else None

    def list(self) -> List[DraftRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM drafts ORDER BY created_at").fetchall()
        return [_row_to_record(r) for r in rows]

    def approve(self, cell_id: str) -> Optional[DraftRecord]:
        with self._write_lock, closing(self._connect()) as conn, conn:
            cur = conn.execute("UPDATE drafts SET approved = 1 WHERE cell_id = ?", (cell_id,))
            if cur.rowcount == 0:
                return None
        return self.get(cell_id)


def _row_to_record(row: sqlite3.Row) -> DraftRecord:
    return DraftRecord(
        cell_id=row["cell_id"],
        cell_type=row["cell_type"],
        review_status=row["review_status"],
        approved=bool(row["approved"]),
        envelope=json.loads(row["envelope_json"]),
        created_at=row["created_at"],
    )
