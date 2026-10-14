// GET /matches does not return a `source` field (only GET /jobs does), so
// any page that needs a match's source has to join it in from the already-
// fetched /jobs list by job_id. This is the one shared place that join
// happens, so every page does it the same (correct) way.
//
// GET /jobs returns every job when called with no limit/offset -- src/api.py's
// _paginate() only slices when a limit is explicitly passed, so the caller
// fetching the lookup must call getJobs() with no pagination params. This
// module doesn't call the API itself; it only joins whatever job list it's
// given, so it's the caller's responsibility to pass a complete list (not a
// single paginated page) -- otherwise some matches will correctly fall back
// to "no source found" rather than being silently mislabeled.
export function buildSourceLookup(jobs) {
  const lookup = new Map();
  for (const job of jobs ?? []) {
    if (job?.id == null) continue;
    if (job.source == null || job.source === "") continue;
    lookup.set(String(job.id), job.source);
  }
  return lookup;
}

// Joins each row's source in by job_id (never by array position or title).
// A row that already has a non-empty source is left untouched; a row with
// no corresponding job in the lookup gets `source: null` so the caller can
// render its own neutral fallback (e.g. "Source unavailable") rather than
// this utility guessing or inventing one.
export function withSourceFromJobs(rows, jobs) {
  const lookup = buildSourceLookup(jobs);
  return rows.map((row) => {
    if (row.source != null && row.source !== "") return row;
    return { ...row, source: lookup.get(String(row.job_id)) ?? null };
  });
}
