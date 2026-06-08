"""Golden invariants (spec §5 worked examples + the §3 brand rules). Schema
validity is necessary but not sufficient; these assert the director honored the
load-bearing rules. The same check_envelope() runs on live output."""


from director_agent.schemas.cell import CellOutputEnvelope
from director_agent.validation import check_envelope

GL_HEX = ["#B61A22", "#4E5154", "#1A6FB3", "#FFFFFF", "#000000"]
GL_ANGLES = ["action_front_3q", "hero_front", "configurator_front_3q", "front_face_low", "front_TBD"]


def _clean_ai_scene_envelope():
    return CellOutputEnvelope.model_validate(
        {
            "cell_id": "south15_scene5__great_lakes",
            "cell_type": "regionalized_ai_scenes",
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
                        "AI Image Generator Prompt": (
                            "A photorealistic 360 HDRI of a Great Lakes winter rural two-lane road, "
                            "snow on the ground, lake-effect gray sky, bare deciduous, salt-streaked "
                            "asphalt; pole barn in mid-distance; no people in frame."
                        ),
                    },
                },
                {
                    "type": "super_text",
                    "confidence": "high",
                    "content": "Get the high output 6.7L Cummins Turbo Diesel.",
                    "voice_tags": ["edgy_bold_direct"],
                },
            ],
        }
    )


def test_clean_envelope_has_no_violations():
    env = _clean_ai_scene_envelope()
    assert check_envelope(env, available_hex=GL_HEX, available_camera_angles=GL_ANGLES) == []


def test_allcaps_ram_is_flagged():
    env = _clean_ai_scene_envelope()
    env.outputs[1].content = "Get the strongest RAM 1500 ever."
    v = check_envelope(env, GL_HEX, GL_ANGLES)
    assert any("all-caps" in x for x in v)


def test_hurricane_cylinder_count_is_flagged():
    env = _clean_ai_scene_envelope()
    env.outputs[1].content = "The Hurricane six-cylinder makes serious power."
    v = check_envelope(env, GL_HEX, GL_ANGLES)
    assert any("Hurricane cylinder" in x for x in v)


def test_people_in_frame_is_flagged():
    env = _clean_ai_scene_envelope()
    env.outputs[0].row.ai_image_generator_prompt = "A rugged driver leans on the Ram 1500 at dusk."
    v = check_envelope(env, GL_HEX, GL_ANGLES)
    assert any("people in frame" in x for x in v)


def test_off_palette_hex_is_flagged():
    env = _clean_ai_scene_envelope()
    env.outputs[0].row.color_preference_hex = "#123456"
    v = check_envelope(env, GL_HEX, GL_ANGLES)
    assert any("not in product_catalog palette" in x for x in v)


def test_bad_camera_angle_is_flagged():
    env = _clean_ai_scene_envelope()
    env.outputs[0].row.camera_angles = "action_front_3q, drone_orbit"
    v = check_envelope(env, GL_HEX, GL_ANGLES)
    assert any("drone_orbit" in x for x in v)


def test_nonverbatim_sponsor_signoff_is_flagged():
    env = _clean_ai_scene_envelope()
    env.outputs[1].content = "Sponsored by Ram. Nothing stops us."
    v = check_envelope(env, GL_HEX, GL_ANGLES)
    assert any("sponsor sign-off" in x for x in v)
