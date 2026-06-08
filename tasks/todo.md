# Production Pipeline Agent — TODO

Approved plan: `~/.claude/plans/radiant-twirling-aurora.md`.
Demo: `MAP_Retail_Ram_Test :15 South`, lanes `great_lakes` then `southwest`.

## Phase 0 — Scaffold
- [x] pyproject.toml, .gitignore, .env.example
- [x] config.py (env-driven settings)
- [x] tasks/todo.md + tasks/lessons.md
- [x] venv + install deps (anthropic 0.107, pydantic 2.13)

## Phase 1 — Vertical slice (regionalized_ai_scenes · great_lakes · scene 5)
- [x] schemas needed for this path (bg, cell, script, dials, common)
- [x] GL + brand fixtures for this bucket-set (deterministic values verbatim)
- [x] bg/fixture_provider.py (deepest-scope-wins, per-run cache, gaps)
- [x] director/{cell_specs,prompt,director}.py (claude-api skill confirmed opus-4-8 + forced tool-use)
- [x] draftstore/local_store.py + outputs/substance_excel.py
- [x] real Anthropic call -> valid envelope -> row drops into the demo xlsx (DONE, live)

## Phase 2 — Breadth
- [x] author remaining fixtures (SW lane env/audience/creative, baseline audience_resonance)
- [x] all 4 cell types in cell_specs + prompt
- [x] full South:15 script fixture + dials + styling configs
- [x] pipeline/runner.py + api/app.py (POST /run, GET/POST drafts) + scripts/run_demo.py
- [x] http_provider + shawn_adapter thin stubs
- [x] bonus: validation.py invariants wired into the runner as review flags

## Phase 3 — Verify
- [x] test_schemas, test_fixture_provider, test_substance_excel
- [x] test_runner_offline (mocked director; GL+SW differ; continuity threaded)
- [x] test_golden_invariants (spec §3 brand rules + §5.4 worked example)
- [x] one live end-to-end run via run_demo.py (DONE: 12 cells across GL+SW, all auto_accept, 0 invariant flags)
- [x] README with reconciled live-BG framing (§9 deltas)

## Review
- 24 tests pass; ruff clean. WORKING end-to-end LIVE: `python scripts/run_demo.py`
  runs South:15 across GL+SW (12 live opus-4-8 calls). Full pipeline: BG resolve
  (deepest-scope-wins + season/sku filters + cache) -> director (forced tool-use,
  validate+retry, stringified-outputs coercion, allowed-type enforcement) ->
  Substance xlsx (exact 6-col format) -> draft store (confidence-driven status) ->
  invariant review flags.
- Pitch mechanics verified (advisor review): dials are OPERATIVE (regional_specificity
  0.2 -> generic winter / 0.9 -> saturated Great Lakes); confidence calibrated so the
  §7 approval gate fires (10/12 needs_approve).
- Bugs found+fixed during live verify (all have regression tests): nameplate
  string-split, corrective-retry tool_result pairing, stringified-outputs coercion.
- OPEN DECISION for Doug: hex doesn't differ by lane (both red, brand-valid).
  color_intent_hint is per-Scene (shared across lanes); a per-lane color override
  is NOT built. Accept, or ask me to add the override.
- Stack: Python 3.9 venv (system python), opus-4-8 director, BG via fixtures.
