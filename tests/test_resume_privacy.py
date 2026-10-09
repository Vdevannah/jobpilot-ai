from unittest.mock import Mock

import pytest

from src.ai.resume_privacy import (
    ResumePrivacyError, approve_resume, preview_resume, require_approved_resume,
)
from src.ai import openai_client


def test_headers_repeated_identifiers_and_contact_lines_removed():
    # Reserved synthetic placeholders only; no real personal data.
    original = '\n'.join(['CANDIDATE_TOKEN', 'CITY_TOKEN', 'Skills:', 'Python',
                          'CANDIDATE_TOKEN authored project', 'CITY_TOKEN research',
                          'contact@example.invalid', 'https://example.invalid/profile',
                          '12345', '000-000-0000', 'Education:', 'PhD in Chemistry'])
    preview = preview_resume(original, identifiers=['CANDIDATE_TOKEN', 'CITY_TOKEN'])
    assert preview == 'Location: Delaware, USA\nSkills:\nPython\nEducation:\nPhD in Chemistry'
    assert str(approve_resume(preview, confirmed=True)) == preview


@pytest.mark.parametrize('status', ['visa', 'immigration', 'citizenship', 'permanent residency',
                                   'work authorization', 'green card', 'H-1B', 'sponsorship'])
def test_status_removed(status):
    preview = preview_resume('Skills:\nPython\n' + status + ': SYNTHETIC', identifiers=[])
    assert status not in preview


def test_unapproved_resume_blocks_sdk(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    sdk = Mock()
    monkeypatch.setattr(openai_client, 'OpenAI', sdk)
    with pytest.raises(ResumePrivacyError):
        openai_client.OpenAIResumeClient().analyze_resume('Skills: Python')
    sdk.return_value.responses.parse.assert_not_called()


def test_approval_and_pdf_fail_closed():
    with pytest.raises(ResumePrivacyError):
        approve_resume('Location: Delaware, USA\nSkills:\nPython', confirmed=False)
    with pytest.raises(ResumePrivacyError):
        preview_resume('%PDF synthetic', identifiers=[])


def test_declined_script_preview_precedes_credentials_and_requests(monkeypatch):
    from scripts import test_openai_resume as script
    monkeypatch.setattr('builtins.input', lambda prompt: 'NO')
    loader, client = Mock(), Mock()
    monkeypatch.setattr(script, 'load_dotenv', loader)
    monkeypatch.setattr(script, 'OpenAIResumeClient', client)
    assert script.main(['--live']) == 1
    loader.assert_not_called()
    client.assert_not_called()


# --- Phase 7G.5G: publicly available professional information policy ---

def test_employer_university_names_and_locations_survive_identifier_match():
    # Reserved synthetic placeholders only; no real personal data. CITY_TOKEN
    # is supplied as an identifier (as a candidate might enter their own
    # hometown), but it also names the university's location; per the new
    # policy, professional employment/education locations are preserved.
    original = '\n'.join([
        'CANDIDATE_TOKEN', 'CITY_TOKEN',
        'Professional experience:', 'Fictional Corp, CITY_TOKEN, Fictional Scientist',
        'Education:', 'PhD, Fictional University of CITY_TOKEN',
        'Skills:', 'Python, CITY_TOKEN-brand-tool',
    ])
    preview = preview_resume(original, identifiers=['CANDIDATE_TOKEN', 'CITY_TOKEN'])
    assert 'Fictional Corp, CITY_TOKEN, Fictional Scientist' in preview
    assert 'PhD, Fictional University of CITY_TOKEN' in preview
    # Skills remains identifier-sensitive; this policy is scoped to
    # education/experience/publications, not every section.
    assert 'CITY_TOKEN-brand-tool' not in preview


def test_citation_names_survive_within_publications_section():
    # A coauthor name and the candidate's own name, as they would appear in a
    # publicly available citation, both survive even though the candidate's
    # name is supplied as a removal identifier.
    original = '\n'.join([
        'CANDIDATE_TOKEN', 'Skills:', 'Python',
        'Publications and patents:',
        'CANDIDATE_TOKEN, COAUTHOR_TOKEN, Fictional Journal of Chemistry, 2020',
    ])
    preview = preview_resume(original, identifiers=['CANDIDATE_TOKEN'])
    assert 'CANDIDATE_TOKEN, COAUTHOR_TOKEN, Fictional Journal of Chemistry, 2020' in preview


@pytest.mark.parametrize('section', ['Education:', 'Professional experience:', 'Publications and patents:'])
def test_sensitive_contact_patterns_still_removed_in_exempt_sections(section):
    # Identifier exemption never weakens the unconditional SENSITIVE removal
    # of contact details or immigration status, even in a preserved section.
    preview = preview_resume('\n'.join([
        section, 'contact@example.invalid', '12345', 'Visa status: SYNTHETIC',
        'Fictional University', 'https://github.com/synthetic-placeholder',
    ]), identifiers=[])
    assert 'contact@example.invalid' not in preview
    assert '12345' not in preview
    assert 'Visa status' not in preview
    assert 'github.com' not in preview
    assert 'Fictional University' in preview


def test_approve_resume_excludes_citations_by_default():
    preview = preview_resume('\n'.join([
        'Skills:', 'Python', 'Publications and patents:',
        'CANDIDATE_TOKEN, COAUTHOR_TOKEN, Fictional Journal, 2020',
    ]), identifiers=[])
    approved = approve_resume(preview, confirmed=True)
    assert 'COAUTHOR_TOKEN' not in str(approved)
    assert 'Publications and patents' not in str(approved)
    assert 'Python' in str(approved)


def test_approve_resume_include_citations_requires_separate_explicit_flag():
    preview = preview_resume('\n'.join([
        'Skills:', 'Python', 'Publications and patents:',
        'CANDIDATE_TOKEN, COAUTHOR_TOKEN, Fictional Journal, 2020',
    ]), identifiers=[])
    excluded = approve_resume(preview, confirmed=True)
    assert 'COAUTHOR_TOKEN' not in str(excluded)
    included = approve_resume(preview, confirmed=True, include_citations=True)
    assert 'COAUTHOR_TOKEN' in str(included)
    # require_approved_resume must not silently re-strip what was already
    # explicitly approved -- it only re-validates shape/safety.
    assert 'COAUTHOR_TOKEN' in require_approved_resume(included)


def test_approve_resume_fails_closed_when_only_citations_survive():
    preview = preview_resume('\n'.join([
        'Publications and patents:', 'CANDIDATE_TOKEN, Fictional Journal, 2020',
    ]), identifiers=[])
    with pytest.raises(ResumePrivacyError):
        approve_resume(preview, confirmed=True)
    approve_resume(preview, confirmed=True, include_citations=True)


def test_sdk_payload_excludes_citations_unless_explicitly_approved(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    sdk = Mock()
    monkeypatch.setattr(openai_client, 'OpenAI', sdk)
    from types import SimpleNamespace
    sdk.return_value.responses.parse.return_value = SimpleNamespace(
        status='completed', output=[], output_parsed={
            'skills': ['Python'], 'professional_experience_years': {'pharma': None, 'data': None},
            'education': [], 'domains': [], 'summary': 'Synthetic summary.',
        },
    )
    preview = preview_resume('\n'.join([
        'Skills:', 'Python', 'Publications and patents:',
        'CANDIDATE_TOKEN, COAUTHOR_TOKEN, Fictional Journal, 2020',
    ]), identifiers=[])
    approved = approve_resume(preview, confirmed=True)
    openai_client.OpenAIResumeClient().analyze_resume(approved)
    sent = sdk.return_value.responses.parse.call_args.kwargs['input'][0]['content']
    assert 'COAUTHOR_TOKEN' not in sent
