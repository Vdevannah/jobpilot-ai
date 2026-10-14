import { Link } from "react-router-dom";
import { SearchIcon, StarIcon, InsightsIcon, ArrowRightIcon } from "./icons";
import "./DashboardHero.css";

const WORKFLOW_STEPS = [
  { label: "Discover", description: "Collect postings from company career pages.", Icon: SearchIcon },
  { label: "Match", description: "Score each job deterministically against your profile.", Icon: StarIcon },
  { label: "Review", description: "Read mock AI insights, then decide yourself.", Icon: InsightsIcon },
];

export default function DashboardHero() {
  return (
    <section className="dashboard-hero" aria-labelledby="dashboard-hero-title">
      <div className="dashboard-hero__intro">
        <span className="dashboard-hero__brand">JobPilot AI</span>
        <h2 id="dashboard-hero-title" className="dashboard-hero__title">
          Find Your Next Opportunity
        </h2>
        <p className="dashboard-hero__subtitle">
          Discover, compare, and analyze job opportunities with JobPilot AI.
        </p>
        <Link to="/discover" className="dashboard-hero__cta">
          Discover Jobs
          <ArrowRightIcon className="dashboard-hero__cta-icon" />
        </Link>
      </div>

      <ol className="dashboard-hero__steps">
        {WORKFLOW_STEPS.map(({ label, description, Icon }, index) => (
          <li key={label} className="dashboard-hero__step">
            <div className="dashboard-hero__step-icon">
              <Icon />
            </div>
            <div className="dashboard-hero__step-text">
              <p className="dashboard-hero__step-label">{label}</p>
              <p className="dashboard-hero__step-description">{description}</p>
            </div>
            {index < WORKFLOW_STEPS.length - 1 && (
              <ArrowRightIcon className="dashboard-hero__step-arrow" />
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
