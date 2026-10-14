export const SCORE_MEANING =
  "Deterministic compatibility estimate from keyword and experience matching -- not a prediction of hiring likelihood.";

// Mirrors src/matching.get_match_recommendation's thresholds so the badge
// tier always lines up with the backend's own recommendation label.
export function scoreTier(score) {
  if (score >= 80) return "strong";
  if (score >= 65) return "worth-reviewing";
  if (score >= 50) return "possible";
  return "low";
}
