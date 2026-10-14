import "./ChartCard.css";

export default function ChartCard({ title, caption, children }) {
  return (
    <section className="chart-card">
      <h3 className="chart-card__title">{title}</h3>
      {caption ? <p className="chart-card__caption">{caption}</p> : null}
      {children}
    </section>
  );
}
