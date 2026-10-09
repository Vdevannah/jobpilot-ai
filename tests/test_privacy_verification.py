"""Local privacy verification with invented identifiers and mocked SDK only."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.ai import openai_client as api
from src.ai.resume_privacy import (
    ApprovedResumeText, ResumePrivacyError, approve_resume, preview_resume,
    require_approved_resume,
)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Network access is forbidden during privacy verification')
    monkeypatch.setattr('socket.socket', blocked)


@pytest.fixture
def synthetic():
    # Entirely invented name/address; reserved example.invalid and 555-01xx phone.
    return '\n'.join([
        'Fictional Zephyr Exampleperson', 'Synthetic Harbor',
        'Qualifications:', 'Fictional Zephyr Exampleperson — resume header',
        'synthetic@example.invalid', '+1 (202) 555-0100',
        '123 Imaginary Street, Synthetic Harbor, 00000',
        'Work authorization: fictional status; sponsorship required',
        'Citizenship: fictional; permanent residency: fictional',
        'https://www.linkedin.com/in/synthetic-placeholder',
        'https://github.com/synthetic-placeholder',
        'Skills:', 'Python, SQL, SAR, PROTACs',
        'Professional experience:', '8 years of pharmaceutical industry research.',
        'Education:', 'PhD in Organic Chemistry',
        'Projects:', 'Built a Python data pipeline.',
        'Fictional Zephyr Exampleperson — repeated footer',
    ])


def sanitized(text):
    return preview_resume(text, identifiers=['Fictional Zephyr Exampleperson', 'Synthetic Harbor'])


def test_synthetic_identifiers_removed_and_evidence_preserved(synthetic, capsys):
    text = sanitized(synthetic)
    assert text == ('Location: Delaware, USA\nQualifications:\nSkills:\nPython, SQL, SAR, PROTACs\n'
                    'Professional experience:\n8 years of pharmaceutical industry research.\n'
                    'Education:\nPhD in Organic Chemistry\nProjects:\nBuilt a Python data pipeline.')
    assert text.count('Delaware, USA') == 1
    assert not isinstance(text, ApprovedResumeText)
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('confirmation', [False, None, 'false', 'APPROVE', 1])
def test_approval_requires_actual_boolean_confirmation(confirmation):
    with pytest.raises(ResumePrivacyError):
        approve_resume('Location: Delaware, USA\nSkills:\nPython', confirmed=confirmation)


def test_unknown_identifier_is_not_automatically_approved():
    preview = preview_resume('Skills:\nPython\nUNKNOWN_IDENTITY_TOKEN', identifiers=[])
    assert 'UNKNOWN_IDENTITY_TOKEN' in preview  # Known limitation, not a claim of detection.
    with pytest.raises(ResumePrivacyError):
        require_approved_resume(preview)
    with pytest.raises(ResumePrivacyError):
        approve_resume(preview, confirmed=False)


def test_modified_approved_text_loses_approval():
    approved = approve_resume('Location: Delaware, USA\nSkills:\nPython', confirmed=True)
    with pytest.raises(ResumePrivacyError):
        require_approved_resume(approved + '\nUNREVIEWED_TEXT')


@pytest.mark.parametrize('text', [None, b'%PDF synthetic', '%PDF synthetic'])
def test_extraction_invalid_input_fails_closed(text):
    with pytest.raises(ResumePrivacyError):
        preview_resume(text, identifiers=[])


def test_only_approved_sanitized_content_reaches_mock_sdk(synthetic, monkeypatch, capsys):
    sdk = Mock()
    monkeypatch.setenv('OPENAI_API_KEY', 'test-placeholder')
    monkeypatch.setattr(api, 'OpenAI', sdk)
    sdk.return_value.responses.parse.return_value = SimpleNamespace(
        status='completed', output=[], output_parsed={
            'skills': ['Python', 'SQL'], 'professional_experience_years': {'pharma': 8.0, 'data': None},
            'education': ['PhD in Organic Chemistry'], 'domains': ['drug discovery'],
            'summary': 'Research experience and technical skills.',
        })
    client = api.OpenAIResumeClient()
    with pytest.raises(ResumePrivacyError):
        client.analyze_resume(synthetic)
    sdk.return_value.responses.parse.assert_not_called()
    approved = approve_resume(sanitized(synthetic), confirmed=True)
    report = client.analyze_resume(approved)
    assert sdk.return_value.responses.parse.call_args.kwargs['input'][0]['content'] == str(approved)
    assert 'Exampleperson' not in report.model_dump_json()
    assert capsys.readouterr().out == ''
    sdk.return_value.responses.parse.return_value.output_parsed['summary'] = 'synthetic@example.invalid'
    with pytest.raises(api.InvalidResumeOutputError) as error:
        client.analyze_resume(approved)
    assert 'example.invalid' not in str(error.value)


@pytest.mark.parametrize('script_name', ['test_openai_resume', 'test_openai_workflow'])
@pytest.mark.parametrize('failure', ['sanitize', 'approval'])
def test_script_errors_prevent_credentials_and_api(monkeypatch, script_name, failure):
    import importlib
    from src.ai import resume_privacy
    script = importlib.import_module('scripts.' + script_name)
    loader = Mock()
    monkeypatch.setattr(script, 'load_dotenv', loader)
    if failure == 'sanitize':
        monkeypatch.setattr(resume_privacy, 'preview_resume', Mock(side_effect=ResumePrivacyError('blocked')))
    else:
        monkeypatch.setattr('builtins.input', Mock(side_effect=EOFError))
    factory = Mock()
    monkeypatch.setattr(script, 'OpenAIResumeClient' if script_name == 'test_openai_resume' else 'create_workflow', factory)
    assert script.main(['--live']) == 1
    loader.assert_not_called()
    factory.assert_not_called()
