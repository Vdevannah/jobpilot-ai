import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import DiscoverJobs from "./pages/DiscoverJobs";
import JobMatches from "./pages/JobMatches";
import JobDetail from "./pages/JobDetail";
import ResumeRecommendations from "./pages/ResumeRecommendations";
import AIInsights from "./pages/AIInsights";
import { getHealth } from "./api/client";

const HEALTH_POLL_MS = 30000;

export default function App() {
  const [backendStatus, setBackendStatus] = useState({ status: "loading", detail: "" });

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        await getHealth();
        if (!cancelled) setBackendStatus({ status: "online", detail: "" });
      } catch (error) {
        if (!cancelled) setBackendStatus({ status: "offline", detail: error.message });
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, HEALTH_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout backendStatus={backendStatus} />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/discover" element={<DiscoverJobs />} />
          <Route path="/matches" element={<JobMatches />} />
          <Route path="/jobs/:jobId" element={<JobDetail />} />
          <Route path="/resumes" element={<ResumeRecommendations />} />
          <Route path="/insights" element={<AIInsights />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
