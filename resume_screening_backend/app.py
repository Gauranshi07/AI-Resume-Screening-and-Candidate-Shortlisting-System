import io
import os
import re
from datetime import datetime

import joblib
import pandas as pd
import requests
import pytesseract
import pymupdf
from docx import Document
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

# Tesseract OCR: update this only if installed in a different folder.
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.isfile(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    print(f"Tesseract configured: {TESSERACT_PATH}")
else:
    print("WARNING: Tesseract not found at configured path. Text-based PDFs/DOCX may still work; OCR files may fail.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "resume_screening_model.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "education_encoder.pkl")
model = joblib.load(MODEL_PATH)
education_encoder = joblib.load(ENCODER_PATH)

app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "docx", "jpg", "jpeg", "png", "webp"}

RELEVANT_SKILLS = {
    "java", "python", "javascript", "c++", "c", "html", "css", "react", "node.js", "express",
    "sql", "mysql", "mongodb", "rest api", "git", "github", "data structures", "algorithms", "oops",
    "machine learning", "scikit-learn", "flask", "api integration", "bootstrap", "tailwind",
    "communication", "problem solving"
}
SECTION_HEADINGS = [
    "PROFESSIONAL SUMMARY", "SUMMARY", "OBJECTIVE", "TECHNICAL SKILLS", "SKILLS",
    "EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "INTERNSHIPS",
    "PROJECTS", "PERSONAL PROJECTS", "ACADEMIC PROJECTS", "EDUCATION", "CERTIFICATIONS",
    "ACHIEVEMENTS", "LEADERSHIP & ACHIEVEMENTS", "LEADERSHIP", "POSITIONS OF RESPONSIBILITY",
    "PUBLICATIONS", "COURSEWORK", "RELEVANT COURSEWORK"
]
PROJECT_HEADINGS = {"PROJECTS", "PERSONAL PROJECTS", "ACADEMIC PROJECTS"}
EXPERIENCE_HEADINGS = ["EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "INTERNSHIPS"]


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Resume Screening API is running"})


def normalize_text(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_heading(line):
    line = (line or "").strip()
    line = re.sub(r"^[#\s]+", "", line)
    return re.sub(r"[:\s]+$", "", line).upper().strip()


def is_heading(line, headings=None):
    headings = headings or SECTION_HEADINGS
    return clean_heading(line) in {clean_heading(h) for h in headings}


def get_section(text, target_headings):
    if isinstance(target_headings, str):
        target_headings = [target_headings]
    lines = (text or "").splitlines()
    start = None
    for index, line in enumerate(lines):
        if is_heading(line, target_headings):
            start = index + 1
            break
    if start is None:
        return ""
    section_lines = []
    for line in lines[start:]:
        if is_heading(line):
            break
        section_lines.append(line)
    return "\n".join(section_lines).strip()


def ocr_image(image):
    executable = pytesseract.pytesseract.tesseract_cmd
    if not os.path.isfile(executable):
        raise RuntimeError("Tesseract OCR is not configured. Check TESSERACT_PATH at the top of app.py.")
    return pytesseract.image_to_string(image)


def extract_pdf_text(file_bytes):
    parts = []
    with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf:
        for page in pdf:
            page_text = page.get_text("text").strip()
            if len(page_text) < 30:
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                page_text = ocr_image(ImageOps.exif_transpose(image))
            parts.append(page_text)
    return "\n".join(parts)


def extract_docx_text(file_bytes):
    document = Document(io.BytesIO(file_bytes))
    parts = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(parts)


def extract_image_text(file_bytes):
    image = Image.open(io.BytesIO(file_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")
    return ocr_image(image)


def extract_experience(text):
    """Estimate total inclusive calendar months from date ranges in experience sections."""
    month_names = (r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
                   r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
                   r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?")
    date_pattern = re.compile(
        rf"\b({month_names})\s+((?:19|20)\d{{2}})\s*(?:-|–|—|\bto\b)\s*"
        rf"({month_names}|Present|Current|Till\s+Date)(?:\s+((?:19|20)\d{{2}}))?\b",
        re.IGNORECASE
    )
    def month_number(name):
        return {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}.get(name[:3].lower())
    now = datetime.now()
    current_index = now.year * 12 + now.month - 1
    experience_text = get_section(text, EXPERIENCE_HEADINGS)
    source_text = experience_text if experience_text else text
    intervals = []
    for match in date_pattern.finditer(source_text):
        start_month, start_year = month_number(match.group(1)), int(match.group(2))
        end_label, end_year_text = match.group(3), match.group(4)
        if not start_month:
            continue
        start_index = start_year * 12 + start_month - 1
        if end_label.lower().replace(" ", "") in {"present", "current", "tilldate"}:
            end_index = current_index
        else:
            end_month = month_number(end_label)
            if not end_month:
                continue
            end_year = int(end_year_text) if end_year_text else start_year
            end_index = end_year * 12 + end_month - 1
        if start_index > current_index:
            continue
        end_index = min(end_index, current_index)
        if end_index >= start_index:
            intervals.append((start_index, end_index + 1))
    if not intervals:
        return {"years": None, "months": None, "display": None}
    intervals.sort()
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    total_months = sum(end - start for start, end in merged)
    years, months = divmod(total_months, 12)
    if years and months:
        display = f"{years} year(s), {months} month(s)"
    elif years:
        display = f"{years} year(s)"
    else:
        display = f"{months} month(s)"
    return {"years": round(total_months / 12, 2), "months": total_months, "display": display}


def extract_projects(text):
    """Count likely title lines in a Projects section; always review the result."""
    project_section = get_section(text, list(PROJECT_HEADINGS))
    if not project_section:
        return None
    lines = [line.strip() for line in project_section.splitlines() if line.strip()]
    description_starters = (
        "developed ", "built ", "implemented ", "created ", "integrated ", "designed ", "trained ",
        "responsible for ", "technologies:", "technology:", "tech stack:", "tools used:",
        "description:", "features:", "role:", "github:", "live demo:"
    )
    ignored_exact = {"projects", "personal projects", "academic projects", "technical skills", "technologies used"}
    titles = []
    for raw_line in lines:
        line = re.sub(r"^[\s•●▪*+\-–—\d.)]+", "", raw_line).strip()
        if not line:
            continue
        lower = line.lower().strip()
        if lower in ignored_exact or lower.startswith(description_starters):
            continue
        if re.fullmatch(r"(https?://\S+|www\.\S+)", line, re.IGNORECASE):
            continue
        if len(line.split()) > 14 or (line.endswith((".", ";")) and len(line.split()) > 8):
            continue
        normalized_title = re.sub(r"[^a-z0-9]+", " ", lower).strip()
        if normalized_title and normalized_title not in titles:
            titles.append(normalized_title)
    return len(titles) if titles else None


def calculate_skills_score(text):
    """Keyword coverage, not a measure of actual skill proficiency."""
    skills_text = get_section(text, ["TECHNICAL SKILLS", "SKILLS"])
    source = skills_text if skills_text else text
    normalized = source.lower()
    found = set()
    for skill in RELEVANT_SKILLS:
        pattern = r"(?<![a-z0-9+#.])" + re.escape(skill.lower()) + r"(?![a-z0-9+#.])"
        if re.search(pattern, normalized):
            found.add(skill)
    return round(len(found) / len(RELEVANT_SKILLS) * 100, 2) if RELEVANT_SKILLS else None


def extract_github_username(text):
    urls = re.findall(r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9-]{1,39})", text, re.IGNORECASE)
    ignored = {"features", "topics", "settings", "login", "signup", "orgs", "about", "marketplace", "collections", "sponsors", "enterprise"}
    for username in urls:
        if username.lower() not in ignored:
            return username
    return None


def calculate_github_activity(text):
    """Heuristic based on public GitHub data; not an official contribution count."""
    username = extract_github_username(text)
    empty = {"username": username, "score": None, "public_repos": None,
             "recent_public_events": None, "recently_pushed_repos": None}
    if not username:
        return empty
    headers = {"Accept": "application/vnd.github+json"}
    try:
        profile_response = requests.get(f"https://api.github.com/users/{username}", headers=headers, timeout=8)
        if profile_response.status_code == 404:
            return empty
        profile_response.raise_for_status()
        profile = profile_response.json()
        repos_response = requests.get(
            f"https://api.github.com/users/{username}/repos",
            params={"per_page": 100, "sort": "updated", "type": "owner"}, headers=headers, timeout=8
        )
        repos_response.raise_for_status()
        repos = repos_response.json()
        events_response = requests.get(
            f"https://api.github.com/users/{username}/events/public",
            params={"per_page": 100}, headers=headers, timeout=8
        )
        events_response.raise_for_status()
        events = events_response.json()
        public_repos = int(profile.get("public_repos", 0))
        recent_events = len(events) if isinstance(events, list) else 0
        pushed_repos = sum(1 for repo in repos if isinstance(repo, dict) and repo.get("pushed_at")) if isinstance(repos, list) else 0
        score = min(100, public_repos * 2 + recent_events * 0.5 + pushed_repos)
        return {"username": username, "score": round(score, 2), "public_repos": public_repos,
                "recent_public_events": recent_events, "recently_pushed_repos": pushed_repos}
    except (requests.RequestException, ValueError, TypeError):
        app.logger.warning("Could not verify GitHub activity for %s", username)
        return empty


def detect_education(text):
    education_text = get_section(text, ["EDUCATION"])
    normalized = (education_text if education_text else text).lower()
    patterns = [
        ("PhD", r"\b(ph\.?\s*d\.?|doctorate|doctoral)\b"),
        ("Masters", r"\b(master(?:'s)?|m\.?\s*tech|m\.?\s*e\.?|m\.?\s*sc\.?|mba|mca)\b"),
        ("Bachelors", r"\b(bachelor(?:'s)?|b\.?\s*tech|b\.?\s*e\.?|b\.?\s*sc\.?|bca|b\.?\s*com|b\.?\s*a\.?)\b"),
        ("High School", r"\b(high school|secondary education|class x|class 10|class xii|class 12|senior secondary)\b")
    ]
    classes = list(education_encoder.classes_)
    for level, pattern in patterns:
        if re.search(pattern, normalized) and level in classes:
            return level
    return None


@app.route("/extract-resume", methods=["POST"])
def extract_resume():
    if "resume" not in request.files:
        return jsonify({"error": "No resume file was uploaded."}), 400
    uploaded_file = request.files["resume"]
    if not uploaded_file.filename:
        return jsonify({"error": "Please select a resume file."}), 400
    filename = secure_filename(uploaded_file.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Unsupported file format.", "allowed_formats": sorted(ALLOWED_EXTENSIONS)}), 400
    file_bytes = uploaded_file.read()
    if not file_bytes:
        return jsonify({"error": "The uploaded file is empty."}), 400
    try:
        if extension == "pdf":
            extracted_text = extract_pdf_text(file_bytes)
        elif extension == "docx":
            extracted_text = extract_docx_text(file_bytes)
        else:
            extracted_text = extract_image_text(file_bytes)
        extracted_text = normalize_text(extracted_text)
        if not extracted_text:
            return jsonify({"error": "No readable text was found in the resume."}), 422
        experience = extract_experience(extracted_text)
        github = calculate_github_activity(extracted_text)
        candidate_fields = {
            "experience": experience["years"],
            "experience_months": experience["months"],
            "experience_display": experience["display"],
            "skills_score": calculate_skills_score(extracted_text),
            "education_level": detect_education(extracted_text),
            "projects": extract_projects(extracted_text),
            "resume_length": len(extracted_text.split()),
            "github_activity": github["score"]
        }
        return jsonify({"message": "Resume text extracted successfully.", "filename": filename,
                        "extracted_text": extracted_text, "candidate_fields": candidate_fields,
                        "github_details": github, "review_required": True})
    except pytesseract.TesseractNotFoundError:
        app.logger.exception("Tesseract OCR executable was not found")
        return jsonify({"error": "OCR is required for this file but Tesseract was not found.",
                        "details": "Check TESSERACT_PATH at the top of app.py."}), 500
    except Exception as error:
        app.logger.exception("Resume extraction failed")
        return jsonify({"error": "Resume extraction failed.", "details": str(error)}), 500


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Expected a JSON request body."}), 400
        required_fields = ["experience", "skills_score", "education_level", "projects", "resume_length", "github_activity"]
        missing = [field for field in required_fields if data.get(field) is None or data.get(field) == ""]
        if missing:
            return jsonify({"error": "Please fill all required fields.", "fields": missing}), 400
        education = data["education_level"]
        classes = list(education_encoder.classes_)
        if education not in classes:
            return jsonify({"error": "Invalid education_level.", "allowed_values": classes}), 400
        experience = float(data["experience"])
        skills_score = float(data["skills_score"])
        projects = float(data["projects"])
        resume_length = float(data["resume_length"])
        github_activity = float(data["github_activity"])
        numeric_values = [experience, skills_score, projects, resume_length, github_activity]
        if any(not pd.notna(value) for value in numeric_values):
            return jsonify({"error": "Numeric fields must contain valid numbers."}), 400
        if min(experience, projects, resume_length, github_activity) < 0:
            return jsonify({"error": "Numeric fields cannot be negative."}), 400
        if not 0 <= skills_score <= 100:
            return jsonify({"error": "Skills score must be between 0 and 100."}), 400
        candidate = pd.DataFrame([{
            "years_experience": experience,
            "skills_match_score": skills_score,
            "education_level": int(education_encoder.transform([education])[0]),
            "project_count": projects,
            "resume_length": resume_length,
            "github_activity": github_activity
        }])
        prediction = int(model.predict(candidate)[0])
        probabilities = model.predict_proba(candidate)[0]
        class_labels = list(model.classes_)
        if 1 not in class_labels:
            return jsonify({"error": "The loaded model does not contain a positive class labelled 1."}), 500
        positive_index = class_labels.index(1)
        probability = round(float(probabilities[positive_index]) * 100, 2)
        print("\n--- PREDICTION DEBUG ---")
        print("Candidate input:")
        print(candidate.to_dict(orient="records"))
        print("Model classes:", model.classes_)
        print("Raw probabilities:", probabilities)
        print("Prediction:", prediction)
        print("Shortlisted class index:", positive_index)
        print("Shortlisted probability:", probabilities[positive_index])
        print("------------------------\n")

        return jsonify({"prediction": prediction,
                        "result": "Shortlisted" if prediction == 1 else "Not Shortlisted",
                        "shortlisted_probability": probability})
    except (ValueError, TypeError) as error:
        return jsonify({"error": "Invalid input values.", "details": str(error)}), 400
    except Exception as error:
        app.logger.exception("Prediction failed")
        return jsonify({"error": "Prediction failed.", "details": str(error)}), 500


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({"error": "File exceeds the 10 MB limit."}), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
