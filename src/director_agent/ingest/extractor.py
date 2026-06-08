"""Extract a draft scene matrix from an uploaded deck via one Claude call.

Same forced-tool-use pattern as the director: Claude must call `emit_draft_script`,
returning per-scene description, super, and a SUGGESTED cell_type (the human confirms
in the matrix — the agent never owns the tag). PDF is sent as a vision document block
(storyboards are image-heavy); PPTX is sent as extracted text.
"""

from __future__ import annotations

import base64
import json
from typing import List, Optional

import anthropic
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from ..config import Settings, get_settings
from ..schemas.common import CellType
from ..schemas.script import Scene, Script
from .pptx_text import slides_text

TOOL_NAME = "emit_draft_script"

SYSTEM = """\
You extract a shot-by-shot draft matrix from an advertising storyboard/deck for an
automotive retail production pipeline. Read the deck and return one scene per shot.

For each scene provide:
  - scene_index: 1-based order
  - scene_description: what's on screen (the action/shot), concise
  - super_called: true if on-screen text / a "super" / a copy line is indicated
  - super_intent: that copy line verbatim if present, else null
  - cell_type: your SUGGESTED production technique (the human will confirm). Choose:
      * existing_running_footage  — find existing footage as-is (badge close-ups,
        specific running/driving shots, feature detail). The default when unsure.
      * stock                     — establishing / thematic / scene-setting stock footage.
      * regionalized_running_w_cgi_ai — existing vehicle running footage with the
        environment replaced by AI (regionalize a generic driving shot).
      * regionalized_ai_scenes    — fully CGI vehicle composited onto an AI environment
        (the most custom/bespoke hero shots).
  - suggested_trim: a trim/SKU if the deck names one, else null

Map any technique labels in the deck to the closest cell_type. If a deck has a row of
technique callouts per shot, honor them. When genuinely unsure, suggest
existing_running_footage. Return JSON only via the emit_draft_script tool.\
"""


class _ExtractedScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_index: int
    scene_description: str
    super_called: bool = False
    super_intent: Optional[str] = None
    cell_type: CellType
    suggested_trim: Optional[str] = None


class _ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenes: List[_ExtractedScene]

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data):
        if isinstance(data, dict) and isinstance(data.get("scenes"), str):
            try:
                data["scenes"] = json.loads(data["scenes"])
            except (ValueError, TypeError):
                pass
        return data


_TOOL = {
    "name": TOOL_NAME,
    "description": "Emit the draft scene matrix extracted from the deck. Call exactly once.",
    "input_schema": _ExtractionResult.model_json_schema(),
}


class DeckExtractor:
    def __init__(self, settings: Optional[Settings] = None, client: Optional[anthropic.Anthropic] = None):
        self.settings = settings or get_settings()
        if client is not None:
            self.client = client
        else:
            kwargs = {}
            if self.settings.anthropic_api_key:
                kwargs["api_key"] = self.settings.anthropic_api_key
            self.client = anthropic.Anthropic(**kwargs)

    def extract(self, filename: str, content: bytes) -> Script:
        lower = filename.lower()
        if lower.endswith(".pdf"):
            user_content = [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": base64.standard_b64encode(content).decode("ascii"),
                    },
                },
                {"type": "text", "text": "Extract the scene matrix from this storyboard deck."},
            ]
        elif lower.endswith((".pptx", ".ppt")):
            text = "\n\n".join(slides_text(content))
            user_content = [
                {"type": "text", "text": f"Extract the scene matrix from this deck text:\n\n{text}"}
            ]
        else:
            raise ValueError(f"Unsupported deck type: {filename} (use .pdf or .pptx)")

        result = self._call(user_content)
        return self._to_script(filename, result)

    def extract_from_text(self, filename: str, text: str) -> Script:
        """Test/CLI seam: extract from already-extracted deck text."""
        result = self._call([{"type": "text", "text": f"Extract the scene matrix:\n\n{text}"}])
        return self._to_script(filename, result)

    def _call(self, user_content) -> _ExtractionResult:
        messages = [{"role": "user", "content": user_content}]
        last_error: Optional[str] = None
        for _ in range(2):
            resp = self.client.messages.create(
                model=self.settings.director_model,
                max_tokens=self.settings.director_max_tokens,
                system=SYSTEM,
                tools=[_TOOL],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=messages,
            )
            tool_id, tool_input = _extract_tool_call(resp)
            if tool_input is not None:
                try:
                    return _ExtractionResult.model_validate(tool_input)
                except ValidationError as e:
                    last_error = str(e)
            else:
                last_error = "No emit_draft_script tool call found."
            messages.append({"role": "assistant", "content": resp.content})
            if tool_id is not None:
                messages.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": tool_id,
                     "content": f"Did not validate: {last_error}. Fix and call emit_draft_script again.",
                     "is_error": True}]})
            else:
                messages.append({"role": "user", "content": f"Fix: {last_error}"})
        raise RuntimeError(f"Deck extraction failed: {last_error}")

    @staticmethod
    def _to_script(filename: str, result: _ExtractionResult) -> Script:
        import re

        stem = re.sub(r"[^a-z0-9]+", "_", filename.rsplit(".", 1)[0].lower()).strip("_") or "deck"
        scenes = [
            Scene(
                cell_id=f"{stem}_scene{s.scene_index}",
                cell_type=s.cell_type,
                scene_index=s.scene_index,
                scene_description=s.scene_description,
                nameplate="Ram 1500",
                trim_intent=s.suggested_trim,
                color_intent_hint=None,
                camera_angles=["action_front_3q", "hero_front"]
                if s.cell_type == "regionalized_ai_scenes"
                else [],
                super_called=s.super_called,
                super_intent=s.super_intent,
            )
            for s in sorted(result.scenes, key=lambda x: x.scene_index)
        ]
        return Script(script_id=stem, total_scenes=len(scenes), scenes=scenes)


def _extract_tool_call(resp):
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == TOOL_NAME:
            return block.id, block.input
    return None, None


def extract_deck(filename: str, content: bytes, settings: Optional[Settings] = None) -> Script:
    return DeckExtractor(settings).extract(filename, content)
