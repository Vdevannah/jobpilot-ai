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
