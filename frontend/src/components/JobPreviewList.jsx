import ScoreBadge from "./ScoreBadge";
import DemoRecordBadge from "./DemoRecordBadge";
import { isDemoRecord } from "../utils/demoRecord";
import "./JobPreviewList.css";

export default function JobPreviewList({ matches }) {
  return (
    <ul className="job-preview-list">
      {matches.map((match) => (
        <li key={match.job_id} className="job-preview-row">
          <div className="job-preview-row__main">
            <a
              href={match.url}
              target="_blank"
              rel="noreferrer"
              className="job-preview-row__title"
            >
              {match.title}
            </a>
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
