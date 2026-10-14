import StatusIndicator from "./StatusIndicator";
import "./Header.css";

export default function Header({ title, onMenuClick, backendStatus }) {
  return (
    <header className="header">
      <button
        type="button"
        className="header__menu-button"
        onClick={onMenuClick}
        aria-label="Toggle navigation"
      >
        <span aria-hidden="true">&#9776;</span>
      </button>

      <h1 className="header__title">{title}</h1>

      <div className="header__status">
        <StatusIndicator status={backendStatus.status} detail={backendStatus.detail} />
      </div>
    </header>
  );
}
