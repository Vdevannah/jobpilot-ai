import { render, screen, waitFor, within } from "@testing-library/react";
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
    // "data reason"/"data limitation" now appear twice (the prominent
    // recommended-resume card, and the full comparison list below it) --
    // scope to the comparison list specifically.
    const comparisonList = document.querySelector(".resume-recommendations__rankings");
    expect(within(comparisonList).getByText("data reason")).toBeInTheDocument();
    expect(within(comparisonList).getByText("data limitation")).toBeInTheDocument();
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

    await screen.findByText("Resume comparison");
    const comparisonList = document.querySelector(".resume-recommendations__rankings");
    expect(within(comparisonList).getByText("Ranking points: 11")).toBeInTheDocument();
    expect(within(comparisonList).getByText("Ranking points: 4")).toBeInTheDocument();
    expect(within(comparisonList).getByText("Ranking points: 2")).toBeInTheDocument();
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

  it("shows the page heading and subtitle", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    renderPage();

    expect(await screen.findByRole("heading", { name: "Resume Recommendations" })).toBeInTheDocument();
    expect(
      screen.getByText("Compare resume variants recommended for each opportunity."),
    ).toBeInTheDocument();
  });

  it("shows the selected job's available context (title, company, location) as soon as it is chosen", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");

    expect(await screen.findByText("Data Engineer")).toBeInTheDocument();
    expect(screen.getByText("Acme")).toBeInTheDocument();
    expect(screen.getByText("NY")).toBeInTheDocument();
  });

  it("shows the career track in the job context only once the AI response actually returns one", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getResumeRecommendation").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");

    const contextCard = document.querySelector(".job-context-card");
    expect(within(contextCard).queryByText("Data")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /get resume recommendation/i }));
    await screen.findByText("Resume comparison");

    expect(within(contextCard).getByText("Data")).toBeInTheDocument();
  });

  it("shows a visually distinct recommended-resume card with the variant, reasons, and limitations", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getResumeRecommendation").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /get resume recommendation/i }));

    const leaderCard = await screen.findByText("Recommended resume");
    const card = leaderCard.closest(".resume-recommendations__leader-card");
    expect(within(card).getByText("Data")).toBeInTheDocument();
    expect(within(card).getByText("11")).toBeInTheDocument();
    expect(within(card).getByText("ranking points")).toBeInTheDocument();
    expect(within(card).getByText("data reason")).toBeInTheDocument();
    expect(within(card).getByText("data limitation")).toBeInTheDocument();
  });

  it("does not show a recommended-resume card when evidence is insufficient to pick one", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    vi.spyOn(apiClient, "getResumeRecommendation").mockResolvedValue({
      ...SUCCESS_RESPONSE,
      recommendation: { ...SUCCESS_RESPONSE.recommendation, insufficient_evidence: true, recommended_variant: null },
    });
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    await userEvent.selectOptions(select, "1");
    await userEvent.click(screen.getByRole("button", { name: /get resume recommendation/i }));

    await screen.findByText(/no variant had enough matching evidence/i);
    expect(screen.queryByText("Recommended resume")).not.toBeInTheDocument();
  });

  it("supports selecting a job and triggering the request entirely via the keyboard", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    const recSpy = vi.spyOn(apiClient, "getResumeRecommendation").mockResolvedValue(SUCCESS_RESPONSE);
    renderPage();

    const select = await screen.findByLabelText(/select a discovered job/i);
    select.focus();
    await userEvent.selectOptions(select, "1");

    const button = screen.getByRole("button", { name: /get resume recommendation/i });
    button.focus();
    expect(button).toHaveFocus();
    await userEvent.keyboard("{Enter}");

    await waitFor(() => expect(recSpy).toHaveBeenCalledWith("1"));
  });

  it("shows a single, non-repeated demo/human-review notice before any job is selected", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    renderPage();

    expect(await screen.findByText(/fictional demonstration data/i)).toBeInTheDocument();
    expect(
      screen.getByText(/requiring human review before any real application/i),
    ).toBeInTheDocument();
    // Exactly one top-level disclosure notice before any job/result exists --
    // not a second, separate warning box repeating the same point.
    expect(screen.getAllByRole("note")).toHaveLength(1);
  });
});
