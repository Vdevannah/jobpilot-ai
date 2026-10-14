import { useEffect, useState } from "react";
import { getJobs, getMatches } from "../api/client";
import StatTile from "../components/StatTile";
import JobPreviewList from "../components/JobPreviewList";
import { LoadingState, ErrorState, EmptyState } from "../components/AsyncState";
import "./Dashboard.css";

const STRONG_MATCH_THRESHOLD = 80;
const TOP_JOBS_PREVIEW_COUNT = 5;

function average(numbers) {
  if (numbers.length === 0) return 0;
  return numbers.reduce((sum, value) => sum + value, 0) / numbers.length;
}

export default function Dashboard() {
  const [state, setState] = useState({ status: "loading", jobs: [], matches: [], error: null });
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [jobs, matches] = await Promise.all([getJobs(), getMatches()]);
        if (!cancelled) setState({ status: "ready", jobs, matches, error: null });
      } catch (error) {
        if (!cancelled) setState({ status: "error", jobs: [], matches: [], error: error.message });
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  function retry() {
    setState({ status: "loading", jobs: [], matches: [], error: null });
    setReloadToken((token) => token + 1);
  }

  if (state.status === "loading") {
    return <LoadingState label="Loading dashboard data..." />;
  }

  if (state.status === "error") {
    return <ErrorState message={state.error} onRetry={retry} />;
  }

  const totalJobs = state.jobs.length;
  const strongMatches = state.matches.filter((match) => match.overall_score >= STRONG_MATCH_THRESHOLD);
  const averageScore = average(state.matches.map((match) => match.overall_score));
  const topJobs = [...state.matches]
    .sort((a, b) => b.overall_score - a.overall_score)
    .slice(0, TOP_JOBS_PREVIEW_COUNT);

  return (
    <div className="dashboard">
      <section className="dashboard__stats">
        <StatTile label="Total jobs" value={totalJobs} />
        <StatTile
          label="Strong matches"
          value={strongMatches.length}
          hint={`${STRONG_MATCH_THRESHOLD}%+ overall score`}
        />
        <StatTile label="Average match score" value={`${averageScore.toFixed(1)}%`} />
      </section>

      <section className="dashboard__panel">
        <h2 className="dashboard__panel-title">Top-ranked jobs</h2>
        {topJobs.length === 0 ? (
          <EmptyState message="No jobs are available yet. Run the job collection script to populate the dashboard." />
        ) : (
          <JobPreviewList matches={topJobs} />
        )}
      </section>
    </div>
  );
}
