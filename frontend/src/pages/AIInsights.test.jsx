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

const COMPARISON_RESPONSE = {
  requirement_comparison: {
    job_id: 1,
    matches: [
      {
        requirement_kind: "skill",
        requirement_description: "python",
        requirement_evidence: [],
        is_required: true,
        alternative_group: null,
        candidate_evidence: [
          { claim: "Data Engineer, Fictional Analytics Corp", source_category: "professional_experience", professional_experience_years: 6.0 },
        ],
        evidence_source_categories: ["professional_experience"],
        status: "supported",
        explanation: "Professional experience evidence documents 6 years of professional use of 'python'.",
        limitations: [],
      },
      {
        requirement_kind: "skill",
        requirement_description: "kafka",
        requirement_evidence: [],
        is_required: false,
        alternative_group: null,
        candidate_evidence: [],
        evidence_source_categories: [],
        status: "not_demonstrated",
        explanation: "No evidence of 'kafka' was found in the supplied candidate evidence.",
        limitations: ["No matching candidate evidence was found; this is not proof the candidate lacks the qualification."],
      },
      {
        requirement_kind: "experience",
        requirement_description: "12+ years with Bachelor's",
        requirement_evidence: [],
        is_required: true,
        alternative_group: 1,
        candidate_evidence: [],
        evidence_source_categories: [],
        status: "partially_supported",
        explanation: "Documented pharma professional experience (9 years) is below the 12-year requirement.",
        limitations: [],
      },
      {
        requirement_kind: "experience",
        requirement_description: "9+ years with PhD",
        requirement_evidence: [],
        is_required: true,
        alternative_group: 1,
        candidate_evidence: [],
        evidence_source_categories: [],
        status: "requires_review",
        explanation: "The required degree level in 'PhD' could not be determined with confidence.",
        limitations: ["Ambiguous degree equivalency is never resolved automatically."],
      },
    ],
    unresolved_alternative_groups: [1],
    overall_limitations: ["This comparison is deterministic text/category matching, not a hiring or suitability assessment."],
    analysis_mode: "deterministic",
    requires_human_review: true,
    status: "pending_review",
  },
  candidate_id: "fictional-candidate-b-experienced-qualified",
  candidate_label: "Fictional Candidate B -- Experienced & Qualified Data Engineer (demonstration data only)",
  candidate_is_fictional: true,
  comparison_scope: "fictional_demo",
  is_demo_record: false,
  source: "greenhouse",
  limitations: [
    "This compares the job posting against a fixed FICTIONAL candidate evidence fixture, not the user's actual resume or any real candidate data.",
    "A job that is not a known example.com demo record is not thereby proven to be currently live or still accepting applications.",
  ],
};

const EMPTY_COMPARISON_RESPONSE = {
  requirement_comparison: {
    job_id: 1,
    matches: [],
    unresolved_alternative_groups: [],
    overall_limitations: ["Job posting limitation (carried over from extraction): No job description is available for this posting."],
    analysis_mode: "deterministic",
    requires_human_review: true,
    status: "pending_review",
  },
  candidate_id: "fictional-candidate-b-experienced-qualified",
  candidate_label: "Fictional Candidate B -- Experienced & Qualified Data Engineer (demonstration data only)",
  candidate_is_fictional: true,
  comparison_scope: "fictional_demo",
  is_demo_record: false,
  source: "greenhouse",
  limitations: [
    "This compares the job posting against a fixed FICTIONAL candidate evidence fixture, not the user's actual resume or any real candidate data.",
  ],
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

  describe("evidence-based requirement comparison (Phase 9B)", () => {
    it("prompts for a job selection before loading any comparison", async () => {
      vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
      const comparisonSpy = vi.spyOn(apiClient, "getJobRequirementComparison").mockResolvedValue(COMPARISON_RESPONSE);
      renderPage();

      expect(
        await screen.findByText(/select a job above to view its evidence-based requirement comparison/i),
      ).toBeInTheDocument();
      expect(comparisonSpy).not.toHaveBeenCalled();
    });

    it("loads the comparison automatically once a job is selected, without an extra click", async () => {
      vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
      const comparisonSpy = vi.spyOn(apiClient, "getJobRequirementComparison").mockResolvedValue(COMPARISON_RESPONSE);
      renderPage();

      const select = await screen.findByLabelText(/select a discovered job/i);
      await userEvent.selectOptions(select, "1");

      await waitFor(() => expect(comparisonSpy).toHaveBeenCalledWith("1"));
      expect(await screen.findByText(/demo comparison/i)).toBeInTheDocument();
    });

    it("shows a prominent, persistent fictional-candidate warning", async () => {
      vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
      vi.spyOn(apiClient, "getJobRequirementComparison").mockResolvedValue(COMPARISON_RESPONSE);
      renderPage();

      const select = await screen.findByLabelText(/select a discovered job/i);
      await userEvent.selectOptions(select, "1");

      expect(
        await screen.findByText(/DEMO COMPARISON.*fictional candidate, not your resume/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/Fictional Candidate B/)).toBeInTheDocument();
    });

    it("distinguishes required from preferred requirement matches", async () => {
      vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
      vi.spyOn(apiClient, "getJobRequirementComparison").mockResolvedValue(COMPARISON_RESPONSE);
      renderPage();

      const select = await screen.findByLabelText(/select a discovered job/i);
      await userEvent.selectOptions(select, "1");

      const pythonMatch = (await screen.findByText("python")).closest(".requirement-comparison-panel__match");
      expect(within(pythonMatch).getByText("Required")).toBeInTheDocument();
      const kafkaMatch = screen.getByText("kafka").closest(".requirement-comparison-panel__match");
      expect(within(kafkaMatch).getByText("Preferred")).toBeInTheDocument();
    });

    it("shows supported, partially supported, and requires-review statuses with their explanations", async () => {
      vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
      vi.spyOn(apiClient, "getJobRequirementComparison").mockResolvedValue(COMPARISON_RESPONSE);
      renderPage();

      const select = await screen.findByLabelText(/select a discovered job/i);
      await userEvent.selectOptions(select, "1");

      await screen.findByText("python");
      expect(screen.getByText("Supported")).toBeInTheDocument();
      expect(screen.getByText("Not demonstrated")).toBeInTheDocument();
      expect(screen.getByText("Partially supported")).toBeInTheDocument();
      expect(screen.getByText("Requires review")).toBeInTheDocument();
      expect(
        screen.getByText(/documents 6 years of professional use of 'python'/i),
      ).toBeInTheDocument();
    });

    it("shows candidate evidence for a match when expanded", async () => {
      vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
      vi.spyOn(apiClient, "getJobRequirementComparison").mockResolvedValue(COMPARISON_RESPONSE);
      renderPage();

      const select = await screen.findByLabelText(/select a discovered job/i);
      await userEvent.selectOptions(select, "1");

      const pythonMatch = (await screen.findByText("python")).closest(".requirement-comparison-panel__match");
      await userEvent.click(within(pythonMatch).getByText(/candidate evidence/i));
      expect(within(pythonMatch).getByText(/Fictional Analytics Corp/)).toBeVisible();
    });

    it("preserves education-dependent experience alternatives and flags the unresolved group", async () => {
      vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
      vi.spyOn(apiClient, "getJobRequirementComparison").mockResolvedValue(COMPARISON_RESPONSE);
      renderPage();

      const select = await screen.findByLabelText(/select a discovered job/i);
      await userEvent.selectOptions(select, "1");

      expect(await screen.findByText("12+ years with Bachelor's")).toBeInTheDocument();
      expect(screen.getByText("9+ years with PhD")).toBeInTheDocument();
      expect(screen.getByText(/no single alternative fully satisfies/i)).toBeInTheDocument();
    });

    it("shows an honest, non-fabricated message when the job has no usable description", async () => {
      vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
      vi.spyOn(apiClient, "getJobRequirementComparison").mockResolvedValue(EMPTY_COMPARISON_RESPONSE);
      renderPage();

      const select = await screen.findByLabelText(/select a discovered job/i);
      await userEvent.selectOptions(select, "1");

      expect(
        await screen.findByText(/a meaningful comparison cannot be performed without extracted job requirements/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/human review is still required/i)).toBeInTheDocument();
    });

    it("shows an error state when the comparison request fails", async () => {
      vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
      vi.spyOn(apiClient, "getJobRequirementComparison").mockRejectedValue(
        new Error("Request to /jobs/1/requirement-comparison failed (503): unavailable"),
      );
      renderPage();

      const select = await screen.findByLabelText(/select a discovered job/i);
      await userEvent.selectOptions(select, "1");

      expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
    });

    it("refetches and replaces the comparison when switching to a different job, never showing stale data", async () => {
      vi.spyOn(apiClient, "getJobs").mockResolvedValue([
        ...JOBS,
        { id: 2, title: "Office Coordinator", company: "Acme", location: "NY", url: "https://x/2", source: "greenhouse" },
      ]);
      const comparisonSpy = vi.spyOn(apiClient, "getJobRequirementComparison");
      comparisonSpy.mockResolvedValueOnce(COMPARISON_RESPONSE);
      renderPage();

      const select = await screen.findByLabelText(/select a discovered job/i);
      await userEvent.selectOptions(select, "1");
      await screen.findByText("python");

      comparisonSpy.mockResolvedValueOnce(EMPTY_COMPARISON_RESPONSE);
      await userEvent.selectOptions(select, "2");

      await waitFor(() => expect(comparisonSpy).toHaveBeenCalledWith("2"));
      expect(
        await screen.findByText(/a meaningful comparison cannot be performed without extracted job requirements/i),
      ).toBeInTheDocument();
      expect(screen.queryByText("python")).not.toBeInTheDocument();
    });

    it("does not affect the existing mock AI review flow", async () => {
      vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
      vi.spyOn(apiClient, "getJobRequirementComparison").mockResolvedValue(COMPARISON_RESPONSE);
      const reviewSpy = vi.spyOn(apiClient, "getAIReview").mockResolvedValue(SUCCESS_RESPONSE);
      renderPage();

      const select = await screen.findByLabelText(/select a discovered job/i);
      await userEvent.selectOptions(select, "1");
      await userEvent.click(screen.getByRole("button", { name: /request ai review/i }));

      await waitFor(() => expect(reviewSpy).toHaveBeenCalledWith("1"));
      expect(await screen.findByText("Mock job analysis")).toBeInTheDocument();
      expect(screen.getByText(/demo comparison/i)).toBeInTheDocument();
    });

    it("never shows a hiring probability or ATS score anywhere in the comparison view", async () => {
      vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
      vi.spyOn(apiClient, "getJobRequirementComparison").mockResolvedValue(COMPARISON_RESPONSE);
      renderPage();

      const select = await screen.findByLabelText(/select a discovered job/i);
      await userEvent.selectOptions(select, "1");

      await screen.findByText("python");
      expect(screen.queryByText(/hiring probability/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/ats score/i)).not.toBeInTheDocument();
    });
  });
});
