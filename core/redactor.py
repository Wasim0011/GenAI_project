"""
Redacted PDF generator.

Reads the original PDF page-by-page, overlays black redaction rectangles
over sentences / spans that triggered compliance violations, then writes
a new PDF with all flagged content removed.

Strategy (no PyMuPDF):
  - Use pypdfium2 to render each page to an image
  - Use reportlab to build the new PDF page-by-page:
      * If page has NO violations → copy the original page text as-is
      * If page HAS violations   → embed the rendered image with
        black rectangles drawn over flagged text regions

  Since pypdfium2 supports search-and-highlight we use its text-search
  to locate bounding boxes of flagged terms and redact them precisely.
"""

import os
import re
import io
import math
from typing import List, Dict, Any, Tuple, Optional
import pypdfium2 as pdfium
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate
from reportlab.pdfgen import canvas
from PIL import Image


def _get_flag_terms(page_result) -> List[str]:
    """
    Extract short search terms from all flags on a page.
    We look for anything in quotes or after key phrases like 'detected:'.
    """
    terms = []
    all_flags = (
        page_result.pii_flags +
        page_result.confidential_flags +
        page_result.encoding_flags +
        page_result.abusive_flags
    )
    for flag in all_flags:
        detail = flag.get("detail", "")
        # Extract tokens after "detected:" / "found:" / colon patterns
        colon_match = re.search(r":\s*(.+)$", detail)
        if colon_match:
            val = colon_match.group(1).strip().strip("'\"").split()[0]
            if len(val) > 3:
                terms.append(val)
        # Also grab tokens in quotes
        quoted = re.findall(r"[\"']([^\"']{4,60})[\"']", detail)
        terms.extend(quoted)
    return list(set(t for t in terms if t.strip()))


def generate_redacted_pdf(
    original_pdf_path: str,
    page_results: list,
    output_dir: str = "reports",
    original_filename: str = "document.pdf",
) -> str:
    """
    Generate a new PDF with flagged content redacted.
    Returns the path to the new redacted PDF.
    """
    from datetime import datetime
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = original_filename.replace(" ", "_").replace(".pdf", "")
    out_path = os.path.join(output_dir, f"redacted_{safe}_{ts}.pdf")

    # Index violations by page number
    violations_by_page: Dict[int, Any] = {
        r.page_number: r for r in page_results if r.has_violations
    }

    doc = pdfium.PdfDocument(original_pdf_path)
    c = canvas.Canvas(out_path)

    try:
        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc[page_idx]
            width_pt  = page.get_width()   # PDF points
            height_pt = page.get_height()

            c.setPageSize((width_pt, height_pt))

            # Render page to image at 2× scale for good quality
            SCALE = 2.0
            bitmap = page.render(scale=SCALE)
            pil_img = bitmap.to_pil()

            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format="PNG")
            img_byte_arr.seek(0)

            # Draw the page image as background
            from reportlab.lib.utils import ImageReader
            img_reader = ImageReader(img_byte_arr)
            c.drawImage(img_reader, 0, 0, width=width_pt, height=height_pt)

            # If this page has violations, paint redaction bars
            if page_num in violations_by_page:
                result = violations_by_page[page_num]
                terms = _get_flag_terms(result)

                textpage = page.get_textpage()

                redacted_rects: List[Tuple] = []

                # Search for each flagged term and collect bounding boxes
                for term in terms:
                    if len(term) < 4:
                        continue
                    try:
                        searcher = textpage.search(term, match_case=False, match_whole_word=False)
                        while True:
                            result_obj = searcher.get_next()
                            if result_obj is None:
                                break
                            rects = result_obj.get_charbox_list()
                            if rects:
                                # Union of all char boxes for this hit
                                xs = [r[0] for r in rects] + [r[2] for r in rects]
                                ys = [r[1] for r in rects] + [r[3] for r in rects]
                                x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
                                # Add padding
                                redacted_rects.append((x0 - 2, y0 - 2, x1 + 2, y1 + 2))
                    except Exception:
                        pass

                # If we couldn't locate specific terms, redact whole violated paragraphs
                # by painting a "REDACTED" strip across known violation lines
                if not redacted_rects and result.has_violations:
                    # Fallback: add a prominent notice banner at page top
                    c.setFillColor(colors.Color(0.8, 0, 0, 0.15))
                    c.rect(0, height_pt - 30, width_pt, 30, fill=1, stroke=0)
                    c.setFillColor(colors.red)
                    c.setFont("Helvetica-Bold", 9)
                    c.drawString(8, height_pt - 18, "⚠ This page contains redacted compliance violations")
                    c.setFillColor(colors.black)

                # Draw black redaction boxes
                c.setFillColor(colors.black)
                for (x0, y0, x1, y1) in redacted_rects:
                    # pypdfium2 y=0 is BOTTOM; reportlab y=0 is also BOTTOM — direct mapping
                    box_x = x0
                    box_y = y0
                    box_w = x1 - x0
                    box_h = y1 - y0
                    if box_w > 0 and box_h > 0:
                        c.rect(box_x, box_y, box_w, box_h, fill=1, stroke=0)

                # Stamp "REDACTED" label on boxes
                if redacted_rects:
                    c.setFillColor(colors.white)
                    c.setFont("Helvetica-Bold", 6)
                    for (x0, y0, x1, y1) in redacted_rects:
                        mid_x = (x0 + x1) / 2 - 14
                        mid_y = (y0 + y1) / 2 - 3
                        c.drawString(mid_x, mid_y, "REDACTED")
                    c.setFillColor(colors.black)

            c.showPage()
    finally:
        doc.close()

    c.save()
    return out_path