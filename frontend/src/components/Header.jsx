import StatusIndicator from "./StatusIndicator";
import { MenuIcon } from "./icons";
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
        <MenuIcon className="header__menu-icon" />
      </button>

      <h1 className="header__title">{title}</h1>

      <div className="header__status">
        <StatusIndicator status={backendStatus.status} detail={backendStatus.detail} />
      </div>
    </header>
  );
}
