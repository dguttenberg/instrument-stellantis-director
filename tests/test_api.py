"""API surface: UI page, project, per-cell run, edit, exports — driven by a fake
director so it runs offline."""

import director_agent.api.app as appmod
from director_agent.director.director import Director
from director_agent.draftstore import LocalDraftStore
from director_agent.project import ProjectStore
from fastapi.testclient import TestClient

from conftest import FakeAnthropic

client = TestClient(appmod.app)

# regionalized_running_w_cgi_ai (scene 1) allows twelvelabs_query, cg_env_prompt, super_text.
EMISSION = {
    "outputs": [
        {"type": "twelvelabs_query", "confidence": "high",
         "query": {"tags": ["ram_1500", "driving"], "natural_language": "ram 1500 driving toward camera, daylight"}},
        {"type": "cg_env_prompt", "confidence": "medium",
         "for_pipeline": "runway_env_refs_for_replacement", "prompt": "Great Lakes winter, no people."},
        {"type": "super_text", "confidence": "high",
         "content": "The holidays are all about giving around here.", "voice_tags": ["edgy_bold_direct"]},
    ]
}


def _fake_backend(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "Director", lambda settings=None: Director(client=FakeAnthropic(EMISSION)))
    monkeypatch.setattr(appmod, "_draft_store", lambda: LocalDraftStore(tmp_path / "d.sqlite"))
    monkeypatch.setattr(appmod, "_project_store", lambda: ProjectStore(tmp_path / "project.json"))


def test_index_page_is_dcp_branded():
    r = client.get("/")
    assert r.status_code == 200
    assert "Doner" in r.text and "DCP" in r.text
    assert "/ingest" in r.text and "/run/cell" in r.text  # workflow wiring present


def test_project_starts_blank_then_sample_then_edit(monkeypatch, tmp_path):
    _fake_backend(monkeypatch, tmp_path)
    # Blank on first load so an upload visibly populates the matrix.
    assert client.get("/project").json()["script"]["scenes"] == []

    # Load-sample fallback populates the bundled South:15.
    sample = client.post("/project/sample").json()
    assert len(sample["script"]["scenes"]) == 6

    r = client.put("/project/scenes/1", json={"cell_type": "regionalized_ai_scenes"})
    assert r.status_code == 200 and r.json()["cell_type"] == "regionalized_ai_scenes"
    assert client.get("/project").json()["script"]["scenes"][0]["cell_type"] == "regionalized_ai_scenes"


def test_run_cell_then_edit_then_export(monkeypatch, tmp_path):
    _fake_backend(monkeypatch, tmp_path)
    client.post("/project/sample")  # populate the matrix (blank by default)

    rc = client.post("/run/cell", json={"lane": "great_lakes", "scene_index": 1,
                                        "dials": {"regional_specificity": 0.9}})
    assert rc.status_code == 200
    env = rc.json()["envelope"]
    cell_id = env["cell_id"]
    assert cell_id == "south15_scene1__great_lakes"
    assert {o["type"] for o in env["outputs"]} == {"twelvelabs_query", "cg_env_prompt", "super_text"}
    assert env["provenance"]  # surfaced for review
    assert rc.json()["record"]["review_status"] == "needs_approve"  # cg_env medium -> gate fires

    # Edit what the director made: change the super copy + make it all-high.
    edited = [
        {"type": "twelvelabs_query", "confidence": "high",
         "query": {"tags": ["ram_1500"], "natural_language": "ram driving"}},
        {"type": "cg_env_prompt", "confidence": "high", "for_pipeline": "runway", "prompt": "edited env, no people."},
        {"type": "super_text", "confidence": "high", "content": "Edited super line.", "voice_tags": []},
    ]
    pe = client.put(f"/drafts/{cell_id}", json={"outputs": edited})
    assert pe.status_code == 200
    rec = pe.json()
    assert rec["review_status"] == "auto_accept"  # now all-high
    saved_super = next(o for o in rec["envelope"]["outputs"] if o["type"] == "super_text")
    assert saved_super["content"] == "Edited super line."

    # TwelveLabs export reflects the cell.
    tl = client.get("/export/twelvelabs.json").json()
    assert any(row["cell_id"] == cell_id and row["query_type"] == "footage" for row in tl)
    assert client.get("/export/twelvelabs.csv").status_code == 200
    assert client.get("/export/cgi.xlsx").status_code == 200


def test_edit_reflags_invariants(monkeypatch, tmp_path):
    _fake_backend(monkeypatch, tmp_path)
    client.post("/project/sample")
    client.post("/run/cell", json={"lane": "great_lakes", "scene_index": 1})
    cid = "south15_scene1__great_lakes"
    # Introduce an all-caps RAM violation via edit -> should be re-flagged.
    bad = [{"type": "super_text", "confidence": "high", "content": "Get the strongest RAM ever.", "voice_tags": []}]
    rec = client.put(f"/drafts/{cid}", json={"outputs": bad}).json()
    assert any("invariant" in g and "all-caps" in g for g in rec["envelope"]["gaps_flagged"])
