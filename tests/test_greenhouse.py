from unittest.mock import patch

import requests

from src.greenhouse import get_jobs
from src.utils import deduplicate_jobs, is_us_location, matches_target_role


def test_is_us_location_returns_true_for_us_locations():
    assert is_us_location("Austin, TX") is True
    assert is_us_location("Wilmington, DE") is True
    assert is_us_location("Remote - USA") is True
    assert is_us_location("United States") is True
    assert is_us_location("Atlanta, Georgia") is True
    assert is_us_location("Boston, Massachusetts") is True


def test_is_us_location_returns_false_for_non_us_locations():
    assert is_us_location("Bangalore, India") is False
    assert is_us_location("London, UK") is False
    assert is_us_location("Remote") is False


def test_matches_target_role_returns_true_for_matching_titles():
    assert matches_target_role("Senior Data Scientist", ["data scientist"]) is True
    assert matches_target_role("Senior Staff Data Engineer", ["data engineer"]) is True
    assert matches_target_role("Medicinal Chemist", ["medicinal chemist"]) is True


def test_matches_target_role_returns_false_for_non_matching_titles():
    assert matches_target_role("Strategic Finance & Analytics", ["analytics"]) is False
    assert matches_target_role("Investment Banking Analyst", ["analyst"]) is False
    assert matches_target_role("Software Engineer", ["data engineer"]) is False


def test_deduplicate_jobs():
    jobs = [
        {
            "title": "Data Engineer",
            "company": "Acme",
            "location": "New York, NY",
            "url": "https://greenhouse.example.com/123",
            "source": "greenhouse",
        },
        {
            "title": " data engineer ",
            "company": "ACME",
            "location": "new york, ny",
            "url": "https://lever.example.com/456",
            "source": "lever",
        },
        {
            "title": "Data Scientist",
            "company": "Acme",
            "location": "New York, NY",
            "url": "https://example.com/789",
            "source": "greenhouse",
        },
    ]

    result = deduplicate_jobs(jobs)

    assert len(result) == 2
    assert result[0] == {
        "title": "Data Engineer",
        "company": "Acme",
        "location": "New York, NY",
        "url": "https://greenhouse.example.com/123",
        "source": "greenhouse",
    }
    assert result[1] == {
        "title": "Data Scientist",
        "company": "Acme",
        "location": "New York, NY",
        "url": "https://example.com/789",
        "source": "greenhouse",
    }


def test_greenhouse_api_error_returns_empty_list():
    target_roles = ["data engineer"]

    with patch("src.greenhouse.requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException("API unavailable")
        result = get_jobs("testcompany", target_roles)

    assert result == []
