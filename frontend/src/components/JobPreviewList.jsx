import { Link } from "react-router-dom";
import ScoreBadge from "./ScoreBadge";
import DemoRecordBadge from "./DemoRecordBadge";
import { isDemoRecord } from "../utils/demoRecord";
import { shouldShowPostingLink } from "../utils/postingLink";
import "./JobPreviewList.css";

export default function JobPreviewList({ matches }) {
  return (
    <ul className="job-preview-list">
      {matches.map((match) => (
        <li key={match.job_id} className="job-preview-row">
          <div className="job-preview-row__main">
            {shouldShowPostingLink(match) ? (
              <a
                href={match.url}
                target="_blank"
                rel="noreferrer"
                className="job-preview-row__title"
              >
                {match.title}
              </a>
            ) : (
              // No real external posting to open (e.g. a demo-seeded
              // placeholder record) -- link to the internal job detail
              // page instead of a dead https://example.com destination.
              <Link to={`/jobs/${match.job_id}`} className="job-preview-row__title">
                {match.title}
              </Link>
            )}
            <p className="job-preview-row__meta">
              {match.company} &middot; {match.location}
            </p>
          </div>
          {isDemoRecord(match) && <DemoRecordBadge />}
          <ScoreBadge score={match.overall_score} />
        </li>
      ))}
    </ul>
  );
}
