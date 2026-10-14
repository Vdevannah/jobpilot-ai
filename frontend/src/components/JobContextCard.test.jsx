import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import JobContextCard from "./JobContextCard";

const JOB = { id: 1, title: "Data Engineer", company: "Acme", location: "New York, NY" };

describe("JobContextCard", () => {
  it("renders nothing when no job is selected", () => {
    const { container } = render(<JobContextCard job={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the job's own title, company, and location", () => {
    render(<JobContextCard job={JOB} />);
    expect(screen.getByText("Data Engineer")).toBeInTheDocument();
    expect(screen.getByText("Acme")).toBeInTheDocument();
    expect(screen.getByText("New York, NY")).toBeInTheDocument();
  });

  it("does not show a track pill when no track label is given", () => {
    render(<JobContextCard job={JOB} />);
    expect(document.querySelector(".job-context-card__track")).not.toBeInTheDocument();
  });

  it("shows the track pill only when a track label is explicitly provided", () => {
    render(<JobContextCard job={JOB} trackLabel="Data" />);
    expect(screen.getByText("Data")).toBeInTheDocument();
  });
});
