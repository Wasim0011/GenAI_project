"""
Unit tests for the PDF compliance pipeline components.
Run: pytest tests/test_pipeline.py -v
"""

import pytest
import tempfile
import os
from pathlib import Path


class TestPDFExtractor:
    """Tests for the PDF text extraction node."""

    def test_extract_empty_state(self):
        """Pipeline should gracefully handle a missing PDF path."""
        from core.pdf_extractor import extract_pdf_text
        state = {
            "pdf_path": "/nonexistent/file.pdf",
            "pdf_filename": "test.pdf",
            "compliance_rules": [],
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
            "progress_message": "",
        }
        result = extract_pdf_text(state)
        assert result["status"] == "error"
        assert result["extraction_error"] is not None

    def test_encoding_detection_replacement_char(self):
        """Encoding detector should flag replacement characters."""
        from core.pdf_extractor import _detect_encoding_issues
        text = "Hello \ufffd world"
        issues = _detect_encoding_issues(text, 1)
        types = [i["type"] for i in issues]
        assert "replacement_character" in types

    def test_encoding_detection_clean_text(self):
        """Clean English text should produce no encoding issues."""
        from core.pdf_extractor import _detect_encoding_issues
        text = "This is a completely clean English sentence with no encoding issues."
        issues = _detect_encoding_issues(text, 1)
        assert len(issues) == 0


class TestAggregator:
    """Tests for the result aggregation node."""

    def test_empty_results_compliant(self):
        """Empty page results should yield COMPLIANT overall risk."""
        from core.aggregator import aggregate_results
        from core.state import PageResult

        state = {
            "pdf_path": "test.pdf",
            "pdf_filename": "test.pdf",
            "compliance_rules": [
                {"id": "PII_CHECK", "name": "PII", "enabled": True, "severity": "HIGH", "description": ""},
            ],
            "pages_text": [],
            "total_pages": 2,
            "extraction_error": None,
            "page_results": [
                PageResult(page_number=1, text_content="Clean text here."),
                PageResult(page_number=2, text_content="Also clean."),
            ],
            "current_page_index": 2,
            "summary": {},
            "violation_counts": {},
            "report_path": None,
            "report_html": None,
            "status": "aggregating",
            "errors": [],
            "progress_message": "",
        }
        result = aggregate_results(state)
        assert result["summary"]["overall_risk"] == "COMPLIANT"
        assert result["summary"]["total_violations"] == 0

    def test_pii_flags_increase_count(self):
        """PII flags on a page should be counted in the summary."""
        from core.aggregator import aggregate_results
        from core.state import PageResult

        page = PageResult(page_number=1, text_content="test")
        page.pii_flags = [
            {"source": "gemini", "severity": "HIGH", "detail": "email found"},
        ]
        page.has_violations = True

        state = {
            "pdf_path": "test.pdf",
            "pdf_filename": "test.pdf",
            "compliance_rules": [
                {"id": "PII_CHECK", "name": "PII", "enabled": True, "severity": "HIGH", "description": ""},
            ],
            "pages_text": [],
            "total_pages": 1,
            "extraction_error": None,
            "page_results": [page],
            "current_page_index": 1,
            "summary": {},
            "violation_counts": {},
            "report_path": None,
            "report_html": None,
            "status": "aggregating",
            "errors": [],
            "progress_message": "",
        }
        result = aggregate_results(state)
        assert result["summary"]["violation_counts"]["PII_CHECK"] == 1
        assert result["summary"]["pages_with_violations"] == 1
        assert result["summary"]["overall_risk"] == "HIGH"


class TestRulesManager:
    """Tests for rules loading and saving."""

    def test_load_default_rules(self, tmp_path, monkeypatch):
        """Should return defaults when rules file is missing."""
        monkeypatch.chdir(tmp_path)
        from utils.rules_manager import load_rules, DEFAULT_RULES
        rules = load_rules()
        assert len(rules) == len(DEFAULT_RULES)
        assert all("id" in r for r in rules)

    def test_save_and_load_rules(self, tmp_path, monkeypatch):
        """Saved rules should be retrievable."""
        monkeypatch.chdir(tmp_path)
        from utils.rules_manager import save_rules, load_rules
        test_rules = [{"id": "TEST", "name": "Test Rule", "enabled": True, "severity": "LOW", "description": "test"}]
        save_rules(test_rules)
        loaded = load_rules()
        assert loaded[0]["id"] == "TEST"


class TestReportGenerator:
    """Tests for HTML report generation."""

    def test_report_contains_filename(self, tmp_path, monkeypatch):
        """Generated HTML report should contain the PDF filename."""
        monkeypatch.chdir(tmp_path)
        from core.report_generator import _build_html_report
        summary = {
            "total_pages": 1,
            "pages_with_violations": 0,
            "total_violations": 0,
            "overall_risk": "COMPLIANT",
            "severity_counts": {},
            "violation_counts": {},
            "violated_pages_by_rule": {},
            "rule_summaries": [],
            "pdf_filename": "my_test.pdf",
        }
        html = _build_html_report(summary, [], "my_test.pdf", [])
        assert "my_test.pdf" in html
        assert "COMPLIANT" in html

    def test_report_shows_violations(self, tmp_path, monkeypatch):
        """Report should list rule violations when they exist."""
        monkeypatch.chdir(tmp_path)
        from core.report_generator import _build_html_report
        from core.state import PageResult

        page = PageResult(page_number=1, text_content="test")
        page.pii_flags = [{"source": "gemini", "severity": "HIGH", "detail": "email: x@y.com"}]
        page.has_violations = True

        summary = {
            "total_pages": 1,
            "pages_with_violations": 1,
            "total_violations": 1,
            "overall_risk": "HIGH",
            "severity_counts": {"HIGH": 1},
            "violation_counts": {"PII_CHECK": 1},
            "violated_pages_by_rule": {"PII_CHECK": [1]},
            "rule_summaries": [{
                "rule_id": "PII_CHECK",
                "rule_name": "PII Detection",
                "severity": "HIGH",
                "enabled": True,
                "violation_count": 1,
                "violated_pages": [1],
                "passed": False,
            }],
            "pdf_filename": "test.pdf",
        }
        html = _build_html_report(summary, [page], "test.pdf", [])
        assert "PII Detection" in html
        assert "FAILED" in html