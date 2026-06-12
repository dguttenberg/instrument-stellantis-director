"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Play,
  RotateCcw,
  AlertTriangle,
  Loader2,
  PanelsTopLeft,
  ChevronDown,
} from "lucide-react";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import {
  CELL_TYPES,
  type CellType,
  type Dials,
  type Lane,
  type Project,
  type Recommendations,
  type RunCellResult,
  type Scene,
} from "@/lib/types";
import { AppSidebar } from "./app-sidebar";
import { ReviewDialog } from "./review-dialog";
import {
  cellTypeLabel,
  confidenceMarker,
  directorNote,
  displayFlags,
} from "./helpers";
import { TechniqueBadge } from "./technique-badge";
import { IntelligenceFacets } from "./intelligence-facets";

const DEFAULT_REGIONS = ["great_lakes", "southwest"];
const EMPTY_REC: Recommendations = { recommendations: {}, tool_label: {} };

type ResultMap = Record<string, Record<number, RunCellResult>>;

export function DirectorApp() {
  const [lanes, setLanes] = useState<Lane[]>([]);
  const [rec, setRec] = useState<Recommendations>(EMPTY_REC);
  const [project, setProject] = useState<Project | null>(null);
  const [dials, setDials] = useState<Dials>({
    styling_carry_over: 0.5,
    regional_specificity: 0.5,
    voice_adherence: 0.5,
    narrative_continuity: 0.5,
  });
  const [shownRegions, setShownRegions] = useState<string[]>([]);
  const [results, setResults] = useState<ResultMap>({});
  const [running, setRunning] = useState<Record<string, boolean>>({});
  const [bulk, setBulk] = useState<{
    active: boolean;
    done: number;
    total: number;
    label: string;
  }>({ active: false, done: 0, total: 0, label: "" });
  const [ingestStatus, setIngestStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [modal, setModal] = useState<{ lane: string; idx: number } | null>(null);

  // Initial load
  useEffect(() => {
    (async () => {
      try {
        const [ls, rc, pj] = await Promise.all([
          api.lanes(),
          api.recommendations(),
          api.project(),
        ]);
        setLanes(ls);
        setRec(rc);
        setProject(pj);
        setDials(pj.dials);
        setShownRegions(
          DEFAULT_REGIONS.filter((k) => ls.some((l) => l.key === k)),
        );
        if (pj.script.scenes.length > 0) setSidebarOpen(false);
      } catch (e) {
        setIngestStatus(`Could not reach the Director API: ${(e as Error).message}`);
      }
    })();
  }, []);

  const laneOf = useCallback(
    (key: string) => lanes.find((l) => l.key === key) ?? { key, label: key, abbrev: key },
    [lanes],
  );

  const shownLanes = useMemo(
    () => lanes.filter((l) => shownRegions.includes(l.key)),
    [lanes, shownRegions],
  );

  const resultsCount = useMemo(
    () =>
      Object.values(results).reduce(
        (n, byScene) => n + Object.keys(byScene).length,
        0,
      ),
    [results],
  );

  const scenes = project?.script.scenes ?? [];
  const currentStep = scenes.length === 0 ? 0 : resultsCount === 0 ? 2 : 3;

  // --- actions ---

  const loadSample = useCallback(async () => {
    setBusy(true);
    setIngestStatus("Loading sample…");
    try {
      const pj = await api.loadSample();
      setProject(pj);
      setDials(pj.dials);
      setResults({});
      setSidebarOpen(false);
      setIngestStatus(`Sample loaded — ${pj.script.scenes.length} scenes.`);
    } catch (e) {
      setIngestStatus(`Could not load sample: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }, []);

  const upload = useCallback(async (file: File) => {
    setBusy(true);
    setIngestStatus(`Extracting "${file.name}"…`);
    try {
      const pj = await api.ingest(file);
      setProject(pj);
      setDials(pj.dials);
      setResults({});
      setSidebarOpen(false);
      setIngestStatus(`${pj.script.scenes.length} scenes extracted — confirm, then run.`);
    } catch (e) {
      setIngestStatus(`Ingest failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }, []);

  const toggleRegion = useCallback((key: string) => {
    setShownRegions((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    );
  }, []);

  const onDialChange = useCallback((key: keyof Dials, value: number) => {
    setDials((prev) => ({ ...prev, [key]: value }));
  }, []);

  const patchScene = useCallback(
    async (sceneIndex: number, patch: Partial<Scene>) => {
      // optimistic local update
      setProject((prev) =>
        prev
          ? {
              ...prev,
              script: {
                ...prev.script,
                scenes: prev.script.scenes.map((s) =>
                  s.scene_index === sceneIndex ? { ...s, ...patch } : s,
                ),
              },
            }
          : prev,
      );
      try {
        await api.patchScene(sceneIndex, patch);
      } catch (e) {
        setIngestStatus(`Save failed: ${(e as Error).message}`);
      }
    },
    [],
  );

  // Low-level: run one cell with an explicit prior envelope. Returns the result
  // (or null on failure) so callers can thread continuity in a loop.
  const executeCell = useCallback(
    async (
      lane: string,
      sceneIndex: number,
      prior: unknown,
    ): Promise<RunCellResult | null> => {
      const key = `${lane}:${sceneIndex}`;
      setRunning((r) => ({ ...r, [key]: true }));
      try {
        // Retry transient failures (e.g. brief write-lock contention when many regions
        // run at once on the hosted instance) so a cell is never silently dropped.
        const ATTEMPTS = 3;
        let lastErr: unknown;
        for (let attempt = 0; attempt < ATTEMPTS; attempt++) {
          try {
            const data = await api.runCell({
              lane,
              scene_index: sceneIndex,
              dials,
              prior_cell_resolved: prior,
            });
            setResults((prev) => ({
              ...prev,
              [lane]: { ...(prev[lane] ?? {}), [sceneIndex]: data },
            }));
            return data;
          } catch (e) {
            lastErr = e;
            if (attempt < ATTEMPTS - 1) {
              await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
            }
          }
        }
        setIngestStatus(
          `Scene ${sceneIndex} (${lane}) failed after retries: ${(lastErr as Error)?.message ?? "error"}`,
        );
        return null;
      } finally {
        setRunning((r) => {
          const next = { ...r };
          delete next[key];
          return next;
        });
      }
    },
    [dials],
  );

  // Single cell (button): prior = the previous shown scene's result, if any.
  const runCell = useCallback(
    (lane: string, sceneIndex: number) => {
      const ordered = scenes.map((s) => s.scene_index);
      const pos = ordered.indexOf(sceneIndex);
      const prior =
        pos > 0 ? results[lane]?.[ordered[pos - 1]]?.envelope ?? null : null;
      return executeCell(lane, sceneIndex, prior);
    },
    [executeCell, results, scenes],
  );

  // Run regions SCENE BY SCENE: each scene runs across all selected regions at once,
  // and the next scene only starts once the current row finishes — an orderly fill,
  // not regions racing independently. Continuity threads per region (scene N sees its
  // own scene N-1, which is complete before scene N begins).
  const runRegions = useCallback(
    async (laneKeys: string[], label: string) => {
      if (!scenes.length || !laneKeys.length) return;
      setBulk({ active: true, done: 0, total: laneKeys.length * scenes.length, label });
      const prior: Record<string, unknown> = {};
      try {
        for (const s of scenes) {
          await Promise.all(
            laneKeys.map(async (lane) => {
              const data = await executeCell(lane, s.scene_index, prior[lane] ?? null);
              prior[lane] = data?.envelope ?? prior[lane] ?? null;
              setBulk((b) => ({ ...b, done: b.done + 1 }));
            }),
          );
        }
      } finally {
        setBulk({ active: false, done: 0, total: 0, label: "" });
      }
    },
    [executeCell, scenes],
  );

  const modalResult = modal ? results[modal.lane]?.[modal.idx] ?? null : null;
  const modalScene = modal
    ? scenes.find((s) => s.scene_index === modal.idx) ?? null
    : null;

  return (
    <SidebarProvider open={sidebarOpen} onOpenChange={setSidebarOpen}>
      <AppSidebar
        project={project}
        lanes={lanes}
        shownRegions={shownRegions}
        onToggleRegion={toggleRegion}
        dials={dials}
        onDialChange={onDialChange}
        onLoadSample={loadSample}
        onUpload={upload}
        ingestStatus={ingestStatus}
        busy={busy}
        resultsCount={resultsCount}
        currentStep={currentStep}
      />

      <SidebarInset>
        {/* Pinned header — logo lives here so it is never clipped by the sidebar collapse */}
        <header className="bg-background/80 sticky top-0 z-10 flex items-center gap-3 border-b px-5 py-3 backdrop-blur">
          <SidebarTrigger />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/brand/DCP_Logos_DCP_Logo_2C_Violet-Midnight-Blue.svg"
            alt="DonerColle Partners"
            className="h-5 w-auto"
          />
          <div className="bg-border h-6 w-px" />
          <div>
            <div className="text-aurora-violet text-[11px] font-semibold uppercase tracking-[0.14em]">
              RAM · Tier 2 Retail · Director
            </div>
            <h1
              className="text-foreground text-lg leading-tight tracking-tight"
              style={{ fontFamily: "Magnetik, sans-serif", fontWeight: 800 }}
            >
              Stellantis Regional Director.
            </h1>
          </div>

          {/* Run controls — all selected regions, or a single region */}
          {scenes.length > 0 && (
            <div className="ml-auto flex items-center gap-2">
              {bulk.active && (
                <span
                  className="text-muted-foreground flex items-center gap-1.5 text-xs"
                  aria-live="polite"
                >
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {bulk.label} · {bulk.done}/{bulk.total}
                </span>
              )}
              <Button
                size="sm"
                disabled={bulk.active || shownLanes.length === 0}
                onClick={() =>
                  runRegions(
                    shownLanes.map((l) => l.key),
                    "Running all regions",
                  )
                }
              >
                <Play className="h-4 w-4" />
                Run all regions
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={bulk.active || shownLanes.length === 0}
                    aria-label="Run a single region"
                  >
                    Run region
                    <ChevronDown className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-52">
                  <DropdownMenuLabel>Run one region</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {shownLanes.map((l) => (
                    <DropdownMenuItem
                      key={l.key}
                      onClick={() => runRegions([l.key], `Running ${l.label}`)}
                    >
                      {l.label}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )}
        </header>

        <main className="ds-aurora-bg flex-1 px-5 py-6">
          {scenes.length === 0 ? (
            <EmptyState onLoadSample={loadSample} busy={busy} />
          ) : (
            <div className="mx-auto flex max-w-6xl flex-col gap-7">
              {scenes.map((scene) => (
                <SceneGroup
                  key={scene.scene_index}
                  scene={scene}
                  shownLanes={shownLanes}
                  rec={rec}
                  results={results}
                  running={running}
                  onPatchScene={patchScene}
                  onRun={runCell}
                  onOpen={(lane, idx) => setModal({ lane, idx })}
                  laneLabel={(k) => laneOf(k).label}
                />
              ))}
            </div>
          )}
        </main>
      </SidebarInset>

      <ReviewDialog
        open={modal !== null}
        onOpenChange={(o) => !o && setModal(null)}
        result={modalResult}
        scene={modalScene}
        laneLabel={modal ? laneOf(modal.lane).label : ""}
        rec={rec}
        onSaved={(r) => {
          if (modal)
            setResults((prev) => ({
              ...prev,
              [modal.lane]: { ...(prev[modal.lane] ?? {}), [modal.idx]: r },
            }));
        }}
        onRerun={() => {
          if (modal) runCell(modal.lane, modal.idx);
        }}
      />
    </SidebarProvider>
  );
}

// ---- Empty state ----
function EmptyState({
  onLoadSample,
  busy,
}: {
  onLoadSample: () => void;
  busy: boolean;
}) {
  return (
    <div className="mx-auto mt-16 flex max-w-md flex-col items-center gap-3 text-center">
      <PanelsTopLeft className="text-muted-foreground/50 h-9 w-9" />
      <h2
        className="text-xl tracking-tight"
        style={{ fontFamily: "Magnetik, sans-serif", fontWeight: 700 }}
      >
        Upload the deck. Build the matrix.
      </h2>
      <p className="text-muted-foreground text-sm">
        Drop a .pdf or .pptx storyboard in the sidebar to extract the scene
        matrix — or load the bundled sample.
      </p>
      <Button onClick={onLoadSample} disabled={busy}>
        Load sample
      </Button>
    </div>
  );
}

// ---- Scene group: full-width header + its region cards beneath ----
function SceneGroup({
  scene,
  shownLanes,
  rec,
  results,
  running,
  onPatchScene,
  onRun,
  onOpen,
  laneLabel,
}: {
  scene: Scene;
  shownLanes: Lane[];
  rec: Recommendations;
  results: ResultMap;
  running: Record<string, boolean>;
  onPatchScene: (idx: number, patch: Partial<Scene>) => void;
  onRun: (lane: string, idx: number) => void;
  onOpen: (lane: string, idx: number) => void;
  laneLabel: (key: string) => string;
}) {
  return (
    <section className="flex flex-col gap-3">
      {/* Scene header */}
      <div className="bg-accent/40 rounded-xl border p-4">
        <div className="flex flex-wrap items-center gap-3">
          <span
            className="text-aurora-violet text-2xl leading-none"
            style={{ fontFamily: "Magnetik, sans-serif", fontWeight: 900 }}
          >
            {scene.scene_index}
          </span>
          <TechniqueBadge cellType={scene.cell_type} iconOnly />
          <Select
            value={scene.cell_type}
            onValueChange={(v) =>
              onPatchScene(scene.scene_index, { cell_type: v as CellType })
            }
          >
            <SelectTrigger size="sm" className="w-[19rem] max-w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {CELL_TYPES.map((ct) => (
                <SelectItem key={ct} value={ct}>
                  {cellTypeLabel(ct)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Textarea
          defaultValue={scene.scene_description}
          rows={2}
          className="mt-3 text-sm"
          onBlur={(e) =>
            onPatchScene(scene.scene_index, { scene_description: e.target.value })
          }
        />
        {/* Super — the on-screen copy, given real emphasis */}
        <div className="mt-3">
          <label className="text-muted-foreground mb-1 block text-[10px] font-semibold uppercase tracking-[0.12em]">
            Super · on-screen copy
          </label>
          <Input
            defaultValue={scene.super_intent ?? ""}
            placeholder="No on-screen copy for this scene"
            className="h-10 text-base font-medium"
            onBlur={(e) =>
              onPatchScene(scene.scene_index, {
                super_intent: e.target.value,
                super_called: !!e.target.value,
              })
            }
          />
        </div>
      </div>

      {/* Region cards */}
      <div className="text-muted-foreground pl-1 text-[10px] font-semibold uppercase tracking-[0.12em]">
        Regions
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {shownLanes.length === 0 && (
          <p className="text-muted-foreground text-sm">
            Pick regions in the sidebar.
          </p>
        )}
        {shownLanes.map((lane) => (
          <RegionCard
            key={lane.key}
            laneKey={lane.key}
            laneLabel={laneLabel(lane.key)}
            sceneIndex={scene.scene_index}
            result={results[lane.key]?.[scene.scene_index] ?? null}
            running={!!running[`${lane.key}:${scene.scene_index}`]}
            rec={rec}
            onRun={() => onRun(lane.key, scene.scene_index)}
            onOpen={() => onOpen(lane.key, scene.scene_index)}
          />
        ))}
      </div>
    </section>
  );
}

// ---- Region card (the cell) ----
function RegionCard({
  laneKey,
  laneLabel,
  sceneIndex,
  result,
  running,
  rec,
  onRun,
  onOpen,
}: {
  laneKey: string;
  laneLabel: string;
  sceneIndex: number;
  result: RunCellResult | null;
  running: boolean;
  rec: Recommendations;
  onRun: () => void;
  onOpen: () => void;
}) {
  const env = result?.envelope;
  const marker = result ? confidenceMarker(result.record.review_status) : null;
  const flags = displayFlags(env?.gaps_flagged);
  const note = env ? directorNote(env, rec) : "";
  // Existing footage defaults to reusing the core spot's shot as-is — no regionalized
  // intelligence on the card; a footage-intelligence alternative is offered on open.
  const isExisting = env?.cell_type === "existing_running_footage";

  return (
    <div
      className={cn(
        "bg-card flex min-h-[112px] flex-col gap-2 rounded-xl border p-3.5 shadow-sm transition-all",
        result &&
          "hover:border-aurora-green-deep/50 cursor-pointer hover:-translate-y-0.5",
        running && "border-sky-deep",
      )}
      onClick={() => result && onOpen()}
      role={result ? "button" : undefined}
      tabIndex={result ? 0 : undefined}
      onKeyDown={(e) => {
        if (result && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onOpen();
        }
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold">{laneLabel}</span>
        <Button
          size="sm"
          variant={result ? "outline" : "default"}
          className="h-7 px-2.5 text-xs"
          disabled={running}
          onClick={(e) => {
            e.stopPropagation();
            onRun();
          }}
        >
          {running ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : result ? (
            <RotateCcw className="h-3.5 w-3.5" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          {running ? "Directing" : result ? "Re-run" : "Run"}
        </Button>
      </div>

      {!result && !running && (
        <span className="text-muted-foreground text-xs">Not run yet</span>
      )}

      {running && <span className="text-sky-deep text-xs">Directing…</span>}

      {result && env && marker && (
        <>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
            <TechniqueBadge cellType={env.cell_type} />
            <span className="text-muted-foreground inline-flex items-center gap-1">
              <span className={cn("leading-none", marker.dot)}>●</span>
              {marker.label}
            </span>
          </div>
          {isExisting ? (
            <>
              <p className="text-foreground text-xs">
                Existing footage used — reused from the core spot.
              </p>
              <p className="text-sky-deep text-[11px]">
                Regional alternative suggested — open to view
              </p>
            </>
          ) : (
            <>
              {/* The three intelligences whose intersection drives this cell */}
              <IntelligenceFacets intelligence={env.intelligence} />
              {/* Synthesis — shown in full (no truncation) */}
              {note && (
                <p className="text-muted-foreground border-border border-l-2 pl-2 text-xs leading-snug">
                  {note}
                </p>
              )}
            </>
          )}
          {flags.length > 0 && (
            <span className="text-ember-deep inline-flex items-center gap-1 pt-1 text-[11px]">
              <AlertTriangle className="h-3 w-3" />
              {flags.length} flag{flags.length > 1 ? "s" : ""}
            </span>
          )}
        </>
      )}
    </div>
  );
}
