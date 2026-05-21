
from __future__ import annotations
import os
import io
import json
from datetime import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from modules.parser import extract_text
from modules.llm_audit import audit_resume, compare_resumes
from modules.checks import build_format_checklist
from modules import charts
from modules import pdf_report

load_dotenv()

ORG_NAME = os.environ.get("ORG_NAME", "Resume Audit")
ORG_TAGLINE = os.environ.get("ORG_TAGLINE", "AI-Powered Resume Audits")
LOGO_PATH = os.environ.get("LOGO_PATH", "assets/logo.png")

# ---------------- Page config & styling ----------------
st.set_page_config(
    page_title=f"{ORG_NAME} - Resume Auditor",
    page_icon="assets/VisionBoard.ico",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --brand: #0F4C81;
        --accent: #16A085;
        --bg: #F8FAFC;
        --card: #FFFFFF;
        --muted: #6B7280;
        --text: #1F2933;
      }
      .stApp { background: var(--bg); }
      .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
      h1, h2, h3 { color: var(--text); }
      .brand-banner {
        background: linear-gradient(120deg, #0F4C81 0%, #16A085 100%);
        color: #fff; padding: 24px 28px; border-radius: 14px;
        box-shadow: 0 6px 20px rgba(15, 76, 129, 0.15);
        margin-bottom: 18px;
      }
      .brand-banner h1 { color: #fff; margin: 0; font-size: 28px; }
      .brand-banner p  { color: #E6F3F0; margin: 6px 0 0 0; font-size: 14px; }
      .metric-card {
        background: var(--card); border: 1px solid #E5E7EB;
        border-radius: 12px; padding: 14px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      }
      .verdict-pill {
        display:inline-block; padding: 4px 12px; border-radius: 999px;
        background: #E8F8F1; color: #0F766E; font-weight: 600; font-size: 12px;
      }
      .small-muted { color: var(--muted); font-size: 12px; }
      section[data-testid="stSidebar"] { background: #0F172A; }
      section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
      div[data-testid="stFileUploader"] section { border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### 📄 VisionBoard -  Resume Auditor")
    st.caption("Powered by OpenAI GPT-4o-mini")
    mode = st.radio(
        "Choose Mode",
        ["Single Audit", "Bulk Audit", "Compare Candidates"],
        index=0,
    )
    st.markdown("---")
    key_ok = bool(os.environ.get("OPENAI_API_KEY")) and not os.environ.get("OPENAI_API_KEY", "").startswith("sk-your")
    if key_ok:
        st.success("OpenAI key loaded")
    else:
        st.error("OPENAI_API_KEY missing in .env")
    st.caption(f"Model: `{os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')}`")
    st.markdown("---")
    st.caption("Tip: Paste a Job Description for sharper JD-match scoring.")


# ---------------- Banner ----------------
banner_l, banner_r = st.columns([1, 4])
with banner_l:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=180)
with banner_r:
    st.markdown(
        f"""
        <div class="brand-banner">
          <h1>{ORG_NAME} · Resume Audit Agent</h1>
          <p>{ORG_TAGLINE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------- Helpers ----------------
def jd_input(key: str) -> str:
    with st.expander("📌 Job Description (optional, recommended)", expanded=False):
        col1, col2 = st.columns([2, 1])
        with col1:
            jd_text = st.text_area("Paste JD text", key=f"jd_text_{key}", height=180,
                                   placeholder="Paste the job description here for JD-match scoring…")
        with col2:
            jd_file = st.file_uploader("…or upload a JD file", type=["pdf", "docx", "txt"],
                                       key=f"jd_file_{key}")
            if jd_file is not None:
                try:
                    jd_text = extract_text(jd_file.name, jd_file.getvalue())
                    st.success(f"Loaded JD ({len(jd_text)} chars)")
                except Exception as e:
                    st.error(f"JD parse error: {e}")
        return jd_text.strip() if jd_text else ""


def metric_grid(audit: dict):
    cols = st.columns(5)
    metrics = [
        ("Overall", audit.get("overall_score", 0), "🎯"),
        ("JD Match", audit.get("jd_match_score", 0), "🧭"),
        ("ATS", audit.get("ats_score", 0), "🤖"),
        ("Quality", audit.get("quality_score", 0), "✨"),
        ("Experience", audit.get("experience_score", 0), "💼"),
    ]
    for col, (label, val, icon) in zip(cols, metrics):
        col.markdown(
            f"""
            <div class="metric-card">
              <div class="small-muted">{icon} {label}</div>
              <div style="font-size: 28px; font-weight: 700; color: #0F4C81;">{int(val or 0)}</div>
              <div class="small-muted">out of 100</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_audit_view(audit: dict, key_prefix: str = "k"):
    name = audit.get("candidate_name", "Candidate")
    verdict = audit.get("verdict", "—")
    st.subheader(f"👤 {name}")
    st.markdown(f"<span class='verdict-pill'>{verdict}</span>", unsafe_allow_html=True)
    st.caption(audit.get("headline", ""))
    st.markdown("###  ")

    metric_grid(audit)
    st.markdown("###  ")

    # Org format compliance checklist (rule-based)
    fc = audit.get("_format_check")
    if fc:
        st.markdown(f"#### 📋 Org Format Compliance — {fc['passed']}/{fc['total']} ({fc['score']}%)")
        for it in fc["items"]:
            icon = "✅" if it["passed"] else "❌"
            note = f" — {it['note']}" if it.get("note") else ""
            st.markdown(f"{icon} **{it['item']}**{note}")
        st.markdown("###  ")

    # Section compliance from LLM
    sec = audit.get("section_compliance") or []
    if sec:
        st.markdown("#### 🔎 Section-by-Section Review")
        for s in sec:
            icon = "✅" if s.get("passed") else "❌"
            note = f" — {s.get('note','')}" if s.get("note") else ""
            st.markdown(f"{icon} **{s.get('section','—')}**{note}")
        st.markdown("###  ")

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(charts.gauge(audit.get("overall_score", 0), "Overall Score"),
                        use_container_width=True, key=f"{key_prefix}_gauge")
    with c2:
        st.plotly_chart(
            charts.radar({
                "ATS": audit.get("ats_score", 0),
                "Quality": audit.get("quality_score", 0),
                "JD Match": audit.get("jd_match_score", 0),
                "Experience": audit.get("experience_score", 0),
                "Overall": audit.get("overall_score", 0),
            }, "Score Breakdown"),
            use_container_width=True, key=f"{key_prefix}_radar",
        )

    skills = audit.get("skills") or {}
    st.plotly_chart(
        charts.donut_skills(skills.get("matched"), skills.get("missing"), skills.get("additional")),
        use_container_width=True, key=f"{key_prefix}_donut",
    )

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown("**✅ Matched Skills**")
        st.write(", ".join(skills.get("matched") or []) or "—")
    with s2:
        st.markdown("**❌ Missing Skills**")
        st.write(", ".join(skills.get("missing") or []) or "—")
    with s3:
        st.markdown("**➕ Additional Skills**")
        st.write(", ".join(skills.get("additional") or []) or "—")

    st.markdown("###  ")
    a, b = st.columns(2)
    with a:
        st.markdown("**💪 Strengths**")
        for s in audit.get("strengths") or []:
            st.markdown(f"- {s}")
        st.markdown("**🚩 Red Flags**")
        for s in audit.get("red_flags") or []:
            st.markdown(f"- {s}")
    with b:
        st.markdown("**⚠️ Weaknesses**")
        for s in audit.get("weaknesses") or []:
            st.markdown(f"- {s}")
        st.markdown("**🛠 Recommendations**")
        for s in audit.get("recommendations") or []:
            st.markdown(f"- {s}")


def build_single_pdf_bytes(audit: dict, format_check=None) -> bytes:
    skills = audit.get("skills") or {}
    pngs = {
        "gauge": charts.fig_to_png_bytes(charts.gauge(audit.get("overall_score", 0))),
        "radar": charts.fig_to_png_bytes(charts.radar({
            "ATS": audit.get("ats_score", 0),
            "Quality": audit.get("quality_score", 0),
            "JD Match": audit.get("jd_match_score", 0),
            "Experience": audit.get("experience_score", 0),
            "Overall": audit.get("overall_score", 0),
        })),
        "donut": charts.fig_to_png_bytes(
            charts.donut_skills(skills.get("matched"), skills.get("missing"), skills.get("additional")),
            width=900, height=380,
        ),
    }
    return pdf_report.build_single_pdf(audit, pngs, format_check=format_check)


# ---------------- MODE: Single Audit ----------------
if mode == "Single Audit":
    st.markdown("## Single Resume Audit")
    jd = jd_input("single")
    file = st.file_uploader("Upload a resume (PDF / DOCX / TXT)",
                            type=["pdf", "docx", "txt"], key="single_file")
    run = st.button("🚀 Run Audit", type="primary", use_container_width=False, disabled=file is None)

    if run and file is not None:
        try:
            with st.spinner("Extracting resume text…"):
                text = extract_text(file.name, file.getvalue())
            if not text or len(text) < 50:
                st.error("Could not extract enough text from this file.")
            else:
                with st.spinner("Auditing with GPT-4o-mini…"):
                    audit = audit_resume(text, jd or None)
                fc = build_format_checklist(
                    file.name, file.getvalue(), text,
                    float(audit.get("total_experience_years") or 0),
                )
                audit["_format_check"] = fc
                audit["_filename"] = file.name
                st.session_state["single_audit"] = audit
                st.success("Audit complete.")
        except Exception as e:
            st.error(f"Audit failed: {e}")

    if "single_audit" in st.session_state:
        audit = st.session_state["single_audit"]
        st.markdown("---")
        render_audit_view(audit, key_prefix="single")
        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        with col1:
            try:
                pdf_bytes = build_single_pdf_bytes(audit, audit.get("_format_check"))
                st.download_button(
                    "📥 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"resume_audit_{audit.get('candidate_name','candidate').replace(' ','_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"PDF render error: {e}")
        with col2:
            st.download_button(
                "📥 Download JSON",
                data=json.dumps(audit, indent=2),
                file_name="audit.json", mime="application/json",
                use_container_width=True,
            )


# ---------------- MODE: Bulk Audit ----------------
elif mode == "Bulk Audit":
    st.markdown("## Bulk Resume Audit")
    jd = jd_input("bulk")
    files = st.file_uploader(
        "Upload multiple resumes (PDF / DOCX / TXT)",
        type=["pdf", "docx", "txt"], accept_multiple_files=True, key="bulk_files",
    )
    run = st.button("🚀 Run Bulk Audit", type="primary", disabled=not files)

    if run and files:
        audits = []
        progress = st.progress(0.0)
        status = st.empty()
        for i, f in enumerate(files, 1):
            status.info(f"Processing ({i}/{len(files)}): {f.name}")
            try:
                txt = extract_text(f.name, f.getvalue())
                if len(txt) < 50:
                    st.warning(f"Skipped {f.name}: too little text")
                else:
                    a = audit_resume(txt, jd or None)
                    a["_filename"] = f.name
                    a["_format_check"] = build_format_checklist(
                        f.name, f.getvalue(), txt,
                        float(a.get("total_experience_years") or 0),
                    )
                    audits.append(a)
            except Exception as e:
                st.error(f"{f.name}: {e}")
            progress.progress(i / len(files))
        status.success(f"Done. {len(audits)} resumes audited.")
        st.session_state["bulk_audits"] = audits

    if "bulk_audits" in st.session_state and st.session_state["bulk_audits"]:
        audits = st.session_state["bulk_audits"]
        st.markdown("---")

        df = pd.DataFrame([{
            "candidate_name": a.get("candidate_name", a.get("_filename", "—")),
            "overall_score": int(a.get("overall_score", 0) or 0),
            "jd_match_score": int(a.get("jd_match_score", 0) or 0),
            "experience_score": int(a.get("experience_score", 0) or 0),
            "quality_score": int(a.get("quality_score", 0) or 0),
            "verdict": a.get("verdict", "—"),
        } for a in audits]).sort_values("overall_score", ascending=False).reset_index(drop=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Candidates", len(df))
        c2.metric("Avg Overall", f"{df['overall_score'].mean():.0f}")
        c3.metric("Top Score", int(df["overall_score"].max()))
        c4.metric("Strong Fits", int((df["overall_score"] >= 75).sum()))

        st.markdown("###  ")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(charts.horizontal_ranking(df, "Candidate Ranking"),
                            use_container_width=True, key="bulk_rank")
        with col2:
            st.plotly_chart(charts.bulk_histogram(df["overall_score"].tolist(), "Score Distribution"),
                            use_container_width=True, key="bulk_hist")

        st.plotly_chart(charts.bar_compare(df, "Side-by-side Metrics"), use_container_width=True, key="bulk_bar")

        st.markdown("### 📋 Summary Table")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("### 🔍 Detailed Reports")
        for idx, a in enumerate(sorted(audits, key=lambda x: x.get("overall_score", 0), reverse=True)):
            with st.expander(f"{a.get('candidate_name','—')} · Overall {a.get('overall_score',0)} · {a.get('verdict','—')}"):
                render_audit_view(a, key_prefix=f"bulk_{idx}")

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            try:
                pngs = {
                    "ranking": charts.fig_to_png_bytes(charts.horizontal_ranking(df), width=900, height=max(360, 60*len(df))),
                    "histogram": charts.fig_to_png_bytes(charts.bulk_histogram(df["overall_score"].tolist()), width=900, height=340),
                }
                pdf_bytes = pdf_report.build_bulk_pdf(
                    audits, pngs,
                    format_checks=[a.get("_format_check") for a in audits],
                )
                st.download_button(
                    "📥 Download Bulk PDF Report",
                    data=pdf_bytes,
                    file_name=f"bulk_resume_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"PDF render error: {e}")
        with col2:
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            st.download_button(
                "📥 Download CSV Summary",
                data=csv_buf.getvalue(),
                file_name="bulk_audit_summary.csv", mime="text/csv",
                use_container_width=True,
            )


# ---------------- MODE: Compare ----------------
else:
    st.markdown("## Compare Candidates")
    jd = jd_input("compare")
    files = st.file_uploader(
        "Upload 2–6 resumes to compare",
        type=["pdf", "docx", "txt"], accept_multiple_files=True, key="compare_files",
    )
    can_run = files is not None and 2 <= len(files) <= 6
    if files and not can_run:
        st.warning("Please upload between 2 and 6 resumes.")
    run = st.button("🚀 Run Comparison", type="primary", disabled=not can_run)

    if run and can_run:
        resumes = []
        try:
            with st.spinner("Extracting resumes…"):
                for f in files:
                    txt = extract_text(f.name, f.getvalue())
                    resumes.append({"name": f.name.rsplit(".", 1)[0], "text": txt})
            with st.spinner("Comparing with GPT-4o-mini…"):
                comparison = compare_resumes(resumes, jd or None)
            st.session_state["compare_result"] = comparison
            st.success("Comparison complete.")
        except Exception as e:
            st.error(f"Comparison failed: {e}")

    if "compare_result" in st.session_state:
        comp = st.session_state["compare_result"]
        st.markdown("---")
        ranking = sorted(comp.get("ranking") or [], key=lambda r: r.get("rank", 999))

        wcol1, wcol2 = st.columns([1, 3])
        wcol1.markdown(
            f"""
            <div class="metric-card" style="text-align:center;">
              <div class="small-muted">🏆 Winner</div>
              <div style="font-size:22px;font-weight:700;color:#0F4C81;">{comp.get('winner','—')}</div>
            </div>
            """, unsafe_allow_html=True,
        )
        wcol2.info(f"**Why:** {comp.get('why_winner', '—')}")

        df = pd.DataFrame([{
            "candidate_name": r.get("candidate_name", "—"),
            "overall_score": int(r.get("overall_score", 0) or 0),
            "jd_match_score": int(r.get("jd_match_score", 0) or 0),
            "experience_score": int(r.get("experience_score", 0) or 0),
            "quality_score": int(r.get("quality_score", 0) or 0),
            "verdict": r.get("verdict", "—"),
        } for r in ranking])

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(charts.bar_compare(df, "Metric Comparison"),
                            use_container_width=True, key="cmp_bar")
        with col2:
            st.plotly_chart(charts.horizontal_ranking(df, "Ranking"),
                            use_container_width=True, key="cmp_rank")

        st.markdown("### 📋 Ranking Table")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("### 📝 Executive Summary")
        st.write(comp.get("comparison_summary", "—"))

        for r in ranking:
            with st.expander(f"#{r.get('rank','—')} · {r.get('candidate_name','—')} · {r.get('verdict','—')}"):
                a, b = st.columns(2)
                with a:
                    st.markdown("**💪 Key Strengths**")
                    for s in r.get("key_strengths") or []:
                        st.markdown(f"- {s}")
                with b:
                    st.markdown("**⚠️ Key Gaps**")
                    for s in r.get("key_gaps") or []:
                        st.markdown(f"- {s}")

        st.markdown("---")
        try:
            pngs = {
                "bar": charts.fig_to_png_bytes(charts.bar_compare(df), width=900, height=420),
                "ranking": charts.fig_to_png_bytes(charts.horizontal_ranking(df), width=900, height=max(360, 60*len(df))),
            }
            pdf_bytes = pdf_report.build_compare_pdf(comp, pngs)
            st.download_button(
                "📥 Download Comparison PDF",
                data=pdf_bytes,
                file_name=f"resume_comparison_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"PDF render error: {e}")