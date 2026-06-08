"""Shared test fixtures: a fake Anthropic client that returns a canned tool_use
response, so the director plumbing is exercised without a live API call."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from director_agent.bg import build_client
from director_agent.director.cell_specs import buckets_for
from director_agent.schemas.bg import BGRequest
from director_agent.schemas.cell import CellInput, ScriptPosition
from director_agent.schemas.dials import Dials, StylingInputs


class FakeAnthropic:
    """Stands in for anthropic.Anthropic. `messages.create` returns, in order, one
    response per entry in `tool_outputs` (a single dict is treated as a one-element
    list). Each response is a single tool_use block carrying that output. Records
    the `messages` kwarg of every call so the retry-turn shape can be asserted."""

    def __init__(self, tool_outputs, tool_name: str = "emit_cell_output"):
        if isinstance(tool_outputs, dict):
            tool_outputs = [tool_outputs]
        self._outputs = list(tool_outputs)
        self._tool_name = tool_name
        self.messages = SimpleNamespace(create=self._create)
        self.calls = 0
        self.received_messages = []

    def _create(self, **kwargs):
        self.received_messages.append(kwargs.get("messages"))
        out = self._outputs[min(self.calls, len(self._outputs) - 1)]
        self.calls += 1
        block = SimpleNamespace(type="tool_use", name=self._tool_name, id=f"toolu_fake_{self.calls}", input=out)
        return SimpleNamespace(stop_reason="tool_use", content=[block])


@pytest.fixture
def demo_dials() -> Dials:
    return Dials(styling_carry_over=0.75, regional_specificity=0.6, voice_adherence=0.8, narrative_continuity=0.7)


@pytest.fixture
def demo_styling() -> StylingInputs:
    return StylingInputs(
        tone_of_voice="edgy, bold, rebellious, direct",
        creative_intent="year-end big finish, capability-led, no people in frame",
        direction="cinematic, motion-forward, vehicle-as-hero",
        lighting_aesthetic="natural-feeling, regionally truthful, golden where season allows",
        storytelling_flow="each frame advances the spot, no isolated beats",
    )


def make_cell(cell_type: str, lane: str = "great_lakes", **overrides) -> CellInput:
    base = dict(
        cell_id=f"test_{cell_type}",
        cell_type=cell_type,
        scene_description="Wide shot of Ram with Cummins Turbo Diesel towing.",
        script_position=ScriptPosition(script_id="ram_wrapup_15s_south", scene_index=5, total_scenes=6),
        brand="ram",
        lane=lane,
        trim_intent="D28H91",
        color_intent_hint="red",
        camera_angles=["action_front_3q", "hero_front"],
        super_called=True,
        super_intent="high output 6.7L Cummins turbo diesel",
    )
    base.update(overrides)
    return CellInput(**base)


def resolve_slices(cell: CellInput, season: str = "winter"):
    needs = buckets_for(cell.cell_type, cell.trim_intent, season=season)
    req = BGRequest(
        request_id=str(uuid.uuid4()),
        brand=cell.brand,
        lane=cell.lane,
        buckets_needed=needs,
        context_hint=cell.scene_description,
    )
    return build_client().resolve(req)
