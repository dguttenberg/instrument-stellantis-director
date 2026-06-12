import type {
  CellType,
  CellOutput,
  OutputType,
  Recommendations,
  ReviewStatus,
} from "@/lib/types";

// The four techniques are defined BY THE SCRIPT (MAP Retail Ram Test, "Process"
// page). The human tags the shot style per scene; the AI reacts within it. Names,
// process notes, and colors below follow the script verbatim.
export type TechniqueKind = "hybrid" | "stock" | "existing" | "ai";

export interface TechniqueMode {
  label: string;
  kind: TechniqueKind;
  hint: string;
}

const TECHNIQUE: Record<CellType, TechniqueMode> = {
  regionalized_running_w_cgi_ai: {
    label: "Regionalized running footage w/CGI+AI",
    kind: "hybrid",
    hint: "Find existing running footage, render regional environments, and replace the environment in the footage. Cheaper — best for MAPs.",
  },
  stock: {
    label: "Stock",
    kind: "stock",
    hint: "Define the region and source the shot from a stock library (footage intelligence can search stock-house selects).",
  },
  existing_running_footage: {
    label: "Existing Running Footage",
    kind: "existing",
    hint: "Find existing running footage specific to the region — no modification, keep the shot. Best use case for footage intelligence.",
  },
  regionalized_ai_scenes: {
    label: "Regionalized AI scenes",
    kind: "ai",
    hint: "Render regional environments, render the vehicle with Runway, then place the CGI vehicle over the AI. Most custom, most expensive.",
  },
};

export function techniqueMode(ct: CellType): TechniqueMode {
  return TECHNIQUE[ct] ?? { label: ct.replace(/_/g, " "), kind: "generate", hint: "" };
}

export function cellTypeLabel(ct: CellType): string {
  return techniqueMode(ct).label;
}

// Internal validation diagnostics (engineering jargon) that shouldn't surface to a
// creative reviewer as a "flag". Keep real brand/gap flags; tidy their prefixes.
const INTERNAL_FLAG = /(disallowed output type|director emitted|;\s*dropped)/i;
export function displayFlags(gaps: string[] | undefined): string[] {
  return (gaps ?? [])
    .filter((g) => !INTERNAL_FLAG.test(g))
    .map((g) => g.replace(/^invariant:\s*/i, ""));
}

export function humanize(s: string): string {
  return s.replace(/_/g, " ");
}

// --- Output role ordering (primary first, then super, supporting, flags) ---

export type OutputRole = "primary" | "super" | "supporting" | "flag" | "other";

const ROLE_RANK: Record<OutputRole, number> = {
  primary: 0,
  super: 1,
  supporting: 2,
  flag: 3,
  other: 4,
};

export function outputRole(
  ct: CellType,
  type: OutputType,
  rec: Recommendations,
): OutputRole {
  const r = rec.recommendations[ct] ?? {};
  if (type === "super_text") return "super";
  if (type === "gap_signal") return "flag";
  if (type === r.primary_output) return "primary";
  if ((r.supporting ?? []).includes(type)) return "supporting";
  return "other";
}

export function sortOutputs(
  outputs: CellOutput[],
  ct: CellType,
  rec: Recommendations,
): CellOutput[] {
  return [...outputs].sort(
    (a, b) =>
      ROLE_RANK[outputRole(ct, a.type, rec)] -
      ROLE_RANK[outputRole(ct, b.type, rec)],
  );
}

export function toolLabel(rec: Recommendations, tool?: string): string {
  if (!tool) return "";
  return rec.tool_label[tool] ?? tool;
}

const OUTPUT_LABELS: Record<string, string> = {
  twelvelabs_query: "Footage search",
  cg_env_prompt: "CG / AI environment",
  stock_search: "Stock search",
  substance_row: "Substance variant",
  super_text: "On-screen copy",
  gap_signal: "Gap flag",
};
export function outputLabel(t: string): string {
  return OUTPUT_LABELS[t] ?? humanize(t);
}

// --- Calm, non-gating confidence marker (NOT the old approval gate). ---
// Until Phase 0 ships a true "inferred" signal, we surface the real
// review_status as information only.

export interface ConfidenceMarker {
  label: string;
  dot: string; // tailwind text color class for the • dot
}

export function confidenceMarker(status: ReviewStatus): ConfidenceMarker {
  switch (status) {
    case "auto_accept":
      return { label: "High confidence", dot: "text-aurora-green-deep" };
    case "needs_approve":
      return { label: "Review suggested", dot: "text-sky-deep" };
    case "blocked":
      return { label: "Low confidence", dot: "text-ember-deep" };
  }
}

// The primary output for a cell (per the recommendation), falling back to the
// first non-flag output.
export function primaryOutput(
  env: { cell_type: CellType; outputs: CellOutput[] },
  rec: Recommendations,
): CellOutput | undefined {
  const r = rec.recommendations[env.cell_type] ?? {};
  return (
    env.outputs.find((o) => o.type === r.primary_output) ??
    env.outputs.find((o) => o.type !== "gap_signal") ??
    env.outputs[0]
  );
}

function outputText(o: CellOutput): string {
  switch (o.type) {
    case "cg_env_prompt":
      return o.prompt;
    case "twelvelabs_query":
      return o.query.natural_language;
    case "stock_search":
      return o.natural_language_description;
    case "super_text":
      return `On-screen copy: "${o.content}"`;
    case "substance_row":
      return (
        o.director_notes ||
        o.row["AI Image Generator Prompt"] ||
        `Substance variant ${o.row["Color Preference (HEX)"] ?? ""}`.trim()
      );
    case "gap_signal":
      return o.reason;
  }
}

// The director's note shown on the matrix card. Prefer the director-written
// `synopsis` (audience + location + brand voice); fall back to a composed excerpt
// of the primary output for cells run before the synopsis field existed.
export function directorNote(
  env: { cell_type: CellType; outputs: CellOutput[]; synopsis?: string },
  rec: Recommendations,
): string {
  if (env.synopsis && env.synopsis.trim()) return env.synopsis.trim();
  const o = primaryOutput(env, rec);
  return o ? outputText(o).trim() : "";
}

// A short chip label for an individual output.
export function outputChipLabel(o: CellOutput): string {
  if (o.type === "twelvelabs_query") {
    const f = o.query?.filters ?? {};
    const n = Object.values(f).filter((v) => v && v.length).length;
    return "TwelveLabs" + (n ? ` · ${n} filters` : "");
  }
  if (o.type === "substance_row") {
    const hex = o.row["Color Preference (HEX)"] ?? "#000";
    return `Substance ${hex}`;
  }
  return humanize(o.type);
}
