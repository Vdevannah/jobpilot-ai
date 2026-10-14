import "./FilterField.css";

export default function FilterField({ label, htmlFor, children }) {
  return (
    <div className="filter-field">
      <label htmlFor={htmlFor} className="filter-field__label">
        {label}
      </label>
      {children}
    </div>
  );
}
