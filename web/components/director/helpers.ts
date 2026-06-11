import type {
  CellType,
  CellOutput,
  OutputType,
  Recommendations,
  ReviewStatus,
} from "@/lib/types";

// Friendly, sentence-case technique labels (replaces raw cell_type strings).
const CELL_TYPE_LABELS: Record<CellType, string> = {
  regionalized_running_w_cgi_ai: "Regionalized running + CG/AI",
  stock: "Stock footage",
  existing_running_footage: "Existing running footage",
  regionalized_ai_scenes: "Regionalized AI scenes",
};

export function cellTypeLabel(ct: CellType): string {
  return CELL_TYPE_LABELS[ct] ?? ct.replace(/_/g, " ");
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
      return { label: "High confidence", dot: "text-aurora-green" };
    case "needs_approve":
      return { label: "Review suggested", dot: "text-sky-blue" };
    case "blocked":
      return { label: "Low confidence", dot: "text-sunset-ember" };
  }
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
