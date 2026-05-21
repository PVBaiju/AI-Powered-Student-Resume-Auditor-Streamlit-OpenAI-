from __future__ import annotations
import io
import re
from pypdf import PdfReader

REQUIRED_CERTS = [
    "DP-900", "DP900", "DP-700", "DP700",
    "Databricks Associate", "Databricks Fundamentals",
    "Databricks GenAI", "Databricks Generative AI",
]
KEY_SKILLS = ["Azure", "ADF", "SQL", "Python", "PySpark", "Databricks"]
CONTACT_PATTERNS = {
    "email":    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phone":    r"(\+?\d[\d\s\-().]{7,}\d)",
    "linkedin": r"linkedin\.com/in/[A-Za-z0-9\-_/]+",
}


def get_page_count(file_name: str, file_bytes: bytes) -> int:
    """Return PDF page count, or 0 for non-PDF."""
    if not file_name.lower().endswith(".pdf"):
        return 0
    try:
        return len(PdfReader(io.BytesIO(file_bytes)).pages)
    except Exception:
        return 0


def has_profile_photo(file_name: str, file_bytes: bytes) -> bool:
    """Detect if PDF/DOCX likely contains an embedded image (proxy for profile photo)."""
    name = file_name.lower()
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages[:2]:  # photo usually on first page
                if "/XObject" in page.get("/Resources", {}):
                    xobjs = page["/Resources"]["/XObject"].get_object()
                    for obj_name in xobjs:
                        obj = xobjs[obj_name]
                        if obj.get("/Subtype") == "/Image":
                            return True
        except Exception:
            return False
    elif name.endswith(".docx"):
        # docx is a zip; images are stored as media/ entries
        try:
            import zipfile
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                return any(n.startswith("word/media/") for n in z.namelist())
        except Exception:
            return False
    return False


def check_filename(file_name: str) -> bool:
    """Expected: 'RESUME AZURE DATA ENGINEER_<NAME>.pdf' (case-insensitive)."""
    base = file_name.rsplit(".", 1)[0].upper().strip()
    return bool(re.match(r"^RESUME[\s_]+AZURE[\s_]+DATA[\s_]+ENGINEER[_\s].+", base))


def check_pdf_format(file_name: str) -> bool:
    return file_name.lower().endswith(".pdf")


def page_count_ok(pages: int, years_experience: float) -> tuple[bool, str]:
    """Org policy: 1pg (0-5y), 2pg (5-10y), 3pg (10+y)."""
    if pages == 0:
        return False, "Not a PDF (page count unknown)"
    if years_experience < 5 and pages == 1:
        return True, "1 page · matches 0-5 yr policy"
    if 5 <= years_experience < 10 and pages == 2:
        return True, "2 pages · matches 5-10 yr policy"
    if years_experience >= 10 and pages == 3:
        return True, "3 pages · matches 10+ yr policy"
    expected = "1" if years_experience < 5 else "2" if years_experience < 10 else "3"
    return False, f"{pages} page(s) · expected {expected} for {years_experience:.0f} yrs exp"


def contact_completeness(text: str) -> dict:
    return {
        "email":    bool(re.search(CONTACT_PATTERNS["email"], text)),
        "phone":    bool(re.search(CONTACT_PATTERNS["phone"], text)),
        "linkedin": bool(re.search(CONTACT_PATTERNS["linkedin"], text, re.I)),
    }


def keywords_found(text: str) -> list:
    t = text.lower()
    return [k for k in KEY_SKILLS if k.lower() in t]


def certifications_found(text: str) -> list:
    t = text.lower()
    found = []
    for c in REQUIRED_CERTS:
        if c.lower() in t:
            found.append(c)
    # dedupe (DP-900 vs DP900)
    return sorted({c.replace("-", "").upper() for c in found})


def build_format_checklist(file_name: str, file_bytes: bytes, text: str, years_exp: float) -> dict:
    """Returns a dict with score (0-100) and a list of pass/fail items."""
    photo = has_profile_photo(file_name, file_bytes)
    fname_ok = check_filename(file_name)
    pdf_ok = check_pdf_format(file_name)
    pages = get_page_count(file_name, file_bytes)
    pages_ok, pages_note = page_count_ok(pages, years_exp)
    contact = contact_completeness(text)
    kw = keywords_found(text)
    certs = certifications_found(text)

    items = [
        {"item": "Profile photo embedded",     "passed": photo,                  "note": ""},
        {"item": "Email present",              "passed": contact["email"],       "note": ""},
        {"item": "Phone present",              "passed": contact["phone"],       "note": ""},
        {"item": "LinkedIn profile link",      "passed": contact["linkedin"],    "note": ""},
        {"item": "PDF format",                 "passed": pdf_ok,                 "note": "" if pdf_ok else "Convert to PDF"},
        {"item": "Filename format",            "passed": fname_ok,
         "note": "Expected: RESUME AZURE DATA ENGINEER_<NAME>.pdf"},
        {"item": "Page count matches policy",  "passed": pages_ok,               "note": pages_note},
        {"item": "Key skills present (Azure/ADF/SQL/Python/PySpark/Databricks)",
         "passed": len(kw) >= 4, "note": f"Found {len(kw)}/6: {', '.join(kw) or '—'}"},
        {"item": "Certifications listed (DP-900/DP-700/Databricks)",
         "passed": len(certs) >= 1, "note": f"Found: {', '.join(certs) or 'None'}"},
    ]
    passed = sum(1 for it in items if it["passed"])
    score = round(100 * passed / len(items))
    return {"score": score, "passed": passed, "total": len(items), "items": items, "page_count": pages}