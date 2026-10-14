import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import JobDetail from "./JobDetail";
import * as apiClient from "../api/client";

const JOB = {
  id: 1, title: "Data Engineer", company: "Acme", location: "New York, NY",
  url: "https://example.com/1", source: "greenhouse",
  description: "Build and maintain data pipelines.",
};

const REQUIREMENTS_RESPONSE = {
  requirements: {
    job_id: 1,
    job_title: "Data Engineer",
    career_track: "data",
    career_track_evidence: [],
    required_skills: ["python"],
    required_skills_evidence: { python: [{ quote: "5+ years of Python experience", char_start: 0, char_end: 30 }] },
    preferred_skills: ["kafka"],
    preferred_skills_evidence: { kafka: [{ quote: "Experience with Kafka", char_start: 31, char_end: 53 }] },
    experience_requirements: [
      { minimum_years: 5.0, education_qualifier: null, is_required: true, alternative_group: null, evidence: [] },
    ],
    required_education: ["Bachelor's degree"],
    required_education_evidence: { "Bachelor's degree": [] },
    preferred_education: [],
    preferred_education_evidence: {},
    responsibilities: ["Build and maintain data pipelines"],
    responsibilities_evidence: {},
    domain_expertise: ["data pipeline"],
    domain_expertise_evidence: {},
    location_requirement: "This role is fully remote.",
    remote_allowed: true,
    location_evidence: [],
    missing_information: [],
    ambiguous_information: [],
    analysis_mode: "deterministic",
    limitations: ["Extraction is deterministic (keyword/regex-based)."],
    requires_human_review: true,
    status: "pending_review",
  },
  is_demo_record: false,
  source: "greenhouse",
};

const EMPTY_REQUIREMENTS_RESPONSE = {
  requirements: {
    job_id: 1,
    job_title: "Data Engineer",
    career_track: "unknown",
    career_track_evidence: [],
    required_skills: [],
    required_skills_evidence: {},
    preferred_skills: [],
    preferred_skills_evidence: {},
    experience_requirements: [],
    required_education: [],
    required_education_evidence: {},
    preferred_education: [],
    preferred_education_evidence: {},
    responsibilities: [],
    responsibilities_evidence: {},
    domain_expertise: [],
    domain_expertise_evidence: {},
    location_requirement: null,
    remote_allowed: null,
    location_evidence: [],
    missing_information: ["No job description is available for this posting."],
    ambiguous_information: [],
    analysis_mode: "deterministic",
    limitations: ["Extraction is deterministic (keyword/regex-based)."],
    requires_human_review: true,
    status: "pending_review",
  },
  is_demo_record: false,
  source: "greenhouse",
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
    // A genuine (non-demo-placeholder) URL, since the posting link is now
    // hidden for example.com records -- see the "only shows..." test below.
    const realJob = { ...JOB, url: "https://careers.acme-corp.com/1" };
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(realJob);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    expect(await screen.findByText("Build and maintain data pipelines.")).toBeInTheDocument();
    expect(screen.getByText(/Acme/)).toBeInTheDocument();
    expect(screen.getByText(/greenhouse/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view original posting/i })).toHaveAttribute(
      "href",
      "https://careers.acme-corp.com/1",
    );
  });

  it("shows an explicit notice when the description is missing, rather than fabricating one", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue({ ...JOB, description: null });
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    expect(
      await screen.findByText("Job description is unavailable. Match scores may be based on limited information."),
    ).toBeInTheDocument();
  });

  it("renders the existing score breakdown when a match is available", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    // "82%" and "Strong Match" now appear both in the compact summary near
    // the header and in the full breakdown below -- scope to the full
    // breakdown section specifically.
    await screen.findByText("Skill score");
    const breakdown = document.getElementById("match-breakdown");
    expect(within(breakdown).getByText("82%")).toBeInTheDocument();
    expect(within(breakdown).getByText("Strong Match")).toBeInTheDocument();
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

    expect(await screen.findByText(/not predictions of hiring likelihood/i)).toBeInTheDocument();
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

  it("only shows the posting link when the job has a valid URL", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue({ ...JOB, url: "" });
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    await screen.findByText(JOB.title);
    expect(screen.queryByRole("link", { name: /view original posting/i })).not.toBeInTheDocument();
  });

  it("hides the posting link for a demo-seeded placeholder record, but keeps internal AI nav links", async () => {
    // JOB.url is the example.com placeholder domain, so it's a demo record.
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    await screen.findByText("Demo record");
    expect(screen.queryByRole("link", { name: /view original posting/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /get resume recommendation/i })).toHaveAttribute(
      "href",
      "/resumes?jobId=1",
    );
  });

  it("shows the posting link for a genuine job with a real URL", async () => {
    const realJob = { ...JOB, url: "https://careers.acme-corp.com/1" };
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(realJob);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    await screen.findByText(JOB.title);
    expect(screen.getByRole("link", { name: /view original posting/i })).toHaveAttribute(
      "href",
      "https://careers.acme-corp.com/1",
    );
  });

  it("omits the source meta item rather than showing a blank one when source is unavailable", async () => {
    vi.spyOn(apiClient, "getJobById").mockResolvedValue({ ...JOB, source: "" });
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    await screen.findByText(JOB.title);
    expect(screen.queryByText("greenhouse")).not.toBeInTheDocument();
  });

  it("marks the job title area and posting link as distinct, clearly-labeled navigation", async () => {
    const realJob = { ...JOB, url: "https://careers.acme-corp.com/1" };
    vi.spyOn(apiClient, "getJobById").mockResolvedValue(realJob);
    vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
    renderDetail();

    const postingLink = await screen.findByRole("link", { name: /view original posting/i });
    expect(postingLink).toHaveAttribute("target", "_blank");
    expect(postingLink).toHaveAttribute("href", "https://careers.acme-corp.com/1");
  });

  describe("compact match summary", () => {
    it("shows the score, recommendation, and career track near the top, without presenting it as a hiring probability", async () => {
      vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      renderDetail();

      await screen.findByText(JOB.title);
      const summary = document.querySelector(".job-detail__summary");
      expect(within(summary).getByText("82%")).toBeInTheDocument();
      expect(within(summary).getByText("Strong Match")).toBeInTheDocument();
      expect(within(summary).getByText("Data")).toBeInTheDocument();
      expect(screen.queryByText(/hiring probability/i)).not.toBeInTheDocument();
    });

    it("shows a concise limited-evidence note when no career track was detected, without inferring missing skills", async () => {
      const unknownTrackMatch = { ...MATCH, job_track: null };
      vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([unknownTrackMatch]);
      renderDetail();

      await screen.findByText(JOB.title);
      const summary = document.querySelector(".job-detail__summary");
      expect(within(summary).getByText(/no career track was detected/i)).toBeInTheDocument();
    });

    it("shows a truthful unavailable state, not an invented score, when there is no corresponding match", async () => {
      vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([]);
      renderDetail();

      await screen.findByText(JOB.title);
      const summary = document.querySelector(".job-detail__summary");
      expect(within(summary).getByText(/no match information is available/i)).toBeInTheDocument();
      expect(within(summary).queryByText(/%/)).not.toBeInTheDocument();
    });

    it("does not duplicate the full score grid, skills, or reasons from the detailed breakdown", async () => {
      vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      renderDetail();

      await screen.findByText(JOB.title);
      const summary = document.querySelector(".job-detail__summary");
      expect(within(summary).queryByText("Skill score")).not.toBeInTheDocument();
      expect(within(summary).queryByText("python, sql")).not.toBeInTheDocument();
    });

    it("provides a keyboard-reachable link to the full match breakdown section", async () => {
      vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      renderDetail();

      await screen.findByText(JOB.title);
      const link = screen.getByRole("link", { name: /view full match breakdown/i });
      expect(link).toHaveAttribute("href", "#match-breakdown");
      expect(document.getElementById("match-breakdown")).not.toBeNull();

      link.focus();
      expect(link).toHaveFocus();
    });
  });

  describe("job description rendering", () => {
    it("preserves paragraph breaks when the stored description has them", async () => {
      vi.spyOn(apiClient, "getJobById").mockResolvedValue({
        ...JOB,
        description: "First paragraph.\n\nSecond paragraph.",
      });
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      renderDetail();

      expect(await screen.findByText("First paragraph.")).toBeInTheDocument();
      expect(screen.getByText("Second paragraph.")).toBeInTheDocument();
    });

    it("renders HTML-like description content as literal text, never as executable markup", async () => {
      const text = "<img src=x onerror=alert(1)> and <b>bold</b> claims.";
      vi.spyOn(apiClient, "getJobById").mockResolvedValue({ ...JOB, description: text });
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      const { container } = renderDetail();

      expect(await screen.findByText(text)).toBeInTheDocument();
      expect(container.querySelector("img")).not.toBeInTheDocument();
      expect(container.querySelector("b")).not.toBeInTheDocument();
    });

    it("keeps a very long description complete (not truncated) once expanded via Read full description", async () => {
      const longText = "word ".repeat(2500).trim();
      vi.spyOn(apiClient, "getJobById").mockResolvedValue({ ...JOB, description: longText });
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      renderDetail();

      const toggle = await screen.findByRole("button", { name: /read full description/i });
      await userEvent.click(toggle);
      expect(screen.getByText(longText)).toBeInTheDocument();
    });

    it("shows a readable preview with a Read full description button for a long description", async () => {
      const longText = "word ".repeat(2500).trim();
      vi.spyOn(apiClient, "getJobById").mockResolvedValue({ ...JOB, description: longText });
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      renderDetail();

      await screen.findByRole("button", { name: /read full description/i });
      expect(screen.queryByText(longText)).not.toBeInTheDocument();
    });

    it("shows Show less after expanding, and collapses back when clicked", async () => {
      const longText = "word ".repeat(2500).trim();
      vi.spyOn(apiClient, "getJobById").mockResolvedValue({ ...JOB, description: longText });
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      renderDetail();

      await userEvent.click(await screen.findByRole("button", { name: /read full description/i }));
      await userEvent.click(screen.getByRole("button", { name: /show less/i }));
      expect(screen.queryByText(longText)).not.toBeInTheDocument();
      expect(await screen.findByRole("button", { name: /read full description/i })).toBeInTheDocument();
    });

    it("still shows the missing-description notice unchanged", async () => {
      vi.spyOn(apiClient, "getJobById").mockResolvedValue({ ...JOB, description: null });
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      renderDetail();

      expect(
        await screen.findByText("Job description is unavailable. Match scores may be based on limited information."),
      ).toBeInTheDocument();
    });
  });

  describe("extracted requirements (Phase 9A)", () => {
    it("loads and displays job-specific required/preferred skills, experience, and education", async () => {
      vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      const requirementsSpy = vi.spyOn(apiClient, "getJobRequirements").mockResolvedValue(REQUIREMENTS_RESPONSE);
      renderDetail();

      expect(await screen.findByText("Extracted Requirements")).toBeInTheDocument();
      expect(requirementsSpy).toHaveBeenCalledWith("1");
      expect(screen.getByText("python")).toBeInTheDocument();
      expect(screen.getByText("kafka")).toBeInTheDocument();
      expect(screen.getByText("5+ years")).toBeInTheDocument();
      expect(screen.getByText("Bachelor's degree")).toBeInTheDocument();
      expect(screen.getByText("Build and maintain data pipelines")).toBeInTheDocument();
    });

    it("labels the extraction as deterministic and requiring human review", async () => {
      vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      vi.spyOn(apiClient, "getJobRequirements").mockResolvedValue(REQUIREMENTS_RESPONSE);
      renderDetail();

      expect(await screen.findByText("Deterministic extraction")).toBeInTheDocument();
      expect(screen.getByText("Requires human review")).toBeInTheDocument();
    });

    it("lets a user inspect the supporting job-description evidence for a requirement", async () => {
      vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      vi.spyOn(apiClient, "getJobRequirements").mockResolvedValue(REQUIREMENTS_RESPONSE);
      renderDetail();

      const pythonItem = (await screen.findByText("python")).closest(".job-requirements-panel__skill-item");
      const toggle = within(pythonItem).getByText(/show evidence/i);
      expect(toggle.closest("details")).not.toHaveAttribute("open");
      await userEvent.click(toggle);
      expect(toggle.closest("details")).toHaveAttribute("open");
      expect(screen.getByText(/5\+ years of Python experience/)).toBeVisible();
    });

    it("shows a missing-information notice and no fabricated requirements when the description is unavailable", async () => {
      vi.spyOn(apiClient, "getJobById").mockResolvedValue({ ...JOB, description: null });
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      vi.spyOn(apiClient, "getJobRequirements").mockResolvedValue(EMPTY_REQUIREMENTS_RESPONSE);
      renderDetail();

      expect(await screen.findByText("No job description is available for this posting.")).toBeInTheDocument();
      expect(screen.getByText(/no structured requirements could be extracted/i)).toBeInTheDocument();
    });

    it("shows an error state for the requirements section when the request fails, without blocking the rest of the page", async () => {
      vi.spyOn(apiClient, "getJobById").mockResolvedValue(JOB);
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);
      vi.spyOn(apiClient, "getJobRequirements").mockRejectedValue(
        new Error("Request to /jobs/1/requirements failed (503): unavailable"),
      );
      renderDetail();

      expect(await screen.findByText(JOB.title)).toBeInTheDocument();
      expect(await screen.findByRole("alert")).toHaveTextContent(/unavailable/i);
    });

    it("requests requirements for the job in the current route, keyed by that job's own ID", async () => {
      const requirementsSpy = vi.spyOn(apiClient, "getJobRequirements").mockResolvedValue(REQUIREMENTS_RESPONSE);
      vi.spyOn(apiClient, "getJobById").mockImplementation((id) => Promise.resolve({ ...JOB, id: Number(id) }));
      vi.spyOn(apiClient, "getMatches").mockResolvedValue([MATCH]);

      renderDetail("1");
      await screen.findByText("Extracted Requirements");
      expect(requirementsSpy).toHaveBeenCalledWith("1");

      requirementsSpy.mockClear();
      renderDetail("2");
      await waitFor(() => expect(requirementsSpy).toHaveBeenCalledWith("2"));
    });
  });
});
