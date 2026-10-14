"""Deterministic comparison of Phase 9A JobRequirements against structured
candidate evidence (CandidateEvidence). Pure, offline, regex/keyword-based --
no LLM, no network access, no database access, and no dependency on
src.matching, CandidateProfile, resume_selector.py, or critic_agent.py.
Those existing deterministic-match and mock-AI-review paths are untouched by
this module and this module is never imported by them.

Every comparison degrades honestly rather than inventing confidence:
"not_demonstrated" means the relevant evidence category was checked and
nothing matching was found -- it is never asserted as proof the candidate
lacks the qualification (the candidate may simply not have documented it in
the supplied evidence). "requires_review" is used whenever the comparison
itself is unreliable to compute deterministically (an unknown job track,
ambiguous degree equivalency, an unresolved specialized field of study,
overlapping/undated professional_experience items that cannot be safely
summed) -- it is never silently resolved by guessing.

Phase 9B.3 adds explicit professional-skill-use tracking
(CandidateEvidenceItem.professional_skills) and education field-of-study
matching. Both are read from already-present, caller-supplied text (a
role's own asserted skill list; "in <field>" phrasing already present in
Phase 9A's verbatim evidence quotes and in the candidate's own claim/detail
text) -- never guessed from a job title or inferred across unrelated items.
"""

from __future__ import annotations

import re
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.ai.candidate_evidence import CandidateEvidence, CandidateEvidenceItem, SourceCategory
from src.ai.job_requirements import EvidenceRef, ExperienceRequirement, JobRequirements

MatchStatus = Literal["supported", "partially_supported", "not_demonstrated", "requires_review"]
RequirementKind = Literal["skill", "experience", "education", "domain_expertise"]

ABSENCE_LIMITATION = (
    "No matching candidate evidence was found; this is not proof the candidate "
    "lacks the qualification, only that the supplied evidence does not document it."
)


class RequirementMatch(BaseModel):
    model_config = ConfigDict(strict=True)

    requirement_kind: RequirementKind
    requirement_description: str
    requirement_evidence: list[EvidenceRef]
    is_required: bool
    alternative_group: int | None
    candidate_evidence: list[CandidateEvidenceItem]
    evidence_source_categories: list[SourceCategory]
    status: MatchStatus
    explanation: str
    limitations: list[str]


class RequirementComparisonResult(BaseModel):
    model_config = ConfigDict(strict=True)

    job_id: int
    matches: list[RequirementMatch]
    unresolved_alternative_groups: list[int]
    overall_limitations: list[str]
    analysis_mode: Literal["deterministic"] = "deterministic"
    requires_human_review: Literal[True] = True
    status: Literal["pending_review"] = "pending_review"


# ---------------------------------------------------------------------------
# Conservative text normalization -- exact-match comparison only, after
# casefolding/whitespace/punctuation normalization and a small, explicit
# alias table. Never fuzzy, never semantic/embedding-based.
# ---------------------------------------------------------------------------

_ALIASES = {
    "ml": "machine learning",
    "nlp": "natural language processing",
    "js": "javascript",
    "sar": "sar",
    "structure activity relationship": "sar",
    "protac": "protac",
    "proteolysis targeting chimera": "protac",
}


def _normalize(text: str) -> str:
    text = re.sub(r"[^\w+#.]+", " ", text.casefold()).strip()
    return _ALIASES.get(text, text)


# ---------------------------------------------------------------------------
# Degree-level parsing. Two separate functions because the same regex
# matches mean different things depending on which side of the comparison
# is being read: a job requirement string listing multiple degrees ("BS/MS")
# states alternatives, so the *lowest* named level is the real bar; a
# candidate's own claim listing a degree states what they attained, so the
# *highest* named level found is what they hold.
# ---------------------------------------------------------------------------

_DEGREE_LEVELS = (
    (3, re.compile(r"\bph\.?\s*d\.?\b|\bdoctorate\b|\bdoctor of philosophy\b", re.I)),
    (2, re.compile(r"\bmaster'?s?(?:\s+degree)?\b|\bm\.?s\.?c?\.?\b|\bm\.?a\.?\b", re.I)),
    (1, re.compile(r"\bbachelor'?s?(?:\s+degree)?\b|\bb\.?s\.?c?\.?\b|\bb\.?a\.?\b", re.I)),
)

_DEGREE_LEVEL_NAMES = {1: "Bachelor's", 2: "Master's", 3: "PhD"}


def _found_degree_levels(text: str) -> list[int]:
    found = []
    for level, pattern in _DEGREE_LEVELS:
        if pattern.search(text):
            found.append(level)
    return found


def _required_degree_level(text: str) -> int | None:
    """The lowest level named -- satisfying any one alternative is enough."""
    found = _found_degree_levels(text)
    return min(found) if found else None


def _candidate_degree_level(text: str) -> int | None:
    """The highest level named -- the candidate's own attained degree."""
    found = _found_degree_levels(text)
    return max(found) if found else None


def _is_ambiguous_degree_text(text: str) -> bool:
    """A degree-like claim with no level this module recognizes at all --
    e.g. "JD", "MD", "MBA" -- is never silently treated as unmet; it is
    flagged for human review instead of guessing an equivalency.
    """
    degree_like = re.search(r"\bdegree\b|\bdiploma\b|\bcertificate\b", text, re.I)
    return bool(degree_like) and not _found_degree_levels(text)


# ---------------------------------------------------------------------------
# Field-of-study parsing. Conservative "in <field>" extraction applied to
# the SAME verbatim text Phase 9A/the candidate already provided -- never a
# new field invented by this module. If neither side's text contains an
# "in <field>" phrase, the field is "unspecified" and only degree level is
# compared, exactly as in 9B.2.
# ---------------------------------------------------------------------------

_FIELD_OF_STUDY = re.compile(
    r"\bin\s+([A-Za-z][A-Za-z\s/&-]{2,60}?)(?=\s*(?:degree\b|required\b|preferred\b|\(|,|\.|$))",
    re.I,
)


def _extract_field_of_study(text: str) -> str | None:
    match = _FIELD_OF_STUDY.search(text)
    if not match:
        return None
    field = match.group(1).strip()
    return field or None


def _normalize_field(text: str) -> str:
    return re.sub(r"[^\w&/-]+", " ", text.casefold()).strip()


def _job_field_of_study(evidence: list[EvidenceRef]) -> str | None:
    for ref in evidence:
        field = _extract_field_of_study(ref.quote)
        if field:
            return field
    return None


def _candidate_field_of_study(item: CandidateEvidenceItem) -> str | None:
    field = _extract_field_of_study(item.claim)
    if field:
        return field
    if item.detail:
        return _extract_field_of_study(item.detail)
    return None


# ---------------------------------------------------------------------------
# Status combination -- used when a single requirement has more than one
# condition that must *both* hold (e.g. an experience alternative's years
# AND its education_qualifier).
# ---------------------------------------------------------------------------


def _combine(a: MatchStatus, b: MatchStatus | None) -> MatchStatus:
    if b is None:
        return a
    if a == "requires_review" or b == "requires_review":
        return "requires_review"
    if a == "supported" and b == "supported":
        return "supported"
    if a == "not_demonstrated" and b == "not_demonstrated":
        return "not_demonstrated"
    return "partially_supported"


# ---------------------------------------------------------------------------
# Professional-experience aggregation -- shared by track-level experience
# comparison and skill-level professional-use comparison. Never sums
# overlapping or duplicate roles, never treats a missing duration as zero,
# and never assumes an end date for an ongoing (employment_period.end_year
# is None) role -- an open end is only ever used to detect that it *might*
# overlap a later role, never to compute how long it has lasted.
# ---------------------------------------------------------------------------


def _aggregate_values(
    items: list[CandidateEvidenceItem],
    subject: str,
    duration_of,
) -> tuple[float | None, MatchStatus | None, str | None]:
    """Returns (total, forced_status, note) for an already-filtered list of
    professional_experience items, using `duration_of(item) -> float | None`
    to read whatever duration is relevant to the caller -- the role's own
    `professional_experience_years` for track-level experience, or a single
    skill's `professional_skill_years[skill]` for skill-level professional
    use. The overlap/duplicate/missing-duration rules are identical either
    way: `forced_status` is set only when the comparison cannot be safely
    completed (requires_review); when it is None, `total` (possibly None,
    meaning no evidence at all) is the caller's signal to proceed with a
    normal years-vs-minimum comparison.
    """
    if not items:
        return None, None, None

    if len(items) == 1:
        item = items[0]
        duration = duration_of(item)
        if duration is None:
            return None, "requires_review", (
                f"A professional_experience item documenting {subject} exists but states no "
                "duration; a total cannot be computed without guessing."
            )
        return duration, None, None

    if any(item.employment_period is None for item in items):
        return None, "requires_review", (
            f"Multiple professional_experience items document {subject} but at least one has no "
            "employment_period, so overlap between roles cannot be ruled out."
        )

    spans = sorted(
        (item.employment_period.start_year,
         item.employment_period.end_year if item.employment_period.end_year is not None else float("inf"))
        for item in items
    )
    for (_, end), (next_start, _) in zip(spans, spans[1:]):
        if next_start < end:
            return None, "requires_review", (
                f"Multiple professional_experience items documenting {subject} have overlapping "
                "employment periods; summing them would double-count overlapping time, so no total "
                "is calculated automatically."
            )

    durations = [duration_of(item) for item in items]
    if any(duration is None for duration in durations):
        return None, "requires_review", (
            f"Multiple non-overlapping professional_experience items document {subject} but at "
            "least one states no duration; a total cannot be computed without guessing."
        )

    return sum(durations), None, None


def _role_duration(item: CandidateEvidenceItem) -> float | None:
    return item.professional_experience_years


def _skill_duration(skill: str):
    normalized_skill = _normalize(skill)

    def getter(item: CandidateEvidenceItem) -> float | None:
        """Only ever reads `professional_skill_years` -- a role's overall
        tenure is never substituted for a specific skill's duration, so a
        skill listed in `professional_skills` without its own entry here
        has an unknown duration, not an inherited one.
        """
        if not item.professional_skill_years:
            return None
        for key, years in item.professional_skill_years.items():
            if _normalize(key) == normalized_skill:
                return years
        return None

    return getter


def _professional_items_for_track(evidence: CandidateEvidence, track: str) -> list[CandidateEvidenceItem]:
    return [
        item for item in evidence.items
        if item.source_category == "professional_experience" and item.career_track == track
    ]


def _professional_skill_items(evidence: CandidateEvidence, skill: str) -> list[CandidateEvidenceItem]:
    """Items whose role explicitly lists this skill as used professionally.

    Deliberately not track-scoped: a skill used professionally in one track
    is still professional use of that skill, regardless of which track's
    years requirement is being evaluated elsewhere. Deliberately never
    derived from the role's own `claim`/title text -- a "Data Engineer"
    title never implies "Python" unless professional_skills says so.
    """
    normalized_skill = _normalize(skill)
    return [
        item for item in evidence.items
        if item.source_category == "professional_experience"
        and item.professional_skills
        and normalized_skill in {_normalize(s) for s in item.professional_skills}
    ]


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

_PROFESSIONAL_USE_CUE = re.compile(r"\b(\d+(?:\.\d+)?)\s*\+?\s*years?\b", re.I)

_NON_PROFESSIONAL_SKILL_CATEGORIES: tuple[SourceCategory, ...] = (
    "technical_skill", "technical_training", "portfolio_project", "domain_expertise",
)
_SKILL_SUPPORTING_CATEGORIES: tuple[SourceCategory, ...] = (
    "professional_experience", "technical_skill", "technical_training",
    "portfolio_project", "domain_expertise",
)


def _extract_required_years(evidence: list[EvidenceRef]) -> float | None:
    """Conservative heuristic: if the job posting's own evidence quote for
    this skill is phrased alongside a specific number of years, treat that
    number as the professional-use duration the posting is asking for.
    Plain substring/regex matching against the verbatim quote Phase 9A
    already captured -- never an inference beyond what the quoted text
    itself contains.
    """
    for ref in evidence:
        match = _PROFESSIONAL_USE_CUE.search(ref.quote)
        if match:
            return float(match.group(1))
    return None


def _compare_skill(
    skill: str,
    evidence: list[EvidenceRef],
    claim_items_by_claim: dict[str, list[CandidateEvidenceItem]],
    full_evidence: CandidateEvidence,
    *,
    is_required: bool,
) -> RequirementMatch:
    required_years = _extract_required_years(evidence)
    normalized_skill = _normalize(skill)
    professional_items = _professional_skill_items(full_evidence, skill)
    non_professional_hits = [
        item for item in claim_items_by_claim.get(normalized_skill, [])
        if item.source_category in _NON_PROFESSIONAL_SKILL_CATEGORIES
    ]

    limitations: list[str] = []
    if required_years is not None:
        limitations.append(
            "The job's own text ties this skill to a specific number of years, so only explicitly "
            "documented professional use (a professional_experience item's professional_skills) was "
            "accepted toward meeting that duration."
        )
        years, forced_status, note = _aggregate_values(
            professional_items, f"professional use of {skill!r}", _skill_duration(skill),
        )
        if forced_status == "requires_review":
            return RequirementMatch(
                requirement_kind="skill", requirement_description=skill, requirement_evidence=evidence,
                is_required=is_required, alternative_group=None, candidate_evidence=professional_items,
                evidence_source_categories=sorted({item.source_category for item in professional_items}),
                status="requires_review", explanation=note, limitations=[note],
            )
        if years is None:
            if non_professional_hits:
                status, explanation, used = (
                    "partially_supported",
                    f"{skill!r} is demonstrated only through training or a portfolio project, not "
                    f"documented professional use, but the job appears to require {required_years:g}+ "
                    "years of professional use.",
                    non_professional_hits,
                )
            else:
                status, explanation, used = (
                    "not_demonstrated",
                    f"No evidence of {skill!r} was found in the supplied candidate evidence.",
                    [],
                )
                limitations.append(ABSENCE_LIMITATION)
        elif years >= required_years:
            status, explanation, used = (
                "supported",
                f"Professional experience evidence documents {years:g} years of professional use of "
                f"{skill!r}, meeting the {required_years:g}-year requirement.",
                professional_items,
            )
        else:
            status, explanation, used = (
                "partially_supported",
                f"Professional experience evidence documents {years:g} years of professional use of "
                f"{skill!r}, below the {required_years:g}-year requirement.",
                professional_items,
            )
    else:
        if professional_items:
            status, explanation, used = (
                "supported",
                f"Professional experience evidence documents use of {skill!r}.",
                professional_items,
            )
        elif non_professional_hits:
            status, explanation, used = (
                "supported",
                f"{skill!r} is demonstrated by the candidate's supplied evidence.",
                non_professional_hits,
            )
        else:
            status, explanation, used = (
                "not_demonstrated",
                f"No evidence of {skill!r} was found in the supplied candidate evidence.",
                [],
            )
            limitations.append(ABSENCE_LIMITATION)

    return RequirementMatch(
        requirement_kind="skill", requirement_description=skill, requirement_evidence=evidence,
        is_required=is_required, alternative_group=None, candidate_evidence=used,
        evidence_source_categories=sorted({item.source_category for item in used}),
        status=status, explanation=explanation, limitations=limitations,
    )


def _compare_domain_expertise(
    term: str,
    evidence: list[EvidenceRef],
    candidate_items_by_claim: dict[str, list[CandidateEvidenceItem]],
) -> RequirementMatch:
    candidates = candidate_items_by_claim.get(_normalize(term), [])
    hits = [item for item in candidates if item.source_category in _SKILL_SUPPORTING_CATEGORIES]
    if hits:
        status: MatchStatus = "supported"
        explanation = f"Domain expertise in {term!r} is demonstrated by the candidate's supplied evidence."
        limitations: list[str] = []
    else:
        status = "not_demonstrated"
        explanation = f"No evidence of domain expertise in {term!r} was found in the supplied candidate evidence."
        limitations = [ABSENCE_LIMITATION]
    return RequirementMatch(
        requirement_kind="domain_expertise",
        requirement_description=term,
        requirement_evidence=evidence,
        is_required=True,
        alternative_group=None,
        candidate_evidence=hits,
        evidence_source_categories=sorted({item.source_category for item in hits}),
        status=status,
        explanation=explanation,
        limitations=limitations,
    )


# ---------------------------------------------------------------------------
# Education -- shared degree-level + field-of-study matcher, used both for
# standalone required/preferred education entries and for an experience
# alternative's attached education_qualifier.
# ---------------------------------------------------------------------------


def _match_degree_requirement(
    label: str, job_evidence: list[EvidenceRef], candidate_items: list[CandidateEvidenceItem],
) -> tuple[MatchStatus, str, list[str], list[CandidateEvidenceItem]]:
    required_level = _required_degree_level(label)
    if required_level is None or _is_ambiguous_degree_text(label):
        return (
            "requires_review",
            f"The required degree level in {label!r} could not be determined with confidence.",
            ["Ambiguous degree equivalency is never resolved automatically."],
            [],
        )

    ambiguous_candidate_items = [item for item in candidate_items if _is_ambiguous_degree_text(item.claim)]
    if ambiguous_candidate_items:
        return (
            "requires_review",
            "The candidate's own education evidence names a degree this module cannot confidently "
            "map to a level (e.g. a professional degree other than a bachelor's/master's/PhD).",
            ["Ambiguous degree equivalency is never resolved automatically."],
            ambiguous_candidate_items,
        )

    levels = [(_candidate_degree_level(item.claim), item) for item in candidate_items]
    levels = [(level, item) for level, item in levels if level is not None]
    if not levels:
        return (
            "not_demonstrated",
            f"No education evidence meeting {label!r} was found in the supplied candidate evidence.",
            [ABSENCE_LIMITATION],
            [],
        )

    best_level, best_item = max(levels, key=lambda pair: pair[0])
    if best_level < required_level:
        return (
            "partially_supported",
            f"Candidate holds a {_DEGREE_LEVEL_NAMES[best_level]} degree, which is below the "
            f"required {_DEGREE_LEVEL_NAMES[required_level]}-level requirement.",
            [],
            [best_item],
        )

    job_field = _job_field_of_study(job_evidence)
    if job_field is None:
        return (
            "supported",
            f"Candidate holds a {_DEGREE_LEVEL_NAMES[best_level]} degree, which meets or exceeds "
            f"the required {_DEGREE_LEVEL_NAMES[required_level]}-level requirement. The job "
            "requirement text does not specify a field of study, so field-of-study is not evaluated.",
            [],
            [best_item],
        )

    candidate_field = _candidate_field_of_study(best_item)
    if candidate_field is None:
        return (
            "requires_review",
            f"The job requires a degree in {job_field!r}, but the candidate's field of study "
            "cannot be established from the supplied evidence.",
            ["A specialized field requirement is never assumed satisfied when the candidate's "
             "field of study is undocumented, regardless of degree level."],
            [best_item],
        )

    if _normalize_field(candidate_field) == _normalize_field(job_field):
        return (
            "supported",
            f"Candidate holds a {_DEGREE_LEVEL_NAMES[best_level]} degree in {candidate_field!r}, "
            f"matching the required field of {job_field!r}.",
            [],
            [best_item],
        )

    return (
        "partially_supported",
        f"Candidate holds a {_DEGREE_LEVEL_NAMES[best_level]} degree in {candidate_field!r}, which "
        f"does not match the required field of {job_field!r}, even though the degree level is "
        "sufficient.",
        ["Field-of-study equivalency is only recognized on an exact, conservative text match -- "
         "a subfield (e.g. a specific chemistry discipline) is never assumed equivalent to a "
         "broader or differently named field."],
        [best_item],
    )


def _compare_education(
    label: str,
    evidence: list[EvidenceRef],
    education_items: list[CandidateEvidenceItem],
    *,
    is_required: bool,
) -> RequirementMatch:
    status, explanation, limitations, used = _match_degree_requirement(label, evidence, education_items)
    return RequirementMatch(
        requirement_kind="education",
        requirement_description=label,
        requirement_evidence=evidence,
        is_required=is_required,
        alternative_group=None,
        candidate_evidence=used,
        evidence_source_categories=sorted({item.source_category for item in used}),
        status=status,
        explanation=explanation,
        limitations=limitations,
    )


def _compare_experience_education(
    requirement: ExperienceRequirement, education_items: list[CandidateEvidenceItem],
) -> tuple[MatchStatus | None, str | None, list[str], list[CandidateEvidenceItem]]:
    if requirement.education_qualifier is None:
        return None, None, [], []
    return _match_degree_requirement(requirement.education_qualifier, requirement.evidence, education_items)


# ---------------------------------------------------------------------------
# Experience requirements (including education-dependent alternatives)
# ---------------------------------------------------------------------------


def _compare_experience_years(
    requirement: ExperienceRequirement, evidence: CandidateEvidence, track: str,
) -> tuple[MatchStatus, str, list[str], list[CandidateEvidenceItem]]:
    if track == "unknown":
        return (
            "requires_review",
            "The job's career track is unknown, so professional experience cannot be compared "
            "to a specific track.",
            ["No track-specific professional experience comparison is possible for an unknown track."],
            [],
        )

    matching_items = _professional_items_for_track(evidence, track)
    years, forced_status, note = _aggregate_values(
        matching_items, f"{track} professional experience", _role_duration,
    )

    if forced_status == "requires_review":
        return "requires_review", note, [note], matching_items

    if years is None:
        return (
            "not_demonstrated",
            f"No professional_experience evidence for the {track} track was found.",
            [ABSENCE_LIMITATION],
            [],
        )

    if not isfinite(years) or years < 0:
        return "requires_review", "Candidate professional experience years are invalid.", [], matching_items

    minimum = requirement.minimum_years
    if years >= minimum:
        return (
            "supported",
            f"Documented {track} professional experience ({years:g} years) meets the "
            f"{minimum:g}-year requirement.",
            [],
            matching_items,
        )
    return (
        "partially_supported",
        f"Documented {track} professional experience ({years:g} years) is below the "
        f"{minimum:g}-year requirement.",
        [],
        matching_items,
    )


def _compare_experience_requirement(
    requirement: ExperienceRequirement, evidence: CandidateEvidence, track: str, education_items: list[CandidateEvidenceItem],
) -> RequirementMatch:
    years_status, years_explanation, years_limitations, years_items = _compare_experience_years(
        requirement, evidence, track,
    )
    edu_status, edu_explanation, edu_limitations, edu_items = _compare_experience_education(
        requirement, education_items,
    )

    status = _combine(years_status, edu_status)
    explanations = [years_explanation] + ([edu_explanation] if edu_explanation else [])
    limitations = years_limitations + edu_limitations
    used = years_items + edu_items

    description = f"{requirement.minimum_years:g}+ years"
    if requirement.education_qualifier:
        description += f" with {requirement.education_qualifier}"

    return RequirementMatch(
        requirement_kind="experience",
        requirement_description=description,
        requirement_evidence=requirement.evidence,
        is_required=requirement.is_required,
        alternative_group=requirement.alternative_group,
        candidate_evidence=used,
        evidence_source_categories=sorted({item.source_category for item in used}),
        status=status,
        explanation=" ".join(explanations),
        limitations=limitations,
    )


# ---------------------------------------------------------------------------
# Evidence provenance -- defense-in-depth sweep mirroring Phase 9A's
# _filter_valid_evidence(): every candidate_evidence item attached to a
# match must be one of the exact objects supplied in `evidence.items`, so a
# bug elsewhere can never let a fabricated or altered claim reach a caller.
# ---------------------------------------------------------------------------


def _filter_provenance(
    evidence: CandidateEvidence, items: list[CandidateEvidenceItem],
) -> list[CandidateEvidenceItem]:
    allowed = evidence.items
    return [item for item in items if item in allowed]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def compare_requirements(requirements: JobRequirements, evidence: CandidateEvidence) -> RequirementComparisonResult:
    """Pure comparison: never mutates `requirements` or `evidence`, never
    calls out to a network or database, and never infers an experience
    total from training/project dates (CandidateEvidenceItem structurally
    cannot carry professional_experience_years/employment_period/
    professional_skills unless its source_category is professional_experience).
    """
    candidate_items_by_claim: dict[str, list[CandidateEvidenceItem]] = {}
    for item in evidence.items:
        candidate_items_by_claim.setdefault(_normalize(item.claim), []).append(item)

    education_items = [item for item in evidence.items if item.source_category == "education"]

    matches: list[RequirementMatch] = []

    for skill in requirements.required_skills:
        matches.append(_compare_skill(
            skill, requirements.required_skills_evidence.get(skill, []),
            candidate_items_by_claim, evidence, is_required=True,
        ))
    for skill in requirements.preferred_skills:
        matches.append(_compare_skill(
            skill, requirements.preferred_skills_evidence.get(skill, []),
            candidate_items_by_claim, evidence, is_required=False,
        ))

    for label in requirements.required_education:
        matches.append(_compare_education(
            label, requirements.required_education_evidence.get(label, []),
            education_items, is_required=True,
        ))
    for label in requirements.preferred_education:
        matches.append(_compare_education(
            label, requirements.preferred_education_evidence.get(label, []),
            education_items, is_required=False,
        ))

    for term in requirements.domain_expertise:
        matches.append(_compare_domain_expertise(
            term, requirements.domain_expertise_evidence.get(term, []), candidate_items_by_claim,
        ))

    track = requirements.career_track
    experience_matches: dict[int | None, list[RequirementMatch]] = {}
    for requirement in requirements.experience_requirements:
        match = _compare_experience_requirement(requirement, evidence, track, education_items)
        matches.append(match)
        experience_matches.setdefault(requirement.alternative_group, []).append(match)

    unresolved_alternative_groups = sorted(
        group_id for group_id, group_matches in experience_matches.items()
        if group_id is not None and not any(m.status == "supported" for m in group_matches)
    )

    for match in matches:
        match.candidate_evidence = _filter_provenance(evidence, match.candidate_evidence)
        match.evidence_source_categories = sorted({item.source_category for item in match.candidate_evidence})

    overall_limitations = [
        "This comparison is deterministic text/category matching, not a hiring or suitability "
        "assessment, and does not verify the accuracy of either the job posting or the "
        "candidate evidence supplied to it.",
        "Responsibilities extracted from the job posting are not compared against candidate "
        "evidence in this phase; no candidate evidence category maps to a 'responsibility'.",
    ]
    overall_limitations.extend(
        f"Job posting limitation (carried over from extraction): {note}"
        for note in requirements.missing_information
    )
    overall_limitations.extend(
        f"Job posting ambiguity (carried over from extraction): {note}"
        for note in requirements.ambiguous_information
    )

    return RequirementComparisonResult(
        job_id=requirements.job_id,
        matches=matches,
        unresolved_alternative_groups=unresolved_alternative_groups,
        overall_limitations=overall_limitations,
    )
