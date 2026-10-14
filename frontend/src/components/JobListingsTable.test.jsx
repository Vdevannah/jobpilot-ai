import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import JobListingsTable from "./JobListingsTable";

const LONG_TITLE =
  "Senior Staff Principal Data Engineer, Foundational Analytics and Machine Learning Infrastructure Platform";

const ROWS = [
  {
    job_id: 1,
    title: LONG_TITLE,
    company: "Airbnb",
    location: "Remote",
    url: "https://careers.airbnb.com/1",
    source: "greenhouse",
    overall_score: 82,
  },
  {
    job_id: 2,
    title: "Data Scientist",
    company: "Acme",
    location: "New York, NY",
    url: "https://example.com/2",
    source: "greenhouse",
    overall_score: 41,
  },
];

function renderTable(rows = ROWS) {
  return render(
    <MemoryRouter>
      <JobListingsTable rows={rows} />
    </MemoryRouter>,
  );
}

describe("JobListingsTable", () => {
  it("renders a short title as plain, fully readable text", () => {
    renderTable();
    const link = screen.getByRole("link", { name: "Data Scientist" });
    expect(link).toHaveTextContent("Data Scientist");
  });

  it("keeps the full long title in the link's text content, not just in a hover tooltip", () => {
    renderTable();
    // The accessible name comes from the link's own text, which is never
    // clamped at the DOM level -- only CSS line-clamp affects what's
    // visually painted (up to two lines), so this holds regardless of
    // visual truncation, and nothing here depends on the hover title.
    const link = screen.getByRole("link", { name: LONG_TITLE });
    expect(link).toHaveTextContent(LONG_TITLE);
    expect(link).toHaveClass("job-listings-table__title-link");
  });

  it("also exposes the full title via a title attribute, as a supplementary (not exclusive) hint", () => {
    renderTable();
    const link = screen.getByRole("link", { name: LONG_TITLE });
    expect(link).toHaveAttribute("title", LONG_TITLE);
  });

  it("navigates to job detail from both the title link and the View action", () => {
    renderTable();
    const row = screen.getByText("Data Scientist").closest("tr");
    const links = within(row).getAllByRole("link");
    expect(links.every((link) => link.getAttribute("href") === "/jobs/2")).toBe(true);
  });

  it("shows a demo-record badge only for jobs seeded at the example.com placeholder domain", () => {
    renderTable();
    const demoRow = screen.getByText("Data Scientist").closest("tr");
    expect(within(demoRow).getByText("Demo record")).toBeInTheDocument();

    const realRow = screen.getByText(LONG_TITLE).closest("tr");
    expect(within(realRow).queryByText("Demo record")).not.toBeInTheDocument();
  });

  it("shows 'Not available' rather than guessing when a row has no source", () => {
    renderTable([{ ...ROWS[0], source: undefined }]);
    expect(screen.getByText("Not available")).toBeInTheDocument();
  });

  it("wraps the table in a horizontally scrollable container", () => {
    renderTable();
    expect(screen.getByRole("table").closest(".job-listings-table__scroll")).not.toBeNull();
  });

  it("keeps the expected table structure: one header row, column headers, and one row per job", () => {
    renderTable();
    expect(screen.getByRole("columnheader", { name: "Job title" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Company" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Location" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Source" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Match score" })).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(ROWS.length + 1); // + header row
  });
});
