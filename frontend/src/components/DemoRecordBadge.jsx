import "./DemoRecordBadge.css";

// Presentation-only label for seeded demo/sample job records (identified by
// utils/demoRecord.js, never by company name alone). Does not affect the
// underlying record, its source label, or its posting link.
export default function DemoRecordBadge() {
  return <span className="demo-record-badge">Demo record</span>;
}
