from __future__ import annotations
import json
import os
from typing import Optional
from openai import OpenAI


def _client() -> OpenAI:
    key = os.environ.get("OPENAI_API_KEY")
    if not key or key.startswith("sk-your"):
        raise RuntimeError("OPENAI_API_KEY is not configured. Add it to your .env file.")
    return OpenAI(api_key=key)


def _model() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


ORG_RUBRIC = """
ORG-SPECIFIC RESUME STANDARDS (for Azure Data Engineer candidates):
- Professional summary must highlight: Azure Data Engineer role, years of experience,
  and core skills (ADF, SQL, Python, PySpark, Databricks).
- Skillset section must align with Azure Data Engineering skillset.
- Work experience: each role must have Company-Role-Period; current role should mention
  "Azure Data Engineer"; Roles & Responsibilities should have AT LEAST 10 bullet points
  with keywords (ADF, SQL, Python, PySpark, Databricks, Synapse, ADLS, etc.) highlighted.
- Education: only highest qualification kept.
- Certifications expected (any of): DP-900, DP-700, Databricks Associate,
  Databricks Fundamentals, Databricks GenAI Fundamentals.
"""

SINGLE_AUDIT_SYSTEM = f"""You are a senior technical recruiter and resume auditor for an
Azure Data Engineering practice. Evaluate resumes against optional job descriptions and
the org's specific resume standards. Produce strictly structured JSON. Be objective and
evidence-based. Never invent facts. {ORG_RUBRIC}"""


SINGLE_AUDIT_SCHEMA_HINT = """
Return a JSON object with EXACTLY this shape:
{
  "candidate_name": string,
  "headline": string,
  "overall_score": int,
  "ats_score": int,
  "quality_score": int,
  "jd_match_score": int,
  "experience_score": int,
  "org_standard_score": int,
  "total_experience_years": number,
  "seniority_fit": string,
  "skills": {
    "matched":    [string],
    "missing":    [string],
    "additional": [string]
  },
  "section_compliance": [
    { "section": "Professional Summary",
      "passed": bool,
      "note": "...keyword highlight check, mentions years + Azure DE..." },
    { "section": "Skillset",                  "passed": bool, "note": "..." },
    { "section": "Work Experience Structure", "passed": bool, "note": "Company-Role-Period present" },
    { "section": "Current Role = Azure DE",   "passed": bool, "note": "..." },
    { "section": "Min 10 R&R bullets",        "passed": bool, "note": "..." },
    { "section": "Education (highest only)",  "passed": bool, "note": "..." },
    { "section": "Certifications listed",     "passed": bool, "note": "..." }
  ],
  "red_flags":   [string],
  "strengths":   [string],
  "weaknesses":  [string],
  "recommendations": [string],
  "verdict": string
}
All score keys must be integers 0..100. No prose outside the JSON.
"""


def audit_resume(resume_text: str, jd_text: Optional[str] = None) -> dict:
    client = _client()
    jd_block = f"\n\nJOB DESCRIPTION:\n{jd_text.strip()}" if jd_text else "\n\n(No job description provided — evaluate generally.)"
    user_prompt = f"RESUME:\n{resume_text.strip()[:18000]}{jd_block}\n\n{SINGLE_AUDIT_SCHEMA_HINT}"
    resp = client.chat.completions.create(
        model=_model(),
        response_format={"type": "json_object"},
        temperature=0.2,
        messages=[
            {"role": "system", "content": SINGLE_AUDIT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
    )
    return _safe_load(resp.choices[0].message.content or "{}")


COMPARE_SYSTEM = """You are a senior technical recruiter for Azure Data Engineering hires.
Compare candidates head-to-head against an optional job description and the org's resume
standards. Produce strictly structured JSON."""

COMPARE_SCHEMA_HINT = """
Return a JSON object with EXACTLY this shape:
{
  "ranking": [
    { "rank": int, "candidate_name": string,
      "overall_score": int, "jd_match_score": int,
      "experience_score": int, "quality_score": int,
      "key_strengths": [string], "key_gaps": [string], "verdict": string }
  ],
  "winner": string,
  "why_winner": string,
  "comparison_summary": string
}
All score keys must be integers 0..100. No prose outside the JSON.
"""


def compare_resumes(resumes: list, jd_text: Optional[str] = None) -> dict:
    client = _client()
    blocks = []
    for i, r in enumerate(resumes, 1):
        blocks.append(f"=== CANDIDATE {i}: {r['name']} ===\n{r['text'].strip()[:9000]}")
    joined = "\n\n".join(blocks)
    jd_block = f"\n\nJOB DESCRIPTION:\n{jd_text.strip()}" if jd_text else "\n\n(No job description — compare generally.)"
    user_prompt = f"{joined}{jd_block}\n\n{COMPARE_SCHEMA_HINT}"
    resp = client.chat.completions.create(
        model=_model(),
        response_format={"type": "json_object"},
        temperature=0.2,
        messages=[
            {"role": "system", "content": COMPARE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
    )
    return _safe_load(resp.choices[0].message.content or "{}")


def _safe_load(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        raise