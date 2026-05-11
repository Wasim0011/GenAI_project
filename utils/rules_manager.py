"""
Utility functions for loading, saving, resetting, and creating compliance rules.
"""

import json
import re
import uuid
from typing import List, Dict, Any
from pathlib import Path

RULES_FILE = Path("compliance_rules.json")

DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "id": "PII_CHECK",
        "name": "PII / Personal Information Detection",
        "description": "Flags pages containing personally identifiable information such as email addresses, phone numbers, SSNs, passport numbers, dates of birth, full names combined with identifiers, credit card numbers, or home addresses.",
        "enabled": True,
        "severity": "HIGH",
        "examples": "john.doe@example.com, +1-800-555-1234, SSN: 123-45-6789",
        "custom": False,
    },
    {
        "id": "CONFIDENTIAL_CHECK",
        "name": "Confidential / Sensitive Business Information",
        "description": "Flags pages containing confidential business information including trade secrets, internal pricing, unreleased product details, M&A activity, proprietary algorithms, API keys, passwords, or internal strategy documents.",
        "enabled": True,
        "severity": "HIGH",
        "examples": "API_KEY=abc123, Project Codename: Phoenix (confidential), Q3 acquisition target",
        "custom": False,
    },
    {
        "id": "ENCODING_CHECK",
        "name": "Encoding Consistency (UTF-8 / English Only)",
        "description": "Flags pages where text encoding is inconsistent with UTF-8, or where non-English language content is detected. Only English text is supported.",
        "enabled": True,
        "severity": "MEDIUM",
        "examples": "Garbled characters (â€™), non-Latin scripts, mojibake text",
        "custom": False,
    },
    {
        "id": "ABUSIVE_CONTENT_CHECK",
        "name": "Abusive / Unlawful Content",
        "description": "Flags pages containing abusive language, hate speech, threats, harassment, discriminatory language, or any content that may be unlawful including instructions for illegal activities.",
        "enabled": True,
        "severity": "CRITICAL",
        "examples": "Slurs, threats, hate speech, instructions for illegal activity",
        "custom": False,
    },
]


def load_rules() -> List[Dict[str, Any]]:
    """Load rules from JSON file, or return defaults if missing/corrupt."""
    try:
        if RULES_FILE.exists():
            data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
            rules = data.get("rules", DEFAULT_RULES)
            for r in rules:
                r.setdefault("custom", True)
            return rules
    except (json.JSONDecodeError, KeyError):
        pass
    return [dict(r) for r in DEFAULT_RULES]


def save_rules(rules: List[Dict[str, Any]]) -> None:
    """Persist rules to JSON file."""
    RULES_FILE.write_text(
        json.dumps({"rules": rules}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def reset_rules() -> None:
    """Reset to built-in defaults."""
    save_rules([dict(r) for r in DEFAULT_RULES])


def create_rule(name: str, description: str, severity: str, examples: str = "") -> Dict[str, Any]:
    """Create a new custom rule dict with a unique generated ID."""
    slug = re.sub(r"[^A-Z0-9]", "_", name.upper())[:24].strip("_")
    uid  = uuid.uuid4().hex[:6].upper()
    return {
        "id":          f"CUSTOM_{slug}_{uid}",
        "name":        name.strip(),
        "description": description.strip(),
        "enabled":     True,
        "severity":    severity,
        "examples":    examples.strip(),
        "custom":      True,
    }