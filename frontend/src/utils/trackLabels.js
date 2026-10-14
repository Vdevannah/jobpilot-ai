// job_track values are always the deterministic Phase 1-6 classification
// from GET /matches (src.matching.determine_job_track): "pharma", "data",
// or null. Never the Phase 7 AI track, and never "scientific_ai".
export const TRACK_LABELS = {
  pharma: "Pharma",
  data: "Data",
};
