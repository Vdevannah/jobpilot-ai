import Notice from "./Notice";
import "./RequirementComparisonPanel.css";

// Renders the Phase 9B deterministic comparison of a job's extracted
// requirements against ONE FIXED FICTIONAL candidate fixture. This is a
// demonstration of the comparison engine, never a personalized match
// against the user's own resume -- the persistent banner below is never
// hidden or made conditional on anything in the response.

const STATUS_LABELS = {
  supported: "Supported",
  partially_supported: "Partially supported",
  not_demonstrated: "Not demonstrated",
  requires_review: "Requires review",
};

function MatchCard({ match }) {
  const statusClass = match.status.replace(/_/g, "-");
  return (
    <li className="requirement-comparison-panel__match">
      <div className="requirement-comparison-panel__match-header">
        <span className="requirement-comparison-panel__requirement">
          {match.requirement_description}
        </span>
        <span
          className={`requirement-comparison-panel__chip requirement-comparison-panel__chip--${
            match.is_required ? "required" : "preferred"
          }`}
        >
          {match.is_required ? "Required" : "Preferred"}
        </span>
        <span
          className={`requirement-comparison-panel__status requirement-comparison-panel__status--${statusClass}`}
        >
          {STATUS_LABELS[match.status] ?? match.status}
        </span>
      </div>

      <p className="requirement-comparison-panel__explanation">{match.explanation}</p>

      {match.candidate_evidence.length > 0 && (
        <details className="requirement-comparison-panel__evidence">
          <summary>Candidate evidence ({match.candidate_evidence.length})</summary>
          <ul>
            {match.candidate_evidence.map((item, index) => (
              <li key={index}>
                <span className="requirement-comparison-panel__evidence-category">
                  {item.source_category.replace(/_/g, " ")}
                </span>
                {" -- "}
                {item.claim}
                {item.professional_experience_years != null
                  ? ` (${item.professional_experience_years}y)`
                  : ""}
              </li>
            ))}
          </ul>
        </details>
      )}

      {match.limitations.length > 0 && (
        <ul className="requirement-comparison-panel__limitations">
          {match.limitations.map((limitation, index) => (
            <li key={index}>{limitation}</li>
          ))}
        </ul>
      )}
    </li>
  );
}

function MatchSection({ title, matches }) {
  if (!matches || matches.length === 0) return null;
  return (
    <section className="requirement-comparison-panel__section">
      <h4>{title}</h4>
      <ul className="requirement-comparison-panel__match-list">
        {matches.map((match, index) => (
          <MatchCard key={index} match={match} />
        ))}
      </ul>
    </section>
  );
}

function ExperienceSection({ matches, unresolvedGroups }) {
  if (!matches || matches.length === 0) return null;

  const groups = new Map();
  const standalone = [];
  for (const match of matches) {
    if (match.alternative_group != null) {
      const bucket = groups.get(match.alternative_group) ?? [];
      bucket.push(match);
      groups.set(match.alternative_group, bucket);
    } else {
      standalone.push(match);
    }
  }

  return (
    <section className="requirement-comparison-panel__section">
      <h4>Experience</h4>
      {unresolvedGroups.length > 0 && (
        <Notice tone="warning">
          No single alternative fully satisfies the experience requirement below (group
          {unresolvedGroups.length > 1 ? "s" : ""} {unresolvedGroups.join(", ")}). Human review
          is required to determine whether any other evidence resolves this.
        </Notice>
      )}
      <ul className="requirement-comparison-panel__match-list">
        {standalone.map((match, index) => (
          <MatchCard key={`standalone-${index}`} match={match} />
        ))}
        {[...groups.entries()].map(([groupId, groupMatches]) => (
          <li key={`group-${groupId}`} className="requirement-comparison-panel__alternative-group">
            <p className="requirement-comparison-panel__alternative-label">
              Alternative requirement -- any one fully qualifying is enough
            </p>
            <ul className="requirement-comparison-panel__match-list">
              {groupMatches.map((match, index) => (
                <MatchCard key={`${groupId}-${index}`} match={match} />
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function RequirementComparisonPanel({ comparison }) {
  if (!comparison) return null;
  const result = comparison.requirement_comparison;

  const skillMatches = result.matches.filter((match) => match.requirement_kind === "skill");
  const educationMatches = result.matches.filter((match) => match.requirement_kind === "education");
  const domainMatches = result.matches.filter((match) => match.requirement_kind === "domain_expertise");
  const experienceMatches = result.matches.filter((match) => match.requirement_kind === "experience");

  return (
    <div className="requirement-comparison-panel">
      <div className="requirement-comparison-panel__demo-banner">
        DEMO COMPARISON -- This analysis uses a fictional candidate, not your resume.
      </div>

      <p className="requirement-comparison-panel__candidate-label">
        Fictional candidate: {comparison.candidate_label}
      </p>

      {comparison.limitations?.map((limitation, index) => (
        <Notice key={index} tone="warning">
          {limitation}
        </Notice>
      ))}

      {result.matches.length === 0 ? (
        <p className="requirement-comparison-panel__empty">
          No job requirements were available to compare against -- a meaningful comparison cannot
          be performed without extracted job requirements. Human review is still required.
        </p>
      ) : (
        <>
          <MatchSection title="Skills" matches={skillMatches} />
          <ExperienceSection
            matches={experienceMatches}
            unresolvedGroups={result.unresolved_alternative_groups}
          />
          <MatchSection title="Education" matches={educationMatches} />
          <MatchSection title="Domain expertise" matches={domainMatches} />
        </>
      )}

      {result.overall_limitations.length > 0 && (
        <div className="requirement-comparison-panel__field">
          <p className="requirement-comparison-panel__field-label">Limitations</p>
          <ul className="requirement-comparison-panel__plain-list">
            {result.overall_limitations.map((limitation, index) => (
              <li key={index}>{limitation}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
