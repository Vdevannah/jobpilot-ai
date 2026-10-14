import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import ResumeRecommendations from "./ResumeRecommendations";
import * as apiClient from "../api/client";

const JOBS = [
  { id: 1, title: "Data Engineer", company: "Acme", location: "NY", url: "https://x/1", source: "greenhouse" },
  { id: 2, title: "Chemist", company: "Pharmaco", location: "Boston", url: "https://x/2", source: "lever" },
];

const RANKING = (variant, score) => ({
  variant,
  score,
  matched_evidence: [],
  missing_evidence: [],
  reasons: [`${variant} reason`],
  limitations: [`${variant} limitation`],
});

const SUCCESS_RESPONSE = {
  job_id: 1,
  job_analysis: {
    required_skills: ["python"],
    preferred_skills: [],
    minimum_experience_years: 3,
    job_track: "data",
    summary: "MOCK SAMPLE: fixed summary.",
  },
  recommendation: {
    rankings: [RANKING("data", 11), RANKING("scientific_ai", 4), RANKING("pharma", 2)],
    recommended_variant: "data",
    tied_variants: [],
    insufficient_evidence: false,
    limitations: ["Scores compare resume evidence, not candidate suitability."],
    requires_human_review: true,
    status: "pending_review",
  },
  analysis_mode: "mock",
  evidence_source: "fictional_mock_fixture",
  personalized: false,
  requires_human_review: true,
  status: "pending_review",
  warnings: ["The job analysis is fixed mock sample output and does not analyze the stored description."],
  limitations: ["Resume evidence is fictional structured fixture data."],
};

const MISSING_DESCRIPTION_RESPONSE = {
  job_id: 1,
  job_analysis: null,
  recommendation: null,
  analysis_mode: "mock",
  evidence_source: "not_available",
  personalized: false,
  requires_human_review: true,
  status: "pending_review",
  warnings: ["Job description is missing; no job analysis or resume ranking was produced."],
  limitations: ["Resume evidence is fictional structured fixture data."],
};

function renderPage(initialPath = "/resumes") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/resumes" element={<ResumeRecommendations />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ResumeRecommendations", () => {
  it("does not request a recommendation automatically on page load", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    const recSpy = vi.spyOn(apiClient, "getResumeRecommendation").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    await screen.findByText("Data Engineer -- Acme", { exact: false });
    expect(recSpy).not.toHaveBeenCalled();
  });

  it("requests a recommendation only after the user selects a job and clicks the button", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    const recSpy = vi.spyOn(apiClient, "getResumeRecommendation").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    const button = screen.getByRole("button", { name: /get resume recommendation/i });
    expect(recSpy).not.toHaveBeenCalled();

    await userEvent.click(button);

    await waitFor(() => expect(recSpy).toHaveBeenCalledWith("1"));
  });

  it("shows loading then the recommended variant, rankings, reasons, and limitations", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getResumeRecommendation").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /get resume recommendation/i }));

    expect(await screen.findByText(/highest ranking points: data/i)).toBeInTheDocument();
    expect(screen.getByText("data reason")).toBeInTheDocument();
    expect(screen.getByText("data limitation")).toBeInTheDocument();
    expect(screen.getByText(/pending review/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/requires human review/i);
    expect(screen.getByRole("status")).toHaveTextContent(/not personalized/i);
  });

  it("labels scores as ranking points, not a percentage, and explains their origin", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getResumeRecommendation").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /get resume recommendation/i }));

    expect(await screen.findByText("Ranking points: 11")).toBeInTheDocument();
    expect(screen.getByText("Ranking points: 4")).toBeInTheDocument();
    expect(screen.getByText("Ranking points: 2")).toBeInTheDocument();
    expect(screen.queryByText(/^score:/i)).not.toBeInTheDocument();
    expect(
      screen.getByText(/phase 7 deterministic resume-selection algorithm/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/not a percentage, a hiring probability/i)).toBeInTheDocument();
  });

  it("labels evidence as fictional demonstration data", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getResumeRecommendation").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    expect(
      await screen.findByText(/fictional demonstration data/i),
    ).toBeInTheDocument();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /get resume recommendation/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(/fictional evidence only/i);
  });

  it("shows ties between variants when the API reports them", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getResumeRecommendation").mockResolvedValue({
      ...SUCCESS_RESPONSE,
      recommendation: {
        ...SUCCESS_RESPONSE.recommendation,
        recommended_variant: null,
        tied_variants: ["data", "pharma"],
      },
    });
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /get resume recommendation/i }));

    expect(await screen.findByText(/tied ranking points between/i)).toBeInTheDocument();
  });

  it("handles a missing job description without fabricating a recommendation", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getResumeRecommendation").mockResolvedValue(MISSING_DESCRIPTION_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /get resume recommendation/i }));

    expect(await screen.findByText(/description is missing/i)).toBeInTheDocument();
    expect(screen.queryByText(/highest ranking points/i)).not.toBeInTheDocument();
  });

  it("shows an error state when the request fails, with a retry option", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getResumeRecommendation").mockRejectedValue(
      new Error("Request to /jobs/1/resume-recommendation failed (503): Mock AI analysis unavailable."),
    );
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /get resume recommendation/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
  });

  it("preselects the job passed via the jobId query parameter", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getResumeRecommendation").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage("/resumes?jobId=2");

    const select = await screen.findByLabelText(/select a discovered job/i);
    expect(select).toHaveValue("2");
  });
});
