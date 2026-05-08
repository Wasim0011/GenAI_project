# 📋 PDF Compliance Checker

An AI-powered PDF compliance scanning pipeline built with **Streamlit**, **LangGraph**, **Gemini AI**, and **PyMuPDF**.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit UI                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │ Upload & Scan│  │   Reports    │  │  Rules Editor  │   │
│  └──────┬───────┘  └──────────────┘  └────────────────┘   │
└─────────┼───────────────────────────────────────────────────┘
          │ PDF file + compliance rules
          ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Pipeline                         │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌───────────┐  ┌────────┐  │
│  │ extract  │──▶│ analyze  │──▶│ aggregate │─▶│ report │  │
│  │(PyMuPDF) │   │(Gemini)  │   │           │  │ (HTML) │  │
│  └──────────┘   └──────────┘   └───────────┘  └────────┘  │
│        │               │                                   │
│        └───────────────┴──── error_handler ───────────────▶│
└─────────────────────────────────────────────────────────────┘
```

### Pipeline Nodes (LangGraph)

| Node | File | Responsibility |
|------|------|----------------|
| `extract` | `core/pdf_extractor.py` | PyMuPDF text extraction, encoding pre-check |
| `analyze` | `core/compliance_analyzer.py` | Gemini AI compliance checks per page |
| `aggregate` | `core/aggregator.py` | Summarise violations, compute risk level |
| `report` | `core/report_generator.py` | Generate downloadable HTML report |
| `error_handler` | `core/pipeline.py` | Catch & surface pipeline errors |

---

## ✅ Compliance Checks

| Check | ID | Severity | Description |
|-------|----|----------|-------------|
| PII Detection | `PII_CHECK` | HIGH | Emails, phones, SSNs, credit cards, DOB, passports |
| Confidential Info | `CONFIDENTIAL_CHECK` | HIGH | API keys, trade secrets, M&A info, internal strategies |
| Encoding Consistency | `ENCODING_CHECK` | MEDIUM | UTF-8 integrity, English-only, mojibake detection |
| Abusive Content | `ABUSIVE_CONTENT_CHECK` | CRITICAL | Hate speech, threats, harassment, illegal instructions |

All rules are configurable via the **Rules Editor** tab in the UI.

---

## 🚀 Quick Start

### 1. Clone and install

```bash
git clone https://github.com/your-org/pdf-compliance-checker
cd pdf-compliance-checker
pip install -r requirements.txt
```

### 2. Set up your Gemini API key

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here
```

Get a free API key at [https://aistudio.google.com](https://aistudio.google.com)

### 3. Generate the sample PDF (optional)

```bash
python generate_sample_pdf.py
```

This creates `sample_pdf/sample_document.pdf` with intentional violations on pages 2, 3, and 5.

### 4. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📁 Project Structure

```
pdf_compliance_checker/
├── app.py                        # Main Streamlit application
├── compliance_rules.json         # Active compliance rules (editable via UI)
├── generate_sample_pdf.py        # Sample test PDF generator
├── requirements.txt
├── .env.example
├── core/
│   ├── __init__.py
│   ├── state.py                  # LangGraph PipelineState TypedDict
│   ├── pdf_extractor.py          # PyMuPDF text extraction node
│   ├── compliance_analyzer.py    # Gemini AI analysis node
│   ├── aggregator.py             # Results aggregation node
│   ├── report_generator.py       # HTML report generation node
│   └── pipeline.py               # LangGraph graph definition & runner
├── utils/
│   ├── __init__.py
│   └── rules_manager.py          # Load/save/reset compliance rules
├── reports/                      # Generated HTML reports (auto-created)
├── sample_pdf/                   # Sample PDFs for testing
└── tests/
    ├── __init__.py
    └── test_pipeline.py          # pytest unit tests
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📊 Sample Report

After scanning, the pipeline produces a detailed HTML report with:
- Overall risk rating (COMPLIANT / LOW / MEDIUM / HIGH / CRITICAL)
- Per-rule pass/fail summary with violated page numbers
- Page-level violation details with specific findings
- Severity distribution breakdown

Reports are saved to the `reports/` directory and downloadable from the UI.

---

## 🔧 Customising Compliance Rules

1. Navigate to the **Rules Editor** tab in the UI
2. Enable/disable any rule with a checkbox
3. Adjust severity levels (CRITICAL / HIGH / MEDIUM / LOW)
4. Edit the rule description to guide the AI's analysis
5. Click **Save Rules** — changes take effect on the next scan

Rules are stored in `compliance_rules.json` and passed into the LangGraph pipeline at runtime.

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI |
| `langgraph` | Pipeline orchestration |
| `langchain-google-genai` | Gemini API integration |
| `pymupdf` | PDF text extraction |
| `reportlab` | Sample PDF generation |
| `python-dotenv` | Environment variable management |

---

## ⚠️ Limitations

- Text-based PDFs only (scanned/image PDFs require OCR — not included)
- Gemini free tier has rate limits; large PDFs (30+ pages) may be slower
- Encoding check is heuristic-based; some edge cases may produce false positives

---

## 📄 License

MIT License. See LICENSE for details.