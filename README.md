# instrument-stellantis-director

Production-pipeline agent for the Stellantis Tier 2 Retail AOR pitch. A tagged
script and a dial config go in; for each scene ("cell") the agent assembles a
Brand Gravity request, resolves brand-knowledge slices, runs one Claude director
call, and emits a typed **cell-output envelope** (TwelveLabs queries, CG/AI
environment prompts, Substance rows, super text) to a draft store for human
approval.

Demo: the `MAP_Retail_Ram_Test :15 South` script, run through `great_lakes`, then
`southwest`, watching the scene-by-lane matrix fill.

---

## Architecture

```
POST /run {script, dials, styling_inputs, lane, season}
   └─ pipeline.runner: walk scenes in order (sequential, so the room watches the matrix fill)
        ├─ cell_specs[cell_type] → which BG buckets to request + which output types are allowed
        ├─ BGClient.resolve(request)        # fixture provider (deepest-scope-wins) + per-run cache
        ├─ director.run(slices, dials, styling, prior_cell_resolved)
        │     └─ Claude (claude-opus-4-8), forced tool-use → schema-valid envelope, confidence-tagged
        ├─ validation.check_envelope(...)   # brand-rule invariants → review flags
        ├─ outputs.substance_excel          # substance_row drops into the exact demo xlsx
        └─ DraftStore.put(envelope)         # status by confidence: high=auto-accept, med=needs-approve, low=blocked
GET /drafts · GET /drafts/{id} · POST /drafts/{id}/approve
```

Each cell receives the prior cell's resolved envelope as `prior_cell_resolved`
(continuity). The four dials (`styling_carry_over`, `regional_specificity`,
`voice_adherence`, `narrative_continuity`) and the spot-level styling inputs flow
into the director's system prompt.

The four cell types (the script writer tags each scene; the agent inherits, never
decides): `regionalized_running_w_cgi_ai`, `stock`, `existing_running_footage`,
`regionalized_ai_scenes` (the only one that emits a Substance row).

---

## Setup

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # then set ANTHROPIC_API_KEY
```

Key env vars (see `.env.example`): `ANTHROPIC_API_KEY`, `DIRECTOR_MODEL`
(default `claude-opus-4-8`), `BG_MODE` (`fixture` | `http`), `DRAFT_STORE_PATH`,
`SUBSTANCE_OUT_PATH`.

## Run the demo

```bash
python scripts/run_demo.py          # South:15 through great_lakes then southwest; prints the matrix
```

## Run the local web app (DCP-branded)

```bash
uvicorn director_agent.api.app:app --reload --port 8000
# open http://localhost:8000/
```

A DonerColle Partners–branded workflow application:

1. **Upload** a `.pdf` or `.pptx` storyboard deck → Claude extracts a draft scene
   matrix with a **suggested technique** per scene (`POST /ingest`). Ships seeded
   with the bundled South:15 so it's never empty.
2. **Confirm the matrix** — each scene row is editable: a technique (cell_type)
   dropdown plus editable description / super / trim (`PUT /project/scenes/{i}`).
3. **Run by region** — **Run Great Lakes** / **Run Southwest** fill the matrix
   cell-by-cell, one live director call each (`POST /run/cell`), threading
   continuity.
4. **Review & edit** — click a cell to see a **provenance summary** ("directed
   from: environmental_context (high)…") and **edit every output the director
   made** (super copy, query, prompts, Substance hex/trim/camera); Save
   (`PUT /drafts/{id}`, re-validated + re-flagged) and Approve (§7 gate).
5. **Export per tool** — **CGI `.xlsx`** (Substance rows + AI/Runway env-ref
   sheet) and **TwelveLabs `.csv` / `.json`** (footage + stock retrieval queries).
   Exports build from the store, so they include your edits.

Retrieval queries (TwelveLabs/stock) are written **broad and findable** (content
search); generative prompts (Substance AI prompt, cg_env) stay richly specific.
Served at `/`; the raw API is at `/docs`.

## Run the service (API only)

```bash
uvicorn director_agent.api.app:app --reload
# POST /run with {script, lane, dials?, styling, season}; or POST /run/cell for one cell
```

## Tests

```bash
pytest                              # schema, fixtures, substance xlsx, runner, director plumbing, invariants
```

The director-plumbing and runner tests use a fake Anthropic client, so the suite
runs fully offline (no API key needed). Only `run_demo.py` makes live calls.

---

## Deploy (hosted) — persistent container

The app is stateful (working project + draft store on disk), takes deck uploads,
and makes long live calls — so it's hosted as a **persistent container**, not
serverless. The `Dockerfile` runs the current code as-is; `render.yaml` is a
one-service Render blueprint (Railway/Fly work the same way with the Dockerfile).

**Steps (Render):**
1. Push to GitHub; in Render: New → Blueprint → pick the repo (uses `render.yaml`).
2. Set secrets in the dashboard: `ANTHROPIC_API_KEY` and `APP_PASSWORD` (the shared
   password to enter the app).
3. Deploy. The blueprint mounts a 1 GB disk at `/data`, where `draftstore.sqlite`
   and `project.json` persist across restarts.

**Access:** when `APP_PASSWORD` is set, the whole app is behind an HTTP Basic gate
(any username, that password); `/health` stays open for the platform health check.
Leave `APP_PASSWORD` unset locally for no auth.

**Hosting notes / current limits:**
- **Single shared workspace** — one working project + draft store for everyone
  (effectively one deck at a time). Per-user workspaces would need the stores scoped
  by login.
- Uploads + long ingest/run calls work on a container (no serverless body-size cap
  or cold-start drops).
- `BG_MODE=fixture` ships the bundled RAM fixtures; flip to `http` when live Brand
  Gravity is wired.

Build/run the container locally:
```bash
docker build -t director-agent .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... -e APP_PASSWORD=secret \
  -v "$PWD/data:/data" director-agent
# open http://localhost:8000/  (enter any username + the password)
```

---

## Deploy to Vercel (API-only)

The app deploys to Vercel as a FastAPI serverless function. Two serverless
constraints are handled: the SQLite draft store is swapped for **Upstash Redis**
(Vercel function FS is read-only/ephemeral), and the Substance xlsx is rebuilt on
the fly via `GET /substance.xlsx` (the in-run `/tmp` copy doesn't persist). The
`/docs` Swagger UI is the shareable surface.

**One-time setup on the Vercel project:**
1. Provision Upstash Redis: dashboard → Storage → Marketplace → Upstash (or
   `vercel install upstash`). It auto-injects the REST URL/token env vars.
2. Set env vars (Production + Preview):
   - `ANTHROPIC_API_KEY` — mark **Sensitive**
   - `BG_MODE=fixture` — read `data/bg_fixtures/`, don't call the (not-yet-live) BG endpoint
   - `DRAFT_STORE_BACKEND=upstash`
   - `SUBSTANCE_OUT_PATH=/tmp/substance_rows.xlsx`
   - Upstash creds: auto-injected. Config accepts either `UPSTASH_REDIS_REST_URL`/
     `UPSTASH_REDIS_REST_TOKEN` or `KV_REST_API_URL`/`KV_REST_API_TOKEN`.
3. Push to `main` → Vercel auto-builds (entrypoint pinned in `pyproject.toml`).

**Verify after deploy:** `GET /health`, open `/docs`, `POST /run` for one lane
(~30s–2min, within the 300s function ceiling), `GET /drafts`, `GET /substance.xlsx`.

**If the build errors `ModuleNotFoundError: No module named 'director_agent'`:**
the builder is running from the repo root — change the `pyproject.toml`
`[tool.vercel] entrypoint` to `src.director_agent.api.app:app`.

> Note: `POST /run` is a synchronous multi-minute request (6 sequential Claude
> calls/lane). It fits the 300s ceiling but a browser/proxy may drop a long idle
> connection — fine for low-traffic manual use via `/docs`. A per-cell endpoint +
> live matrix UI is the upgrade if you want the in-room "watch it fill" demo.

---

## Brand Gravity is a live service — not built here

Brand Gravity is a live, consumer-grade data application (admin GUI at
`bg-admin.donercolle.dev`, retrieval endpoint `/v1/context`). This repo is a
**consumer** of it, not a reimplementation. The agent talks to BG through one
`BGClient` interface with two providers:

- **`fixture`** (default) — serves slices from `data/bg_fixtures/`, authored from
  `BrandGravity_RAM_Store_Compilation_2026-06-08.md`. The RAM buckets are not yet
  connected to live BG, so fixtures stand in for the pitch.
- **`http`** — posts the structured request to `/v1/context` and parses the
  documented response. A thin, interface-complete stub today; flip `BG_MODE=http`
  and supply `BG_BASE_URL` / `BG_API_KEY` when the RAM buckets come online. No
  agent code changes.

Both satisfy the same contract; the director cannot tell which path produced a
response. Slices carry `notes_for_consumers` addressing the director directly —
the director composes by following those notes, not by interpreting raw content.

### Reconciliation of the spec (§4 / §9 deltas)

The cell-contracts spec (`_ref/BrandGravity_CellContracts_DirectorSpec_2026-06-08.md`)
predates this build. Two clarifications it should reflect:

- **§4** documents the BG request/response *contract* (which this repo implements
  on the agent side). It is **not** a build spec for Brand Gravity — BG already
  exists. Treated here as the client contract only.
- **§9** "Repo scaffold" is realized as this single service. There is no Brand
  Gravity to build; the only BG-side artifact is the fixture data that proxies the
  live store until the RAM buckets connect.

The dated `_ref` spec is left unmodified as the source artifact; this section is
the authoritative reconciliation.

---

## Layout

```
data/
  scripts/    map_retail_ram_test_15_south.json   # tagged South:15 script
  dials/      year_end_demo.json                  # 0.75 / 0.6 / 0.8 / 0.7
  styling/    year_end_demo.json                  # spot-level styling inputs
  bg_fixtures/{brand,great_lakes,southwest,baseline}/*.json
src/director_agent/
  schemas/    bg, cell, script, dials, common      # strict Pydantic (no extra fields)
  bg/         client, fixture_provider, http_provider, cache
  director/   cell_specs, prompt, director          # one Claude call per cell, forced tool-use
  draftstore/ store, local_store, shawn_adapter     # SQLite local store behind an adapter
  pipeline/   runner                                # the scene walk + continuity
  outputs/    substance_excel                        # exact 6-column demo format
  validation.py                                      # brand-rule invariants
  api/app.py                                         # FastAPI surface
scripts/run_demo.py
tests/
```

## Not in scope

Brand Gravity itself; Shawn's real draft system (local store stands in behind the
`DraftStore` adapter); TwelveLabs / Substance / Runway / Odd integrations;
local-tagging-to-77-markets; the social-intelligence agent. All are
downstream/external per the architecture diagram.
