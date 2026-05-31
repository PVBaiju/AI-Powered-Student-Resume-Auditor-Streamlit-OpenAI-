from __future__ import annotations
import sys
sys.path.append("./modules")  # Ensure the modules directory is in the path
import base64   
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

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title=f"{ORG_NAME} - Resume Auditor",
    page_icon="assets/VisionBoard.ico",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# Hide Streamlit Header (Deploy Button & Menu)
# =========================================================
HIDE_STREAMLIT_HEADER = """
<style>
header {visibility: hidden; display: none;}
[data-testid="stHeader"] {visibility: hidden; display: none;}
.main .block-container {padding-top: 2rem;}
</style>
"""
st.markdown(HIDE_STREAMLIT_HEADER, unsafe_allow_html=True)

# ---------------- LOGOUT CONFIRMATION MODAL ----------------
@st.dialog("Confirm Sign Out")
def show_logout_dialog():
    st.markdown("<p style='font-size: 1.05rem; margin-bottom: 16px;'>Are you sure you want to log out of the platform?</p>", unsafe_allow_html=True)
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("✔️ Yes, Logout", use_container_width=True, type="primary", key="modal_confirm_yes"):
            st.session_state.logged_in = False
            st.session_state.role = ""
            st.rerun()
    with col_no:
        if st.button("❌ No, Cancel", use_container_width=True, type="secondary", key="modal_confirm_no"):
            st.rerun()

# ---------------- SESSION INITIALIZATION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = ""

if "single_version" not in st.session_state:
    st.session_state["single_version"] = 0
if "bulk_version" not in st.session_state:
    st.session_state["bulk_version"] = 0
if "compare_version" not in st.session_state:
    st.session_state["compare_version"] = 0

# =========================================================
# LOGIN PAGE
# =========================================================
if not st.session_state.logged_in:

    if "form_version" not in st.session_state:
        st.session_state["form_version"] = 0

    bg_style_rule = ""
    if os.path.exists("login_banner.jpg"):
        with open("login_banner.jpg", "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        
        bg_style_rule = f"""
        [data-testid="stAppViewContainer"]::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-image: url("data:image/jpeg;base64,{encoded_string}") !important;
            background-size: cover !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
            opacity: 0.60 !important; 
            z-index: 0 !important;
            pointer-events: none;
        }}
        """

    st.markdown(
        f"""
        <style>
        *, *:before, *:after {{
            box-sizing: border-box !important;
        }}
        [data-testid="stAppViewContainer"] {{
            background-color: #07111a !important;
            position: relative;
        }}
        {bg_style_rule}
        [data-testid="stHeader"] {{
            background: transparent;
        }}
        .main .block-container {{
            padding-top: 10vh;
            padding-bottom: 2rem;
            max-width: 100%;
        }}
        .login-shell {{
            max-width: 100%;
            margin: 0 auto 1.5rem auto;
            text-align: center;
        }}
        div[data-testid="stForm"] {{
            background: rgba(255, 255, 255, 0.12) !important; 
            backdrop-filter: blur(20px) saturate(160%) !important; 
            -webkit-backdrop-filter: blur(20px) saturate(160%) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important; 
            border-radius: 24px;
            padding: 2.8rem 2.25rem;
            box-shadow: 0 30px 60px -12px rgba(0, 0, 0, 0.55);
            width: 100%;
            max-width: 450px;
            margin: 0 auto;
            position: relative;
            z-index: 10;
        }}
        div[data-testid="stForm"] label {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
            font-size: 0.85rem !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        [data-testid="InputInstructions"] {{
            display: none !important;
        }}
        div[data-testid="stTextInput"] input,
        div[data-testid="stSelectbox"] [data-baseweb="select"] > div {{
            min-height: 46px;
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
            background: #f8fafc !important; 
            color: #0f172a !important;       
        }}
        div[data-testid="stTextInput"] input::placeholder {{
            color: #64748b !important;
        }}
        div[data-testid="stFormSubmitButton"] button {{
            min-height: 46px;
            border-radius: 12px !important;
            font-size: 0.95rem !important;
            font-weight: 700 !important;
            width: 100%;
        }}
        div[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] {{
            background: linear-gradient(90deg, #16A085 0%, #0F4C81 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
        }}
        div[data-testid="stFormSubmitButton"] button[kind="secondaryFormSubmit"] {{
            background: rgba(255, 255, 255, 0.2) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
        }}
        .login-help {{
            text-align: center;
            color: #cbd5e1;
            font-size: 0.85rem;
            margin-top: 1.5rem;
        }}
        .login-help span {{
            color: #38bdf8;
            font-weight: 600;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, center, right = st.columns([1, 1.8, 1])
    with center:
        st.markdown('<div class="login-shell"><br><br><br><br><br><br></div>', unsafe_allow_html=True)
        with st.form(f"login_form_{st.session_state['form_version']}", clear_on_submit=False):
            role = st.selectbox("Authorization Role", ["HR", "ADMIN"], index=0, key="login_role", label_visibility="collapsed")
            username = st.text_input("Username", placeholder="Enter username", key="login_username", label_visibility="collapsed")
            password = st.text_input("Password", type="password", placeholder="Enter password", key="login_password", label_visibility="collapsed")

            c1, c2 = st.columns(2)
            with c1:
                login_btn = st.form_submit_button("Sign In", use_container_width=True, type="primary")
            with c2:
                reset_btn = st.form_submit_button("Reset", use_container_width=True, type="secondary")

        st.markdown('<div class="login-help">Authorized access only. <span>System logs active.</span></div>', unsafe_allow_html=True)

    if reset_btn:
        st.session_state["form_version"] += 1
        st.rerun()

    if login_btn:
        valid = False
        entered_username = username.strip().lower()

        if role == "ADMIN":
            expected_admin = os.getenv("ADMIN_USERNAME", "").strip().lower()
            valid = (entered_username == expected_admin and password == os.getenv("ADMIN_PASSWORD"))
        elif role == "HR":
            expected_hr = os.getenv("HR_USERNAME", "").strip().lower()
            valid = (entered_username == expected_hr and password == os.getenv("HR_PASSWORD"))

        if valid:
            st.session_state.logged_in = True
            st.session_state.role = role
            st.rerun()
        else:
            st.error("Invalid Username or Password")
    st.stop()


# =========================================================
# MAIN APP GLOBAL APPLICATION CSS
# =========================================================
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
      .stApp {
        background: var(--bg);
      }
      .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
      }
      .metric-card {
        background: var(--card);
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      }
      .verdict-pill {
        display:inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        background: #E8F8F1;
        color: #0F766E;
        font-weight: 600;
        font-size: 12px;
      }
      .small-muted {
        color: var(--muted);
        font-size: 12px;
      }
      
      section[data-testid="stSidebar"] {
        background-color: #0F4C81 !important;
      }
      section[data-testid="stSidebar"] h3,
      section[data-testid="stSidebar"] p,
      section[data-testid="stSidebar"] label,
      section[data-testid="stSidebar"] span [data-testid="stMarkdownContainer"] {
        color: #38bdf8 !important;
      }

      /* =========================================================
         GLASSMORPHISM USER PROFILE CARD STYLES
         ========================================================= */
      .glass-profile-card {
        background: rgba(255, 255, 255, 0.06) !important;
        backdrop-filter: blur(20px) saturate(140%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(140%) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 20px !important;
        padding: 18px !important;
        margin-top: 25px !important;
        margin-bottom: 5px !important;
        box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.3) !important;
      }
      .glass-profile-layout {
        display: flex !important;
        align-items: center !important;
        gap: 14px !important;
      }
      .glass-avatar-frame {
        width: 46px !important;
        height: 46px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #38bdf8 0%, #16a085 100%) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 1.35rem !important;
        border: 1.5px solid rgba(255, 255, 255, 0.2) !important;
      }
      .glass-meta-details {
        flex: 1 !important;
      }
      .glass-user-title {
        font-size: 1rem !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        margin: 0 !important;
        line-height: 1.2 !important;
      }
      .glass-user-badge {
        display: inline-block !important;
        background: rgba(56, 189, 248, 0.15) !important;
        color: #38bdf8 !important;
        font-size: 0.65rem !important;
        font-weight: 800 !important;
        padding: 2px 6px !important;
        border-radius: 6px !important;
        text-transform: uppercase !important;
        margin-left: 6px !important;
        letter-spacing: 0.05em !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
      }
      .glass-user-subtext {
        font-size: 0.78rem !important;
        color: rgba(255, 255, 255, 0.65) !important;
        margin: 4px 0 0 0 !important;
      }
      .glass-session-timestamp {
        font-size: 0.72rem !important;
        color: rgba(255, 255, 255, 0.45) !important;
        font-family: monospace !important;
        margin-top: 12px !important;
        padding-top: 10px !important;
        border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
        text-align: center !important;
      }

      /* Sidebar Controls Buttons Customization */
      section[data-testid="stSidebar"] div.stButton > button {
        background-color: #BAE6FD !important;
        color: #000000 !important;            
        border: none;
        font-weight: 600;
        border-radius: 10px !important;
      }
      section[data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #7DD3FC !important;
      }
      /* Red accent rule specifically targets the custom primary logout selector block */
      section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {
        background-color: rgba(239, 68, 68, 0.15) !important; 
        color: #ef4444 !important;            
        border: 1px solid rgba(239, 68, 68, 0.25) !important;
        font-weight: 700;                     
        margin-top: 6px !important;
      }
      section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"]:hover {
        background-color: #ef4444 !important; 
        color: #ffffff !important;            
      }
      section[data-testid="stSidebar"] hr {
        border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.12);
        margin: 16px 0;
      }
      /* Neon Green Glow for Separators */
    section[data-testid="stSidebar"] hr {
    height: 1px !important;
    border: none !important;
    background: #16a085 !important; /* Neon Green base */
    box-shadow: 0 0 8px 2px #16a085, 0 0 15px 4px rgba(22, 160, 133, 0.5) !important;
    margin: 20px 0 !important;
}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# SIDEBAR NAVIGATION & ACCOUNT ARCHITECTURE
# =========================================================
with st.sidebar:
    st.markdown(
        """
        <div style="margin-bottom: 12px; padding-top: 10px;">
            <div style="color: #38bdf8; font-size: 1.5rem; font-weight: 800; letter-spacing: -0.02em;">🌟 VisionBoard</div>
            <div style="color: #94a3b8; font-size: 0.82rem; font-weight: 500; margin-top: 2px;">Enterprise Talent Analytics Platform</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    mode = st.radio("Choose Mode", ["Single Audit", "Bulk Audit", "Compare Candidates"], index=0)
    st.markdown("---")

    key_ok = bool(os.environ.get("OPENAI_API_KEY")) and not os.environ.get("OPENAI_API_KEY", "").startswith("sk-your")
    if key_ok:
        st.success("OpenAI key loaded")
    else:
        st.error("OPENAI_API_KEY missing in .env")
        
    st.markdown(f'<p style="color:#94a3b8; font-size:0.82rem; margin:0;">Engine: <strong style="color:#f8fafc;">{os.environ.get("OPENAI_MODEL", "gpt-4o-mini")}</strong></p>', unsafe_allow_html=True)
    st.markdown("---")
    st.caption("💡 Add a Job Description to enhance match scoring.")
    
    #if st.button("🔄 Reset Audit Counters", use_container_width=True):
    #    st.session_state["counter_reset_offset"] = (1 if "single_audit" in st.session_state else 0) + len(st.session_state.get("bulk_audits", []))
    #    st.rerun()

    # Layout buffer to lock the card elegantly at the sidebar footer
    st.markdown("<br>" * 2, unsafe_allow_html=True)
    
    # ---------------- DYNAMIC METADATA BAR BLOCK ----------------
 #   now = datetime.now()
 #   date_part = now.strftime("%b %d, %Y")
 #   time_part = now.strftime("%I:%M %p")
 #   current_time_str = f"📅 {date_part}  |  ⏰ {time_part}"

    # Crystalline Glass Container displaying active login privileges
 #   st.markdown(
 #       f"""
 #       <div class="glass-profile-card">
 #           <div class="glass-profile-layout">
 #               <div class="glass-avatar-frame">👤</div>
  #              <div class="glass-meta-details">
  #                  <p class="glass-user-title">{st.session_state.role} User <span class="glass-user-badge">PRO</span></p>
   #                 <p class="glass-user-subtext">Secure Session Console</p>
   #             </div>
  #          </div>
  #          <div class="glass-session-timestamp">
   #             {current_time_str}
    #       </div>
  #      </div>
   #     """,
   #     unsafe_allow_html=True
   # )
       
    # ---------------- DYNAMIC METADATA BAR BLOCK END   ----------------
    
    #if st.button("🚪 Logout of Session", use_container_width=True, type="primary", key="sidebar_logout_trigger"):
    #    show_logout_dialog()

# =========================================================
# MAIN APP BODY CONTENT
# =========================================================
def get_base64_image(image_path):
    try:
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        st.warning(f"Logo loading failed: {e}")
    return ""

logo_base64 = get_base64_image(LOGO_PATH)

col_spacer, col_logout = st.columns([9, 1])

with col_logout:
    if st.button(
        "Sign Out",
        key="top_logout",
        help="Signing Out of the platform",
        use_container_width=True
    ):
        show_logout_dialog()

now = datetime.now()
date_part = now.strftime("%b %d, %Y")
time_part = now.strftime("%I:%M %p")

# Use an f-string for cleaner, more reliable HTML rendering
# This avoids the .replace() issues and potential syntax errors
BANNER_HTML = f"""
<div style="
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:22px 28px;
    border-radius:18px;
    background:linear-gradient(135deg,#0F4C81 0%,#16A085 100%);
    box-shadow:0 12px 32px rgba(15,76,129,.18);
    margin-bottom:22px;
">
    <div style="display:flex;align-items:center;gap:22px;">
        <img src="data:image/png;base64,{logo_base64}" width="120" style="border-radius:8px; background:white; padding:4px;">
        <div>
            <h1 style="margin:0; color:white; font-size:2rem; font-weight:700; line-height:1.1;">
                {ORG_NAME} | Resume Audit Agent
            </h1>
            <div style="margin-top:8px; color:rgba(255,255,255,.85); font-size:.95rem;">
                {ORG_TAGLINE}
            </div>
        </div>
    </div>
    <div style="min-width:270px; background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.18); backdrop-filter:blur(18px); border-radius:16px; padding:14px 18px;">
        <div style="display:flex; align-items:center; gap:12px;">
            <div style="width:48px; height:48px; border-radius:50%; background:linear-gradient(135deg,#38BDF8,#14B8A6); display:flex; align-items:center; justify-content:center; font-size:22px;">👤</div>
            <div>
                <div style="color:white; font-size:16px; font-weight:700;">{st.session_state.role} User</div>
                <div style="color:rgba(255,255,255,.70); font-size:12px;">Secure Session Active</div>
            </div>
        </div>
        <div style="margin-top:12px; padding-top:10px; border-top:1px solid rgba(255,255,255,.15); color:rgba(255,255,255,.65); font-size:11px;">
            📅 {date_part} &nbsp;&nbsp;|&nbsp;&nbsp; ⏰ {time_part}
        </div>
    </div>
</div>
"""

st.markdown(BANNER_HTML, unsafe_allow_html=True)

#rendered_banner = (
 #   BANNER_HTML
  #  .replace("{{LOGO_BASE64}}", logo_base64)
   # .replace("{{ORG_NAME}}", ORG_NAME)
   # .replace("{{ORG_TAGLINE}}", ORG_TAGLINE)
   # .replace("{{ROLE}}", st.session_state.role)
   # .replace("{{DATE}}", date_part)
   # .replace("{{TIME}}", time_part)
#)

#st.markdown(rendered_banner, unsafe_allow_html=True)

# ---------------- UI Shared Reusables ----------------
def jd_input(key: str, version: int) -> str:
    with st.expander("📌 Job Description (optional, recommended)", expanded=False):
        col1, col2 = st.columns([2, 1])
        with col1:
            jd_text = st.text_area("Paste JD text", key=f"jd_text_{key}_{version}", height=180, placeholder="Paste the job description here for JD-match scoring…")
        with col2:
            jd_file = st.file_uploader("…or upload a JD file", type=["pdf", "docx", "txt"], key=f"jd_file_{key}_{version}")
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

    fc = audit.get("_format_check")
    if fc:
        st.markdown(f"#### 📋 Org Format Compliance — {fc['passed']}/{fc['total']} ({fc['score']}%)")
        for it in fc["items"]:
            icon = "✅" if it["passed"] else "❌"
            note = f" — {it['note']}" if it.get("note") else ""
            st.markdown(f"{icon} **{it['item']}**{note}")
        st.markdown("###  ")

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
        st.plotly_chart(charts.gauge(audit.get("overall_score", 0), "Overall Score"), use_container_width=True, key=f"{key_prefix}_gauge")
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
    v = st.session_state["single_version"]
    jd = jd_input("single", v)
    
    file = st.file_uploader("Upload a resume (PDF / DOCX / TXT)", type=["pdf", "docx", "txt"], key=f"single_file_{v}")
    
    c1, c2 = st.columns([1.5, 8.5])
    with c1:
        run = st.button("🚀 Run Audit", type="primary", disabled=file is None, use_container_width=True)
    with c2:
        has_data = file is not None or "single_audit" in st.session_state
        if st.button("🧹 Clear Page", disabled=not has_data, type="secondary"):
            st.session_state.pop("single_audit", None)
            st.session_state["single_version"] += 1
            st.rerun()

    if run and file is not None:
        try:
            with st.spinner("Extracting resume text…"):
                text = extract_text(file.name, file.getvalue())
            if not text or len(text) < 50:
                st.error("Could not extract enough text from this file.")
            else:
                with st.spinner("Auditing with GPT-4o-mini…"):
                    audit = audit_resume(text, jd or None)
                fc = build_format_checklist(file.name, file.getvalue(), text, float(audit.get("total_experience_years") or 0))
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
            st.download_button("📥 Download JSON", data=json.dumps(audit, indent=2), file_name="audit.json", mime="application/json", use_container_width=True)


# ---------------- MODE: Bulk Audit ----------------
elif mode == "Bulk Audit":
    st.markdown("## Bulk Resume Audit")
    v = st.session_state["bulk_version"]
    jd = jd_input("bulk", v)
    
    files = st.file_uploader("Upload multiple resumes (PDF / DOCX / TXT)", type=["pdf", "docx", "txt"], accept_multiple_files=True, key=f"bulk_files_{v}")
    
    c1, c2 = st.columns([1.8, 8.2])
    with c1:
        run = st.button("🚀 Run Bulk Audit", type="primary", disabled=not files, use_container_width=True)
    with c2:
        has_bulk_data = bool(files) or "bulk_audits" in st.session_state
        if st.button("🧹 Clear All Audits", disabled=not has_bulk_data, type="secondary"):
            st.session_state.pop("bulk_audits", None)
            st.session_state["bulk_version"] += 1
            st.rerun()

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
                    a["_format_check"] = build_format_checklist(f.name, f.getvalue(), txt, float(a.get("total_experience_years") or 0))
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
            st.plotly_chart(charts.horizontal_ranking(df, "Candidate Ranking"), use_container_width=True, key="bulk_rank")
        with col2:
            st.plotly_chart(charts.bulk_histogram(df["overall_score"].tolist(), "Score Distribution"), use_container_width=True, key="bulk_hist")

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
                reports_dictionary = pdf_report.build_bulk_pdf(audits, pngs, format_checks=[a.get("_format_check") for a in audits])
                
                st.download_button(
                    "📊 Download Bulk Overview Summary Report",
                    data=reports_dictionary["SUMMARY_OVERVIEW"],
                    file_name=f"bulk_summary_overview_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
                
                st.markdown("#### 📥 Download Individual Candidate Reports")
                for candidate_key, pdf_data in reports_dictionary.items():
                    if candidate_key == "SUMMARY_OVERVIEW":
                        continue
                    readable_candidate_name = candidate_key.replace("_", " ")
                    st.download_button(
                        label=f"📄 Download Report — {readable_candidate_name}",
                        data=pdf_data,
                        file_name=f"Resume_Audit_Report_{candidate_key}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
            except Exception as e:
                st.error(f"PDF render error: {e}")
        with col2:
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            st.download_button("📥 Download CSV Summary", data=csv_buf.getvalue(), file_name="bulk_audit_summary.csv", mime="text/csv", use_container_width=True)


# ---------------- MODE: Compare Candidates ----------------
else:
    st.markdown("## Compare Candidates")
    v = st.session_state["compare_version"]
    jd = jd_input("compare", v)
    
    files = st.file_uploader("Upload 2–6 resumes to compare", type=["pdf", "docx", "txt"], accept_multiple_files=True, key=f"compare_files_{v}")
    
    can_run = files is not None and 2 <= len(files) <= 6
    if files and not can_run:
        st.warning("Please upload between 2 and 6 resumes.")
        
    c1, c2 = st.columns([2.0, 8.0])
    with c1:
        run = st.button("🚀 Run Comparison", type="primary", disabled=not can_run, use_container_width=True)
    with c2:
        has_comp_data = bool(files) or "compare_result" in st.session_state
        if st.button("🧹 Clear Comparison Layout", disabled=not has_comp_data, type="secondary"):
            st.session_state.pop("compare_result", None)
            st.session_state["compare_version"] += 1
            st.rerun()

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
            st.plotly_chart(charts.bar_compare(df, "Metric Comparison"), use_container_width=True, key="cmp_bar")
        with col2:
            st.plotly_chart(charts.horizontal_ranking(df, "Ranking"), use_container_width=True, key="cmp_rank")

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
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PDF render error: {e}")