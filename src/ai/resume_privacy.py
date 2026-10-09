"""Local-only resume minimization and exact-content human approval.

Policy (Phase 7G.5G): publicly available professional information is
permitted locally -- employer/university names, professional employment and
education locations, scientific accomplishments/degrees/technical
qualifications, and names appearing in published scientific articles/patents
(including coauthors and the candidate's own name in a citation) are
preserved. Personal name in resume headers/contact sections, personal email
and phone, home address/ZIP, personal LinkedIn/GitHub profile URLs, and
immigration/visa/citizenship/residency/work-authorization status are always
removed regardless of section. The candidate's general location is always
represented only as "Delaware, USA". Publication/patent citations preserved
locally are additionally excluded from external-use approval by default; see
approve_resume's include_citations parameter.
"""

import re


class ResumePrivacyError(ValueError):
    """Resume content has not passed local privacy review."""


class ApprovedResumeText(str):
    """In-memory marker for exact content explicitly reviewed by the caller."""


SENSITIVE = re.compile(
    r'visa|immigration|citizenship|citizen|permanent resid|work authori|green card|'
    r'right to work|sponsorship|\bh[ -]?1b\b|\bopt\b|\bcpt\b|\bf[ -]?1\b|'
    r'@|https?://|www\.|linkedin|github\.com|\b\d{5}(?:-\d{4})?\b|'
    r'(?:\+?\d[\s().-]*){7,}|\b\d+\s+\w+\s+(?:street|st|road|rd|avenue|ave|lane|ln)\b', re.I,
)
SECTIONS = {
    'skills', 'education', 'professional experience', 'projects',
    'qualifications', 'publications and patents',
}
PUBLICATIONS_SECTION = 'publications and patents'

# Sections where publicly available professional facts -- employer/university
# names, professional locations, and (for publications) coauthor/candidate
# citation names -- are preserved against identifier-substring removal.
# SENSITIVE patterns (contact info, immigration status) still apply there
# unconditionally; only the caller-supplied identifier list is exempted.
IDENTIFIER_EXEMPT_SECTIONS = {'education', 'professional experience', PUBLICATIONS_SECTION}


def preview_resume(text: str, *, identifiers: list[str]) -> str:
    """Keep allowlisted sections; drop identifying lines. Never read/upload files.

    identifiers must include all known candidate names, cities and address variants.
    Human review is mandatory because unknown identifiers cannot be inferred reliably.
    Within education, professional experience, and publications/patents sections,
    identifier matching is skipped so employer/university names, professional
    locations, and citation names are preserved; contact-pattern (SENSITIVE)
    removal still applies everywhere, including those sections.
    """
    if not isinstance(text, str) or text.startswith('%PDF'):
        raise ResumePrivacyError('Only locally extracted plain text is supported.')
    lines = ['Location: Delaware, USA']
    active = False
    current_section = None
    for line in text.splitlines():
        stripped = line.strip()
        folded = stripped.casefold().rstrip(':')
        if folded in SECTIONS:
            active = True
            current_section = folded
            lines.append(stripped)
            continue
        if not active or not stripped:
            continue
        if SENSITIVE.search(stripped):
            continue
        if current_section not in IDENTIFIER_EXEMPT_SECTIONS and any(
            i.strip() and i.casefold() in stripped.casefold() for i in identifiers
        ):
            continue
        if re.search(r'\b(location|address|name|contact)\s*:', stripped, re.I):
            continue
        lines.append(stripped)
    return '\n'.join(lines)


def _without_section(text: str, section: str) -> str:
    """Remove one recognized section's heading and body lines from text."""
    out = []
    skipping = False
    for line in text.splitlines():
        folded = line.strip().casefold().rstrip(':')
        if folded in SECTIONS:
            skipping = (folded == section)
            if skipping:
                continue
        elif skipping:
            continue
        out.append(line)
    return '\n'.join(out)


def _validate_preview_shape(text: str) -> None:
    if (not text.startswith('Location: Delaware, USA\n')
            or SENSITIVE.search(text) or len(text.splitlines()) < 3):
        raise ResumePrivacyError('Local privacy review is required; request blocked.')


def approve_resume(preview: str, *, confirmed: bool, include_citations: bool = False) -> ApprovedResumeText:
    """Caller attests human review of every line; never approve automatically.

    Publication/patent citations are preserved locally by preview_resume() but
    are excluded from this external-use approval by default, since a citation
    combines the candidate's name with coauthors and exact titles -- a stronger
    identifying fingerprint than structured skills/education/experience facts.
    Pass include_citations=True only as a second, separate, explicit decision
    to share that specific content externally; it is never implied by confirmed=True.
    """
    if confirmed is not True:
        raise ResumePrivacyError('Local privacy review is required; request blocked.')
    _validate_preview_shape(preview)
    text = preview if include_citations else _without_section(preview, PUBLICATIONS_SECTION)
    _validate_preview_shape(text)
    return ApprovedResumeText(text)


def require_approved_resume(text: str) -> str:
    if not isinstance(text, ApprovedResumeText):
        raise ResumePrivacyError('Unapproved resume content blocked. Preview and approve locally first.')
    _validate_preview_shape(text)
    return str(text)


def review_sample_locally(text: str) -> ApprovedResumeText:
    """Interactive approval for the repository's synthetic sample only."""
    preview = preview_resume('Qualifications:\n' + text, identifiers=[])
    print('LOCAL PRIVACY PREVIEW — not sent to any provider\n' + preview)
    print('Verify no names, contact details, cities, immigration/work status, or other personal data remain.')
    try:
        answer = input('Type APPROVE to authorize this exact sanitized content: ')
    except (EOFError, KeyboardInterrupt):
        raise ResumePrivacyError('Privacy approval not received.') from None
    return approve_resume(preview, confirmed=answer == 'APPROVE')
