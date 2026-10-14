import { render, screen, waitFor, within } from "@testing-library/react";
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

  it("consolidates the mock-analysis disclosure into a single info card, not multiple warning boxes", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getAIReview").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    await screen.findByText("Mock AI Analysis");
    expect(document.querySelectorAll(".ai-insights__mock-indicator")).toHaveLength(1);
    // Before any request, there must be exactly one disclosure of the
    // "does not analyze the actual description" fact -- not a second,
    // separate warning box repeating it.
    expect(screen.getAllByText(/does not read or analyze the selected job's actual description/i)).toHaveLength(1);
  });

  it("shows all three critic-review variants (Pharma, Data, Scientific AI) with their own summaries", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getAIReview").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /request ai review/i }));

    await screen.findByText("Mock critic summary for data.");
    expect(screen.getByRole("heading", { name: "Pharma" })).toBeInTheDocument();
    expect(screen.getByText("Mock critic summary for pharma.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Data" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Scientific AI" })).toBeInTheDocument();
    expect(screen.getByText("Mock critic summary for scientific_ai.")).toBeInTheDocument();
  });

  it("supports selecting a job and triggering the review entirely via the keyboard", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    const reviewSpy = vi.spyOn(apiClient, "getAIReview").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    select.focus();
    await userEvent.selectOptions(select, "1");

    const button = screen.getByRole("button", { name: /request ai review/i });
    button.focus();
    expect(button).toHaveFocus();
    await userEvent.keyboard("{Enter}");

    await waitFor(() => expect(reviewSpy).toHaveBeenCalledWith("1"));
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

  it("shows the page heading and subtitle", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    renderPage();

    expect(await screen.findByRole("heading", { name: "AI Insights" })).toBeInTheDocument();
    expect(
      screen.getByText("Explore mock AI analysis of job requirements and potential fit."),
    ).toBeInTheDocument();
  });

  it("shows a prominent Mock AI Analysis indicator explaining this is not a live OpenAI analysis", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    renderPage();

    expect(await screen.findByText("Mock AI Analysis")).toBeInTheDocument();
    expect(screen.getByText(/not a live openai analysis of your personal resumes/i)).toBeInTheDocument();
  });

  it("communicates that the user must independently verify the analysis before applying", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    renderPage();

    expect(
      await screen.findByText(/independently verify the job requirements and this analysis/i),
    ).toBeInTheDocument();
  });

  it("shows the selected job's available context as soon as it is chosen, and adds the career track once the API returns one", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getAIReview").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");

    const contextCard = document.querySelector(".job-context-card");
    expect(within(contextCard).getByText("Data Engineer")).toBeInTheDocument();
    expect(within(contextCard).getByText("Acme")).toBeInTheDocument();
    expect(within(contextCard).queryByText("Data")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /request ai review/i }));
    await screen.findByText("python, sql");

    expect(within(contextCard).getByText("Data")).toBeInTheDocument();
  });

  it("renders only the insight sections the API actually returned, never a forced empty card", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getAIReview").mockResolvedValue({
      ...SUCCESS_RESPONSE,
      research_report: null,
      critic_reports: null,
    });
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /request ai review/i }));

    await screen.findByText("Mock job analysis");
    expect(screen.queryByText("Research findings")).not.toBeInTheDocument();
    expect(screen.queryByText(/critic review/i)).not.toBeInTheDocument();
  });
});
