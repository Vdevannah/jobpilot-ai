import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import Sidebar from "./Sidebar";

function renderSidebar(initialPath = "/discover") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Sidebar open={false} onNavigate={vi.fn()} />
    </MemoryRouter>,
  );
}

describe("Sidebar", () => {
  it("keeps the five existing routes and no unimplemented ones", () => {
    renderSidebar();
    const nav = screen.getByRole("navigation", { name: /primary/i });
    const links = Array.from(nav.querySelectorAll("a")).map((a) => a.getAttribute("href"));
    expect(links).toEqual(["/", "/discover", "/matches", "/resumes", "/insights"]);
    expect(screen.queryByText(/companies/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/favorites/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/settings/i)).not.toBeInTheDocument();
  });

  it("marks the current route's nav item as active via aria-current", async () => {
    renderSidebar("/matches");
    const activeLink = screen.getByRole("link", { name: /job matches/i });
    expect(activeLink).toHaveAttribute("aria-current", "page");
    expect(activeLink).toHaveClass("sidebar__link--active");

    const inactiveLink = screen.getByRole("link", { name: /discover jobs/i });
    expect(inactiveLink).not.toHaveAttribute("aria-current");
  });

  it("supports keyboard navigation to and activation of a nav link", async () => {
    const onNavigate = vi.fn();
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Sidebar open={false} onNavigate={onNavigate} />
      </MemoryRouter>,
    );

    await userEvent.tab();
    const firstLink = screen.getByRole("link", { name: /dashboard/i });
    expect(firstLink).toHaveFocus();

    await userEvent.keyboard("{Enter}");
    expect(onNavigate).toHaveBeenCalled();
  });

  it("shows current, non-phase-specific footer text", () => {
    renderSidebar();
    expect(screen.getByText(/jobpilot ai/i, { selector: ".sidebar__footer-text" })).toBeInTheDocument();
    expect(screen.queryByText(/phase 8c/i)).not.toBeInTheDocument();
  });
});
