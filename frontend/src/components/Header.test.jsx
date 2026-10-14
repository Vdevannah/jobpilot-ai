import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Header from "./Header";

describe("Header", () => {
  it("shows the page title and backend connection status", () => {
    render(<Header title="Dashboard" backendStatus={{ status: "online", detail: "" }} onMenuClick={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText(/backend connected/i)).toBeInTheDocument();
  });

  it("does not render any fabricated notifications, profile menu, or agent activity", () => {
    render(<Header title="Dashboard" backendStatus={{ status: "online", detail: "" }} onMenuClick={vi.fn()} />);

    expect(screen.queryByRole("button", { name: /notification/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /profile|account/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/agent/i)).not.toBeInTheDocument();
  });

  it("invokes onMenuClick when the mobile menu button is activated", async () => {
    const onMenuClick = vi.fn();
    render(<Header title="Dashboard" backendStatus={{ status: "online", detail: "" }} onMenuClick={onMenuClick} />);

    await userEvent.click(screen.getByRole("button", { name: /toggle navigation/i }));
    expect(onMenuClick).toHaveBeenCalledTimes(1);
  });
});
