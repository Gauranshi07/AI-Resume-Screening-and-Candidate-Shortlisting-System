
import React, { useRef, useState } from "react";
import ResumeForm from "./components/ResumeForm";
import "./App.css";

const MAX_FILE_SIZE = 10 * 1024 * 1024;

const SUPPORTED_EXTENSIONS = [
  "pdf",
  "docx",
  "jpg",
  "jpeg",
  "png",
  "webp",
];

const API_URL = "http://127.0.0.1:5000";

function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [resumeFile, setResumeFile] = useState(null);
  const [fileError, setFileError] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  const [extracting, setExtracting] = useState(false);
  const [extractionMessage, setExtractionMessage] = useState("");
  const [initialData, setInitialData] = useState(null);

  const fileInputRef = useRef(null);

  // Validate the selected resume.
  const handleFile = (file) => {
    setFileError("");
    setExtractionMessage("");
    setError("");

    if (!file) return;

    const extension = file.name.split(".").pop().toLowerCase();

    if (!SUPPORTED_EXTENSIONS.includes(extension)) {
      setResumeFile(null);
      setInitialData(null);
      setFileError(
        "Unsupported format. Please select PDF, DOCX, JPG, PNG or WEBP."
      );
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setResumeFile(null);
      setInitialData(null);
      setFileError("File size must be 10 MB or less.");
      return;
    }

    if (file.size === 0) {
      setResumeFile(null);
      setInitialData(null);
      setFileError("The selected file is empty.");
      return;
    }

    setResumeFile(file);
    setInitialData(null);
    setResult(null);
  };

  const handleFileChange = (event) => {
    handleFile(event.target.files?.[0]);
    event.target.value = "";
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    handleFile(event.dataTransfer.files?.[0]);
  };

  const removeFile = () => {
    setResumeFile(null);
    setFileError("");
    setExtractionMessage("");
    setInitialData(null);
    setResult(null);
    setError("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const formatSize = (bytes) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Extract candidate information from the uploaded resume.
  const handleExtract = async () => {
    if (!resumeFile) {
      setFileError("Please select a resume first.");
      return;
    }

    setExtracting(true);
    setFileError("");
    setExtractionMessage("");
    setError("");
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("resume", resumeFile);

      const response = await fetch(`${API_URL}/extract-resume`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            data.details ||
            "Resume extraction failed."
        );
      }

      const extractedFields =
        data.candidate_fields || data.suggested_fields;

      if (
        !extractedFields ||
        typeof extractedFields !== "object"
      ) {
        throw new Error(
          "The server did not return candidate fields. Check the backend response."
        );
      }

      // ResumeForm maps matching fields and leaves other fields editable.
      setInitialData(extractedFields);

      setExtractionMessage(
        "Resume processed successfully. Review extracted values and complete the remaining fields."
      );
    } catch (err) {
      setFileError(
        err.message ||
          "Unable to extract resume details. Check the backend."
      );
    } finally {
      setExtracting(false);
    }
  };

  // Send all 15 candidate fields to the trained model API.
  const handleScreen = async (candidateData) => {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(candidateData),
      });

      const resultData = await response.json();

      if (!response.ok) {
        throw new Error(
          resultData.error ||
            resultData.details ||
            "Screening request failed."
        );
      }

      setResult(resultData);
    } catch (err) {
      setError(
        err.message ||
          "Unable to connect with the screening server. Make sure Flask is running."
      );
    } finally {
      setLoading(false);
    }
  };

  // Format the model score safely.
  const probabilityValue =
    result?.shortlisted_probability !== undefined &&
    result?.shortlisted_probability !== null &&
    result?.shortlisted_probability !== ""
      ? Number(result.shortlisted_probability)
      : NaN;

  const validProbability = Number.isFinite(probabilityValue)
    ? Math.min(100, Math.max(0, probabilityValue))
    : null;

  return (
    <div className="app">
      <header className="navbar">
        <div className="logo">
          <div className="logo-box">R</div>
          <span>
            Resume<span>AI</span>
          </span>
        </div>

        <div className="server-status">
          <i></i>
          Candidate Evaluation
        </div>
      </header>

      <main>
        <section className="hero">
          <p>AI POWERED RECRUITMENT</p>

          <h1>
            AI Resume <span>Screening</span>
          </h1>

          <div>
            Upload a resume or enter candidate details below
            to get a model-based screening result.
          </div>
        </section>

        <section className="screen-card">
          {/* Resume upload heading */}
          <div className="upload-heading">
            <div className="upload-icon">↑</div>

            <div>
              <h2>Upload Resume</h2>
              <p>Upload a candidate&apos;s resume to get started</p>
            </div>
          </div>

          {/* Drag-and-drop upload area */}
          <div
            className={`upload-zone ${
              isDragging ? "drag-active" : ""
            } ${resumeFile ? "has-file" : ""}`}
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={(event) => {
              if (
                !event.currentTarget.contains(event.relatedTarget)
              ) {
                setIsDragging(false);
              }
            }}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="file-input"
              accept=".pdf,.docx,.jpg,.jpeg,.png,.webp"
              onChange={handleFileChange}
              aria-label="Choose a resume file"
            />

            {resumeFile ? (
              <div className="selected-file">
                <div className="file-icon">📄</div>

                <div className="file-details">
                  <strong>{resumeFile.name}</strong>

                  <span>
                    {formatSize(resumeFile.size)} · Ready to process
                  </span>
                </div>

                <button
                  type="button"
                  className="remove-file"
                  onClick={removeFile}
                  aria-label="Remove selected resume"
                  title="Remove file"
                  disabled={extracting || loading}
                >
                  ×
                </button>
              </div>
            ) : (
              <>
                <div className="cloud-icon">⇧</div>

                <h3>Drag and drop your resume here</h3>
                <p>or choose a file from your computer</p>

                <button
                  type="button"
                  className="choose-file-btn"
                  onClick={() => fileInputRef.current?.click()}
                >
                  Choose Resume
                </button>

                <span className="file-hint">
                  PDF, DOCX, JPG, PNG, WEBP · Max 10 MB
                </span>
              </>
            )}

            {resumeFile && (
              <button
                type="button"
                className="replace-file-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={extracting || loading}
              >
                Replace Resume
              </button>
            )}
          </div>

          {/* Extract button */}
          {resumeFile && (
            <button
              type="button"
              className="extract-resume-btn"
              onClick={handleExtract}
              disabled={extracting || loading}
            >
              {extracting ? (
                <>
                  <span
                    className="extract-spinner"
                    aria-hidden="true"
                  ></span>
                  Extracting Resume Details...
                </>
              ) : (
                "Extract Resume Details"
              )}
            </button>
          )}

          {fileError && (
            <div className="file-error" role="alert">
              {fileError}
            </div>
          )}

          {extractionMessage && (
            <div className="message loading" role="status">
              {extractionMessage}
            </div>
          )}

          <div className="upload-note">
            <span>ⓘ</span>
            <div>
              Extracted values are estimates. Review project count,
              experience, skills score and resume word count.
              Complete and verify all remaining candidate details
              before screening.
            </div>
          </div>

          <div className="section-divider"></div>

          {/* Candidate profile */}
          <div className="section-title">
            <div className="profile-icon">♙</div>

            <div>
              <h2>Candidate Profile</h2>
              <p>Enter or review the candidate&apos;s information</p>
            </div>
          </div>

          <div className="line"></div>

          <ResumeForm
            onScreen={handleScreen}
            initialData={initialData}
            loading={loading || extracting}
          />

          {loading && (
            <div className="message loading" role="status">
              Screening candidate...
            </div>
          )}

          {error && (
            <div className="message error" role="alert">
              {error}
            </div>
          )}

          {/* Screening result */}
          {result && (
            <div className="result" aria-live="polite">
              <div className="result-top">
                <div>
                  <small>SCREENING RESULT</small>
                  <h2>{result.result || "Result unavailable"}</h2>
                </div>

                <strong>
                  {validProbability === null
                    ? "N/A"
                    : `${validProbability.toFixed(2)}%`}
                </strong>
              </div>

              <div
                className="bar"
                role="progressbar"
                aria-label="Model score"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={validProbability ?? 0}
              >
                <div
                  style={{
                    width: `${validProbability ?? 0}%`,
                  }}
                />
              </div>

              <p>Model prediction score — not a hiring guarantee.</p>

              {validProbability === null && (
                <p className="field-hint">
                  The API returned no valid score. Check the
                  prediction response from the Flask backend.
                </p>
              )}
            </div>
          )}
        </section>

        <footer>ResumeAI • Candidate Screening</footer>
      </main>
    </div>
  );
}

export default App;
