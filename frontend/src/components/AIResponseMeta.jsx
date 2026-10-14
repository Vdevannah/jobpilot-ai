import "./AIResponseMeta.css";

// Surfaces the trust-relevant fields every Phase 8E AI response carries
// (analysis_mode, evidence_source, personalized, requires_human_review,
// status) as always-visible badges, so a viewer never mistakes mock,
// fictional, unreviewed output for a verified, personalized recommendation.
export default function AIResponseMeta({
  analysisMode,
  evidenceSource,
  personalized,
  requiresHumanReview,
  status,
}) {
  return (
    <div className="ai-meta" role="status">
      {analysisMode ? (
        <span className="ai-meta__badge ai-meta__badge--mock">
          {analysisMode === "mock" ? "Mock analysis" : analysisMode}
        </span>
      ) : null}
      <span
        className={`ai-meta__badge ${
          evidenceSource === "fictional_mock_fixture" ? "ai-meta__badge--mock" : "ai-meta__badge--unavailable"
        }`}
      >
        {evidenceSource === "fictional_mock_fixture" ? "Fictional evidence only" : "No evidence available"}
      </span>
      <span className="ai-meta__badge">{personalized ? "Personalized" : "Not personalized"}</span>
      {requiresHumanReview ? (
        <span className="ai-meta__badge ai-meta__badge--review">Requires human review</span>
      ) : null}
      {status ? <span className="ai-meta__badge">{status.replace("_", " ")}</span> : null}
    </div>
  );
}
