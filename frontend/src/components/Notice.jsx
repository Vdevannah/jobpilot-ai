import "./Notice.css";

const ICONS = {
  info: "ℹ",
  warning: "⚠",
};

// A visible, always-on explanatory note -- never a hover-only tooltip -- so
// data-quality caveats (limited job info, deterministic vs. predictive
// scores, track-specific experience) are readable without discovery.
export default function Notice({ tone = "info", children }) {
  return (
    <p className={`notice notice--${tone}`} role="note">
      <span className="notice__icon" aria-hidden="true">
        {ICONS[tone] ?? ICONS.info}
      </span>
      <span>{children}</span>
    </p>
  );
}
