import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import DiscoverJobs from "./DiscoverJobs";
import * as apiClient from "../api/client";

const JOBS = [
  { id: 1, title: "Data Engineer", company: "Acme", location: "New York, NY", url: "https://example.com/1", source: "greenhouse" },
  { id: 2, title: "Medicinal Chemist", company: "Pharma Co", location: "Boston, MA", url: "https://example.com/2", source: "lever" },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <DiscoverJobs />
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("DiscoverJobs", () => {
  it("shows a loading state before data arrives", () => {
    vi.spyOn(apiClient, "getJobs").mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByRole("status")).toHaveTextContent(/loading/i);
  });

  it("renders fetched jobs with a link to the original posting", async () => {
    // Genuine (non-demo-placeholder) URLs, since the posting link is now
    // hidden for example.com records -- see the dedicated demo-record test.
    const realJobs = JOBS.map((job, i) => ({ ...job, url: `https://careers.realco.com/${i + 1}` }));
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(realJobs);
    renderPage();

    expect(await screen.findByText("Data Engineer")).toBeInTheDocument();
    expect(screen.getByText("Medicinal Chemist")).toBeInTheDocument();

    const postingLinks = screen.getAllByRole("link", { name: /view original posting/i });
    expect(postingLinks[0]).toHaveAttribute("href", "https://careers.realco.com/1");
  });

  it("hides the posting link for demo-seeded placeholder records, but keeps View Details working", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS); // example.com URLs
    renderPage();

    const card = (await screen.findByText("Data Engineer")).closest(".job-card");
    expect(within(card).queryByRole("link", { name: /view original posting/i })).not.toBeInTheDocument();
    expect(within(card).getByRole("link", { name: /^view details$/i })).toHaveAttribute("href", "/jobs/1");
  });

  it("shows a distinct View Details link to job detail, separate from the title link and the posting link", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    renderPage();

    const viewDetailsLinks = await screen.findAllByRole("link", { name: /^view details$/i });
    expect(viewDetailsLinks[0]).toHaveAttribute("href", "/jobs/1");
  });

  it("only shows a posting link when the job has a valid URL", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue([
      ...JOBS,
      { id: 3, title: "No URL Role", company: "Acme", location: "Remote", url: "", source: "greenhouse" },
    ]);
    renderPage();

    const card = (await screen.findByText("No URL Role")).closest(".job-card");
    expect(within(card).queryByRole("link", { name: /view original posting/i })).not.toBeInTheDocument();
    expect(within(card).getByRole("link", { name: /^view details$/i })).toBeInTheDocument();
  });

  it("marks the job title as a clearly-labeled navigation link, distinct from the external posting link", async () => {
    const realJobs = JOBS.map((job, i) => ({ ...job, url: `https://careers.realco.com/${i + 1}` }));
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(realJobs);
    renderPage();

    const titleLink = await screen.findByRole("link", { name: /data engineer/i });
    expect(titleLink).toHaveAttribute("href", "/jobs/1");
    expect(titleLink).toHaveAttribute("title", "View full job details");

    const postingLink = screen.getAllByRole("link", { name: /view original posting/i })[0];
    expect(postingLink).toHaveAttribute("target", "_blank");
    expect(postingLink).not.toBe(titleLink);
  });

  it("filters by title/company search text", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    renderPage();
    await screen.findByText("Data Engineer");

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/search title or company/i), "chemist");

    await waitFor(() => {
      expect(screen.queryByText("Data Engineer")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Medicinal Chemist")).toBeInTheDocument();
  });

  it("labels jobs seeded at the example.com placeholder domain as demo records, not real companies by name", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue([
      ...JOBS,
      { id: 3, title: "Analyst", company: "Realco", location: "Remote", url: "https://careers.realco.com/3", source: "greenhouse" },
    ]);
    renderPage();

    await screen.findByText("Data Engineer");
    const demoBadges = screen.getAllByText("Demo record");
    expect(demoBadges).toHaveLength(2);
    expect(screen.queryByText("Analyst")).toBeInTheDocument();
  });

  it("shows the page heading and subtitle without claiming to search the whole internet or run an active agent", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    renderPage();

    expect(await screen.findByRole("heading", { name: "Discover Opportunities" })).toBeInTheDocument();
    expect(
      screen.getByText("Explore job opportunities collected from company career pages."),
    ).toBeInTheDocument();
  });

  it("shows an empty state when no jobs are returned", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText(/no jobs match these filters/i)).toBeInTheDocument();
  });

  it("shows an error state with a retry action on failure", async () => {
    vi.spyOn(apiClient, "getJobs").mockRejectedValue(new Error("Could not reach the JobPilot AI backend."));
    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not reach/i);
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});
