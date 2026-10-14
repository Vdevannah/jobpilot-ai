import { describe, expect, it } from "vitest";
import { buildSourceLookup, withSourceFromJobs } from "./jobSourceLookup";

const JOBS = [
  { id: 1, source: "greenhouse" },
  { id: 2, source: "lever" },
  { id: 3, source: "greenhouse" },
];

describe("buildSourceLookup", () => {
  it("maps job id to source", () => {
    const lookup = buildSourceLookup(JOBS);
    expect(lookup.get("1")).toBe("greenhouse");
    expect(lookup.get("2")).toBe("lever");
  });

  it("skips jobs with no id or no source", () => {
    const lookup = buildSourceLookup([{ id: 1, source: "" }, { id: null, source: "lever" }, {}]);
    expect(lookup.size).toBe(0);
  });

  it("returns an empty map for an empty or missing job list", () => {
    expect(buildSourceLookup([]).size).toBe(0);
    expect(buildSourceLookup(undefined).size).toBe(0);
  });
});

describe("withSourceFromJobs", () => {
  it("joins by job_id, not by array position", () => {
    // Deliberately out-of-order relative to JOBS, so a position-based join
    // (rows[i] <-> jobs[i]) would produce wrong results here.
    const matches = [
      { job_id: 3, title: "C" },
      { job_id: 1, title: "A" },
      { job_id: 2, title: "B" },
    ];
    const result = withSourceFromJobs(matches, JOBS);
    expect(result.find((m) => m.job_id === 3).source).toBe("greenhouse");
    expect(result.find((m) => m.job_id === 1).source).toBe("greenhouse");
    expect(result.find((m) => m.job_id === 2).source).toBe("lever");
  });

  it("never joins by title, even if a title happens to collide", () => {
    const matches = [{ job_id: 999, title: "greenhouse" }];
    const result = withSourceFromJobs(matches, JOBS);
    expect(result[0].source).toBeNull();
  });

  it("does not overwrite a source the row already has", () => {
    const matches = [{ job_id: 1, source: "already-set" }];
    const result = withSourceFromJobs(matches, JOBS);
    expect(result[0].source).toBe("already-set");
  });

  it("falls back to null, not a guess, when no corresponding job exists", () => {
    const matches = [{ job_id: 404 }];
    const result = withSourceFromJobs(matches, JOBS);
    expect(result[0].source).toBeNull();
  });

  it("joins correctly at the boundaries of a large, non-sequential id range (pagination-like gaps)", () => {
    const sparseJobs = [{ id: 1, source: "greenhouse" }, { id: 50, source: "lever" }, { id: 999, source: "greenhouse" }];
    const matches = [{ job_id: 999 }, { job_id: 2 }, { job_id: 50 }, { job_id: 1 }];
    const result = withSourceFromJobs(matches, sparseJobs);
    expect(result.find((m) => m.job_id === 999).source).toBe("greenhouse");
    expect(result.find((m) => m.job_id === 50).source).toBe("lever");
    expect(result.find((m) => m.job_id === 1).source).toBe("greenhouse");
    expect(result.find((m) => m.job_id === 2).source).toBeNull();
  });

  it("handles an empty rows array", () => {
    expect(withSourceFromJobs([], JOBS)).toEqual([]);
  });

  it("handles an empty or not-yet-loaded jobs list by falling back to null for every row", () => {
    const matches = [{ job_id: 1 }, { job_id: 2 }];
    expect(withSourceFromJobs(matches, [])).toEqual([{ job_id: 1, source: null }, { job_id: 2, source: null }]);
    expect(withSourceFromJobs(matches, undefined)).toEqual([{ job_id: 1, source: null }, { job_id: 2, source: null }]);
  });
});
