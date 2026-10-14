import { describe, expect, it } from "vitest";
import { countBy, countDistinct, topNWithOther, withPercentages } from "./jobStats";

describe("countBy", () => {
  it("groups items by the key function and sorts by count descending", () => {
    const items = [{ source: "greenhouse" }, { source: "lever" }, { source: "greenhouse" }];
    expect(countBy(items, (i) => i.source)).toEqual([
      { key: "greenhouse", count: 2 },
      { key: "lever", count: 1 },
    ]);
  });

  it("normalizes whitespace and casing into one bucket, keeping the majority casing for display", () => {
    const items = [{ loc: "New York, NY" }, { loc: "new york, ny" }, { loc: "New York, NY" }];
    const result = countBy(items, (i) => i.loc);
    expect(result).toEqual([{ key: "New York, NY", count: 3 }]);
  });

  it("buckets missing or blank values as Unknown instead of dropping them", () => {
    const items = [{ loc: null }, { loc: "" }, { loc: "  " }, { loc: "Boston" }];
    const result = countBy(items, (i) => i.loc);
    expect(result.find((g) => g.key === "Unknown").count).toBe(3);
    expect(result.find((g) => g.key === "Boston").count).toBe(1);
  });

  it("returns an empty array for an empty dataset", () => {
    expect(countBy([], (i) => i.source)).toEqual([]);
  });
});

describe("countDistinct", () => {
  it("counts distinct normalized values", () => {
    expect(countDistinct([{ c: "Acme" }, { c: "acme" }, { c: "Other" }], (i) => i.c)).toBe(2);
  });

  it("is zero for an empty dataset", () => {
    expect(countDistinct([], (i) => i.c)).toBe(0);
  });
});

describe("topNWithOther", () => {
  it("passes groups through unchanged when within the limit", () => {
    const groups = [{ key: "a", count: 3 }, { key: "b", count: 1 }];
    expect(topNWithOther(groups, 5)).toEqual(groups);
  });

  it("collapses everything past the limit into a single Other bucket", () => {
    const groups = [
      { key: "a", count: 5 },
      { key: "b", count: 4 },
      { key: "c", count: 3 },
      { key: "d", count: 2 },
      { key: "e", count: 1 },
    ];
    expect(topNWithOther(groups, 3)).toEqual([
      { key: "a", count: 5 },
      { key: "b", count: 4 },
      { key: "c", count: 3 },
      { key: "Other", count: 3 },
    ]);
  });
});

describe("withPercentages", () => {
  it("computes each group's share of the total", () => {
    const groups = [{ key: "a", count: 3 }, { key: "b", count: 1 }];
    const result = withPercentages(groups);
    expect(result[0].percentage).toBeCloseTo(75);
    expect(result[1].percentage).toBeCloseTo(25);
  });

  it("returns zero percentages for an empty dataset without dividing by zero", () => {
    expect(withPercentages([])).toEqual([]);
  });
});
