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

---

# Front-end rebuild on DCP Design System (React/Next/shadcn) — 2026-06-11

Acting on the UX team's review + wireframe in
`~/Downloads/g. Director Agent (Doug G)-selected/UX asessement and action plan/`.

## Decisions locked
- **Stack:** React/Next.js 16 + React 19 + Tailwind v4 + shadcn/ui (DS Track B1). DS Claude
  Skill + assets pulled to `/tmp/dcp-ds/skill/dcp-design/` (tokens, Magnetik OTFs, logos, refs).
- **Scope this pass:** FRONT-END ONLY. Backend `src/director_agent/` untouched. Phase 0 ingest deferred.
- **Integration:** Next `rewrites` proxy `/api/be/*` → `http://localhost:8000/*`. No CORS, no backend edits, auth gate off locally.
- **Status tension (Phase 0 deferred):** do NOT fabricate "◆ inferred". Render REAL `confidence`/`review_status`
  as a calm, non-gating per-card marker; drop the Approve gate. Literal "inferred" lands with Phase 0.
- **New app in sibling `web/`.** Existing FastAPI-served `static/index.html` untouched until parity (working fallback).

## DS ground truth (corrects earlier inferred guesses)
- Light-mode primary CTA = **Sky Blue**; Aurora Green = active/positive; Sunset Ember = destructive.
- Headings = **Magnetik** via inline `style={{fontFamily:'Magnetik,sans-serif',fontWeight:N}}`. Body/UI = **Geist Mono** (`font-mono`). No italics, no `font-magnetik` class.
- Brand token classes only (`bg-aurora-green/15`); cards `rounded-xl`=28px; inputs `rounded-md`=14px, focus ring aurora-violet.
- Eyebrow: aurora-violet uppercase tracking-[0.14em] 13px semibold. Sentence case, headline ends in a period, no emoji except `●`. lucide-react. radix-ui v1.4 unified import.

## THIS SESSION — vertical slice (RUNS end-to-end ✓)
- [x] 1. Scaffold `web/` (Next 16.2.9 + TS + Tailwind v4); DS `globals.css` (real tokens) + Magnetik @font-face + 18 OTFs + DCP logos.
- [x] 2. `shadcn init` (Nova preset, radix base) + added button card dialog badge input select textarea tooltip sidebar sonner skeleton label separator scroll-area slider dropdown-menu. (form/zod deferred — used controlled inputs.)
- [x] 3. `next.config` rewrites `/api/be/:path*`→`:8000` + turbopack.root; `lib/api.ts` client + `lib/types.ts` (exact backend shapes).
- [x] 4. App shell: SidebarProvider (controlled, auto-collapse on load) + collapsible AppSidebar (branding, Flow step tracker, deck upload, dials, regions, export) + SidebarInset.
- [x] 5. Scene-grouped main: each scene = full-width header (index + technique select + trim/super + description); region cards tile beneath.
- [x] 6. Wire reads (/lanes, /recommendations, /project) on mount; **Load sample** + project render the matrix.
- [x] 7. Per-card **/run/cell** (Run + Re-run, overwrite, continuity threaded); outputs as Badges; calm confidence marker (not a gate).
- [x] 8. Reasoning-first review **Dialog**: "Why the Director chose this" (headline + provenance + flags) on top, editable outputs below, Save / Save & re-run.
- [x] 9. Launched `next dev` + uvicorn; Playwright-verified landing, expanded sidebar, real run, open modal — all clean in light mode.

## Deferred this session (named, not silently dropped)
- Toast on save, export guard+count, dial tooltips/staleness, per-cell inline errors + continue-on-error,
  run-concurrency progress, reset/upload-progress, responsive pass, friendly-label glossary.
- Phase 0 ingest integrity (backend): input-type detection + true inferred markers + field validation.
- Production deploy (default: static-export served by FastAPI = one Render service; or split Next-on-Vercel→Render API). Flagged, deferred.

### Polish round 3 (2026-06-11) — AA + run controls + director's notes
- **AA (light mode):** bright brand hues fail contrast as foreground on white. Added deep tokens
  to globals.css @theme — `aurora-green-deep #0b6f42`, `sky-deep #205691`, `ember-deep #b84535`
  (all >=4.5:1). Swapped every green/sky/ember used as text/icon/dot/border (confidence dots,
  region chips, step checks, dial LIVE, provenance, out-type, flags, running labels, card hover/
  running borders). Bright hues now only fill buttons/backgrounds. Cards keyboard-focusable
  (role/tabIndex/Enter-Space → open modal).
- **Three run levels:** header "Run all regions" (all selected) + "Run region ▾" dropdown
  (one region, all scenes) + existing per-card Run/Re-run (single cell). Sequential with
  continuity threading; header shows live progress (done/total, aria-live). Refactored runCell →
  executeCell(prior) + runRegions(laneKeys,label).
- **Director's note on run cells:** `directorNote()` composes a brief synopsis from the primary
  output (cg prompt / TL query / super / substance notes / stock desc / gap reason), line-clamped
  to 3 lines on the card — a real preview of what you'll see before clicking in.
- VERIFIED: tsc clean, prod static build passes, Playwright confirmed AA tones, director note on
  card, run-all progress, sidebar AA. NOTE: a *director-written* synopsis (vs. composed-from-output)
  would need a small backend field (Phase 1.3) — deferred.

### Polish round 4 (2026-06-11) — parallel runs, find-vs-create, declutter
- **Run all = simultaneous:** runRegions now `Promise.all`s the regions (parallel); scenes stay
  sequential WITHIN a region for continuity. Verified 2 cells "Directing…" at once.
- **Find vs create distinction (the key ask):** `toolMode()` maps tool → mode. twelvelabs =
  **"Footage intelligence"** (find existing footage; sky tint + Search icon); cgai =
  **"AI generation"** (create new with AI; violet tint + Sparkles icon). Replaces the old
  "TwelveLabs"/"CG·AI" tags on cards + modal.
- **Removed output-type chips** from cards (cg env prompt / super text / TL filters / substance —
  "always the same, don't help"). Card now: mode badge + confidence marker + director's note + flags.
- Friendly output labels in the modal edit blocks (`outputLabel`): Footage search, CG/AI
  environment, Stock search, Substance variant, On-screen copy, Gap flag.
- VERIFIED: tsc clean, prod static build passes, Playwright confirmed parallel run + both mode badges.

### Polish round 5 (2026-06-11) — four techniques, not a binary
- Replaced the 2-way find/create (toolMode) with a 4-way **technique by cell_type** (the script's
  per-scene tagging): existing_running_footage = **Footage intelligence** (reuse/keep the shot,
  sky + Search); stock = **Stock footage** (neutral + Film); regionalized_running_w_cgi_ai =
  **CGI/AI hybrid** (violet + Blend); regionalized_ai_scenes = **Full CG/AI** (green + Sparkles).
- New `<TechniqueBadge>` (icon + AA color + label) used on run cards + modal; icon-only chip in
  each scene header beside the dropdown. `cellTypeLabel` now derives from `techniqueMode`, so the
  dropdown / modal / badges all read the same technique name.
- VERIFIED: tsc clean, prod static build passes, all four labels render (Playwright).
- Wording is easy to tweak (e.g. "Stock footage"→"Stock generation", "Full CG/AI"→"AI generation").

### Polish round 6 (2026-06-11) — FOLLOW THE SCRIPT's techniques
- Read `_ref/MAP Retail Ram Test.pdf` "Process" page. The four techniques are DEFINED BY THE
  SCRIPT (human tags shot style per scene; AI reacts). Replaced my invented labels with the
  script's verbatim names + color coding + process notes (as tooltips):
  - regionalized_running_w_cgi_ai → "Regionalized running footage w/CGI+AI" (cyan/sky, Blend)
  - stock → "Stock" (green, Library)
  - existing_running_footage → "Existing Running Footage" (magenta→violet, Film) = keep the shot
  - regionalized_ai_scenes → "Regionalized AI scenes" (amber→ember, Sparkles)
- cellTypeLabel + TechniqueBadge + dropdown all read the script names; badge rounded-md so the
  long names wrap cleanly. Widened the scene-header dropdown. Tooltips carry the script's process.
- VERIFIED: tsc clean, prod build passes, all four script names render, card badge wraps cleanly.

### Polish round 7 (2026-06-11) — director synopsis (brand×location×audience)
- BACKEND change (approved): director now emits a one-sentence `synopsis` weaving AUDIENCE
  (audience_resonance) + LOCATION (environmental_context) + BRAND voice (tone/creative_intent) —
  not the bare region name. Frame: "[audience truth] · [location texture] · [brand voice]".
  - `_DirectorEmission.synopsis` (optional default "" so the mocked-director tests still validate;
    prompt + schema description drive the model to fill it reliably — confirmed on live runs).
  - `CellOutputEnvelope.synopsis`; `_finalize` passes it through; prompt rule added.
- FE: `Envelope.synopsis`; `directorNote()` prefers it, falls back to the composed excerpt for
  cells run before the field existed. Shown as the matrix card descriptor.
- VERIFIED live (opus-4-8): hybrid/stock/existing all produce rich synopses, e.g. "For Southwest
  Proud Workhorses, a HEMI badge glints in sharp winter desert light…". 51 backend tests pass,
  tsc clean, static build passes, card shows the synopsis.

### Polish round 8 (2026-06-11) — show the brand×location×audience intersection
- Chosen viz (Doug): three labeled facets + synthesis on the matrix card.
- BACKEND: director now also emits `intelligence {brand, location, audience}` (each <=6 words)
  alongside the synopsis — `SceneIntelligence` model on the envelope + `_DirectorEmission`
  (optional defaults so mocked tests still validate) + prompt rule. Verified live: e.g. brand
  "HEMI V8 return, capability-led" · location "Great Lakes winter two-lanes, snowbanks" ·
  audience "Proud Workhorses".
- FE: `<IntelligenceFacets>` (color-keyed: Brand=violet, Location=sky, Audience=green) on the
  card (above the synopsis) and in the modal's "Why" block. Synopsis now shows IN FULL (removed
  the line-clamp) per Doug — not cut off; the modal scrolls for the full detail.
- VERIFIED: 51 backend tests pass, tsc clean, static build passes, card + modal render the three
  facets + full synopsis.

### Polish round 9 (2026-06-11)
- Flags: `displayFlags()` hides engineering diagnostics ("director emitted disallowed output
  type … dropped") from the creative UI and strips the "invariant:" prefix; card + modal use it.
- Synopsis: prompt updated to NOT lead with "For [audience]…" — it's a direct visual description
  (location texture + brand voice); audience is shown as its own facet. Verified live.
- Existing Running Footage = "keep the shot": card now just says "Existing footage used — reused
  from the core spot" (no BG facets/synopsis), with a "Regional alternative suggested — open to
  view" cue. The modal frames it as Default (existing) + a "Suggested regional alternative ·
  Footage intelligence" callout containing the brand/location/audience facets + synopsis, with the
  editable footage-search query below. (Front-end gating by cell_type; no backend change.)
- VERIFIED: 51 tests pass, tsc clean, static build passes, card + modal confirmed via Playwright.

### Polish round 10 (2026-06-11) — fix run-all fill order
- Regression from round 4: "Run all" ran each REGION in parallel with its scenes going down
  independently → regions raced/desynced ("random, 4 at a time, no order").
- Fixed: `runRegions` is now SCENE-MAJOR — outer loop scenes (sequential), inner `Promise.all`
  over the selected regions. Each scene runs across all regions at once; the next scene starts
  only when the row finishes. Continuity threads per region via a local `prior` map (scene N-1
  is complete before scene N). Verified: 4 regions all "Directing…" on scene 1 together, scene 2
  waiting; orderly row-by-row fill.

## Review (front-end rebuild)
- WORKING: new DCP-DS front end in `web/` (Next 16 + React 19 + Tailwind v4 + shadcn/radix-ui),
  proxying the untouched FastAPI backend via `/api/be/*` rewrites. Run: backend `uvicorn …:8000`
  + `cd web && npm run dev` → http://localhost:3000. Verified end-to-end with a live opus-4-8 run.
- Faithful to the wireframe: collapsible sidebar (all setup) auto-collapsing to a rail once a
  project loads; scene-grouped main (scene header + region cards beneath). Light mode, Magnetik
  headings, Geist Mono body, Sky-Blue primary, brand token classes (no hex).
- Followed the sequencing rule: did NOT fabricate "◆ inferred" (no Phase 0). Surfaced the real
  `review_status` as a calm confidence marker; dropped the Approve gate.
- DEFERRED (next passes): toast on save, export guard wired to live count edge-cases, dial
  tooltips/staleness, per-cell inline errors + continue-on-error, run-all-region + progress,
  reset/upload-progress, full RHF/zod forms, responsive QA, friendly-label glossary.
- DEFERRED (backend): Phase 0 ingest integrity (input-type detection, true inferred markers,
  field validation) — then flip the marker to literal "inferred" and remove status entirely.
- DEFERRED (decision): production deploy. Default = static-export `web/` served by FastAPI (one
  Render service) OR split Next-on-Vercel w/ rewrites→Render API. Dev uses the rewrite proxy.
- Old FastAPI-served `static/index.html` left intact as a working fallback until parity.

### Polish round 1 (2026-06-11, post-review)
- Fixed hydration console error: added `suppressHydrationWarning` to `<html>` (was a browser
  extension injecting `data-scribe-recorder-ready` on <html> before hydration — benign).
- Moved DCP logo into the pinned top header (was clipping in the collapsing sidebar header,
  which is now just a "Setup" label). Logo: `public/brand/DCP_Logos_DCP_Logo_2C_Violet-Midnight-Blue.svg`.
- Added a "Scene N · what you're reviewing" block to the top of the review modal (scene
  description + vehicle/trim/super) so the concept has context; friendly subtitle (Scene N · technique).

### Polish round 2 (2026-06-11)
- Removed the cryptic unlabeled trim/SKU (D28H91) field from the scene header; super copy is now
  a labeled, full-width, readable field. Super also gets an emphasized callout in the review modal.

### PRODUCTION DEPLOY wired (2026-06-11) — single Render service, static export
- Root cause the new UI wasn't showing live: Render only built/served the FastAPI backend
  (`static/index.html`); the `web/` Next app was never built or served.
- Fix (chosen: one Render service): two-stage Dockerfile — node stage runs `STATIC_EXPORT=1
  npm run build` → `web/out`; python stage `COPY --from=web /web/out /app/web/out`. FastAPI
  serves it (`WEB_DIST`): `GET /` returns the SPA index, a `StaticFiles` mount (registered last)
  serves /_next, /brand, /fonts; all API routes match first. Same origin → no CORS; APP_PASSWORD
  gate covers SPA + API together (browser caches Basic creds, re-sends on same-origin fetches).
- API base: `web/lib/api.ts` BASE = `NEXT_PUBLIC_API_BASE ?? ""`. Dev sets `/api/be` via
  `web/.env.development` (un-ignored) + Next rewrites; prod build leaves it unset → same-origin.
- `next.config.ts`: STATIC_EXPORT=1 → `output:"export"` + drops rewrites (export ignores them).
- `.dockerignore`: excludes web/node_modules, web/.next, web/out, index.dark-backup.html.
- VERIFIED LOCALLY (= Docker behavior): `STATIC_EXPORT=1 npm run build` → web/out; uvicorn serves
  `/` (SPA), `/lanes`, `/_next/*`, `/brand/*` all 200 same-origin; Playwright: SPA renders + loads
  data, zero console errors. Dev (:3000 proxy) still works.
- TO SHIP: commit + push to main (Render auto-redeploys). No Render env/config changes needed
  (render.yaml unchanged; APP_PASSWORD/ANTHROPIC_API_KEY already set). First post-deploy hit may
  cold-start 500 briefly (Starter tier) — that's the known cold-start, not a bug.
