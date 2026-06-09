"""TwelveLabs controlled filters: taxonomy, schema, prompt injection, endpoint."""

import director_agent.api.app as appmod
from director_agent.director.prompt import build_system_prompt
from director_agent.schemas.cell import TwelveLabsQuery
from director_agent.schemas.dials import Dials, StylingInputs
from director_agent.twelvelabs import FILTER_KEYS, load_taxonomy, prompt_vocab
from fastapi.testclient import TestClient

client = TestClient(appmod.app)
_S = StylingInputs(tone_of_voice="x", creative_intent="x", direction="x", lighting_aesthetic="x", storytelling_flow="x")


def test_taxonomy_has_trim_and_known_values():
    cats = {c["key"]: c for c in load_taxonomy()["categories"]}
    assert "trim" in cats and "trim" in FILTER_KEYS
    assert "Laramie" in cats["trim"]["values"] and "Tungsten" in cats["trim"]["values"]
    assert cats["brand"]["values"] == ["Dodge", "Chrysler", "Ram", "Jeep"]
    assert "M18364 Dodge MAP Retail" in cats["project"]["values"]


def test_query_accepts_sparse_filters():
    q = TwelveLabsQuery.model_validate({
        "type": "twelvelabs_query", "confidence": "high",
        "query": {"tags": ["ram_1500"], "natural_language": "ram 1500 driving, winter",
                  "filters": {"brand": ["Ram"], "vehicle_type": ["Truck"], "trim": ["Laramie"],
                              "action": ["Driving"], "environment": ["Rural", "Overcast"]}}})
    assert q.query.filters.trim == ["Laramie"]
    assert q.query.filters.color is None  # sparse — not every category set


def test_prompt_injects_filters_only_for_retrieval_cells():
    erf = build_system_prompt(_S, Dials(), "existing_running_footage")
    assert "TwelveLabs filters" in erf
    assert "leaving one unset is normal" in erf            # the "not every filter" instruction
    assert "Off-Roading" in erf and "Laramie" in erf       # vocabulary present (incl. trim)
    ais = build_system_prompt(_S, Dials(), "regionalized_ai_scenes")
    assert "TwelveLabs filters" not in ais  # CG/AI cell emits no twelvelabs_query


def test_filters_endpoint():
    body = client.get("/twelvelabs-filters").json()
    keys = [c["key"] for c in body["categories"]]
    assert "trim" in keys and "duration" in keys


def test_prompt_vocab_lists_categories():
    v = prompt_vocab()
    assert "Brand" in v and "Trim" in v and "Ram" in v
