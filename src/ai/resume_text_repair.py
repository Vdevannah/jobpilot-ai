"""Local-only, conservative section-heading repair for PDF-extracted resume text.

Produces text compatible with the existing privacy sanitizer's exact-line
SECTIONS allowlist in resume_privacy.py, without modifying that module. Only
known heading labels are touched: recognized headings are normalized onto
their own line, and recognized headings that map confidently onto one of the
sanitizer's recognized categories are rewritten to that category's exact
label. Never invents, rewrites, or summarizes resume content. Merged
heading+content lines are split only when the merge pattern is unambiguous;
anything less certain is left untouched and reported, never guessed. A
heading with no confident match to any known phrase is also left untouched
and reported, rather than guessed. Pure text processing: no file, network,
credential, or approval operations occur here.
"""

import re
from dataclasses import dataclass, field

SKILLS = 'Skills'
EDUCATION = 'Education'
EXPERIENCE = 'Professional experience'
PROJECTS = 'Projects'
QUALIFICATIONS = 'Qualifications'
PUBLICATIONS = 'Publications and patents'

# Each phrase maps to one of the sanitizer's recognized categories. Coauthor
# names, the candidate's own name in a citation, and publication/patent
# citations are publicly available professional information and are
# preserved locally under PUBLICATIONS (Phase 7G.5G); that section is
# excluded from external-use approval by default (see resume_privacy.
# approve_resume's include_citations parameter), which is the appropriate
# place to gate that distinction -- not heading recognition.
_ALIASES: dict[str, str | None] = {
    'skills': SKILLS,
    'summary of skills': SKILLS,
    'technical skills': SKILLS,
    'technical & scientific skills': SKILLS,
    'technical and scientific skills': SKILLS,
    'education': EDUCATION,
    'professional experience': EXPERIENCE,
    'employment history': EXPERIENCE,
    'projects': PROJECTS,
    'selected ai, data science & application projects': PROJECTS,
    'selected ai, data science and application projects': PROJECTS,
    'professional summary': QUALIFICATIONS,
    'qualifications': QUALIFICATIONS,
    'publications and patents': PUBLICATIONS,
    'publications & patents': PUBLICATIONS,
}

# Longest phrase first so a longer, more specific phrase is tried before a
# shorter one that could also match as a prefix (defensive; current phrases
# do not actually collide, but this keeps future additions safe).
_ORDERED_PHRASES = sorted(_ALIASES, key=len, reverse=True)
_PATTERNS = [(phrase, re.compile(re.escape(phrase).replace(r'\ ', r'\s+'), re.IGNORECASE))
             for phrase in _ORDERED_PHRASES]


@dataclass
class RepairReport:
    """Summary of heading repairs. Contains only generic category labels and
    the known boilerplate heading phrases themselves -- never resume content."""

    mapped_headings: list[str] = field(default_factory=list)
    unmapped_headings: list[str] = field(default_factory=list)
    ambiguous_count: int = 0

    @property
    def needs_manual_review(self) -> bool:
        return bool(self.unmapped_headings) or self.ambiguous_count > 0


@dataclass
class RepairResult:
    text: str
    report: RepairReport


def _classify_merge(heading_segment: str, remainder: str) -> str:
    """Return 'standalone', 'high', 'ambiguous', or 'none' confidence that
    heading_segment is genuinely a heading and remainder is separate content."""
    if remainder == '':
        return 'standalone'
    if remainder.startswith(':'):
        return 'high'
    first = remainder[0]
    if first not in (' ', '\t'):
        # No separating whitespace at all (a common no-space PDF merge
        # artifact, e.g. "EducationPhD..."). Only confident when the next
        # character starts a new token (upper/digit); a lowercase
        # continuation likely means the "heading" is actually a prefix of a
        # longer, unrelated word (e.g. "Skillset").
        return 'high' if (first.isupper() or first.isdigit()) else 'none'
    content = remainder.lstrip()
    if not content:
        return 'standalone'
    if heading_segment.isupper() and len(heading_segment) > 3:
        # ALL-CAPS heading styling followed by space-separated content is a
        # strong signal, provided the content itself looks like it starts a
        # new item rather than continuing a sentence.
        return 'high' if (content[0].isupper() or content[0].isdigit()) else 'ambiguous'
    # Mixed/title-case heading immediately followed by a space and lowercase
    # content, with no colon, is too easily confused with an ordinary
    # sentence that happens to start with a heading word (e.g. "Skills
    # development was central to..."). Do not guess; flag for manual review.
    return 'ambiguous'


def _match_known_heading(stripped_line: str):
    for phrase, pattern in _PATTERNS:
        m = pattern.match(stripped_line)
        if not m:
            continue
        heading_segment = stripped_line[:m.end()]
        remainder = stripped_line[m.end():]
        confidence = _classify_merge(heading_segment, remainder)
        if confidence == 'none':
            continue
        return phrase, _ALIASES[phrase], heading_segment, remainder, confidence
    return None


def repair_section_headings(text: str) -> RepairResult:
    """Conservatively repair known resume section headings in extracted text.

    - A standalone known heading is normalized to its mapped category label
      (case/wording only; unmapped known headings keep their original text).
    - A heading merged with content on the same line is split onto its own
      line only when the merge pattern is unambiguous (explicit colon, or a
      no-space/ALL-CAPS artifact followed by a new token); the content that
      follows is preserved verbatim.
    - Ambiguous merges and headings with no safe existing category are left
      as local text and reported, never guessed or dropped silently.
    - All other lines are returned completely unchanged.
    """
    report = RepairReport()
    out_lines: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            out_lines.append(raw_line)
            continue
        match = _match_known_heading(stripped)
        if match is None:
            out_lines.append(raw_line)
            continue
        phrase, canonical, heading_segment, remainder, confidence = match
        if confidence == 'ambiguous':
            report.ambiguous_count += 1
            out_lines.append(raw_line)
            continue
        if canonical is not None:
            report.mapped_headings.append(canonical)
            out_lines.append(canonical)
        else:
            report.unmapped_headings.append(heading_segment.strip())
            out_lines.append(heading_segment.strip())
        content = remainder.lstrip(': \t')
        if content:
            out_lines.append(content)
    return RepairResult(text='\n'.join(out_lines), report=report)
