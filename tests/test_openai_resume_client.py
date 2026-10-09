from types import SimpleNamespace
from unittest.mock import Mock

import httpx2
import pytest

from src.ai import openai_client as module
from src.ai.agents.resume_agent import ResumeAnalysisAgent
from src.ai.schemas import ResumeAnalysis
from src.ai.resume_privacy import approve_resume

def approved(text):
    return approve_resume("Location: Delaware, USA\nSkills:\n" + text, confirmed=True)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unexpected network access")
    monkeypatch.setattr("socket.socket", forbidden)


@pytest.fixture
def sdk(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", "configured-model")
    factory = Mock()
    monkeypatch.setattr(module, "OpenAI", factory)
    factory.return_value.responses.parse.return_value = SimpleNamespace(
        status="completed", output=[], output_parsed={
            "skills": ["medicinal chemistry", "Python", "SQL"],
            "professional_experience_years": {"pharma": 8.0, "data": None},
            "domains": ["oncology"], "education": ["PhD in Organic Chemistry"],
            "summary": "Sample pharmaceutical researcher with data training.",
        },
    )
    return factory


def test_valid_resume_and_shared_controls(sdk):
    client = module.OpenAIResumeClient()
    sdk.return_value.responses.parse.assert_not_called()
    result = ResumeAnalysisAgent(client).analyze(approved("Resume text"))
    assert isinstance(result, ResumeAnalysis)
    assert result.professional_experience_years == {"pharma": 8.0}
    assert result.education == ["PhD in Organic Chemistry"]
    sdk.assert_called_once_with(api_key="test-placeholder", timeout=30.0, max_retries=0)
    kwargs = sdk.return_value.responses.parse.call_args.kwargs
    assert kwargs["model"] == "configured-model"
    assert kwargs["max_output_tokens"] == 1000
    assert kwargs["store"] is False
    assert kwargs["input"] == [{"role": "user", "content": str(approved("Resume text"))}]
    assert "untrusted data" in kwargs["instructions"]
    assert "bootcamps, projects, and training" in kwargs["instructions"]


@pytest.mark.parametrize("years,expected", [
    ({"pharma": None, "data": None}, {}),
    ({"pharma": 8.0, "data": 2.0}, {"pharma": 8.0, "data": 2.0}),
    ({"pharma": None, "data": 0.0}, {"data": 0.0}),
])
def test_missing_and_separate_experience(sdk, years, expected):
    sdk.return_value.responses.parse.return_value.output_parsed["professional_experience_years"] = years
    assert module.OpenAIResumeClient().analyze_resume(approved("Resume")).professional_experience_years == expected


@pytest.mark.parametrize("output", [None, {}, "invalid"])
def test_malformed_output(sdk, output):
    sdk.return_value.responses.parse.return_value.output_parsed = output
    with pytest.raises(module.InvalidResumeOutputError):
        module.OpenAIResumeClient().analyze_resume(approved("Resume"))


@pytest.mark.parametrize("years", [-1.0, float("nan"), float("inf"), "8"])
def test_invalid_years(sdk, years):
    sdk.return_value.responses.parse.return_value.output_parsed["professional_experience_years"]["pharma"] = years
    with pytest.raises(module.InvalidResumeOutputError):
        module.OpenAIResumeClient().analyze_resume(approved("Resume"))


def test_refusal(sdk):
    sdk.return_value.responses.parse.return_value.output = [
        SimpleNamespace(type="message", content=[SimpleNamespace(type="refusal")])
    ]
    with pytest.raises(module.ResumeAnalysisRefusalError):
        module.OpenAIResumeClient().analyze_resume(approved("Resume"))


def test_incomplete_response(sdk):
    sdk.return_value.responses.parse.return_value.status = "incomplete"
    with pytest.raises(module.InvalidResumeOutputError):
        module.OpenAIResumeClient().analyze_resume(approved("Resume"))


@pytest.mark.parametrize("kind", ["timeout", "api", "parse"])
def test_sdk_failures(sdk, kind):
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    error, expected = {
        "timeout": (module.APITimeoutError(request), module.ResumeAnalysisTimeoutError),
        "api": (module.APIError("private", request, body=None), module.ResumeAnalysisAPIError),
        "parse": (ValueError("private"), module.InvalidResumeOutputError),
    }[kind]
    sdk.return_value.responses.parse.side_effect = error
    with pytest.raises(expected):
        module.OpenAIResumeClient().analyze_resume(approved("Resume"))
    sdk.return_value.responses.parse.assert_called_once()


def test_missing_credentials(sdk, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(module.MissingCredentialsError):
        module.OpenAIResumeClient()
    sdk.assert_not_called()


def test_blank_input(sdk):
    with pytest.raises(ValueError):
        module.OpenAIResumeClient().analyze_resume(" \n")
    sdk.return_value.responses.parse.assert_not_called()


def test_wire_schema_has_only_fixed_object_keys():
    from openai.lib._pydantic import to_strict_json_schema
    schema = to_strict_json_schema(module._ResumeOutput)
    assert schema["additionalProperties"] is False
    experience = schema["$defs"]["_TrackExperience"]
    assert experience["additionalProperties"] is False
    assert set(experience["required"]) == {"pharma", "data"}
