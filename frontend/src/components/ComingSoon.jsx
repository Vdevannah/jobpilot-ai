import "./ComingSoon.css";

export default function ComingSoon({ title, description }) {
  return (
    <div className="coming-soon">
      <span className="coming-soon__badge">Coming soon</span>
      <h2 className="coming-soon__title">{title}</h2>
      <p className="coming-soon__description">{description}</p>
    </div>
  );
}
