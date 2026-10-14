import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import JobMatches from "./JobMatches";
import * as apiClient from "../api/client";

const MATCHES = [
  {
    job_id: 1, title: "Data Engineer", company: "Acme", location: "New York, NY",
    url: "https://example.com/1", overall_score: 82.0, recommendation: "Strong Match",
    job_track: "data", skill_score: 100, experience_score: 50, role_score: 100,
    domain_score: 100, location_score: 100, candidate_years: 2.0, required_years: 3,
    matched_skills: ["python", "sql"], missing_skills: [], reasons: [], source: "greenhouse",
  },
  {
    job_id: 2, title: "Office Coordinator", company: "Weak Co", location: "Boston, MA",
    url: "https://example.com/2", overall_score: 30.0, recommendation: "Low Priority",
    job_track: null, skill_score: 0, experience_score: 50, role_score: 0,
    domain_score: 100, location_score: 100, candidate_years: 0.0, required_years: null,
    matched_skills: [], missing_skills: ["python"], reasons: [], source: "lever",
  },
  {
    job_id: 3, title: "General Role", company: "Sparse Co", location: "Remote",
    url: "https://example.com/3", overall_score: 50.0, recommendation: "Possible Match",
    job_track: null, skill_score: 50, experience_score: 50, role_score: 0,
    domain_score: 100, location_score: 100, candidate_years: 0.0, required_years: null,
    matched_skills: [], missing_skills: [], reasons: [], source: "greenhouse",
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <JobMatches />
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("JobMatches", () => {
  it("shows a loading state before data arrives", () => {
    vi.spyOn(apiClient, "getMatches").mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByRole("status")).toHaveTextContent(/loading/i);
  });

  it("renders overall score, recommendation, track, and matched/missing skills", async () => {
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderPage();

    expect(await screen.findByText("Data Engineer")).toBeInTheDocument();
    expect(screen.getByText("Strong Match")).toBeInTheDocument();
    expect(screen.getByText("82%")).toBeInTheDocument();
    expect(screen.getByText("python, sql")).toBeInTheDocument();

    const card = screen.getByText("Data Engineer").closest(".match-card");
    expect(within(card).getByText("Data")).toBeInTheDocument();
  });

  it("clearly labels a job with no detected track instead of leaving it blank", async () => {
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderPage();
    const card = (await screen.findByText("Office Coordinator")).closest(".match-card");
    expect(within(card).getByText(/track not detected/i)).toBeInTheDocument();
  });

  it("never offers scientific_ai as a track filter option", async () => {
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderPage();
    await screen.findByText("Data Engineer");

    const trackSelect = screen.getByLabelText(/career track/i);
    const optionLabels = within(trackSelect)
      .getAllByRole("option")
      .map((option) => option.textContent.toLowerCase());

    expect(optionLabels.join(" ")).not.toContain("scientific_ai");
    expect(optionLabels).toEqual(
      expect.arrayContaining(["all tracks", "pharma", "data", "unknown / not detected"]),
    );
  });

  it("re-fetches with job_track=pharma when the Pharma filter is selected", async () => {
    const getMatches = vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderPage();
    await screen.findByText("Data Engineer");

    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText(/career track/i), "pharma");

    await waitFor(() => {
      expect(getMatches).toHaveBeenLastCalledWith(
        expect.objectContaining({ job_track: "pharma" }),
      );
    });
  });

  it("filters to the minimum score entered (server-side, like production)", async () => {
    // min_score is sent to the backend as a query parameter (see src/api.py);
    // simulate that server-side filtering here rather than asserting on a
    // client-side filter that the component does not perform.
    vi.spyOn(apiClient, "getMatches").mockImplementation(({ min_score } = {}) =>
      Promise.resolve(
        min_score === undefined ? MATCHES : MATCHES.filter((m) => m.overall_score >= min_score),
      ),
    );
    renderPage();
    await screen.findByText("Data Engineer");
    expect(screen.getByText("Office Coordinator")).toBeInTheDocument();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/minimum score/i), "50");

    // Check both conditions inside one waitFor so a transient loading state
    // (nothing rendered -- which would also make "Office Coordinator"
    // absent) can't produce a false pass; only the genuinely settled,
    // filtered render satisfies both at once.
    await waitFor(() => {
      expect(screen.getByText("Data Engineer")).toBeInTheDocument();
      expect(screen.queryByText("Office Coordinator")).not.toBeInTheDocument();
    });
  });

  it("shows an empty state when no matches meet the filters", async () => {
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText(/no matches meet these filters/i)).toBeInTheDocument();
  });

  it("shows an error state on failure", async () => {
    vi.spyOn(apiClient, "getMatches").mockRejectedValue(new Error("Request to /matches failed (500)"));
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent(/failed/i);
  });

  it("marks job titles as clear navigation links, distinct from the external posting link", async () => {
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderPage();

    const titleLink = await screen.findByRole("link", { name: /data engineer/i });
    expect(titleLink).toHaveAttribute("href", "/jobs/1");
    expect(titleLink).toHaveAttribute("title", "View full job details");
  });

  it("explains that match scores are deterministic compatibility estimates, not hiring predictions", async () => {
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderPage();
    await screen.findByText("Data Engineer");

    expect(screen.getByText(/not a prediction of hiring likelihood/i)).toBeInTheDocument();
  });

  it("flags a job with no detected skills/experience as limited information, not a skill gap", async () => {
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderPage();

    const card = (await screen.findByText("General Role")).closest(".match-card");
    expect(within(card).getByText(/no skills were detected in this job's description/i)).toBeInTheDocument();
    expect(within(card).queryByText("None detected")).not.toBeInTheDocument();
  });

  it("distinguishes 'none of the candidate's skills matched' from 'no skills detected'", async () => {
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderPage();

    const card = (await screen.findByText("Office Coordinator")).closest(".match-card");
    expect(within(card).getByText(/none of the candidate's skills matched/i)).toBeInTheDocument();
  });

  it("shows a positive, specific message when every required skill is matched", async () => {
    vi.spyOn(apiClient, "getMatches").mockResolvedValue(MATCHES);
    renderPage();

    const card = (await screen.findByText("Data Engineer")).closest(".match-card");
    expect(within(card).getByText(/all detected required skills are matched/i)).toBeInTheDocument();
  });
});
