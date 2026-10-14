import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getJobs, getMatches } from "../api/client";
import { useApiQuery } from "../hooks/useApiQuery";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import FilterField from "../components/FilterField";
import Pagination from "../components/Pagination";
import ScoreBadge from "../components/ScoreBadge";
import TrackBadge from "../components/TrackBadge";
import SkillSummary from "../components/SkillSummary";
import Notice from "../components/Notice";
import DemoRecordBadge from "../components/DemoRecordBadge";
import PageHeader from "../components/PageHeader";
import { LoadingState, ErrorState, EmptyState } from "../components/AsyncState";
import { BuildingIcon, MapPinIcon, SourceIcon } from "../components/icons";
import { SCORE_MEANING } from "../utils/scoreTier";
import { isDemoRecord } from "../utils/demoRecord";
import { withSourceFromJobs } from "../utils/jobSourceLookup";
import "./JobMatches.css";

const PAGE_SIZE = 10;

// job_track filter options are deliberately limited to the deterministic
// Phase 1-6 values the backend's job_track query parameter actually accepts
// (pharma/data), plus a client-side-only "unknown" bucket for jobs with no
// detected track. scientific_ai (a Phase 7 AI-track value) is never offered
// here -- GET /matches has no such track and would reject it.
const TRACK_OPTIONS = [
  { value: "", label: "All tracks" },
  { value: "pharma", label: "Pharma" },
  { value: "data", label: "Data" },
  { value: "unknown", label: "Unknown / not detected" },
];

const SORT_OPTIONS = [
  { value: "score", label: "Score (high to low)" },
  { value: "location", label: "Location (A-Z)" },
  { value: "source", label: "Source (A-Z)" },
  { value: "track", label: "Track (A-Z)" },
];

function sortMatches(matches, sortBy) {
  const sorted = [...matches];
  switch (sortBy) {
    case "location":
      return sorted.sort((a, b) => a.location.localeCompare(b.location));
    case "source":
      // source can be null when no corresponding job was found to join it
      // from (see utils/jobSourceLookup) -- sort those to the end rather
      // than crashing on a null .localeCompare call.
      return sorted.sort((a, b) => (a.source ?? "zzz").localeCompare(b.source ?? "zzz"));
    case "track":
      return sorted.sort((a, b) => (a.job_track ?? "zzz").localeCompare(b.job_track ?? "zzz"));
    case "score":
    default:
      return sorted.sort((a, b) => b.overall_score - a.overall_score);
  }
}

export default function JobMatches() {
  const [location, setLocation] = useState("");
  const [source, setSource] = useState("");
  const [track, setTrack] = useState("");
  const [minScore, setMinScore] = useState("");
  const [sortBy, setSortBy] = useState("score");
  const [page, setPage] = useState(1);
  const [retryToken, setRetryToken] = useState(0);

  const debouncedLocation = useDebouncedValue(location);
  const debouncedSource = useDebouncedValue(source);
  const debouncedMinScore = useDebouncedValue(minScore);

  const apiParams = useMemo(
    () => ({
      location: debouncedLocation || undefined,
      source: debouncedSource || undefined,
      job_track: track === "pharma" || track === "data" ? track : undefined,
      min_score: debouncedMinScore === "" ? undefined : Number(debouncedMinScore),
    }),
    [debouncedLocation, debouncedSource, track, debouncedMinScore],
  );

  const { isLoading, data: matches, error } = useApiQuery(
    () => getMatches(apiParams),
    [apiParams, retryToken],
  );

  // GET /matches doesn't return a job's source (see utils/jobSourceLookup),
  // so the complete /jobs list is fetched once here -- stable deps, not
  // re-fetched on every filter change -- and joined in by job_id below.
  // getJobs() with no limit/offset returns every job (src/api.py only
  // slices when a limit is explicitly passed), so this join never misses a
  // job to a pagination boundary.
  const { data: allJobs } = useApiQuery(() => getJobs(), []);

  function updateFilter(setter) {
    return (event) => {
      setter(event.target.value);
      setPage(1);
    };
  }

  const visibleMatches = useMemo(() => {
    if (!matches) return [];
    const enriched = withSourceFromJobs(matches, allJobs);
    const filtered = track === "unknown" ? enriched.filter((match) => match.job_track == null) : enriched;
    return sortMatches(filtered, sortBy);
  }, [matches, allJobs, track, sortBy]);

  const pageCount = Math.max(1, Math.ceil(visibleMatches.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pageMatches = visibleMatches.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  function resetFilters() {
    setLocation("");
    setSource("");
    setTrack("");
    setMinScore("");
    setSortBy("score");
    setPage(1);
  }

  return (
    <div className="job-matches">
      <PageHeader
        title="Job Matches"
        subtitle="Review deterministic compatibility scores based on available job information."
      />

      <Notice tone="info">{SCORE_MEANING}</Notice>

      <form className="filter-bar" onSubmit={(event) => event.preventDefault()}>
        <FilterField label="Location" htmlFor="matches-location">
          <input
            id="matches-location"
            type="text"
            placeholder="e.g. Boston"
            value={location}
            onChange={updateFilter(setLocation)}
          />
        </FilterField>
        <FilterField label="Source" htmlFor="matches-source">
          <input
            id="matches-source"
            type="text"
            placeholder="e.g. greenhouse"
            value={source}
            onChange={updateFilter(setSource)}
          />
        </FilterField>
        <FilterField label="Career track" htmlFor="matches-track">
          <select id="matches-track" value={track} onChange={updateFilter(setTrack)}>
            {TRACK_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Minimum score" htmlFor="matches-min-score">
          <input
            id="matches-min-score"
            type="number"
            min="0"
            max="100"
            placeholder="0-100"
            value={minScore}
            onChange={updateFilter(setMinScore)}
          />
        </FilterField>
        <FilterField label="Sort by" htmlFor="matches-sort">
          <select
            id="matches-sort"
            value={sortBy}
            onChange={(event) => setSortBy(event.target.value)}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </FilterField>
        <button type="button" className="filter-bar__reset" onClick={resetFilters}>
          Reset filters
        </button>
      </form>

      {isLoading ? (
        <LoadingState label="Loading matches..." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => setRetryToken((value) => value + 1)} />
      ) : visibleMatches.length === 0 ? (
        <EmptyState message="No matches meet these filters." />
      ) : (
        <>
          <ul className="match-list">
            {pageMatches.map((match) => (
              <li key={match.job_id} className="match-card">
                <div className="match-card__header">
                  <div className="match-card__main">
                    <Link
                      to={`/jobs/${match.job_id}`}
                      className="match-card__title"
                      title="View full job details"
                    >
                      {match.title}
                      <span className="match-card__title-chevron" aria-hidden="true">
                        &rsaquo;
                      </span>
                    </Link>
                    <p className="match-card__meta">
                      <span className="match-card__meta-item">
                        <BuildingIcon className="match-card__meta-icon" />
                        {match.company}
                      </span>
                      <span className="match-card__meta-item">
                        <MapPinIcon className="match-card__meta-icon" />
                        {match.location}
                      </span>
                      <span className="match-card__meta-item">
                        <SourceIcon className="match-card__meta-icon" />
                        {match.source ?? "Source unavailable"}
                      </span>
                    </p>
                  </div>
                  <div className="match-card__badges">
                    {isDemoRecord(match) && <DemoRecordBadge />}
                    <TrackBadge track={match.job_track} />
                    <ScoreBadge score={match.overall_score} className="match-card__score" />
                  </div>
                </div>

                <p className="match-card__recommendation">{match.recommendation}</p>

                <div className="match-card__skills">
                  <SkillSummary matchedSkills={match.matched_skills} missingSkills={match.missing_skills} />
                </div>
              </li>
            ))}
          </ul>
          <Pagination
            page={currentPage}
            pageCount={pageCount}
            totalCount={visibleMatches.length}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
