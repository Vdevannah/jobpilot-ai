"""Phase 7G.5H: integration tests for ranking resume variants after job analysis.

Reuses the existing, unmodified resume_selector.recommend_resume() through
JobPilotOrchestrator.rank_resumes_for_job(). Fictional synthetic data only;
no real resumes, no network access, no credential access.
"""
from unittest.mock import Mock

import pytest

from src.ai.agents.critic_agent import CriticAgent
from src.ai.agents.job_agent import JobAnalysisAgent
from src.ai.agents.research_agent import ResearchAgent
from src.ai.agents.resume_agent import ResumeAnalysisAgent
from src.ai.orchestrator import JobPilotOrchestrator, ResumeSelectionReport, create_workflow
from src.ai.schemas import JobAnalysis, ResumeAnalysis


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Network or credential access is forbidden in resume-selection tests')
    monkeypatch.setattr('socket.socket', blocked)


def job(skills=(), preferred=(), track='data', years=None, summary='Synthetic fictional job'):
    return JobAnalysis(required_skills=list(skills), preferred_skills=list(preferred),
                       minimum_experience_years=years, job_track=track, summary=summary)


def resume(skills=(), years=None, domains=(), education=()):
    return ResumeAnalysis(skills=list(skills), professional_experience_years=years or {},
                          domains=list(domains), education=list(education),
                          summary='Synthetic fictional resume fixture')


@pytest.fixture
def variants():
    return {
        'pharma': resume(['SAR', 'PROTACs', 'medicinal chemistry'], {'pharma': 8.0},
                          domains=['pharma']),
        'data': resume(['Python', 'SQL', 'data engineering'], {'data': 3.0}, domains=['data']),
        'scientific_ai': resume(['Python', 'cheminformatics', 'RDKit', 'machine learning']),
    }


@pytest.fixture
def job_agent_mock():
    return Mock(spec=JobAnalysisAgent)


@pytest.fixture
def orchestrator(job_agent_mock):
    return JobPilotOrchestrator(
        job_agent_mock,
        Mock(spec=ResumeAnalysisAgent),
        Mock(spec=ResearchAgent),
        Mock(spec=CriticAgent),
        analysis_mode='mock',
    )


# 1. Pharma job recommends the pharma resume.
def test_pharma_job_recommends_pharma_resume(orchestrator, job_agent_mock, variants):
    job_agent_mock.analyze.return_value = job(
        ['structure-activity relationship', 'proteolysis-targeting chimeras'], track='pharma',
        summary='Fictional Principal Scientist, medicinal chemistry',
    )
    report = orchestrator.rank_resumes_for_job('Fictional pharma job description', variants)
    assert isinstance(report, ResumeSelectionReport)
    assert report.recommendation.recommended_variant == 'pharma'
    assert len(report.recommendation.rankings) == 3


# 2. Data Engineering job recommends the data resume.
def test_data_job_recommends_data_resume(orchestrator, job_agent_mock, variants):
    job_agent_mock.analyze.return_value = job(
        ['Python', 'SQL', 'data engineering'], track='data', years=2,
        summary='Fictional Data Engineer role',
    )
    report = orchestrator.rank_resumes_for_job('Fictional data job description', variants)
    assert report.recommendation.recommended_variant == 'data'


# 3. Scientific AI / Cheminformatics job recommends the scientific_ai resume.
def test_scientific_ai_job_recommends_scientific_ai_resume(orchestrator, job_agent_mock, variants):
    job_agent_mock.analyze.return_value = job(
        ['cheminformatics', 'RDKit', 'machine learning'], track='unknown',
        summary='Fictional Scientific AI / Cheminformatics role',
    )
    report = orchestrator.rank_resumes_for_job('Fictional scientific AI job description', variants)
    assert report.recommendation.recommended_variant == 'scientific_ai'


# 4. Ambiguous job produces an explainable ranking with visible uncertainty.
def test_ambiguous_job_produces_explainable_uncertainty(orchestrator, job_agent_mock, variants):
    job_agent_mock.analyze.return_value = job(['Python'], track='unknown',
                                               summary='Fictional generic technical role')
    report = orchestrator.rank_resumes_for_job('Fictional ambiguous job description', variants)
    # Python is evidenced by both data and scientific_ai (not pharma): a
    # genuine tie, with an explicit explanation rather than a guessed winner.
    assert all(row.reasons for row in report.recommendation.rankings)
    assert set(report.recommendation.tied_variants) == {'data', 'scientific_ai'}
    assert report.recommendation.recommended_variant is None
    assert any('unknown' in limit.casefold()
               for row in report.recommendation.rankings for limit in row.limitations)


# 5. All three variants appear in the ranking regardless of outcome.
def test_all_three_variants_appear_in_ranking(orchestrator, job_agent_mock, variants):
    job_agent_mock.analyze.return_value = job(['Python'], track='data')
    report = orchestrator.rank_resumes_for_job('Fictional job description', variants)
    assert {row.variant for row in report.recommendation.rankings} == {'pharma', 'data', 'scientific_ai'}


# 6. Job discovery/analysis remains unchanged: identical regardless of which
# or how many resume variants are supplied, and independent of variant content.
def test_job_analysis_independent_of_resume_variants(orchestrator, job_agent_mock, variants):
    fixed_job = job(['Python'], track='data')
    job_agent_mock.analyze.return_value = fixed_job
    full = orchestrator.rank_resumes_for_job('Fictional job description', variants)
    partial = orchestrator.rank_resumes_for_job(
        'Fictional job description', {'data': variants['data']},
    )
    assert full.job_analysis == fixed_job == partial.job_analysis
    job_agent_mock.analyze.assert_called_with('Fictional job description')
    assert job_agent_mock.analyze.call_count == 2


# 7. No private resume text enters AI requests or logs: this method takes no
# resume text at all, and never constructs or calls a resume AI client.
def test_no_resume_text_or_client_touched(orchestrator, job_agent_mock, variants):
    job_agent_mock.analyze.return_value = job(['Python'], track='data')
    orchestrator.resume_agent.analyze = Mock(side_effect=AssertionError('must not be called'))
    report = orchestrator.rank_resumes_for_job('Fictional job description', variants)
    orchestrator.resume_agent.analyze.assert_not_called()
    assert isinstance(report, ResumeSelectionReport)


# 8. Human approval remains mandatory: every report requires review.
def test_human_review_mandatory(orchestrator, job_agent_mock, variants):
    job_agent_mock.analyze.return_value = job(['Python'], track='data')
    report = orchestrator.rank_resumes_for_job('Fictional job description', variants)
    assert report.requires_human_review is True
    assert report.status == 'pending_review'
    assert report.recommendation.requires_human_review is True
    assert report.recommendation.status == 'pending_review'


# 9. Existing mock and OpenAI-mode workflows keep functioning unchanged: the
# factory still builds a working orchestrator, run() is untouched (already
# exhaustively covered by test_orchestrator.py, which still passes in full),
# and the new selection method is available alongside it on the same object.
@pytest.mark.parametrize('mode', ['mock', 'openai'])
def test_create_workflow_unaffected_and_exposes_new_method(mode, monkeypatch):
    if mode == 'openai':
        monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
        monkeypatch.setattr('src.ai.openai_client.OpenAI', Mock())
    workflow = create_workflow(mode)
    assert isinstance(workflow, JobPilotOrchestrator)
    assert workflow.analysis_mode == mode
    assert callable(workflow.run)
    assert callable(workflow.rank_resumes_for_job)


# Orchestrator-level input validation and selector input validation compose cleanly.
@pytest.mark.parametrize('blank', ['', '  ', '\n\t'])
def test_blank_job_description_rejected_before_job_agent_call(orchestrator, job_agent_mock, variants, blank):
    with pytest.raises(ValueError):
        orchestrator.rank_resumes_for_job(blank, variants)
    job_agent_mock.analyze.assert_not_called()


def test_empty_variants_rejected_by_existing_selector_validation(orchestrator, job_agent_mock):
    job_agent_mock.analyze.return_value = job(['Python'], track='data')
    with pytest.raises(ValueError):
        orchestrator.rank_resumes_for_job('Fictional job description', {})


def test_conflicting_claims_and_candidate_profile_untouched(orchestrator, job_agent_mock):
    job_agent_mock.analyze.return_value = job(['Python'], track='data', years=3)
    conflicting = {
        'pharma': resume(['Python'], {'data': 8.0}),
        'data': resume(['Python'], {'data': 1.0}),
    }
    report = orchestrator.rank_resumes_for_job('Fictional job description', conflicting)
    assert any('Conflicting data' in text for text in report.recommendation.limitations)
    assert report.recommendation.recommended_variant is None
    # Scoring never inferred employment from education/projects/training;
    # reused selector limitations remain intact.
    assert any('No employment inferred' in limit
               for row in report.recommendation.rankings for limit in row.limitations)
