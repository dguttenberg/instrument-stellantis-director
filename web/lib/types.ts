// Types mirror the FastAPI backend (src/director_agent). Field names are exact —
// the backend is untouched this pass, so these must match its JSON verbatim.

export type Confidence = "high" | "medium" | "low";
export type ReviewStatus = "auto_accept" | "needs_approve" | "blocked";

export type CellType =
  | "regionalized_running_w_cgi_ai"
  | "stock"
  | "existing_running_footage"
  | "regionalized_ai_scenes";

export const CELL_TYPES: CellType[] = [
  "regionalized_running_w_cgi_ai",
  "stock",
  "existing_running_footage",
  "regionalized_ai_scenes",
];

export interface Lane {
  key: string;
  label: string;
  abbrev: string;
}

export interface Dials {
  styling_carry_over: number;
  regional_specificity: number;
  voice_adherence: number;
  narrative_continuity: number;
}

export interface Scene {
  cell_id: string;
  cell_type: CellType;
  scene_index: number;
  scene_description: string;
  nameplate?: string | null;
  trim_intent?: string | null;
  color_intent_hint?: string | null;
  camera_angles?: string[];
  super_called?: boolean;
  super_intent?: string | null;
}

export interface Script {
  script_id: string;
  total_scenes: number;
  scenes: Scene[];
}

export interface Project {
  script: Script;
  dials: Dials;
}

// --- Output union (discriminated on `type`) ---

export interface TwelveLabsQuery {
  tags: string[];
  natural_language: string;
  duration_min?: number | null;
  duration_max?: number | null;
  filters?: Record<string, string[] | null> | null;
}

export interface SubstanceRow {
  [key: string]: string | undefined;
  Nameplate?: string;
  "Specific Trim Request"?: string;
  "Location Variant"?: string;
  "Color Preference (HEX)"?: string;
  "Camera Angles"?: string;
  "AI Image Generator Prompt"?: string;
}

export type CellOutput =
  | { type: "twelvelabs_query"; confidence: Confidence; query: TwelveLabsQuery }
  | { type: "cg_env_prompt"; confidence: Confidence; for_pipeline: string; prompt: string }
  | { type: "stock_search"; confidence: Confidence; natural_language_description: string; tags_for_indexed_search: string[] }
  | { type: "substance_row"; confidence: Confidence; row: SubstanceRow; director_notes?: string | null }
  | { type: "super_text"; confidence: Confidence; content: string; voice_tags: string[]; legal_disclaimers: string[]; source_claim?: string | null }
  | { type: "gap_signal"; confidence: Confidence; reason: string; lane: string; season?: string | null; shot_type?: string | null };

export type OutputType = CellOutput["type"];

export interface Provenance {
  key?: string;
  bucket: string;
  scope_resolved: string;
  confidence: Confidence;
}

export interface Envelope {
  cell_id: string;
  cell_type: CellType;
  draft: boolean;
  outputs: CellOutput[];
  gaps_flagged: string[];
  provenance: Provenance[];
}

export interface DraftRecord {
  cell_id: string;
  cell_type: CellType;
  review_status: ReviewStatus;
  approved: boolean;
  envelope: Envelope;
  created_at?: string;
}

export interface RunCellResult {
  envelope: Envelope;
  record: DraftRecord;
}

// --- Recommendations (label/role metadata, keyed by cell_type) ---
export interface Recommendation {
  tool?: string;
  headline?: string;
  primary_output?: OutputType;
  supporting?: OutputType[];
  preferred?: boolean;
}
export interface Recommendations {
  recommendations: Record<string, Recommendation>;
  tool_label: Record<string, string>;
}

// --- TwelveLabs filter taxonomy ---
export interface TLFilterCategory {
  key: string;
  label: string;
  values: string[];
}
export interface TLFilters {
  categories: TLFilterCategory[];
}
