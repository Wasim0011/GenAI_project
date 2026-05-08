"""
LangGraph State definitions for the PDF Compliance Pipeline.
"""

from typing import TypedDict, List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class PageResult:
    """Compliance result for a single PDF page."""
    page_number: int
    text_content: str
    pii_flags: List[Dict[str, Any]] = field(default_factory=list)
    confidential_flags: List[Dict[str, Any]] = field(default_factory=list)
    encoding_flags: List[Dict[str, Any]] = field(default_factory=list)
    abusive_flags: List[Dict[str, Any]] = field(default_factory=list)
    has_violations: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text_content": self.text_content[:500] + "..." if len(self.text_content) > 500 else self.text_content,
            "pii_flags": self.pii_flags,
            "confidential_flags": self.confidential_flags,
            "encoding_flags": self.encoding_flags,
            "abusive_flags": self.abusive_flags,
            "has_violations": self.has_violations,
        }


class PipelineState(TypedDict):
    """Main state object flowing through the LangGraph pipeline."""
    # Input
    pdf_path: str
    pdf_filename: str
    compliance_rules: List[Dict[str, Any]]

    # Extraction phase
    pages_text: List[Dict[str, Any]]   # [{page_number, text, char_count}]
    total_pages: int
    extraction_error: Optional[str]

    # Analysis phase
    page_results: List[PageResult]
    current_page_index: int

    # Aggregation phase
    summary: Dict[str, Any]
    violation_counts: Dict[str, int]

    # Report phase
    report_path: Optional[str]
    report_html: Optional[str]

    # Pipeline status
    status: str   # "pending" | "extracting" | "analyzing" | "aggregating" | "reporting" | "done" | "error"
    errors: List[str]
    progress_message: str