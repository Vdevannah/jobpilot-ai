import { scoreTier, SCORE_MEANING } from "../utils/scoreTier";
import "./ScoreBadge.css";

export default function ScoreBadge({ score, label }) {
  return (
    <span className={`score-badge score-badge--${scoreTier(score)}`} title={SCORE_MEANING}>
      {label ?? `${Math.round(score)}%`}
    </span>
  );
}
