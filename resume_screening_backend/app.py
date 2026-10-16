
import io
import os
import re
from datetime import datetime

import joblib
import pandas as pd
import requests
import pymupdf
import pytesseract

from docx import Document
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename


# -------------------- CONFIGURATION --------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "resume_screening_model.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "education_encoder.pkl")

model = joblib.load(MODEL_PATH)
education_encoder = joblib.load(ENCODER_PATH)

app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "docx", "png", "jpg", "jpeg", "webp"}

# Adjust these keywords according to the job role.
RELEVANT_SKILLS = {
    "java", "python", "javascript", "c++", "c", "html", "css",
    "react", "node.js", "express", "sql", "mysql", "mongodb",
    "rest api", "git", "github", "data structures", "algorithms",
    "oops", "machine learning", "scikit-learn", "flask",
    "api integration", "bootstrap", "tailwind", "dbms"
}

SECTION_HEADINGS = {
    "professional summary", "summary", "objective",
    "technical skills", "skills", "experience",
    "work experience", "professional experience", "internships",
    "projects", "personal projects", "academic projects",
    "education", "certifications", "certificates",
    "achievements", "leadership", "leadership & achievements"
}


# -------------------- HOME --------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Resume Screening API is running"})


# -------------------- TEXT EXTRACTION --------------------

def normalize_text(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_text(file_bytes):
    parts = []

    with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf:
        for page in pdf:
            page_text = page.get_text("text").strip()

            # OCR is used for scanned pages.
            if len(page_text) < 30:
                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(2, 2)
                )
                image = Image.open(
                    io.BytesIO(pixmap.tobytes("png"))
                )
                page_text = pytesseract.image_to_string(
                    ImageOps.exif_transpose(image)
                )

            parts.append(page_text)

    return "\n".join(parts)


def extract_docx_text(file_bytes):
    document = Document(io.BytesIO(file_bytes))
    parts = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))

    return "\n".join(parts)


def extract_image_text(file_bytes):
    image = Image.open(io.BytesIO(file_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")
    return pytesseract.image_to_string(image)


# -------------------- SECTION DETECTION --------------------

def get_section_lines(text, section_names):
    """
    Returns lines from the requested section until the next
    recognized major section heading.
    """

    lines = text.splitlines()
    start_index = None

    normalized_names = {
        name.lower().strip() for name in section_names
    }

    for index, raw_line in enumerate(lines):
        heading = raw_line.strip().strip(":").lower()

        if heading in normalized_names:
            start_index = index + 1
            break

    if start_index is None:
        return []

    result = []

    for raw_line in lines[start_index:]:
        line = raw_line.strip()
        heading = line.strip(":").lower()

        if heading in SECTION_HEADINGS:
            break

        result.append(line)

    return result


# -------------------- EXPERIENCE CALCULATION --------------------

def extract_experience_years(text):
    """
    Finds month/year employment ranges such as:
    Sep 2026 - Present
    Jul 2026 - Aug 2026
    January 2024 - March 2025

    Future periods are ignored and overlapping periods are merged.
    Education dates should not be interpreted as employment.
    """

    month_pattern = (
        r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
        r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
    )

    date_pattern = re.compile(
        rf"\b({month_pattern})\s+((?:19|20)\d{{2}})"
        rf"\s*(?:-|–|—|\bto\b)\s*"
        rf"({month_pattern}|Present|Current|Till Date)"
        rf"(?:\s+((?:19|20)\d{{2}}))?\b",
        re.IGNORECASE
    )

    month_numbers = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "may": 5, "jun": 6, "jul": 7, "aug": 8,
        "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }

    def month_number(name):
        return month_numbers.get(name[:3].lower())

    now = datetime.now()
    current_index = now.year * 12 + now.month - 1
    intervals = []

    # Prefer date ranges appearing in experience sections.
    experience_lines = get_section_lines(
        text,
        [
            "EXPERIENCE",
            "WORK EXPERIENCE",
            "PROFESSIONAL EXPERIENCE",
            "INTERNSHIPS"
        ]
    )

    # If no experience heading exists, scan the whole resume.
    # This fallback can be less accurate.
    source_text = (
        "\n".join(experience_lines)
        if experience_lines
        else text
    )

    for match in date_pattern.finditer(source_text):
        start_month = month_number(match.group(1))
        start_year = int(match.group(2))
        end_month_name = match.group(3)
        end_year_text = match.group(4)

        if not start_month:
            continue

        start_index = start_year * 12 + start_month - 1

        if end_month_name.lower() in {
            "present", "current", "till date"
        }:
            end_index = current_index
        else:
            end_month = month_number(end_month_name)

            if not end_month:
                continue

            end_year = (
                int(end_year_text)
                if end_year_text
                else start_year
            )
            end_index = end_year * 12 + end_month - 1

        if start_index > current_index:
            continue

        end_index = min(end_index, current_index)

        if end_index >= start_index:
            intervals.append((start_index, end_index + 1))

    if not intervals:
        return None

    intervals.sort()
    merged = []

    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    total_months = sum(end - start for start, end in merged)
    return round(total_months / 12, 2)


# -------------------- PROJECT COUNT --------------------

def extract_projects(text):
    """
    Counts likely project-title lines from the Projects section.
    Skips bullets, technology stacks and description lines.

    Resume layouts vary, so the result should be reviewed.
    """

    project_lines = get_section_lines(
        text,
        ["PROJECTS", "PERSONAL PROJECTS", "ACADEMIC PROJECTS"]
    )

    if not project_lines:
        return None

    titles = []
    seen = set()

    description_starters = (
        "developed ", "built ", "implemented ", "created ",
        "integrated ", "trained ", "designed ", "used ",
        "achieved ", "leveraged ", "technologies:",
        "tech stack:", "tools used:"
    )

    technology_only = re.compile(
        r"(?i)^(react(?:\.js)?|python|javascript|html|css|"
        r"java|node(?:\.js)?|flask|scikit-learn|"
        r"machine learning|html,\s*css.*|"
        r"react\.js,\s*python.*|"
        r"[\w.+#/-]+(?:\s*,\s*[\w.+#/-]+){1,8})$"
    )

    for raw_line in project_lines:
        line = raw_line.strip()

        if not line:
            continue

        # Remove common bullet symbols.
        line = re.sub(r"^[\s•●▪*-]+", "", line).strip()

        if len(line) < 5:
            continue

        lower = line.lower()

        if lower.startswith(description_starters):
            continue

        if technology_only.fullmatch(line):
            continue

        # Skip lines that look like sentences.
        if re.match(
            r"^(this project|the application|the system|"
            r"it allows|users can)\b",
            lower
        ):
            continue

        key = re.sub(r"\s+", " ", lower).strip()

        if key not in seen:
            seen.add(key)
            titles.append(line)

    app.logger.info("Detected project titles: %s", titles)
    return len(titles) if titles else None


# -------------------- SKILLS SCORE --------------------

def calculate_skills_score(text):
    """
    Measures keyword coverage, not actual proficiency.
    The score depends on RELEVANT_SKILLS.
    """

    normalized = text.lower()
    found = set()

    for skill in RELEVANT_SKILLS:
        pattern = (
            r"(?<![a-z0-9+#.])"
            + re.escape(skill)
            + r"(?![a-z0-9+#.])"
        )

        if re.search(pattern, normalized):
            found.add(skill)

    if not RELEVANT_SKILLS:
        return None

    return round(len(found) / len(RELEVANT_SKILLS) * 100, 2)


# -------------------- GITHUB ACTIVITY --------------------

def extract_github_username(text):
    urls = re.findall(
        r"(?:https?://)?(?:www\.)?github\.com/"
        r"([A-Za-z0-9-]{1,39})",
        text,
        re.IGNORECASE
    )

    ignored = {
        "features", "topics", "settings", "login",
        "signup", "orgs", "about", "collections",
        "marketplace", "sponsors"
    }

    for username in urls:
        if username.lower() not in ignored:
            return username

    return None


def calculate_github_activity(text):
    """
    Heuristic score from public GitHub API data.
    It is not an official contribution score.
    """

    username = extract_github_username(text)

    if not username:
        return None

    headers = {
        "Accept": "application/vnd.github+json"
    }

    try:
        profile_response = requests.get(
            f"https://api.github.com/users/{username}",
            headers=headers,
            timeout=5
        )

        if profile_response.status_code == 404:
            return None

        profile_response.raise_for_status()
        profile = profile_response.json()

        repos_response = requests.get(
            f"https://api.github.com/users/{username}/repos",
            params={"per_page": 100, "sort": "updated"},
            headers=headers,
            timeout=5
        )
        repos_response.raise_for_status()
        repos = repos_response.json()

        events_response = requests.get(
            f"https://api.github.com/users/{username}/events/public",
            params={"per_page": 100},
            headers=headers,
            timeout=5
        )
        events_response.raise_for_status()
        events = events_response.json()

        public_repos = int(profile.get("public_repos", 0))

        recent_events = len(events) if isinstance(events, list) else 0

        updated_repos = (
            sum(
                1 for repo in repos
                if isinstance(repo, dict) and repo.get("pushed_at")
            )
            if isinstance(repos, list)
            else 0
        )

        score = min(
            100,
            public_repos * 2
            + recent_events * 0.5
            + updated_repos
        )

        return round(score, 2)

    except (requests.RequestException, ValueError, TypeError):
        app.logger.warning(
            "Could not verify GitHub activity for %s", username
        )
        return None


# -------------------- EDUCATION DETECTION --------------------

def detect_education(text):
    normalized = text.lower()

    if re.search(
        r"\b(ph\.?\s*d|doctorate|doctoral)\b",
        normalized
    ):
        level = "PhD"

    elif re.search(
        r"\b(master(?:'s)?|m\.?\s*tech|m\.?\s*e\.?"
        r"|m\.?\s*sc|mba|mca)\b",
        normalized
    ):
        level = "Masters"

    elif re.search(
        r"\b(bachelor(?:'s)?|b\.?\s*tech|b\.?\s*e\.?"
        r"|b\.?\s*sc|bca|b\.?\s*s\.?)\b",
        normalized
    ):
        level = "Bachelors"

    elif re.search(
        r"\b(high school|secondary education|class x|class 10)\b",
        normalized
    ):
        level = "High School"

    else:
        return None

    if level in education_encoder.classes_:
        return level

    return None


# -------------------- EXTRACT RESUME API --------------------

@app.route("/extract-resume", methods=["POST"])
def extract_resume():
    if "resume" not in request.files:
        return jsonify({"error": "No resume file was uploaded."}), 400

    uploaded_file = request.files["resume"]

    if not uploaded_file.filename:
        return jsonify({"error": "Please select a resume file."}), 400

    filename = secure_filename(uploaded_file.filename)
    extension = (
        filename.rsplit(".", 1)[-1].lower()
        if "." in filename
        else ""
    )

    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": "Unsupported file format.",
            "allowed_formats": sorted(ALLOWED_EXTENSIONS)
        }), 400

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
            return jsonify({
                "error": "No readable text was found in the resume."
            }), 422

        candidate_fields = {
            "experience": extract_experience_years(extracted_text),
            "skills_score": calculate_skills_score(extracted_text),
            "education_level": detect_education(extracted_text),
            "projects": extract_projects(extracted_text),
            "resume_length": len(extracted_text.split()),
            "github_activity": calculate_github_activity(extracted_text)
        }

        return jsonify({
            "message": "Resume text extracted successfully.",
            "filename": filename,
            "extracted_text": extracted_text,
            "candidate_fields": candidate_fields
        })

    except Exception as error:
        app.logger.exception("Resume extraction failed")
        return jsonify({
            "error": "Resume extraction failed.",
            "details": str(error)
        }), 500


# -------------------- PREDICTION API --------------------

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "Expected a JSON request body."
            }), 400

        required_fields = [
            "experience", "skills_score", "education_level",
            "projects", "resume_length", "github_activity"
        ]

        missing = [
            field for field in required_fields
            if data.get(field) is None or data.get(field) == ""
        ]

        if missing:
            return jsonify({
                "error": "Please fill all required fields.",
                "fields": missing
            }), 400

        education = data["education_level"]

        if education not in education_encoder.classes_:
            return jsonify({
                "error": "Invalid education_level",
                "allowed_values": education_encoder.classes_.tolist()
            }), 400

        experience = float(data["experience"])
        skills_score = float(data["skills_score"])
        projects = float(data["projects"])
        resume_length = float(data["resume_length"])
        github_activity = float(data["github_activity"])

        if min(experience, projects, resume_length, github_activity) < 0:
            return jsonify({
                "error": "Numeric fields cannot be negative."
            }), 400

        if not 0 <= skills_score <= 100:
            return jsonify({
                "error": "Skills score must be between 0 and 100."
            }), 400

        candidate = pd.DataFrame([{
            "years_experience": experience,
            "skills_match_score": skills_score,
            "education_level": int(
                education_encoder.transform([education])[0]
            ),
            "project_count": projects,
            "resume_length": resume_length,
            "github_activity": github_activity
        }])

        prediction = int(model.predict(candidate)[0])
        probabilities = model.predict_proba(candidate)[0]

        # Find the probability belonging to class 1 explicitly.
        class_list = list(model.classes_)
        positive_index = class_list.index(1)
        shortlisted_probability = round(
            float(probabilities[positive_index]) * 100,
            2
        )

        return jsonify({
            "prediction": prediction,
            "result": (
                "Shortlisted" if prediction == 1
                else "Not Shortlisted"
            ),
            "shortlisted_probability": shortlisted_probability
        })

    except (ValueError, TypeError) as error:
        return jsonify({
            "error": "Invalid input values.",
            "details": str(error)
        }), 400

    except Exception as error:
        app.logger.exception("Prediction failed")
        return jsonify({
            "error": "Prediction failed.",
            "details": str(error)
        }), 500


# -------------------- ERROR HANDLERS --------------------

@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({
        "error": "File exceeds the 10 MB limit."
    }), 413


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
