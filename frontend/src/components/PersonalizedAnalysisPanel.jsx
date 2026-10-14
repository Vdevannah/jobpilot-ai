import { useId, useState } from "react";
import {
  getApplicationAssistance,
  getPersonalizedAnalysis,
  previewResumeText,
} from "../api/client";
import { useLazyRequest } from "../hooks/useLazyRequest";
import { AI_JOB_TRACK_LABELS } from "../utils/aiLabels";
import { ErrorState, LoadingState } from "./AsyncState";
import Notice from "./Notice";
import RequirementComparisonPanel from "./RequirementComparisonPanel";
import "./PersonalizedAnalysisPanel.css";

const VARIANTS = ["pharma", "data", "scientific_ai"];

function splitIdentifiers(text) {
  return text
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

export default function PersonalizedAnalysisPanel({ jobId }) {
  const resumeFieldId = useId();
  const identifiersFieldId = useId();

  const [resumeText, setResumeText] = useState("");
  const [identifiersText, setIdentifiersText] = useState("");
  const [variant, setVariant] = useState("data");
  const [mode, setMode] = useState("mock");
  const [confirmed, setConfirmed] = useState(false);

  const preview = useLazyRequest(previewResumeText);
  const analysis = useLazyRequest(getPersonalizedAnalysis);
  const assistance = useLazyRequest(getApplicationAssistance);

  // Editing the resume text or identifiers after a preview was generated
  // means the previously reviewed text is no longer what would be sent --
  // approval, and anything already produced from it, must never carry
  // forward to the newly edited text.
  function invalidatePreviousApproval() {
    setConfirmed(false);
    preview.reset();
    analysis.reset();
    assistance.reset();
  }

  function handleResumeTextChange(event) {
    setResumeText(event.target.value);
    invalidatePreviousApproval();
  }

  function handleIdentifiersChange(event) {
    setIdentifiersText(event.target.value);
    invalidatePreviousApproval();
  }

  function handlePreview() {
    preview.run(resumeText, splitIdentifiers(identifiersText));
  }

  function handleAnalyze() {
    analysis.run(jobId, { previewText: preview.data.preview, confirmed: true, variant, mode });
  }

  function handleAssistance() {
    assistance.run(jobId, { previewText: preview.data.preview, confirmed: true, variant, mode });
  }

  const comparisonForDisplay = analysis.data
    ? {
        requirement_comparison: analysis.data.requirement_comparison,
        candidate_is_fictional: false,
        candidate_label: `Your approved resume evidence (${AI_JOB_TRACK_LABELS[variant] ?? variant} variant, ${mode === "mock" ? "mock analysis" : "live OpenAI analysis"})`,
        limitations: analysis.data.limitations,
      }
    : null;

  return (
    <div className="personalized-analysis-panel">
      <p className="personalized-analysis-panel__intro">
        Paste your own resume text below (never read automatically from your computer). You
        control exactly what is analyzed, and nothing is sent anywhere -- including to OpenAI --
        until you explicitly review the sanitized preview and approve it below.
      </p>

      <div className="personalized-analysis-panel__field">
        <label htmlFor={resumeFieldId}>Your resume text</label>
        <textarea
          id={resumeFieldId}
          className="personalized-analysis-panel__textarea"
          rows={8}
          value={resumeText}
          onChange={handleResumeTextChange}
          placeholder={"Professional Experience:\nData Engineer, Acme Co, 2019-2024...\n\nEducation:\nMS in Computer Science"}
        />
      </div>

      <div className="personalized-analysis-panel__field">
        <label htmlFor={identifiersFieldId}>
          Names, cities, or other identifiers to remove (comma-separated, optional)
        </label>
        <input
          id={identifiersFieldId}
          type="text"
          className="personalized-analysis-panel__input"
          value={identifiersText}
          onChange={handleIdentifiersChange}
          placeholder="Jane Doe, Springfield"
        />
      </div>

      <div className="personalized-analysis-panel__row">
        <label>
          Resume variant
          <select value={variant} onChange={(event) => { setVariant(event.target.value); invalidatePreviousApproval(); }}>
            {VARIANTS.map((value) => (
              <option key={value} value={value}>{AI_JOB_TRACK_LABELS[value] ?? value}</option>
            ))}
          </select>
        </label>
        <label>
          Analysis mode
          <select value={mode} onChange={(event) => { setMode(event.target.value); invalidatePreviousApproval(); }}>
            <option value="mock">Mock (safe, no OpenAI request)</option>
            <option value="openai">Live OpenAI (sends your approved text to OpenAI)</option>
          </select>
        </label>
      </div>

      <button
        type="button"
        className="personalized-analysis-panel__action"
        onClick={handlePreview}
        disabled={!resumeText.trim() || preview.isLoading}
      >
        {preview.isLoading ? "Generating preview..." : "Preview sanitized text"}
      </button>

      {preview.status === "error" && <ErrorState message={preview.error} onRetry={handlePreview} />}

      {preview.status === "success" && (
        <div className="personalized-analysis-panel__preview">
          <p className="personalized-analysis-panel__preview-label">
            Sanitized preview -- this exact text is what would be analyzed
          </p>
          <pre className="personalized-analysis-panel__preview-text">{preview.data.preview}</pre>
          <label className="personalized-analysis-panel__confirm">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
            I have reviewed every line above and approve sending this exact text for{" "}
            {mode === "openai" ? "a live OpenAI request" : "mock analysis"}.
          </label>

          <div className="personalized-analysis-panel__approved-actions">
            <button
              type="button"
              className="personalized-analysis-panel__action"
              onClick={handleAnalyze}
              disabled={!confirmed || analysis.isLoading}
            >
              {analysis.isLoading ? "Analyzing..." : "Approve & run personalized analysis"}
            </button>
            <button
              type="button"
              className="personalized-analysis-panel__action personalized-analysis-panel__action--secondary"
              onClick={handleAssistance}
              disabled={!confirmed || assistance.isLoading}
            >
              {assistance.isLoading ? "Generating..." : "Generate application assistance"}
            </button>
          </div>
        </div>
      )}

      {analysis.status === "loading" && <LoadingState label="Running personalized analysis..." />}
      {analysis.status === "error" && <ErrorState message={analysis.error} onRetry={handleAnalyze} />}

      {analysis.status === "success" && analysis.data && (
        <div className="personalized-analysis-panel__results">
          {analysis.data.variant_matches_job_track === false && (
            <Notice tone="warning">
              The {AI_JOB_TRACK_LABELS[variant] ?? variant} variant you selected does not match
              this job's own detected career track. Consider reviewing a different variant.
            </Notice>
          )}
          {analysis.data.live_job_analysis && (
            <div className="personalized-analysis-panel__live-job-analysis">
              <p className="personalized-analysis-panel__field-label">
                Live AI interpretation of this job (independent of the deterministic comparison below)
              </p>
              <p>{analysis.data.live_job_analysis.summary}</p>
            </div>
          )}
          <RequirementComparisonPanel comparison={comparisonForDisplay} />
        </div>
      )}

      {assistance.status === "loading" && <LoadingState label="Generating application assistance..." />}
      {assistance.status === "error" && <ErrorState message={assistance.error} onRetry={handleAssistance} />}

      {assistance.status === "success" && assistance.data && (
        <div className="personalized-analysis-panel__assistance">
          <p className="personalized-analysis-panel__field-label">Resume suggestions</p>
          <ul className="personalized-analysis-panel__plain-list">
            {assistance.data.assistance.resume_suggestions.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>

          <p className="personalized-analysis-panel__field-label">Bullet-point rewrites</p>
          <ul className="personalized-analysis-panel__plain-list">
            {assistance.data.assistance.bullet_rewrites.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>

          <p className="personalized-analysis-panel__field-label">Cover-letter draft</p>
          <pre className="personalized-analysis-panel__preview-text">
            {assistance.data.assistance.cover_letter_draft}
          </pre>

          <p className="personalized-analysis-panel__field-label">Interview talking points</p>
          <ul className="personalized-analysis-panel__plain-list">
            {assistance.data.assistance.interview_talking_points.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>

          <ul className="personalized-analysis-panel__plain-list">
            {assistance.data.assistance.limitations.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
