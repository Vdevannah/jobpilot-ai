import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import PersonalizedAnalysisPanel from "./PersonalizedAnalysisPanel";
import * as apiClient from "../api/client";

const PREVIEW_RESPONSE = { preview: "Location: Delaware, USA\nProfessional Experience:\nData Engineer, 5 years" };

const ANALYSIS_RESPONSE = {
  job_id: 1,
  variant: "data",
  variant_matches_job_track: true,
  live_job_analysis: { required_skills: ["python"], preferred_skills: [], minimum_experience_years: 5, job_track: "data", summary: "Live summary." },
  requirement_comparison: {
    job_id: 1,
    matches: [
      {
        requirement_kind: "skill", requirement_description: "python", requirement_evidence: [],
        is_required: true, alternative_group: null,
        candidate_evidence: [{ claim: "Data Engineer", source_category: "professional_experience", professional_experience_years: 5.0 }],
        evidence_source_categories: ["professional_experience"], status: "supported",
        explanation: "Supported.", limitations: [],
      },
    ],
    unresolved_alternative_groups: [], overall_limitations: [],
    analysis_mode: "mock", requires_human_review: true, status: "pending_review",
  },
  candidate_is_fictional: false,
  comparison_scope: "personalized",
  analysis_mode: "mock",
  requires_human_review: true,
  status: "pending_review",
  limitations: ["This is a personalized analysis of the resume text you explicitly reviewed and approved."],
};

const ASSISTANCE_RESPONSE = {
  job_id: 1,
  variant: "data",
  assistance: {
    resume_suggestions: ["Lead with Python."],
    bullet_rewrites: ["Rewrote bullet."],
    cover_letter_draft: "Draft cover letter.",
    interview_talking_points: ["Discuss your pipeline project."],
    analysis_mode: "mock",
    requires_human_review: true,
    status: "pending_review",
    limitations: ["Fixed mock sample output; not derived from the supplied evidence."],
  },
};

afterEach(() => {
  vi.restoreAllMocks();
});

async function pasteResume(text = "Professional Experience:\nData Engineer, 5 years") {
  await userEvent.type(screen.getByLabelText(/your resume text/i), text);
}

describe("PersonalizedAnalysisPanel", () => {
  it("makes no API call at all until the user clicks Preview", () => {
    const previewSpy = vi.spyOn(apiClient, "previewResumeText");
    const analysisSpy = vi.spyOn(apiClient, "getPersonalizedAnalysis");
    render(<PersonalizedAnalysisPanel jobId="1" />);

    expect(previewSpy).not.toHaveBeenCalled();
    expect(analysisSpy).not.toHaveBeenCalled();
  });

  it("previews only after explicit user action, never automatically from typing alone", async () => {
    const previewSpy = vi.spyOn(apiClient, "previewResumeText").mockResolvedValue(PREVIEW_RESPONSE);
    render(<PersonalizedAnalysisPanel jobId="1" />);

    await pasteResume();
    expect(previewSpy).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /preview sanitized text/i }));
    await waitFor(() => expect(previewSpy).toHaveBeenCalledWith(
      "Professional Experience:\nData Engineer, 5 years", [],
    ));
  });

  it("requires the approval checkbox before enabling personalized analysis or assistance", async () => {
    vi.spyOn(apiClient, "previewResumeText").mockResolvedValue(PREVIEW_RESPONSE);
    render(<PersonalizedAnalysisPanel jobId="1" />);

    await pasteResume();
    await userEvent.click(screen.getByRole("button", { name: /preview sanitized text/i }));
    await screen.findByText(/Data Engineer, 5 years/, { selector: "pre" });

    expect(screen.getByRole("button", { name: /approve & run personalized analysis/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /generate application assistance/i })).toBeDisabled();

    await userEvent.click(screen.getByRole("checkbox"));
    expect(screen.getByRole("button", { name: /approve & run personalized analysis/i })).toBeEnabled();
  });

  it("never calls the analysis endpoint before the checkbox is checked", async () => {
    vi.spyOn(apiClient, "previewResumeText").mockResolvedValue(PREVIEW_RESPONSE);
    const analysisSpy = vi.spyOn(apiClient, "getPersonalizedAnalysis").mockResolvedValue(ANALYSIS_RESPONSE);
    render(<PersonalizedAnalysisPanel jobId="1" />);

    await pasteResume();
    await userEvent.click(screen.getByRole("button", { name: /preview sanitized text/i }));
    await screen.findByText(/Data Engineer, 5 years/, { selector: "pre" });

    expect(analysisSpy).not.toHaveBeenCalled();
  });

  it("runs personalized analysis only after preview and explicit approval, and shows a PERSONALIZED (not DEMO) banner", async () => {
    vi.spyOn(apiClient, "previewResumeText").mockResolvedValue(PREVIEW_RESPONSE);
    const analysisSpy = vi.spyOn(apiClient, "getPersonalizedAnalysis").mockResolvedValue(ANALYSIS_RESPONSE);
    render(<PersonalizedAnalysisPanel jobId="1" />);

    await pasteResume();
    await userEvent.click(screen.getByRole("button", { name: /preview sanitized text/i }));
    await screen.findByText(/Data Engineer, 5 years/, { selector: "pre" });
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /approve & run personalized analysis/i }));

    await waitFor(() => expect(analysisSpy).toHaveBeenCalledWith("1", {
      previewText: PREVIEW_RESPONSE.preview, confirmed: true, variant: "data", mode: "mock",
    }));
    expect(await screen.findByText(/personalized analysis/i, { selector: ".requirement-comparison-panel__personalized-banner" })).toBeInTheDocument();
    expect(screen.queryByText(/demo comparison/i)).not.toBeInTheDocument();
    expect(screen.getByText("python")).toBeInTheDocument();
  });

  it("flags a variant/job-track mismatch rather than silently ignoring it", async () => {
    vi.spyOn(apiClient, "previewResumeText").mockResolvedValue(PREVIEW_RESPONSE);
    vi.spyOn(apiClient, "getPersonalizedAnalysis").mockResolvedValue({
      ...ANALYSIS_RESPONSE, variant_matches_job_track: false,
    });
    render(<PersonalizedAnalysisPanel jobId="1" />);

    await pasteResume();
    await userEvent.click(screen.getByRole("button", { name: /preview sanitized text/i }));
    await screen.findByText(/Data Engineer, 5 years/, { selector: "pre" });
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /approve & run personalized analysis/i }));

    expect(await screen.findByText(/does not match this job's own detected career track/i)).toBeInTheDocument();
  });

  it("edits to the resume text after a preview invalidate the prior approval", async () => {
    vi.spyOn(apiClient, "previewResumeText").mockResolvedValue(PREVIEW_RESPONSE);
    render(<PersonalizedAnalysisPanel jobId="1" />);

    await pasteResume();
    await userEvent.click(screen.getByRole("button", { name: /preview sanitized text/i }));
    await screen.findByText(/Data Engineer, 5 years/, { selector: "pre" });
    await userEvent.click(screen.getByRole("checkbox"));

    await userEvent.type(screen.getByLabelText(/your resume text/i), " more text");

    expect(screen.queryByText(/Data Engineer, 5 years/, { selector: "pre" })).not.toBeInTheDocument();
  });

  it("generates application assistance only after approval, grounded and reviewable", async () => {
    vi.spyOn(apiClient, "previewResumeText").mockResolvedValue(PREVIEW_RESPONSE);
    const assistanceSpy = vi.spyOn(apiClient, "getApplicationAssistance").mockResolvedValue(ASSISTANCE_RESPONSE);
    render(<PersonalizedAnalysisPanel jobId="1" />);

    await pasteResume();
    await userEvent.click(screen.getByRole("button", { name: /preview sanitized text/i }));
    await screen.findByText(/Data Engineer, 5 years/, { selector: "pre" });
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /generate application assistance/i }));

    await waitFor(() => expect(assistanceSpy).toHaveBeenCalled());
    expect(await screen.findByText("Draft cover letter.")).toBeInTheDocument();
    expect(screen.getByText("Lead with Python.")).toBeInTheDocument();
    expect(screen.getByText(/fixed mock sample output/i)).toBeInTheDocument();
  });

  it("shows an error state when the preview request fails", async () => {
    vi.spyOn(apiClient, "previewResumeText").mockRejectedValue(new Error("Request failed (400): bad input"));
    render(<PersonalizedAnalysisPanel jobId="1" />);

    await pasteResume();
    await userEvent.click(screen.getByRole("button", { name: /preview sanitized text/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/bad input/i);
  });

  it("shows an error state when the personalized analysis request fails", async () => {
    vi.spyOn(apiClient, "previewResumeText").mockResolvedValue(PREVIEW_RESPONSE);
    vi.spyOn(apiClient, "getPersonalizedAnalysis").mockRejectedValue(
      new Error("Request failed (503): Live OpenAI analysis is unavailable."),
    );
    render(<PersonalizedAnalysisPanel jobId="1" />);

    await pasteResume();
    await userEvent.click(screen.getByRole("button", { name: /preview sanitized text/i }));
    await screen.findByText(/Data Engineer, 5 years/, { selector: "pre" });
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /approve & run personalized analysis/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
  });

  it("never shows a hiring probability or ATS score", async () => {
    vi.spyOn(apiClient, "previewResumeText").mockResolvedValue(PREVIEW_RESPONSE);
    vi.spyOn(apiClient, "getPersonalizedAnalysis").mockResolvedValue(ANALYSIS_RESPONSE);
    render(<PersonalizedAnalysisPanel jobId="1" />);

    await pasteResume();
    await userEvent.click(screen.getByRole("button", { name: /preview sanitized text/i }));
    await screen.findByText(/Data Engineer, 5 years/, { selector: "pre" });
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /approve & run personalized analysis/i }));

    await screen.findByText("python");
    expect(screen.queryByText(/hiring probability/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/ats score/i)).not.toBeInTheDocument();
  });
});
