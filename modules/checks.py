from __future__ import annotations
import io
import re
from pypdf import PdfReader
from PIL import Image as PILImage

# Computer Vision components for deep profile photo analysis
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

REQUIRED_CERTS = [
    "DP-900", "DP900", "DP-700", "DP700",
    "Databricks Associate", "Databricks Fundamentals",
    "Databricks GenAI", "Databricks Generative AI",
]
KEY_SKILLS = ["Azure", "ADF", "SQL", "Python", "PySpark", "Databricks"]

# Added GitHub verification rules to standard mapping filters
CONTACT_PATTERNS = {
    "email":    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phone":    r"(\+?\d[\d\s\-().]{7,}\d)",
    "linkedin": r"linkedin\.com/in/[A-Za-z0-9\-_/]+",
    "github":   r"github\.com/[A-Za-z0-9\-_]+",
}


def get_page_count(file_name: str, file_bytes: bytes) -> int:
    """Return PDF page count, or 0 for non-PDF."""
    if not file_name.lower().endswith(".pdf"):
        return 0
    try:
        return len(PdfReader(io.BytesIO(file_bytes)).pages)
    except Exception:
        return 0


def _is_actual_face(pil_img: PILImage) -> bool:
    """
    Applies Computer Vision (Haar Cascades) to detect actual human faces and eyes.
    Instantly filters out badges, logos, abstracts, and shapes.
    """
    if not OPENCV_AVAILABLE:
        if pil_img.mode in ("P", "1", "L"):
            return False
        unique_colors = pil_img.convert("RGB").getcolors(maxcolors=4000)
        return unique_colors is None

    try:
        img_rgb = pil_img.convert("RGB")
        img_np = np.array(img_rgb)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        face_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        eye_path = cv2.data.haarcascades + "haarcascade_eye.xml"
        
        face_cascade = cv2.CascadeClassifier(face_path)
        eye_cascade = cv2.CascadeClassifier(eye_path)

        if face_cascade.empty() or eye_cascade.empty():
            unique_colors = pil_img.convert("RGB").getcolors(maxcolors=4000)
            return unique_colors is None

        # Detect clear facial landscapes
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=4, minSize=(40, 40))

        # Confirm eye features match parameters inside the face target box
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.05, minNeighbors=2)
            if len(eyes) >= 1:
                return True
                
        return False
    except Exception:
        return False


def has_profile_photo(file_name: str, file_bytes: bytes) -> bool:
    """Detect if PDF/DOCX contains an authentic face portrait on Page 1."""
    name = file_name.lower().strip()
    
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            if not reader.pages:
                return False
            
            first_page = reader.pages[0]
            for img_obj in first_page.images:
                try:
                    with PILImage.open(io.BytesIO(img_obj.data)) as img:
                        width, height = img.size
                        aspect_ratio = width / height
                        
                        if not (0.65 <= aspect_ratio <= 1.4):
                            continue
                        if not (100 <= width <= 900 and 100 <= height <= 900):
                            continue
                        
                        if _is_actual_face(img):
                            return True
                except Exception:
                    continue
        except Exception:
            return False

    elif name.endswith(".docx"):
        try:
            import zipfile
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                media_files = [n for n in z.namelist() if n.startswith("word/media/")]
                for media_file in media_files:
                    with z.open(media_file) as img_file:
                        with PILImage.open(img_file) as img:
                            width, height = img.size
                            aspect_ratio = width / height
                            
                            if (0.65 <= aspect_ratio <= 1.4) and (100 <= width <= 900 and 100 <= height <= 900):
                                if _is_actual_face(img):
                                    return True
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
        "github":   bool(re.search(CONTACT_PATTERNS["github"], text, re.I)),
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

    # Added GitHub to compliance engine layout matrix tracking 
    items = [
        {"item": "Profile photo embedded",     "passed": photo,                  "note": ""},
        {"item": "Email present",              "passed": contact["email"],       "note": ""},
        {"item": "Phone present",              "passed": contact["phone"],       "note": ""},
        {"item": "LinkedIn profile link",      "passed": contact["linkedin"],    "note": ""},
        {"item": "GitHub portfolio link",      "passed": contact["github"],      "note": ""},
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