import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getJobs } from "../api/client";
import { useApiQuery } from "../hooks/useApiQuery";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import FilterField from "../components/FilterField";
import Pagination from "../components/Pagination";
import DemoRecordBadge from "../components/DemoRecordBadge";
import PageHeader from "../components/PageHeader";
import { LoadingState, ErrorState, EmptyState } from "../components/AsyncState";
import { BuildingIcon, MapPinIcon, SourceIcon } from "../components/icons";
import { isDemoRecord } from "../utils/demoRecord";
import { shouldShowPostingLink } from "../utils/postingLink";
import "./DiscoverJobs.css";

const PAGE_SIZE = 10;

export default function DiscoverJobs() {
  const [search, setSearch] = useState("");
  const [location, setLocation] = useState("");
  const [source, setSource] = useState("");
  const [page, setPage] = useState(1);
  const [retryToken, setRetryToken] = useState(0);

  const debouncedSearch = useDebouncedValue(search);
  const debouncedLocation = useDebouncedValue(location);
  const debouncedSource = useDebouncedValue(source);

  const apiParams = useMemo(
    () => ({ location: debouncedLocation || undefined, source: debouncedSource || undefined }),
    [debouncedLocation, debouncedSource],
  );

  const { isLoading, data: jobs, error } = useApiQuery(
    () => getJobs(apiParams),
    [apiParams, retryToken],
  );

  function updateFilter(setter) {
    return (event) => {
      setter(event.target.value);
      setPage(1);
    };
  }

  const searchedJobs = useMemo(() => {
    if (!jobs) return [];
    const term = debouncedSearch.trim().toLowerCase();
    if (!term) return jobs;
    return jobs.filter(
      (job) => job.title.toLowerCase().includes(term) || job.company.toLowerCase().includes(term),
    );
  }, [jobs, debouncedSearch]);

  const pageCount = Math.max(1, Math.ceil(searchedJobs.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pageJobs = searchedJobs.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  function resetFilters() {
    setSearch("");
    setLocation("");
    setSource("");
    setPage(1);
  }

  return (
    <div className="discover-jobs">
      <PageHeader
        title="Discover Opportunities"
        subtitle="Explore job opportunities collected from company career pages."
      />

      <form className="filter-bar" onSubmit={(event) => event.preventDefault()}>
        <FilterField label="Search title or company" htmlFor="discover-search">
          <input
            id="discover-search"
            type="search"
            placeholder="e.g. Data Engineer"
            value={search}
            onChange={updateFilter(setSearch)}
          />
        </FilterField>
        <FilterField label="Location" htmlFor="discover-location">
          <input
            id="discover-location"
            type="text"
            placeholder="e.g. Boston"
            value={location}
            onChange={updateFilter(setLocation)}
          />
        </FilterField>
        <FilterField label="Source" htmlFor="discover-source">
          <input
            id="discover-source"
            type="text"
            placeholder="e.g. greenhouse"
            value={source}
            onChange={updateFilter(setSource)}
          />
        </FilterField>
        <button type="button" className="filter-bar__reset" onClick={resetFilters}>
          Reset filters
        </button>
      </form>

      {isLoading ? (
        <LoadingState label="Loading jobs..." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => setRetryToken((value) => value + 1)} />
      ) : searchedJobs.length === 0 ? (
        <EmptyState message="No jobs match these filters." />
      ) : (
        <>
          <ul className="job-list">
            {pageJobs.map((job) => (
              <li key={job.id} className="job-card">
                <div className="job-card__main">
                  <div className="job-card__title-row">
                    <Link to={`/jobs/${job.id}`} className="job-card__title" title="View full job details">
                      {job.title}
                    </Link>
                    {isDemoRecord(job) && <DemoRecordBadge />}
                  </div>
                  <p className="job-card__meta">
                    <span className="job-card__meta-item">
                      <BuildingIcon className="job-card__meta-icon" />
                      {job.company}
                    </span>
                    <span className="job-card__meta-item">
                      <MapPinIcon className="job-card__meta-icon" />
                      {job.location}
                    </span>
                    <span className="job-card__meta-item">
                      <SourceIcon className="job-card__meta-icon" />
                      {job.source}
                    </span>
                  </p>
                </div>
                <div className="job-card__actions">
                  <Link to={`/jobs/${job.id}`} className="job-card__view-link">
                    View Details
                  </Link>
                  {shouldShowPostingLink(job) && (
                    <a href={job.url} target="_blank" rel="noreferrer" className="job-card__posting-link">
                      View Original Posting ↗
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <Pagination
            page={currentPage}
            pageCount={pageCount}
            totalCount={searchedJobs.length}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
