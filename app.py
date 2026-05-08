"""
PDF Compliance Checker — Main Streamlit App
Entry point: streamlit run app.py
"""

import os
import json
import tempfile
import time
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Load .env for local dev (GEMINI_API_KEY)
load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PDF Compliance Checker",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports after page config ─────────────────────────────────────────────────
from core.pipeline import run_pipeline
from utils.rules_manager import load_rules, save_rules

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 28px 32px;
        border-radius: 12px;
        color: white;
        margin-bottom: 24px;
    }
    .main-header h1 { font-size: 1.9rem; font-weight: 700; margin: 0; }
    .main-header p { opacity: 0.75; margin-top: 6px; font-size: 0.95rem; }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,.08);
        text-align: center;
    }
    .risk-critical { color: #dc2626; font-weight: 700; }
    .risk-high { color: #ea580c; font-weight: 700; }
    .risk-medium { color: #d97706; font-weight: 700; }
    .risk-low { color: #65a30d; font-weight: 700; }
    .risk-compliant { color: #16a34a; font-weight: 700; }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1> PDF Compliance Checker</h1>
    <p>Upload a PDF · Run AI-powered compliance checks · Download a detailed report</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/document--v1.png", width=64)
    st.markdown("### Navigation")
    st.markdown("""
    - 📤 **Upload & Scan** — Upload PDF and run compliance checks
    - 📊 **Reports** — Browse past reports
    - ⚙️ **Rules Editor** — Update compliance rules
    """)

    st.divider()
    st.markdown("### API Configuration")
    api_key_input = st.text_input(
        "Gemini API Key",
        value=os.environ.get("GEMINI_API_KEY", ""),
        type="password",
        help="Get your key at https://aistudio.google.com",
    )
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input
        st.success(" API key set")
    else:
        st.warning(" Enter your Gemini API key to run scans")

    st.divider()
    st.caption("Powered by Gemini AI · LangGraph · PyMuPDF")

# ── Tab layout ────────────────────────────────────────────────────────────────
tab_scan, tab_reports, tab_rules = st.tabs(["📤 Upload & Scan", "📊 Reports", "⚙️ Rules Editor"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Upload & Scan
# ═══════════════════════════════════════════════════════════════════════════════

def _display_results(state: dict):
    """Render compliance results in the UI."""
    summary = state.get("summary", {})
    page_results = state.get("page_results", [])
    overall_risk = summary.get("overall_risk", "UNKNOWN")
    risk_css = f"risk-{overall_risk.lower()}"

    st.markdown("---")
    st.markdown("##  Scan Results")

    # Metric cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Pages", summary.get("total_pages", 0))
    m2.metric("Pages with Violations", summary.get("pages_with_violations", 0))
    m3.metric("Total Violations", summary.get("total_violations", 0))
    m4.metric("Overall Risk", overall_risk)

    # Risk level banner
    risk_colors = {
        "CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡",
        "LOW": "🟢", "COMPLIANT": "✅",
    }
    badge = risk_colors.get(overall_risk, "❓")
    if overall_risk == "COMPLIANT":
        st.success(f" **COMPLIANT** — No violations detected across all pages!")
    elif overall_risk in ("CRITICAL", "HIGH"):
        st.error(f"{badge} **{overall_risk} RISK** — Serious compliance violations found.")
    else:
        st.warning(f"{badge} **{overall_risk} RISK** — Compliance issues found.")

    # Rule summary table
    st.markdown("###  Rule-by-Rule Summary")
    rule_summaries = summary.get("rule_summaries", [])
    if rule_summaries:
        import pandas as pd
        df = pd.DataFrame([{
            "Rule": rs["rule_name"],
            "Severity": rs["severity"],
            "Status": "PASSED" if rs["passed"] else f" FAILED ({rs['violation_count']})",
            "Violated Pages": ", ".join(str(p) for p in rs["violated_pages"]) or "—",
        } for rs in rule_summaries])
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Page-level violations
    violated_pages = [r for r in page_results if r.has_violations]
    if violated_pages:
        st.markdown(f"###  Page-Level Violations ({len(violated_pages)} page(s) flagged)")
        for result in violated_pages:
            with st.expander(f" Page {result.page_number} — {sum([len(result.pii_flags), len(result.confidential_flags), len(result.encoding_flags), len(result.abusive_flags)])} violation(s)", expanded=False):
                if result.pii_flags:
                    st.markdown("** PII / Personal Information**")
                    for f in result.pii_flags:
                        st.markdown(f"- `{f.get('severity','?')}` {f.get('detail','')}")
                if result.confidential_flags:
                    st.markdown("** Confidential Information**")
                    for f in result.confidential_flags:
                        st.markdown(f"- `{f.get('severity','?')}` {f.get('detail','')}")
                if result.encoding_flags:
                    st.markdown("** Encoding Issues**")
                    for f in result.encoding_flags:
                        st.markdown(f"- `{f.get('severity','?')}` {f.get('detail','')}")
                if result.abusive_flags:
                    st.markdown("** Abusive / Unlawful Content**")
                    for f in result.abusive_flags:
                        st.markdown(f"- `{f.get('severity','?')}` {f.get('detail','')}")
    else:
        st.success(" No page-level violations found!")

    # Download report
    if state.get("report_html"):
        st.markdown("---")
        st.markdown("### Download Report")
        st.download_button(
            label=" Download HTML Report",
            data=state["report_html"],
            file_name=f"compliance_report_{state.get('pdf_filename','doc').replace('.pdf','')}.html",
            mime="text/html",
            type="primary",
        )

    # Errors
    if state.get("errors"):
        with st.expander(" Pipeline warnings/errors"):
            for err in state["errors"]:
                st.warning(err)
with tab_scan:
    st.markdown("### Upload a PDF for Compliance Scanning")

    col_upload, col_info = st.columns([2, 1])
    with col_upload:
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            help="Max size: 50 MB. Text-based PDFs only.",
        )

    with col_info:
        st.markdown("""
        **Checks performed:**
        -  PII / Personal Information
        -  Confidential Data
        -  Encoding Consistency (UTF-8 / EN)
        -  Abusive / Unlawful Content
        """)

    if uploaded_file:
        st.success(f" **{uploaded_file.name}** — {uploaded_file.size / 1024:.1f} KB uploaded")

        # Load rules
        rules = load_rules()
        enabled_rules = [r for r in rules if r.get("enabled", True)]
        st.info(f" {len(enabled_rules)} compliance rule(s) enabled. Manage them in the **Rules Editor** tab.")

        col_btn, col_space = st.columns([1, 3])
        with col_btn:
            run_scan = st.button(" Run Compliance Scan", type="primary", use_container_width=True)

        if run_scan:
            if not os.environ.get("GEMINI_API_KEY"):
                st.error(" Please enter your Gemini API Key in the sidebar before scanning.")
            else:
                # Save uploaded PDF to a temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name

                progress_bar = st.progress(0, text="⏳ Starting pipeline...")
                status_placeholder = st.empty()

                try:
                    # Run LangGraph pipeline
                    with st.spinner("Running LangGraph compliance pipeline…"):
                        progress_bar.progress(10, text="⏳ Extracting PDF text...")
                        time.sleep(0.3)

                        final_state = run_pipeline(
                            pdf_path=tmp_path,
                            pdf_filename=uploaded_file.name,
                            compliance_rules=rules,
                        )

                    progress_bar.progress(100, text=" Done!")

                    if final_state.get("status") == "error":
                        st.error(" Pipeline encountered an error:")
                        for err in final_state.get("errors", []):
                            st.error(err)
                    else:
                        # Store in session state for display
                        st.session_state["last_result"] = final_state
                        _display_results(final_state)

                except Exception as e:
                    st.error(f" Unexpected error: {str(e)}")
                finally:
                    os.unlink(tmp_path)

    # Display last result if available
    elif "last_result" in st.session_state:
        st.info(" Showing results from last scan. Upload a new PDF to re-run.")
        _display_results(st.session_state["last_result"])





# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Reports Browser
# ═══════════════════════════════════════════════════════════════════════════════
with tab_reports:
    st.markdown("###  Past Compliance Reports")
    reports_dir = Path("reports")

    if not reports_dir.exists() or not list(reports_dir.glob("*.html")):
        st.info("No reports generated yet. Upload and scan a PDF first.")
    else:
        report_files = sorted(reports_dir.glob("*.html"), reverse=True)
        st.markdown(f"**{len(report_files)} report(s) found:**")

        for rpt in report_files:
            col_name, col_dl = st.columns([4, 1])
            with col_name:
                st.markdown(f" `{rpt.name}`")
            with col_dl:
                with open(rpt, "r", encoding="utf-8") as f:
                    html_content = f.read()
                st.download_button(
                    label=" Download",
                    data=html_content,
                    file_name=rpt.name,
                    mime="text/html",
                    key=f"dl_{rpt.name}",
                )

        st.divider()
        if st.button("🗑️ Clear all reports", type="secondary"):
            for rpt in report_files:
                rpt.unlink()
            st.success("All reports cleared.")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Rules Editor
# ═══════════════════════════════════════════════════════════════════════════════
with tab_rules:
    st.markdown("### ⚙️ Compliance Rules Editor")
    st.info("Enable/disable rules, adjust severity, and customise descriptions. Changes are saved to `compliance_rules.json`.")

    rules = load_rules()
    updated_rules = []
    changed = False

    for i, rule in enumerate(rules):
        with st.expander(f"{'Pass' if rule.get('enabled', True) else 'Fail'} {rule['name']}", expanded=False):
            c1, c2 = st.columns([3, 1])
            with c1:
                new_name = st.text_input("Rule Name", value=rule["name"], key=f"name_{i}")
                new_desc = st.text_area("Description", value=rule["description"], key=f"desc_{i}", height=100)
                new_examples = st.text_input("Examples", value=rule.get("examples", ""), key=f"ex_{i}")
            with c2:
                new_enabled = st.checkbox("Enabled", value=rule.get("enabled", True), key=f"en_{i}")
                new_severity = st.selectbox(
                    "Severity",
                    options=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    index=["CRITICAL", "HIGH", "MEDIUM", "LOW"].index(rule.get("severity", "MEDIUM")),
                    key=f"sev_{i}",
                )

            updated_rule = {
                **rule,
                "name": new_name,
                "description": new_desc,
                "examples": new_examples,
                "enabled": new_enabled,
                "severity": new_severity,
            }
            updated_rules.append(updated_rule)

            if updated_rule != rule:
                changed = True

    st.divider()
    col_save, col_reset = st.columns([1, 1])

    with col_save:
        if st.button(" Save Rules", type="primary", use_container_width=True):
            save_rules(updated_rules)
            st.success("Rules saved successfully!")
            st.rerun()

    with col_reset:
        if st.button("↩Reset to Defaults", type="secondary", use_container_width=True):
            from utils.rules_manager import reset_rules
            reset_rules()
            st.success("Rules reset to defaults.")
            st.rerun()

    st.divider()
    st.markdown("** Raw JSON Preview**")
    st.json(updated_rules)