
import React, { useEffect, useState } from "react";

const EMPTY_FORM = {
  age: "",
  education_level: "",
  university_tier: "",
  cgpa: "",
  internships: "",
  projects: "",
  programming_languages: "",
  certifications: "",
  experience_years: "",
  hackathons: "",
  research_papers: "",
  skills_score: "",
  soft_skills_score: "",
  resume_length_words: "",
  company_type: "",
};

const FIELD_NAMES = {
  age: "Age",
  education_level: "Education Level",
  university_tier: "University Tier",
  cgpa: "CGPA",
  internships: "Internships",
  projects: "Projects",
  programming_languages: "Programming Languages",
  certifications: "Certifications",
  experience_years: "Experience (Years)",
  hackathons: "Hackathons",
  research_papers: "Research Papers",
  skills_score: "Skills Score",
  soft_skills_score: "Soft Skills Score",
  resume_length_words: "Resume Length",
  company_type: "Company Type",
};

const NUMERIC_FIELDS = [
  "age",
  "cgpa",
  "internships",
  "projects",
  "programming_languages",
  "certifications",
  "experience_years",
  "hackathons",
  "research_papers",
  "skills_score",
  "soft_skills_score",
  "resume_length_words",
];

const INTEGER_FIELDS = [
  "age",
  "internships",
  "projects",
  "programming_languages",
  "certifications",
  "hackathons",
  "research_papers",
  "resume_length_words",
];

const ResumeForm = ({
  onScreen,
  initialData = null,
  loading = false,
}) => {
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    if (!initialData) return;

    setFormData((previous) => {
      const updated = { ...previous };

      // Only overwrite fields for which extraction returned a value.
      Object.keys(EMPTY_FORM).forEach((key) => {
        const value = initialData[key];

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

  const getExperienceLabel = (value) => {
    if (value === "" || !Number.isFinite(Number(value))) {
      return "";
    }

    const totalMonths = Math.round(Number(value) * 12);
    const years = Math.floor(totalMonths / 12);
    const months = totalMonths % 12;

    return `${years} year(s), ${months} month(s)`;
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

    const payload = { ...formData };

    for (const key of NUMERIC_FIELDS) {
      const value = Number(formData[key]);

      if (!Number.isFinite(value) || value < 0) {
        setFormError(
          `${FIELD_NAMES[key]} must be a valid non-negative number.`
        );
        return;
      }

      if (INTEGER_FIELDS.includes(key) && !Number.isInteger(value)) {
        setFormError(`${FIELD_NAMES[key]} must be a whole number.`);
        return;
      }

      payload[key] = value;
    }

    if (payload.age <= 0 || payload.age > 100) {
      setFormError("Please enter a valid age between 1 and 100.");
      return;
    }

    if (payload.cgpa > 10) {
      setFormError("CGPA must be between 0 and 10.");
      return;
    }

    for (const key of ["skills_score", "soft_skills_score"]) {
      if (payload[key] > 100) {
        setFormError(`${FIELD_NAMES[key]} must be between 0 and 100.`);
        return;
      }
    }

    const validOptions = {
      education_level: ["Bachelors", "Masters", "PhD"],
      university_tier: ["Tier 1", "Tier 2", "Tier 3"],
      company_type: ["MNC", "Mid-size", "Startup"],
    };

    for (const [key, options] of Object.entries(validOptions)) {
      if (!options.includes(payload[key])) {
        setFormError(`Please select a valid ${FIELD_NAMES[key]}.`);
        return;
      }
    }

    // Send exactly the 15 fields expected by the trained model.
    onScreen(payload);
  };

  return (
    <form className="resume-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="age">Age</label>
        <input
          id="age"
          type="number"
          name="age"
          placeholder="Enter age"
          value={formData.age}
          onChange={handleChange}
          min="1"
          max="100"
          step="1"
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
          <option value="Bachelors">Bachelors</option>
          <option value="Masters">Masters</option>
          <option value="PhD">PhD</option>
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="university_tier">University Tier</label>
        <select
          id="university_tier"
          name="university_tier"
          value={formData.university_tier}
          onChange={handleChange}
          required
        >
          <option value="">Select University Tier</option>
          <option value="Tier 1">Tier 1</option>
          <option value="Tier 2">Tier 2</option>
          <option value="Tier 3">Tier 3</option>
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="cgpa">CGPA (out of 10)</label>
        <input
          id="cgpa"
          type="number"
          name="cgpa"
          placeholder="e.g. 8.2"
          value={formData.cgpa}
          onChange={handleChange}
          min="0"
          max="10"
          step="any"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="internships">Number of Internships</label>
        <input
          id="internships"
          type="number"
          name="internships"
          placeholder="Enter internship count"
          value={formData.internships}
          onChange={handleChange}
          min="0"
          step="1"
          required
        />
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
        <small className="field-hint">
          Verify the count against the projects listed in the resume.
        </small>
      </div>

      <div className="form-group">
        <label htmlFor="programming_languages">
          Number of Programming Languages
        </label>
        <input
          id="programming_languages"
          type="number"
          name="programming_languages"
          placeholder="e.g. 3"
          value={formData.programming_languages}
          onChange={handleChange}
          min="0"
          step="1"
          required
        />
        <small className="field-hint">
          Enter the count, not the language names.
        </small>
      </div>

      <div className="form-group">
        <label htmlFor="certifications">Number of Certifications</label>
        <input
          id="certifications"
          type="number"
          name="certifications"
          placeholder="Enter certification count"
          value={formData.certifications}
          onChange={handleChange}
          min="0"
          step="1"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="experience_years">Experience (Years)</label>
        <input
          id="experience_years"
          type="number"
          name="experience_years"
          placeholder="e.g. 0.5"
          value={formData.experience_years}
          onChange={handleChange}
          min="0"
          step="any"
          required
        />
        {formData.experience_years !== "" && (
          <small className="field-hint">
            Duration: {getExperienceLabel(formData.experience_years)}
          </small>
        )}
        <small className="field-hint">
          Enter total experience in years. For example, 6 months = 0.5.
        </small>
      </div>

      <div className="form-group">
        <label htmlFor="hackathons">Number of Hackathons</label>
        <input
          id="hackathons"
          type="number"
          name="hackathons"
          placeholder="Enter hackathon count"
          value={formData.hackathons}
          onChange={handleChange}
          min="0"
          step="1"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="research_papers">Number of Research Papers</label>
        <input
          id="research_papers"
          type="number"
          name="research_papers"
          placeholder="Enter research paper count"
          value={formData.research_papers}
          onChange={handleChange}
          min="0"
          step="1"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="skills_score">Skills Score (0–100)</label>
        <input
          id="skills_score"
          type="number"
          name="skills_score"
          placeholder="Enter skills score"
          value={formData.skills_score}
          onChange={handleChange}
          min="0"
          max="100"
          step="any"
          required
        />
        <small className="field-hint">
          Use a consistent estimate based on the candidate's skills.
        </small>
      </div>

      <div className="form-group">
        <label htmlFor="soft_skills_score">Soft Skills Score (0–100)</label>
        <input
          id="soft_skills_score"
          type="number"
          name="soft_skills_score"
          placeholder="Enter soft skills score"
          value={formData.soft_skills_score}
          onChange={handleChange}
          min="0"
          max="100"
          step="any"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="resume_length_words">Resume Length (Words)</label>
        <input
          id="resume_length_words"
          type="number"
          name="resume_length_words"
          placeholder="Enter word count"
          value={formData.resume_length_words}
          onChange={handleChange}
          min="0"
          step="1"
          required
        />
        <small className="field-hint">
          Review the extracted word count or enter it manually.
        </small>
      </div>

      <div className="form-group">
        <label htmlFor="company_type">Company Type</label>
        <select
          id="company_type"
          name="company_type"
          value={formData.company_type}
          onChange={handleChange}
          required
        >
          <option value="">Select Company Type</option>
          <option value="MNC">MNC</option>
          <option value="Mid-size">Mid-size</option>
          <option value="Startup">Startup</option>
        </select>
      </div>

      {formError && (
        <div className="message error form-error" role="alert">
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
