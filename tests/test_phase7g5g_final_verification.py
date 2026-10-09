"""Phase 7G.5G final privacy verification.

Confirms identifier-exempt professional sections (education, professional
experience, publications and patents) do not accidentally let private
contact information into approved, AI-bound text. Fictional synthetic
examples only; no real personal data. No network access, no external API
calls, no CandidateProfile access.
"""
from unittest.mock import Mock

import pytest

from src.ai.resume_privacy import (
    ResumePrivacyError, approve_resume, preview_resume, require_approved_resume,
)
from src.ai.resume_text_repair import repair_section_headings


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Network or credential access is forbidden during privacy verification')
    monkeypatch.setattr('socket.socket', blocked)
    monkeypatch.setattr('os.getenv', blocked)


FICTIONAL_NAME = 'Fictional Zephyr Exampleperson'
FICTIONAL_CITY = 'Fictional Harbor City'
FICTIONAL_COAUTHOR = 'Fictional A. Coauthor'


# 1. Personal name in resume header is removed.
def test_1_personal_name_in_header_removed():
    text = '\n'.join([
        FICTIONAL_NAME, FICTIONAL_CITY,
        'Skills:', 'Python, SQL',
    ])
    preview = preview_resume(text, identifiers=[FICTIONAL_NAME, FICTIONAL_CITY])
    assert FICTIONAL_NAME not in preview
    assert FICTIONAL_CITY not in preview
    assert preview.startswith('Location: Delaware, USA\n')


# 2. Employer and university names remain intact.
def test_2_employer_and_university_names_intact():
    text = '\n'.join([
        FICTIONAL_NAME,
        'Professional experience:', 'Fictional BioPharm Corp, Senior Fictional Scientist',
        'Education:', 'PhD, Fictional Institute of Technology',
    ])
    preview = preview_resume(text, identifiers=[FICTIONAL_NAME])
    assert 'Fictional BioPharm Corp' in preview
    assert 'Fictional Institute of Technology' in preview


# 3. Professional city/state locations remain intact, even when they match a
# personal identifier the candidate supplied (e.g. a hometown that coincides
# with an employer's or university's city).
def test_3_professional_locations_intact_despite_identifier_collision():
    text = '\n'.join([
        FICTIONAL_NAME,
        'Professional experience:', f'Fictional BioPharm Corp, {FICTIONAL_CITY}, FS',
        'Education:', f'PhD, Fictional University of {FICTIONAL_CITY}',
        'Skills:', f'{FICTIONAL_CITY}-brand-toolkit',
    ])
    preview = preview_resume(text, identifiers=[FICTIONAL_NAME, FICTIONAL_CITY])
    assert f'Fictional BioPharm Corp, {FICTIONAL_CITY}, FS' in preview
    assert f'PhD, Fictional University of {FICTIONAL_CITY}' in preview
    # Skills is not identifier-exempt by policy; the collision still applies there.
    assert f'{FICTIONAL_CITY}-brand-toolkit' not in preview


# 4. Personal contact/immigration info removed even inside Education and
# Professional experience (the identifier-exempt sections never exempt
# SENSITIVE structural removal).
@pytest.mark.parametrize('section', ['Education:', 'Professional experience:'])
def test_4_sensitive_contact_and_immigration_removed_in_exempt_sections(section):
    text = '\n'.join([
        section,
        'Fictional Institute of Technology',
        'fictional.synthetic@example.invalid',
        '+1 (202) 555-0100',
        '123 Imaginary Street, Fictional Harbor City, 00000',
        'https://www.linkedin.com/in/fictional-placeholder',
        'https://github.com/fictional-placeholder',
        'Work authorization: fictional status; sponsorship required',
        'Citizenship: fictional; permanent residency: fictional',
    ])
    preview = preview_resume(text, identifiers=[])
    assert 'Fictional Institute of Technology' in preview
    for leaked in (
        'example.invalid', '555-0100', 'Imaginary Street', '00000',
        'linkedin.com', 'github.com', 'Work authorization', 'Citizenship', 'residency',
    ):
        assert leaked not in preview


# 5. Public publication citations are preserved in local preview, including
# the candidate's own name supplied as a removal identifier.
def test_5_publication_citations_preserved_locally():
    text = '\n'.join([
        FICTIONAL_NAME, 'Skills:', 'Python',
        'Publications and patents:',
        f'{FICTIONAL_NAME}, {FICTIONAL_COAUTHOR}, Fictional Journal of Chemistry, 2021',
    ])
    preview = preview_resume(text, identifiers=[FICTIONAL_NAME])
    assert f'{FICTIONAL_NAME}, {FICTIONAL_COAUTHOR}, Fictional Journal of Chemistry, 2021' in preview


# 6. Publication citations are excluded from approved external text by default.
def test_6_citations_excluded_from_approval_by_default():
    text = '\n'.join([
        'Skills:', 'Python',
        'Publications and patents:',
        f'{FICTIONAL_NAME}, {FICTIONAL_COAUTHOR}, Fictional Journal of Chemistry, 2021',
    ])
    preview = preview_resume(text, identifiers=[FICTIONAL_NAME])
    approved = approve_resume(preview, confirmed=True)
    assert FICTIONAL_COAUTHOR not in str(approved)
    assert 'Publications and patents' not in str(approved)
    assert 'Python' in str(approved)
    # require_approved_resume (the OpenAIResumeClient gate) must not restore them.
    assert FICTIONAL_COAUTHOR not in require_approved_resume(approved)


# 7. Publication citations are included only with explicit include_citations=True.
def test_7_citations_included_only_with_explicit_flag():
    text = '\n'.join([
        'Skills:', 'Python',
        'Publications and patents:',
        f'{FICTIONAL_NAME}, {FICTIONAL_COAUTHOR}, Fictional Journal of Chemistry, 2021',
    ])
    preview = preview_resume(text, identifiers=[FICTIONAL_NAME])
    default_approved = approve_resume(preview, confirmed=True)
    explicit_false = approve_resume(preview, confirmed=True, include_citations=False)
    included = approve_resume(preview, confirmed=True, include_citations=True)
    assert FICTIONAL_COAUTHOR not in str(default_approved)
    assert FICTIONAL_COAUTHOR not in str(explicit_false)
    assert FICTIONAL_COAUTHOR in str(included)
    # The decision is exact-content and is not silently changed on reuse.
    assert FICTIONAL_COAUTHOR in require_approved_resume(included)


# 8. Ambiguous or unsafe content fails closed rather than being silently approved.
def test_8a_unconfirmed_approval_fails_closed():
    with pytest.raises(ResumePrivacyError):
        approve_resume('Location: Delaware, USA\nSkills:\nPython', confirmed=False)


def test_8b_tampered_preview_with_sensitive_content_fails_closed():
    forged = 'Location: Delaware, USA\nSkills:\nPython\nfictional.synthetic@example.invalid'
    with pytest.raises(ResumePrivacyError):
        approve_resume(forged, confirmed=True)


def test_8c_citation_only_content_fails_closed_without_explicit_flag():
    text = '\n'.join(['Publications and patents:', f'{FICTIONAL_NAME}, Fictional Journal, 2021'])
    preview = preview_resume(text, identifiers=[])
    with pytest.raises(ResumePrivacyError):
        approve_resume(preview, confirmed=True)
    # Still succeeds with the separate, explicit decision -- not a dead end.
    approve_resume(preview, confirmed=True, include_citations=True)


def test_8d_unapproved_plain_string_is_rejected():
    with pytest.raises(ResumePrivacyError):
        require_approved_resume('Location: Delaware, USA\nSkills:\nPython\nEducation:\nPhD')


def test_8e_modified_approved_text_loses_approval():
    approved = approve_resume('Location: Delaware, USA\nSkills:\nPython', confirmed=True)
    tampered = approved + '\nfictional.synthetic@example.invalid'  # becomes a plain str
    with pytest.raises(ResumePrivacyError):
        require_approved_resume(tampered)


def test_8f_ambiguous_heading_not_guessed_and_flagged_for_manual_review():
    # A sentence that merely starts with a heading word, with no colon and no
    # merge artifact, must not be guessed into a section.
    text = f'Skills development was central to my role as {FICTIONAL_NAME} the fictional scientist.\n'
    result = repair_section_headings(text)
    assert result.text == text.rstrip('\n')
    assert result.report.ambiguous_count == 1
    assert result.report.needs_manual_review is True


def test_8g_privacy_functions_never_print_content(capsys):
    text = '\n'.join([
        FICTIONAL_NAME, 'Education:', f'PhD, Fictional University, {FICTIONAL_CITY}',
        'Publications and patents:', f'{FICTIONAL_NAME}, {FICTIONAL_COAUTHOR}, Fictional Journal, 2021',
    ])
    preview_resume(text, identifiers=[FICTIONAL_NAME])
    approve_resume(
        preview_resume(text, identifiers=[FICTIONAL_NAME]), confirmed=True, include_citations=True,
    )
    assert capsys.readouterr().out == ''
