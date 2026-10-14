import { hasNoDetectedRequirements } from "../utils/matchInfo";
import Notice from "./Notice";
import "./SkillSummary.css";

// Distinguishes "no skills were ever required" (nothing to compare) from a
// true gap (candidate matched none of the required skills) and from a full
// match (nothing missing) -- "None detected" alone is ambiguous between
// these very different situations.
export default function SkillSummary({ matchedSkills, missingSkills }) {
  if (hasNoDetectedRequirements({ matched_skills: matchedSkills, missing_skills: missingSkills })) {
    return (
      <Notice tone="warning">
        No skills were detected in this job's description, so skill matching
        could not be evaluated and the match score above is based on
        limited job information. This does not mean the candidate lacks
        relevant skills -- the posting simply had little to analyze.
      </Notice>
    );
  }

  return (
    <div className="skill-summary">
      <div>
        <p className="skill-summary__label">Matched skills</p>
        <p className="skill-summary__value">
          {matchedSkills.length > 0
            ? matchedSkills.join(", ")
            : "None of the candidate's skills matched this job's detected requirements."}
        </p>
      </div>
      <div>
        <p className="skill-summary__label">Missing skills</p>
        <p className="skill-summary__value">
          {missingSkills.length > 0 ? missingSkills.join(", ") : "All detected required skills are matched."}
        </p>
      </div>
    </div>
  );
}
