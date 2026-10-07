from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api import app


client = TestClient(app)


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

    with patch("src.api.get_job_by_id", return_value=mock_job) as mock_get_job:
        response = client.get("/jobs/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1
    mock_get_job.assert_called_once_with(1)


def test_get_job_not_found():
    with patch("src.api.get_job_by_id", return_value=None):
        response = client.get("/jobs/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


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
