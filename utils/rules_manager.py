"""
Utility functions for loading, saving, and resetting compliance rules.
"""

import json
import os
from typing import List, Dict, Any
from pathlib import Path

RULES_FILE = Path("compliance_rules.json")

DEFAULT_RULES = [
    {
        "id": "PII_CHECK",
        "name": "PII / Personal Information Detection",
        "description": "Flags pages containing personally identifiable information such as email addresses, phone numbers, SSNs, passport numbers, dates of birth, full names combined with identifiers, credit card numbers, or home addresses.",
        "enabled": True,
        "severity": "HIGH",
        "examples": "john.doe@example.com, +1-800-555-1234, SSN: 123-45-6789",
    },
    {
        "id": "CONFIDENTIAL_CHECK",
        "name": "Confidential / Sensitive Business Information",
        "description": "Flags pages containing confidential business information including trade secrets, internal pricing, unreleased product details, M&A activity, proprietary algorithms, API keys, passwords, or internal strategy documents.",
        "enabled": True,
        "severity": "HIGH",
        "examples": "API_KEY=abc123, Project Codename: Phoenix (confidential), Q3 acquisition target",
    },
    {
        "id": "ENCODING_CHECK",
        "name": "Encoding Consistency (UTF-8 / English Only)",
        "description": "Flags pages where text encoding is inconsistent with UTF-8, or where non-English language content is detected. Only English text is supported.",
        "enabled": True,
        "severity": "MEDIUM",
        "examples": "Garbled characters (â€™), non-Latin scripts, mojibake text",
    },
    {
        "id": "ABUSIVE_CONTENT_CHECK",
        "name": "Abusive / Unlawful Content",
        "description": "Flags pages containing abusive language, hate speech, threats, harassment, discriminatory language, or any content that may be unlawful including instructions for illegal activities.",
        "enabled": True,
        "severity": "CRITICAL",
        "examples": "Slurs, threats, hate speech, instructions for illegal activity",
    },
]


def load_rules() -> List[Dict[str, Any]]:
    """Load rules from JSON file, or return defaults if file is missing/corrupt."""
    try:
        if RULES_FILE.exists():
            with open(RULES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("rules", DEFAULT_RULES)
    except (json.JSONDecodeError, KeyError):
        pass
    return DEFAULT_RULES


def save_rules(rules: List[Dict[str, Any]]) -> None:
    """Persist updated rules to JSON file."""
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump({"rules": rules}, f, indent=2, ensure_ascii=False)


def reset_rules() -> None:
    """Reset rules file to defaults."""
    save_rules(DEFAULT_RULES)