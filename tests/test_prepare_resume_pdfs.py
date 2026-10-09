import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts import prepare_resume_pdfs as script


@pytest.fixture(autouse=True)
def local_only(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Forbidden network, credential, or OpenAI operation')
    monkeypatch.setattr('socket.socket', forbidden)
    monkeypatch.setattr('os.getenv', forbidden)


def _write_config(path: Path, pdf_paths: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: str(v) for k, v in pdf_paths.items()}))


def _fictional_pdfs(tmp_path: Path) -> dict:
    desktop = tmp_path / 'Desktop'
    desktop.mkdir(exist_ok=True)
    paths = {}
    for variant, filename in (
        ('pharma', 'fictional_pharma_resume.pdf'),
        ('data', 'fictional_data_resume.pdf'),
        ('scientific_ai', 'fictional_scientific_ai_resume.pdf'),
    ):
        pdf = desktop / filename
        pdf.write_bytes(b'%PDF-synthetic-placeholder')
        paths[variant] = pdf
    return paths


def test_no_network_or_openai_imports():
    source = Path(script.__file__).read_text()
    for forbidden in ('import requests', 'import openai', 'from openai', 'import socket'):
        assert forbidden not in source


def test_example_config_exists_and_uses_only_fictional_paths():
    example = script.EXAMPLE_CONFIG_PATH.read_text()
    data = json.loads(example)
    assert set(data) >= {'pharma', 'data', 'scientific_ai'}
    for forbidden in ('devannah', 'vijayarajan', 'vijayviveka'):
        assert forbidden not in example.casefold()


# --- load_pdf_sources: configuration loading and validation ---

def test_load_pdf_sources_success(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    pdfs = _fictional_pdfs(tmp_path)
    config_path = tmp_path / 'private_resumes' / 'pdf_sources.json'
    _write_config(config_path, pdfs)
    resolved = script.load_pdf_sources(config_path)
    assert set(resolved) == {'pharma', 'data', 'scientific_ai'}
    assert all(path.is_file() for path in resolved.values())


def test_load_pdf_sources_refuses_when_not_gitignored(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'is_gitignored', lambda path: False)
    config_path = tmp_path / 'pdf_sources.json'
    _write_config(config_path, _fictional_pdfs(tmp_path))
    with pytest.raises(script.PdfPrepError, match='git-ignored'):
        script.load_pdf_sources(config_path)


def test_load_pdf_sources_missing_file_gives_helpful_message(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    config_path = tmp_path / 'private_resumes' / 'pdf_sources.json'
    with pytest.raises(script.PdfPrepError) as excinfo:
        script.load_pdf_sources(config_path)
    assert 'pdf_sources.example.json' in str(excinfo.value)


def test_load_pdf_sources_invalid_json_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    config_path = tmp_path / 'pdf_sources.json'
    config_path.write_text('not valid json {{{')
    with pytest.raises(script.PdfPrepError, match='not valid JSON'):
        script.load_pdf_sources(config_path)


def test_load_pdf_sources_missing_variant_named_without_leaking_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    pdfs = _fictional_pdfs(tmp_path)
    del pdfs['data']
    config_path = tmp_path / 'pdf_sources.json'
    _write_config(config_path, pdfs)
    with pytest.raises(script.PdfPrepError) as excinfo:
        script.load_pdf_sources(config_path)
    assert 'data' in str(excinfo.value)
    assert 'pharma' not in str(excinfo.value)
    assert 'scientific_ai' not in str(excinfo.value)


def test_load_pdf_sources_nonexistent_path_reported_without_leaking_path(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    pdfs = _fictional_pdfs(tmp_path)
    pdfs['pharma'] = tmp_path / 'Desktop' / 'does_not_exist_fictional.pdf'
    config_path = tmp_path / 'pdf_sources.json'
    _write_config(config_path, pdfs)
    with pytest.raises(script.PdfPrepError) as excinfo:
        script.load_pdf_sources(config_path)
    assert 'pharma' in str(excinfo.value)
    assert 'does_not_exist_fictional.pdf' not in str(excinfo.value)
    assert str(tmp_path) not in str(excinfo.value)


def test_load_pdf_sources_rejects_non_pdf_extension(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    pdfs = _fictional_pdfs(tmp_path)
    not_a_pdf = tmp_path / 'Desktop' / 'fictional_resume.txt'
    not_a_pdf.write_text('fictional text, not a pdf')
    pdfs['data'] = not_a_pdf
    config_path = tmp_path / 'pdf_sources.json'
    _write_config(config_path, pdfs)
    with pytest.raises(script.PdfPrepError) as excinfo:
        script.load_pdf_sources(config_path)
    assert 'data' in str(excinfo.value)
    assert 'fictional_resume.txt' not in str(excinfo.value)


def test_load_pdf_sources_expands_user_home(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    monkeypatch.setenv('HOME', str(tmp_path))
    pdfs = _fictional_pdfs(tmp_path)
    config_path = tmp_path / 'pdf_sources.json'
    _write_config(config_path, {k: f'~/Desktop/{v.name}' for k, v in pdfs.items()})
    resolved = script.load_pdf_sources(config_path)
    assert resolved['pharma'] == pdfs['pharma']


# --- extract_text_from_pdf: unchanged behavior, fictional fixtures ---

class _FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class _FakeReader:
    def __init__(self, pages_text, is_encrypted=False, decrypt_result=0):
        self.pages = [_FakePage(t) for t in pages_text]
        self.is_encrypted = is_encrypted
        self._decrypt_result = decrypt_result

    def decrypt(self, password):
        return self._decrypt_result


def _fake_pypdf_module(reader_factory):
    module = Mock()
    module.PdfReader = reader_factory
    return module


def test_extract_text_success(monkeypatch, tmp_path):
    pdf_path = tmp_path / 'fictional_sample.pdf'
    pdf_path.write_bytes(b'%PDF-synthetic-placeholder')
    fake_reader = _FakeReader(['Skills: Example, Testing', 'Education: Example University'])
    monkeypatch.setattr(script, '_load_pypdf', lambda: _fake_pypdf_module(lambda _path: fake_reader))
    text, report = script.extract_text_from_pdf(pdf_path)
    assert 'Example, Testing' in text
    assert 'Example University' in text
    assert isinstance(report, script.RepairReport)
    assert report.mapped_headings == ['Skills', 'Education']


def test_extract_text_rejects_encrypted(monkeypatch, tmp_path):
    pdf_path = tmp_path / 'fictional_sample.pdf'
    pdf_path.write_bytes(b'%PDF-synthetic-placeholder')
    fake_reader = _FakeReader(['irrelevant'], is_encrypted=True, decrypt_result=0)
    monkeypatch.setattr(script, '_load_pypdf', lambda: _fake_pypdf_module(lambda _path: fake_reader))
    with pytest.raises(script.PdfPrepError) as excinfo:
        script.extract_text_from_pdf(pdf_path)
    assert 'Encrypted' in str(excinfo.value)
    assert 'irrelevant' not in str(excinfo.value)


def test_extract_text_rejects_unreadable(monkeypatch, tmp_path):
    pdf_path = tmp_path / 'fictional_sample.pdf'
    pdf_path.write_bytes(b'not-a-real-pdf')

    def _raise(_path):
        raise RuntimeError('PRIVATE_PARSER_DETAIL')

    monkeypatch.setattr(script, '_load_pypdf', lambda: _fake_pypdf_module(_raise))
    with pytest.raises(script.PdfPrepError) as excinfo:
        script.extract_text_from_pdf(pdf_path)
    assert 'Unreadable PDF' in str(excinfo.value)
    assert 'PRIVATE_PARSER_DETAIL' not in str(excinfo.value)


def test_extract_text_rejects_empty_image_only(monkeypatch, tmp_path):
    pdf_path = tmp_path / 'fictional_sample.pdf'
    pdf_path.write_bytes(b'%PDF-synthetic-placeholder')
    fake_reader = _FakeReader(['', '   '])
    monkeypatch.setattr(script, '_load_pypdf', lambda: _fake_pypdf_module(lambda _path: fake_reader))
    with pytest.raises(script.PdfPrepError) as excinfo:
        script.extract_text_from_pdf(pdf_path)
    assert 'image-only' in str(excinfo.value).lower()


def test_missing_dependency_reported_without_installing(monkeypatch):
    install = Mock()
    monkeypatch.setattr(script.importlib.util, 'find_spec', lambda name: None)
    monkeypatch.setattr('subprocess.run', install)
    with pytest.raises(script.PdfPrepError) as excinfo:
        script._load_pypdf()
    assert 'pypdf' in str(excinfo.value)
    install.assert_not_called()


# --- git-ignore protection ---

def test_real_private_resumes_dir_is_gitignored():
    target = script.PROJECT_ROOT / 'private_resumes' / 'pharma.txt'
    assert script.is_gitignored(target) is True


def test_real_pdf_sources_config_path_is_gitignored():
    assert script.is_gitignored(script.CONFIG_PATH) is True


def test_tracked_file_is_not_gitignored():
    target = script.PROJECT_ROOT / 'requirements.txt'
    assert script.is_gitignored(target) is False


def test_example_config_is_tracked_not_gitignored():
    assert script.is_gitignored(script.EXAMPLE_CONFIG_PATH) is False


# --- write_private_resume: unchanged safety behavior ---

def test_write_rejects_unsafe_key(tmp_path):
    with pytest.raises(script.PdfPrepError):
        script.write_private_resume(
            '../../etc/passwd', 'text', output_dir=tmp_path / 'private_resumes', overwrite=True,
        )


def test_write_refuses_when_not_gitignored(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'is_gitignored', lambda path: False)
    with pytest.raises(script.PdfPrepError):
        script.write_private_resume(
            'pharma', 'Skills: Example', output_dir=tmp_path / 'private_resumes', overwrite=True,
        )


def test_write_creates_file_with_restrictive_permissions(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    output_dir = tmp_path / 'private_resumes'
    target = script.write_private_resume(
        'pharma', 'Skills: Example', output_dir=output_dir, overwrite=False,
    )
    assert target == output_dir / 'pharma.txt'
    assert target.read_text() == 'Skills: Example'
    mode = target.stat().st_mode & 0o777
    assert mode == 0o600


def test_write_does_not_overwrite_without_approval(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    output_dir = tmp_path / 'private_resumes'
    script.write_private_resume('pharma', 'ORIGINAL', output_dir=output_dir, overwrite=False)
    with pytest.raises(script.PdfPrepError):
        script.write_private_resume('pharma', 'REPLACEMENT', output_dir=output_dir, overwrite=False)
    assert (output_dir / 'pharma.txt').read_text() == 'ORIGINAL'


def test_write_overwrite_flag_allows_replacement(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    output_dir = tmp_path / 'private_resumes'
    script.write_private_resume('pharma', 'ORIGINAL', output_dir=output_dir, overwrite=False)
    script.write_private_resume('pharma', 'REPLACEMENT', output_dir=output_dir, overwrite=True)
    assert (output_dir / 'pharma.txt').read_text() == 'REPLACEMENT'


# --- main(): end-to-end with a fictional, temporary configuration ---

def test_main_happy_path_prints_commands_not_content(monkeypatch, tmp_path, capsys):
    pdfs = _fictional_pdfs(tmp_path)
    config_path = tmp_path / 'private_resumes' / 'pdf_sources.json'
    _write_config(config_path, pdfs)
    monkeypatch.setattr(script, 'CONFIG_PATH', config_path)
    monkeypatch.setattr(script, 'OUTPUT_DIR', tmp_path / 'private_resumes')
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    monkeypatch.setattr(
        script, 'extract_text_from_pdf',
        lambda path: ('Skills: Example\nEducation: Example University', script.RepairReport()),
    )
    assert script.main([]) == 0
    out = capsys.readouterr().out
    assert 'Skills: Example' not in out
    assert 'fictional_pharma_resume.pdf' not in out
    for key in ('pharma', 'data', 'scientific_ai'):
        assert f'preview_resume.py private_resumes/{key}.txt --preview' in out
    assert (tmp_path / 'private_resumes' / 'pharma.txt').exists()


def test_main_reports_heading_repair_categories_without_content(monkeypatch, tmp_path, capsys):
    pdfs = _fictional_pdfs(tmp_path)
    config_path = tmp_path / 'private_resumes' / 'pdf_sources.json'
    _write_config(config_path, pdfs)
    monkeypatch.setattr(script, 'CONFIG_PATH', config_path)
    monkeypatch.setattr(script, 'OUTPUT_DIR', tmp_path / 'private_resumes')
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    report = script.RepairReport(mapped_headings=['Skills'],
                                  unmapped_headings=['Publications and Patents'], ambiguous_count=1)
    monkeypatch.setattr(script, 'extract_text_from_pdf', lambda path: ('Skills\nFICTIONAL_CONTENT', report))
    assert script.main([]) == 0
    out = capsys.readouterr().out
    assert 'FICTIONAL_CONTENT' not in out
    assert 'heading repair recognized: Skills' in out
    assert 'manual review recommended: 1 unmapped heading(s), 1 ambiguous line(s)' in out


def test_main_missing_config_stops_before_any_write(monkeypatch, tmp_path, capsys):
    config_path = tmp_path / 'private_resumes' / 'pdf_sources.json'
    monkeypatch.setattr(script, 'CONFIG_PATH', config_path)
    output_dir = tmp_path / 'private_resumes'
    monkeypatch.setattr(script, 'OUTPUT_DIR', output_dir)
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    writer = Mock()
    monkeypatch.setattr(script, 'write_private_resume', writer)
    assert script.main([]) == 1
    writer.assert_not_called()
    err = capsys.readouterr().err
    assert 'pdf_sources.example.json' in err


def test_main_extraction_failure_is_reported_without_raw_text(monkeypatch, tmp_path, capsys):
    pdfs = _fictional_pdfs(tmp_path)
    config_path = tmp_path / 'private_resumes' / 'pdf_sources.json'
    _write_config(config_path, pdfs)
    monkeypatch.setattr(script, 'CONFIG_PATH', config_path)
    monkeypatch.setattr(script, 'OUTPUT_DIR', tmp_path / 'private_resumes')
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    monkeypatch.setattr(
        script, 'extract_text_from_pdf',
        Mock(side_effect=script.PdfPrepError('Encrypted PDF cannot be opened locally without a password.')),
    )
    assert script.main([]) == 1
    captured = capsys.readouterr()
    assert 'PRIVATE' not in captured.out + captured.err
    assert 'fictional_pharma_resume.pdf' not in captured.out + captured.err


def test_main_never_prints_configured_paths(monkeypatch, tmp_path, capsys):
    pdfs = _fictional_pdfs(tmp_path)
    config_path = tmp_path / 'private_resumes' / 'pdf_sources.json'
    _write_config(config_path, pdfs)
    monkeypatch.setattr(script, 'CONFIG_PATH', config_path)
    monkeypatch.setattr(script, 'OUTPUT_DIR', tmp_path / 'private_resumes')
    monkeypatch.setattr(script, 'is_gitignored', lambda path: True)
    monkeypatch.setattr(
        script, 'extract_text_from_pdf',
        lambda path: ('Skills: Example', script.RepairReport()),
    )
    script.main([])
    captured = capsys.readouterr()
    for pdf_path in pdfs.values():
        assert str(pdf_path) not in captured.out + captured.err
        assert pdf_path.name not in captured.out + captured.err
    assert str(tmp_path) not in captured.out + captured.err


def test_approval_boundary_untouched():
    from src.ai import resume_privacy
    assert not hasattr(script, 'approve_resume')
    assert not hasattr(script, 'ApprovedResumeText')
    with pytest.raises(resume_privacy.ResumePrivacyError):
        resume_privacy.approve_resume('Location: Delaware, USA\nSkills:\nPython', confirmed=False)
