// Fixed categorical color order shared by every chart on the dashboard.
// Assigned by position, never cycled past "Other" -- a group beyond the
// fixed slots is expected to already have been folded into "Other" by
// topNWithOther() before it reaches a chart.
export const CATEGORICAL_COLORS = [
  "var(--accent)",
  "var(--accent-green)",
  "var(--accent-purple)",
  "var(--accent-orange)",
];

export const OTHER_COLOR = "var(--text-muted)";

export function colorForGroup(group, index) {
  return group.key === "Other" ? OTHER_COLOR : CATEGORICAL_COLORS[index % CATEGORICAL_COLORS.length];
}
