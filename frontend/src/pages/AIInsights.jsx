import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getAIReview, getJobs } from "../api/client";
import { useApiQuery } from "../hooks/useApiQuery";
import { useLazyRequest } from "../hooks/useLazyRequest";
import JobPicker from "../components/JobPicker";
import JobContextCard from "../components/JobContextCard";
import AIResponseMeta from "../components/AIResponseMeta";
import Notice from "../components/Notice";
import PageHeader from "../components/PageHeader";
import { LoadingState, ErrorState, EmptyState } from "../components/AsyncState";
import { AI_JOB_TRACK_LABELS, RESUME_VARIANT_LABELS } from "../utils/aiLabels";
import "./AIInsights.css";

// The API repeats each critic's warnings inside data.warnings (deduplicated
// across variants) so a consumer that only reads the top-level list never
// misses one. Since this page already renders each critic's warnings in
// its own card below, re-showing them again as top-level banners would just
// be the same disclosure twice -- so the top banner keeps only the warnings
// that aren't already covered by a critic card, which in practice leaves
// just the one general mock-analysis warning.
function primaryWarnings(data) {
  const criticWarnings = new Set(
    data.critic_reports ? Object.values(data.critic_reports).flatMap((report) => report.warnings) : [],
  );
  return (data.warnings ?? []).filter((warning) => !criticWarnings.has(warning));
}

export default function AIInsights() {
  const [searchParams] = useSearchParams();
  const [selectedJobId, setSelectedJobId] = useState(searchParams.get("jobId") ?? null);

  const { isLoading: jobsLoading, data: jobs, error: jobsError } = useApiQuery(() => getJobs(), []);
  const { status, data, error, isLoading, run, reset } = useLazyRequest(getAIReview);

  useEffect(() => {
    reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedJobId]);

  if (jobsLoading) {
    return <LoadingState label="Loading discovered jobs..." />;
  }

  if (jobsError) {
    return <ErrorState message={jobsError} />;
  }

  const selectedJob = jobs.find((job) => String(job.id) === String(selectedJobId)) ?? null;
  const trackLabel = data?.job_analysis?.job_track
    ? AI_JOB_TRACK_LABELS[data.job_analysis.job_track] ?? data.job_analysis.job_track
    : null;

  return (
    <div className="ai-insights">
      <PageHeader
        title="AI Insights"
        subtitle="Explore mock AI analysis of job requirements and potential fit."
      />

      <div className="ai-insights__mock-indicator">
        <span className="ai-insights__mock-label">Mock AI Analysis</span>
        <p>
          This analysis uses JobPilot AI's mock workflow: fixed, pre-written sample output that
          does not read or analyze the selected job's actual description -- not a live OpenAI
          analysis of your personal resumes. Research findings and critic warnings below are
          fictional demonstration data and have not been reviewed by a human yet. You must
          independently verify the job requirements and this analysis before making any
          application decisions.
        </p>
      </div>

      {jobs.length === 0 ? (
        <EmptyState message="No jobs are available yet. Run the job collection script to populate the dashboard." />
      ) : (
        <JobPicker
          selectId="insights-job-select"
          jobs={jobs}
          selectedJobId={selectedJobId}
          onSelectJob={setSelectedJobId}
          onRequest={() => run(selectedJobId)}
          requestLabel={isLoading ? "Requesting..." : "Request AI review"}
          requestDisabled={isLoading}
        />
      )}

      <JobContextCard job={selectedJob} trackLabel={trackLabel} />

      {status === "error" && <ErrorState message={error} onRetry={() => run(selectedJobId)} />}

      {status === "loading" && <LoadingState label="Requesting mock AI review..." />}

      {status === "success" && data && (
        <section className="ai-insights__result">
          <AIResponseMeta
            analysisMode={data.analysis_mode}
            evidenceSource={data.evidence_source}
            personalized={data.personalized}
            requiresHumanReview={data.requires_human_review}
            status={data.status}
          />

          {primaryWarnings(data).map((warning) => (
            <Notice key={warning} tone="warning">
              {warning}
            </Notice>
          ))}

          {!data.job_analysis ? (
            <EmptyState message="No AI review or resume ranking was produced for this job." />
          ) : (
            <>
              <div className="ai-insights__block">
                <h3>Mock job analysis</h3>
                <p className="ai-insights__summary">{data.job_analysis.summary}</p>
                <dl className="ai-insights__facts">
                  <div>
                    <dt>Career track</dt>
                    <dd>{AI_JOB_TRACK_LABELS[data.job_analysis.job_track] ?? data.job_analysis.job_track}</dd>
                  </div>
                  <div>
                    <dt>Minimum experience</dt>
                    <dd>
                      {data.job_analysis.minimum_experience_years != null
                        ? `${data.job_analysis.minimum_experience_years} yrs`
                        : "Not detected"}
                    </dd>
                  </div>
                  <div>
                    <dt>Required skills</dt>
                    <dd>{data.job_analysis.required_skills.join(", ") || "None detected"}</dd>
                  </div>
                  <div>
                    <dt>Preferred skills</dt>
                    <dd>{data.job_analysis.preferred_skills.join(", ") || "None detected"}</dd>
                  </div>
                </dl>
              </div>

              {data.research_report && (
                <div className="ai-insights__block">
                  <h3>Research findings</h3>
                  <p className="ai-insights__summary">{data.research_report.summary}</p>
                  {data.research_report.missing_information.length > 0 && (
                    <>
                      <p className="ai-insights__block-label">Missing information</p>
                      <ul className="ai-insights__list">
                        {data.research_report.missing_information.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </>
                  )}
                  {data.research_report.research_questions.length > 0 && (
                    <>
                      <p className="ai-insights__block-label">Open research questions</p>
                      <ul className="ai-insights__list">
                        {data.research_report.research_questions.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>
              )}

              {data.critic_reports && (
                <div className="ai-insights__block">
                  <h3>Critic review (per fictional resume variant)</h3>
                  <ul className="ai-insights__critic-list">
                    {["pharma", "data", "scientific_ai"].map((variant) => {
                      const report = data.critic_reports[variant];
                      if (!report) return null;
                      return (
                        <li key={variant} className="ai-insights__critic-card">
                          <div className="ai-insights__critic-header">
                            <h4>{RESUME_VARIANT_LABELS[variant]}</h4>
                            {report.requires_human_review && (
                              <span className="ai-insights__review-flag">Requires human review</span>
                            )}
                          </div>
                          <p className="ai-insights__summary">{report.summary}</p>
                          {report.warnings.length > 0 && (
                            <ul className="ai-insights__list">
                              {report.warnings.map((warning) => (
                                <li key={warning}>{warning}</li>
                              ))}
                            </ul>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}

              {data.limitations?.length > 0 && (
                <div className="ai-insights__block">
                  <p className="ai-insights__block-label">Analysis limitations</p>
                  <ul className="ai-insights__overall-limitations">
                    {data.limitations.map((limitation) => (
                      <li key={limitation}>{limitation}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </section>
      )}
    </div>
  );
}
