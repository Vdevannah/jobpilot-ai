import "./AsyncState.css";

export function LoadingState({ label = "Loading..." }) {
  return (
    <div className="async-state async-state--loading" role="status">
      <span className="async-state__spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="async-state async-state--error" role="alert">
      <p>{message}</p>
      {onRetry ? (
        <button type="button" className="async-state__retry" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ message }) {
  return (
    <div className="async-state async-state--empty">
      <p>{message}</p>
    </div>
  );
}
