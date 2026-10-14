import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { getJobById, getMatches } from "../api/client";
import { useApiQuery } from "../hooks/useApiQuery";
import ScoreBadge from "../components/ScoreBadge";
import TrackBadge from "../components/TrackBadge";
import SkillSummary from "../components/SkillSummary";
import Notice from "../components/Notice";
import DemoRecordBadge from "../components/DemoRecordBadge";
import { LoadingState, ErrorState } from "../components/AsyncState";
import { SCORE_MEANING } from "../utils/scoreTier";
import { TRACK_LABELS } from "../utils/trackLabels";
import { isDemoRecord } from "../utils/demoRecord";
import "./JobDetail.css";

const SCORE_ROWS = [
  { key: "skill_score", label: "Skill score" },
  { key: "experience_score", label: "Experience score" },
  { key: "role_score", label: "Role score" },
  { key: "domain_score", label: "Domain score" },
  { key: "location_score", label: "Location score" },
];

export default function JobDetail() {
  const { jobId } = useParams();

  const { isLoading: jobLoading, data: job, error: jobError } = useApiQuery(
    () => getJobById(jobId),
    [jobId],
  );
  const { isLoading: matchesLoading, data: matches } = useApiQuery(() => getMatches(), [jobId]);

  const match = useMemo(() => {
    if (!matches) return null;
    return matches.find((item) => String(item.job_id) === String(jobId)) ?? null;
  }, [matches, jobId]);

  if (jobLoading) {
    return <LoadingState label="Loading job details..." />;
  }

  if (jobError) {
    return <ErrorState message={jobError} />;
  }

  const trackLabel = match?.job_track ? TRACK_LABELS[match.job_track] ?? match.job_track : null;

  return (
    <div className="job-detail">
      <Link to="/discover" className="job-detail__back">
        &larr; Back to Discover Jobs
      </Link>

      <header className="job-detail__header">
        <div className="job-detail__title-row">
          <h2 className="job-detail__title">{job.title}</h2>
          {isDemoRecord(job) && <DemoRecordBadge />}
        </div>
        <p className="job-detail__meta">
          {job.company} &middot; {job.location} &middot; {job.source}
        </p>
        <a href={job.url} target="_blank" rel="noreferrer" className="job-detail__posting-link">
          View original posting ↗
        </a>
      </header>

      <nav className="job-detail__ai-links" aria-label="AI preview pages for this job">
        <Link to={`/resumes?jobId=${encodeURIComponent(jobId)}`} className="job-detail__ai-link">
          Get resume recommendation ↗
        </Link>
        <Link to={`/insights?jobId=${encodeURIComponent(jobId)}`} className="job-detail__ai-link">
          View AI insights ↗
        </Link>
      </nav>

      <section className="job-detail__section">
        <h3 className="job-detail__section-title">Description</h3>
        {job.description ? (
          <p className="job-detail__description">{job.description}</p>
        ) : (
          <>
            <p className="job-detail__description job-detail__description--empty">
              No description is available for this job posting.
            </p>
            <Notice tone="warning">
              Because no description is available, the match score below is based on limited job
              information.
            </Notice>
          </>
        )}
      </section>

      <section className="job-detail__section">
        <h3 className="job-detail__section-title">Match score breakdown</h3>
        {matchesLoading ? (
          <LoadingState label="Loading score breakdown..." />
        ) : !match ? (
          <p className="job-detail__no-match">No score breakdown is available for this job.</p>
        ) : (
          <>
            <Notice tone="info">{SCORE_MEANING}</Notice>

            <div className="job-detail__score-summary">
              <ScoreBadge score={match.overall_score} />
              <span className="job-detail__recommendation">{match.recommendation}</span>
              <TrackBadge track={match.job_track} />
            </div>

            <dl className="job-detail__score-grid">
              {SCORE_ROWS.map((row) => (
                <div key={row.key} className="job-detail__score-row">
                  <dt>{row.label}</dt>
                  <dd>{match[row.key].toFixed(1)}</dd>
                </div>
              ))}
              <div className="job-detail__score-row">
                <dt>{trackLabel ? `Candidate experience (${trackLabel} track)` : "Candidate experience"}</dt>
                <dd>{trackLabel ? `${match.candidate_years.toFixed(1)} yrs` : "Not applicable"}</dd>
              </div>
              <div className="job-detail__score-row">
                <dt>Required experience</dt>
                <dd>{match.required_years != null ? `${match.required_years} yrs` : "Not detected"}</dd>
              </div>
            </dl>

            <p className="job-detail__experience-hint">
              {trackLabel
                ? `This reflects the candidate's experience in the ${trackLabel} track only -- it is not their total professional experience across all tracks.`
                : "No career track was detected for this job, so track-specific experience could not be compared. This does not mean the candidate has no professional experience."}
            </p>

            <div className="job-detail__skills">
              <SkillSummary matchedSkills={match.matched_skills} missingSkills={match.missing_skills} />
            </div>

            {match.reasons.length > 0 && (
              <ul className="job-detail__reasons">
                {match.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>
    </div>
  );
}
