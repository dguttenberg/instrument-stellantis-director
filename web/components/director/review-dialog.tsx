"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TechniqueBadge } from "./technique-badge";
import { IntelligenceFacets } from "./intelligence-facets";
import { api } from "@/lib/api";
import type {
  CellOutput,
  Confidence,
  Recommendations,
  RunCellResult,
  Scene,
} from "@/lib/types";
import {
  cellTypeLabel,
  displayFlags,
  outputLabel,
  sortOutputs,
} from "./helpers";

interface ReviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: RunCellResult | null;
  scene: Scene | null;
  laneLabel: string;
  rec: Recommendations;
  onSaved: (r: RunCellResult) => void;
  onRerun: () => void;
}

const csv = (s: string) =>
  s
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);

export function ReviewDialog({
  open,
  onOpenChange,
  result,
  scene,
  laneLabel,
  rec,
  onSaved,
  onRerun,
}: ReviewDialogProps) {
  const [outputs, setOutputs] = useState<CellOutput[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (result) {
      setOutputs(
        sortOutputs(result.envelope.outputs, result.envelope.cell_type, rec),
      );
    }
  }, [result, rec]);

  if (!result) return null;
  const env = result.envelope;
  const r = rec.recommendations[env.cell_type] ?? {};

  function patch(i: number, next: Partial<CellOutput>) {
    setOutputs((prev) =>
      prev.map((o, idx) => (idx === i ? ({ ...o, ...next } as CellOutput) : o)),
    );
  }

  async function save(thenRerun: boolean) {
    setSaving(true);
    try {
      const record = await api.editDraft(env.cell_id, outputs, env.gaps_flagged);
      onSaved({ envelope: record.envelope, record });
      if (thenRerun) onRerun();
    } catch (e) {
      // surfaced by the caller's toast in a later pass; keep inline for now
      alert(`Save failed: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[88vh] gap-0 overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle
            className="text-xl tracking-tight"
            style={{ fontFamily: "Magnetik, sans-serif", fontWeight: 700 }}
          >
            {r.headline ?? cellTypeLabel(env.cell_type)}
          </DialogTitle>
          <DialogDescription>
            {laneLabel} · Scene {scene?.scene_index ?? ""} ·{" "}
            {cellTypeLabel(env.cell_type)}
          </DialogDescription>
        </DialogHeader>

        {/* What you're reviewing — the actual scene, so the concept has context */}
        {scene && (
          <section className="bg-muted/50 mt-3 rounded-lg border p-4">
            <div className="text-muted-foreground text-[11px] font-semibold uppercase tracking-[0.12em]">
              Scene {scene.scene_index} · what you&apos;re reviewing
            </div>
            <p className="mt-1.5 text-sm leading-relaxed">
              {scene.scene_description || "(no scene description)"}
            </p>
            {scene.super_intent && (
              <div className="border-aurora-violet/40 bg-background mt-3 rounded-md border-l-2 px-3 py-2">
                <span className="text-muted-foreground text-[10px] font-semibold uppercase tracking-[0.12em]">
                  Super · on-screen copy
                </span>
                <p className="text-base font-medium leading-snug">
                  {scene.super_intent}
                </p>
              </div>
            )}
            <div className="text-muted-foreground mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs">
              {scene.nameplate && (
                <span>
                  <span className="opacity-70">Vehicle: </span>
                  {scene.nameplate}
                </span>
              )}
              {scene.trim_intent && (
                <span>
                  <span className="opacity-70">Trim / SKU: </span>
                  {scene.trim_intent}
                </span>
              )}
              <span className="font-mono text-[10px] opacity-60">
                {env.cell_id}
              </span>
            </div>
          </section>
        )}

        {/* Reasoning-first block */}
        <section className="bg-accent/40 mt-2 rounded-lg border p-4">
          <div className="text-aurora-violet text-[11px] font-semibold uppercase tracking-[0.12em]">
            Why the Director chose this
          </div>
          {r.headline && (
            <p className="mt-1.5 text-sm font-medium">
              {r.headline}
              <TechniqueBadge
                cellType={env.cell_type}
                className="ml-2 align-middle"
              />
            </p>
          )}
          {env.cell_type === "existing_running_footage" ? (
            <div className="mt-3 space-y-2">
              <p className="text-foreground text-sm">
                <span className="font-medium">Default — existing footage used.</span>{" "}
                Reuse the core spot&apos;s shot for this scene as-is.
              </p>
              <div className="border-sky-deep/40 bg-sky-blue/10 rounded-md border p-3">
                <div className="text-sky-deep text-[11px] font-semibold uppercase tracking-[0.12em]">
                  Suggested regional alternative · Footage intelligence
                </div>
                <p className="text-muted-foreground mt-1 text-xs leading-relaxed">
                  If you want a region-specific version, footage intelligence can find
                  one — directed by:
                </p>
                <IntelligenceFacets intelligence={env.intelligence} className="mt-2" />
                {env.synopsis && (
                  <p className="text-foreground border-border mt-2 border-l-2 pl-2 text-sm leading-relaxed">
                    {env.synopsis}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <>
              {/* Brand × Location × Audience — the three intelligences, then the synthesis */}
              <IntelligenceFacets intelligence={env.intelligence} className="mt-3" />
              {env.synopsis && (
                <p className="text-foreground border-border mt-2 border-l-2 pl-2 text-sm leading-relaxed">
                  {env.synopsis}
                </p>
              )}
            </>
          )}
          {env.provenance.length > 0 && (
            <p className="text-muted-foreground mt-2 text-xs leading-relaxed">
              <span className="font-semibold">Directed from: </span>
              {env.provenance.map((p, i) => (
                <span key={i}>
                  {i > 0 && " · "}
                  {p.bucket}{" "}
                  <span className="text-aurora-green-deep">
                    ({p.scope_resolved} · {p.confidence})
                  </span>
                </span>
              ))}
            </p>
          )}
          {env.outputs.find(
            (o) => o.type === "substance_row" && o.director_notes,
          ) && (
            <p className="text-muted-foreground mt-2 text-xs leading-relaxed">
              <span className="font-semibold">Notes: </span>
              {
                (
                  env.outputs.find(
                    (o) => o.type === "substance_row",
                  ) as Extract<CellOutput, { type: "substance_row" }>
                ).director_notes
              }
            </p>
          )}
          {displayFlags(env.gaps_flagged).length > 0 && (
            <div className="text-ember-deep mt-2 flex items-start gap-1.5 text-xs">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{displayFlags(env.gaps_flagged).join(" · ")}</span>
            </div>
          )}
        </section>

        {/* Edit fields */}
        <div className="mt-4 mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          Edit
        </div>
        <div className="flex flex-col gap-3">
          {outputs.map((o, i) => (
            <div key={i} className="rounded-lg border p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="text-aurora-green-deep text-xs font-semibold uppercase tracking-wide">
                  {outputLabel(o.type)}
                </span>
                <Select
                  value={o.confidence}
                  onValueChange={(v) =>
                    patch(i, { confidence: v as Confidence })
                  }
                >
                  <SelectTrigger size="sm" className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(["high", "medium", "low"] as Confidence[]).map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <OutputEditor output={o} onPatch={(next) => patch(i, next)} />
            </div>
          ))}
        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => save(false)} disabled={saving}>
            Save edits
          </Button>
          <Button onClick={() => save(true)} disabled={saving}>
            <RotateCcw className="h-4 w-4" /> Save &amp; re-run
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label className="text-muted-foreground text-[10px] uppercase tracking-wide">
        {label}
      </Label>
      {children}
    </div>
  );
}

function OutputEditor({
  output,
  onPatch,
}: {
  output: CellOutput;
  onPatch: (next: Partial<CellOutput>) => void;
}) {
  switch (output.type) {
    case "cg_env_prompt":
      return (
        <div className="flex flex-col gap-2">
          <Field label="For pipeline">
            <Input
              value={output.for_pipeline}
              onChange={(e) => onPatch({ for_pipeline: e.target.value })}
            />
          </Field>
          <Field label="Environment prompt">
            <Textarea
              rows={4}
              value={output.prompt}
              onChange={(e) => onPatch({ prompt: e.target.value })}
            />
          </Field>
        </div>
      );
    case "twelvelabs_query":
      return (
        <div className="flex flex-col gap-2">
          <Field label="Natural-language query (keep broad)">
            <Textarea
              rows={2}
              value={output.query.natural_language}
              onChange={(e) =>
                onPatch({
                  query: { ...output.query, natural_language: e.target.value },
                })
              }
            />
          </Field>
          <Field label="Tags (comma-separated)">
            <Input
              value={(output.query.tags ?? []).join(", ")}
              onChange={(e) =>
                onPatch({ query: { ...output.query, tags: csv(e.target.value) } })
              }
            />
          </Field>
        </div>
      );
    case "stock_search":
      return (
        <div className="flex flex-col gap-2">
          <Field label="Description (keep broad)">
            <Textarea
              rows={2}
              value={output.natural_language_description}
              onChange={(e) =>
                onPatch({ natural_language_description: e.target.value })
              }
            />
          </Field>
          <Field label="Tags (comma-separated)">
            <Input
              value={(output.tags_for_indexed_search ?? []).join(", ")}
              onChange={(e) =>
                onPatch({ tags_for_indexed_search: csv(e.target.value) })
              }
            />
          </Field>
        </div>
      );
    case "super_text":
      return (
        <div className="flex flex-col gap-2">
          <Field label="Super copy">
            <Textarea
              rows={2}
              value={output.content}
              onChange={(e) => onPatch({ content: e.target.value })}
            />
          </Field>
          <Field label="Voice tags (comma-separated)">
            <Input
              value={(output.voice_tags ?? []).join(", ")}
              onChange={(e) => onPatch({ voice_tags: csv(e.target.value) })}
            />
          </Field>
        </div>
      );
    case "substance_row":
      return (
        <div className="grid grid-cols-2 gap-2">
          <Field label="Nameplate">
            <Input
              value={output.row["Nameplate"] ?? ""}
              onChange={(e) =>
                onPatch({ row: { ...output.row, Nameplate: e.target.value } })
              }
            />
          </Field>
          <Field label="Trim">
            <Input
              value={output.row["Specific Trim Request"] ?? ""}
              onChange={(e) =>
                onPatch({
                  row: {
                    ...output.row,
                    "Specific Trim Request": e.target.value,
                  },
                })
              }
            />
          </Field>
          <Field label="Color (HEX)">
            <Input
              value={output.row["Color Preference (HEX)"] ?? ""}
              onChange={(e) =>
                onPatch({
                  row: {
                    ...output.row,
                    "Color Preference (HEX)": e.target.value,
                  },
                })
              }
            />
          </Field>
          <Field label="Camera angles">
            <Input
              value={output.row["Camera Angles"] ?? ""}
              onChange={(e) =>
                onPatch({
                  row: { ...output.row, "Camera Angles": e.target.value },
                })
              }
            />
          </Field>
        </div>
      );
    case "gap_signal":
      return (
        <Field label="Reason">
          <Textarea
            rows={2}
            value={output.reason}
            onChange={(e) => onPatch({ reason: e.target.value })}
          />
        </Field>
      );
    default:
      return null;
  }
}
