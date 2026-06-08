"""Shared types."""

from __future__ import annotations

from typing import Literal

# Confidence drives draft-system review priority (spec §7):
#   high   -> visible in approve list, default-accepted unless rejected
#   medium -> requires explicit approve
#   low    -> blocked, requires approve-with-edit or reject
Confidence = Literal["high", "medium", "low"]

# The four cell types (spec §5). Cell type is decided by the script writer and
# tagged on the scene; the agent inherits, never decides.
CellType = Literal[
    "regionalized_running_w_cgi_ai",
    "stock",
    "existing_running_footage",
    "regionalized_ai_scenes",
]
