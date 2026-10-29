
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

  const sections = [
    {
      number: "01",
      title: "Candidate & education",
      description: "Basic details and academic background",
      fields: [
        { key: "age", label: "Age", type: "number", placeholder: "e.g. 22", min: 1, max: 100, step: 1 },
        { key: "education_level", label: "Education level", type: "select", options: ["Bachelors", "Masters", "PhD"] },
        { key: "university_tier", label: "University tier", type: "select", options: ["Tier 1", "Tier 2", "Tier 3"] },
        { key: "cgpa", label: "CGPA (out of 10)", type: "number", placeholder: "e.g. 8.2", min: 0, max: 10, step: "any" },
      ],
    },
    {
      number: "02",
      title: "Experience & activity",
      description: "Practical experience and project involvement",
      fields: [
        { key: "internships", label: "Number of internships", type: "number", placeholder: "e.g. 2", min: 0, step: 1 },
        { key: "projects", label: "Number of projects", type: "number", placeholder: "e.g. 3", min: 0, step: 1, hint: "Verify the count against the projects listed in the resume." },
        { key: "experience_years", label: "Experience (years)", type: "number", placeholder: "e.g. 0.5", min: 0, step: "any", hint: "Enter total experience in years; 6 months = 0.5." },
        { key: "hackathons", label: "Number of hackathons", type: "number", placeholder: "e.g. 1", min: 0, step: 1 },
        { key: "research_papers", label: "Research papers", type: "number", placeholder: "e.g. 0", min: 0, step: 1 },
      ],
    },
    {
      number: "03",
      title: "Skills & credentials",
      description: "Skills assessment and supporting credentials",
      fields: [
        { key: "programming_languages", label: "Programming languages", type: "number", placeholder: "Number of languages", min: 0, step: 1, hint: "Enter a count, not the language names." },
        { key: "certifications", label: "Certifications", type: "number", placeholder: "Number of certifications", min: 0, step: 1 },
        { key: "skills_score", label: "Skills score (0–100)", type: "number", placeholder: "Enter skills score", min: 0, max: 100, step: "any", hint: "Use a consistent estimate based on role-related skills." },
        { key: "soft_skills_score", label: "Soft skills score (0–100)", type: "number", placeholder: "Enter soft skills score", min: 0, max: 100, step: "any" },
        { key: "resume_length_words", label: "Resume length (words)", type: "number", placeholder: "Approximate word count", min: 0, step: 1, hint: "Review the extracted word count or enter it manually." },
        { key: "company_type", label: "Company type", type: "select", options: ["MNC", "Mid-size", "Startup"] },
      ],
    },
  ];

  const renderField = (field) => (
    <div className="form-group" key={field.key}>
      <label htmlFor={field.key}>{field.label}</label>
      {field.type === "select" ? (
        <select
          id={field.key}
          name={field.key}
          value={formData[field.key]}
          onChange={handleChange}
          required
        >
          <option value="">Select {field.label.toLowerCase()}</option>
          {field.options.map((option) => (
            <option value={option} key={option}>{option}</option>
          ))}
        </select>
      ) : (
        <input
          id={field.key}
          type="number"
          name={field.key}
          placeholder={field.placeholder}
          value={formData[field.key]}
          onChange={handleChange}
          min={field.min}
          max={field.max}
          step={field.step}
          required
        />
      )}
      {field.key === "experience_years" && formData.experience_years !== "" && (
        <small className="field-hint">Duration: {getExperienceLabel(formData.experience_years)}</small>
      )}
      {field.hint && <small className="field-hint">{field.hint}</small>}
    </div>
  );

  return (
    <form className="resume-form" onSubmit={handleSubmit}>
      {sections.map((section) => (
        <section className="form-section" key={section.number}>
          <div className="form-section-label">
            <span>{section.number}</span>
            <div>
              <strong>{section.title}</strong>
              <small>{section.description}</small>
            </div>
          </div>
          <div className="form-fields">
            {section.fields.map(renderField)}
          </div>
        </section>
      ))}

      {formError && (
        <div className="notice error form-error" role="alert">
          {formError}
        </div>
      )}

      <div className="form-submit-row">
        <div>
          <strong>Ready to evaluate this profile?</strong>
          <small>Check extracted values before sending them to the screening model.</small>
        </div>
        <button type="submit" className="screen-btn screen-submit" disabled={loading}>
          {loading ? "Screening candidate…" : "Screen resume"}
        </button>
      </div>
    </form>
  );
};

export default ResumeForm;
