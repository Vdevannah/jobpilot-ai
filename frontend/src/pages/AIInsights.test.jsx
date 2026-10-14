import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import AIInsights from "./AIInsights";
import * as apiClient from "../api/client";

const JOBS = [
  { id: 1, title: "Data Engineer", company: "Acme", location: "NY", url: "https://x/1", source: "greenhouse" },
];

const SUCCESS_RESPONSE = {
  job_id: 1,
  job_analysis: {
    required_skills: ["python", "sql"],
    preferred_skills: ["aws"],
    minimum_experience_years: 3,
    job_track: "data",
    summary: "MOCK SAMPLE: fixed summary, not derived from the actual job description.",
  },
  recommendation: {
    rankings: [],
    recommended_variant: "data",
    tied_variants: [],
    insufficient_evidence: false,
    limitations: [],
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
  research_report: {
    missing_information: ["Actual team size"],
    research_questions: ["What does the interview process look like?"],
    summary: "No external research was performed.",
  },
  critic_reports: {
    data: { warnings: ["No employment inferred from education alone."], requires_human_review: true, summary: "Mock critic summary for data." },
    pharma: { warnings: [], requires_human_review: true, summary: "Mock critic summary for pharma." },
    scientific_ai: { warnings: [], requires_human_review: true, summary: "Mock critic summary for scientific_ai." },
  },
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
  warnings: ["Job description is missing; no AI review or resume ranking was produced."],
  limitations: ["Resume evidence is fictional structured fixture data."],
  research_report: null,
  critic_reports: null,
};

function renderPage(initialPath = "/insights") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/insights" element={<AIInsights />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AIInsights", () => {
  it("does not request an AI review automatically on page load", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    const reviewSpy = vi.spyOn(apiClient, "getAIReview").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    await screen.findByText("Data Engineer -- Acme", { exact: false });
    expect(reviewSpy).not.toHaveBeenCalled();
  });

  it("requests a review only after the user selects a job and clicks the button", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    const reviewSpy = vi.spyOn(apiClient, "getAIReview").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    expect(reviewSpy).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /request ai review/i }));

    await waitFor(() => expect(reviewSpy).toHaveBeenCalledWith("1"));
  });

  it("explains that the mock job analysis is fixed example output, not derived from the job", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getAIReview").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    expect(
      await screen.findByText(/does not read or analyze the selected job's actual description/i),
    ).toBeInTheDocument();
  });

  it("displays structured job analysis, research findings, and critic warnings", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getAIReview").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /request ai review/i }));

    expect(await screen.findByText("python, sql")).toBeInTheDocument();
    expect(screen.getByText("No external research was performed.")).toBeInTheDocument();
    expect(screen.getByText("Actual team size")).toBeInTheDocument();
    expect(screen.getByText("No employment inferred from education alone.")).toBeInTheDocument();
  });

  it("shows one prominent mock-analysis warning and does not repeat critic warnings as separate banners", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getAIReview").mockResolvedValue({
      ...SUCCESS_RESPONSE,
      warnings: [
        "The job analysis is fixed mock sample output and does not analyze the stored description.",
        "No employment inferred from education alone.",
      ],
    });
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /request ai review/i }));

    await screen.findByText(/does not analyze the stored description/i);
    const topLevelNotices = screen.getAllByRole("note");
    const duplicateBanners = topLevelNotices.filter((node) =>
      node.textContent.includes("No employment inferred from education alone."),
    );
    expect(duplicateBanners).toHaveLength(0);
    // Still present once, inside the relevant critic's card.
    expect(screen.getByText("No employment inferred from education alone.")).toBeInTheDocument();
  });

  it("shows the human-review status and never presents the review as completed", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getAIReview").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /request ai review/i }));

    expect(await screen.findAllByText(/requires human review/i)).not.toHaveLength(0);
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
  });

  it("handles a missing job description without fabricating insights", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getAIReview").mockResolvedValue(MISSING_DESCRIPTION_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /request ai review/i }));

    expect(await screen.findByText(/description is missing/i)).toBeInTheDocument();
    expect(screen.queryByText("No external research was performed.")).not.toBeInTheDocument();
  });

  it("shows an error state when the request fails", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getAIReview").mockRejectedValue(
      new Error("Request to /jobs/1/ai-review failed (503): Mock AI review unavailable."),
    );
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /request ai review/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
  });

  it("preselects the job passed via the jobId query parameter", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getAIReview").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage("/insights?jobId=1");

    const select = await screen.findByLabelText(/select a discovered job/i);
    expect(select).toHaveValue("1");
  });
});
