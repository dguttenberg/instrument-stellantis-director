"""The director LLM call: one Anthropic request per cell, forced to emit a
schema-valid cell-output envelope via tool use (spec §3, §5).

Forced tool use (tool_choice → a single `emit_cell_output` tool) guarantees the
model returns the envelope shape rather than prose. We validate the tool input
against the Pydantic envelope and make one corrective retry on a validation miss.
We deliberately do not use `strict` tool schemas: Pydantic emits oneOf+discriminator
for the output union, which the structured-output validator does not accept, and
forcing a specific tool is incompatible with extended thinking.
"""

from __future__ import annotations

import json
from typing import List, Optional

import anthropic
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from ..config import Settings, get_settings
from ..schemas.bg import BGResponse
from ..schemas.cell import CellInput, CellOutput, CellOutputEnvelope
from ..schemas.dials import Dials, StylingInputs
from .cell_specs import allowed_output_types
from .prompt import build_system_prompt, build_user_payload

TOOL_NAME = "emit_cell_output"


class _DirectorEmission(BaseModel):
    """What the director fills in; the agent supplies cell_id/cell_type/draft."""

    model_config = ConfigDict(extra="forbid")

    outputs: List[CellOutput]
    gaps_flagged: List[str] = []

    @model_validator(mode="before")
    @classmethod
    def _coerce_stringified(cls, data):
        # Opus tool-use occasionally serializes array fields as a JSON string.
        if isinstance(data, dict):
            for k in ("outputs", "gaps_flagged"):
                if isinstance(data.get(k), str):
                    try:
                        data[k] = json.loads(data[k])
                    except (ValueError, TypeError):
                        pass
        return data


_EMISSION_SCHEMA = _DirectorEmission.model_json_schema()


class Director:
    def __init__(self, settings: Optional[Settings] = None, client: Optional[anthropic.Anthropic] = None):
        self.settings = settings or get_settings()
        if client is not None:
            self.client = client
        else:
            kwargs = {}
            if self.settings.anthropic_api_key:
                kwargs["api_key"] = self.settings.anthropic_api_key
            self.client = anthropic.Anthropic(**kwargs)

    def run(
        self,
        cell: CellInput,
        slices: BGResponse,
        dials: Dials,
        styling: StylingInputs,
        prior_cell_resolved: Optional[dict] = None,
    ) -> CellOutputEnvelope:
        system = build_system_prompt(styling, dials, cell.cell_type)
        payload = build_user_payload(cell, slices, prior_cell_resolved)
        tool = {
            "name": TOOL_NAME,
            "description": "Emit the cell-output envelope for this cell. Call exactly once.",
            "input_schema": _EMISSION_SCHEMA,
        }
        messages = [{"role": "user", "content": payload}]

        last_error: Optional[str] = None
        for attempt in range(2):
            resp = self.client.messages.create(
                model=self.settings.director_model,
                max_tokens=self.settings.director_max_tokens,
                system=system,
                tools=[tool],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=messages,
            )
            if resp.stop_reason == "refusal":
                raise RuntimeError(f"Director refused for cell {cell.cell_id}")

            tool_use_id, tool_input = _extract_tool_call(resp)
            if tool_input is not None:
                try:
                    emission = _DirectorEmission.model_validate(tool_input)
                    return self._finalize(cell, emission)
                except ValidationError as e:
                    last_error = str(e)
            else:
                last_error = "No emit_cell_output tool call found in the response."

            # Build a valid follow-up turn for the corrective retry. After an
            # assistant tool_use block, the next user turn MUST carry a matching
            # tool_result block (API requirement) — not a bare text message.
            messages.append({"role": "assistant", "content": resp.content})
            fix_msg = (
                "Your previous emit_cell_output call did not validate:\n"
                f"{last_error}\nFix it and call emit_cell_output again."
            )
            if tool_use_id is not None:
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {"type": "tool_result", "tool_use_id": tool_use_id, "content": fix_msg, "is_error": True}
                        ],
                    }
                )
            else:
                messages.append({"role": "user", "content": fix_msg})

        raise RuntimeError(f"Director failed to emit a valid envelope for {cell.cell_id}: {last_error}")

    def _finalize(self, cell: CellInput, emission: _DirectorEmission) -> CellOutputEnvelope:
        allowed = set(allowed_output_types(cell.cell_type))
        kept: List[CellOutput] = []
        gaps = list(emission.gaps_flagged)
        for out in emission.outputs:
            if out.type in allowed:
                kept.append(out)
            else:
                gaps.append(f"director emitted disallowed output type '{out.type}' for {cell.cell_type}; dropped")
        return CellOutputEnvelope(
            cell_id=cell.cell_id,
            cell_type=cell.cell_type,
            draft=True,
            outputs=kept,
            gaps_flagged=gaps,
        )


def _extract_tool_call(resp):
    """Return (tool_use_id, input) for the emit_cell_output call, or (None, None)."""
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == TOOL_NAME:
            return block.id, block.input
    return None, None
