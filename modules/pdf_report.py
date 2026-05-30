from __future__ import annotations
import io
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)

BRAND_PRIMARY = colors.HexColor("#0F4C81")
BRAND_ACCENT = colors.HexColor("#16A085")
BRAND_TEXT = colors.HexColor("#1F2933")
BRAND_MUTED = colors.HexColor("#7F8C8D")
BRAND_LIGHT = colors.HexColor("#F4F6F8")
BRAND_DANGER = colors.HexColor("#C0392B")

ORG_NAME = os.environ.get("ORG_NAME", "Resume Audit")
ORG_TAGLINE = os.environ.get("ORG_TAGLINE", "AI-Powered Resume Audits")
LOGO_PATH = os.environ.get("LOGO_PATH", "assets/logo.png")


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="H1Brand", parent=s["Heading1"],
                         textColor=BRAND_PRIMARY, fontSize=20, leading=24, spaceAfter=6))
    s.add(ParagraphStyle(name="H2Brand", parent=s["Heading2"],
                         textColor=BRAND_TEXT, fontSize=13, leading=17, spaceBefore=10, spaceAfter=4))
    s.add(ParagraphStyle(name="Muted", parent=s["BodyText"],
                         textColor=BRAND_MUTED, fontSize=9, leading=12))
    s.add(ParagraphStyle(name="Body2", parent=s["BodyText"],
                         textColor=BRAND_TEXT, fontSize=10, leading=14, wordWrap="CJK"))
    s.add(ParagraphStyle(name="Body2Small", parent=s["BodyText"],
                         textColor=BRAND_TEXT, fontSize=9, leading=12, wordWrap="CJK"))
    s.add(ParagraphStyle(name="Bullet2", parent=s["BodyText"],
                         textColor=BRAND_TEXT, fontSize=10, leading=14,
                         leftIndent=14, bulletIndent=4, wordWrap="CJK"))
    s.add(ParagraphStyle(name="OrgTitle", parent=s["BodyText"],
                         textColor=BRAND_PRIMARY, fontSize=14, leading=17, alignment=2))
    s.add(ParagraphStyle(name="OrgTagline", parent=s["BodyText"],
                         textColor=BRAND_MUTED, fontSize=9, leading=11, alignment=2))
    return s


def _logo_image(max_w_cm=3.5, max_h_cm=1.5):
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        try:
            return Image(LOGO_PATH, width=max_w_cm * cm, height=max_h_cm * cm, kind="proportional")
        except Exception:
            return None
    return None


def _branded_header(styles, title, subtitle=""):
    logo = _logo_image()
    left = logo if logo else Paragraph("", styles["Body2"])
    right = [
        Paragraph(f"<b>{ORG_NAME}</b>", styles["OrgTitle"]),
        Paragraph(ORG_TAGLINE, styles["OrgTagline"]),
    ]
    header_tbl = Table([[left, right]], colWidths=[8 * cm, 8.4 * cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 1, BRAND_PRIMARY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return [
        header_tbl,
        Spacer(1, 0.35 * cm),
        Paragraph(title, styles["H1Brand"]),
        Paragraph(subtitle or f"Generated on {datetime.now().strftime('%d %b %Y, %H:%M')}",
                  styles["Muted"]),
        Spacer(1, 0.35 * cm),
    ]


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BRAND_MUTED)
    canvas.drawString(1.8 * cm, 1 * cm, f"© {datetime.now().year} {ORG_NAME} · Confidential")
    canvas.drawRightString(doc.pagesize[0] - 1.8 * cm, 1 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _P(text, styles, style="Body2"):
    return Paragraph(str(text) if text is not None else "—", styles[style])


def _kv_table(rows, styles):
    data = [[_P(f"<b>{k}</b>", styles), _P(v, styles)] for k, v in rows]
    t = Table(data, colWidths=[5 * cm, 11.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BRAND_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E8EB")),
    ]))
    return t


def _bullets(items, styles):
    out = []
    for it in (items or []):
        out.append(Paragraph(f"• {it}", styles["Bullet2"]))
    if not items:
        out.append(Paragraph("—", styles["Body2"]))
    return out


def _checklist_table(items, styles, score_label=""):
    header = [_P("<b>Check</b>", styles), _P("<b>Status</b>", styles), _P("<b>Note</b>", styles)]
    rows = [header]
    for it in items:
        status_color = BRAND_ACCENT if it["passed"] else BRAND_DANGER
        status_label = "PASS" if it["passed"] else "FAIL"
        rows.append([
            _P(it["item"], styles),
            Paragraph(f"<font color='{status_color.hexval()}'><b>{status_label}</b></font>",
                      styles["Body2"]),
            _P(it.get("note", "") or "—", styles, "Body2Small"),
        ])
    t = Table(rows, colWidths=[7 * cm, 2 * cm, 7.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E8EB")),
    ]))
    return t


def _doc(buf, title):
    return SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.6 * cm, bottomMargin=1.8 * cm,
        title=title,
    )


def build_single_pdf(audit, chart_pngs, format_check=None):
    buf = io.BytesIO()
    doc = _doc(buf, f"Resume Audit — {audit.get('candidate_name','Candidate')}")
    styles = _styles()
    story = []
    
    # Defensive programming: Ensure chart_pngs is always a dictionary object
    if not isinstance(chart_pngs, dict):
        chart_pngs = {}

    name = audit.get("candidate_name", "Candidate")
    story += _branded_header(styles, "Resume Audit Report", f"Candidate: {name}")

    story.append(_kv_table([
        ("Candidate", name),
        ("Headline", audit.get("headline", "—")),
        ("Verdict", audit.get("verdict", "—")),
        ("Overall Score", f"{audit.get('overall_score', 0)} / 100"),
        ("ATS Score", f"{audit.get('ats_score', 0)} / 100"),
        ("JD Match Score", f"{audit.get('jd_match_score', 0)} / 100"),
        ("Quality Score", f"{audit.get('quality_score', 0)} / 100"),
        ("Experience Score", f"{audit.get('experience_score', 0)} / 100"),
        ("Org-Standard Score", f"{audit.get('org_standard_score', 0)} / 100"),
        ("Total Experience", f"{audit.get('total_experience_years', 0)} years"),
        ("Seniority Fit", audit.get("seniority_fit", "—")),
    ], styles))
    story.append(Spacer(1, 0.4 * cm))

    if chart_pngs.get("gauge") and chart_pngs.get("radar"):
        row = Table([[Image(io.BytesIO(chart_pngs["gauge"]), width=7.5 * cm, height=4.7 * cm),
                      Image(io.BytesIO(chart_pngs["radar"]), width=7.5 * cm, height=4.7 * cm)]],
                    colWidths=[8.2 * cm, 8.2 * cm])
        story.append(row)
        story.append(Spacer(1, 0.3 * cm))
    if chart_pngs.get("donut"):
        story.append(Image(io.BytesIO(chart_pngs["donut"]), width=15 * cm, height=6.5 * cm))
        story.append(Spacer(1, 0.3 * cm))

    skills = audit.get("skills") or {}
    story.append(Paragraph("Skills Analysis", styles["H2Brand"]))
    skill_data = [
        [_P("<b>Matched</b>", styles), _P("<b>Missing</b>", styles), _P("<b>Additional</b>", styles)],
        [_P(", ".join(skills.get("matched") or []) or "—", styles),
         _P(", ".join(skills.get("missing") or []) or "—", styles),
         _P(", ".join(skills.get("additional") or []) or "—", styles)],
    ]
    skill_t = Table(skill_data, colWidths=[5.4 * cm, 5.4 * cm, 5.4 * cm])
    skill_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E8EB")),
    ]))
    story.append(skill_t)
    story.append(Spacer(1, 0.4 * cm))

    if format_check:
        story.append(Paragraph(
            f"Org Format Compliance — {format_check['passed']}/{format_check['total']} passed "
            f"({format_check['score']}%)", styles["H2Brand"]))
        story.append(_checklist_table(format_check["items"], styles))
        story.append(Spacer(1, 0.3 * cm))

    sec = audit.get("section_compliance") or []
    if sec:
        story.append(Paragraph("Section-by-Section Review (AI)", styles["H2Brand"]))
        items = [{"item": s.get("section", "—"),
                  "passed": bool(s.get("passed")),
                  "note": s.get("note", "")} for s in sec]
        story.append(_checklist_table(items, styles))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Strengths", styles["H2Brand"]))
    story += _bullets(audit.get("strengths"), styles)
    story.append(Paragraph("Weaknesses", styles["H2Brand"]))
    story += _bullets(audit.get("weaknesses"), styles)
    story.append(Paragraph("Red Flags", styles["H2Brand"]))
    story += _bullets(audit.get("red_flags"), styles)
    story.append(Paragraph("Recommendations", styles["H2Brand"]))
    story += _bullets(audit.get("recommendations"), styles)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def build_bulk_pdf(audits, chart_pngs, format_checks=None) -> dict[str, bytes]:
    """
    Generates a collection of separate, individual report data packets.
    Returns:
        dict: A lookup table where:
            - key "SUMMARY_OVERVIEW": Master ranking analytics file bytes.
            - key "[Candidate Name]": Individual comprehensive score sheet data bytes.
    """
    format_checks = format_checks or [None] * len(audits)
    pdf_output_collection = {}
    styles = _styles()

    # -------------------------------------------------------------------------
    # PART A: GENERATE SEPARATE MASTER SUMMARY REPORT FIRST
    # -------------------------------------------------------------------------
    summary_buf = io.BytesIO()
    summary_doc = _doc(summary_buf, "Bulk Overview Analytics Master Summary")
    summary_story = []
    
    summary_story += _branded_header(
        styles, "Bulk Resume Audit Report",
        f"{len(audits)} candidates · Generated on {datetime.now().strftime('%d %b %Y, %H:%M')}"
    )

    if chart_pngs and isinstance(chart_pngs, dict):
        if chart_pngs.get("ranking"):
            summary_story.append(Image(io.BytesIO(chart_pngs["ranking"]), width=15 * cm, height=7.5 * cm))
            summary_story.append(Spacer(1, 0.3 * cm))
        if chart_pngs.get("histogram"):
            summary_story.append(Image(io.BytesIO(chart_pngs["histogram"]), width=15 * cm, height=5.6 * cm))
            summary_story.append(Spacer(1, 0.3 * cm))

    # Construct overall candidate placement dynamic index table
    header = [_P(f"<b>{h}</b>", styles) for h in ["#", "Candidate", "Overall", "JD", "Exp", "Quality", "Verdict"]]
    rows = [header]
    paired = sorted(zip(audits, format_checks), key=lambda p: p[0].get("overall_score", 0), reverse=True)
    
    for i, (a, _) in enumerate(paired, 1):
        rows.append([
            _P(str(i), styles),
            _P(a.get("candidate_name", "—"), styles),
            _P(a.get("overall_score", 0), styles),
            _P(a.get("jd_match_score", 0), styles),
            _P(a.get("experience_score", 0), styles),
            _P(a.get("quality_score", 0), styles),
            _P(a.get("verdict", "—"), styles, "Body2Small"),
        ])
        
    summary_table = Table(rows, colWidths=[0.9 * cm, 5 * cm, 1.7 * cm, 1.3 * cm, 1.3 * cm, 1.7 * cm, 4.5 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (5, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E8EB")),
    ]))
    summary_story.append(summary_table)
    
    summary_doc.build(summary_story, onFirstPage=_footer, onLaterPages=_footer)
    pdf_output_collection["SUMMARY_OVERVIEW"] = summary_buf.getvalue()

    # -------------------------------------------------------------------------
    # PART B: GENERATE INDEPENDENT FILES FOR EACH UNIQUE RESUME
    # -------------------------------------------------------------------------
    # Cross-Environment safe import pattern for Cloud vs Local Servers
    try:
        import charts
    except ImportError:
        from modules import charts

    for a, fc in paired:
        candidate_name = a.get("candidate_name", "Unknown_Candidate").strip().replace(" ", "_")
        skills = a.get("skills") or {}
        
        # Build individual chart visuals for each candidate sheet on the fly safely
        indiv_charts = {}
        try:
            indiv_charts["gauge"] = charts.fig_to_png_bytes(charts.gauge(a.get("overall_score", 0)))
            indiv_charts["radar"] = charts.fig_to_png_bytes(charts.radar({
                "ATS": a.get("ats_score", 0),
                "Quality": a.get("quality_score", 0),
                "JD Match": a.get("jd_match_score", 0),
                "Experience": a.get("experience_score", 0),
                "Overall": a.get("overall_score", 0),
            }))
            indiv_charts["donut"] = charts.fig_to_png_bytes(
                charts.donut_skills(skills.get("matched"), skills.get("missing"), skills.get("additional")),
                width=900, height=380,
            )
        except Exception:
            # Fallback to empty dict to keep code robust if an individual generation error happens
            indiv_charts = {}

        # Safely pass the individual metrics along to build the candidate report
        pdf_output_collection[candidate_name] = build_single_pdf(a, indiv_charts, format_check=fc)

    return pdf_output_collection


def build_compare_pdf(comparison, chart_pngs):
    buf = io.BytesIO()
    doc = _doc(buf, "Candidate Comparison Report")
    styles = _styles()
    story = []
    story += _branded_header(styles, "Candidate Comparison Report")
    story.append(_kv_table([
        ("Winner", comparison.get("winner", "—")),
        ("Why", comparison.get("why_winner", "—")),
    ], styles))
    story.append(Spacer(1, 0.3 * cm))
    
    if chart_pngs and isinstance(chart_pngs, dict):
        if chart_pngs.get("bar"):
            story.append(Image(io.BytesIO(chart_pngs["bar"]), width=15 * cm, height=7.5 * cm))
            story.append(Spacer(1, 0.3 * cm))
        if chart_pngs.get("ranking"):
            story.append(Image(io.BytesIO(chart_pngs["ranking"]), width=15 * cm, height=6.5 * cm))
            story.append(Spacer(1, 0.3 * cm))

    header = [_P(f"<b>{h}</b>", styles) for h in ["Rank", "Candidate", "Overall", "JD", "Exp", "Quality", "Verdict"]]
    rows = [header]
    ranking = sorted(comparison.get("ranking") or [], key=lambda r: r.get("rank", 999))
    for r in ranking:
        rows.append([
            _P(r.get("rank", "—"), styles),
            _P(r.get("candidate_name", "—"), styles),
            _P(r.get("overall_score", 0), styles),
            _P(r.get("jd_match_score", 0), styles),
            _P(r.get("experience_score", 0), styles),
            _P(r.get("quality_score", 0), styles),
            _P(r.get("verdict", "—"), styles, "Body2Small"),
        ])
    t = Table(rows, colWidths=[1.2 * cm, 5 * cm, 1.7 * cm, 1.3 * cm, 1.3 * cm, 1.7 * cm, 4.2 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E8EB")),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Executive Summary", styles["H2Brand"]))
    story.append(Paragraph(str(comparison.get("comparison_summary", "—")), styles["Body2"]))
    story.append(Spacer(1, 0.3 * cm))
    for r in ranking:
        story.append(Paragraph(f"#{r.get('rank','—')} · {r.get('candidate_name','—')}", styles["H2Brand"]))
        story.append(Paragraph(f"<b>Verdict:</b> {r.get('verdict','—')}", styles["Body2"]))
        story.append(Paragraph("<b>Key Strengths</b>", styles["Body2"]))
        story += _bullets(r.get("key_strengths"), styles)
        story.append(Paragraph("<b>Key Gaps</b>", styles["Body2"]))
        story += _bullets(r.get("key_gaps"), styles)
        story.append(Spacer(1, 0.2 * cm))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()