import { describe, expect, it } from "vitest";
import { parseDescription } from "./parseDescription";

describe("parseDescription", () => {
  it("returns a single paragraph for a flat, unbroken string (today's real stored data)", () => {
    const text = "Airbnb was born in 2007 when two hosts welcomed three guests to their home.";
    expect(parseDescription(text)).toEqual([{ type: "paragraph", lines: [text] }]);
  });

  it("splits blank-line-separated blocks into separate paragraphs", () => {
    const text = "First paragraph.\n\nSecond paragraph.";
    expect(parseDescription(text)).toEqual([
      { type: "paragraph", lines: ["First paragraph."] },
      { type: "paragraph", lines: ["Second paragraph."] },
    ]);
  });

  it("preserves single newlines within a paragraph as separate lines", () => {
    const text = "Line one.\nLine two.";
    expect(parseDescription(text)).toEqual([{ type: "paragraph", lines: ["Line one.", "Line two."] }]);
  });

  it("recognizes a block as a bullet list only when every line starts with a bullet marker", () => {
    const text = "- First item\n- Second item\n- Third item";
    expect(parseDescription(text)).toEqual([
      { type: "list", items: ["First item", "Second item", "Third item"] },
    ]);
  });

  it("does not treat a single bulleted line, or a mixed block, as a list", () => {
    expect(parseDescription("- Only one bullet")).toEqual([
      { type: "paragraph", lines: ["- Only one bullet"] },
    ]);
    expect(parseDescription("Intro line\n- A bullet")).toEqual([
      { type: "paragraph", lines: ["Intro line", "- A bullet"] },
    ]);
  });

  it("never fabricates a heading or list from a plain sentence", () => {
    const text = "Responsibilities include many things and qualifications are listed below in prose.";
    const result = parseDescription(text);
    expect(result).toHaveLength(1);
    expect(result[0].type).toBe("paragraph");
    expect(result[0].lines[0]).toBe(text);
  });

  it("handles missing or empty descriptions", () => {
    expect(parseDescription("")).toEqual([]);
    expect(parseDescription("   ")).toEqual([]);
    expect(parseDescription(null)).toEqual([]);
    expect(parseDescription(undefined)).toEqual([]);
  });

  it("preserves literal HTML-like text as plain text segments rather than parsing it", () => {
    const text = "<b>Bold</b> claim with a <script>alert(1)</script> tag inside.";
    expect(parseDescription(text)).toEqual([{ type: "paragraph", lines: [text] }]);
  });

  it("keeps a very long unbroken description complete, not truncated", () => {
    const text = "word ".repeat(2000).trim();
    const result = parseDescription(text);
    expect(result[0].lines[0]).toBe(text);
    expect(result[0].lines[0].length).toBe(text.length);
  });
});
