"""
Compliance analysis node using Google Gemini API.
Sends each page's text to Gemini with structured prompts per compliance rule.
"""

import json
import os
import re
import time
from typing import Dict, Any, List
import google.generativeai as genai
from core.state import PipelineState, PageResult


def _get_gemini_client():
    """Initialize Gemini client."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def _build_compliance_prompt(page_text: str, rules: List[Dict[str, Any]]) -> str:
    """Build a structured prompt for Gemini to analyze compliance violations."""
    enabled_rules = [r for r in rules if r.get("enabled", True)]

    rules_text = "\n".join([
        f'- {r["id"]}: {r["description"]}' for r in enabled_rules
    ])

    prompt = f"""You are a compliance auditor AI. Analyze the following text extracted from a PDF page.

COMPLIANCE RULES TO CHECK:
{rules_text}

TEXT FROM PDF PAGE:
\"\"\"
{page_text[:3000]}
\"\"\"

For each rule, determine if there are ANY violations in the text above.

Respond ONLY with a valid JSON object in this exact format (no markdown, no explanation):
{{
  "PII_CHECK": {{
    "violated": true/false,
    "findings": ["specific finding 1", "specific finding 2"]
  }},
  "CONFIDENTIAL_CHECK": {{
    "violated": true/false,
    "findings": ["specific finding 1"]
  }},
  "ENCODING_CHECK": {{
    "violated": true/false,
    "findings": ["specific finding 1"]
  }},
  "ABUSIVE_CONTENT_CHECK": {{
    "violated": true/false,
    "findings": ["specific finding 1"]
  }}
}}

Important rules:
- Only include rule IDs that are being checked: {[r["id"] for r in enabled_rules]}
- For PII_CHECK: Look for emails, phone numbers, SSNs, credit cards, addresses, DOB, passport numbers
- For CONFIDENTIAL_CHECK: Look for API keys, passwords, trade secrets, unreleased products, internal pricing, M&A info
- For ENCODING_CHECK: Look for garbled text, non-English words/sentences, mojibake patterns
- For ABUSIVE_CONTENT_CHECK: Look for hate speech, slurs, threats, harassment, illegal instructions
- findings should be SHORT, specific excerpts or descriptions (max 100 chars each), never reproduce long text
- If no violation, findings should be an empty array []
"""
    return prompt


def analyze_page_compliance(
    page_data: Dict[str, Any],
    rules: List[Dict[str, Any]],
    model,
    retry_count: int = 2,
) -> PageResult:
    """
    Analyze a single page for compliance violations using Gemini.
    Returns a PageResult with all flags populated.
    """
    page_num = page_data["page_number"]
    text = page_data.get("text", "").strip()
    encoding_issues = page_data.get("encoding_issues", [])

    result = PageResult(
        page_number=page_num,
        text_content=text,
    )

    # If page is empty, skip AI analysis
    if not text:
        result.encoding_flags = [{
            "source": "extractor",
            "detail": "Page appears to be empty or contains only images/non-extractable content.",
            "severity": "LOW",
        }] if any(r["id"] == "ENCODING_CHECK" and r.get("enabled") for r in rules) else []
        return result

    # Pre-populate encoding flags from extractor
    if encoding_issues:
        result.encoding_flags = [
            {"source": "extractor", **issue} for issue in encoding_issues
        ]

    # Build prompt and call Gemini
    prompt = _build_compliance_prompt(text, rules)

    for attempt in range(retry_count + 1):
        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()

            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            parsed = json.loads(raw)
            _apply_gemini_findings(result, parsed, rules)
            break

        except json.JSONDecodeError as e:
            if attempt == retry_count:
                result.encoding_flags.append({
                    "source": "pipeline",
                    "detail": f"AI response parse error on page {page_num}: {str(e)}",
                    "severity": "LOW",
                })
        except Exception as e:
            if attempt == retry_count:
                result.pii_flags.append({
                    "source": "pipeline",
                    "detail": f"Gemini API error on page {page_num}: {str(e)}",
                    "severity": "LOW",
                })
            else:
                time.sleep(1.5)  # Brief back-off before retry

    # Determine if page has any violations
    result.has_violations = bool(
        result.pii_flags or result.confidential_flags or
        result.encoding_flags or result.abusive_flags
    )

    return result


def _apply_gemini_findings(
    result: PageResult,
    parsed: Dict[str, Any],
    rules: List[Dict[str, Any]],
) -> None:
    """Apply parsed Gemini JSON findings to the PageResult."""
    rule_map = {r["id"]: r for r in rules}

    for rule_id, data in parsed.items():
        rule = rule_map.get(rule_id, {})
        if not rule.get("enabled", True):
            continue

        violated = data.get("violated", False)
        findings = data.get("findings", [])

        if not violated:
            continue

        flags = [
            {
                "source": "gemini",
                "rule_id": rule_id,
                "rule_name": rule.get("name", rule_id),
                "detail": f,
                "severity": rule.get("severity", "MEDIUM"),
            }
            for f in findings
        ] if findings else [{
            "source": "gemini",
            "rule_id": rule_id,
            "rule_name": rule.get("name", rule_id),
            "detail": f"Violation detected (no specific excerpt provided).",
            "severity": rule.get("severity", "MEDIUM"),
        }]

        if rule_id == "PII_CHECK":
            result.pii_flags.extend(flags)
        elif rule_id == "CONFIDENTIAL_CHECK":
            result.confidential_flags.extend(flags)
        elif rule_id == "ENCODING_CHECK":
            result.encoding_flags.extend(flags)
        elif rule_id == "ABUSIVE_CONTENT_CHECK":
            result.abusive_flags.extend(flags)


def analyze_all_pages(state: PipelineState) -> PipelineState:
    """
    LangGraph node: Run compliance analysis on all extracted pages.
    """
    pages_text = state.get("pages_text", [])
    rules = state.get("compliance_rules", [])
    page_results: List[PageResult] = []
    errors = list(state.get("errors", []))

    try:
        model = _get_gemini_client()
    except ValueError as e:
        return {
            **state,
            "page_results": [],
            "status": "error",
            "errors": errors + [str(e)],
            "progress_message": f"❌ {str(e)}",
        }

    for i, page_data in enumerate(pages_text):
        try:
            result = analyze_page_compliance(page_data, rules, model)
            page_results.append(result)
            # Small delay to respect Gemini rate limits
            if i < len(pages_text) - 1:
                time.sleep(0.3)
        except Exception as e:
            errors.append(f"Page {page_data['page_number']} analysis error: {str(e)}")
            # Add an empty result so page count stays consistent
            page_results.append(PageResult(
                page_number=page_data["page_number"],
                text_content=page_data.get("text", ""),
            ))

    return {
        **state,
        "page_results": page_results,
        "current_page_index": len(page_results),
        "status": "aggregating",
        "errors": errors,
        "progress_message": f"✅ Analyzed {len(page_results)} pages for compliance.",
    }