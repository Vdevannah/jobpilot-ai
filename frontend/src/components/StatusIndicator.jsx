import "./StatusIndicator.css";

const LABELS = {
  loading: "Checking backend...",
  online: "Backend connected",
  offline: "Backend unreachable",
};

export default function StatusIndicator({ status, detail }) {
  const label = LABELS[status] || LABELS.offline;

  return (
    <span className={`status status--${status}`} role="status">
      <span className="status__dot" aria-hidden="true" />
      <span className="status__label">{label}</span>
      {detail ? <span className="status__detail">{detail}</span> : null}
    </span>
  );
}
