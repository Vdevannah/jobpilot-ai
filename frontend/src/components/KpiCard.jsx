import "./KpiCard.css";

// Four fixed categorical accents (never cycled past these), matching the
// shared design tokens from the dashboard's own palette.
const ACCENTS = ["blue", "green", "purple", "orange"];

export default function KpiCard({ label, value, hint, icon, accent = "blue" }) {
  const safeAccent = ACCENTS.includes(accent) ? accent : "blue";
  return (
    <div className={`kpi-card kpi-card--${safeAccent}`}>
      <div className="kpi-card__icon" aria-hidden="true">
        {icon}
      </div>
      <div className="kpi-card__body">
        <p className="kpi-card__label">{label}</p>
        <p className="kpi-card__value">{value}</p>
        {hint ? <p className="kpi-card__hint">{hint}</p> : null}
      </div>
    </div>
  );
}
