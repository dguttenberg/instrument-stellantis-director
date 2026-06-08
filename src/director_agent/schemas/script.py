"""Structured script: scenes tagged with cell_type by the human (spec §2, §5)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import CellType


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell_id: str
    cell_type: CellType
    scene_index: int
    scene_description: str
    # Production intent the human tags on the scene; the agent inherits.
    nameplate: str = "Ram 1500"
    trim_intent: Optional[str] = None  # e.g. "D28H91"
    color_intent_hint: Optional[str] = None  # e.g. "red"; director still resolves vs palette
    camera_angles: List[str] = Field(default_factory=list)
    super_called: bool = False
    super_intent: Optional[str] = None


class Script(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script_id: str
    total_scenes: int
    scenes: List[Scene]
