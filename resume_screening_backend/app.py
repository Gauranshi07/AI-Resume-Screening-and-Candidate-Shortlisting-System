import io
import os
import re
from datetime import datetime

import joblib
import pandas as pd
import pytesseract
import pymupdf

from docx import Document
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "shortlisting_model.pkl")

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.isfile(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

if not os.path.isfile(MODEL_PATH):
    raise FileNotFoundError(f"Trained model not found: {MODEL_PATH}")

# Load existing trained model. No retraining.
model = joblib.load(MODEL_PATH)
FEATURES = list(model.feature_names_in_)

EXPECTED_FEATURES = [
    "age", "education_level", "university_tier", "cgpa", "internships",
    "projects", "programming_languages", "certifications", "experience_years",
    "hackathons", "research_papers", "skills_score", "soft_skills_score",
    "resume_length_words", "company_type",
]
if FEATURES != EXPECTED_FEATURES:
    raise RuntimeError(
        "Model feature schema mismatch. Check the trained model's feature order."
    )

preprocessor = model.named_steps["preprocessor"]

NUMERIC_FIELDS = [
    "age", "cgpa", "internships", "projects", "programming_languages",
    "certifications", "experience_years", "hackathons", "research_papers",
    "skills_score", "soft_skills_score", "resume_length_words",
]
CATEGORICAL_FIELDS = ["education_level", "university_tier", "company_type"]

actual_numeric_fields = next(
    columns for name, transformer, columns in preprocessor.transformers_
    if name == "num"
)
actual_categorical_fields = next(
    columns for name, transformer, columns in preprocessor.transformers_
    if name == "cat"
)
if set(NUMERIC_FIELDS) != set(actual_numeric_fields):
    raise RuntimeError("Numeric fields do not match the trained pipeline.")
if set(CATEGORICAL_FIELDS) != set(actual_categorical_fields):
    raise RuntimeError("Categorical fields do not match the trained pipeline.")

app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "docx", "jpg", "jpeg", "png", "webp"}

RELEVANT_SKILLS = {
    "java", "python", "javascript", "c++", "c", "html", "css", "react",
    "node.js", "express", "sql", "mysql", "mongodb", "rest api", "git",
    "github", "data structures", "algorithms", "oops", "machine learning",
    "scikit-learn", "flask", "api integration", "bootstrap", "tailwind",
    "communication", "problem solving",
}


# --------------------------------------------------
# BASIC ROUTES
# --------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Resume Screening API is running",
        "model": "final_extra_trees",
        "features": len(FEATURES),
    })


@app.route("/model-info", methods=["GET"])
def model_info():
    encoder = (
        preprocessor.named_transformers_["cat"]
        .named_steps["encoder"]
    )
    categorical_options = {
        field: [str(value) for value in categories]
        for field, categories in zip(CATEGORICAL_FIELDS, encoder.categories_)
    }
    return jsonify({
        "model_type": type(model).__name__,
        "feature_count": len(FEATURES),
        "features": FEATURES,
        "numeric_fields": NUMERIC_FIELDS,
        "categorical_fields": CATEGORICAL_FIELDS,
        "categorical_options": categorical_options,
        "classes": [str(value) for value in model.classes_],
    })


# --------------------------------------------------
# RESUME TEXT EXTRACTION
# --------------------------------------------------

def normalize_text(text):
    text = (text or "").replace("\r\n", "\n")
    text = text.replace("\r", "\n").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def ocr_image(image):
    executable = pytesseract.pytesseract.tesseract_cmd
    if not executable or not os.path.isfile(executable):
        raise RuntimeError(
            "Tesseract OCR was not found. Install Tesseract OCR "
            "or update TESSERACT_PATH in app.py."
        )
    return pytesseract.image_to_string(image)


def extract_pdf_text(file_bytes):
    parts = []
    with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf:
        for page in pdf:
            page_text = page.get_text("text").strip()
            if len(page_text) < 30:
                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(2, 2), alpha=False
                )
                image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                page_text = ocr_image(ImageOps.exif_transpose(image))
            parts.append(page_text)
    return "\n".join(parts)


def extract_docx_text(file_bytes):
    document = Document(io.BytesIO(file_bytes))
    parts = [
        paragraph.text for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(parts)


def extract_image_text(file_bytes):
    image = Image.open(io.BytesIO(file_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")
    return ocr_image(image)


def calculate_skills_score(text):
    """Keyword coverage only; this is not a measure of proficiency."""
    normalized = text.lower()
    found = set()
    for skill in RELEVANT_SKILLS:
        pattern = (
            r"(?<![a-z0-9+#.])" + re.escape(skill.lower())
            + r"(?![a-z0-9+#.])"
        )
        if re.search(pattern, normalized):
            found.add(skill)
    return round(len(found) / len(RELEVANT_SKILLS) * 100, 2)


def extract_experience_years(text):
    """Estimate duration from month/year ranges; manual review is required."""
    month_names = (
        r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
        r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
    )
    pattern = re.compile(
        rf"\b({month_names})\s+((?:19|20)\d{{2}})\s*"
        rf"(?:-|–|—|\bto\b)\s*"
        rf"({month_names}|Present|Current|Till\s+Date)"
        rf"(?:\s+((?:19|20)\d{{2}}))?\b",
        re.IGNORECASE,
    )

    def month_number(name):
        return {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4,
            "may": 5, "jun": 6, "jul": 7, "aug": 8,
            "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }.get(name[:3].lower())

    now = datetime.now()
    current_index = now.year * 12 + now.month - 1
    intervals = []
    for match in pattern.finditer(text):
        start_month = month_number(match.group(1))
        start_year = int(match.group(2))
        end_label = match.group(3)
        end_year_text = match.group(4)
        if not start_month:
            continue
        start = start_year * 12 + start_month - 1
        if end_label.lower().replace(" ", "") in {
            "present", "current", "tilldate"
        }:
            end = current_index
        else:
            end_month = month_number(end_label)
            if not end_month:
                continue
            end_year = int(end_year_text) if end_year_text else start_year
            end = end_year * 12 + end_month - 1
        if start > current_index:
            continue
        end = min(end, current_index)
        if end >= start:
            intervals.append((start, end + 1))

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


def extract_project_count(text):
    """Estimate project entries from a clearly labelled Projects section."""
    lines = text.splitlines()
    project_lines = []
    in_projects = False
    headings = {
        "PROJECTS", "PERSONAL PROJECTS", "ACADEMIC PROJECTS",
        "KEY PROJECTS", "PROJECT EXPERIENCE",
    }
    other_headings = {
        "EDUCATION", "EXPERIENCE", "WORK EXPERIENCE",
        "PROFESSIONAL EXPERIENCE", "SKILLS", "TECHNICAL SKILLS",
        "CERTIFICATIONS", "CERTIFICATES", "ACHIEVEMENTS",
        "INTERNSHIPS", "PUBLICATIONS",
    }
    for line in lines:
        cleaned = line.strip().strip("# :").upper()
        if cleaned in headings:
            in_projects = True
            continue
        if in_projects and cleaned in other_headings:
            break
        if in_projects and line.strip():
            project_lines.append(line.strip())
    if not project_lines:
        return None

    candidates = []
    for line in project_lines:
        cleaned = re.sub(r"^[\s•●▪*+\-–—\d.)]+", "", line).strip()
        if not cleaned:
            continue
        is_bullet = bool(re.match(r"^\s*[•●▪*+\-]", line))
        if len(cleaned.split()) <= 12 and (
            is_bullet or len(cleaned.split()) <= 8
        ):
            candidates.append(cleaned)
    return len(candidates) if candidates else None


def extract_candidate_fields(text):
    """Return conservative resume-derived suggestions; unknowns remain None."""
    fields = {
        "age": None,
        "education_level": None,
        "university_tier": None,
        "cgpa": None,
        "internships": None,
        "projects": extract_project_count(text),
        "programming_languages": None,
        "certifications": None,
        "experience_years": extract_experience_years(text),
        "hackathons": None,
        "research_papers": None,
        "skills_score": calculate_skills_score(text),
        "soft_skills_score": None,
        "resume_length_words": len(text.split()),
        "company_type": None,
    }

    age_match = re.search(r"\bAge\s*[:\-]\s*(\d{1,2})\b", text, re.I)
    if age_match:
        age = int(age_match.group(1))
        if 16 <= age <= 100:
            fields["age"] = age

    if re.search(r"\bPh\.?\s?D\b|\bDoctorate\b", text, re.I):
        fields["education_level"] = "PhD"
    elif re.search(
        r"\b(M\.?\s?Tech|M\.?\s?Sc|M\.?\s?E|MBA|Master'?s|Postgraduate)\b",
        text, re.I
    ):
        fields["education_level"] = "Masters"
    elif re.search(
        r"\b(B\.?\s?Tech|B\.?\s?E|B\.?\s?Sc|BCA|BBA|Bachelor'?s|Undergraduate)\b",
        text, re.I
    ):
        fields["education_level"] = "Bachelors"

    cgpa_match = re.search(
        r"\b(?:CGPA|C\.G\.P\.A\.|GPA)\s*[:\-]?\s*"
        r"(\d{1,2}(?:\.\d+)?)\s*(?:/\s*10)?\b",
        text, re.I
    )
    if cgpa_match:
        cgpa = float(cgpa_match.group(1))
        if 0 <= cgpa <= 10:
            fields["cgpa"] = cgpa

    language_patterns = {
        "Python": r"\bpython\b",
        "Java": r"\bjava\b",
        "JavaScript": r"\bjavascript\b",
        "TypeScript": r"\btypescript\b",
        "C++": r"(?<![A-Za-z0-9])C\+\+(?![A-Za-z0-9])",
        "C#": r"(?<![A-Za-z0-9])C#(?![A-Za-z0-9])",
        "PHP": r"\bphp\b",
        "Ruby": r"\bruby\b",
        "Go": r"\bgolang\b|\bgo language\b",
        "Kotlin": r"\bkotlin\b",
        "Swift": r"\bswift\b",
    }
    found_languages = {
        name for name, pattern in language_patterns.items()
        if re.search(pattern, text, re.I)
    }
    if found_languages:
        fields["programming_languages"] = len(found_languages)

    lines = text.splitlines()
    cert_lines = []
    in_certifications = False
    cert_headings = {
        "CERTIFICATIONS", "CERTIFICATES", "LICENSES AND CERTIFICATIONS",
    }
    stop_headings = {
        "EDUCATION", "EXPERIENCE", "WORK EXPERIENCE", "PROJECTS",
        "PERSONAL PROJECTS", "SKILLS", "TECHNICAL SKILLS",
        "ACHIEVEMENTS", "INTERESTS", "INTERNSHIPS", "PUBLICATIONS",
    }
    for line in lines:
        cleaned = line.strip().strip("# :").upper()
        if cleaned in cert_headings:
            in_certifications = True
            continue
        if in_certifications and cleaned in stop_headings:
            break
        if in_certifications and line.strip():
            cert_lines.append(line.strip())

    if cert_lines:
        bullet_entries = [
            line for line in cert_lines
            if re.match(r"^\s*(?:[•●▪*+-]|\d+[.)])\s*", line)
        ]
        if bullet_entries:
            fields["certifications"] = len(bullet_entries)
        else:
            likely_entries = [line for line in cert_lines if len(line.split()) >= 2]
            if likely_entries:
                fields["certifications"] = len(likely_entries)

    internship_terms = re.findall(r"\binternships?\b|\bintern\b", text, re.I)
    if internship_terms:
        fields["internships"] = min(len(internship_terms), 20)

    hackathon_terms = re.findall(r"\bhackathons?\b", text, re.I)
    if hackathon_terms:
        fields["hackathons"] = min(len(hackathon_terms), 20)

    research_terms = re.findall(
        r"\b(?:research papers?|published papers?|publications?)\b", text, re.I
    )
    if research_terms:
        fields["research_papers"] = min(len(research_terms), 50)

    # University tier, soft-skills score, and company type are not guessed.
    return fields


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
        return jsonify({
            "error": "Unsupported file format.",
            "allowed_formats": sorted(ALLOWED_EXTENSIONS),
        }), 400

    file_bytes = uploaded_file.read()
    if not file_bytes:
        return jsonify({"error": "The uploaded file is empty."}), 400

    try:
        if extension == "pdf":
            text = extract_pdf_text(file_bytes)
        elif extension == "docx":
            text = extract_docx_text(file_bytes)
        else:
            text = extract_image_text(file_bytes)
        text = normalize_text(text)
        if not text:
            return jsonify({
                "error": "No readable text was found in the resume."
            }), 422

        suggestions = extract_candidate_fields(text)
        return jsonify({
            "message": "Resume text extracted successfully.",
            "filename": filename,
            "extracted_text": text,
            "suggested_fields": suggestions,
            "candidate_fields": suggestions,
            "review_required": True,
            "note": (
                "Extracted values are suggestions, not verified facts. "
                "Review all fields and manually complete missing details."
            ),
        })
    except Exception:
        app.logger.exception("Resume extraction failed")
        return jsonify({
            "error": (
                "Resume extraction failed. Check backend logs "
                "and the OCR configuration."
            )
        }), 500


# --------------------------------------------------
# SHORTLISTING PREDICTION
# --------------------------------------------------

def is_positive_class(label):
    return str(label).strip().lower() in {
        "1", "1.0", "true", "yes", "shortlisted"
    }


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Expected a JSON request body."}), 400

        missing = [
            field for field in FEATURES
            if field not in data or data[field] is None or data[field] == ""
        ]
        if missing:
            return jsonify({
                "error": "Please provide all 15 model features.",
                "missing_fields": missing,
            }), 400

        candidate = {}
        for field in NUMERIC_FIELDS:
            try:
                value = float(data[field])
            except (ValueError, TypeError):
                return jsonify({
                    "error": f"{field} must be a valid number."
                }), 400
            if not pd.notna(value):
                return jsonify({"error": f"{field} must be a valid number."}), 400
            if value < 0:
                return jsonify({"error": f"{field} cannot be negative."}), 400
            if field in {
                "age", "internships", "projects", "programming_languages",
                "certifications", "hackathons", "research_papers",
                "resume_length_words",
            } and not value.is_integer():
                return jsonify({
                    "error": f"{field} must be a whole number."
                }), 400
            candidate[field] = int(value) if value.is_integer() else value

        if not 16 <= candidate["age"] <= 100:
            return jsonify({"error": "age must be between 16 and 100."}), 400
        if candidate["cgpa"] > 10:
            return jsonify({
                "error": "CGPA cannot exceed 10. Confirm your dataset scale."
            }), 400
        for field in ("skills_score", "soft_skills_score"):
            if not 0 <= candidate[field] <= 100:
                return jsonify({
                    "error": f"{field} must be between 0 and 100."
                }), 400

        encoder = (
            preprocessor.named_transformers_["cat"]
            .named_steps["encoder"]
        )
        category_map = {
            field: {str(value) for value in categories}
            for field, categories in zip(CATEGORICAL_FIELDS, encoder.categories_)
        }
        for field in CATEGORICAL_FIELDS:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                return jsonify({
                    "error": f"{field} must be a non-empty string."
                }), 400
            value = value.strip()
            if value not in category_map[field]:
                return jsonify({
                    "error": f"Invalid value for {field}.",
                    "allowed_values": sorted(category_map[field]),
                }), 400
            candidate[field] = value

        candidate_df = pd.DataFrame([candidate], columns=FEATURES)
        prediction_value = model.predict(candidate_df)[0]
        classes = list(model.classes_)
        positive_classes = [
            label for label in classes if is_positive_class(label)
        ]

        probability = None
        if hasattr(model, "predict_proba") and positive_classes:
            probabilities = model.predict_proba(candidate_df)[0]
            positive_label = positive_classes[0]
            probability = round(
                float(probabilities[classes.index(positive_label)]) * 100, 2
            )

        result = (
            "Shortlisted"
            if is_positive_class(prediction_value)
            else "Not Shortlisted"
        )
        return jsonify({
            "prediction": str(prediction_value),
            "result": result,
            "shortlisted_probability": probability,
            "model": "final_extra_trees",
            "note": (
                "This is a model prediction, not a hiring guarantee. "
                "The probability is a model score, not a real-world "
                "hiring likelihood."
            ),
        })
    except Exception:
        app.logger.exception("Prediction failed")
        return jsonify({
            "error": "Prediction failed. Check backend logs for details."
        }), 500


# --------------------------------------------------
# ERROR HANDLERS
# --------------------------------------------------

@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({"error": "File exceeds the 10 MB limit."}), 413


# --------------------------------------------------
# START SERVER
# --------------------------------------------------

if __name__ == "__main__":
    print("Shortlisting model loaded successfully.")
    print("Model type:", type(model).__name__)
    print("Feature count:", len(FEATURES))
    print("Numeric fields:", NUMERIC_FIELDS)
    print("Categorical fields:", CATEGORICAL_FIELDS)
    app.run(host="127.0.0.1", port=5000, debug=False)
