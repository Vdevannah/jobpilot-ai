import pytest
from pydantic import ValidationError

from src.ai.agents.resume_agent import ResumeAnalysisAgent
from src.ai.client import MockResumeLLMClient
from src.ai.schemas import ResumeAnalysis


class FakeResumeClient:
    def __init__(self, response):
        self.response = response
        self.inputs = []

    def analyze_resume(self, resume_text: str) -> ResumeAnalysis:
        self.inputs.append(resume_text)
        return self.response


@pytest.fixture
def resume_data():
    return {
        "skills": ["python"],
        "professional_experience_years": {"pharma": 8.0, "data": 1.0},
        "domains": ["drug discovery"],
        "education": ["PhD in Chemistry", "Data science training program"],
        "summary": "Fake resume analysis for testing.",
    }


def test_mock_returns_explicit_deterministic_sample():
    agent = ResumeAnalysisAgent(MockResumeLLMClient())

    result = agent.analyze("A sample resume")

    assert isinstance(result, ResumeAnalysis)
    assert "MOCK SAMPLE" in result.summary
    assert "not actual resume extraction" in result.summary
    assert result == agent.analyze("An unrelated resume")


@pytest.mark.parametrize("resume_text", ["", " ", "\n\t\r"])
def test_blank_input_does_not_call_client(resume_text):
    client = FakeResumeClient(None)

    with pytest.raises(ValueError, match="must not be empty or blank"):
        ResumeAnalysisAgent(client).analyze(resume_text)

    assert client.inputs == []


def test_injected_client_receives_input_and_supplies_result(resume_data):
    expected = ResumeAnalysis(**resume_data)
    client = FakeResumeClient(expected)
    resume_text = "  Research scientist resume.\n"

    result = ResumeAnalysisAgent(client).analyze(resume_text)

    assert result == expected
    assert client.inputs == [resume_text]


@pytest.mark.parametrize("experience", [{"pharma": 8.0, "data": 1.0}, {"pharma": 8.0}, {}])
def test_experience_is_preserved_without_combining_or_filling(resume_data, experience):
    resume_data["professional_experience_years"] = experience

    result = ResumeAnalysisAgent(FakeResumeClient(resume_data)).analyze(
        "PhD in Chemistry and a data science training program."
    )

    assert result.professional_experience_years == experience
    assert result.education == resume_data["education"]


@pytest.mark.parametrize("response", [None, {}, [], "invalid response"])
def test_malformed_output_is_rejected(response):
    with pytest.raises(ValidationError):
        ResumeAnalysisAgent(FakeResumeClient(response)).analyze("Resume text")


@pytest.mark.parametrize(
    "field, value",
    [
        ("skills", "python"),
        ("professional_experience_years", {"data": "unknown"}),
        ("professional_experience_years", {"data": "3"}),
        ("domains", [123]),
        ("education", None),
        ("summary", None),
    ],
)
def test_invalid_fields_are_rejected(resume_data, field, value):
    resume_data[field] = value

    with pytest.raises(ValidationError):
        ResumeAnalysisAgent(FakeResumeClient(resume_data)).analyze("Resume text")


def test_model_output_is_revalidated(resume_data):
    response = ResumeAnalysis(**resume_data)
    response.professional_experience_years["data"] = "invalid"

    with pytest.raises(ValidationError):
        ResumeAnalysisAgent(FakeResumeClient(response)).analyze("Resume text")
