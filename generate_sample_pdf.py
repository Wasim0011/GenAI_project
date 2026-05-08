"""
Generates a sample PDF with intentional compliance violations for testing.
Run: python generate_sample_pdf.py
"""

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import os

os.makedirs("sample_pdf", exist_ok=True)


def create_sample_pdf(output_path="sample_pdf/sample_document.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=20,
        textColor=colors.HexColor("#1e293b"),
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#334155"),
    )
    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=11,
        leading=16,
        spaceAfter=10,
    )

    story = []

    # ── PAGE 1: Clean page ─────────────────────────────────────────────────────
    story.append(Paragraph("TechCorp Internal Document Repository", title_style))
    story.append(Paragraph("Annual Process Documentation 2024", heading_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "This document contains a summary of internal processes, employee guidelines, "
        "and company policies for the fiscal year 2024. It is intended for internal use "
        "only and should not be distributed externally without written approval from the "
        "Legal and Compliance department.",
        body_style,
    ))
    story.append(Paragraph(
        "All employees are expected to review this document and acknowledge compliance "
        "with the outlined policies by the end of Q1 2024.",
        body_style,
    ))
    story.append(PageBreak())

    # ── PAGE 2: PII Violations ────────────────────────────────────────────────
    story.append(Paragraph("Employee Contact Directory", heading_style))
    story.append(Paragraph(
        "The following is a list of key personnel and their contact information "
        "for internal reference only:",
        body_style,
    ))
    story.append(Paragraph(
        "John Smith — Engineering Lead<br/>"
        "Email: john.smith@techcorp-internal.com<br/>"
        "Phone: +1 (415) 555-0192<br/>"
        "SSN: 123-45-6789<br/>"
        "Date of Birth: March 14, 1985<br/>"
        "Home Address: 4821 Maple Avenue, San Francisco, CA 94102",
        body_style,
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Sarah Johnson — HR Director<br/>"
        "Email: s.johnson@techcorp-internal.com<br/>"
        "Phone: (650) 555-7834<br/>"
        "Passport No: US-789456123<br/>"
        "Credit Card: 4111 1111 1111 1111 (Exp: 12/26, CVV: 344)",
        body_style,
    ))
    story.append(PageBreak())

    # ── PAGE 3: Confidential Info ─────────────────────────────────────────────
    story.append(Paragraph("Project Phoenix — Strictly Confidential", heading_style))
    story.append(Paragraph(
        "CONFIDENTIAL — DO NOT DISTRIBUTE. This section contains proprietary "
        "trade secret information and unreleased product details.",
        body_style,
    ))
    story.append(Paragraph(
        "Q4 2024 Acquisition Target: MegaSoft Inc. (valuation: $2.3B). "
        "Preliminary due diligence has been completed. Board approval pending. "
        "Code name: Operation Bluebird. Legal team contact: legal-secret@techcorp.com",
        body_style,
    ))
    story.append(Paragraph(
        "Internal API Keys and Infrastructure:",
        body_style,
    ))
    story.append(Paragraph(
        "Production DB Password: Tr0ub4dor&3_Prod<br/>"
        "AWS Access Key ID: AKIAIOSFODNN7EXAMPLE<br/>"
        "AWS Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY<br/>"
        "Stripe Secret Key: sk_test_PLACEHOLDER",
        body_style,
    ))
    story.append(PageBreak())

    # ── PAGE 4: Clean process documentation ───────────────────────────────────
    story.append(Paragraph("Standard Operating Procedures", heading_style))
    story.append(Paragraph(
        "Section 3.2 — Code Review Process",
        body_style,
    ))
    story.append(Paragraph(
        "All code changes must be reviewed by at least two senior engineers before "
        "merging into the main branch. Pull requests should include a description of "
        "changes, testing steps, and references to related tickets.",
        body_style,
    ))
    story.append(Paragraph(
        "Section 3.3 — Incident Response",
        body_style,
    ))
    story.append(Paragraph(
        "In case of a production incident, the on-call engineer must acknowledge the "
        "alert within 5 minutes. A postmortem must be filed within 48 hours of resolution. "
        "All incidents are logged in the internal incident tracker.",
        body_style,
    ))
    story.append(PageBreak())

    # ── PAGE 5: Abusive content ────────────────────────────────────────────────
    story.append(Paragraph("Anonymous Feedback (Unmoderated Dump — For Review)", heading_style))
    story.append(Paragraph(
        "The following feedback was collected anonymously and has NOT been moderated. "
        "This content requires compliance review before archival.",
        body_style,
    ))
    story.append(Paragraph(
        "Feedback #1: I hate working with the idiot in the compliance team. "
        "He is a complete moron and should be fired immediately. This company is run by incompetent fools.",
        body_style,
    ))
    story.append(Paragraph(
        "Feedback #2: The manager is a racist piece of garbage. "
        "Nobody from that community should be in leadership roles.",
        body_style,
    ))
    story.append(Paragraph(
        "Feedback #3: I know how to make the security system fail. "
        "If they dont fix my salary I will leak all user data to competitors.",
        body_style,
    ))
    story.append(PageBreak())

    # ── PAGE 6: Mostly clean with minor encoding hint ─────────────────────────
    story.append(Paragraph("Appendix A — Glossary", heading_style))
    story.append(Paragraph(
        "API — Application Programming Interface: A set of rules that allows "
        "different software applications to communicate with each other.",
        body_style,
    ))
    story.append(Paragraph(
        "CI/CD — Continuous Integration/Continuous Deployment: A method to frequently "
        "deliver apps to customers by introducing automation into the stages of app development.",
        body_style,
    ))
    story.append(Paragraph(
        "SLA — Service Level Agreement: A contract between a service provider and the "
        "end user that defines the level of service expected from the service provider.",
        body_style,
    ))
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Document version: 2024.1.0 | Classification: INTERNAL | Owner: Compliance Team",
        styles["Normal"],
    ))

    doc.build(story)
    print(f"Sample PDF created: {output_path}")
    return output_path


if __name__ == "__main__":
    create_sample_pdf()