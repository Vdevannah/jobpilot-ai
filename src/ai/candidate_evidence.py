"""Typed, evidence-based candidate qualification models.

CandidateEvidence is intentionally separate from both CandidateProfile
(src/profile.py, the flat dataclass that still drives src.matching.match_job
unchanged) and ResumeAnalysis (src/ai/schemas.py, the Phase 7 mock/OpenAI
resume-workflow model). Neither of those models distinguishes *how* a claim
was demonstrated -- CandidateProfile is a single hand-curated skills list
plus one float per track, and ResumeAnalysis's `professional_experience_years`
has no accompanying provenance. CandidateEvidence exists so that distinction
(professional employment vs. training vs. a portfolio project vs. a degree)
is structural, not a convention a human has to remember to apply.

The one rule this module enforces by construction: only `professional_experience`
evidence may carry `professional_experience_years`, `employment_period`, or
`professional_skills`. Training/course dates and project dates are never a
stand-in for employment duration, so they are never even representable on a
non-professional item -- a caller cannot "accidentally" let a bootcamp date
range be read as job tenure, or a project's tech stack be read as a skill
used on the job.

`professional_skills` (Phase 9B.3) is an explicit, caller-asserted list of
skills actually used *during* a specific role -- it is never derived from
the role's own `claim`/title text (a "Data Engineer" claim does not imply
"Python" was used; the matcher in requirement_matcher.py never tokenizes
`claim` to guess skills) and it is never derived from any other evidence
item.

`professional_skill_years` (Phase 9B.3a) is an explicit, optional mapping
of a subset of `professional_skills` to how long *that specific skill* was
used during the role. A skill present in `professional_skills` but absent
from this mapping has an unknown duration -- it is never assumed to equal
the role's own `professional_experience_years` ("the role lasted 6 years"
does not mean "Python was used for 6 years"), and requirement_matcher.py
treats that as `requires_review` rather than guessing a number. The
validator below also rejects a `professional_skill_years` entry for a
skill not present in `professional_skills`, and rejects a stated skill
duration that is negative, non-finite, or exceeds the role's own
`professional_experience_years` (when that is itself known).
"""

from __future__ import annotations

from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

SourceCategory = Literal[
    "professional_experience",
    "technical_training",
    "portfolio_project",
    "education",
    "technical_skill",
    "domain_expertise",
    "unverified",
]

CareerTrack = Literal["pharma", "data", "scientific_ai"]

VerificationStatus = Literal["self_reported", "unverified"]


class EmploymentPeriod(BaseModel):
    """A professional_experience item's own stated dates -- used only to
    detect overlap between multiple roles in the same track, never to
    compute a duration by itself (the item's own `professional_experience_years`
    is always the stated duration; this is not derived from the period).
    """

    model_config = ConfigDict(strict=True)

    start_year: float
    end_year: float | None = None  # None means "ongoing/current"


class CandidateEvidenceItem(BaseModel):
    """One qualification claim, its source category, and whatever the
    candidate (or, for these fixtures, the fictional scenario) actually
    documented -- never more than that.
    """

    model_config = ConfigDict(strict=True)

    claim: str
    source_category: SourceCategory
    career_track: CareerTrack | None = None
    detail: str | None = None
    professional_experience_years: float | None = None
    employment_period: EmploymentPeriod | None = None
    professional_skills: list[str] | None = None
    professional_skill_years: dict[str, float] | None = None
    verification_status: VerificationStatus = "self_reported"

    @model_validator(mode="after")
    def _employment_fields_require_professional_experience(self) -> "CandidateEvidenceItem":
        if self.source_category != "professional_experience":
            if self.professional_experience_years is not None:
                raise ValueError(
                    f"{self.source_category!r} evidence cannot carry "
                    "professional_experience_years -- only professional_experience "
                    "items may claim employment duration; training/project/course "
                    "dates are never a substitute for employment years."
                )
            if self.employment_period is not None:
                raise ValueError(
                    f"{self.source_category!r} evidence cannot carry an "
                    "employment_period -- only professional_experience items "
                    "track employment dates."
                )
            if self.professional_skills:
                raise ValueError(
                    f"{self.source_category!r} evidence cannot carry "
                    "professional_skills -- only a professional_experience item can "
                    "assert a skill was used on the job; training/project evidence "
                    "already has its own `claim` for that purpose."
                )
            if self.professional_skill_years:
                raise ValueError(
                    f"{self.source_category!r} evidence cannot carry "
                    "professional_skill_years -- only a professional_experience item "
                    "can assert how long a skill was used on the job."
                )
            return self

        if self.professional_skill_years:
            allowed_skills = {skill.casefold() for skill in (self.professional_skills or ())}
            for skill, years in self.professional_skill_years.items():
                if skill.casefold() not in allowed_skills:
                    raise ValueError(
                        f"professional_skill_years key {skill!r} must also appear in "
                        "professional_skills -- a skill-specific duration cannot be stated "
                        "for a skill the role never claims to have used."
                    )
                if not isfinite(years) or years < 0:
                    raise ValueError(
                        f"professional_skill_years[{skill!r}] must be a finite, nonnegative number."
                    )
                if self.professional_experience_years is not None and years > self.professional_experience_years:
                    raise ValueError(
                        f"professional_skill_years[{skill!r}]={years!r} cannot exceed this role's "
                        f"own professional_experience_years ({self.professional_experience_years!r})."
                    )
        return self


class CandidateEvidence(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[CandidateEvidenceItem]
