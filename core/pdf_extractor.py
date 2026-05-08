"""
PDF text extraction node.

Primary engine : pypdfium2  (Chromium's PDF renderer — pre-installed)
Drop-in swap   : PyMuPDF (fitz) — uncomment _extract_with_pymupdf below
                 and change the call in extract_pdf_text if preferred.

Install PyMuPDF on a supported platform:
    pip install pymupdf==1.24.5
Then replace _extract_with_pypdfium2 with _extract_with_pymupdf below.
"""

import pypdfium2 as pdfium
import unicodedata
import re
from typing import Dict, Any, List
from core.state import PipelineState


def extract_pdf_text(state: PipelineState) -> PipelineState:
    """
    LangGraph node: Extract text from all pages of the PDF.
    Populates state['pages_text'] and state['total_pages'].
    """
    pdf_path = state["pdf_path"]

    try:
        pages_data = _extract_with_pypdfium2(pdf_path)
        total_pages = len(pages_data)

        return {
            **state,
            "pages_text": pages_data,
            "total_pages": total_pages,
            "extraction_error": None,
            "status": "analyzing",
            "progress_message": f"✅ Extracted text from {total_pages} pages.",
        }

    except Exception as e:
        return {
            **state,
            "pages_text": [],
            "total_pages": 0,
            "extraction_error": str(e),
            "status": "error",
            "errors": state.get("errors", []) + [f"PDF extraction failed: {str(e)}"],
            "progress_message": f"❌ Extraction error: {str(e)}",
        }


def _extract_with_pypdfium2(pdf_path: str) -> List[Dict[str, Any]]:
    """Extract text page-by-page using pypdfium2."""
    pages_data = []
    doc = pdfium.PdfDocument(pdf_path)
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            encoding_issues = _detect_encoding_issues(text, page_num + 1)
            pages_data.append({
                "page_number": page_num + 1,
                "text": text,
                "char_count": len(text),
                "word_count": len(text.split()),
                "encoding_issues": encoding_issues,
                "width": page.get_width(),
                "height": page.get_height(),
            })
    finally:
        doc.close()
    return pages_data


# ── PyMuPDF alternative ────────────────────────────────────────────────────────
# def _extract_with_pymupdf(pdf_path: str) -> List[Dict[str, Any]]:
#     import fitz
#     pages_data = []
#     doc = fitz.open(pdf_path)
#     try:
#         for page_num in range(len(doc)):
#             page = doc[page_num]
#             text = page.get_text("text")
#             encoding_issues = _detect_encoding_issues(text, page_num + 1)
#             pages_data.append({
#                 "page_number": page_num + 1,
#                 "text": text,
#                 "char_count": len(text),
#                 "word_count": len(text.split()),
#                 "encoding_issues": encoding_issues,
#                 "width": page.rect.width,
#                 "height": page.rect.height,
#             })
#     finally:
#         doc.close()
#     return pages_data


def _detect_encoding_issues(text: str, page_num: int) -> List[Dict[str, Any]]:
    """
    Detect potential UTF-8 encoding inconsistencies and non-English content.
    Returns a list of issue dicts.
    """
    issues = []

    if not text.strip():
        return issues

    # 1. Check for replacement characters (U+FFFD) — common sign of bad decoding
    if "\ufffd" in text:
        count = text.count("\ufffd")
        issues.append({
            "type": "replacement_character",
            "detail": f"Found {count} Unicode replacement character(s) — possible encoding corruption.",
            "severity": "HIGH",
        })

    # 2. Check for non-Latin characters (detect non-English scripts)
    non_latin_chars = []
    for ch in text:
        if ch.isalpha():
            try:
                name = unicodedata.name(ch, "")
                # Allow basic Latin, Latin Extended A/B, common punctuation
                cat = unicodedata.category(ch)
                block = _get_unicode_block(ch)
                if block not in (
                    "Basic Latin",
                    "Latin-1 Supplement",
                    "Latin Extended-A",
                    "Latin Extended-B",
                    "General Punctuation",
                    "Currency Symbols",
                    "Letterlike Symbols",
                ):
                    non_latin_chars.append(ch)
            except Exception:
                pass

    if non_latin_chars:
        unique_foreign = list(set(non_latin_chars))[:10]
        issues.append({
            "type": "non_english_characters",
            "detail": f"Non-Latin/non-English characters detected: {''.join(unique_foreign)}",
            "severity": "MEDIUM",
        })

    # 3. Check for common mojibake patterns (Windows-1252 decoded as Latin-1)
    # Look for sequences of high-codepoint characters that are typical mojibake clusters
    mojibake_pattern = re.compile(
        r"(?:[\u00e2\u00c3][\u0080-\u00bf][\u0080-\u00bf]){2,}"  # 3-byte UTF-8 clusters decoded as Latin-1
        r"|â€™|â€œ|â€\x9d|Ã©|Ã¨|Ã\xa0"  # specific common mojibake sequences
    )
    if mojibake_pattern.search(text):
        issues.append({
            "type": "mojibake",
            "detail": "Possible mojibake (mis-encoded characters) detected — text may have encoding mismatch.",
            "severity": "HIGH",
        })

    return issues


def _get_unicode_block(char: str) -> str:
    """Return approximate Unicode block name for a character."""
    cp = ord(char)
    blocks = [
        (0x0000, 0x007F, "Basic Latin"),
        (0x0080, 0x00FF, "Latin-1 Supplement"),
        (0x0100, 0x017F, "Latin Extended-A"),
        (0x0180, 0x024F, "Latin Extended-B"),
        (0x2000, 0x206F, "General Punctuation"),
        (0x20A0, 0x20CF, "Currency Symbols"),
        (0x2100, 0x214F, "Letterlike Symbols"),
    ]
    for start, end, name in blocks:
        if start <= cp <= end:
            return name
    return "Other"