import FilterField from "./FilterField";
import "./JobPicker.css";

// Lets the user choose one already-discovered job and explicitly trigger an
// action for it. Selecting a job never fetches anything by itself -- only
// clicking the action button does, so no AI request happens as a side
// effect of opening the page or changing the selection.
export default function JobPicker({
  jobs,
  selectedJobId,
  onSelectJob,
  onRequest,
  requestLabel,
  requestDisabled,
  selectId,
}) {
  return (
    <form className="job-picker" onSubmit={(event) => event.preventDefault()}>
      <FilterField label="Select a discovered job" htmlFor={selectId}>
        <select
          id={selectId}
          className="job-picker__select"
          value={selectedJobId ?? ""}
          onChange={(event) => onSelectJob(event.target.value || null)}
        >
          <option value="">Choose a job...</option>
          {jobs.map((job) => (
            <option key={job.id} value={job.id}>
              {job.title} -- {job.company}
            </option>
          ))}
        </select>
      </FilterField>
      <button
        type="button"
        className="job-picker__action"
        onClick={onRequest}
        disabled={!selectedJobId || requestDisabled}
      >
        {requestLabel}
      </button>
    </form>
  );
}
