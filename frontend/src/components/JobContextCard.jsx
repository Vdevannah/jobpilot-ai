import { BuildingIcon, MapPinIcon } from "./icons";
import "./JobContextCard.css";

// Shows whatever the selected job's own record already has (title, company,
// location) -- never fetches anything extra. `trackLabel` is optional and
// only ever passed once an AI response has actually returned a
// job_analysis.job_track; before that, there is no track to show, and none
// is invented.
export default function JobContextCard({ job, trackLabel }) {
  if (!job) return null;

  return (
    <div className="job-context-card">
      <div>
        <h3 className="job-context-card__title">{job.title}</h3>
        <p className="job-context-card__meta">
          <span className="job-context-card__meta-item">
            <BuildingIcon className="job-context-card__meta-icon" />
            {job.company}
          </span>
          <span className="job-context-card__meta-item">
            <MapPinIcon className="job-context-card__meta-icon" />
            {job.location}
          </span>
        </p>
      </div>
      {trackLabel ? <span className="job-context-card__track">{trackLabel}</span> : null}
    </div>
  );
}
