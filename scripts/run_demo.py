#!/usr/bin/env python
"""Two-row demo path (spec §9): run the MAP_Retail_Ram_Test :15 South script
through great_lakes, then southwest, and print the scene-by-lane matrix.

Requires ANTHROPIC_API_KEY (the director makes a live Claude call per cell).
Run from anywhere:  python scripts/run_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from director_agent.bg import build_client
from director_agent.config import DATA_DIR, get_settings
from director_agent.director import Director
from director_agent.draftstore import LocalDraftStore
from director_agent.pipeline import PipelineRunner, load_dials, load_script, load_styling

LANES = ["great_lakes", "southwest"]


def _summarize(envelope) -> str:
    parts = []
    for o in envelope.outputs:
        if o.type == "substance_row":
            parts.append(f"substance[{o.row.color_preference_hex}]")
        elif o.type == "super_text":
            parts.append("super")
        else:
            parts.append(o.type)
    return "+".join(parts) if parts else "(none)"


def main() -> int:
    settings = get_settings()
    if not (settings.anthropic_api_key or _env_key()):
        print("ERROR: ANTHROPIC_API_KEY is not set. Add it to .env or the environment.", file=sys.stderr)
        return 2

    script = load_script(DATA_DIR / "scripts" / "map_retail_ram_test_15_south.json")
    dials = load_dials(DATA_DIR / "dials" / "year_end_demo.json")
    styling = load_styling(DATA_DIR / "styling" / "year_end_demo.json")

    # Fresh stores for a reproducible demo run.
    draft_path = settings.draft_store_abspath
    substance_path = settings.substance_out_abspath
    for p in (draft_path, substance_path):
        if Path(p).exists():
            Path(p).unlink()

    store = LocalDraftStore(draft_path)
    director = Director(settings)

    results = {}
    for lane in LANES:
        print(f"\n=== Running {script.script_id} | lane = {lane} ===")
        runner = PipelineRunner(
            bg_client=build_client(settings),  # fresh per-run slice cache
            director=director,
            draft_store=store,
            substance_out_path=substance_path,
            season="winter",
        )
        result = runner.run(script, lane=lane, dials=dials, styling=styling)
        results[lane] = result
        for env, rec in zip(result.envelopes, result.records):
            print(f"  scene {env.cell_id:<32} {env.cell_type:<30} {_summarize(env):<30} [{rec.review_status}]")

    _print_matrix(script, results)
    print(f"\nSubstance rows  -> {substance_path}")
    print(f"Draft store     -> {draft_path}")
    return 0


def _print_matrix(script, results) -> None:
    print("\n=== Matrix (scene x lane) ===")
    header = f"{'scene / cell_type':<46}" + "".join(f"{lane:<34}" for lane in LANES)
    print(header)
    print("-" * len(header))
    for i, scene in enumerate(script.scenes):
        label = f"{scene.scene_index}. {scene.cell_type}"
        row = f"{label:<46}"
        for lane in LANES:
            env = results[lane].envelopes[i]
            rec = results[lane].records[i]
            row += f"{_summarize(env) + ' [' + rec.review_status + ']':<34}"
        print(row)


def _env_key() -> str:
    import os

    return os.environ.get("ANTHROPIC_API_KEY", "")


if __name__ == "__main__":
    raise SystemExit(main())
