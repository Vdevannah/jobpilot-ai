import { colorForGroup } from "../utils/chartColors";
import "./BarChart.css";

// Simple inline-SVG-free bar chart (plain divs) -- no charting library is
// installed and this dataset is small enough that a dependency isn't
// warranted. Each bar is directly labeled with its category and count, so
// identity never depends on color alone.
export default function BarChart({ data, unitLabel = "jobs" }) {
  if (data.length === 0) {
    return <p className="bar-chart__empty">No data available yet.</p>;
  }

  const max = Math.max(...data.map((group) => group.count));

  return (
    <div
      className="bar-chart"
      role="img"
      aria-label={`Bar chart: ${data.map((g) => `${g.key} ${g.count} ${unitLabel}`).join(", ")}`}
    >
      <div className="bar-chart__plot">
        {data.map((group, index) => {
          const heightPercent = max === 0 ? 0 : Math.max((group.count / max) * 100, 6);
          return (
            <div className="bar-chart__column" key={group.key}>
              <span className="bar-chart__value">{group.count}</span>
              <div
                className="bar-chart__bar"
                style={{ height: `${heightPercent}%`, background: colorForGroup(group, index) }}
              />
              <span className="bar-chart__label">{group.key}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
