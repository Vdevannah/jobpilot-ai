import { Link } from "react-router-dom";
import ScoreBadge from "./ScoreBadge";
import DemoRecordBadge from "./DemoRecordBadge";
import { isDemoRecord } from "../utils/demoRecord";
import "./JobListingsTable.css";

// `source` is passed in per-row (joined from the /jobs list by the caller)
// because GET /matches does not currently return it -- this table never
// invents it, and shows "Not available" rather than guessing.
export default function JobListingsTable({ rows }) {
  return (
    <div className="job-listings-table__scroll">
      <table className="job-listings-table">
        <thead>
          <tr>
            <th scope="col">Job title</th>
            <th scope="col">Company</th>
            <th scope="col">Location</th>
            <th scope="col">Source</th>
            <th scope="col">Match score</th>
            <th scope="col">
              <span className="visually-hidden">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.job_id}>
              <td className="job-listings-table__title-cell">
                <Link to={`/jobs/${row.job_id}`} className="job-listings-table__title-link" title={row.title}>
                  {row.title}
                </Link>
                {isDemoRecord(row) && <DemoRecordBadge />}
              </td>
              <td>{row.company}</td>
              <td>{row.location}</td>
              <td>{row.source ?? "Not available"}</td>
              <td className="job-listings-table__score-cell">
                <ScoreBadge score={row.overall_score} />
              </td>
              <td className="job-listings-table__actions-cell">
                <Link to={`/jobs/${row.job_id}`} className="job-listings-table__view-link">
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
