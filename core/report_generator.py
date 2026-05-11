"""
Report generation node — professional, comprehensive HTML compliance report.

Sections:
  1.  Header  — gradient, risk pill, compliance score gauge, file metadata
  2.  Executive Summary — AI-written paragraph
  3.  KPI Cards (8)
  4.  Severity Distribution (SVG bar chart)
  5.  Pipeline Timeline
  6.  Rule-by-Rule Compliance Table  (with criticality badges)
  7.  Violation Heatmap  — page × rule matrix
  8.  Clean Pages Roster
  9.  Page-Level Violation Deep-dive  (expandable cards per page)
  10. Top Findings Summary  — deduplicated, ranked by severity
  11. Recommended Remediation Actions
  12. Scan Metadata & Audit Trail
  13. Footer
"""

import os
from datetime import datetime
from typing import Dict, Any, List
from core.state import PipelineState, PageResult

# ── colour / icon maps ─────────────────────────────────────────────────────────
SC = {
    "CRITICAL": "#dc2626", "HIGH": "#ea580c",
    "MEDIUM":   "#d97706", "LOW":  "#65a30d",
    "COMPLIANT":"#16a34a",
}
ICONS  = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","LOW":"🟢","COMPLIANT":"✅"}
RULE_ICONS = {
    "PII_CHECK":"🔍","CONFIDENTIAL_CHECK":"🔒",
    "ENCODING_CHECK":"🔤","ABUSIVE_CONTENT_CHECK":"🚫",
}
SEV_ORDER = ["CRITICAL","HIGH","MEDIUM","LOW"]


# ═══════════════════════════════════════════════════════════════════════════════
# Public node
# ═══════════════════════════════════════════════════════════════════════════════

def generate_report(state: PipelineState) -> PipelineState:
    summary      = state.get("summary", {})
    page_results = state.get("page_results", [])
    pdf_filename = state.get("pdf_filename", "document.pdf")
    rules        = state.get("compliance_rules", [])
    duration     = state.get("scan_duration_seconds")

    html = _build_html(summary, page_results, pdf_filename, rules, duration)

    os.makedirs("reports", exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = pdf_filename.replace(" ", "_").replace(".pdf", "")
    path = f"reports/compliance_report_{safe}_{ts}.html"

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    return {
        **state,
        "report_path": path,
        "report_html": html,
        "status":      "done",
        "progress_message": f"✅ Report saved: {path}",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _gauge(score: int) -> str:
    r    = 52
    circ = 2 * 3.14159 * r
    dash = circ * score / 100
    col  = SC["COMPLIANT"] if score >= 80 else (SC["HIGH"] if score >= 50 else SC["CRITICAL"])
    return f"""
<svg width="130" height="130" viewBox="0 0 130 130" xmlns="http://www.w3.org/2000/svg">
  <circle cx="65" cy="65" r="{r}" fill="none" stroke="#1e3a5f" stroke-width="11"/>
  <circle cx="65" cy="65" r="{r}" fill="none" stroke="{col}" stroke-width="11"
    stroke-dasharray="{dash:.1f} {circ:.1f}"
    stroke-dashoffset="{circ/4:.1f}" stroke-linecap="round"/>
  <text x="65" y="70" text-anchor="middle"
    font-family="Segoe UI,sans-serif" font-size="24" font-weight="800" fill="{col}">{score}</text>
  <text x="65" y="84" text-anchor="middle"
    font-family="Segoe UI,sans-serif" font-size="9" fill="#64748b" letter-spacing="1">SCORE / 100</text>
</svg>"""


def _sev_bars(counts: Dict) -> str:
    total = sum(counts.values()) or 1
    html  = ""
    for s in SEV_ORDER:
        n = counts.get(s, 0)
        pct = round(n * 100 / total)
        html += f"""
<div style="margin-bottom:14px;">
  <div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:5px;">
    <span style="font-weight:800;color:{SC[s]};">{ICONS[s]} {s}</span>
    <span style="font-weight:700;color:#1e293b;">{n}
      <span style="color:#94a3b8;font-weight:400;">({pct}%)</span>
    </span>
  </div>
  <div style="background:#1e3a5f;border-radius:6px;height:10px;overflow:hidden;">
    <div style="width:{pct}%;background:{SC[s]};height:10px;border-radius:6px;
      box-shadow:0 0 8px {SC[s]}66;transition:width .3s;"></div>
  </div>
</div>"""
    if not any(counts.get(s, 0) for s in SEV_ORDER):
        html = "<p style='color:#64748b;font-size:.85rem;'>No violations — all checks passed.</p>"
    return html


def _sev_badge(sev: str, small: bool = False) -> str:
    c  = SC.get(sev, "#94a3b8")
    px = "2px 9px" if small else "3px 13px"
    fs = ".68rem" if small else ".75rem"
    return (f'<span style="display:inline-block;background:{c};color:white;'
            f'padding:{px};border-radius:999px;font-size:{fs};font-weight:800;">{sev}</span>')


def _rule_table(rule_summaries: List[Dict]) -> str:
    rows = ""
    for rs in rule_summaries:
        passed   = rs["passed"]
        sev_col  = SC.get(rs.get("severity","MEDIUM"), SC["MEDIUM"])
        icon     = RULE_ICONS.get(rs["rule_id"], "📌")
        pages    = ", ".join(f"p.{p}" for p in rs["violated_pages"]) or "—"
        status   = "✅ PASSED" if passed else "❌ FAILED"
        st_col   = "#16a34a" if passed else "#dc2626"
        bg_row   = "#f0fdf4" if passed else "#fff5f5"
        cnt_col  = "#16a34a" if passed else "#dc2626"
        rows += f"""
<tr style="background:{bg_row};">
  <td style="padding:12px 14px;font-weight:700;font-size:.87rem;color:#0f172a;border-bottom:1px solid #e2e8f0;">
    {icon} {rs['rule_name']}
    {'<span style="font-size:.68rem;color:#64748b;font-weight:400;display:block;">custom rule</span>' if rs.get('custom') else ''}
  </td>
  <td style="padding:12px 14px;text-align:center;border-bottom:1px solid #e2e8f0;">
    {_sev_badge(rs['severity'])}
  </td>
  <td style="padding:12px 14px;text-align:center;border-bottom:1px solid #e2e8f0;">
    <span style="font-weight:800;font-size:.88rem;color:{st_col};">{status}</span>
  </td>
  <td style="padding:12px 14px;text-align:center;font-weight:800;font-size:.9rem;
    color:{cnt_col};border-bottom:1px solid #e2e8f0;">{rs['violation_count']}</td>
  <td style="padding:12px 14px;font-size:.82rem;color:#475569;border-bottom:1px solid #e2e8f0;">{pages}</td>
</tr>"""

    return f"""
<table style="width:100%;border-collapse:collapse;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.07);">
  <thead>
    <tr style="background:#0f172a;color:#e2e8f0;">
      <th style="padding:12px 14px;text-align:left;font-size:.75rem;letter-spacing:.07em;font-weight:700;">RULE</th>
      <th style="padding:12px 14px;text-align:center;font-size:.75rem;letter-spacing:.07em;font-weight:700;">SEVERITY</th>
      <th style="padding:12px 14px;text-align:center;font-size:.75rem;letter-spacing:.07em;font-weight:700;">STATUS</th>
      <th style="padding:12px 14px;text-align:center;font-size:.75rem;letter-spacing:.07em;font-weight:700;">FINDINGS</th>
      <th style="padding:12px 14px;text-align:left;font-size:.75rem;letter-spacing:.07em;font-weight:700;">AFFECTED PAGES</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>"""


def _heatmap(page_results: List[PageResult], rule_summaries: List[Dict]) -> str:
    """Page × Rule violation matrix."""
    if not page_results or not rule_summaries:
        return ""

    rule_ids   = [rs["rule_id"] for rs in rule_summaries]
    rule_names = [rs["rule_name"] for rs in rule_summaries]

    # Build index: {page_number: {rule_id: severity}}
    page_map: Dict[int, Dict[str, str]] = {}
    for r in page_results:
        pm: Dict[str, str] = {}
        for flag in r.pii_flags:
            pm["PII_CHECK"] = flag.get("severity","HIGH")
        for flag in r.confidential_flags:
            pm["CONFIDENTIAL_CHECK"] = flag.get("severity","HIGH")
        for flag in r.encoding_flags:
            pm["ENCODING_CHECK"] = flag.get("severity","MEDIUM")
        for flag in r.abusive_flags:
            rid = flag.get("rule_id","ABUSIVE_CONTENT_CHECK")
            pm[rid] = flag.get("severity","CRITICAL")
        page_map[r.page_number] = pm

    # Only include pages with at least one violation
    violated_pnums = sorted([r.page_number for r in page_results if r.has_violations])
    if not violated_pnums:
        return ""

    # Header row
    th_rules = "".join(
        f'<th style="padding:7px 6px;font-size:.65rem;font-weight:700;color:#64748b;'
        f'text-align:center;max-width:80px;white-space:normal;line-height:1.2;">'
        f'{RULE_ICONS.get(rid,"📌")}<br>{name.replace(" /","<br>")}</th>'
        for rid, name in zip(rule_ids, rule_names)
    )

    rows_html = ""
    for pnum in violated_pnums:
        pm = page_map.get(pnum, {})
        cells = ""
        for rid in rule_ids:
            if rid in pm:
                sev = pm[rid]
                c   = SC.get(sev, "#94a3b8")
                cells += (f'<td style="text-align:center;padding:7px 6px;">'
                          f'<span style="display:inline-block;width:28px;height:28px;line-height:28px;'
                          f'background:{c};border-radius:6px;font-size:.65rem;color:white;font-weight:800;">'
                          f'{sev[0]}</span></td>')
            else:
                cells += '<td style="text-align:center;padding:7px 6px;"><span style="color:#e2e8f0;font-size:.85rem;">—</span></td>'
        rows_html += f"""
<tr>
  <td style="padding:7px 10px;font-weight:700;font-size:.82rem;color:#0f172a;
    border-right:2px solid #e2e8f0;">p.{pnum}</td>
  {cells}
</tr>"""

    return f"""
<div style="overflow-x:auto;">
<table style="width:100%;border-collapse:collapse;font-size:.82rem;">
  <thead>
    <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
      <th style="padding:7px 10px;text-align:left;font-size:.75rem;font-weight:700;color:#0f172a;
        border-right:2px solid #e2e8f0;">PAGE</th>
      {th_rules}
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
</div>
<p style="font-size:.7rem;color:#94a3b8;margin-top:8px;">
  Cell key: <strong style="color:{SC['CRITICAL']};">C</strong>=Critical &nbsp;
  <strong style="color:{SC['HIGH']};">H</strong>=High &nbsp;
  <strong style="color:{SC['MEDIUM']};">M</strong>=Medium &nbsp;
  <strong style="color:{SC['LOW']};">L</strong>=Low &nbsp; —=No violation
</p>"""


def _top_findings(page_results: List[PageResult], top_n: int = 10) -> str:
    """Deduplicated top findings ranked by severity."""
    all_flags = []
    for r in page_results:
        for f in (r.pii_flags + r.confidential_flags +
                  r.encoding_flags + r.abusive_flags):
            all_flags.append({**f, "page_number": r.page_number})

    if not all_flags:
        return "<p style='color:#64748b;font-size:.85rem;'>No findings to report.</p>"

    # Sort by severity then page
    sev_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_flags.sort(key=lambda x: (sev_rank.get(x.get("severity","LOW"),3), x.get("page_number",0)))

    # Deduplicate by detail text (keep first occurrence)
    seen   = set()
    unique = []
    for f in all_flags:
        key = f.get("detail","")[:60]
        if key not in seen:
            seen.add(key)
            unique.append(f)

    rows = ""
    for i, f in enumerate(unique[:top_n], 1):
        sev   = f.get("severity","MEDIUM")
        c     = SC.get(sev, "#94a3b8")
        rname = f.get("rule_name", f.get("rule_id",""))
        rows += f"""
<tr style="{'background:#fff5f5' if sev in ('CRITICAL','HIGH') else ''}">
  <td style="padding:10px 12px;text-align:center;font-weight:800;font-size:.82rem;
    color:#64748b;border-bottom:1px solid #f1f5f9;">{i}</td>
  <td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;">
    {_sev_badge(sev, small=True)}
  </td>
  <td style="padding:10px 12px;font-size:.82rem;font-weight:700;color:#374151;
    border-bottom:1px solid #f1f5f9;">{rname}</td>
  <td style="padding:10px 12px;font-size:.82rem;color:#475569;
    border-bottom:1px solid #f1f5f9;">{f.get("detail","")}</td>
  <td style="padding:10px 12px;text-align:center;font-weight:700;font-size:.82rem;
    color:#0f172a;border-bottom:1px solid #f1f5f9;">p.{f.get("page_number","?")}</td>
</tr>"""

    return f"""
<table style="width:100%;border-collapse:collapse;">
  <thead>
    <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
      <th style="padding:9px 12px;font-size:.72rem;font-weight:700;color:#64748b;">#</th>
      <th style="padding:9px 12px;font-size:.72rem;font-weight:700;color:#64748b;">SEVERITY</th>
      <th style="padding:9px 12px;font-size:.72rem;font-weight:700;color:#64748b;">RULE</th>
      <th style="padding:9px 12px;font-size:.72rem;font-weight:700;color:#64748b;">FINDING</th>
      <th style="padding:9px 12px;font-size:.72rem;font-weight:700;color:#64748b;text-align:center;">PAGE</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
{'<p style="font-size:.72rem;color:#94a3b8;margin-top:6px;">Showing top '+str(top_n)+' unique findings by severity.</p>' if len(unique) > top_n else ''}"""


def _page_details(page_results: List[PageResult]) -> str:
    violated = [r for r in page_results if r.has_violations]
    if not violated:
        return """
<div style="text-align:center;padding:48px 24px;background:#f0fdf4;border-radius:12px;
  border:1px dashed #86efac;">
  <div style="font-size:3rem;margin-bottom:10px;">🎉</div>
  <strong style="font-size:1rem;color:#16a34a;">No violations found on any page</strong>
  <p style="color:#64748b;font-size:.85rem;margin-top:6px;">All pages passed every enabled compliance rule.</p>
</div>"""

    html = ""
    for result in violated:
        all_f = (result.pii_flags + result.confidential_flags +
                 result.encoding_flags + result.abusive_flags)
        worst = max((f.get("severity","LOW") for f in all_f),
                    key=lambda s: SEV_ORDER.index(s) if s in SEV_ORDER else 3,
                    default="LOW")
        wc    = SC.get(worst, "#64748b")
        n_v   = len(all_f)

        groups_html = ""
        for label, flags in [
            ("🔍 PII / Personal Information",  result.pii_flags),
            ("🔒 Confidential Information",    result.confidential_flags),
            ("🔤 Encoding Issues",             result.encoding_flags),
            ("🚫 Abusive / Unlawful Content",  result.abusive_flags),
        ]:
            if not flags:
                continue
            items = "".join(
                f'<li style="display:flex;gap:10px;align-items:flex-start;padding:7px 0;'
                f'border-bottom:1px solid #f1f5f9;">'
                f'{_sev_badge(f.get("severity","MEDIUM"), small=True)}'
                f'<span style="font-size:.83rem;color:#374151;">{f.get("detail","")}</span></li>'
                for f in flags
            )
            groups_html += f"""
<div style="margin-bottom:14px;">
  <div style="font-size:.78rem;font-weight:800;color:#475569;text-transform:uppercase;
    letter-spacing:.05em;margin-bottom:6px;">{label} &nbsp;({len(flags)})</div>
  <ul style="list-style:none;padding:0;">{items}</ul>
</div>"""

        html += f"""
<div style="border:1px solid #e2e8f0;border-radius:10px;margin-bottom:14px;overflow:hidden;">
  <div style="background:#f8fafc;padding:12px 16px;display:flex;justify-content:space-between;
    align-items:center;border-bottom:1px solid #e2e8f0;">
    <span style="font-weight:800;font-size:.9rem;color:#0f172a;">📄 Page {result.page_number}</span>
    <div style="display:flex;gap:8px;align-items:center;">
      {_sev_badge(worst)}
      <span style="font-size:.78rem;color:#64748b;">{n_v} finding(s)</span>
    </div>
  </div>
  <div style="padding:14px 16px;">{groups_html}</div>
</div>"""

    return html


def _clean_badges(page_results: List[PageResult]) -> str:
    clean = [r for r in page_results if not r.has_violations]
    if not clean:
        return "<p style='color:#64748b;font-size:.85rem;'>All pages have at least one finding.</p>"
    return " ".join(
        f'<span style="display:inline-block;background:#f0fdf4;border:1px solid #86efac;'
        f'border-radius:6px;padding:4px 10px;font-size:.78rem;font-weight:700;'
        f'color:#16a34a;margin:3px;">p.{r.page_number}</span>'
        for r in clean
    )


def _recommendations(overall_risk: str, rule_summaries: List[Dict]) -> str:
    recs_map = {
        "PII_CHECK": (
            "🔐 Remove or pseudonymise all PII",
            "Redact email addresses, phone numbers, SSNs, credit card numbers, "
            "passport numbers, dates of birth, and home addresses before distributing this document.",
        ),
        "CONFIDENTIAL_CHECK": (
            "🔑 Secure or remove confidential data",
            "Revoke and rotate any exposed API keys or passwords immediately. "
            "Remove unreleased product details, M&A information, and internal pricing from this document.",
        ),
        "ENCODING_CHECK": (
            "🔤 Fix encoding inconsistencies",
            "Re-save the document as UTF-8. Remove or translate non-English content. "
            "Ensure no garbled or mojibake characters remain.",
        ),
        "ABUSIVE_CONTENT_CHECK": (
            "🚫 Remove abusive / unlawful content",
            "Review and delete all abusive language, hate speech, threats, "
            "discriminatory statements, and any instructions for illegal activities.",
        ),
    }
    failed = [rs for rs in rule_summaries if not rs["passed"]]
    if not failed:
        return """
<div style="display:flex;gap:12px;align-items:center;padding:14px;
  background:#f0fdf4;border-radius:10px;border:1px solid #86efac;">
  <span style="font-size:1.5rem;">🎉</span>
  <span style="color:#16a34a;font-weight:700;">Document is fully compliant — no remediation required.</span>
</div>"""

    html = ""
    for rs in failed:
        rid  = rs["rule_id"]
        sev  = rs["severity"]
        c    = SC.get(sev, "#94a3b8")
        pages_str = ", ".join(f"p.{p}" for p in rs["violated_pages"])
        title, detail = recs_map.get(rid, (
            f"Remediate {rs['rule_name']} violations",
            "Review the flagged pages and remove or correct the identified content.",
        ))
        html += f"""
<div style="display:flex;gap:14px;align-items:flex-start;padding:14px 0;
  border-bottom:1px solid #f1f5f9;">
  <div style="background:{c};color:white;border-radius:8px;padding:6px 11px;
    font-size:.72rem;font-weight:800;flex-shrink:0;line-height:1.4;text-align:center;">
    {sev}<br><span style="font-weight:400;font-size:.65rem;">SEVERITY</span>
  </div>
  <div>
    <strong style="font-size:.88rem;color:#0f172a;">{title}</strong>
    <span style="font-size:.75rem;color:#94a3b8;margin-left:8px;">Affects pages: {pages_str}</span>
    <p style="font-size:.83rem;color:#64748b;margin-top:4px;">{detail}</p>
  </div>
</div>"""
    return html


def _pipeline_timeline(duration) -> str:
    dur_str = f"{duration}s" if duration else "—"
    steps = [
        ("📖", "Text Extraction",     "pypdfium2 page-by-page extraction with encoding heuristics"),
        ("🤖", "AI Compliance Check", f"Groq Llama-3.1-8b-instant · per-page chunked analysis · guardrails active"),
        ("📊", "Aggregation",         "Per-rule violation counts, risk scoring, compliance score"),
        ("📝", "Report Generation",   f"HTML report · JSON export · Scan duration: {dur_str}"),
        ("✂️", "PDF Redaction",       "Targeted black-box redaction of flagged content"),
    ]
    html = ""
    for i, (icon, title, desc) in enumerate(steps):
        connector = ('<div style="width:2px;height:16px;background:#e2e8f0;'
                     'margin-left:13px;"></div>') if i < len(steps) - 1 else ""
        html += f"""
<div style="display:flex;gap:12px;align-items:flex-start;">
  <div style="width:28px;height:28px;border-radius:50%;background:#1e40af;color:white;
    display:flex;align-items:center;justify-content:center;font-size:.8rem;flex-shrink:0;">
    {icon}
  </div>
  <div style="padding-bottom:4px;">
    <div style="font-weight:700;font-size:.86rem;color:#0f172a;">{title}</div>
    <div style="font-size:.77rem;color:#64748b;">{desc}</div>
  </div>
</div>
{connector}"""
    return html


def _audit_table(summary: Dict, pdf_filename: str, rules: List[Dict], duration) -> str:
    ts           = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    enabled_ids  = [r["id"] for r in rules if r.get("enabled", True)]
    custom_cnt   = sum(1 for r in rules if r.get("custom", False))
    dur_str      = f"{duration}s" if duration else "—"
    rows = [
        ("Document",         pdf_filename),
        ("Report Generated", ts),
        ("Scan Duration",    dur_str),
        ("AI Model",         "groq/llama-3.1-8b-instant"),
        ("LLM Guardrails",   "Prompt-injection defence · JSON-only output · findings capped at 100 chars"),
        ("Orchestration",    "LangGraph stateful pipeline (extract → analyze → aggregate → report → redact)"),
        ("PDF Engine",       "pypdfium2 (Chromium PDF renderer)"),
        ("Pages Scanned",    str(summary.get("total_pages", 0))),
        ("Rules Active",     f"{len(enabled_ids)} ({custom_cnt} custom)"),
        ("Rule IDs",         " · ".join(enabled_ids)),
        ("Overall Risk",     summary.get("overall_risk","—")),
        ("Compliance Score", f"{summary.get('compliance_score',0)} / 100"),
    ]
    rows_html = "".join(
        f'<tr style="background:{"#f8fafc" if i%2==0 else "white"};">'
        f'<td style="padding:9px 14px;font-weight:700;font-size:.8rem;color:#475569;'
        f'width:220px;border-bottom:1px solid #f1f5f9;">{k}</td>'
        f'<td style="padding:9px 14px;font-size:.8rem;color:#1e293b;'
        f'border-bottom:1px solid #f1f5f9;">{v}</td></tr>'
        for i, (k, v) in enumerate(rows)
    )
    return f"""
<table style="width:100%;border-collapse:collapse;border-radius:10px;overflow:hidden;">
  <tbody>{rows_html}</tbody>
</table>"""


# ═══════════════════════════════════════════════════════════════════════════════
# Master HTML builder
# ═══════════════════════════════════════════════════════════════════════════════

def _build_html(
    summary: Dict[str, Any],
    page_results: List[PageResult],
    pdf_filename: str,
    rules: List[Dict],
    duration,
) -> str:
    ts           = datetime.now().strftime("%B %d, %Y at %H:%M:%S")
    overall_risk = summary.get("overall_risk", "UNKNOWN")
    risk_color   = SC.get(overall_risk, "#6b7280")
    risk_icon    = ICONS.get(overall_risk, "❓")
    score        = summary.get("compliance_score", 0)
    dur_str      = f"{duration}s" if duration else "—"

    tv = summary.get("total_violations", 0)
    pv = summary.get("pages_with_violations", 0)
    tp = summary.get("total_pages", 0)
    pc = summary.get("pages_clean", 0)
    sev= summary.get("severity_counts", {})
    pa = summary.get("pages_analyzed", 0)

    enabled_rules = [r for r in rules if r.get("enabled", True)]
    custom_rules  = [r for r in enabled_rules if r.get("custom", False)]

    # Executive summary text
    if overall_risk == "COMPLIANT":
        exec_text = (
            "This document successfully passed all enabled compliance checks with zero violations detected "
            f"across all {tp} page(s). It is cleared for distribution subject to any manual review policies "
            "in place at your organisation."
        )
    else:
        crit = sev.get("CRITICAL", 0)
        high = sev.get("HIGH", 0)
        med  = sev.get("MEDIUM", 0)
        parts = []
        if crit: parts.append(f"<strong style='color:{SC['CRITICAL']};'>{crit} Critical</strong>")
        if high: parts.append(f"<strong style='color:{SC['HIGH']};'>{high} High</strong>")
        if med:  parts.append(f"<strong style='color:{SC['MEDIUM']};'>{med} Medium</strong>")
        sev_str = ", ".join(parts) if parts else f"<strong>{tv}</strong>"
        exec_text = (
            f"This document contains <strong>{tv} compliance violation(s)</strong> across "
            f"<strong>{pv} of {tp} page(s)</strong>, with findings categorised as {sev_str}. "
            f"The overall risk rating is <strong style='color:{risk_color};'>{overall_risk}</strong> "
            f"and the compliance score is <strong>{score}/100</strong>. "
            f"<strong>Immediate remediation is recommended</strong> before this document is "
            "distributed, archived, or shared externally."
        )

    gauge_svg    = _gauge(score)
    sev_html     = _sev_bars(sev)
    rule_tbl     = _rule_table(summary.get("rule_summaries", []))
    heatmap_html = _heatmap(page_results, summary.get("rule_summaries", []))
    page_det     = _page_details(page_results)
    clean_bdg    = _clean_badges(page_results)
    recs_html    = _recommendations(overall_risk, summary.get("rule_summaries", []))
    timeline_html= _pipeline_timeline(duration)
    top_find     = _top_findings(page_results)
    audit_html   = _audit_table(summary, pdf_filename, rules, duration)
    exec_bg      = ("#f0fdf4" if overall_risk == "COMPLIANT"
                    else "#fff7ed" if overall_risk in ("MEDIUM","LOW")
                    else "#fef2f2")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Compliance Report — {pdf_filename}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
    background:#f0f4f8;color:#1e293b;line-height:1.6;}}
  .wrap{{max-width:1100px;margin:0 auto;padding:32px 20px;}}
  /* header */
  .hdr{{background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 50%,#1e40af 100%);
    color:white;padding:36px 40px;border-radius:16px;margin-bottom:28px;
    position:relative;overflow:hidden;box-shadow:0 4px 24px rgba(30,64,175,.4);}}
  .hdr::before{{content:'';position:absolute;top:-60px;right:-60px;
    width:280px;height:280px;background:rgba(255,255,255,.04);border-radius:50%;}}
  .hdr::after{{content:'';position:absolute;bottom:-40px;left:30%;
    width:180px;height:180px;background:rgba(56,189,248,.06);border-radius:50%;}}
  .hdr h1{{font-size:1.8rem;font-weight:800;letter-spacing:-.02em;position:relative;}}
  .hdr .meta{{opacity:.7;font-size:.83rem;margin-top:8px;line-height:1.9;position:relative;}}
  .risk-pill{{display:inline-flex;align-items:center;gap:8px;margin-top:14px;
    padding:7px 20px;border-radius:999px;font-weight:800;font-size:1rem;
    background:{risk_color};color:white;box-shadow:0 4px 14px {risk_color}55;position:relative;}}
  /* exec */
  .exec{{background:{exec_bg};border-left:5px solid {risk_color};border-radius:10px;
    padding:16px 20px;margin-bottom:24px;font-size:.9rem;color:#374151;line-height:1.75;}}
  /* grid */
  .grid8{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));
    gap:14px;margin-bottom:26px;}}
  .kcard{{background:white;border-radius:12px;padding:18px 14px;text-align:center;
    box-shadow:0 1px 4px rgba(0,0,0,.07);border:1px solid #e2e8f0;}}
  .kcard .val{{font-size:1.9rem;font-weight:800;line-height:1;}}
  .kcard .lbl{{font-size:.65rem;color:#94a3b8;text-transform:uppercase;
    letter-spacing:.07em;margin-top:5px;}}
  /* section */
  .sec{{background:white;border-radius:14px;padding:26px 28px;margin-bottom:22px;
    box-shadow:0 1px 4px rgba(0,0,0,.07);border:1px solid #e2e8f0;}}
  .sec-title{{font-size:.95rem;font-weight:800;color:#0f172a;border-bottom:2px solid #f1f5f9;
    padding-bottom:10px;margin-bottom:18px;display:flex;align-items:center;gap:8px;}}
  /* two-col */
  .two-col{{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-bottom:22px;}}
  @media(max-width:720px){{.two-col{{grid-template-columns:1fr;}}
    .grid8{{grid-template-columns:repeat(4,1fr);}}.hdr{{padding:24px 20px;}}}}
  /* footer */
  .footer{{text-align:center;color:#94a3b8;font-size:.75rem;margin-top:36px;
    padding-top:16px;border-top:1px solid #e2e8f0;line-height:2.2;}}
  @media print{{body{{background:white;}}.wrap{{padding:10px;}}
    .hdr{{box-shadow:none;}}}}
</style>
</head>
<body>
<div class="wrap">

<!-- ══ HEADER ══ -->
<div class="hdr">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;
    flex-wrap:wrap;gap:20px;position:relative;">
    <div>
      <h1>📋 PDF Compliance Report</h1>
      <div class="meta">
        📄 <strong>{pdf_filename}</strong><br>
        🕒 Generated: {ts}<br>
        ⏱ Scan duration: <strong>{dur_str}</strong>
        &nbsp;·&nbsp; 📑 Pages: <strong>{pa} / {tp}</strong>
        &nbsp;·&nbsp; 📏 Rules: <strong>{len(enabled_rules)}</strong>
        {f'&nbsp;·&nbsp; 🛠 Custom: <strong>{len(custom_rules)}</strong>' if custom_rules else ''}
        &nbsp;·&nbsp; 🤖 Model: <strong>Groq / Llama-3.1-8b-instant</strong>
      </div>
      <div class="risk-pill">{risk_icon} Overall Risk: {overall_risk}</div>
    </div>
    <div style="text-align:center;position:relative;">{gauge_svg}
      <div style="font-size:.68rem;color:rgba(255,255,255,.5);margin-top:-4px;">Compliance Score</div>
    </div>
  </div>
</div>

<!-- ══ EXECUTIVE SUMMARY ══ -->
<div class="exec">
  <strong style="display:block;margin-bottom:6px;font-size:.92rem;color:#0f172a;">
    📌 Executive Summary
  </strong>
  {exec_text}
</div>

<!-- ══ KPI CARDS ══ -->
<div class="grid8">
  <div class="kcard"><div class="val" style="color:#1e293b;">{tp}</div><div class="lbl">Total Pages</div></div>
  <div class="kcard"><div class="val" style="color:#dc2626;">{pv}</div><div class="lbl">Pages Flagged</div></div>
  <div class="kcard"><div class="val" style="color:#16a34a;">{pc}</div><div class="lbl">Pages Clean</div></div>
  <div class="kcard"><div class="val" style="color:#ea580c;">{tv}</div><div class="lbl">Violations</div></div>
  <div class="kcard"><div class="val" style="color:{SC['CRITICAL']};">{sev.get('CRITICAL',0)}</div><div class="lbl">🔴 Critical</div></div>
  <div class="kcard"><div class="val" style="color:{SC['HIGH']};">{sev.get('HIGH',0)}</div><div class="lbl">🟠 High</div></div>
  <div class="kcard"><div class="val" style="color:{SC['MEDIUM']};">{sev.get('MEDIUM',0)}</div><div class="lbl">🟡 Medium</div></div>
  <div class="kcard"><div class="val" style="color:{SC['LOW']};">{sev.get('LOW',0)}</div><div class="lbl">🟢 Low</div></div>
</div>

<!-- ══ SEVERITY + PIPELINE ══ -->
<div class="two-col">
  <div class="sec">
    <div class="sec-title">📊 Severity Distribution</div>
    {sev_html}
  </div>
  <div class="sec">
    <div class="sec-title">🔄 Pipeline Stages</div>
    {timeline_html}
  </div>
</div>

<!-- ══ RULE TABLE ══ -->
<div class="sec">
  <div class="sec-title">📏 Rule-by-Rule Compliance Status</div>
  {rule_tbl}
</div>

<!-- ══ VIOLATION HEATMAP ══ -->
{f'<div class="sec"><div class="sec-title">🔥 Violation Heatmap (Page × Rule)</div>{heatmap_html}</div>' if heatmap_html else ''}

<!-- ══ TOP FINDINGS ══ -->
<div class="sec">
  <div class="sec-title">⚡ Top Findings (ranked by severity)</div>
  {top_find}
</div>

<!-- ══ CLEAN PAGES ══ -->
<div class="sec">
  <div class="sec-title">✅ Clean Pages ({pc})</div>
  {clean_bdg}
</div>

<!-- ══ PAGE VIOLATIONS ══ -->
<div class="sec">
  <div class="sec-title">📄 Page-Level Violation Details ({pv} page(s) flagged)</div>
  {page_det}
</div>

<!-- ══ RECOMMENDATIONS ══ -->
<div class="sec">
  <div class="sec-title">💡 Recommended Remediation Actions</div>
  {recs_html}
</div>

<!-- ══ AUDIT TRAIL ══ -->
<div class="sec">
  <div class="sec-title">🔎 Scan Metadata & Audit Trail</div>
  {audit_html}
</div>

<!-- ══ FOOTER ══ -->
<div class="footer">
  <strong>PDF Compliance Checker</strong> — Automated AI Audit Report<br>
  🤖 <strong>Groq / Llama-3.1-8b-instant</strong>
  &nbsp;·&nbsp; 🔗 <strong>LangGraph</strong> pipeline
  &nbsp;·&nbsp; 📄 <strong>pypdfium2</strong> extraction
  &nbsp;·&nbsp; ✂️ <strong>reportlab</strong> redaction<br>
  Generated: {ts} &nbsp;·&nbsp;
  <em>This report is auto-generated — human review is recommended before action.</em>
</div>

</div>
</body>
</html>"""