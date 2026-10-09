from unittest.mock import Mock

import pytest

from scripts import preview_resume as script
from src.ai import resume_privacy


@pytest.fixture(autouse=True)
def local_only(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Forbidden credential, network, write, or approval operation')
    monkeypatch.setattr('socket.socket', forbidden)
    monkeypatch.setattr('os.getenv', forbidden)
    monkeypatch.setattr(resume_privacy, 'approve_resume', forbidden)
    monkeypatch.setattr(script.Path, 'write_text', forbidden)
    monkeypatch.setattr(script.Path, 'write_bytes', forbidden)
    monkeypatch.setattr(script, 'getpass', Mock(return_value=''))


def test_safe_preview_reuses_sanitizer(monkeypatch, capsys):
    raw = 'PRIVATE_HEADER\nSkills:\nPython\nCITY_TOKEN\ncontact@example.invalid\nProfessional experience:\n8 years pharmaceutical research'
    reader = Mock(return_value=raw)
    monkeypatch.setattr(script.Path, 'read_text', reader)
    monkeypatch.setattr(script, 'getpass', Mock(side_effect=['CITY_TOKEN', '']))
    spy = Mock(wraps=resume_privacy.preview_resume)
    monkeypatch.setattr(script, 'preview_resume', spy)
    assert script.main(['private_resumes/input.txt', '--preview']) == 0
    spy.assert_called_once_with(raw, identifiers=['CITY_TOKEN'])
    out = capsys.readouterr().out
    assert 'Python' in out and '8 years pharmaceutical research' in out
    assert 'Location: Delaware, USA' in out
    assert all(value not in out for value in ['PRIVATE_HEADER', 'CITY_TOKEN', 'contact@example.invalid'])
    assert 'may miss identifiers' in out and 'NOT approved' in out


@pytest.mark.parametrize('args', [[], ['input.txt']])
def test_no_flag_no_read_or_preview(monkeypatch, capsys, args):
    reader = Mock()
    monkeypatch.setattr(script.Path, 'read_text', reader)
    assert script.main(args) == 0
    reader.assert_not_called()
    script.getpass.assert_not_called()
    assert 'Location:' not in capsys.readouterr().out


@pytest.mark.parametrize('error', [FileNotFoundError('PRIVATE'), UnicodeError('PRIVATE'), PermissionError('PRIVATE')])
def test_read_failure_generic(monkeypatch, capsys, error):
    monkeypatch.setattr(script.Path, 'read_text', Mock(side_effect=error))
    assert script.main(['input.txt', '--preview']) == 1
    captured = capsys.readouterr()
    assert 'PRIVATE' not in captured.out + captured.err


@pytest.mark.parametrize('raw', ['', '  ', '%PDF synthetic', '\n%PDF synthetic', 'Skills:\nPython\x00', 'Skills:\nPython\x1b[31m'])
def test_malformed_text_not_displayed(monkeypatch, capsys, raw):
    monkeypatch.setattr(script.Path, 'read_text', Mock(return_value=raw))
    assert script.main(['input.txt', '--preview']) == 1
    assert capsys.readouterr().out == ''


def test_sanitizer_failure_no_raw_leak(monkeypatch, capsys):
    monkeypatch.setattr(script.Path, 'read_text', Mock(return_value='PRIVATE_TEXT'))
    monkeypatch.setattr(script, 'preview_resume', Mock(side_effect=RuntimeError('PRIVATE_TEXT')))
    assert script.main(['input.txt', '--preview']) == 1
    output = capsys.readouterr()
    assert 'PRIVATE_TEXT' not in output.out + output.err


def test_pdf_path_rejected_before_read(monkeypatch):
    reader = Mock()
    monkeypatch.setattr(script.Path, 'read_text', reader)
    assert script.main(['input.pdf', '--preview']) == 1
    reader.assert_not_called()


def test_help_has_no_reads(monkeypatch, capsys):
    reader = Mock()
    monkeypatch.setattr(script.Path, 'read_text', reader)
    with pytest.raises(SystemExit) as result:
        script.main(['--help'])
    assert result.value.code == 0
    reader.assert_not_called()
    assert '--preview' in capsys.readouterr().out


def test_hidden_input_failure_blocks_preview(monkeypatch, capsys):
    monkeypatch.setattr(script.Path, 'read_text', Mock(return_value='Skills:\nPython'))
    monkeypatch.setattr(script, 'getpass', Mock(side_effect=EOFError))
    assert script.main(['input.txt', '--preview']) == 1
    assert 'Python' not in capsys.readouterr().out


def test_insufficient_surviving_content_reports_specific_error_without_leaking(monkeypatch, capsys):
    # Mirrors a real extraction artifact: Skills/Experience headers merged onto
    # the same line as their content (never recognized by the exact-line
    # allowlist), so only Qualifications survives with one content line; an
    # identifier matching that last line removes it too, dropping the
    # sanitized output below the 3-line floor. (Education/Professional
    # experience/Publications are identifier-exempt as of Phase 7G.5G, so this
    # uses Qualifications, which remains identifier-sensitive.)
    raw = (
        'HEADER_TOKEN\n'
        'Skills Python SQL merged-with-header-content\n'
        'Professional Experience 8 years merged-with-header-content\n'
        'Qualifications:\n'
        'PhD CITY_TOKEN University\n'
    )
    monkeypatch.setattr(script.Path, 'read_text', Mock(return_value=raw))
    monkeypatch.setattr(script, 'getpass', Mock(side_effect=['CITY_TOKEN', '']))
    assert script.main(['input.txt', '--preview']) == 1
    captured = capsys.readouterr()
    assert 'Location:' not in captured.out
    assert 'too little content survived privacy sanitization' in captured.err
    assert 'CITY_TOKEN' not in captured.err
    assert 'PhD' not in captured.err
    assert 'HEADER_TOKEN' not in captured.err


def test_other_failures_keep_original_generic_message(monkeypatch, capsys):
    monkeypatch.setattr(script.Path, 'read_text', Mock(side_effect=FileNotFoundError('PRIVATE')))
    assert script.main(['input.txt', '--preview']) == 1
    captured = capsys.readouterr()
    assert captured.err.strip() == (
        'Unable to prepare a local preview. Check the text file and retry. No content approved.'
    )
