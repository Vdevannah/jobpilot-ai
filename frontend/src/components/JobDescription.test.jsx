import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import JobDescription from "./JobDescription";

describe("JobDescription", () => {
  it("renders a short, flat, unbroken description as one paragraph with no expand toggle", () => {
    const text = "A single long sentence with no newlines in it whatsoever, as real data has today.";
    render(<JobDescription text={text} />);
    expect(screen.getByText(text).closest("p")).not.toBeNull();
    expect(screen.queryByRole("button", { name: /read full description/i })).not.toBeInTheDocument();
  });

  it("preserves paragraph breaks when the text has them", () => {
    render(<JobDescription text={"First paragraph.\n\nSecond paragraph."} />);
    const paragraphs = screen.getAllByText(/paragraph\./);
    expect(paragraphs).toHaveLength(2);
    expect(paragraphs[0].tagName).toBe("SPAN");
    expect(paragraphs[0].closest("p")).not.toBe(paragraphs[1].closest("p"));
  });

  it("renders a bullet block as a real list", () => {
    render(<JobDescription text={"- First item\n- Second item"} />);
    const list = screen.getByRole("list");
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("First item");
    expect(list.tagName).toBe("UL");
  });

  it("renders HTML-like text as literal, inert text rather than parsing or executing it", () => {
    const text = "<script>alert('xss')</script> and <b>bold</b> claims.";
    const { container } = render(<JobDescription text={text} />);
    expect(screen.getByText(text)).toBeInTheDocument();
    expect(container.querySelector("script")).not.toBeInTheDocument();
    expect(container.querySelector("b")).not.toBeInTheDocument();
  });

  it("renders nothing for a missing or empty description", () => {
    const { container: emptyContainer } = render(<JobDescription text="" />);
    expect(emptyContainer).toBeEmptyDOMElement();

    const { container: nullContainer } = render(<JobDescription text={null} />);
    expect(nullContainer).toBeEmptyDOMElement();
  });

  describe("expand/collapse for a long description", () => {
    const longText = "word ".repeat(3000).trim();

    it("shows a truncated preview and a Read full description button initially", () => {
      render(<JobDescription text={longText} />);

      expect(screen.queryByText(longText)).not.toBeInTheDocument();
      const button = screen.getByRole("button", { name: /read full description/i });
      expect(button).toHaveAttribute("aria-expanded", "false");
    });

    it("reveals the complete text when the Read full description button is clicked", async () => {
      render(<JobDescription text={longText} />);

      await userEvent.click(screen.getByRole("button", { name: /read full description/i }));

      expect(screen.getByText(longText)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /show less/i })).toHaveAttribute("aria-expanded", "true");
    });

    it("collapses back to the preview when Show less is clicked", async () => {
      render(<JobDescription text={longText} />);

      await userEvent.click(screen.getByRole("button", { name: /read full description/i }));
      expect(screen.getByText(longText)).toBeInTheDocument();

      await userEvent.click(screen.getByRole("button", { name: /show less/i }));
      expect(screen.queryByText(longText)).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: /read full description/i })).toHaveAttribute(
        "aria-expanded",
        "false",
      );
    });

    it("supports keyboard activation of the toggle", async () => {
      render(<JobDescription text={longText} />);

      const button = screen.getByRole("button", { name: /read full description/i });
      button.focus();
      expect(button).toHaveFocus();

      await userEvent.keyboard("{Enter}");
      expect(screen.getByText(longText)).toBeInTheDocument();
    });

    it("associates the toggle with the content it controls via aria-controls", () => {
      render(<JobDescription text={longText} />);
      const button = screen.getByRole("button", { name: /read full description/i });
      const controlledId = button.getAttribute("aria-controls");
      expect(document.getElementById(controlledId)).not.toBeNull();
    });

    it("never truncates list items -- bullet lists are shown in full once expanded", async () => {
      const bulletText = Array.from({ length: 30 }, (_, i) => `- Bullet item number ${i} with enough text to be long.`).join(
        "\n",
      );
      render(<JobDescription text={bulletText} />);

      await userEvent.click(screen.getByRole("button", { name: /read full description/i }));
      expect(screen.getAllByRole("listitem")).toHaveLength(30);
    });
  });
});
