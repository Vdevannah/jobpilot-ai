import { NavLink } from "react-router-dom";
import { DashboardIcon, SearchIcon, StarIcon, ResumeIcon, InsightsIcon } from "./icons";
import "./Sidebar.css";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", Icon: DashboardIcon },
  { to: "/discover", label: "Discover Jobs", Icon: SearchIcon },
  { to: "/matches", label: "Job Matches", Icon: StarIcon },
  { to: "/resumes", label: "Resume Recommendations", Icon: ResumeIcon },
  { to: "/insights", label: "AI Insights", Icon: InsightsIcon },
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
          {NAV_ITEMS.map(({ to, label, Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                className={({ isActive }) => `sidebar__link ${isActive ? "sidebar__link--active" : ""}`}
                onClick={onNavigate}
                end={to === "/"}
              >
                <Icon className="sidebar__icon" />
                <span>{label}</span>
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
