import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import Dashboard from "./Dashboard";
import * as apiClient from "../api/client";

const JOBS = [
  { id: 1, title: "Data Engineer", company: "Acme", location: "New York, NY", url: "https://example.com/1", source: "greenhouse" },
  { id: 2, title: "Data Scientist", company: "Airbnb", location: "Remote", url: "https://careers.airbnb.com/2", source: "greenhouse" },
  { id: 3, title: "Business Analyst", company: "Airbnb", location: "Boston, MA", url: "https://careers.airbnb.com/3", source: "lever" },
];

function makeMatch(job, overrides = {}) {
  return {
    job_id: job.id,
    title: job.title,
    company: job.company,
    location: job.location,
    url: job.url,
    overall_score: 57.5,
    recommendation: "Good Match",
    job_track: "data",
    skill_score: 80,
    experience_score: 50,
    role_score: 100,
    domain_score: 100,
    location_score: 100,
    candidate_years: 2.0,
    required_years: 3,
    matched_skills: ["python"],
    missing_skills: ["sql"],
    reasons: ["Strong detected skill alignment"],
    ...overrides,
  };
}

const MATCHES = JOBS.map((job) => makeMatch(job));

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Dashboard", () => {
  it("shows a loading state before data arrives", () => {
    vi.spyOn(apiClient, "getJobs").mockReturnValue(new Promise(() => {}));
    vi.spyOn(apiClient, "getMatches").mockReturnValue(new Promise(() => {}));
    renderDashboard();
    expect(screen.getByRole("status")).toHaveTextContent(/loading dashboard/i);
  });

  it("calculates KPI totals from the actual jobs returned by the backend, not invented numbers", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderDashboard();

    await screen.findByText("Total jobs");

    function kpiValue(label) {
      return screen.getByText(label).closest(".kpi-card").querySelector(".kpi-card__value").textContent;
    }

    expect(kpiValue("Total jobs")).toBe("3");
    expect(kpiValue("Companies")).toBe("2"); // Acme, Airbnb
    expect(kpiValue("Locations")).toBe("3");
    expect(kpiValue("Sources")).toBe("2"); // greenhouse, lever
  });

  it("preserves the existing average match score and strong-match count as secondary metrics", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([
      makeMatch(JOBS[0], { overall_score: 90 }),
      makeMatch(JOBS[1], { overall_score: 10 }),
      makeMatch(JOBS[2], { overall_score: 50 }),
    ]);
    renderDashboard();

    await screen.findByText("Strong matches");
    expect(
      screen.getByText("Strong matches").closest(".stat-tile").querySelector(".stat-tile__value"),
    ).toHaveTextContent("1");
    expect(
      screen
        .getByText("Average match score")
        .closest(".stat-tile")
        .querySelector(".stat-tile__value"),
    ).toHaveTextContent("50.0%");
  });

  it("groups jobs by source for the bar chart using real counts", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderDashboard();

    const sourceChart = await screen.findByRole("img", { name: /bar chart/i });
    expect(sourceChart).toHaveAccessibleName(/greenhouse 2 jobs/i);
    expect(sourceChart).toHaveAccessibleName(/lever 1 jobs/i);
  });

  it("groups jobs by location for the donut chart with counts and percentages", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderDashboard();

    await screen.findByText("Jobs by location");
    const legendRow = screen.getByText("New York, NY", { selector: ".donut-chart__legend-label" })
      .closest(".donut-chart__legend-row");
    expect(within(legendRow).getByText(/1 · 33%/)).toBeInTheDocument();
  });

  it("shows empty states for KPIs, charts, and the table when there are no jobs", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue([]);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([]);
    renderDashboard();

    await screen.findByText("Total jobs");
    const kpiSection = screen.getByText("Total jobs").closest(".dashboard__kpis");
    expect(within(kpiSection).getAllByText("0")).toHaveLength(4);
    expect(screen.getAllByText(/no data available yet/i).length).toBe(2);
    expect(screen.getByText(/no jobs are available yet/i)).toBeInTheDocument();
  });

  it("labels a demo-seeded job in the recent listings table without hiding it", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderDashboard();

    const row = (await screen.findByText("Data Engineer")).closest("tr");
    expect(within(row).getByText("Demo record")).toBeInTheDocument();

    const realRow = screen.getByText("Data Scientist").closest("tr");
    expect(within(realRow).queryByText("Demo record")).not.toBeInTheDocument();
  });

  it("joins each row's source from the /jobs list, since /matches does not return it", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderDashboard();

    const row = (await screen.findByText("Business Analyst")).closest("tr");
    expect(within(row).getByText("lever")).toBeInTheDocument();
  });

  it("links the recent listings table and the hero CTA to their real destinations", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderDashboard();

    expect(await screen.findByRole("link", { name: /discover jobs/i })).toHaveAttribute(
      "href",
      "/discover",
    );

    const viewLinks = screen.getAllByRole("link", { name: /^view$/i });
    expect(viewLinks[0]).toHaveAttribute("href", expect.stringMatching(/^\/jobs\/\d+$/));
  });

  it("wraps the listings table in a horizontally scrollable container for small screens", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderDashboard();

    const table = await screen.findByRole("table");
    expect(table.closest(".job-listings-table__scroll")).not.toBeNull();
  });

  it("shows an error state with a retry action on failure", async () => {
    vi.spyOn(apiClient, "getJobs").mockRejectedValue(new Error("Could not reach the JobPilot AI backend."));
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([]);
    renderDashboard();

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not reach/i);
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});
