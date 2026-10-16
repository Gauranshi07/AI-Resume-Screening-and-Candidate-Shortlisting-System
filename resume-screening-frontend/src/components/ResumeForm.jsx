
import React, { useEffect, useState } from "react";



const EMPTY_FORM = {
  experience: "",
  skills_score: "",
  education_level: "",
  projects: "",
  resume_length: "",
  github_activity: "",
};

const FIELD_NAMES = {
  experience: "Experience",
  skills_score: "Skills Score",
  education_level: "Education Level",
  projects: "Number of Projects",
  resume_length: "Resume Length",
  github_activity: "GitHub Activity",
};

const ResumeForm = ({ onScreen, initialData = null, loading = false }) => {
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    if (!initialData) return;

    setFormData((previous) => {
      const updated = { ...previous };

      Object.keys(EMPTY_FORM).forEach((key) => {
        const value = initialData[key];

        // Only replace a field when extraction found a real value.
        if (value !== undefined && value !== null && value !== "") {
          updated[key] = String(value);
        }
      });

      return updated;
    });

    setFormError("");
  }, [initialData]);

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));

    setFormError("");
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    setFormError("");

    const missingFields = Object.keys(EMPTY_FORM).filter(
      (key) => String(formData[key]).trim() === ""
    );

    if (missingFields.length > 0) {
      setFormError(
        "Please fill in: " +
          missingFields.map((key) => FIELD_NAMES[key]).join(", ")
      );
      return;
    }

    const numericFields = [
      "experience",
      "skills_score",
      "projects",
      "resume_length",
      "github_activity",
    ];

    const payload = { ...formData };

    for (const key of numericFields) {
      const value = Number(formData[key]);

      if (!Number.isFinite(value) || value < 0) {
        setFormError(`${FIELD_NAMES[key]} must be a valid non-negative number.`);
        return;
      }

      payload[key] = value;
    }

    if (payload.skills_score > 100) {
      setFormError("Skills Score must be between 0 and 100.");
      return;
    }

    if (!payload.education_level) {
      setFormError("Please select an Education Level.");
      return;
    }

    onScreen(payload);
  };

  return (
    <form className="resume-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="experience">Experience (Years)</label>
        <input
          id="experience"
          type="number"
          name="experience"
          placeholder="e.g. 1"
          value={formData.experience}
          onChange={handleChange}
          min="0"
          step="0.01"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="skills_score">Skills Score (0–100)</label>
        <input
          id="skills_score"
          type="number"
          name="skills_score"
          placeholder="Enter score manually"
          value={formData.skills_score}
          onChange={handleChange}
          min="0"
          max="100"
          step="any"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="education_level">Education Level</label>
        <select
          id="education_level"
          name="education_level"
          value={formData.education_level}
          onChange={handleChange}
          required
        >
          <option value="">Select Education</option>
          <option value="High School">High School</option>
          <option value="Bachelors">Bachelors</option>
          <option value="Masters">Masters</option>
          <option value="PhD">PhD</option>
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="projects">Number of Projects</label>
        <input
          id="projects"
          type="number"
          name="projects"
          placeholder="Enter project count"
          value={formData.projects}
          onChange={handleChange}
          min="0"
          step="1"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="resume_length">Resume Length (Words)</label>
        <input
          id="resume_length"
          type="number"
          name="resume_length"
          placeholder="Word count"
          value={formData.resume_length}
          onChange={handleChange}
          min="0"
          step="1"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="github_activity">GitHub Activity</label>
        <input
          id="github_activity"
          type="number"
          name="github_activity"
          placeholder="Enter activity score"
          value={formData.github_activity}
          onChange={handleChange}
          min="0"
          step="any"
          required
        />
      </div>

      {formError && (
        <div className="message error" role="alert">
          {formError}
        </div>
      )}

      <button
        type="submit"
        className="screen-btn"
        disabled={loading}
      >
        {loading ? "Screening Candidate..." : "Screen Resume"}
      </button>
    </form>
  );
};

export default ResumeForm;
