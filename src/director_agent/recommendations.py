"""The single recommendation each cell type makes — one headline production method,
with a primary deliverable and any clearly-secondary supporting outputs. Shared by
the UI (so the recommendation is obvious) and the exports (so each row carries its
role). The technique (cell_type) is the human's choice; this maps it to "what are
we recommending and to which tool."
"""

from __future__ import annotations

from typing import Dict

# tool: "twelvelabs" (find existing footage) | "cgai" (write prompts / render)
RECOMMENDATIONS: Dict[str, dict] = {
    "existing_running_footage": {
        "method": "Find footage",
        "tool": "twelvelabs",
        "headline": "Core footage — reuse from the original spot",
        "primary_output": "twelvelabs_query",
        "supporting": [],
        "preferred": True,  # cheapest / most-preferred path
    },
    "stock": {
        "method": "Find footage",
        "tool": "twelvelabs",
        "headline": "Stock footage",
        "primary_output": "stock_search",
        "supporting": [],
        "preferred": False,
    },
    "regionalized_running_w_cgi_ai": {
        "method": "Write prompts",
        "tool": "cgai",
        "headline": "Regionalize the environment (CG/AI behind the existing plate)",
        "primary_output": "cg_env_prompt",
        "supporting": ["twelvelabs_query"],  # base plate to composite onto — secondary
        "preferred": False,
    },
    "regionalized_ai_scenes": {
        "method": "Write prompts",
        "tool": "cgai",
        "headline": "Full CG/AI scene (Substance render)",
        "primary_output": "substance_row",
        "supporting": [],
        "preferred": False,
    },
}

TOOL_LABEL = {"twelvelabs": "TwelveLabs", "cgai": "CG / AI"}


def recommendation_for(cell_type: str) -> dict:
    return RECOMMENDATIONS.get(cell_type, {})


def output_role(cell_type: str, output_type: str) -> str:
    """primary | supporting | super | flag | other — the role of an output within
    its cell's recommendation."""
    if output_type == "super_text":
        return "super"
    if output_type == "gap_signal":
        return "flag"
    rec = RECOMMENDATIONS.get(cell_type, {})
    if output_type == rec.get("primary_output"):
        return "primary"
    if output_type in rec.get("supporting", []):
        return "supporting"
    return "other"
