from __future__ import annotations
import io
import os
import sys

# --- FIX FOR STREAMLIT CLOUD PATH ENGINE CONFLICT ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)
# ----------------------------------------------------

from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)

# Professional Corporate Palette
BRAND_PRIMARY = colors.HexColor("#0F4C81")   # Deep Corporate Navy
BRAND_ACCENT = colors.HexColor("#16A085")    # Mint Teal Success
BRAND_TEXT = colors.HexColor("#1F2933")      # Midnight Charcoal
BRAND_MUTED = colors.HexColor("#7F8C8D")     # Cool Slate Gray
BRAND_LIGHT = colors.HexColor("#F8FAFC")     # Ultra-light background tint
BRAND_DANGER = colors.HexColor("#C0392B")    # Crimson Warning

ORG_NAME = os.environ.get("ORG_NAME", "Resume Audit")
ORG_TAGLINE = os.environ.get("ORG_TAGLINE", "AI-Powered Resume Audits")
LOGO_PATH = os.environ.get("LOGO_PATH", "assets/logo.png")


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas renderer to dynamically inject high-end corporate 
    headers/footers and accurate "Page X of Y" pagination.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(BRAND_MUTED)
        
        # Render clean consistent legal/confidential footer
        self.drawString(1.8 * cm, 1 * cm, f"© {datetime.now().year} {ORG_NAME} · Confidential Audit Report")
        
        # Render dynamic precise pagination
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(self._pagesize[0] - 1.8 * cm, 1 * cm, page_text)
        self.restoreState()


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="H1Brand", parent=s["Heading1"],
                         textColor=BRAND_PRIMARY, fontName="Helvetica-Bold", fontSize=20, leading=24, spaceAfter=6))
    s.add(ParagraphStyle(name="H2Brand", parent=s["Heading2"],
                         textColor=BRAND_PRIMARY, fontName="Helvetica-Bold", fontSize=13, leading=17, spaceBefore=14, spaceAfter=6))
    s.add(ParagraphStyle(name="Muted", parent=s["BodyText"],
                         textColor=BRAND_MUTED, fontSize=9, leading=12))
    s.add(ParagraphStyle(name="Body2", parent=s["BodyText"],
                         textColor=BRAND_TEXT, fontSize=10, leading=14, wordWrap="CJK"))
    s.add(ParagraphStyle(name="Body2Small", parent=s["BodyText"],
                         textColor=BRAND_TEXT, fontSize=9, leading=13, wordWrap="CJK"))
    s.add(ParagraphStyle(name="TableHeader", parent=s["BodyText"],
                         textColor=colors.white, fontName="Helvetica-Bold", fontSize=10, leading=14, wordWrap="CJK"))
    s.add(ParagraphStyle(name="Bullet2", parent=s["BodyText"],
                         textColor=BRAND_TEXT, fontSize=10, leading=14,
                         leftIndent=14, bulletIndent=4, wordWrap="CJK"))
    s.add(ParagraphStyle(name="OrgTitle", parent=s["BodyText"],
                         textColor=BRAND_PRIMARY, fontName="Helvetica-Bold", fontSize=14, leading=17, alignment=2))
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
    # Standardized to exactly 17.4 cm full page width
    header_tbl = Table([[left, right]], colWidths=[8.5 * cm, 8.9 * cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.2, BRAND_PRIMARY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return [
        header_tbl,
        Spacer(1, 0.35 * cm),
        Paragraph(title, styles["H1Brand"]),
        Paragraph(subtitle or f"Generated on {datetime.now().strftime('%d %b %Y, %H:%M')}", styles["Muted"]),
        Spacer(1, 0.4 * cm),
    ]


def _P(text, styles, style="Body2"):
    if text is None:
        return Paragraph("—", styles[style])
    t_str = str(text).strip()
    if not t_str:
        return Paragraph("—", styles[style])
    
    # 1. Parse manual newlines to HTML breaks to preserve formatting block spacing
    t_str = t_str.replace("\n", "<br/>")
    
    # 2. Escape raw data ampersands safely to preserve XML layout validation rules
    if "&" in t_str:
        t_str = t_str.replace("&", "&amp;").replace("&amp;amp;", "&amp;").replace("&amp;lt;", "&lt;").replace("&amp;gt;", "&gt;")
        
    return Paragraph(t_str, styles[style])


def _kv_table(rows, styles):
    data = [[_P(f"<b>{k}</b>", styles), _P(v, styles)] for k, v in rows]
    # Standardized to exactly 17.4 cm full page width
    t = Table(data, colWidths=[5.0 * cm, 12.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BRAND_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    return t


def _bullets(items, styles):
    out = []
    for it in (items or []):
        if it:
            it_str = str(it).replace("&", "&amp;").replace("&amp;amp;", "&amp;")
            out.append(Paragraph(f"• {it_str}", styles["Bullet2"]))
    if not out:
        out.append(Paragraph("—", styles["Body2"]))
    return out


def _checklist_table(items, styles):
    header = [Paragraph("<b>Check Checkpoint</b>", styles["TableHeader"]), 
              Paragraph("<b>Status</b>", styles["TableHeader"]), 
              Paragraph("<b>Evaluation Note</b>", styles["TableHeader"])]
    rows = [header]
    for it in items:
        status_color = BRAND_ACCENT if it["passed"] else BRAND_DANGER
        status_label = "PASS" if it["passed"] else "FAIL"
        rows.append([
            _P(it["item"], styles),
            Paragraph(f"<font color='{status_color.hexval()}'><b>{status_label}</b></font>", styles["Body2"]),
            _P(it.get("note", "") or "—", styles, "Body2Small"),
        ])
    # Standardized to exactly 17.4 cm full page width
    t = Table(rows, colWidths=[7.5 * cm, 2.0 * cm, 7.9 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
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
    
    if not isinstance(chart_pngs, dict):
        chart_pngs = {}

    name = audit.get("candidate_name", "Candidate")
    story += _branded_header(styles, "Resume Audit Report", f"Candidate: {name}")

    story.append(_kv_table([
        ("Candidate Profile", name),
        ("Target Role Headline", audit.get("headline", "—")),
        ("Executive Verdict", audit.get("verdict", "—")),
        ("Overall Score", f"{audit.get('overall_score', 0)} / 100"),
        ("ATS Parsability Score", f"{audit.get('ats_score', 0)} / 100"),
        ("Job Description Match", f"{audit.get('jd_match_score', 0)} / 100"),
        ("Quality Audit Score", f"{audit.get('quality_score', 0)} / 100"),
        ("Experience Depth Score", f"{audit.get('experience_score', 0)} / 100"),
        ("Org-Standard Compliance", f"{audit.get('org_standard_score', 0)} / 100"),
        ("Total Verified Experience", f"{audit.get('total_experience_years', 0)} Years"),
        ("Seniority Alignment Fit", audit.get("seniority_fit", "—")),
    ], styles))
    story.append(Spacer(1, 0.4 * cm))

    # Clean aligned dual grid system for KPI visuals
    if chart_pngs.get("gauge") and chart_pngs.get("radar"):
        row = Table([[Image(io.BytesIO(chart_pngs["gauge"]), width=7.8 * cm, height=4.9 * cm),
                      Image(io.BytesIO(chart_pngs["radar"]), width=7.8 * cm, height=4.9 * cm)]],
                    colWidths=[8.7 * cm, 8.7 * cm])
        row.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "RIGHT"),
            ("ALIGN", (1, 0), (1, 0), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(row)
        story.append(Spacer(1, 0.4 * cm))
        
    if chart_pngs.get("donut"):
        img = Image(io.BytesIO(chart_pngs["donut"]), width=15 * cm, height=6.5 * cm)
        donut_container = Table([[img]], colWidths=[17.4 * cm])
        donut_container.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(donut_container)
        story.append(Spacer(1, 0.4 * cm))

    skills = audit.get("skills") or {}
    story.append(Paragraph("Skillset & Keyword Analysis", styles["H2Brand"]))
    skill_data = [
        [Paragraph("<b>Matched Competencies</b>", styles["TableHeader"]), 
         Paragraph("<b>Missing Target Gaps</b>", styles["TableHeader"]), 
         Paragraph("<b>Additional Credentials</b>", styles["TableHeader"])],
        [_P(", ".join(skills.get("matched") or []) or "—", styles),
         _P(", ".join(skills.get("missing") or []) or "—", styles),
         _P(", ".join(skills.get("additional") or []) or "—", styles)],
    ]
    # Standardized to exactly 17.4 cm full page width
    skill_t = Table(skill_data, colWidths=[5.8 * cm, 5.8 * cm, 5.8 * cm])
    skill_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    story.append(skill_t)
    story.append(Spacer(1, 0.4 * cm))

    if format_check:
        passed = format_check.get("passed", 0)
        total = format_check.get("total", 0)
        score = format_check.get("score", 0)
        story.append(Paragraph(f"Organizational Format Compliance — {passed}/{total} Passed ({score}%)", styles["H2Brand"]))
        story.append(_checklist_table(format_check.get("items", []), styles))
        story.append(Spacer(1, 0.4 * cm))

    sec = audit.get("section_compliance") or []
    if sec:
        story.append(Paragraph("Section-by-Section Structural Review (AI)", styles["H2Brand"]))
        items = [{"item": s.get("section", "—"),
                  "passed": bool(s.get("passed")),
                  "note": s.get("note", "")} for s in sec]
        story.append(_checklist_table(items, styles))
        story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Core Strategic Strengths", styles["H2Brand"]))
    story += _bullets(audit.get("strengths"), styles)
    
    story.append(Paragraph("Areas for Optimization (Weaknesses)", styles["H2Brand"]))
    story += _bullets(audit.get("weaknesses"), styles)
    
    story.append(Paragraph("Critical Evaluation Red Flags", styles["H2Brand"]))
    story += _bullets(audit.get("red_flags"), styles)
    
    story.append(Paragraph("Actionable Roadmap Recommendations", styles["H2Brand"]))
    story += _bullets(audit.get("recommendations"), styles)

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


def build_bulk_pdf(audits, chart_pngs, format_checks=None) -> dict[str, bytes]:
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
        styles, "Bulk Resume Audit Summary Report",
        f"{len(audits)} Candidates Tracked · Generated Summary"
    )

    if chart_pngs and isinstance(chart_pngs, dict):
        if chart_pngs.get("ranking"):
            img = Image(io.BytesIO(chart_pngs["ranking"]), width=15 * cm, height=7.5 * cm)
            t_rank = Table([[img]], colWidths=[17.4 * cm])
            t_rank.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
            summary_story.append(t_rank)
            summary_story.append(Spacer(1, 0.4 * cm))
            
        if chart_pngs.get("histogram"):
            img = Image(io.BytesIO(chart_pngs["histogram"]), width=15 * cm, height=5.6 * cm)
            t_hist = Table([[img]], colWidths=[17.4 * cm])
            t_hist.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
            summary_story.append(t_hist)
            summary_story.append(Spacer(1, 0.4 * cm))

    header = [Paragraph(f"<b>{h}</b>", styles["TableHeader"]) for h in ["#", "Candidate Name", "Overall", "JD Match", "Exp", "Quality", "Verdict"]]
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
        
    # Standardized to exactly 17.4 cm full page width
    summary_table = Table(rows, colWidths=[1.0 * cm, 5.5 * cm, 1.7 * cm, 1.3 * cm, 1.3 * cm, 1.7 * cm, 4.9 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (5, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    summary_story.append(summary_table)
    
    summary_doc.build(summary_story, canvasmaker=NumberedCanvas)
    pdf_output_collection["SUMMARY_OVERVIEW"] = summary_buf.getvalue()

    # -------------------------------------------------------------------------
    # PART B: GENERATE INDEPENDENT FILES FOR EACH UNIQUE RESUME
    # -------------------------------------------------------------------------
    import charts

    for a, fc in paired:
        candidate_name = a.get("candidate_name", "Unknown_Candidate").strip().replace(" ", "_")
        skills = a.get("skills") or {}
        
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
            indiv_charts = {}

        pdf_output_collection[candidate_name] = build_single_pdf(a, indiv_charts, format_check=fc)

    return pdf_output_collection


def build_compare_pdf(comparison, chart_pngs):
    buf = io.BytesIO()
    doc = _doc(buf, "Candidate Comparison Report")
    styles = _styles()
    story = []
    story += _branded_header(styles, "Candidate Comparison Report")
    
    story.append(_kv_table([
        ("Top Performer", comparison.get("winner", "—")),
        ("Strategic Justification", comparison.get("why_winner", "—")),
    ], styles))
    story.append(Spacer(1, 0.4 * cm))
    
    if chart_pngs and isinstance(chart_pngs, dict):
        if chart_pngs.get("bar"):
            img = Image(io.BytesIO(chart_pngs["bar"]), width=15 * cm, height=7.5 * cm)
            t_bar = Table([[img]], colWidths=[17.4 * cm])
            t_bar.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
            story.append(t_bar)
            story.append(Spacer(1, 0.4 * cm))
            
        if chart_pngs.get("ranking"):
            img = Image(io.BytesIO(chart_pngs["ranking"]), width=15 * cm, height=6.5 * cm)
            t_rank = Table([[img]], colWidths=[17.4 * cm])
            t_rank.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
            story.append(t_rank)
            story.append(Spacer(1, 0.4 * cm))

    header = [Paragraph(f"<b>{h}</b>", styles["TableHeader"]) for h in ["Rank", "Candidate Name", "Overall", "JD Match", "Exp", "Quality", "Verdict"]]
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
        
    # Standardized to exactly 17.4 cm full page width
    t = Table(rows, colWidths=[1.2 * cm, 5.5 * cm, 1.7 * cm, 1.3 * cm, 1.3 * cm, 1.7 * cm, 4.7 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4 * cm))
    
    story.append(Paragraph("Executive Analytical Summary", styles["H2Brand"]))
    story.append(Paragraph(str(comparison.get("comparison_summary", "—")), styles["Body2"]))
    story.append(Spacer(1, 0.4 * cm))
    
    for r in ranking:
        story.append(Paragraph(f"#{r.get('rank','—')} · {r.get('candidate_name','—')}", styles["H2Brand"]))
        story.append(Paragraph(f"<b>Core Selection Verdict:</b> {r.get('verdict','—')}", styles["Body2"]))
        story.append(Spacer(1, 0.15 * cm))
        
        story.append(Paragraph("<b>Identified Key Strengths</b>", styles["Body2"]))
        story += _bullets(r.get("key_strengths"), styles)
        story.append(Spacer(1, 0.15 * cm))
        
        story.append(Paragraph("<b>Identified Technical/Experience Gaps</b>", styles["Body2"]))
        story += _bullets(r.get("key_gaps"), styles)
        story.append(Spacer(1, 0.3 * cm))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()