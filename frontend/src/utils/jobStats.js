// Pure, dependency-free grouping helpers for the Dashboard's KPI cards and
// charts. Every count here is derived from the actual jobs array the
// backend returned -- nothing is estimated, assumed, or invented.

function normalizeKey(value) {
  if (value == null) return "";
  return value.trim().replace(/\s+/g, " ");
}

// Groups by the normalized key, but keeps the most common original casing
// for display (so "new york, ny" and "New York, NY" collapse into one
// bucket without losing readable capitalization).
export function countBy(items, keyFn) {
  const counts = new Map();
  const displayVariants = new Map();

  for (const item of items) {
    const raw = normalizeKey(keyFn(item));
    const groupKey = raw.toLowerCase();
    const label = raw === "" ? "Unknown" : raw;

    counts.set(groupKey, (counts.get(groupKey) ?? 0) + 1);

    const variants = displayVariants.get(groupKey) ?? new Map();
    variants.set(label, (variants.get(label) ?? 0) + 1);
    displayVariants.set(groupKey, variants);
  }

  return [...counts.entries()]
    .map(([groupKey, count]) => {
      const variants = displayVariants.get(groupKey);
      const label = [...variants.entries()].sort((a, b) => b[1] - a[1])[0][0];
      return { key: label, count };
    })
    .sort((a, b) => b.count - a.count || a.key.localeCompare(b.key));
}

export function countDistinct(items, keyFn) {
  return new Set(items.map((item) => normalizeKey(keyFn(item)).toLowerCase()).filter((key) => key !== "")).size;
}

// Collapses anything past the first `limit` groups into a single "Other"
// bucket, so a long tail of one-off values never turns into unreadable
// chart segments.
export function topNWithOther(groups, limit) {
  if (groups.length <= limit) return groups;
  const top = groups.slice(0, limit);
  const otherCount = groups.slice(limit).reduce((sum, group) => sum + group.count, 0);
  return [...top, { key: "Other", count: otherCount }];
}

export function withPercentages(groups) {
  const total = groups.reduce((sum, group) => sum + group.count, 0);
  return groups.map((group) => ({
    ...group,
    percentage: total === 0 ? 0 : (group.count / total) * 100,
  }));
}
