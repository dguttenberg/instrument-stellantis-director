"""Each cell type maps to one clear recommendation; output roles are correct."""

import director_agent.api.app as appmod
from director_agent.recommendations import output_role, recommendation_for
from fastapi.testclient import TestClient

client = TestClient(appmod.app)


def test_recommendation_per_cell_type():
    assert recommendation_for("existing_running_footage")["tool"] == "twelvelabs"
    assert recommendation_for("existing_running_footage")["preferred"] is True  # core footage primary
    assert recommendation_for("stock")["tool"] == "twelvelabs"
    assert recommendation_for("regionalized_running_w_cgi_ai")["tool"] == "cgai"
    assert recommendation_for("regionalized_ai_scenes")["tool"] == "cgai"


def test_output_roles():
    # regionalized_running: cg_env is the headline, twelvelabs is the supporting base plate.
    assert output_role("regionalized_running_w_cgi_ai", "cg_env_prompt") == "primary"
    assert output_role("regionalized_running_w_cgi_ai", "twelvelabs_query") == "supporting"
    assert output_role("existing_running_footage", "twelvelabs_query") == "primary"
    assert output_role("regionalized_ai_scenes", "substance_row") == "primary"
    assert output_role("stock", "super_text") == "super"


def test_recommendations_endpoint():
    body = client.get("/recommendations").json()
    assert body["tool_label"]["twelvelabs"] == "TwelveLabs"
    assert "headline" in body["recommendations"]["existing_running_footage"]
