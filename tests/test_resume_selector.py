from copy import deepcopy

import pytest

from src.ai.resume_selector import recommend_resume
from src.ai.schemas import JobAnalysis, ResumeAnalysis


def resume(skills=(), years=None, domains=(), education=()):
    return ResumeAnalysis(skills=list(skills), professional_experience_years=years or {},
                          domains=list(domains), education=list(education), summary='Synthetic fixture')


def job(skills=(), track='data', years=None, summary='Synthetic job'):
    return JobAnalysis(required_skills=list(skills), preferred_skills=[],
                       minimum_experience_years=years, job_track=track, summary=summary)


@pytest.fixture
def variants():
    return {
        'pharma': resume(['SAR', 'PROTACs', 'medicinal chemistry'], {'pharma': 8.0}),
        'data': resume(['Python', 'SQL', 'data engineering', 'business analysis']),
        'scientific_ai': resume(['Python', 'cheminformatics', 'machine learning']),
    }


@pytest.mark.parametrize('skills,track,winner', [
    (['structure-activity relationship', 'proteolysis-targeting chimeras'], 'pharma', 'pharma'),
    (['Python', 'SQL', 'data engineering'], 'data', 'data'),
    (['cheminformatics', 'machine learning', 'Python'], 'unknown', 'scientific_ai'),
])
def test_evidence_based_winner(variants, skills, track, winner):
    report = recommend_resume(job(skills, track), variants)
    assert report.recommended_variant == winner
    assert len(report.rankings) == 3
    assert report.requires_human_review and report.status == 'pending_review'
    assert report.rankings[0].matched_evidence
    assert report.rankings[0].reasons


@pytest.mark.parametrize('role', ['Data Scientist', 'Business Analyst', 'Python Developer', 'Data Analyst'])
def test_technology_roles_remain_stretch_opportunities(variants, role):
    report = recommend_resume(job(['Python', 'SQL'], years=3, summary=role), variants)
    assert report.recommended_variant == 'data'
    assert len(report.rankings) == 3
    assert any('not evidenced' in text for text in report.rankings[0].missing_evidence)


def test_pharma_years_never_transfer_to_data():
    report = recommend_resume(job(['Python'], years=3), {'data': resume(['Python'], {'pharma': 8.0})})
    assert report.rankings[0].score == 4
    assert any('not evidenced' in item for item in report.rankings[0].missing_evidence)


def test_conflicting_claims_not_merged():
    report = recommend_resume(job(['Python'], years=3), {
        'pharma': resume(['Python'], {'data': 8.0}),
        'data': resume(['Python'], {'data': 1.0}),
    })
    assert [r.score for r in report.rankings] == [4, 4]
    assert any('Conflicting data' in text for text in report.limitations)
    assert report.recommended_variant is None


def test_education_and_missing_skills_visible():
    report = recommend_resume(job(['SAR', 'structure-based drug design'], 'pharma',
                                 summary='Required education: PhD in Organic Chemistry.'), {
        'pharma': resume(['SAR'], education=['Ph.D. in Organic Chemistry']),
    })
    row = report.rankings[0]
    assert row.score == 6
    assert 'Required skill: structure based drug design' in row.missing_evidence
    assert any('Required education' in item for item in row.matched_evidence)


def test_stable_ties_independent_of_mapping_order():
    variants = {'scientific_ai': resume(['Python']), 'data': resume(['Python']), 'pharma': resume(['Python'])}
    report = recommend_resume(job(['Python']), variants)
    assert report == recommend_resume(job(['Python']), dict(reversed(list(variants.items()))))
    assert report.tied_variants == ['pharma', 'data', 'scientific_ai']
    assert report.recommended_variant is None
    assert not report.insufficient_evidence


def test_domain_only_evidence_cannot_claim_winner():
    report = recommend_resume(job(), {'data': resume(domains=['data engineering']), 'pharma': resume()})
    assert report.insufficient_evidence
    assert report.recommended_variant is None


def test_direct_evidence_beats_domain_and_name():
    report = recommend_resume(job(['Python']), {'pharma': resume(['Python']),
                                              'data': resume(domains=['data engineering', 'analytics'])})
    assert report.recommended_variant == 'pharma'


def test_preferred_skills_have_lower_weight_and_aliases_not_double_counted():
    analyzed = job(['SAR', 'structure-activity relationship'])
    analyzed.preferred_skills = ['SAR', 'SQL']
    report = recommend_resume(analyzed, {'data': resume(['SAR', 'SQL'])})
    assert report.rankings[0].score == 5


def test_input_models_unchanged(variants):
    analyzed = job(['Python'])
    before = deepcopy((analyzed, variants))
    recommend_resume(analyzed, variants)
    assert (analyzed, variants) == before


@pytest.mark.parametrize('variants', [{}, {'other': resume()}])
def test_invalid_variant_mapping_rejected(variants):
    with pytest.raises(ValueError):
        recommend_resume(job(), variants)
