import { describe, expect, it } from "vitest";
import { isDemoRecord } from "./demoRecord";

describe("isDemoRecord", () => {
  it("flags jobs whose URL points at the example.com placeholder domain", () => {
    expect(isDemoRecord({ url: "https://example.com/jobs/1" })).toBe(true);
    expect(isDemoRecord({ url: "https://www.example.com/jobs/2" })).toBe(true);
  });

  it("never flags a job based on its company name alone", () => {
    expect(isDemoRecord({ company: "Acme", url: "https://careers.acme-corp.com/42" })).toBe(false);
    expect(isDemoRecord({ company: "Test Company", url: "https://jobs.lever.co/testco/1" })).toBe(false);
  });

  it("does not flag genuinely collected postings", () => {
    expect(isDemoRecord({ company: "Airbnb", url: "https://careers.airbnb.com/positions/1?gh_jid=1" })).toBe(false);
  });

  it("handles a missing or malformed URL without throwing", () => {
    expect(isDemoRecord({})).toBe(false);
    expect(isDemoRecord({ url: "not-a-url" })).toBe(false);
  });
});
