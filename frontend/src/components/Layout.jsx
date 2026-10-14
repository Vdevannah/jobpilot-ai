import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";
import "./Layout.css";

const PAGE_TITLES = {
  "/": "Dashboard",
  "/discover": "Discover Jobs",
  "/matches": "Job Matches",
  "/resumes": "Resume Recommendations",
  "/insights": "AI Insights",
};

export default function Layout({ backendStatus }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { pathname } = useLocation();
  const title = PAGE_TITLES[pathname] || (pathname.startsWith("/jobs/") ? "Job Details" : "JobPilot AI");

  return (
    <div className="layout">
      <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />

      {sidebarOpen && (
        <button
          type="button"
          className="layout__overlay"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="layout__main">
        <Header
          title={title}
          backendStatus={backendStatus}
          onMenuClick={() => setSidebarOpen((value) => !value)}
        />
        <main className="layout__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
