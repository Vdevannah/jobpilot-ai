import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import JobDetail from "./JobDetail";
import * as apiClient from "../api/client";

const JOB = {
  id: 1, title: "Data Engineer", company: "Acme", location: "New York, NY",
  url: "https://example.com/1", source: "greenhouse",
  description: "Build and maintain data pipelines.",
};

const MATCH = {
  job_id: 1, title: "Data Engineer", company: "Acme", location: "New York, NY",
  url: "https://example.com/1", overall_score: 82.0, recommendation: "Strong Match",
  job_track: "data", skill_score: 100, experience_score: 50, role_score: 100,
  domain_score: 100, location_score: 100, candidate_years: 2.0, required_years: 3,
  matched_skills: ["python", "sql"], missing_skills: ["airflow"],
  reasons: ["Strong detected skill alignment"], source: "greenhouse",
};

function renderDetail(jobId = "1") {
  return render(
    <MemoryRouter initialEntries={[`/jobs/${jobId}`]}>
      <Routes>
        <Route path="/jobs/:jobId" element={<JobDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("JobDetail", () => {
  it("shows a loading state before the job loads", () => {
    vi.spyOn(apiClient, "getJobById").mockReturnValue(new Promise(() => {}));
    vi.spyOn(apiClient, "getMatches").mockReturnValue(new Promise(() => {}));
    renderDetail();
    expect(screen.getByRole("status")).toHaveTextContent(/loading job details/i);
  });

  it("renders the full description, employer, location, source, and posting link", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    expect(await screen.findByText("Build and maintain data pipelines.")).toBeInTheDocument();
    expect(screen.getByText(/Acme/)).toBeInTheDocument();
    expect(screen.getByText(/greenhouse/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view original posting/i })).toHaveAttribute(
      "href",
      "https://example.com/1",
    );
  });

  it("shows a clear message when the description is missing, plus a limited-information notice", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue({ ...JOB, description: null });
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    expect(await screen.findByText("No description is available for this job posting.")).toBeInTheDocument();
    expect(screen.getByText(/the match score below is based on limited job information/i)).toBeInTheDocument();
  });

  it("renders the existing score breakdown when a match is available", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    expect(await screen.findByText("82%")).toBeInTheDocument();
    expect(screen.getByText("Strong Match")).toBeInTheDocument();
    const skillScoreRow = screen.getByText("Skill score").closest(".job-detail__score-row");
    expect(skillScoreRow).toHaveTextContent("100.0");
    expect(screen.getByText("python, sql")).toBeInTheDocument();
    expect(screen.getByText("airflow")).toBeInTheDocument();
  });

  it("handles a job with no corresponding match gracefully", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([]);
    renderDetail();

    expect(await screen.findByText(/no score breakdown is available/i)).toBeInTheDocument();
  });

  it("shows an error state when the job cannot be loaded", async () => {
    vi.spyOn(apiClient, "getJobById").mockRejectedValue(new Error("Request to /jobs/1 failed (404): Job not found"));
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([]);
    renderDetail();

    expect(await screen.findByRole("alert")).toHaveTextContent(/not found/i);
  });

  it("explains that the match score is a deterministic estimate, not a hiring prediction", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    expect(await screen.findByText(/not a prediction of hiring likelihood/i)).toBeInTheDocument();
  });

  it("labels candidate experience as track-specific, not total professional experience", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    expect(await screen.findByText("Candidate experience (Data track)")).toBeInTheDocument();
    expect(screen.getByText("2.0 yrs")).toBeInTheDocument();
    expect(
      screen.getByText(/reflects the candidate's experience in the data track only/i),
    ).toBeInTheDocument();
  });

  it("never shows a bare 0.0 yrs for candidate experience when no track was detected", async () => {
    const unknownTrackMatch = { ...MATCH, job_track: null, candidate_years: 0.0 };
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([unknownTrackMatch]);
    renderDetail();

    expect(await screen.findByText("Candidate experience")).toBeInTheDocument();
    expect(screen.getByText("Not applicable")).toBeInTheDocument();
    expect(screen.queryByText("0.0 yrs")).not.toBeInTheDocument();
    expect(
      screen.getByText(/does not mean the candidate has no professional experience/i),
    ).toBeInTheDocument();
  });

  it("labels a job seeded at the example.com placeholder domain as a demo record", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    expect(await screen.findByText("Demo record")).toBeInTheDocument();
  });

  it("does not label a genuinely collected job as a demo record", async () => {
    const realJob = { ...JOB, url: "https://careers.acme-corp.com/1" };
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(realJob);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    await screen.findByText(JOB.title);
    expect(screen.queryByText("Demo record")).not.toBeInTheDocument();
  });

  it("links to the AI pages for this job, carrying the job ID as a query parameter", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail("1");

    const resumeLink = await screen.findByRole("link", { name: /get resume recommendation/i });
    expect(resumeLink).toHaveAttribute("href", "/resumes?jobId=1");

    const insightsLink = screen.getByRole("link", { name: /view ai insights/i });
    expect(insightsLink).toHaveAttribute("href", "/insights?jobId=1");
  });

  it("marks the job title area and posting link as distinct, clearly-labeled navigation", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    const postingLink = await screen.findByRole("link", { name: /view original posting/i });
    expect(postingLink).toHaveAttribute("target", "_blank");
    expect(postingLink).toHaveAttribute("href", "https://example.com/1");
  });
});
