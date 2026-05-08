"""
Aggregation node: Summarises all page-level results into a
structured compliance summary for the report generator.
"""

from typing import Dict, Any, List
from core.state import PipelineState, PageResult


def aggregate_results(state: PipelineState) -> PipelineState:
    """
    LangGraph node: Aggregate page-level PageResult objects into a
    high-level summary dict.
    """
    page_results: List[PageResult] = state.get("page_results", [])
    rules = state.get("compliance_rules", [])

    # Rule-level counters
    violation_counts = {
        "PII_CHECK": 0,
        "CONFIDENTIAL_CHECK": 0,
        "ENCODING_CHECK": 0,
        "ABUSIVE_CONTENT_CHECK": 0,
    }
    violated_pages = {k: [] for k in violation_counts}
    total_violations = 0
    pages_with_violations = 0

    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for result in page_results:
        page_violated = False

        if result.pii_flags:
            violation_counts["PII_CHECK"] += len(result.pii_flags)
            violated_pages["PII_CHECK"].append(result.page_number)
            page_violated = True
            for f in result.pii_flags:
                sev = f.get("severity", "MEDIUM")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if result.confidential_flags:
            violation_counts["CONFIDENTIAL_CHECK"] += len(result.confidential_flags)
            violated_pages["CONFIDENTIAL_CHECK"].append(result.page_number)
            page_violated = True
            for f in result.confidential_flags:
                sev = f.get("severity", "HIGH")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if result.encoding_flags:
            violation_counts["ENCODING_CHECK"] += len(result.encoding_flags)
            violated_pages["ENCODING_CHECK"].append(result.page_number)
            page_violated = True
            for f in result.encoding_flags:
                sev = f.get("severity", "MEDIUM")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if result.abusive_flags:
            violation_counts["ABUSIVE_CONTENT_CHECK"] += len(result.abusive_flags)
            violated_pages["ABUSIVE_CONTENT_CHECK"].append(result.page_number)
            page_violated = True
            for f in result.abusive_flags:
                sev = f.get("severity", "CRITICAL")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if page_violated:
            pages_with_violations += 1
        total_violations += sum([
            len(result.pii_flags),
            len(result.confidential_flags),
            len(result.encoding_flags),
            len(result.abusive_flags),
        ])

    # Compute overall risk level
    if severity_counts.get("CRITICAL", 0) > 0:
        overall_risk = "CRITICAL"
    elif severity_counts.get("HIGH", 0) > 0:
        overall_risk = "HIGH"
    elif severity_counts.get("MEDIUM", 0) > 0:
        overall_risk = "MEDIUM"
    elif total_violations > 0:
        overall_risk = "LOW"
    else:
        overall_risk = "COMPLIANT"

    # Rule-level summary with metadata
    rule_map = {r["id"]: r for r in rules}
    rule_summaries = []
    for rule_id, count in violation_counts.items():
        rule = rule_map.get(rule_id, {})
        if not rule.get("enabled", True):
            continue
        rule_summaries.append({
            "rule_id": rule_id,
            "rule_name": rule.get("name", rule_id),
            "severity": rule.get("severity", "MEDIUM"),
            "enabled": rule.get("enabled", True),
            "violation_count": count,
            "violated_pages": sorted(set(violated_pages[rule_id])),
            "passed": count == 0,
        })

    summary = {
        "total_pages": state.get("total_pages", 0),
        "pages_analyzed": len(page_results),
        "pages_with_violations": pages_with_violations,
        "total_violations": total_violations,
        "overall_risk": overall_risk,
        "severity_counts": severity_counts,
        "violation_counts": violation_counts,
        "violated_pages_by_rule": violated_pages,
        "rule_summaries": rule_summaries,
        "pdf_filename": state.get("pdf_filename", "unknown.pdf"),
    }

    return {
        **state,
        "summary": summary,
        "violation_counts": violation_counts,
        "status": "reporting",
        "progress_message": f"✅ Aggregated results. Overall risk: {overall_risk}",
    }