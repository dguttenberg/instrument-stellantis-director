// Thin typed client over the FastAPI backend, reached through the Next rewrite
// proxy (/api/be/* -> backend). Same-origin in the browser, so no CORS.

import type {
  CellOutput,
  DraftRecord,
  Dials,
  Lane,
  Project,
  Recommendations,
  RunCellResult,
  Scene,
  TLFilters,
} from "./types";

// Dev: "/api/be" (set in .env.development) → Next rewrites proxy to the backend.
// Prod (static export served by FastAPI): "" → same-origin calls (/lanes, /run/cell …).
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? JSON.stringify(body);
    } catch {
      try {
        detail = await res.text();
      } catch {
        /* keep statusText */
      }
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  lanes: () => jsonFetch<{ lanes: Lane[] }>("/lanes").then((r) => r.lanes),
  recommendations: () => jsonFetch<Recommendations>("/recommendations"),
  twelvelabsFilters: () => jsonFetch<TLFilters>("/twelvelabs-filters"),
  project: () => jsonFetch<Project>("/project"),
  loadSample: () => jsonFetch<Project>("/project/sample", { method: "POST" }),

  ingest: async (file: File): Promise<Project> => {
    const fd = new FormData();
    fd.append("file", file);
    // no Content-Type header — the browser sets the multipart boundary
    const res = await fetch(`${BASE}/ingest`, { method: "POST", body: fd });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        detail = (await res.json())?.detail ?? detail;
      } catch {
        /* keep */
      }
      throw new Error(detail);
    }
    return res.json();
  },

  patchScene: (sceneIndex: number, patch: Partial<Scene>) =>
    jsonFetch<Scene>(`/project/scenes/${sceneIndex}`, {
      method: "PUT",
      body: JSON.stringify(patch),
    }),

  runCell: (body: {
    lane: string;
    scene_index: number;
    dials?: Dials;
    prior_cell_resolved?: unknown;
    season?: string;
  }) =>
    jsonFetch<RunCellResult>("/run/cell", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  editDraft: (cellId: string, outputs: CellOutput[], gaps_flagged?: string[]) =>
    jsonFetch<DraftRecord>(`/drafts/${encodeURIComponent(cellId)}`, {
      method: "PUT",
      body: JSON.stringify({ outputs, gaps_flagged }),
    }),

  approveDraft: (cellId: string) =>
    jsonFetch<DraftRecord>(`/drafts/${encodeURIComponent(cellId)}/approve`, {
      method: "POST",
    }),
};

export const exportUrl = (kind: "cgi.xlsx" | "twelvelabs.csv" | "twelvelabs.json") =>
  `${BASE}/export/${kind}`;
