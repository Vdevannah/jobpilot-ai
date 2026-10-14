import { describe, expect, it } from "vitest";
import { shouldShowPostingLink } from "./postingLink";

describe("shouldShowPostingLink", () => {
  it("hides the link for demo-seeded placeholder records", () => {
    expect(shouldShowPostingLink({ url: "https://example.com/jobs/1" })).toBe(false);
    expect(shouldShowPostingLink({ url: "https://www.example.com/jobs/2" })).toBe(false);
  });

  it("shows the link for a genuine job with a valid http(s) URL", () => {
    expect(shouldShowPostingLink({ url: "https://careers.airbnb.com/positions/1" })).toBe(true);
    expect(shouldShowPostingLink({ url: "http://careers.acme-corp.com/1" })).toBe(true);
  });

  it("does not treat a nonempty string alone as sufficient", () => {
    expect(shouldShowPostingLink({ url: "not a url" })).toBe(false);
    expect(shouldShowPostingLink({ url: "javascript:alert(1)" })).toBe(false);
    expect(shouldShowPostingLink({ url: "   " })).toBe(false);
  });

  it("handles a missing or empty url without throwing", () => {
    expect(shouldShowPostingLink({})).toBe(false);
    expect(shouldShowPostingLink({ url: "" })).toBe(false);
    expect(shouldShowPostingLink({ url: null })).toBe(false);
  });

  it("never flags a job as hidden based on company name alone", () => {
    expect(
      shouldShowPostingLink({ company: "Acme", url: "https://careers.acme-corp.com/42" }),
    ).toBe(true);
  });
});
