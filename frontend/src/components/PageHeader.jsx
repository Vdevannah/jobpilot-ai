import "./PageHeader.css";

// A simple, consistent in-page heading (navy title + muted subtitle) shared
// by Discover Jobs, Job Matches, and Job Details -- deliberately plainer
// than the Dashboard's own DashboardHero banner, which is specific to the
// Dashboard and isn't reused here.
export default function PageHeader({ title, subtitle, children }) {
  return (
    <header className="page-header">
      <div className="page-header__text">
        <h2 className="page-header__title">{title}</h2>
        {subtitle ? <p className="page-header__subtitle">{subtitle}</p> : null}
      </div>
      {children}
    </header>
  );
}
