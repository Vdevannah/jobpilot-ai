"""Phase 7G.5J: scientific_ai job-track integration across critic and selector.

Fictional synthetic data only. Confirms the new track is additive: no
existing pharma/data classification, scoring, or approval behavior changes.
"""
import pytest

from src.ai.agents.critic_agent import CriticAgent
from src.ai.resume_selector import recommend_resume
from src.ai.schemas import JobAnalysis, ResumeAnalysis


def job(skills=(), preferred=(), track='data', years=None, summary='Synthetic fictional job'):
    return JobAnalysis(required_skills=list(skills), preferred_skills=list(preferred),
                       minimum_experience_years=years, job_track=track, summary=summary)


def resume(skills=(), years=None, domains=(), education=()):
    return ResumeAnalysis(skills=list(skills), professional_experience_years=years or {},
                          domains=list(domains), education=list(education),
                          summary='Synthetic fictional resume')


# --- schema accepts the new literal; old literals still work unchanged ---

@pytest.mark.parametrize('track', ['pharma', 'data', 'scientific_ai', 'unknown'])
def test_job_track_literal_accepts_all_four_values(track):
    assert job(track=track).job_track == track


def test_invalid_job_track_still_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        job(track='engineering')


# --- CriticAgent: advisory suggestion, never a silent reclassification ---

def test_critic_suggests_scientific_ai_only_when_unknown_and_evidence_present():
    scientific_job = job(
        skills=['cheminformatics', 'RDKit'], track='unknown',
        summary='Fictional Cheminformatics Scientist role.',
    )
    report = CriticAgent().analyze(scientific_job, resume(['Python']))
    assert any('Scientific AI / Cheminformatics' in w for w in report.warnings)
    assert scientific_job.job_track == 'unknown'  # never mutated


def test_critic_does_not_suggest_scientific_ai_for_ordinary_unknown_job():
    plain_job = job(skills=['Python'], track='unknown', summary='Fictional generic role.')
    report = CriticAgent().analyze(plain_job, resume(['Python']))
    assert not any('Scientific AI' in w for w in report.warnings)
    assert any('track is unknown' in w for w in report.warnings)


def test_critic_never_suggests_scientific_ai_for_already_confident_pharma():
    # Even if the text happens to look science-AI-ish, a confidently
    # classified pharma/data job is never second-guessed by the advisory check.
    confident_job = job(
        skills=['cheminformatics'], track='pharma', summary='Fictional pharma role.',
    )
    report = CriticAgent().analyze(confident_job, resume(['SAR'], {'pharma': 8.0}))
    assert not any('Scientific AI' in w for w in report.warnings)


def test_critic_conventional_medicinal_chemistry_unaffected():
    medchem_job = job(
        skills=['SAR', 'PROTACs'], track='pharma', years=5,
        summary='Fictional Principal Scientist, Medicinal Chemistry.',
    )
    report = CriticAgent().analyze(medchem_job, resume(['SAR', 'PROTACs'], {'pharma': 8.0}))
    # The resume fixture's own "fictional"/"synthetic" marker triggers the
    # pre-existing, unrelated mock/sample-data warning; what matters here is
    # that this phase introduces no new, unexpected warning.
    assert not any('Scientific AI' in w for w in report.warnings)
    assert not any('Experience gap' in w for w in report.warnings)
    assert not any('not evidenced' in w for w in report.warnings)


# --- resume_selector: scientific_ai track-specific experience/domain bonus ---

def test_selector_awards_scientific_ai_domain_and_experience_like_other_tracks():
    scientific_job = job(
        skills=['cheminformatics', 'RDKit'], track='scientific_ai', years=2,
        summary='Fictional Cheminformatics Scientist role.',
    )
    variants = {
        'scientific_ai': resume(['cheminformatics', 'RDKit'], {'scientific_ai': 3.0},
                                domains=['scientific_ai']),
        'pharma': resume(['SAR'], {'pharma': 8.0}),
        'data': resume(['Python', 'SQL'], {'data': 3.0}),
    }
    report = recommend_resume(scientific_job, variants)
    assert report.recommended_variant == 'scientific_ai'
    row = next(r for r in report.rankings if r.variant == 'scientific_ai')
    assert any('meets 2' in item for item in row.matched_evidence)
    assert any('Track domain' in item for item in row.matched_evidence)


def test_selector_flags_conflicting_scientific_ai_claims_like_pharma_data():
    ambiguous_job = job(skills=['cheminformatics'], track='scientific_ai')
    variants = {
        'data': resume(['cheminformatics'], {'scientific_ai': 2.0}),
        'scientific_ai': resume(['cheminformatics'], {'scientific_ai': 5.0}),
    }
    report = recommend_resume(ambiguous_job, variants)
    assert any('Conflicting scientific_ai' in text for text in report.limitations)
    assert report.recommended_variant is None


def test_selector_does_not_infer_scientific_ai_experience_from_projects_or_education():
    scientific_job = job(skills=['cheminformatics'], track='scientific_ai', years=3)
    variant = resume(
        skills=['cheminformatics'],
        years={},  # no professional_experience_years entry at all
        education=['PhD in Computational Chemistry (fictional)'],
    )
    report = recommend_resume(scientific_job, {'scientific_ai': variant})
    row = report.rankings[0]
    assert any('not evidenced, not assumed zero' in item for item in row.missing_evidence)
    assert any('No employment inferred' in limit for limit in row.limitations)


# --- existing pharma/data scoring is unchanged by this phase ---

def test_existing_pharma_scoring_unchanged():
    pharma_job = job(skills=['SAR', 'PROTACs'], track='pharma', years=5)
    variant = resume(['SAR', 'PROTACs'], {'pharma': 8.0}, domains=['pharma'])
    report = recommend_resume(pharma_job, {'pharma': variant})
    assert report.rankings[0].score == 11  # 4+4 skills, +2 experience, +1 domain


def test_existing_data_scoring_unchanged():
    data_job = job(skills=['Python', 'SQL'], track='data', years=2)
    variant = resume(['Python', 'SQL'], {'data': 3.0}, domains=['data'])
    report = recommend_resume(data_job, {'data': variant})
    assert report.rankings[0].score == 11  # 4+4 skills, +2 experience, +1 domain


def test_pharma_data_conflict_detection_unaffected_by_new_track():
    job_description = job(skills=['Python'], track='data', years=3)
    variants = {
        'pharma': resume(['Python'], {'data': 8.0}),
        'data': resume(['Python'], {'data': 1.0}),
    }
    report = recommend_resume(job_description, variants)
    assert [r.score for r in report.rankings] == [4, 4]
    assert any('Conflicting data' in text for text in report.limitations)
    assert report.recommended_variant is None
