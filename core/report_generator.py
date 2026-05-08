"""
Report generation node: Produces an HTML compliance report
from the aggregated pipeline results.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List
from core.state import PipelineState, PageResult


SEVERITY_COLORS = {
    "CRITICAL": "#dc2626",
    "HIGH": "#ea580c",
    "MEDIUM": "#d97706",
    "LOW": "#65a30d",
    "COMPLIANT": "#16a34a",
}

SEVERITY_BADGES = {
    "CRITICAL": "🔴",
    "HIGH": "🟠",
    "MEDIUM": "🟡",
    "LOW": "🟢",
    "COMPLIANT": "✅",
}


def generate_report(state: PipelineState) -> PipelineState:
    """
    LangGraph node: Generate an HTML compliance report and save to disk.
    """
    summary = state.get("summary", {})
    page_results: List[PageResult] = state.get("page_results", [])
    pdf_filename = state.get("pdf_filename", "document.pdf")
    rules = state.get("compliance_rules", [])

    html = _build_html_report(summary, page_results, pdf_filename, rules)

    # Save report to reports directory
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = pdf_filename.replace(" ", "_").replace(".pdf", "")
    report_filename = f"reports/compliance_report_{safe_name}_{timestamp}.html"

    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(html)

    return {
        **state,
        "report_path": report_filename,
        "report_html": html,
        "status": "done",
        "progress_message": f"✅ Report generated: {report_filename}",
    }


def _build_html_report(
    summary: Dict[str, Any],
    page_results: List[PageResult],
    pdf_filename: str,
    rules: List[Dict[str, Any]],
) -> str:
    """Build complete HTML report string."""
    timestamp = datetime.now().strftime("%B %d, %Y at %H:%M:%S")
    overall_risk = summary.get("overall_risk", "UNKNOWN")
    risk_color = SEVERITY_COLORS.get(overall_risk, "#6b7280")
    risk_badge = SEVERITY_BADGES.get(overall_risk, "❓")

    # Rule summary cards
    rule_cards_html = ""
    for rs in summary.get("rule_summaries", []):
        passed = rs.get("passed", True)
        card_color = "#16a34a" if passed else SEVERITY_COLORS.get(rs.get("severity", "MEDIUM"), "#d97706")
        status_text = "PASSED ✅" if passed else f"FAILED ❌ ({rs['violation_count']} violation{'s' if rs['violation_count'] != 1 else ''})"
        pages_list = ", ".join(f"p.{p}" for p in rs.get("violated_pages", [])) or "—"
        rule_cards_html += f"""
        <div class="rule-card" style="border-left: 4px solid {card_color};">
            <div class="rule-header">
                <span class="rule-name">{rs['rule_name']}</span>
                <span class="rule-status" style="color: {card_color};">{status_text}</span>
            </div>
            <div class="rule-meta">
                Severity: <strong>{rs.get('severity','MEDIUM')}</strong> &nbsp;|&nbsp;
                Violated pages: <strong>{pages_list}</strong>
            </div>
        </div>"""

    # Page-level details
    page_details_html = ""
    for result in page_results:
        if not result.has_violations:
            continue

        violations_html = ""
        for flag_type, flags, label in [
            (result.pii_flags, result.pii_flags, "PII / Personal Information"),
            (result.confidential_flags, result.confidential_flags, "Confidential Information"),
            (result.encoding_flags, result.encoding_flags, "Encoding Issues"),
            (result.abusive_flags, result.abusive_flags, "Abusive / Unlawful Content"),
        ]:
            if not flags:
                continue
            items_html = "".join(
                f'<li><span class="badge" style="background:{SEVERITY_COLORS.get(f.get("severity","MEDIUM"), "#d97706")};">{f.get("severity","MEDIUM")}</span> {f.get("detail", "")}</li>'
                for f in flags
            )
            violations_html += f"""
            <div class="violation-group">
                <h4>{label} ({len(flags)} finding{'s' if len(flags) != 1 else ''})</h4>
                <ul>{items_html}</ul>
            </div>"""

        if violations_html:
            page_details_html += f"""
            <div class="page-card">
                <div class="page-header">
                    <span>📄 Page {result.page_number}</span>
                    <span class="violation-count">{sum([len(result.pii_flags), len(result.confidential_flags), len(result.encoding_flags), len(result.abusive_flags)])} violation(s)</span>
                </div>
                <div class="page-body">{violations_html}</div>
            </div>"""

    if not page_details_html:
        page_details_html = '<div class="no-violations">🎉 No violations found on any page.</div>'

    # Severity distribution
    sev_counts = summary.get("severity_counts", {})
    sev_bar_html = ""
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = sev_counts.get(sev, 0)
        if count > 0:
            sev_bar_html += f"""
            <div class="sev-item">
                <span class="sev-label" style="color:{SEVERITY_COLORS[sev]};">{sev}</span>
                <span class="sev-count">{count}</span>
            </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Compliance Report — {pdf_filename}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.6; }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 32px 24px; }}
  .header {{ background: linear-gradient(135deg, #1e293b 0%, #334155 100%); color: white; padding: 32px; border-radius: 12px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 1.8rem; font-weight: 700; margin-bottom: 4px; }}
  .header .meta {{ opacity: 0.75; font-size: 0.9rem; margin-top: 8px; }}
  .risk-badge {{ display: inline-block; padding: 6px 18px; border-radius: 999px; font-weight: 700; font-size: 1.1rem; color: white; background: {risk_color}; margin-top: 12px; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .stat-card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); text-align: center; }}
  .stat-card .value {{ font-size: 2rem; font-weight: 700; color: #1e293b; }}
  .stat-card .label {{ font-size: 0.8rem; color: #64748b; text-transform: uppercase; letter-spacing: .05em; margin-top: 4px; }}
  .section {{ background: white; border-radius: 10px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .section h2 {{ font-size: 1.1rem; font-weight: 700; color: #1e293b; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 2px solid #f1f5f9; }}
  .rule-card {{ background: #f8fafc; border-radius: 8px; padding: 14px 16px; margin-bottom: 10px; }}
  .rule-header {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }}
  .rule-name {{ font-weight: 600; font-size: 0.95rem; }}
  .rule-status {{ font-size: 0.85rem; font-weight: 600; }}
  .rule-meta {{ font-size: 0.8rem; color: #64748b; margin-top: 4px; }}
  .page-card {{ border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 16px; overflow: hidden; }}
  .page-header {{ background: #f1f5f9; padding: 12px 16px; display: flex; justify-content: space-between; font-weight: 600; font-size: 0.95rem; }}
  .violation-count {{ color: #dc2626; }}
  .page-body {{ padding: 16px; }}
  .violation-group {{ margin-bottom: 14px; }}
  .violation-group h4 {{ font-size: 0.85rem; font-weight: 700; color: #475569; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .04em; }}
  .violation-group ul {{ list-style: none; padding-left: 0; }}
  .violation-group li {{ font-size: 0.88rem; color: #374151; padding: 6px 0; border-bottom: 1px solid #f1f5f9; display: flex; align-items: flex-start; gap: 8px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; color: white; font-size: 0.7rem; font-weight: 700; flex-shrink: 0; }}
  .sev-item {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f1f5f9; }}
  .sev-label {{ font-weight: 700; font-size: 0.9rem; }}
  .sev-count {{ font-size: 1.1rem; font-weight: 700; color: #1e293b; }}
  .no-violations {{ text-align: center; padding: 40px; color: #16a34a; font-size: 1.1rem; font-weight: 600; }}
  .footer {{ text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 32px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📋 PDF Compliance Report</h1>
    <div class="meta">
      📄 File: <strong>{pdf_filename}</strong><br>
      🕒 Generated: {timestamp}
    </div>
    <div class="risk-badge">{risk_badge} Overall Risk: {overall_risk}</div>
  </div>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="value">{summary.get('total_pages', 0)}</div>
      <div class="label">Total Pages</div>
    </div>
    <div class="stat-card">
      <div class="value" style="color:#dc2626;">{summary.get('pages_with_violations', 0)}</div>
      <div class="label">Pages with Violations</div>
    </div>
    <div class="stat-card">
      <div class="value" style="color:#ea580c;">{summary.get('total_violations', 0)}</div>
      <div class="label">Total Violations</div>
    </div>
    <div class="stat-card">
      <div class="value" style="color:{risk_color};">{overall_risk}</div>
      <div class="label">Risk Level</div>
    </div>
  </div>

  <div class="section">
    <h2>📊 Severity Distribution</h2>
    {sev_bar_html if sev_bar_html else '<p style="color:#64748b;font-size:.9rem;">No violations found.</p>'}
  </div>

  <div class="section">
    <h2>📏 Compliance Rules Summary</h2>
    {rule_cards_html}
  </div>

  <div class="section">
    <h2>📄 Page-Level Violation Details</h2>
    {page_details_html}
  </div>

  <div class="footer">
    Generated by PDF Compliance Checker · Powered by Gemini AI + LangGraph · PyMuPDF
  </div>
</div>
</body>
</html>"""
    return html