import { useState, useEffect } from "react";
import { getJobs, getMatches } from "../api/client";
import DashboardHero from "../components/DashboardHero";
import KpiCard from "../components/KpiCard";
import StatTile from "../components/StatTile";
import ChartCard from "../components/ChartCard";
import BarChart from "../components/BarChart";
import DonutChart from "../components/DonutChart";
import JobListingsTable from "../components/JobListingsTable";
import { BriefcaseIcon, BuildingIcon, MapPinIcon, SourceIcon } from "../components/icons";
import { LoadingState, ErrorState, EmptyState } from "../components/AsyncState";
import { countBy, countDistinct, topNWithOther } from "../utils/jobStats";
import { withSourceFromJobs } from "../utils/jobSourceLookup";
import "./Dashboard.css";

const STRONG_MATCH_THRESHOLD = 80;
const RECENT_JOBS_LIMIT = 8;
const CHART_CATEGORY_LIMIT = 4;

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

  const { jobs, matches } = state;
  const totalJobs = jobs.length;
  const totalCompanies = countDistinct(jobs, (job) => job.company);
  const totalLocations = countDistinct(jobs, (job) => job.location);
  const totalSources = countDistinct(jobs, (job) => job.source);

  const strongMatches = matches.filter((match) => match.overall_score >= STRONG_MATCH_THRESHOLD);
  const averageScore = average(matches.map((match) => match.overall_score));

  const sourceGroups = topNWithOther(countBy(jobs, (job) => job.source), CHART_CATEGORY_LIMIT);
  const locationGroups = topNWithOther(countBy(jobs, (job) => job.location), CHART_CATEGORY_LIMIT);

  // GET /matches doesn't return a job's source, so it's joined in from the
  // already-fetched /jobs list (shared utils/jobSourceLookup, also used by
  // Job Matches) rather than guessed or hidden.
  const recentJobs = withSourceFromJobs(
    [...matches].sort((a, b) => b.job_id - a.job_id).slice(0, RECENT_JOBS_LIMIT),
    jobs,
  );

  return (
    <div className="dashboard">
      <DashboardHero />

      <section className="dashboard__kpis">
        <KpiCard label="Total jobs" value={totalJobs} icon={<BriefcaseIcon />} accent="blue" />
        <KpiCard label="Companies" value={totalCompanies} icon={<BuildingIcon />} accent="green" />
        <KpiCard label="Locations" value={totalLocations} icon={<MapPinIcon />} accent="purple" />
        <KpiCard label="Sources" value={totalSources} icon={<SourceIcon />} accent="orange" />
      </section>

      <section className="dashboard__secondary-stats">
        <StatTile
          label="Strong matches"
          value={strongMatches.length}
          hint={`${STRONG_MATCH_THRESHOLD}%+ overall score`}
        />
        <StatTile label="Average match score" value={`${averageScore.toFixed(1)}%`} />
      </section>

      <section className="dashboard__charts">
        <ChartCard title="Jobs by source">
          <BarChart data={sourceGroups} unitLabel="jobs" />
        </ChartCard>
        <ChartCard title="Jobs by location">
          <DonutChart data={locationGroups} total={totalJobs} unitLabel="jobs" />
        </ChartCard>
      </section>

      <section className="dashboard__panel">
        <h2 className="dashboard__panel-title">Recent job listings</h2>
        <p className="dashboard__panel-caption">
          Ordered by when each job was added to JobPilot AI's database, not by its original
          posting date.
        </p>
        {recentJobs.length === 0 ? (
          <EmptyState message="No jobs are available yet. Run the job collection script to populate the dashboard." />
        ) : (
          <JobListingsTable rows={recentJobs} />
        )}
      </section>
    </div>
  );
}
