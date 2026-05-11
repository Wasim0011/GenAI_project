"""
PDF Compliance Checker — Main Streamlit App
Run: streamlit run app.py

API key is loaded exclusively from .env (GROQ_API_KEY).
No API-key field is exposed in the UI.
"""

import os
import tempfile
import time
import json
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

# ── Load secrets from .env (GROQ_API_KEY must live there) ────────────────────
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# ── Page config — must be FIRST Streamlit call ────────────────────────────────
st.set_page_config(
    page_title="PDF Compliance Checker",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Late imports (after page config) ─────────────────────────────────────────
from core.pipeline import run_pipeline
from utils.rules_manager import load_rules, save_rules, reset_rules, create_rule

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] { background:#f0f4f8; }
[data-testid="stSidebar"] { display:none !important; }

.topbar {
    background: linear-gradient(135deg,#0f172a 0%,#1e3a5f 55%,#1e40af 100%);
    padding:28px 36px 22px; border-radius:16px; margin-bottom:24px;
    position:relative; overflow:hidden;
    box-shadow: 0 4px 24px rgba(30,64,175,.35);
}
.topbar::before {
    content:''; position:absolute; top:-70px; right:-70px;
    width:300px; height:300px; background:rgba(255,255,255,.04); border-radius:50%;
}
.topbar h1 { color:#fff; font-size:1.75rem; font-weight:800; letter-spacing:-.02em; margin:0; }
.topbar p  { color:rgba(255,255,255,.6); font-size:.88rem; margin-top:6px; }
.topbar .pills { display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }
.pill {
    display:inline-flex; align-items:center; gap:6px;
    padding:5px 14px; border-radius:999px; font-size:.75rem; font-weight:700;
    background:rgba(255,255,255,.12); color:rgba(255,255,255,.85);
    border:1px solid rgba(255,255,255,.18);
}
[data-testid="stTabs"] [role="tablist"] {
    background:white; border-radius:12px; padding:6px;
    box-shadow:0 1px 4px rgba(0,0,0,.08); border:1px solid #e2e8f0;
    margin-bottom:20px;
}
[data-testid="stTabs"] [role="tab"] {
    border-radius:8px !important; font-weight:600 !important;
    font-size:.88rem !important; padding:8px 18px !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background:linear-gradient(135deg,#1e40af,#3b82f6) !important;
    color:white !important;
}
.kpi-row {
    display:grid; grid-template-columns:repeat(auto-fit,minmax(118px,1fr));
    gap:14px; margin-bottom:24px;
}
.kpi {
    background:white; border-radius:12px; padding:18px 14px; text-align:center;
    border:1px solid #e2e8f0; box-shadow:0 1px 4px rgba(0,0,0,.06);
}
.kpi .v { font-size:1.9rem; font-weight:800; line-height:1; }
.kpi .l { font-size:.67rem; color:#94a3b8; text-transform:uppercase; letter-spacing:.07em; margin-top:5px; }
.sec {
    background:white; border-radius:14px; padding:22px 24px;
    border:1px solid #e2e8f0; box-shadow:0 1px 4px rgba(0,0,0,.06);
    margin-bottom:18px;
}
.sec-head {
    font-size:.92rem; font-weight:800; color:#0f172a;
    border-bottom:2px solid #f1f5f9; padding-bottom:10px; margin-bottom:16px;
}
.viol-item {
    display:flex; align-items:flex-start; gap:10px;
    padding:8px 0; border-bottom:1px solid #f1f5f9; font-size:.85rem;
}
.viol-item:last-child { border-bottom:none; }
.status-ok   { background:#f0fdf4; border-left:4px solid #16a34a; padding:12px 16px; border-radius:8px; }
.status-warn { background:#fffbeb; border-left:4px solid #d97706; padding:12px 16px; border-radius:8px; }
.status-err  { background:#fef2f2; border-left:4px solid #dc2626; padding:12px 16px; border-radius:8px; }
.stButton > button         { border-radius:8px !important; font-weight:600 !important; }
.stDownloadButton > button { border-radius:8px !important; font-weight:600 !important; }
[data-testid="stFileUploader"] {
    border:2px dashed #cbd5e1 !important; border-radius:12px !important;
    background:#f8fafc !important;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TOP BAR
# ═══════════════════════════════════════════════════════════════════════════════
api_ready    = bool(os.environ.get("GROQ_API_KEY", "").strip())
api_status   = "🟢 API Connected" if api_ready else "🔴 GROQ_API_KEY missing in .env"

st.markdown(f"""
<div class="topbar">
  <h1>📋 PDF Compliance Checker</h1>
  <p>AI-powered document compliance scanning · Groq Llama-3.1-8b-instant · LangGraph pipeline · pypdfium2</p>
  <div class="pills">
    <span class="pill">🤖 Groq / Llama-3.1-8b-instant</span>
    <span class="pill">🔗 LangGraph Orchestration</span>
    <span class="pill">📄 pypdfium2 Extraction</span>
    <span class="pill">🛡️ LLM Guardrails Active</span>
    <span class="pill">{api_status}</span>
  </div>
</div>
""", unsafe_allow_html=True)

if not api_ready:
    st.error("⚠️ **GROQ_API_KEY not found.** Add `GROQ_API_KEY=your_key_here` to your `.env` file and restart.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════
tab_scan, tab_reports, tab_rules = st.tabs([
    "Upload & Scan",
    "Reports",
    "Rules Editor",
])

# ═══════════════════════════════════════════════════════════════════════════════
# COLOUR / ICON HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
_SEV_COLOR = {
    "CRITICAL": "#dc2626", "HIGH": "#ea580c",
    "MEDIUM": "#d97706",   "LOW":  "#65a30d",
    "COMPLIANT": "#16a34a",
}
_SEV_ICON = {
    "CRITICAL": "🔴", "HIGH": "🟠",
    "MEDIUM": "🟡",   "LOW":  "🟢",
    "COMPLIANT": "✅",
}
_RULE_ICON = {
    "PII_CHECK": "🔍", "CONFIDENTIAL_CHECK": "🔒",
    "ENCODING_CHECK": "🔤", "ABUSIVE_CONTENT_CHECK": "🚫",
}


def _badge(sev: str) -> str:
    c = _SEV_COLOR.get(sev, "#94a3b8")
    return (f'<span style="background:{c};color:white;padding:2px 10px;'
            f'border-radius:999px;font-size:.7rem;font-weight:800;flex-shrink:0;">{sev}</span>')


# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS RENDERER
# ═══════════════════════════════════════════════════════════════════════════════
def _display_results(state: dict):
    summary      = state.get("summary", {})
    page_results = state.get("page_results", [])
    overall_risk = summary.get("overall_risk", "UNKNOWN")
    score        = summary.get("compliance_score", 0)
    tv           = summary.get("total_violations", 0)
    pv           = summary.get("pages_with_violations", 0)
    tp           = summary.get("total_pages", 0)
    pc           = summary.get("pages_clean", 0)
    sev          = summary.get("severity_counts", {})
    dur          = state.get("scan_duration_seconds")
    rc           = _SEV_COLOR.get(overall_risk, "#6b7280")
    scan_ts      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    st.markdown("---")
    st.markdown("## 📊 Scan Results")

    # ── Risk banner ──────────────────────────────────────────────────────────
    if overall_risk == "COMPLIANT":
        st.success(f"✅ **COMPLIANT** — No violations detected across all {tp} page(s).")
    elif overall_risk == "CRITICAL":
        st.error(f"🔴 **CRITICAL RISK** — Serious violations on {pv} of {tp} page(s). Immediate action required.")
    elif overall_risk == "HIGH":
        st.error(f"🟠 **HIGH RISK** — Significant violations on {pv} page(s). Review before distribution.")
    elif overall_risk == "MEDIUM":
        st.warning(f"🟡 **MEDIUM RISK** — Compliance issues on {pv} page(s). Remediation recommended.")
    else:
        st.warning(f"🟢 **LOW RISK** — Minor issues found. Review advised.")

    # ── KPI row ──────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi"><div class="v" style="color:#1e293b;">{tp}</div><div class="l">Total Pages</div></div>
      <div class="kpi"><div class="v" style="color:#dc2626;">{pv}</div><div class="l">Pages Flagged</div></div>
      <div class="kpi"><div class="v" style="color:#16a34a;">{pc}</div><div class="l">Pages Clean</div></div>
      <div class="kpi"><div class="v" style="color:#ea580c;">{tv}</div><div class="l">Total Violations</div></div>
      <div class="kpi"><div class="v" style="color:{_SEV_COLOR['CRITICAL']};">{sev.get('CRITICAL',0)}</div><div class="l">🔴 Critical</div></div>
      <div class="kpi"><div class="v" style="color:{_SEV_COLOR['HIGH']};">{sev.get('HIGH',0)}</div><div class="l">🟠 High</div></div>
      <div class="kpi"><div class="v" style="color:{_SEV_COLOR['MEDIUM']};">{sev.get('MEDIUM',0)}</div><div class="l">🟡 Medium</div></div>
      <div class="kpi"><div class="v" style="color:{rc};">{score}</div><div class="l">Score /100</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Rule table + Severity breakdown ──────────────────────────────────────
    col_r, col_s = st.columns([3, 2])

    with col_r:
        st.markdown('<div class="sec"><div class="sec-head">📏 Rule-by-Rule Compliance Status</div>', unsafe_allow_html=True)
        import pandas as pd
        rs_data = summary.get("rule_summaries", [])
        if rs_data:
            df = pd.DataFrame([{
                "Rule": rs["rule_name"],
                "Severity": rs["severity"],
                "Status": "✅ PASSED" if rs["passed"] else "❌ FAILED",
                "Violations": rs["violation_count"],
                "Flagged Pages": ", ".join(str(p) for p in rs["violated_pages"]) or "—",
            } for rs in rs_data])
            st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_s:
        st.markdown('<div class="sec"><div class="sec-head">📊 Severity Breakdown</div>', unsafe_allow_html=True)
        total_v = sum(sev.values()) or 1
        for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            n = sev.get(s, 0)
            if n == 0:
                continue
            pct = round(n * 100 / total_v)
            c   = _SEV_COLOR[s]
            st.markdown(f"""
            <div style="margin-bottom:12px;">
              <div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:4px;">
                <span style="font-weight:800;color:{c};">{_SEV_ICON[s]} {s}</span>
                <span style="font-weight:700;">{n}
                  <span style="color:#94a3b8;font-weight:400;">({pct}%)</span>
                </span>
              </div>
              <div style="background:#f1f5f9;border-radius:6px;height:9px;overflow:hidden;">
                <div style="width:{pct}%;background:{c};height:9px;border-radius:6px;"></div>
              </div>
            </div>""", unsafe_allow_html=True)
        if not any(sev.get(s, 0) for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]):
            st.markdown('<p style="color:#64748b;font-size:.85rem;">No violations — all checks passed.</p>',
                        unsafe_allow_html=True)
        if dur:
            st.markdown(
                f'<p style="font-size:.75rem;color:#94a3b8;margin-top:10px;">'
                f'⏱ Scanned in <strong>{dur}s</strong> &nbsp;·&nbsp; {scan_ts}</p>',
                unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Page-level violations ─────────────────────────────────────────────────
    violated_pages_list = [r for r in page_results if r.has_violations]
    clean_pages_list    = [r for r in page_results if not r.has_violations]

    st.markdown(
        f'<div class="sec"><div class="sec-head">'
        f'📄 Page-Level Violation Details ({len(violated_pages_list)} page(s) flagged)'
        f'</div>',
        unsafe_allow_html=True,
    )
    if not violated_pages_list:
        st.success("🎉 All pages passed every enabled compliance rule!")
    else:
        for result in violated_pages_list:
            all_f = (result.pii_flags + result.confidential_flags +
                     result.encoding_flags + result.abusive_flags)
            worst = max(
                (f.get("severity", "LOW") for f in all_f),
                key=lambda s: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(s),
                default="LOW",
            )
            wc = _SEV_COLOR.get(worst, "#64748b")

            with st.expander(
                f"📄 Page {result.page_number}  ·  {len(all_f)} violation(s)  "
                f"·  Worst severity: {worst}",
                expanded=False,
            ):
                for group_label, flags in [
                    ("🔍 PII / Personal Information", result.pii_flags),
                    ("🔒 Confidential Information",   result.confidential_flags),
                    ("🔤 Encoding Issues",            result.encoding_flags),
                    ("🚫 Abusive / Unlawful Content", result.abusive_flags),
                ]:
                    if not flags:
                        continue
                    st.markdown(f"**{group_label}** &nbsp; ({len(flags)} finding(s))")
                    for f in flags:
                        st.markdown(
                            f'<div class="viol-item">{_badge(f.get("severity","MEDIUM"))}'
                            f'<span style="color:#374151;">{f.get("detail","")}</span></div>',
                            unsafe_allow_html=True,
                        )
                    st.markdown("")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Clean pages ───────────────────────────────────────────────────────────
    if clean_pages_list:
        st.markdown('<div class="sec"><div class="sec-head">✅ Clean Pages (no violations)</div>',
                    unsafe_allow_html=True)
        badges = " ".join(
            f'<span style="display:inline-block;background:#f0fdf4;border:1px solid #86efac;'
            f'border-radius:6px;padding:4px 10px;font-size:.78rem;font-weight:700;'
            f'color:#16a34a;margin:3px;">p.{r.page_number}</span>'
            for r in clean_pages_list
        )
        st.markdown(badges, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Recommendations ───────────────────────────────────────────────────────
    rs_data = summary.get("rule_summaries", [])
    failed  = [r for r in rs_data if not r["passed"]]
    if failed:
        st.markdown('<div class="sec"><div class="sec-head">💡 Recommended Remediation Actions</div>',
                    unsafe_allow_html=True)
        recs_map = {
            "PII_CHECK":            "Remove or pseudonymise all PII (emails, phone numbers, SSNs, credit cards, addresses) before distribution.",
            "CONFIDENTIAL_CHECK":   "Redact or remove API keys, passwords, trade secrets, and unreleased business data.",
            "ENCODING_CHECK":       "Re-encode the document as UTF-8 and remove non-English text sections.",
            "ABUSIVE_CONTENT_CHECK":"Review and remove all abusive, discriminatory, or threatening language.",
        }
        for rule in failed:
            rid  = rule["rule_id"]
            rec  = recs_map.get(rid, "Review and remediate the flagged content before distribution.")
            sev  = rule["severity"]
            c    = _SEV_COLOR.get(sev, "#94a3b8")
            pages_str = ", ".join(f"p.{p}" for p in rule["violated_pages"])
            st.markdown(
                f'<div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;'
                f'border-bottom:1px solid #f1f5f9;">'
                f'<span style="background:{c};color:white;border-radius:6px;padding:4px 9px;'
                f'font-size:.72rem;font-weight:800;flex-shrink:0;">{sev}</span>'
                f'<div><strong style="font-size:.88rem;">{rule["rule_name"]}</strong>'
                f'<span style="color:#94a3b8;font-size:.78rem;margin-left:8px;">Pages: {pages_str}</span>'
                f'<br><span style="color:#64748b;font-size:.83rem;">{rec}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.markdown('<div class="sec"><div class="sec-head">📥 Downloads</div>', unsafe_allow_html=True)
    d1, d2, d3 = st.columns(3)

    with d1:
        if state.get("report_html"):
            fname = state.get("pdf_filename", "doc").replace(".pdf", "")
            st.download_button(
                label="⬇️ HTML Compliance Report",
                data=state["report_html"],
                file_name=f"compliance_report_{fname}.html",
                mime="text/html",
                type="primary",
                use_container_width=True,
                key="dl_report_tab1",
            )
        else:
            st.button("🚫 Report N/A", disabled=True, use_container_width=True)

    with d2:
        rpath = state.get("redacted_pdf_path")
        if rpath and Path(rpath).exists():
            with open(rpath, "rb") as f_:
                st.download_button(
                    label="⬇️ Redacted PDF",
                    data=f_.read(),
                    file_name=f"redacted_{state.get('pdf_filename','doc')}",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_redacted_tab1",
                )
        else:
            st.button("🚫 Redacted PDF N/A", disabled=True, use_container_width=True,
                      help="Redacted PDF could not be generated. Check pipeline warnings.")

    with d3:
        summary_export = {
            "scan_metadata": {
                "filename":         state.get("pdf_filename"),
                "scanned_at":       scan_ts,
                "duration_seconds": state.get("scan_duration_seconds"),
                "total_pages":      tp,
                "model":            "groq/llama-3.1-8b-instant",
            },
            "risk_summary": {
                "overall_risk":      overall_risk,
                "compliance_score":  score,
                "total_violations":  tv,
                "pages_flagged":     pv,
                "severity_counts":   sev,
            },
            "rule_results": summary.get("rule_summaries", []),
        }
        st.download_button(
            label="⬇️ JSON Summary",
            data=json.dumps(summary_export, indent=2),
            file_name=f"compliance_summary_{state.get('pdf_filename','doc').replace('.pdf','')}.json",
            mime="application/json",
            use_container_width=True,
            key="dl_json_tab1",
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Warnings ──────────────────────────────────────────────────────────────
    errs = state.get("errors", [])
    if errs:
        with st.expander(f"⚠️ {len(errs)} pipeline warning(s)", expanded=False):
            for e in errs:
                st.warning(e)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — UPLOAD & SCAN
# ═══════════════════════════════════════════════════════════════════════════════
with tab_scan:
    st.markdown("### 📤 Upload a PDF for Compliance Scanning")

    left, right = st.columns([3, 1])

    with left:
        uploaded_file = st.file_uploader(
            "Drop a PDF here or click to browse",
            type=["pdf"],
            help="Text-based PDFs only. Large documents are automatically chunked per page.",
            label_visibility="collapsed",
        )

    with right:
        st.markdown('<div class="sec" style="margin-bottom:0;padding:16px 18px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:.82rem;font-weight:800;color:#0f172a;margin-bottom:8px;">Active checks</div>', unsafe_allow_html=True)
        for r in load_rules():
            if r.get("enabled", True):
                icon = _RULE_ICON.get(r["id"], "📌")
                sev  = r.get("severity", "MEDIUM")
                c    = _SEV_COLOR.get(sev, "#94a3b8")
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:7px;font-size:.8rem;'
                    f'padding:4px 0;border-bottom:1px solid #f1f5f9;">'
                    f'{icon} <span>{r["name"]}</span>'
                    f'<span style="margin-left:auto;background:{c};color:white;padding:1px 7px;'
                    f'border-radius:999px;font-size:.65rem;font-weight:800;">{sev}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.markdown('</div>', unsafe_allow_html=True)

    if uploaded_file:
        file_kb = uploaded_file.size / 1024
        st.markdown(
            f'<div class="status-ok" style="margin-top:12px;">📄 <strong>{uploaded_file.name}</strong>'
            f' &nbsp;·&nbsp; {file_kb:.1f} KB &nbsp;·&nbsp; Ready to scan</div>',
            unsafe_allow_html=True,
        )
        st.markdown("")

        rules_now = load_rules()
        enabled_count = sum(1 for r in rules_now if r.get("enabled", True))
        st.caption(f"ℹ️ {enabled_count} rule(s) active. Manage them in the **Rules Editor** tab.")

        btn_col, _ = st.columns([1, 4])
        with btn_col:
            run_btn = st.button(
                "🚀 Run Compliance Scan",
                type="primary",
                use_container_width=True,
                disabled=not api_ready,
            )

        if run_btn:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            prog       = st.progress(0)
            step_msgs  = [
                (12, "📖 Extracting text from PDF…"),
                (38, "🤖 AI compliance analysis in progress…"),
                (68, "📊 Aggregating page results…"),
                (85, "📝 Generating HTML report…"),
                (95, "✂️ Creating redacted PDF…"),
            ]

            try:
                with st.spinner("Running LangGraph compliance pipeline…"):
                    for pct, msg in step_msgs:
                        prog.progress(pct, text=msg)
                        time.sleep(0.12)

                    final_state = run_pipeline(
                        pdf_path=tmp_path,
                        pdf_filename=uploaded_file.name,
                        compliance_rules=rules_now,
                    )

                prog.progress(100, text="✅ Pipeline complete!")
                time.sleep(0.4)
                prog.empty()

                if final_state.get("status") == "error":
                    st.error("❌ Pipeline encountered an error:")
                    for err in final_state.get("errors", []):
                        st.error(f"  • {err}")
                else:
                    st.session_state["last_result"] = final_state
                    _display_results(final_state)

            except Exception as exc:
                st.error(f"❌ Unexpected error: {exc}")
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    elif "last_result" in st.session_state:
        st.info("💡 Showing last scan result. Upload a new PDF to re-run.")
        _display_results(st.session_state["last_result"])
    else:
        st.markdown("""
        <div style="text-align:center;padding:60px 24px;color:#94a3b8;
          background:white;border-radius:14px;border:1px solid #e2e8f0;margin-top:16px;">
          <div style="font-size:3.5rem;margin-bottom:12px;">📂</div>
          <strong style="font-size:1.1rem;color:#64748b;">Upload a PDF to get started</strong><br>
          <span style="font-size:.88rem;">Supports text-based PDFs up to 200+ pages · Large docs auto-chunked</span>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — REPORTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_reports:
    st.markdown("### 📊 Compliance Report Archive")

    reports_dir = Path("reports")
    html_files  = sorted(reports_dir.glob("*.html"),           reverse=True) if reports_dir.exists() else []
    pdf_files   = sorted(reports_dir.glob("redacted_*.pdf"),   reverse=True) if reports_dir.exists() else []

    if not html_files and not pdf_files:
        st.markdown("""
        <div style="text-align:center;padding:60px 24px;color:#94a3b8;
          background:white;border-radius:14px;border:1px solid #e2e8f0;">
          <div style="font-size:3rem;margin-bottom:10px;">🗂️</div>
          <strong style="color:#64748b;">No reports yet</strong><br>
          <span style="font-size:.85rem;">Run a scan first to generate reports.</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        def _file_row(fpath: Path, dl_label: str, mime: str, key_prefix: str, binary: bool = False):
            stat  = fpath.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            sz    = stat.st_size / 1024
            c1, c2, c3 = st.columns([5, 1, 1])
            with c1:
                st.markdown(
                    f'<div style="padding:10px 14px;background:#f8fafc;border-radius:8px;'
                    f'border:1px solid #e2e8f0;font-size:.84rem;">'
                    f'<strong>{fpath.name}</strong><br>'
                    f'<span style="color:#94a3b8;font-size:.73rem;">{mtime} &nbsp;·&nbsp; {sz:.1f} KB</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with c2:
                if binary:
                    data = fpath.read_bytes()
                else:
                    data = fpath.read_text(encoding="utf-8")
                st.download_button(dl_label, data=data, file_name=fpath.name,
                                   mime=mime, key=f"{key_prefix}_{fpath.name}",
                                   use_container_width=True)
            with c3:
                if st.button("🗑️", key=f"del_{key_prefix}_{fpath.name}", help="Delete"):
                    fpath.unlink()
                    st.rerun()

        if html_files:
            st.markdown(f"#### 📋 HTML Reports ({len(html_files)})")
            for rpt in html_files:
                _file_row(rpt, "⬇️ HTML", "text/html", "h")
            st.markdown("")

        if pdf_files:
            st.markdown(f"#### ✂️ Redacted PDFs ({len(pdf_files)})")
            for rpt in pdf_files:
                _file_row(rpt, "⬇️ PDF", "application/pdf", "p", binary=True)

        st.markdown("---")
        if st.button("🗑️ Clear ALL files", type="secondary"):
            for f_ in list(html_files) + list(pdf_files):
                f_.unlink(missing_ok=True)
            st.success("All reports cleared.")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RULES EDITOR
# ═══════════════════════════════════════════════════════════════════════════════
with tab_rules:
    st.markdown("### ⚙️ Compliance Rules Editor")
    st.caption("Enable/disable rules · Adjust severity & descriptions · Create custom rules · Delete custom rules")

    # Keep rules in session to survive widget re-renders
    if "rules_state" not in st.session_state:
        st.session_state["rules_state"] = load_rules()
    current_rules: list = st.session_state["rules_state"]

    # ── Existing rules ────────────────────────────────────────────────────────
    st.markdown("#### 📋 Active Rules")
    updated_rules  = []
    pending_delete = None

    for i, rule in enumerate(current_rules):
        is_custom   = rule.get("custom", False)
        enabled     = rule.get("enabled", True)
        icon        = _RULE_ICON.get(rule["id"], "📌")
        sev_display = rule.get("severity", "MEDIUM")
        sev_color   = _SEV_COLOR.get(sev_display, "#94a3b8")
        toggle_lbl  = "✅ Enabled" if enabled else "❌ Disabled"
        custom_tag  = " ·`custom`" if is_custom else ""

        with st.expander(
            f"{icon}  {rule['name']}  —  {sev_display}  {toggle_lbl}{custom_tag}",
            expanded=False,
        ):
            lc, rc_ = st.columns([3, 1])
            with lc:
                new_name = st.text_input("Rule Name", value=rule["name"],       key=f"rname_{i}")
                new_desc = st.text_area("Description (guides the AI)",
                                        value=rule["description"], height=88,   key=f"rdesc_{i}")
                new_ex   = st.text_input("Examples (optional)",
                                         value=rule.get("examples", ""),        key=f"rex_{i}")
            with rc_:
                new_en  = st.checkbox("Enabled", value=enabled,                 key=f"ren_{i}")
                new_sev = st.selectbox(
                    "Severity",
                    ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    index=["CRITICAL", "HIGH", "MEDIUM", "LOW"].index(sev_display),
                    key=f"rsev_{i}",
                )
                if is_custom:
                    st.markdown("")
                    if st.button("🗑️ Delete", key=f"delrule_{i}", type="secondary"):
                        pending_delete = i

            updated_rules.append({
                **rule,
                "name":        new_name,
                "description": new_desc,
                "examples":    new_ex,
                "enabled":     new_en,
                "severity":    new_sev,
            })

    if pending_delete is not None:
        updated_rules.pop(pending_delete)
        st.session_state["rules_state"] = updated_rules
        save_rules(updated_rules)
        st.success("Rule deleted.")
        st.rerun()

    st.markdown("")
    s1, s2 = st.columns(2)
    with s1:
        if st.button("💾 Save Changes", type="primary", use_container_width=True):
            st.session_state["rules_state"] = updated_rules
            save_rules(updated_rules)
            st.success("✅ Rules saved! Applied on the next scan.")
    with s2:
        if st.button("↩️ Reset to Defaults", type="secondary", use_container_width=True):
            reset_rules()
            st.session_state["rules_state"] = load_rules()
            st.success("Rules reset to built-in defaults.")
            st.rerun()

    # ── Create new rule ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ➕ Create New Custom Rule")
    st.caption("Custom rules are checked by the AI on every page alongside the built-in rules.")

    with st.form("new_rule_form", clear_on_submit=True):
        nf1, nf2 = st.columns([3, 1])
        with nf1:
            nr_name = st.text_input(
                "Rule Name *",
                placeholder="e.g. Legal Disclaimer Check",
            )
            nr_desc = st.text_area(
                "Description * — tell the AI exactly what to look for",
                placeholder="Flag pages missing the mandatory legal disclaimer in the footer, "
                            "or pages that include forward-looking statements without a disclaimer.",
                height=80,
            )
            nr_ex = st.text_input(
                "Examples (optional)",
                placeholder="'This document does not constitute legal advice', standard disclaimer text",
            )
        with nf2:
            nr_sev = st.selectbox("Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"], index=1)
            nr_en  = st.checkbox("Enable immediately", value=True)

        if st.form_submit_button("➕ Add Custom Rule", type="primary", use_container_width=True):
            if not nr_name.strip() or not nr_desc.strip():
                st.error("Rule Name and Description are both required.")
            else:
                new_r            = create_rule(nr_name, nr_desc, nr_sev, nr_ex)
                new_r["enabled"] = nr_en
                fresh            = load_rules() + [new_r]
                save_rules(fresh)
                st.session_state["rules_state"] = fresh
                st.success(f"✅ Rule **{new_r['name']}** created (ID: `{new_r['id']}`)")
                st.rerun()