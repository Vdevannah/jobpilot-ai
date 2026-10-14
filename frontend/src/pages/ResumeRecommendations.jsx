import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getJobs, getResumeRecommendation } from "../api/client";
import { useApiQuery } from "../hooks/useApiQuery";
import { useLazyRequest } from "../hooks/useLazyRequest";
import JobPicker from "../components/JobPicker";
import JobContextCard from "../components/JobContextCard";
import AIResponseMeta from "../components/AIResponseMeta";
import Notice from "../components/Notice";
import PageHeader from "../components/PageHeader";
import { LoadingState, ErrorState, EmptyState } from "../components/AsyncState";
import { AI_JOB_TRACK_LABELS, RESUME_VARIANT_LABELS } from "../utils/aiLabels";
import "./ResumeRecommendations.css";

export default function ResumeRecommendations() {
  const [searchParams] = useSearchParams();
  const [selectedJobId, setSelectedJobId] = useState(searchParams.get("jobId") ?? null);

  const { isLoading: jobsLoading, data: jobs, error: jobsError } = useApiQuery(() => getJobs(), []);
  const { status, data, error, isLoading, run, reset } = useLazyRequest(getResumeRecommendation);

  useEffect(() => {
    reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedJobId]);

  function handleSelectJob(jobId) {
    setSelectedJobId(jobId);
  }

  if (jobsLoading) {
    return <LoadingState label="Loading discovered jobs..." />;
  }

  if (jobsError) {
    return <ErrorState message={jobsError} />;
  }

  const recommendation = data?.recommendation ?? null;
  const rankingByVariant = recommendation
    ? Object.fromEntries(recommendation.rankings.map((ranking) => [ranking.variant, ranking]))
    : {};
  const selectedJob = jobs.find((job) => String(job.id) === String(selectedJobId)) ?? null;
  const trackLabel = data?.job_analysis?.job_track
    ? AI_JOB_TRACK_LABELS[data.job_analysis.job_track] ?? data.job_analysis.job_track
    : null;
  const leaderRanking =
    recommendation && !recommendation.insufficient_evidence && recommendation.recommended_variant
      ? rankingByVariant[recommendation.recommended_variant]
      : null;

  return (
    <div className="resume-recommendations">
      <PageHeader
        title="Resume Recommendations"
        subtitle="Compare resume variants recommended for each opportunity."
      />

      <Notice tone="warning">
        All resume evidence below is fictional demonstration data for three sample variants
        (Pharma, Data, Scientific AI) -- not personalized to any real candidate, and requiring
        human review before any real application.
      </Notice>

      {jobs.length === 0 ? (
        <EmptyState message="No jobs are available yet. Run the job collection script to populate the dashboard." />
      ) : (
        <JobPicker
          selectId="resume-job-select"
          jobs={jobs}
          selectedJobId={selectedJobId}
          onSelectJob={handleSelectJob}
          onRequest={() => run(selectedJobId)}
          requestLabel={isLoading ? "Requesting..." : "Get resume recommendation"}
          requestDisabled={isLoading}
        />
      )}

      <JobContextCard job={selectedJob} trackLabel={trackLabel} />

      {status === "error" && <ErrorState message={error} onRetry={() => run(selectedJobId)} />}

      {status === "loading" && <LoadingState label="Requesting mock resume recommendation..." />}

      {status === "success" && data && (
        <section className="resume-recommendations__result">
          <AIResponseMeta
            analysisMode={data.analysis_mode}
            evidenceSource={data.evidence_source}
            personalized={data.personalized}
            requiresHumanReview={data.requires_human_review}
            status={data.status}
          />

          {data.warnings?.map((warning) => (
            <Notice key={warning} tone="warning">
              {warning}
            </Notice>
          ))}

          {!data.job_analysis || !recommendation ? (
            <EmptyState message="No job analysis or resume ranking was produced for this job." />
          ) : (
            <>
              <div className="resume-recommendations__job-analysis">
                <h3>Mock job analysis</h3>
                <p>{data.job_analysis.summary}</p>
              </div>

              <div className="resume-recommendations__headline">
                {recommendation.insufficient_evidence ? (
                  <Notice tone="warning">
                    No variant had enough matching evidence to recommend over the others.
                  </Notice>
                ) : recommendation.tied_variants.length > 0 ? (
                  <Notice tone="info">
                    Tied ranking points between:{" "}
                    {recommendation.tied_variants
                      .map((variant) => RESUME_VARIANT_LABELS[variant] ?? variant)
                      .join(", ")}
                    . Human review is required to break the tie.
                  </Notice>
                ) : (
                  <Notice tone="info">
                    Highest ranking points: {RESUME_VARIANT_LABELS[recommendation.recommended_variant] ??
                      recommendation.recommended_variant}
                  </Notice>
                )}
              </div>

              {leaderRanking && (
                <div className="resume-recommendations__leader-card">
                  <p className="resume-recommendations__leader-label">Recommended resume</p>
                  <div className="resume-recommendations__leader-headline">
                    <h3 className="resume-recommendations__leader-variant">
                      {RESUME_VARIANT_LABELS[leaderRanking.variant] ?? leaderRanking.variant}
                    </h3>
                    <div className="resume-recommendations__leader-points">
                      <span className="resume-recommendations__leader-points-value">
                        {leaderRanking.score}
                      </span>
                      <span className="resume-recommendations__leader-points-label">
                        ranking points
                      </span>
                    </div>
                  </div>
                  {leaderRanking.reasons.length > 0 && (
                    <>
                      <p className="resume-recommendations__leader-heading">Why this variant</p>
                      <ul className="resume-recommendations__reasons">
                        {leaderRanking.reasons.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    </>
                  )}
                  {leaderRanking.limitations.length > 0 && (
                    <ul className="resume-recommendations__limitations">
                      {leaderRanking.limitations.map((limitation) => (
                        <li key={limitation}>{limitation}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              <h3 className="resume-recommendations__comparison-title">Resume comparison</h3>
              <p className="resume-recommendations__points-note">
                Ranking points below come directly from the existing Phase 7 deterministic
                resume-selection algorithm (matched skills, education, and track-specific
                experience). They are relative comparison points only -- not a percentage, a
                hiring probability, or a judgment of candidate suitability -- and have no fixed
                maximum, since it depends on how many skills a job's description lists.
              </p>

              <ul className="resume-recommendations__rankings">
                {["pharma", "data", "scientific_ai"].map((variant) => {
                  const ranking = rankingByVariant[variant];
                  if (!ranking) return null;
                  const isLeader =
                    ranking.variant === recommendation.recommended_variant ||
                    recommendation.tied_variants.includes(ranking.variant);
                  return (
                    <li
                      key={variant}
                      className={`resume-recommendations__variant-card ${
                        isLeader ? "resume-recommendations__variant-card--leader" : ""
                      }`}
                    >
                      <div className="resume-recommendations__variant-header">
                        <h4>{RESUME_VARIANT_LABELS[variant]}</h4>
                        <span className="resume-recommendations__score">
                          Ranking points: {ranking.score}
                        </span>
                      </div>

                      {ranking.reasons.length > 0 && (
                        <ul className="resume-recommendations__reasons">
                          {ranking.reasons.map((reason) => (
                            <li key={reason}>{reason}</li>
                          ))}
                        </ul>
                      )}

                      {ranking.limitations.length > 0 && (
                        <ul className="resume-recommendations__limitations">
                          {ranking.limitations.map((limitation) => (
                            <li key={limitation}>{limitation}</li>
                          ))}
                        </ul>
                      )}
                    </li>
                  );
                })}
              </ul>

              {recommendation.limitations.length > 0 && (
                <ul className="resume-recommendations__overall-limitations">
                  {recommendation.limitations.map((limitation) => (
                    <li key={limitation}>{limitation}</li>
                  ))}
                </ul>
              )}
            </>
          )}
        </section>
      )}
    </div>
  );
}
