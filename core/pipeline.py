"""
LangGraph pipeline orchestration.
Defines the full compliance-check workflow as a directed graph.

Nodes:
  extract_text  →  analyze_compliance  →  aggregate_results  →  generate_report

Edge conditions:
  - If extraction fails, route to error_handler
  - If no pages found, route to error_handler
  - Otherwise proceed linearly
"""

from langgraph.graph import StateGraph, END
from core.state import PipelineState
from core.pdf_extractor import extract_pdf_text
from core.compliance_analyzer import analyze_all_pages
from core.aggregator import aggregate_results
from core.report_generator import generate_report


# ─── Node wrappers ─────────────────────────────────────────────────────────────

def node_extract(state: PipelineState) -> PipelineState:
    return extract_pdf_text({**state, "status": "extracting", "progress_message": "⏳ Extracting PDF text..."})


def node_analyze(state: PipelineState) -> PipelineState:
    return analyze_all_pages({**state, "progress_message": "⏳ Running AI compliance checks..."})


def node_aggregate(state: PipelineState) -> PipelineState:
    return aggregate_results({**state, "progress_message": "⏳ Aggregating results..."})


def node_report(state: PipelineState) -> PipelineState:
    return generate_report({**state, "progress_message": "⏳ Generating report..."})


def node_error(state: PipelineState) -> PipelineState:
    return {
        **state,
        "status": "error",
        "progress_message": "❌ Pipeline failed. Check errors for details.",
    }


# ─── Conditional routing ────────────────────────────────────────────────────────

def route_after_extract(state: PipelineState) -> str:
    if state.get("status") == "error" or state.get("extraction_error"):
        return "error"
    if not state.get("pages_text"):
        return "error"
    return "analyze"


def route_after_analyze(state: PipelineState) -> str:
    if state.get("status") == "error":
        return "error"
    return "aggregate"


# ─── Build graph ────────────────────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    """
    Constructs and compiles the LangGraph compliance pipeline.
    Returns a compiled runnable graph.
    """
    workflow = StateGraph(PipelineState)

    # Register nodes
    workflow.add_node("extract", node_extract)
    workflow.add_node("analyze", node_analyze)
    workflow.add_node("aggregate", node_aggregate)
    workflow.add_node("report", node_report)
    workflow.add_node("error_handler", node_error)

    # Entry point
    workflow.set_entry_point("extract")

    # Edges with conditional routing
    workflow.add_conditional_edges(
        "extract",
        route_after_extract,
        {"analyze": "analyze", "error": "error_handler"},
    )
    workflow.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {"aggregate": "aggregate", "error": "error_handler"},
    )
    workflow.add_edge("aggregate", "report")
    workflow.add_edge("report", END)
    workflow.add_edge("error_handler", END)

    return workflow.compile()


def run_pipeline(
    pdf_path: str,
    pdf_filename: str,
    compliance_rules: list,
) -> PipelineState:
    """
    Run the full compliance pipeline for a given PDF.

    Args:
        pdf_path: Absolute or relative path to the PDF file on disk.
        pdf_filename: Original filename for display in reports.
        compliance_rules: List of rule dicts loaded from compliance_rules.json.

    Returns:
        Final PipelineState after all nodes have executed.
    """
    graph = build_pipeline()

    initial_state: PipelineState = {
        "pdf_path": pdf_path,
        "pdf_filename": pdf_filename,
        "compliance_rules": compliance_rules,
        "pages_text": [],
        "total_pages": 0,
        "extraction_error": None,
        "page_results": [],
        "current_page_index": 0,
        "summary": {},
        "violation_counts": {},
        "report_path": None,
        "report_html": None,
        "status": "pending",
        "errors": [],
        "progress_message": "⏳ Starting pipeline...",
    }

    final_state = graph.invoke(initial_state)
    return final_state