import pytest

from src.ai.agents.critic_agent import CriticAgent
from src.ai.client import MockLLMClient, MockResumeLLMClient
from src.ai.schemas import CriticReport, JobAnalysis, ResumeAnalysis


@pytest.fixture
def job():
    return JobAnalysis(
        required_skills=["Python"], preferred_skills=[],
        minimum_experience_years=3, job_track="data", summary="Data role.",
    )


@pytest.fixture
def resume():
    return ResumeAnalysis(
        skills=[" python "], professional_experience_years={"data": 3.0, "pharma": 8.0},
        domains=[], education=["PhD", "Data training program"], summary="Candidate analysis.",
    )


def test_sufficient_structured_evidence(job, resume):
    report = CriticAgent().analyze(job, resume)
    assert isinstance(report, CriticReport)
    assert report.warnings == []
    assert not report.requires_human_review
    assert "preliminary assessment" in report.summary


@pytest.mark.parametrize("experience", [{}, {"pharma": 8.0}])
def test_missing_experience_is_not_zero_or_education(job, resume, experience):
    resume.professional_experience_years = experience
    report = CriticAgent().analyze(job, resume)
    assert report.requires_human_review
    assert any("data is missing" in warning for warning in report.warnings)
    assert not any("Experience gap" in warning for warning in report.warnings)


def test_missing_job_requirement(job, resume):
    job.minimum_experience_years = None
    report = CriticAgent().analyze(job, resume)
    assert report.requires_human_review
    assert "unspecified" in report.warnings[0]


def test_unknown_track_does_not_combine_experience(job, resume):
    job.job_track = "unknown"
    report = CriticAgent().analyze(job, resume)
    assert report.requires_human_review
    assert any("track is unknown" in warning for warning in report.warnings)
    assert not any("Experience gap" in warning for warning in report.warnings)


@pytest.mark.parametrize("track,years,gap", [("data", 1.0, True), ("data", 0.0, True), ("pharma", 8.0, False)])
def test_track_specific_experience_is_preserved(job, resume, track, years, gap):
    job.job_track = track
    resume.professional_experience_years = {"data": 1.0, "pharma": 8.0}
    resume.professional_experience_years[track] = years
    before = resume.model_dump()
    report = CriticAgent().analyze(job, resume)
    assert report.requires_human_review is gap
    assert any("Experience gap" in warning for warning in report.warnings) is gap
    assert resume.model_dump() == before


def test_explicit_zero_meets_zero_requirement(job, resume):
    job.minimum_experience_years = 0
    resume.professional_experience_years = {"data": 0.0}
    assert not CriticAgent().analyze(job, resume).requires_human_review


@pytest.mark.parametrize("years", [-1.0, float("nan"), float("inf")])
def test_invalid_candidate_experience_requires_review(job, resume, years):
    resume.professional_experience_years["data"] = years
    report = CriticAgent().analyze(job, resume)
    assert report.requires_human_review
    assert any("experience for data is invalid" in warning for warning in report.warnings)


def test_invalid_job_experience_requires_review(job, resume):
    job.minimum_experience_years = -1
    assert CriticAgent().analyze(job, resume).requires_human_review


@pytest.mark.parametrize("skills", [[], [" "], ["sql"]])
def test_missing_or_unsupported_job_skills_require_review(job, resume, skills):
    job.required_skills = skills
    assert CriticAgent().analyze(job, resume).requires_human_review


def test_missing_candidate_skills_requires_review(job, resume):
    resume.skills = []
    report = CriticAgent().analyze(job, resume)
    assert report.requires_human_review
    assert "Candidate skill evidence is missing." in report.warnings


def test_sample_data_cannot_support_real_recommendation():
    job = MockLLMClient().analyze_job("Job")
    resume = MockResumeLLMClient().analyze_resume("Resume")
    report = CriticAgent().analyze(job, resume)
    assert report.requires_human_review
    assert any("mock or sample" in warning for warning in report.warnings)


@pytest.mark.parametrize('left,right', [
    ('SAR', 'structure-activity relationships'),
    ('structure activity relationship', 'SAR analysis'),
    ('PROTACs', 'proteolysis-targeting chimeras'),
    ('proteolysis targeting chimera', 'PROTACs'),
    ('TPD', 'targeted protein degradation'),
    ('targeted protein degradation', 'TPD'),
    ('Structure-Based Drug Design', 'expertise in structure based drug design'),
])
def test_explicit_skill_equivalences(job, resume, left, right):
    job.required_skills = [left]
    resume.skills = [right]
    assert CriticAgent().analyze(job, resume).warnings == []


def test_original_live_qualification_false_warnings(job, resume):
    job.job_track = 'pharma'
    job.minimum_experience_years = 8
    job.required_skills = ['PhD in Organic Chemistry', '8 years pharmaceutical experience',
                           'SAR', 'PROTACs', 'small-molecule drug discovery',
                           'structure-based drug design']
    resume.education = ['Ph.D. in Organic Chemistry']
    resume.skills = ['structure-activity relationship', 'proteolysis-targeting chimeras',
                     'medicinal chemistry']
    report = CriticAgent().analyze(job, resume)
    assert report.warnings == [
        'Required skills not evidenced in the resume: small-molecule drug discovery, structure-based drug design.'
    ]
    assert report.requires_human_review


@pytest.mark.parametrize('education,missing', [
    (['PhD in Organic Chemistry'], False), (['PhD in Physics'], True), ([], True),
])
def test_explicit_summary_education(job, resume, education, missing):
    job.summary = 'Required education: PhD in Organic Chemistry. Research role.'
    resume.education = education
    report = CriticAgent().analyze(job, resume)
    assert any('Required education' in warning for warning in report.warnings) is missing


def test_preferred_degree_is_not_required(job, resume):
    job.summary = 'Preferred education: PhD in Organic Chemistry.'
    resume.education = []
    assert CriticAgent().analyze(job, resume).warnings == []


def test_skill_text_cannot_supply_professional_years(job, resume):
    job.required_skills = ['Python', '3 years data experience']
    resume.professional_experience_years = {'pharma': 8.0}
    resume.skills.append('3 years data experience')
    report = CriticAgent().analyze(job, resume)
    assert any('data is missing' in warning for warning in report.warnings)
    assert not any('Required skills not evidenced' in warning for warning in report.warnings)


def test_unstructured_experience_is_not_inferred(job, resume):
    job.minimum_experience_years = None
    job.required_skills = ['Python', '3 years data experience']
    report = CriticAgent().analyze(job, resume)
    assert any('insufficient evidence' in warning for warning in report.warnings)
