import pytest

from src.ai.agents.research_agent import ResearchAgent
from src.ai.schemas import JobAnalysis, ResearchReport


@pytest.fixture
def job():
    return JobAnalysis(
        required_skills=["python"], preferred_skills=[],
        minimum_experience_years=3, job_track="data", summary="Data role.",
    )


def test_complete_job_requires_no_research(job):
    report = ResearchAgent().analyze(job)
    assert isinstance(report, ResearchReport)
    assert report.missing_information == []
    assert report.research_questions == []
    assert "No external research" in report.summary


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("minimum_experience_years", None, "unspecified"),
        ("minimum_experience_years", -1, "invalid"),
        ("job_track", "unknown", "unknown"),
        ("required_skills", [], "absent or unclear"),
        ("required_skills", [" "], "absent or unclear"),
    ],
)
def test_missing_or_unclear_information(job, field, value, expected):
    setattr(job, field, value)
    report = ResearchAgent().analyze(job)
    assert len(report.missing_information) == 1
    assert expected in report.missing_information[0]
    assert len(report.research_questions) == 1


def test_all_missing_information_is_reported(job):
    job.minimum_experience_years = None
    job.job_track = "unknown"
    job.required_skills = []
    report = ResearchAgent().analyze(job)
    assert len(report.missing_information) == 3
    assert len(report.research_questions) == 3


def test_explicit_zero_is_not_missing(job):
    job.minimum_experience_years = 0
    assert ResearchAgent().analyze(job).missing_information == []
