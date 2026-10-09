from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from src.ai.agents.job_agent import JobAnalysisAgent
from src.ai.schemas import JobAnalysis


class FakeLLMClient:
    def __init__(self, response):
        self.response = response
        self.descriptions = []

    def analyze_job(self, description: str) -> JobAnalysis:
        self.descriptions.append(description)
        return self.response


@pytest.fixture
def analysis():
    return JobAnalysis(
        required_skills=["medicinal chemistry"],
        preferred_skills=[],
        minimum_experience_years=None,
        job_track="pharma",
        summary="Fake analysis for testing.",
    )


def test_agent_delegates_to_existing_analyzer(monkeypatch, analysis):
    client = FakeLLMClient(analysis)
    analyzer = Mock(return_value=analysis)
    monkeypatch.setattr(
        "src.ai.agents.job_agent.analyze_job_description", analyzer
    )
    description = "  Research scientist role.\n"

    result = JobAnalysisAgent(client).analyze(description)

    assert result is analysis
    analyzer.assert_called_once_with(description, client)


@pytest.mark.parametrize("description", ["", " ", "\n\t"])
def test_agent_rejects_blank_descriptions(description, analysis):
    client = FakeLLMClient(analysis)

    with pytest.raises(ValueError, match="must not be empty or blank"):
        JobAnalysisAgent(client).analyze(description)

    assert client.descriptions == []


def test_agent_uses_injected_client_for_each_description(analysis):
    client = FakeLLMClient(analysis)
    agent = JobAnalysisAgent(client)

    assert agent.analyze("Research role") == analysis

    other_analysis = JobAnalysis(
        required_skills=["sql"],
        preferred_skills=["python"],
        minimum_experience_years=2,
        job_track="data",
        summary="Another fake analysis for testing.",
    )
    client.response = other_analysis

    assert agent.analyze("  Data role\n") == other_analysis
    assert client.descriptions == ["Research role", "  Data role\n"]


@pytest.mark.parametrize("response", [None, {}, "invalid response", []])
def test_agent_rejects_malformed_responses(response):
    with pytest.raises(ValidationError):
        JobAnalysisAgent(FakeLLMClient(response)).analyze("Research role")


def test_agent_rejects_invalid_model_response(analysis):
    analysis.required_skills.append(123)

    with pytest.raises(ValidationError):
        JobAnalysisAgent(FakeLLMClient(analysis)).analyze("Research role")
