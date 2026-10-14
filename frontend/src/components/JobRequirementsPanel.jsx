import "./JobRequirementsPanel.css";

// Renders Phase 9A's deterministic (non-AI) requirement extraction for the
// job's own stored description. This is a distinct analysis from the
// Phase 8E mock AI workflow (fixed sample output) -- it reads the job's
// actual text via keyword/regex matching, never an LLM, and every
// substantive item below can carry a verbatim evidence quote traceable to
// that description.

function EvidenceList({ evidence }) {
  if (!evidence || evidence.length === 0) return null;
  return (
    <details className="job-requirements-panel__evidence">
      <summary>Show evidence ({evidence.length})</summary>
      <ul>
        {evidence.map((ref, index) => (
          <li key={index}>&ldquo;{ref.quote}&rdquo;</li>
        ))}
      </ul>
    </details>
  );
}

function SkillList({ title, items, evidenceMap }) {
  return (
    <div className="job-requirements-panel__field">
      <p className="job-requirements-panel__field-label">{title}</p>
      {!items || items.length === 0 ? (
        <p className="job-requirements-panel__empty">None detected.</p>
      ) : (
        <ul className="job-requirements-panel__skill-list">
          {items.map((item) => (
            <li key={item} className="job-requirements-panel__skill-item">
              <span className="job-requirements-panel__skill-name">{item}</span>
              <EvidenceList evidence={evidenceMap?.[item]} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ExperienceClause({ requirement }) {
  return (
    <li className="job-requirements-panel__experience-item">
      <span className="job-requirements-panel__experience-years">
        {requirement.minimum_years}+ years
      </span>
      {requirement.education_qualifier ? (
        <span className="job-requirements-panel__experience-qualifier">
          {" "}
          with {requirement.education_qualifier}
        </span>
      ) : null}
      <span
        className={`job-requirements-panel__chip ${
          requirement.is_required
            ? "job-requirements-panel__chip--required"
            : "job-requirements-panel__chip--preferred"
        }`}
      >
        {requirement.is_required ? "Required" : "Preferred"}
      </span>
      <EvidenceList evidence={requirement.evidence} />
    </li>
  );
}

function ExperienceSection({ experienceRequirements }) {
  if (!experienceRequirements || experienceRequirements.length === 0) {
    return (
      <p className="job-requirements-panel__empty">
        No explicit, numeric experience requirement was detected.
      </p>
    );
  }

  const groups = new Map();
  const standalone = [];
  for (const requirement of experienceRequirements) {
    if (requirement.alternative_group != null) {
      const bucket = groups.get(requirement.alternative_group) ?? [];
      bucket.push(requirement);
      groups.set(requirement.alternative_group, bucket);
    } else {
      standalone.push(requirement);
    }
  }

  return (
    <ul className="job-requirements-panel__experience-list">
      {standalone.map((requirement, index) => (
        <ExperienceClause key={`standalone-${index}`} requirement={requirement} />
      ))}
      {[...groups.entries()].map(([groupId, requirements]) => (
        <li key={`group-${groupId}`} className="job-requirements-panel__alternative-group">
          <p className="job-requirements-panel__alternative-label">
            Alternative requirement -- any one of these qualifies
          </p>
          <ul className="job-requirements-panel__experience-list">
            {requirements.map((requirement, index) => (
              <ExperienceClause key={`${groupId}-${index}`} requirement={requirement} />
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}

function NoteList({ title, items }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="job-requirements-panel__field">
      <p className="job-requirements-panel__field-label">{title}</p>
      <ul className="job-requirements-panel__plain-list">
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default function JobRequirementsPanel({ requirements }) {
  if (!requirements) return null;

  const hasAnyRequirement =
    requirements.required_skills.length > 0 ||
    requirements.preferred_skills.length > 0 ||
    requirements.experience_requirements.length > 0 ||
    requirements.required_education.length > 0 ||
    requirements.preferred_education.length > 0;

  return (
    <div className="job-requirements-panel">
      <div className="job-requirements-panel__meta" role="status">
        <span className="job-requirements-panel__badge job-requirements-panel__badge--deterministic">
          Deterministic extraction
        </span>
        {requirements.requires_human_review ? (
          <span className="job-requirements-panel__badge job-requirements-panel__badge--review">
            Requires human review
          </span>
        ) : null}
      </div>
      <p className="job-requirements-panel__disclaimer">
        Extracted directly from this job&rsquo;s own stored description using deterministic
        keyword/regex matching -- not a language model, and not the fixed mock analysis shown
        elsewhere in this dashboard. It may miss requirements phrased in unexpected ways.
      </p>

      {!hasAnyRequirement && (
        <p className="job-requirements-panel__empty">
          No structured requirements could be extracted from this job&rsquo;s description.
        </p>
      )}

      <div className="job-requirements-panel__grid">
        <SkillList
          title="Required skills"
          items={requirements.required_skills}
          evidenceMap={requirements.required_skills_evidence}
        />
        <SkillList
          title="Preferred skills"
          items={requirements.preferred_skills}
          evidenceMap={requirements.preferred_skills_evidence}
        />
      </div>

      <div className="job-requirements-panel__field">
        <p className="job-requirements-panel__field-label">Experience requirements</p>
        <ExperienceSection experienceRequirements={requirements.experience_requirements} />
      </div>

      <div className="job-requirements-panel__grid">
        <SkillList
          title="Required education"
          items={requirements.required_education}
          evidenceMap={requirements.required_education_evidence}
        />
        <SkillList
          title="Preferred education"
          items={requirements.preferred_education}
          evidenceMap={requirements.preferred_education_evidence}
        />
      </div>

      <div className="job-requirements-panel__field">
        <p className="job-requirements-panel__field-label">Responsibilities</p>
        {requirements.responsibilities.length > 0 ? (
          <ul className="job-requirements-panel__plain-list">
            {requirements.responsibilities.map((item, index) => (
              <li key={index}>
                {item}
                <EvidenceList evidence={requirements.responsibilities_evidence?.[item]} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="job-requirements-panel__empty">
            No clearly labeled responsibilities section was identified.
          </p>
        )}
      </div>

      <SkillList
        title="Domain expertise"
        items={requirements.domain_expertise}
        evidenceMap={requirements.domain_expertise_evidence}
      />

      {requirements.location_requirement && (
        <div className="job-requirements-panel__field">
          <p className="job-requirements-panel__field-label">Location / remote</p>
          <p className="job-requirements-panel__location">{requirements.location_requirement}</p>
          <EvidenceList evidence={requirements.location_evidence} />
        </div>
      )}

      <NoteList title="Missing information" items={requirements.missing_information} />
      <NoteList title="Ambiguous information" items={requirements.ambiguous_information} />
    </div>
  );
}
