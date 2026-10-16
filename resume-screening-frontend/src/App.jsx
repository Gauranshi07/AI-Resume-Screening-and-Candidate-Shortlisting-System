
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

  const handleFile = (file) => {
    setFileError("");
    setExtractionMessage("");

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
    setError("");
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
          data.error || data.details || "Resume extraction failed."
        );
      }

      if (!data.candidate_fields) {
        throw new Error(
          "The server did not return candidate fields. Check the extraction API response."
        );
      }

      setInitialData(data.candidate_fields);

      setExtractionMessage(
        "Resume processed. Review the extracted details and fill in any missing fields."
      );
    } catch (err) {
      setFileError(
        err.message || "Unable to extract resume details. Check the backend."
      );
    } finally {
      setExtracting(false);
    }
  };

  const handleScreen = async (data) => {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      const resultData = await response.json();

      if (!response.ok) {
        throw new Error(
          resultData.error || "Screening request failed."
        );
      }

      setResult(resultData);
    } catch (err) {
      setError(
        err.message || "Unable to connect with the screening server."
      );
    } finally {
      setLoading(false);
    }
  };

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
            to get a quick screening result.
          </div>
        </section>

        <section className="screen-card">
          <div className="upload-heading">
            <div className="upload-icon">↑</div>

            <div>
              <h2>Upload Resume</h2>
              <p>Upload a candidate's resume to get started</p>
            </div>
          </div>

          <div
            className={`upload-zone ${isDragging ? "drag-active" : ""} ${
              resumeFile ? "has-file" : ""
            }`}
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
                disabled={extracting}
              >
                Replace Resume
              </button>
            )}
          </div>

          {resumeFile && (
            <button
              type="button"
              className="extract-resume-btn"
              onClick={handleExtract}
              disabled={extracting}
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
            Upload a resume to pre-fill available candidate details.
            Review all fields before screening.
          </div>

          <div className="section-divider"></div>

          <div className="section-title">
            <div className="profile-icon">♙</div>

            <div>
              <h2>Candidate Profile</h2>
              <p>Enter or review the candidate's information</p>
            </div>
          </div>

          <div className="line"></div>

          <ResumeForm
            onScreen={handleScreen}
            initialData={initialData}
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

          {result && (
            <div className="result">
              <div className="result-top">
                <div>
                  <small>SCREENING RESULT</small>
                  <h2>{result.result}</h2>
                </div>

                <strong>
                  {result.shortlisted_probability}%
                </strong>
              </div>

              <div className="bar">
                <div
                  style={{
                    width: `${result.shortlisted_probability}%`,
                  }}
                ></div>
              </div>

              <p>Shortlisting probability</p>
            </div>
          )}
        </section>

        <footer>ResumeAI • Candidate Screening</footer>
      </main>
    </div>
  );
}

export default App;
