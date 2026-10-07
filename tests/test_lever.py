from unittest.mock import Mock, patch

import requests

from src.lever import get_lever_jobs


def test_get_lever_jobs_filters_and_normalizes_jobs():
    fake_jobs = [
        {
            "text": "Data Engineer",
            "categories": {"location": "Atlanta, Georgia"},
            "hostedUrl": "https://example.com/data-engineer",
            "descriptionPlain": "Build and maintain reliable data pipelines.",
            "lists": [
                {
                    "text": "Skill Set:",
                    "content": (
                        "<ul><li>Python and SQL</li>"
                        "<li>3+ years of experience</li></ul>"
                    ),
                }
            ],
        },
        {
            "text": "Customer Success Manager",
            "categories": {"location": "Atlanta, Georgia"},
            "hostedUrl": "https://example.com/customer-success",
        },
        {
            "text": "Data Scientist",
            "categories": {"location": "London, UK"},
            "hostedUrl": "https://example.com/data-scientist",
        },
    ]
    mock_response = Mock()
    mock_response.json.return_value = fake_jobs

    target_roles = ["data engineer", "data scientist"]

    with patch("src.lever.requests.get") as mock_get:
        mock_get.return_value = mock_response
        jobs = get_lever_jobs("testcompany", "Test Company", target_roles)

    assert len(jobs) == 1
    assert jobs == [
        {
            "title": "Data Engineer",
            "company": "Test Company",
            "location": "Atlanta, Georgia",
            "url": "https://example.com/data-engineer",
            "source": "lever",
            "description": (
                "Build and maintain reliable data pipelines. Skill Set: "
                "Python and SQL 3+ years of experience"
            ),
        }
    ]
    mock_get.assert_called_once_with(
        "https://api.lever.co/v0/postings/testcompany?mode=json"
    )


def test_lever_api_error_returns_empty_list():
    target_roles = ["data engineer"]

    with patch("src.lever.requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException("API unavailable")
        result = get_lever_jobs(
            "testcompany",
            "Test Company",
            target_roles,
        )

    assert result == []
