from copy import deepcopy
from unittest.mock import Mock

import pytest

from src.ai.agents.resume_agent import ResumeAnalysisAgent
from src.ai.schemas import ResumeAnalysis
from src.ai.schemas import JobAnalysis
from src.ai.resume_selector import recommend_resume
from src.candidate import candidate_profile
from src.greenhouse import get_jobs
from src.lever import get_lever_jobs
from src.matching import match_job
from src.utils import matches_target_role


CAREER_TITLES = [
    "Data Scientist", "Junior Data Scientist", "Data Engineer", "Junior Data Engineer",
    "Data Analyst", "Business Intelligence Analyst", "Business Analyst",
    "Technical Business Analyst", "Python Developer", "Software Engineer",
    "Medicinal Chemist", "Senior Scientist", "Principal Scientist",
    "Cheminformatics", "Computational Chemistry", "Scientific AI",
]


@pytest.mark.parametrize("title", CAREER_TITLES)
def test_existing_filter_accepts_configured_career_titles(title):
    # Explicit fixture coverage, not a change to the approved target-role list.
    assert matches_target_role(title, CAREER_TITLES)


@pytest.mark.parametrize("collector", ["greenhouse", "lever"])
def test_resume_variants_do_not_change_discovery_or_matching(monkeypatch, collector):
    profile_before = deepcopy(candidate_profile)
    targets = list(CAREER_TITLES)
    description = "Python, SQL, medicinal chemistry; 3 years of experience."
    if collector == "lever":
        response = Mock()
        response.json.return_value = [
            {"text": title, "categories": {"location": "Boston, Massachusetts"},
             "hostedUrl": f"https://example.com/{i}", "descriptionPlain": description}
            for i, title in enumerate(CAREER_TITLES)
        ]
        monkeypatch.setattr("src.lever.requests.get", Mock(return_value=response))
        discover = lambda: get_lever_jobs("example", "Example", targets)
    else:
        listing, detail = Mock(), Mock()
        listing.json.return_value = {"jobs": [
            {"id": i, "title": title, "location": {"name": "Boston, Massachusetts"},
             "company_name": "Example", "absolute_url": f"https://example.com/{i}"}
            for i, title in enumerate(CAREER_TITLES)
        ]}
        detail.json.return_value = {"content": description}
        monkeypatch.setattr("src.greenhouse.requests.get", Mock(
            side_effect=lambda url: listing if url.endswith("/jobs") else detail
        ))
        discover = lambda: get_jobs("example", targets)

    baseline = discover()
    scores = [match_job(candidate_profile, job) for job in baseline]
    analyzed = JobAnalysis(required_skills=['python'], preferred_skills=[],
                           minimum_experience_years=3, job_track='data', summary='Synthetic job')
    presentation = ResumeAnalysis(skills=['python'], professional_experience_years={},
                                  domains=[], education=[], summary='Synthetic resume')
    for opportunity in baseline:
        match_job(candidate_profile, opportunity)
        recommend_resume(analyzed, {'data': presentation, 'pharma': presentation,
                                   'scientific_ai': presentation})
    assert discover() == baseline
    for skills, experience in [(["medicinal chemistry"], {"pharma": 8.0}),
                               (["python", "sql"], {})]:
        client = Mock()
        client.analyze_resume.return_value = ResumeAnalysis(
            skills=skills, professional_experience_years=experience,
            domains=[], education=[], summary="Resume variant test fixture",
        )
        ResumeAnalysisAgent(client).analyze("Resume variant")
        jobs = discover()
        assert [job["title"] for job in jobs] == CAREER_TITLES
        assert jobs == baseline
        assert [match_job(candidate_profile, job) for job in jobs] == scores
    assert candidate_profile == profile_before
    assert targets == CAREER_TITLES


@pytest.mark.parametrize("title", ["Junior Data Engineer", "Junior Data Scientist", "Data Analyst"])
def test_data_opportunities_keep_skill_credit_and_visible_experience_gaps(title):
    profile = deepcopy(candidate_profile)
    profile.experience_by_domain["data"] = 0.0
    result = match_job(profile, {
        "title": title, "location": "Boston, Massachusetts",
        "description": "Python and SQL required; 3 years of experience.",
    })
    assert result["skill_score"] == 100.0
    assert result["candidate_years"] == 0.0
    assert result["overall_score"] > 0
    assert result["recommendation"]
    assert any("Experience gap" in reason for reason in result["reasons"])
    assert result["matched_skills"] == ["python", "sql"]
