"""Schema strictness + the spec §5.4 worked example round-trips."""

import pytest
from pydantic import ValidationError

from director_agent.schemas.cell import CellOutputEnvelope, SubstanceRowData


def test_substance_row_aliases_are_exact_headers():
    data = {
        "Nameplate": "Ram 1500",
        "Specific Trim Request": "D28H91 - Tradesman (Base)",
        "Location Variant": "Great Lakes",
        "Color Preference (HEX)": "#B61A22",
        "Camera Angles": "action_front_3q, hero_front",
        "AI Image Generator Prompt": "A photorealistic 360 HDRI ... no people.",
    }
    row = SubstanceRowData.model_validate(data)
    assert row.color_preference_hex == "#B61A22"
    assert list(row.model_dump(by_alias=True).keys()) == list(data.keys())


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        SubstanceRowData.model_validate(
            {
                "Nameplate": "Ram 1500",
                "Specific Trim Request": "x",
                "Location Variant": "y",
                "Color Preference (HEX)": "#000",
                "Camera Angles": "a",
                "AI Image Generator Prompt": "p",
                "BOGUS": 1,
            }
        )


def test_spec_5_4_worked_example_parses():
    example = {
        "cell_id": "south15_scene6",
        "cell_type": "regionalized_ai_scenes",
        "draft": True,
        "outputs": [
            {
                "type": "substance_row",
                "confidence": "high",
                "row": {
                    "Nameplate": "Ram 1500",
                    "Specific Trim Request": "D28H91 - Tradesman (Base)",
                    "Location Variant": "Great Lakes",
                    "Color Preference (HEX)": "#B61A22",
                    "Camera Angles": "action_front_3q, hero_front",
                    "AI Image Generator Prompt": "A photorealistic 360 HDRI ... no people in frame.",
                },
                "director_notes": "Red reads warm against the cool palette.",
            },
            {
                "type": "super_text",
                "confidence": "high",
                "content": "Get the high output 6.7L Cummins turbo diesel.",
                "voice_tags": ["edgy_bold_direct"],
            },
        ],
        "gaps_flagged": [],
    }
    env = CellOutputEnvelope.model_validate(example)
    assert [o.type for o in env.outputs] == ["substance_row", "super_text"]
    assert env.outputs[0].row.location_variant == "Great Lakes"
