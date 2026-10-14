// matched_skills and missing_skills together always partition the job's
// required_skills (src/matching.match_job never produces skills outside
// that partition), so their combined emptiness is a reliable signal that no
// skills were detected in the job's description at all -- not that the
// candidate lacks relevant skills.
export function hasNoDetectedRequirements(match) {
  return match.matched_skills.length === 0 && match.missing_skills.length === 0;
}
