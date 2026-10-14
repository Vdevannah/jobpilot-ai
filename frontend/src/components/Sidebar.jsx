import { NavLink } from "react-router-dom";
import "./Sidebar.css";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "▦" },
  { to: "/discover", label: "Discover Jobs", icon: "⌕" },
  { to: "/matches", label: "Job Matches", icon: "★" },
  { to: "/resumes", label: "Resume Recommendations", icon: "☰" },
  { to: "/insights", label: "AI Insights", icon: "✨" },
];

export default function Sidebar({ open, onNavigate }) {
  return (
    <aside className={`sidebar ${open ? "sidebar--open" : ""}`}>
      <div className="sidebar__brand">
        <span className="sidebar__brand-mark" aria-hidden="true">
          JP
        </span>
        <span className="sidebar__brand-name">JobPilot AI</span>
      </div>

      <nav className="sidebar__nav" aria-label="Primary">
        <ul>
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) => `sidebar__link ${isActive ? "sidebar__link--active" : ""}`}
                onClick={onNavigate}
                end={item.to === "/"}
              >
                <span className="sidebar__icon" aria-hidden="true">
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="sidebar__footer">
        <p className="sidebar__footer-text">JobPilot AI &middot; Local Development</p>
      </div>
    </aside>
  );
}
