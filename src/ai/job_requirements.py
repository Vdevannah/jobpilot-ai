"""Deterministic, evidence-based structured requirement extraction.

extract_job_requirements() reads only the supplied title and description --
never a live LLM, never any other job's or candidate's data -- and returns a
JobRequirements object where every substantive claim carries an EvidenceRef
that is a verified exact substring *at a specific, correct location* in the
input description (see _segment_evidence()/_sub_evidence(); nothing else is
allowed to construct an EvidenceRef). Evidence is always anchored to the
specific segment it was found in -- never a blind whole-description
`.find()` -- so a duplicated phrase appearing in both a real requirements
section and an unrelated section (benefits, company background) can never
be misattributed to the wrong occurrence.

This module is intentionally independent of src/matching.py's scoring
engine: it calls two of that module's functions exactly as already exported
(extract_skills, determine_job_track) for candidate detection, but never
imports from or writes into CandidateProfile, match_job(), or anything that
feeds deterministic match scores. It is equally independent of
src/ai/resume_selector.py and src/ai/agents/critic_agent.py -- this module
is never imported by them, and nothing here changes their behavior.

Job descriptions are public postings, not personal data, so this module
does not go through src/ai/resume_privacy.py (that gate exists for resume
text specifically). There is no LLM in this module to be "instructed" by
text embedded in a job description -- posting text is only ever treated as
plain data to run regexes and substring search against.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.ai.job_track_classifier import classify_scientific_ai
from src.matching import determine_job_track, extract_skills


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class EvidenceRef(BaseModel):
    """A verbatim excerpt the extraction is traceable to -- never paraphrased.

    Only ever constructed by _segment_evidence()/_sub_evidence(), which
    verify `quote` is an exact substring of the source description at
    [char_start, char_end) before returning it.
    """

    model_config = ConfigDict(strict=True)

    quote: str
    char_start: int | None = None
    char_end: int | None = None


class ExperienceRequirement(BaseModel):
    """One clause of a (possibly multi-clause) experience requirement.

    Entries that share the same non-null `alternative_group` are mutually
    exclusive alternatives connected by "or" in the source text -- either
    on one line ("12+ years with a BS/MS OR 9+ years with a PhD") or across
    adjacent lines (a bullet, a standalone "OR" line, then another bullet).
    `alternative_group is None` means the entry stands on its own (e.g. a
    separate, independently stated preferred amount).
    """

    model_config = ConfigDict(strict=True)

    minimum_years: float
    education_qualifier: str | None
    is_required: bool
    alternative_group: int | None
    evidence: list[EvidenceRef]


class JobRequirements(BaseModel):
    model_config = ConfigDict(strict=True)

    job_id: int
    job_title: str

    career_track: Literal["data", "pharma", "scientific_ai", "unknown"]
    career_track_evidence: list[EvidenceRef]

    required_skills: list[str]
    required_skills_evidence: dict[str, list[EvidenceRef]]
    preferred_skills: list[str]
    preferred_skills_evidence: dict[str, list[EvidenceRef]]

    experience_requirements: list[ExperienceRequirement]

    required_education: list[str]
    required_education_evidence: dict[str, list[EvidenceRef]]
    preferred_education: list[str]
    preferred_education_evidence: dict[str, list[EvidenceRef]]

    responsibilities: list[str]
    responsibilities_evidence: dict[str, list[EvidenceRef]]
    domain_expertise: list[str]
    domain_expertise_evidence: dict[str, list[EvidenceRef]]

    location_requirement: str | None
    remote_allowed: bool | None
    location_evidence: list[EvidenceRef]

    missing_information: list[str]
    ambiguous_information: list[str]

    analysis_mode: Literal["deterministic"] = "deterministic"
    limitations: list[str]
    requires_human_review: Literal[True] = True
    status: Literal["pending_review"] = "pending_review"


# ---------------------------------------------------------------------------
# Segmenting -- position-aware. Preserves paragraph/bullet boundaries when
# present, falls back to naive sentence splitting for legacy flattened
# (single-line) descriptions. Each segment carries its own verified
# [start, end) span in the ORIGINAL description, found by searching
# sequentially forward from the end of the previous segment -- so a
# duplicated line/sentence occurring twice in the document gets two
# distinct, correctly-ordered spans rather than both collapsing onto the
# first occurrence.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Segment:
    text: str
    start: int
    end: int


def _split_into_segments(description: str) -> list[Segment]:
    raw_parts = description.split("\n") if "\n" in description else re.split(r"(?<=[.;])\s+", description)

    segments = []
    cursor = 0
    for raw in raw_parts:
        stripped = raw.strip()
        if not stripped:
            continue
        start = description.find(stripped, cursor)
        if start == -1:
            start = description.find(stripped)  # defensive fallback; should not happen
        if start == -1:
            continue  # cannot verify a position -- never guess one
        end = start + len(stripped)
        segments.append(Segment(stripped, start, end))
        cursor = end
    return segments


# ---------------------------------------------------------------------------
# Evidence construction -- the only paths that may create an EvidenceRef.
# Both take an already-known, verified position rather than searching the
# whole description, so results are always anchored to the correct
# occurrence.
# ---------------------------------------------------------------------------


def _segment_evidence(description: str, segment: Segment) -> list[EvidenceRef]:
    """Evidence for a claim backed by an entire segment's own verified span."""
    if description[segment.start:segment.end] != segment.text:
        return []
    return [EvidenceRef(quote=segment.text, char_start=segment.start, char_end=segment.end)]


def _sub_evidence(description: str, segment: Segment, sub_quote: str) -> list[EvidenceRef]:
    """Evidence for a claim backed by a smaller quote *within* one specific
    segment occurrence -- the search is scoped to that segment's own text,
    so it can never land on some other, unrelated occurrence of the same
    words elsewhere in the description.
    """
    sub_quote = sub_quote.strip()
    if not sub_quote:
        return []
    rel_index = segment.text.lower().find(sub_quote.lower())
    if rel_index == -1:
        return []
    exact_quote = segment.text[rel_index:rel_index + len(sub_quote)]
    start = segment.start + rel_index
    end = start + len(exact_quote)
    if description[start:end] != exact_quote:
        return []
    return [EvidenceRef(quote=exact_quote, char_start=start, char_end=end)]


def _filter_valid_evidence(description: str, refs: list[EvidenceRef]) -> list[EvidenceRef]:
    """Defense-in-depth: drops any evidence ref that doesn't actually point
    at the claimed substring, so a bug elsewhere can never let fabricated
    or mis-offset evidence reach a caller.
    """
    valid = []
    for ref in refs:
        if ref.char_start is None or ref.char_end is None:
            continue
        if description[ref.char_start:ref.char_end] == ref.quote:
            valid.append(ref)
    return valid


def _filter_evidence_map(description: str, mapping: dict[str, list[EvidenceRef]]) -> dict[str, list[EvidenceRef]]:
    return {key: _filter_valid_evidence(description, refs) for key, refs in mapping.items()}


# ---------------------------------------------------------------------------
# Section classification -- distinguishes qualification sections from
# unrelated ones (company background, benefits, compensation, legal/EEO
# text) and from an explicit "unclassified" state for headings this module
# doesn't recognize at all. Content under an unrelated or unclassified
# heading is never folded into required_skills/required_education by
# default -- that would misrepresent incidental mentions as requirements.
# ---------------------------------------------------------------------------

Section = Literal["required", "preferred", "responsibilities", "unrelated", "unclassified"]

_PREFERRED_HEADER = re.compile(
    r"^(?:[-*•]\s*)?(preferred(?: qualifications)?|nice to have|bonus(?: points)?|desirable)\s*:?\s*$",
    re.I,
)
_REQUIRED_HEADER = re.compile(
    r"^(?:[-*•]\s*)?(required(?: qualifications)?|requirements?|minimum qualifications?|"
    r"qualifications?|must[- ]haves?|what you.ll need|skills?(?: set)?|technical skills|"
    r"key skills|what you bring|who you are|education)\s*:?\s*$",
    re.I,
)
_RESPONSIBILITIES_HEADER = re.compile(
    r"^(?:[-*•]\s*)?(responsibilit(?:y|ies)|what you.ll do|you will|duties|the role|day.to.day)\s*:?\s*$",
    re.I,
)
_UNRELATED_HEADER = re.compile(
    r"^(?:[-*•]\s*)?(about (?:the )?(?:company|us|team|organization|role)|our (?:company|story|mission)|"
    r"benefits?|perks?|compensation(?:\s*(?:and|&)\s*benefits)?|what we offer|salary(?: range)?|"
    r"equal opportunity(?: employer)?|eeo(?: statement)?|diversity(?:\s*(?:and|&)\s*inclusion)?|"
    r"how to apply|application process)\s*:?\s*$",
    re.I,
)
_ANY_SECTION_HEADER = re.compile(r"^(?:[-*•]\s*)?[A-Za-z][A-Za-z /&]{1,45}:\s*$")
_PREFERRED_INLINE_CUE = re.compile(r"\b(preferred|nice to have|a plus|bonus|desirable)\b", re.I)


def _classify_segments(segments: list[Segment]) -> list[tuple[Segment, Section]]:
    """Pairs each content segment with its section. A recognized header
    switches the running section for everything that follows, until the
    *next* header of any kind -- so e.g. "preferred" never leaks into an
    unrelated "Benefits:" section just because no "Requirements:" header
    happened to reappear first. An unrecognized heading explicitly becomes
    "unclassified" rather than silently defaulting to "required". Before
    any heading at all, content defaults to "required" (the common pattern
    of listing a core requirement in the opening paragraph before any
    section header exists). Header-only segments are consumed, not
    returned as content.
    """
    section: Section = "required"
    tagged: list[tuple[Segment, Section]] = []
    for segment in segments:
        text = segment.text
        if _PREFERRED_HEADER.match(text):
            section = "preferred"
            continue
        if _REQUIRED_HEADER.match(text):
            section = "required"
            continue
        if _RESPONSIBILITIES_HEADER.match(text):
            section = "responsibilities"
            continue
        if _UNRELATED_HEADER.match(text):
            section = "unrelated"
            continue
        if _ANY_SECTION_HEADER.match(text):
            section = "unclassified"
            continue
        segment_section = section
        if section not in ("unrelated",) and _PREFERRED_INLINE_CUE.search(text):
            segment_section = "preferred"
        tagged.append((segment, segment_section))
    return tagged


# ---------------------------------------------------------------------------
# Skills (required vs preferred) -- reuses matching.extract_skills() as-is,
# called per segment so each hit carries that exact segment occurrence as
# its evidence. Only "required"/"preferred" sections are consulted;
# "responsibilities", "unrelated", and "unclassified" content is excluded
# so e.g. a skill named in passing in a benefits blurb or a day-to-day
# description is never counted as a requirement.
# ---------------------------------------------------------------------------


def _extract_skill_buckets(description: str, classified: list[tuple[Segment, Section]]):
    required: dict[str, list[EvidenceRef]] = {}
    preferred: dict[str, list[EvidenceRef]] = {}
    unclassified_notes: list[str] = []

    for segment, section in classified:
        hits = extract_skills(segment.text)
        if not hits:
            continue
        if section == "unclassified":
            unclassified_notes.append(
                f"Skill-like terms appear under an unrecognized section heading and were not "
                f"classified as required or preferred: {', '.join(sorted(hits))} "
                f"(from \"{segment.text}\")."
            )
            continue
        if section not in ("required", "preferred"):
            continue
        bucket = preferred if section == "preferred" else required
        for skill in hits:
            bucket.setdefault(skill, []).extend(_segment_evidence(description, segment))

    # A skill explicitly evidenced as preferred somewhere should not also be
    # double-counted as required from a different, required-section mention
    # of the same keyword -- mirrors resume_selector's own `preferred -
    # required` precedence (required wins if evidenced in a required
    # context at all).
    for skill in list(preferred):
        if skill in required:
            del preferred[skill]

    return required, preferred, unclassified_notes


# ---------------------------------------------------------------------------
# Experience requirements -- never delegates to matching.extract_years_experience(),
# since that function's single-max-value behavior cannot represent alternatives.
# ---------------------------------------------------------------------------


_YEARS_RANGE_TOKEN = re.compile(r"(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*\+?\s*years?", re.I)
_YEARS_TOKEN = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", re.I)
_EDU_QUALIFIER_TOKEN = re.compile(
    # Bare two-letter forms (bs/ms/ba/ma) require an adjacent "degree" --
    # otherwise "MA" in "Boston, MA" or "BS" as an unrelated acronym would
    # be misread as a qualifier. "PhD"/"doctorate"/spelled-out
    # bachelor's/master's are distinctive enough not to need that guard.
    # A bs/ms-style slash compound ("BS/MS") is also unambiguous on its own.
    r"\b(bs\s*/\s*ms|ms\s*/\s*bs|ph\.?d\.?|doctorate|master'?s?(?:\s+degree)?|"
    r"bachelor'?s?(?:\s+degree)?|(?:bs|ms|ba|ma)\s+degree)\b",
    re.I,
)
_EDU_QUALIFIER_CANONICAL = {
    "phd": "PhD", "ph.d": "PhD", "ph.d.": "PhD", "doctorate": "PhD",
    "bs": "BS", "ba": "BA", "ms": "MS", "ma": "MA",
    "bachelor": "Bachelor's", "bachelors": "Bachelor's", "bachelor's": "Bachelor's",
    "master": "Master's", "masters": "Master's", "master's": "Master's",
}
_REQUIRED_CUE = re.compile(r"\brequired\b", re.I)
_PREFERRED_CUE = re.compile(r"\bpreferred\b", re.I)
_COMPANY_BACKGROUND_MARKERS = re.compile(
    r"\b(founded|since (?:19|20)\d{2}|our company|we have been|industry leader|"
    r"years in business|years of combined (?:industry )?experience|company has|"
    r"organization has|\bfirm has\b)\b",
    re.I,
)
_VAGUE_EXPERIENCE = re.compile(
    r"\b(?:several|some|a few|extensive|significant|many)\s+years?\s+"
    r"(?:of\s+)?(?:\w+\s+){0,2}experience\b",
    re.I,
)
_STANDALONE_OR_LINE = re.compile(r"^(?:[-*•]\s*)?or\s*(?:[-*•])?$", re.I)


def _canonical_qualifier(raw: str) -> str:
    """Normalizes a matched qualifier token to a short name with no
    "degree" suffix (e.g. "Bachelor's degree" -> "Bachelor's"), so callers
    can consistently append their own " degree" wording without risking a
    duplicated "degree degree".
    """
    key = raw.strip().lower().replace(" degree", "").strip()
    if "/" in key:
        parts = [_EDU_QUALIFIER_CANONICAL.get(p.strip(), p.strip().upper()) for p in key.split("/")]
        return "/".join(parts)
    return _EDU_QUALIFIER_CANONICAL.get(key, key.title())


def _nearest_qualifier(segment_text: str, match_end: int) -> str | None:
    """Associates a years-number with the closest education qualifier word
    in the same (short) segment -- segments are line/sentence length, so
    simple proximity is a reasonable, testable heuristic.
    """
    best = None
    best_distance = None
    for qual_match in _EDU_QUALIFIER_TOKEN.finditer(segment_text):
        distance = abs(qual_match.start() - match_end)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best = qual_match.group(0)
    return _canonical_qualifier(best) if best else None


def _years_matches_excluding_ranges(segment_text: str):
    """Yields (number, match_span_text, match_end) for every years mention
    in the segment, resolving a range like "3-5 years" to its *lower*
    (truly minimum) bound as one entry, tagged so callers can note the
    range rather than silently dropping the upper bound.
    """
    results = []
    consumed = set()
    for range_match in _YEARS_RANGE_TOKEN.finditer(segment_text):
        low, high = range_match.group(1), range_match.group(2)
        results.append((float(low), range_match.group(0), range_match.end(), high))
        consumed.update(range(range_match.start(), range_match.end()))
    for match in _YEARS_TOKEN.finditer(segment_text):
        if any(pos in consumed for pos in range(match.start(), match.end())):
            continue
        results.append((float(match.group(1)), match.group(0), match.end(), None))
    results.sort(key=lambda item: item[2])
    return results


def _extract_experience_requirements(description: str, classified: list[tuple[Segment, Section]]):
    requirements: list[ExperienceRequirement] = []
    ambiguous: list[str] = []
    group_id = 0
    pending_or_link = False
    last_batch: list[ExperienceRequirement] = []

    for segment, section in classified:
        text = segment.text

        if section == "unrelated":
            continue
        if _COMPANY_BACKGROUND_MARKERS.search(text):
            continue  # about the company, not a candidate requirement -- ignore entirely

        if _STANDALONE_OR_LINE.match(text):
            pending_or_link = True
            continue

        years_hits = _years_matches_excluding_ranges(text)
        if not years_hits:
            if _VAGUE_EXPERIENCE.search(text):
                ambiguous.append(
                    f"Experience requirement is stated without a specific number of years: \"{text}\"."
                )
            continue

        has_inline_or = bool(re.search(r"\bor\b", text, re.I))
        this_group = None
        if has_inline_or and len(years_hits) >= 2:
            group_id += 1
            this_group = group_id

        new_batch = []
        for years, matched_text, match_end, range_high in years_hits:
            qualifier = _nearest_qualifier(text, match_end)
            is_required = not (_PREFERRED_CUE.search(text) and not _REQUIRED_CUE.search(text))
            req = ExperienceRequirement(
                minimum_years=years,
                education_qualifier=qualifier,
                is_required=is_required,
                alternative_group=this_group,
                evidence=_segment_evidence(description, segment),
            )
            requirements.append(req)
            new_batch.append(req)
            if range_high is not None:
                ambiguous.append(
                    f"A range of years is stated (\"{matched_text}\"); the lower bound ({years:g}) "
                    f"was recorded as the minimum, and the upper bound ({range_high}) is not separately captured."
                )

        if pending_or_link and new_batch and last_batch:
            group_id += 1
            link_group = group_id
            for req in (*last_batch, *new_batch):
                req.alternative_group = link_group
            pending_or_link = False

        if new_batch:
            last_batch = new_batch

    _flag_conflicting_independent_requirements(requirements, ambiguous)
    return requirements, ambiguous


def _flag_conflicting_independent_requirements(requirements: list[ExperienceRequirement], ambiguous: list[str]) -> None:
    """Independent (non-alternative, alternative_group is None) required
    clauses with *different* minimum years are a genuine contradiction in
    the posting -- flag it rather than silently keeping both or picking one.
    """
    independent_required_years = sorted({
        req.minimum_years for req in requirements
        if req.is_required and req.alternative_group is None
    })
    if len(independent_required_years) > 1:
        years_text = ", ".join(f"{y:g}" for y in independent_required_years)
        ambiguous.append(
            f"Multiple differing required-experience amounts were found ({years_text} years) "
            f"that are not stated as alternatives of each other; the correct requirement is unclear."
        )


# ---------------------------------------------------------------------------
# Education (standalone, not already captured as an experience qualifier)
# ---------------------------------------------------------------------------

_EQUIVALENT_EXPERIENCE = re.compile(r"\bor equivalent experience\b", re.I)


def _extract_education(description: str, classified: list[tuple[Segment, Section]], experience_spans: set[tuple[int, int]]):
    required: dict[str, list[EvidenceRef]] = {}
    preferred: dict[str, list[EvidenceRef]] = {}
    ambiguous: list[str] = []

    for segment, section in classified:
        if section not in ("required", "preferred"):
            continue
        if (segment.start, segment.end) in experience_spans:
            continue
        match = _EDU_QUALIFIER_TOKEN.search(segment.text)
        if not match:
            continue
        if _YEARS_TOKEN.search(segment.text):
            continue  # already handled as an experience-requirement qualifier
        qualifier = _canonical_qualifier(match.group(0))
        label = f"{qualifier} degree"
        target = preferred if section == "preferred" else required
        target.setdefault(label, []).extend(_segment_evidence(description, segment))
        if _EQUIVALENT_EXPERIENCE.search(segment.text):
            ambiguous.append(
                f"An experience-based alternative to the {qualifier} degree requirement is "
                f"mentioned (\"{segment.text}\"), but no specific number of years is stated."
            )

    return required, preferred, ambiguous


# ---------------------------------------------------------------------------
# Responsibilities -- only extracted from a segment run that follows a
# clearly-labeled heading; never guessed from arbitrary bullet lists.
# ---------------------------------------------------------------------------

_BULLET_LINE = re.compile(r"^[-*•]\s+")


def _extract_responsibilities(description: str, segments: list[Segment]):
    responsibilities: list[str] = []
    evidence: dict[str, list[EvidenceRef]] = {}
    in_section = False
    for segment in segments:
        text = segment.text
        if _RESPONSIBILITIES_HEADER.match(text):
            in_section = True
            continue
        if in_section and (
            _PREFERRED_HEADER.match(text) or _REQUIRED_HEADER.match(text)
            or _UNRELATED_HEADER.match(text) or _ANY_SECTION_HEADER.match(text)
        ):
            in_section = False
            continue
        if in_section and _BULLET_LINE.match(text):
            item = _BULLET_LINE.sub("", text).strip()
            if not item:
                continue
            refs = _sub_evidence(description, segment, item)
            if not refs:
                continue
            responsibilities.append(item)
            evidence[item] = refs
    return responsibilities, evidence


# ---------------------------------------------------------------------------
# Domain expertise -- a conservative, self-contained term list (not shared
# with resume_selector.TRACK_DOMAINS or job_track_classifier's private
# pattern tuples, to avoid any coupling to those modules' internals). Only
# "required"/"preferred"/"responsibilities" sections are consulted --
# "unrelated" (benefits/company-background/EEO) and "unclassified" content
# is excluded so an incidental mention there is never reported as evidence
# of domain expertise.
# ---------------------------------------------------------------------------

_DOMAIN_TERMS = (
    "medicinal chemistry", "drug discovery", "oncology", "structure-activity relationship",
    "protac", "targeted protein degradation", "organic synthesis", "pharmacology",
    "machine learning", "data engineering", "data pipeline", "etl", "predictive modeling",
    "cheminformatics", "computational chemistry", "molecular modeling", "qsar",
    "virtual screening", "molecular dynamics", "structural biology",
)


def _extract_domain_expertise(description: str, classified: list[tuple[Segment, Section]]):
    found: list[str] = []
    evidence: dict[str, list[EvidenceRef]] = {}
    for segment, section in classified:
        if section not in ("required", "preferred", "responsibilities"):
            continue
        lowered = segment.text.lower()
        for term in _DOMAIN_TERMS:
            if term in lowered and term not in evidence:
                refs = _sub_evidence(description, segment, term)
                if refs:
                    found.append(term)
                    evidence[term] = refs
    return found, evidence


# ---------------------------------------------------------------------------
# Location / remote -- only from explicit statements in the description
# text itself; the job's own location column is never passed to this
# function at all, so a generic city label can never be mistaken for a
# remote/onsite statement.
# ---------------------------------------------------------------------------

_REMOTE_CUE = re.compile(r"\bremote\b", re.I)
_REMOTE_NEGATION = re.compile(r"\b(not|no longer|isn.t|ineligible for)\s+(?:\w+\s+){0,3}remote\b", re.I)
_ONSITE_CUE = re.compile(r"\b(on[- ]site|onsite|in[- ]office|in[- ]person)\b", re.I)
_HYBRID_CUE = re.compile(r"\bhybrid\b", re.I)


def _extract_location(description: str, segments: list[Segment]):
    for segment in segments:
        text = segment.text
        if _REMOTE_NEGATION.search(text):
            return text, False, _segment_evidence(description, segment)
        if _HYBRID_CUE.search(text):
            return text, None, _segment_evidence(description, segment)
        if _REMOTE_CUE.search(text):
            return text, True, _segment_evidence(description, segment)
        if _ONSITE_CUE.search(text):
            return text, False, _segment_evidence(description, segment)
    return None, None, []


# ---------------------------------------------------------------------------
# Career track -- the decision always comes from matching.determine_job_track()
# and job_track_classifier.classify_scientific_ai(), unmodified; the phrase
# lists below are only used to *locate* a supporting quote, never to decide
# the track themselves.
# ---------------------------------------------------------------------------

_TRACK_EVIDENCE_HINTS = {
    "data": ("data scientist", "data analyst", "data engineer", "business analyst", "analytics"),
    "pharma": (
        "medicinal chemistry", "medicinal chemist", "organic chemistry",
        "drug discovery", "pharmaceutical", "scientist",
    ),
    "scientific_ai": (
        "cheminformatics", "computational chemistry", "computational drug discovery",
        "molecular modeling", "machine learning",
    ),
}


def _track_evidence(description: str, segments: list[Segment], track: str) -> list[EvidenceRef]:
    """Evidence is always grounded in the description -- never the job
    title -- so every EvidenceRef uniformly satisfies "exact substring of
    the source description at [char_start, char_end)", with no special
    case for a title-only match carrying no offsets. The title itself is
    still used by determine_job_track()/classify_scientific_ai() to decide
    the track; it just never becomes the evidence quote here.
    """
    if track == "unknown":
        return []
    for segment in segments:
        for hint in _TRACK_EVIDENCE_HINTS.get(track, ()):
            refs = _sub_evidence(description, segment, hint)
            if refs:
                return refs
    return []


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def extract_job_requirements(job_id: int, title: str, description: str | None) -> JobRequirements:
    """Deterministic extraction only -- no network calls, no LLM, no access
    to any other job's or candidate's data. `description` is treated purely
    as data to search; any instruction-like text inside it is never acted
    upon, only pattern-matched like any other substring.
    """
    missing: list[str] = []
    limitations = [
        "Extraction is deterministic (keyword/regex-based); it does not read or infer "
        "meaning the way a human or language model would, and may miss requirements "
        "phrased in ways these patterns don't anticipate.",
    ]

    if not isinstance(description, str) or not description.strip():
        return JobRequirements(
            job_id=job_id,
            job_title=title,
            career_track="unknown",
            career_track_evidence=[],
            required_skills=[],
            required_skills_evidence={},
            preferred_skills=[],
            preferred_skills_evidence={},
            experience_requirements=[],
            required_education=[],
            required_education_evidence={},
            preferred_education=[],
            preferred_education_evidence={},
            responsibilities=[],
            responsibilities_evidence={},
            domain_expertise=[],
            domain_expertise_evidence={},
            location_requirement=None,
            remote_allowed=None,
            location_evidence=[],
            missing_information=["No job description is available for this posting."],
            ambiguous_information=[],
            limitations=limitations,
        )

    segments = _split_into_segments(description)
    classified = _classify_segments(segments)

    required_skills, preferred_skills, unclassified_notes = _extract_skill_buckets(description, classified)
    if not required_skills and not preferred_skills:
        missing.append("No required or preferred technical skills were identified in the description.")

    experience_requirements, experience_ambiguous = _extract_experience_requirements(description, classified)
    if not experience_requirements:
        missing.append("No explicit, numeric experience requirement was found in the description.")

    experience_spans = {
        (ref.char_start, ref.char_end)
        for req in experience_requirements
        for ref in req.evidence
        if ref.char_start is not None
    }
    required_education, preferred_education, education_ambiguous = _extract_education(
        description, classified, experience_spans,
    )

    responsibilities, responsibilities_evidence = _extract_responsibilities(description, segments)
    if not responsibilities:
        missing.append("No clearly labeled responsibilities section was identified.")

    domain_expertise, domain_evidence = _extract_domain_expertise(description, classified)

    location_requirement, remote_allowed, location_evidence = _extract_location(description, segments)

    base_track = determine_job_track(title, description)
    if base_track in ("pharma", "data"):
        career_track = base_track
    elif classify_scientific_ai(sorted(required_skills), sorted(preferred_skills), description):
        career_track = "scientific_ai"
    else:
        career_track = "unknown"
    if career_track == "unknown":
        missing.append("Career track could not be determined from the title and description.")

    ambiguous_information = experience_ambiguous + education_ambiguous + unclassified_notes

    result = JobRequirements(
        job_id=job_id,
        job_title=title,
        career_track=career_track,
        career_track_evidence=_track_evidence(description, segments, career_track),
        required_skills=sorted(required_skills),
        required_skills_evidence=_filter_evidence_map(description, required_skills),
        preferred_skills=sorted(preferred_skills),
        preferred_skills_evidence=_filter_evidence_map(description, preferred_skills),
        experience_requirements=experience_requirements,
        required_education=sorted(required_education),
        required_education_evidence=_filter_evidence_map(description, required_education),
        preferred_education=sorted(preferred_education),
        preferred_education_evidence=_filter_evidence_map(description, preferred_education),
        responsibilities=responsibilities,
        responsibilities_evidence=_filter_evidence_map(description, responsibilities_evidence),
        domain_expertise=domain_expertise,
        domain_expertise_evidence=_filter_evidence_map(description, domain_evidence),
        location_requirement=location_requirement,
        remote_allowed=remote_allowed,
        location_evidence=_filter_valid_evidence(description, location_evidence),
        missing_information=missing,
        ambiguous_information=ambiguous_information,
        limitations=limitations,
    )

    # Final defense-in-depth evidence sweep across every evidence-bearing field.
    result.career_track_evidence = _filter_valid_evidence(description, result.career_track_evidence)
    for req in result.experience_requirements:
        req.evidence = _filter_valid_evidence(description, req.evidence)

    return result
