import { render, screen, waitFor } from "@testing-library/react";
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
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    renderPage();

    expect(await screen.findByText("Data Engineer")).toBeInTheDocument();
    expect(screen.getByText("Medicinal Chemist")).toBeInTheDocument();

    const postingLinks = screen.getAllByRole("link", { name: /view posting/i });
    expect(postingLinks[0]).toHaveAttribute("href", "https://example.com/1");
  });

  it("marks the job title as a clearly-labeled navigation link, distinct from the external posting link", async () => {
    vi.spyOn(apiClient, "getJobs").mockResolvedValue(JOBS);
    renderPage();

    const titleLink = await screen.findByRole("link", { name: /data engineer/i });
    expect(titleLink).toHaveAttribute("href", "/jobs/1");
    expect(titleLink).toHaveAttribute("title", "View full job details");

    const postingLink = screen.getAllByRole("link", { name: /view posting/i })[0];
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
