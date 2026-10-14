import { colorForGroup } from "../utils/chartColors";
import "./DonutChart.css";

const SIZE = 168;
const CENTER = SIZE / 2;
const RADIUS = 62;
const STROKE = 28;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const GAP_DEGREES = 2;

// Hand-rolled donut (SVG circle segments via stroke-dasharray + rotation) --
// no charting library is installed and six-or-fewer segments doesn't
// warrant adding one. Percentages are always shown as text in the legend,
// which also serves as the chart's accessible table-equivalent, since a
// donut's angles alone aren't reliably readable.
export default function DonutChart({ data, total, unitLabel = "jobs" }) {
  if (data.length === 0 || total === 0) {
    return <p className="donut-chart__empty">No data available yet.</p>;
  }

  const segments = data.reduce((acc, group, index) => {
    const cumulativeDegrees = index === 0 ? -90 : acc[index - 1].cumulativeDegrees;
    const fraction = group.count / total;
    const fullDegrees = fraction * 360;
    const gap = data.length > 1 ? Math.min(GAP_DEGREES, fullDegrees / 2) : 0;
    const drawnDegrees = Math.max(fullDegrees - gap, 0);
    const dash = (drawnDegrees / 360) * CIRCUMFERENCE;
    acc.push({
      ...group,
      percentage: fraction * 100,
      color: colorForGroup(group, index),
      dash,
      rotation: cumulativeDegrees + gap / 2,
      cumulativeDegrees: cumulativeDegrees + fullDegrees,
    });
    return acc;
  }, []);

  return (
    <div className="donut-chart">
      <svg
        className="donut-chart__plot"
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="img"
        aria-label={`Donut chart: ${data
          .map((g) => `${g.key} ${g.count} ${unitLabel} (${((g.count / total) * 100).toFixed(0)}%)`)
          .join(", ")}`}
      >
        {segments.map((segment) => (
          <circle
            key={segment.key}
            cx={CENTER}
            cy={CENTER}
            r={RADIUS}
            fill="none"
            stroke={segment.color}
            strokeWidth={STROKE}
            strokeDasharray={`${segment.dash} ${CIRCUMFERENCE - segment.dash}`}
            transform={`rotate(${segment.rotation} ${CENTER} ${CENTER})`}
          />
        ))}
        <text x={CENTER} y={CENTER - 5} textAnchor="middle" className="donut-chart__total-value">
          {total}
        </text>
        <text x={CENTER} y={CENTER + 16} textAnchor="middle" className="donut-chart__total-label">
          {unitLabel}
        </text>
      </svg>

      <ul className="donut-chart__legend">
        {segments.map((segment) => (
          <li key={segment.key} className="donut-chart__legend-row">
            <span className="donut-chart__swatch" style={{ background: segment.color }} aria-hidden="true" />
            <span className="donut-chart__legend-label">{segment.key}</span>
            <span className="donut-chart__legend-value">
              {segment.count} &middot; {segment.percentage.toFixed(0)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
