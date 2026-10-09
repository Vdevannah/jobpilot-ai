"""Tests for the local-only resume-selection CLI demo (Phase 7G.5I).

Fictional synthetic data only; no network, no credentials, no private files.
"""
import pytest

from scripts import demo_resume_selection as script
from src.ai.orchestrator import JobPilotOrchestrator
from src.ai.schemas import JobAnalysis


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Network or credential access is forbidden in the demo')
    monkeypatch.setattr('socket.socket', blocked)
    monkeypatch.setattr('os.getenv', blocked)


# --- all three built-in examples ---

@pytest.mark.parametrize('example,expected_variant', [
    ('medchem', 'pharma'),
    ('data_engineer', 'data'),
    ('scientific_ai', 'scientific_ai'),
])
def test_builtin_example_recommends_expected_variant(capsys, example, expected_variant):
    assert script.main(['--example', example]) == 0
    out = capsys.readouterr().out
    assert f'Recommended variant: {expected_variant}' in out
    assert '=== Resume variant rankings ===' in out
    assert 'pharma: score' in out and 'data: score' in out and 'scientific_ai: score' in out
    assert 'requires_human_review=True status=pending_review' in out


def test_all_builtin_examples_cover_all_three_keys():
    assert set(script.EXAMPLES) == {'medchem', 'data_engineer', 'scientific_ai'}


# --- ties ---

def test_ambiguous_job_reports_tie_without_single_recommendation(capsys):
    ambiguous = JobAnalysis(
        required_skills=['Python'], preferred_skills=[], minimum_experience_years=None,
        job_track='unknown', summary='Fictional ambiguous role requiring only Python.',
    )
    report = script.run_demo(script._FixedJobAgent(ambiguous), 'Fictional ambiguous job')
    assert report.recommendation.recommended_variant is None
    assert set(report.recommendation.tied_variants) == {'data', 'scientific_ai'}
    text = script.format_report(report)
    assert 'Tied variants, no single recommendation: data, scientific_ai' in text
    assert 'Recommended variant:' not in text
    assert '(tied)' in text


# --- invalid input ---

def test_no_arguments_runs_nothing(capsys):
    assert script.main([]) == 0
    out = capsys.readouterr().out
    assert 'No demo run' in out
    assert 'Job requirements' not in out


def test_unknown_example_rejected_by_argparse():
    with pytest.raises(SystemExit) as excinfo:
        script.main(['--example', 'bogus'])
    assert excinfo.value.code == 2


def test_example_and_job_description_are_mutually_exclusive():
    with pytest.raises(SystemExit) as excinfo:
        script.main(['--example', 'medchem', '--job-description', 'Fictional text'])
    assert excinfo.value.code == 2


@pytest.mark.parametrize('blank', ['', '   ', '\n\t'])
def test_blank_job_description_rejected(capsys, blank):
    assert script.main(['--job-description', blank]) == 1
    captured = capsys.readouterr()
    assert 'must not be empty or blank' in captured.err


def test_help_exits_cleanly_without_running_anything(capsys):
    with pytest.raises(SystemExit) as excinfo:
        script.main(['--help'])
    assert excinfo.value.code == 0
    assert '--example' in capsys.readouterr().out


# --- custom job-description path reuses the existing mock pipeline ---

def test_custom_job_description_uses_mock_llm_client_and_warns(capsys):
    assert script.main(['--job-description', 'Fictional custom role text']) == 0
    out = capsys.readouterr().out
    assert "NOTE: mock mode returns MockLLMClient's fixed sample job data" in out
    assert 'Recommended variant: data' in out  # MockLLMClient's fixed data-track sample


# --- offline / no network, no credentials, no OpenAI client ---

def test_source_never_imports_openai_or_requests():
    from pathlib import Path
    source = Path(script.__file__).read_text()
    for forbidden in ('import requests', 'import openai', 'from openai', 'OpenAIJobClient', 'OpenAIResumeClient'):
        assert forbidden not in source


def test_analysis_mode_is_always_mock(capsys):
    script.main(['--example', 'medchem'])
    report = script.run_demo(script._FixedJobAgent(script.EXAMPLES['medchem'][1]), 'x')
    assert report.analysis_mode == 'mock'


# --- never prints private resume text; resume variants are fictional structured data ---

def test_no_resume_summary_text_printed(capsys):
    script.main(['--example', 'data_engineer'])
    out = capsys.readouterr().out
    for variant in script.FICTIONAL_VARIANTS.values():
        assert variant.summary not in out


def test_resume_research_critic_agents_are_never_touched():
    # run_demo() builds the orchestrator with None for resume/research/critic
    # agents; this only succeeds if rank_resumes_for_job() never calls them.
    orchestrator = JobPilotOrchestrator(
        script._FixedJobAgent(script.EXAMPLES['medchem'][1]), None, None, None,
        analysis_mode='mock',
    )
    report = orchestrator.rank_resumes_for_job('x', script.FICTIONAL_VARIANTS)
    assert report.recommendation.recommended_variant == 'pharma'
