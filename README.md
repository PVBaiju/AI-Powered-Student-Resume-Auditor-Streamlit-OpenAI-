
Action: file_editor create /app/streamlit_resume_auditor/README.md --file-text "# Resume Audit Agent (Streamlit + OpenAI)

AI-powered resume auditor with three modes:

- **Single Audit** — deep audit of one resume vs an optional Job Description.
- **Bulk Audit** — upload multiple resumes, get ranked summary + per-candidate detail.
- **Compare Candidates** — head-to-head comparison (2–6 candidates) with a recommended hire.

Uses **OpenAI `gpt-4o-mini`** (cheap & fast — great for a $10 budget).
Generates enterprise-style **PDF reports** with embedded **Plotly charts** (gauge, radar, donut, bar, ranking).

---

## 1. Setup

### Requirements
- Python **3.10+** (3.11 / 3.12 recommended)
- An OpenAI API key (https://platform.openai.com/api-keys)

### Install
```bash
cd streamlit_resume_auditor
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configure your API key
```bash
cp .env.example .env
# then edit .env and set:
#   OPENAI_API_KEY=sk-...your-real-key...
#   OPENAI_MODEL=gpt-4o-mini
```

### Run
```bash
streamlit run app.py
```
Open the URL Streamlit prints (usually `http://localhost:8501`).

---

## 2. How to Use

### Single Audit
1. (Optional) Paste/upload a **Job Description** for JD-match scoring.
2. Upload a resume (`.pdf`, `.docx`, or `.txt`).
3. Click **Run Audit**.
4. View scores, charts, strengths, weaknesses, red flags, recommendations.
5. Download the **PDF report** or raw **JSON**.

### Bulk Audit
1. (Optional) Add a JD.
2. Upload multiple resumes at once.
3. Click **Run Bulk Audit** — each is scored, then ranked.
4. See ranking chart, score distribution, side-by-side metrics, summary table, per-candidate detail.
5. Download **Bulk PDF** (one per-candidate page each) or **CSV summary**.

### Compare Candidates
1. (Optional) Add a JD.
2. Upload **2–6 resumes**.
3. Click **Run Comparison** — model produces head-to-head ranking + a winner.
4. Download a **Comparison PDF**.

---

## 3. Project Structure

```
streamlit_resume_auditor/
├── app.py                  # Streamlit UI (entry point)
├── requirements.txt
├── .env.example            # copy to .env
├── README.md
└── modules/
    ├── parser.py           # PDF/DOCX/TXT text extraction
    ├── llm_audit.py        # OpenAI JSON-mode prompts
    ├── charts.py           # Plotly chart helpers
    └── pdf_report.py       # ReportLab PDF builders
```

---

## 4. Cost Estimate (gpt-4o-mini)

- Single audit ≈ **$0.001 – $0.003** per resume (well under 1 cent).
- $10 budget ≈ **3,000 – 10,000 audits**.
- Comparison call processes all resumes in one prompt — usually **$0.005 – $0.02** depending on size.

You can switch model in `.env` (`OPENAI_MODEL=gpt-4o` etc.) any time.

---

## 5. Deployment

This is a normal Streamlit app — deploy anywhere that runs Python:

- **Streamlit Community Cloud** (free) — push to GitHub, connect repo, add `OPENAI_API_KEY` as a secret.
- **Render / Railway / Fly.io / Azure App Service** — set `OPENAI_API_KEY` env var, run `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`.
- **Docker** — standard `python:3.12-slim` base, `pip install -r requirements.txt`, expose `8501`.

---

## 6. Troubleshooting

| Issue | Fix |
|---|---|
| `OPENAI_API_KEY is not configured` | Edit `.env`, restart `streamlit run app.py`. |
| `kaleido` PNG export fails | `pip install --force-reinstall kaleido==0.2.1`. On Linux you may need `libgbm1`. |
| PDF parsing returns empty text | Resume is a scanned image — convert to text PDF first (OCR). |
| JSON parsing error from model | Re-run; rare with `response_format=json_object`. |

---

## 7. Privacy

- Resumes are sent **only** to OpenAI for analysis.
- Nothing is stored to disk by the app — files live in browser memory and are released when you close the tab.
- For hard data-residency requirements, swap the OpenAI client for Azure OpenAI in `modules/llm_audit.py`.
"
Observation: Create successful: /app/streamlit_resume_auditor/README.md