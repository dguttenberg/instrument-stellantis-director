"""All six business centers resolve through Brand Gravity, and the /lanes endpoint
lists them. NE/SE/MW/W use authored environmental_context + fall back to the brand
creative_intent baseline."""

import uuid

import director_agent.api.app as appmod
from director_agent.bg import build_client
from director_agent.director.cell_specs import buckets_for
from director_agent.schemas.bg import BGRequest
from fastapi.testclient import TestClient

client = TestClient(appmod.app)
ALL = ["great_lakes", "southwest", "northeast", "southeast", "midwest", "west"]


def test_lanes_endpoint_lists_six_bcs():
    lanes = client.get("/lanes").json()["lanes"]
    keys = [x["key"] for x in lanes]
    assert keys == ALL
    assert all("label" in x and "abbrev" in x for x in lanes)


def test_every_bc_resolves_env_and_creative_with_no_gaps():
    bg = build_client()
    for lane in ALL:
        resp = bg.resolve(BGRequest(
            request_id=str(uuid.uuid4()), brand="ram", lane=lane,
            buckets_needed=buckets_for("regionalized_ai_scenes", "D28H91", "winter")))
        assert f"environmental_context.{lane}" in resp.slices, lane
        assert any(k.startswith("creative_intent") for k in resp.slices), lane
        assert resp.gaps_flagged == [], (lane, resp.gaps_flagged)


def test_new_lanes_fall_back_to_brand_creative_intent():
    bg = build_client()
    resp = bg.resolve(BGRequest(
        request_id="x", brand="ram", lane="northeast",
        buckets_needed=buckets_for("regionalized_ai_scenes", "D28H91", "winter")))
    # No NE lane creative_intent authored -> resolves the brand baseline.
    assert "creative_intent.ram" in resp.slices
    assert resp.slices["creative_intent.ram"].scope_resolved == "brand"


def test_environments_differ_by_bc():
    bg = build_client()

    def winter(lane):
        r = bg.resolve(BGRequest(request_id="x", brand="ram", lane=lane,
                       buckets_needed=buckets_for("existing_running_footage", None, "winter")))
        return r.slices[f"environmental_context.{lane}"].content["weather"]

    weathers = {lane: winter(lane) for lane in ALL}
    assert len(set(weathers.values())) == len(ALL)  # all six distinct
