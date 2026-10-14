from unittest.mock import patch

from fastapi.testclient import TestClient

from src.ai.agents.critic_agent import CriticAgent
from src.ai.agents.research_agent import ResearchAgent
from src.ai.orchestrator import JobPilotOrchestrator, create_workflow
from src.ai.schemas import JobAnalysis
from src.api import app
from src.candidate import candidate_profile


client = TestClient(app)


def _mock_job(**overrides):
    defaults = {
        "id": 1,
        "title": "Data Engineer",
        "company": "Test Company",
        "location": "New York, NY",
        "url": "https://example.com/job/1",
        "source": "greenhouse",
        "description": "",
    }
    defaults.update(overrides)
    return type("MockJob", (), defaults)()


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_jobs():
    mock_job = type(
        "MockJob",
        (),
        {
            "id": 1,
            "title": "Data Engineer",
            "company": "Test Company",
            "location": "New York, NY",
            "url": "https://example.com/job/1",
            "source": "greenhouse",
        },
    )()

    with patch("src.api.get_all_jobs", return_value=[mock_job]):
        response = client.get("/jobs")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "title": "Data Engineer",
            "company": "Test Company",
            "location": "New York, NY",
            "url": "https://example.com/job/1",
            "source": "greenhouse",
        }
    ]


def test_get_job_by_id():
    mock_job = _mock_job(description="Full job description text.")

    with patch("src.api.get_job_by_id", return_value=mock_job) as mock_get_job:
        response = client.get("/jobs/1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["description"] == "Full job description text."
    mock_get_job.assert_called_once_with(1)


def test_get_job_not_found():
    with patch("src.api.get_job_by_id", return_value=None):
        response = client.get("/jobs/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


def test_resume_recommendation_uses_mock_workflow_and_fictional_variants():
    mock_job = _mock_job(description="A sufficiently detailed job description.")
    with patch("src.api.get_job_by_id", return_value=mock_job), patch(
        "src.api.create_workflow", wraps=create_workflow
    ) as factory:
        response = client.get("/jobs/1/resume-recommendation")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == 1
    assert body["analysis_mode"] == "mock"
    assert body["evidence_source"] == "fictional_mock_fixture"
    assert body["personalized"] is False
    assert body["requires_human_review"] is True
    assert body["status"] == "pending_review"
    assert body["recommendation"]["recommended_variant"] in {
        "pharma", "data", "scientific_ai", None
    }
    assert {item["variant"] for item in body["recommendation"]["rankings"]} == {
        "pharma", "data", "scientific_ai"
    }
    assert all(item["reasons"] and "limitations" in item for item in body["recommendation"]["rankings"])
    assert "fixed mock sample" in body["warnings"][0]
    assert factory.call_args.args == ("mock",)


def test_ai_review_returns_research_and_critic_reports_for_fictional_fixtures():
    mock_job = _mock_job(description="A sufficiently detailed job description.")
    with patch("src.api.get_job_by_id", return_value=mock_job):
        response = client.get("/jobs/1/ai-review")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_mode"] == "mock"
    assert body["evidence_source"] == "fictional_mock_fixture"
    assert body["personalized"] is False
    assert body["requires_human_review"] is True
    assert body["research_report"]["summary"].endswith("No external research was performed.")
    assert set(body["critic_reports"]) == {"pharma", "data", "scientific_ai"}
    assert all(report["requires_human_review"] for report in body["critic_reports"].values())
    assert any("mock or sample" in warning for warning in body["warnings"])


def test_missing_description_returns_no_fabricated_analysis_or_recommendation():
    mock_job = _mock_job(description="  ")
    with patch("src.api.get_job_by_id", return_value=mock_job), patch(
        "src.api.create_workflow"
    ) as factory:
        response = client.get("/jobs/1/resume-recommendation")

    assert response.status_code == 200
    body = response.json()
    assert body["job_analysis"] is None
    assert body["recommendation"] is None
    assert body["evidence_source"] == "not_available"
    assert "missing" in body["warnings"][0]
    factory.assert_not_called()


def test_incomplete_description_is_marked_as_unanalyzed_mock_fixture():
    mock_job = _mock_job(description="Engineer")
    with patch("src.api.get_job_by_id", return_value=mock_job):
        response = client.get("/jobs/1/resume-recommendation")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_mode"] == "mock"
    assert body["evidence_source"] == "fictional_mock_fixture"
    assert "does not analyze the stored description" in body["warnings"][0]
    assert "Engineer" not in response.text


def test_ai_recommendation_does_not_filter_discovered_jobs():
    jobs = [_mock_job(id=1), _mock_job(id=2)]
    with patch("src.api.get_job_by_id", return_value=jobs[0]), patch(
        "src.api.get_all_jobs", return_value=jobs
    ):
        recommendation = client.get("/jobs/1/resume-recommendation")
        discovered_jobs = client.get("/jobs")

    assert recommendation.status_code == discovered_jobs.status_code == 200
    assert [job["id"] for job in discovered_jobs.json()] == [1, 2]


def test_missing_job_is_404_for_both_ai_endpoints():
    with patch("src.api.get_job_by_id", return_value=None):
        recommendation = client.get("/jobs/999/resume-recommendation")
        review = client.get("/jobs/999/ai-review")

    assert recommendation.status_code == review.status_code == 404
    assert recommendation.json() == review.json() == {"detail": "Job not found"}


def test_unknown_track_is_preserved_and_reviewable():
    unknown_job = JobAnalysis(
        required_skills=["cheminformatics"],
        preferred_skills=[],
        minimum_experience_years=None,
        job_track="unknown",
        summary="Fictional unknown-track role.",
    )
    workflow = JobPilotOrchestrator(
        job_agent=type("FixedJobAgent", (), {"analyze": lambda self, description: unknown_job})(),
        resume_agent=None,
        research_agent=ResearchAgent(),
        critic_agent=CriticAgent(),
        analysis_mode="mock",
    )
    mock_job = _mock_job(description="A sufficiently detailed job description.")
    with patch("src.api.get_job_by_id", return_value=mock_job), patch(
        "src.api.create_workflow", return_value=workflow
    ):
        response = client.get("/jobs/1/ai-review")

    assert response.status_code == 200
    body = response.json()
    assert body["job_analysis"]["job_track"] == "unknown"
    assert any(
        "Unknown job track" in limitation
        for ranking in body["recommendation"]["rankings"]
        for limitation in ranking["limitations"]
    )
    assert body["research_report"]["missing_information"]


def test_sensitive_job_text_and_internal_errors_are_not_exposed(caplog):
    sentinel = "private-marker@example.invalid visa-status-12345"
    mock_job = _mock_job(description=f"Job description {sentinel}")
    with patch("src.api.get_job_by_id", return_value=mock_job):
        response = client.get("/jobs/1/resume-recommendation")
    assert sentinel not in response.text
    assert "private-marker" not in caplog.text

    with patch("src.api.get_job_by_id", return_value=mock_job), patch(
        "src.api.create_workflow", side_effect=RuntimeError(sentinel)
    ):
        failed = client.get("/jobs/1/resume-recommendation")
    assert failed.status_code == 503
    assert sentinel not in failed.text
    assert "private-marker" not in caplog.text


def test_resume_text_analysis_gate_is_not_invoked_by_api(monkeypatch):
    from src.ai.agents.resume_agent import ResumeAnalysisAgent

    def forbidden(*args, **kwargs):
        raise AssertionError("API must not analyze resume text")

    monkeypatch.setattr(ResumeAnalysisAgent, "analyze", forbidden)
    mock_job = _mock_job(description="A sufficiently detailed job description.")
    with patch("src.api.get_job_by_id", return_value=mock_job):
        response = client.get("/jobs/1/resume-recommendation")
    assert response.status_code == 200


def test_get_matches_returns_ranked_match_details():
    mock_jobs = [
        type(
            "MockJob",
            (),
            {
                "id": 1,
                "title": "Data Engineer",
                "company": "Strong Match Co",
                "location": "Remote - United States",
                "url": "https://example.com/job/1",
                "source": "greenhouse",
                "description": (
                    "Data engineering role requiring Python, SQL, pandas, "
                    "and 2 years of experience."
                ),
            },
        )(),
        type(
            "MockJob",
            (),
            {
                "id": 2,
                "title": "Office Coordinator",
                "company": "Weak Match Co",
                "location": "Boston, Massachusetts",
                "url": "https://example.com/job/2",
                "source": "lever",
                "description": "General office responsibilities.",
            },
        )(),
    ]

    with patch("src.api.get_all_jobs", return_value=mock_jobs) as mock_get_all_jobs:
        response = client.get("/matches")

    assert response.status_code == 200
    matches = response.json()
    assert len(matches) == 2
    assert matches[0]["job_id"] == 1
    assert matches[0]["overall_score"] > matches[1]["overall_score"]

    strong_match = matches[0]
    assert strong_match["recommendation"]
    assert strong_match["job_track"] == "data"
    assert {
        "skill_score",
        "experience_score",
        "role_score",
        "domain_score",
        "location_score",
    }.issubset(strong_match)
    assert strong_match["matched_skills"]
    assert "missing_skills" in strong_match
    assert "reasons" in strong_match
    assert strong_match["candidate_years"] == 0.0
    assert strong_match["required_years"] == 2
    mock_get_all_jobs.assert_called_once_with()


# --- Phase 8B: CORS ---

def test_cors_preflight_allows_configured_dev_origin():
    response = client.options(
        "/jobs",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_preflight_allows_127_0_0_1_dev_origin():
    response = client.options(
        "/jobs",
        headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_cors_preflight_allows_fallback_dev_port_5175():
    # Vite falls back past 5173/5174 when another local project already
    # holds them; this project's frontend currently lands on 5175.
    response = client.options(
        "/jobs",
        headers={"Origin": "http://localhost:5175", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5175"


def test_cors_preflight_allows_127_0_0_1_fallback_dev_port_5175():
    response = client.options(
        "/jobs",
        headers={"Origin": "http://127.0.0.1:5175", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5175"


def test_cors_preflight_rejects_unlisted_origin():
    response = client.options(
        "/jobs",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_rejects_intermediate_fallback_port_5174():
    # 5174 was never explicitly added; only 5173 and 5175 are allowed, so a
    # port in between must still be rejected, not implicitly swept in.
    response = client.options(
        "/jobs",
        headers={"Origin": "http://localhost:5174", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_no_wildcard_origin_configured():
    from src.api import ALLOWED_ORIGINS
    assert "*" not in ALLOWED_ORIGINS
    assert all(origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1")
               for origin in ALLOWED_ORIGINS)


# --- Phase 8B: /jobs filters, pagination, validation ---

def test_jobs_location_filter_is_case_insensitive_substring():
    jobs = [
        _mock_job(id=1, location="New York, NY"),
        _mock_job(id=2, location="Boston, MA"),
    ]
    with patch("src.api.get_all_jobs", return_value=jobs):
        response = client.get("/jobs", params={"location": "new york"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == 1


def test_jobs_source_filter_is_case_insensitive():
    jobs = [
        _mock_job(id=1, source="greenhouse"),
        _mock_job(id=2, source="lever"),
    ]
    with patch("src.api.get_all_jobs", return_value=jobs):
        response = client.get("/jobs", params={"source": "LEVER"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == 2


def test_jobs_pagination_limit_and_offset():
    jobs = [_mock_job(id=i) for i in (3, 1, 2)]  # intentionally unordered
    with patch("src.api.get_all_jobs", return_value=jobs):
        response = client.get("/jobs", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == 2  # sorted by id (1, 2, 3) before paginating


def test_jobs_deterministic_ordering_without_pagination():
    jobs = [_mock_job(id=i) for i in (3, 1, 2)]
    with patch("src.api.get_all_jobs", return_value=jobs):
        response = client.get("/jobs")

    assert [row["id"] for row in response.json()] == [1, 2, 3]


def test_jobs_no_parameters_unchanged_behavior():
    jobs = [_mock_job(id=i) for i in range(1, 4)]
    with patch("src.api.get_all_jobs", return_value=jobs) as mock_get_all_jobs:
        response = client.get("/jobs")

    assert response.status_code == 200
    assert len(response.json()) == 3
    mock_get_all_jobs.assert_called_once_with()


def test_jobs_invalid_limit_rejected():
    with patch("src.api.get_all_jobs", return_value=[]):
        response = client.get("/jobs", params={"limit": 0})
    assert response.status_code == 422


def test_jobs_invalid_offset_rejected():
    with patch("src.api.get_all_jobs", return_value=[]):
        response = client.get("/jobs", params={"offset": -1})
    assert response.status_code == 422


def test_jobs_limit_above_max_rejected():
    with patch("src.api.get_all_jobs", return_value=[]):
        response = client.get("/jobs", params={"limit": 101})
    assert response.status_code == 422


def test_jobs_empty_location_param_rejected():
    with patch("src.api.get_all_jobs", return_value=[]):
        response = client.get("/jobs", params={"location": ""})
    assert response.status_code == 422


# --- Phase 8B: /matches filters, pagination, validation ---

def _match_job_fixture(id, title, location, source, description):
    return type(
        "MockJob",
        (),
        {
            "id": id, "title": title, "company": "Co", "location": location,
            "url": f"https://example.com/job/{id}", "source": source, "description": description,
        },
    )()


def test_matches_location_filter():
    jobs = [
        _match_job_fixture(1, "Data Engineer", "New York, NY", "greenhouse",
                            "Python and SQL role."),
        _match_job_fixture(2, "Data Engineer", "Boston, MA", "greenhouse",
                            "Python and SQL role."),
    ]
    with patch("src.api.get_all_jobs", return_value=jobs):
        response = client.get("/matches", params={"location": "boston"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["job_id"] == 2


def test_matches_source_filter():
    jobs = [
        _match_job_fixture(1, "Data Engineer", "Remote", "greenhouse", "Python role."),
        _match_job_fixture(2, "Data Engineer", "Remote", "lever", "Python role."),
    ]
    with patch("src.api.get_all_jobs", return_value=jobs):
        response = client.get("/matches", params={"source": "lever"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["job_id"] == 2


def test_matches_deterministic_job_track_filter():
    jobs = [
        _match_job_fixture(1, "Data Engineer", "Remote", "greenhouse",
                            "Data engineering role requiring Python and SQL."),
        _match_job_fixture(2, "Medicinal Chemist", "Remote", "greenhouse",
                            "Medicinal chemistry drug discovery role."),
    ]
    with patch("src.api.get_all_jobs", return_value=jobs):
        response = client.get("/matches", params={"job_track": "pharma"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["job_id"] == 2
    assert body[0]["job_track"] == "pharma"


def test_matches_invalid_job_track_rejected():
    with patch("src.api.get_all_jobs", return_value=[]):
        response = client.get("/matches", params={"job_track": "scientific_ai"})
    # scientific_ai is a Phase 7 AI-track value, not valid for this
    # deterministic Phase 1-6 filter; must be rejected, never silently merged.
    assert response.status_code == 422


def test_matches_min_score_filter():
    jobs = [
        _match_job_fixture(1, "Data Engineer", "Remote", "greenhouse",
                            "Data engineering role requiring Python, SQL, pandas, and 2 years."),
        _match_job_fixture(2, "Office Coordinator", "Remote", "greenhouse",
                            "General office responsibilities."),
    ]
    with patch("src.api.get_all_jobs", return_value=jobs):
        full = client.get("/matches").json()
        weak_score = next(m for m in full if m["job_id"] == 2)["overall_score"]
        response = client.get("/matches", params={"min_score": weak_score + 1})

    assert response.status_code == 200
    body = response.json()
    assert all(m["overall_score"] >= weak_score + 1 for m in body)
    assert 2 not in [m["job_id"] for m in body]


def test_matches_invalid_min_score_rejected():
    with patch("src.api.get_all_jobs", return_value=[]):
        response = client.get("/matches", params={"min_score": 101})
    assert response.status_code == 422


def test_matches_pagination():
    jobs = [
        _match_job_fixture(i, "Data Engineer", "Remote", "greenhouse", "Python and SQL role.")
        for i in range(1, 4)
    ]
    with patch("src.api.get_all_jobs", return_value=jobs):
        full = client.get("/matches").json()
        paged = client.get("/matches", params={"limit": 1, "offset": 1}).json()

    assert len(paged) == 1
    assert paged[0]["job_id"] == full[1]["job_id"]


def test_matches_no_parameters_unchanged_behavior():
    jobs = [
        _match_job_fixture(1, "Data Engineer", "Remote - United States", "greenhouse",
                            "Data engineering role requiring Python, SQL, pandas, and 2 years."),
        _match_job_fixture(2, "Office Coordinator", "Boston, Massachusetts", "lever",
                            "General office responsibilities."),
    ]
    with patch("src.api.get_all_jobs", return_value=jobs) as mock_get_all_jobs:
        response = client.get("/matches")

    assert response.status_code == 200
    assert len(response.json()) == 2
    mock_get_all_jobs.assert_called_once_with()


# --- Phase 8B: job detail description handling ---

def test_job_detail_includes_full_description():
    mock_job = _mock_job(description="A very long and complete fictional job description.")
    with patch("src.api.get_job_by_id", return_value=mock_job):
        response = client.get("/jobs/1")

    assert response.status_code == 200
    assert response.json()["description"] == "A very long and complete fictional job description."


def test_job_detail_handles_empty_description():
    mock_job = _mock_job(description="")
    with patch("src.api.get_job_by_id", return_value=mock_job):
        response = client.get("/jobs/1")

    assert response.status_code == 200
    assert response.json()["description"] == ""


def test_job_detail_handles_null_description():
    mock_job = _mock_job(description=None)
    with patch("src.api.get_job_by_id", return_value=mock_job):
        response = client.get("/jobs/1")

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_job_list_response_stays_lightweight_without_description():
    mock_job = _mock_job(description="Should not appear in the list response.")
    with patch("src.api.get_all_jobs", return_value=[mock_job]):
        response = client.get("/jobs")

    assert response.status_code == 200
    assert "description" not in response.json()[0]


def test_matches_handles_missing_description_without_error():
    job = _match_job_fixture(1, "Office Coordinator", "Remote", "greenhouse", "")
    with patch("src.api.get_all_jobs", return_value=[job]):
        response = client.get("/matches")

    assert response.status_code == 200
    assert response.json()[0]["job_track"] is None


# --- Phase 8B: no change to matching scores or CandidateProfile ---

def test_candidate_profile_unchanged():
    assert candidate_profile.experience_by_domain == {"pharma": 8.0, "data": 0.0}
    assert candidate_profile.preferred_locations == ["Anywhere in USA"]
    assert "python" in candidate_profile.skills
    assert "medicinal chemistry" in candidate_profile.skills


def test_matches_score_identical_to_direct_match_job_call():
    from src.matching import match_job

    job = _match_job_fixture(1, "Data Engineer", "Remote - United States", "greenhouse",
                              "Data engineering role requiring Python, SQL, pandas, and 2 years.")
    job_dict = {
        "title": job.title, "company": job.company, "location": job.location,
        "url": job.url, "source": job.source, "description": job.description,
    }
    direct_result = match_job(candidate_profile, job_dict)

    with patch("src.api.get_all_jobs", return_value=[job]):
        response = client.get("/matches")

    api_result = response.json()[0]
    assert api_result["overall_score"] == direct_result["overall_score"]
    assert api_result["skill_score"] == direct_result["skill_score"]
    assert api_result["job_track"] == direct_result["job_track"]
