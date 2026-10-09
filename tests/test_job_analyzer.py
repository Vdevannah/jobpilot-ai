import pytest
from pydantic import ValidationError

from src.ai.client import MockLLMClient
from src.ai.job_analyzer import analyze_job_description
from src.ai.schemas import JobAnalysis


class StubLLMClient:
    def __init__(self, response):
        self.response = response
        self.descriptions = []

    def analyze_job(self, description: str) -> JobAnalysis:
        self.descriptions.append(description)
        return self.response


@pytest.fixture
def analysis_data():
    return {
        "required_skills": ["medicinal chemistry"],
        "preferred_skills": ["oncology"],
        "minimum_experience_years": None,
        "job_track": "pharma",
        "summary": "Injected test analysis for a research role.",
    }


def test_mock_returns_valid_deterministic_sample():
    client = MockLLMClient()

    result = analyze_job_description("Python developer role", client)

    assert isinstance(result, JobAnalysis)
    assert result.required_skills == ["python", "sql"]
    assert result.preferred_skills == ["aws"]
    assert result.minimum_experience_years == 3
    assert result.job_track == "data"
    assert "MOCK SAMPLE" in result.summary
    assert "not genuine AI analysis" in result.summary
    assert result == analyze_job_description("An unrelated role", client)


@pytest.mark.parametrize("description", ["", " ", "\n\t\r "])
def test_blank_description_is_rejected_before_calling_client(description):
    client = StubLLMClient(None)

    with pytest.raises(ValueError, match="must not be empty or blank"):
        analyze_job_description(description, client)

    assert client.descriptions == []


def test_analyzer_uses_injected_client(analysis_data):
    expected = JobAnalysis(**analysis_data)
    client = StubLLMClient(expected)
    description = "  Medicinal chemistry research role.\n"

    result = analyze_job_description(description, client)

    assert result == expected
    assert client.descriptions == [description]


@pytest.mark.parametrize("track", ["data", "pharma", "unknown"])
def test_valid_mapping_response_is_validated(analysis_data, track):
    analysis_data["job_track"] = track

    result = analyze_job_description("Research role", StubLLMClient(analysis_data))

    assert isinstance(result, JobAnalysis)
    assert result.model_dump() == analysis_data


@pytest.mark.parametrize("response", [None, {}, "invalid response", []])
def test_malformed_response_is_rejected(response):
    with pytest.raises(ValidationError):
        analyze_job_description("Research role", StubLLMClient(response))


@pytest.mark.parametrize(
    "field, value",
    [
        ("required_skills", "python"),
        ("required_skills", [123]),
        ("preferred_skills", None),
        ("minimum_experience_years", "3"),
        ("minimum_experience_years", 2.5),
        ("minimum_experience_years", True),
        ("job_track", "engineering"),
        ("summary", None),
    ],
)
def test_invalid_response_fields_are_rejected(analysis_data, field, value):
    analysis_data[field] = value

    with pytest.raises(ValidationError):
        analyze_job_description("Research role", StubLLMClient(analysis_data))


def test_model_instances_are_revalidated(analysis_data):
    response = JobAnalysis(**analysis_data)
    response.required_skills.append(123)

    with pytest.raises(ValidationError):
        analyze_job_description("Research role", StubLLMClient(response))
