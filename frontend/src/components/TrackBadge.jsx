import { TRACK_LABELS } from "../utils/trackLabels";
import "./TrackBadge.css";

// job_track here is always the deterministic Phase 1-6 classification from
// GET /matches (src.matching.determine_job_track): "pharma", "data", or
// null when no track was detected. This is never the Phase 7 AI track and
// never offers/accepts "scientific_ai".
export default function TrackBadge({ track }) {
  if (track == null) {
    return <span className="track-badge track-badge--unknown">Track not detected</span>;
  }
  return <span className={`track-badge track-badge--${track}`}>{TRACK_LABELS[track] ?? track}</span>;
}
