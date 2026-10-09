import importlib
from types import SimpleNamespace
from unittest.mock import Mock

import httpx2
import pytest
from openai import APIError, APITimeoutError

from src.ai import openai_client as module
from src.ai.schemas import JobAnalysis


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unexpected network call")
    monkeypatch.setattr("socket.socket", forbidden)


@pytest.fixture
def sdk(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    factory = Mock()
    monkeypatch.setattr(module, "OpenAI", factory)
    factory.return_value.responses.parse.return_value = SimpleNamespace(
        status="completed", output=[], output_parsed=JobAnalysis(
            required_skills=["python"], preferred_skills=["sql"],
            minimum_experience_years=None, job_track="data", summary="Python role.",
        ),
    )
    return factory


def test_success_and_request_settings(sdk):
    client = module.OpenAIJobClient()
    sdk.return_value.responses.parse.assert_not_called()
    result = client.analyze_job("Python required; SQL preferred.")
    assert isinstance(result, JobAnalysis)
    assert result.minimum_experience_years is None
    assert result.required_skills == ["python"]
    sdk.assert_called_once_with(api_key="test-only-placeholder", timeout=30.0, max_retries=0)
    kwargs = sdk.return_value.responses.parse.call_args.kwargs
    assert kwargs["model"] == "gpt-4.1-mini"
    assert kwargs["text_format"] is JobAnalysis
    assert kwargs["max_output_tokens"] == 1000
    assert kwargs["store"] is False
    assert kwargs["input"] == [{"role": "user", "content": "Python required; SQL preferred."}]
    assert "untrusted data" in kwargs["instructions"]


def test_configurable_model(sdk, monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "configured-model")
    module.OpenAIJobClient().analyze_job("Job")
    assert sdk.return_value.responses.parse.call_args.kwargs["model"] == "configured-model"


@pytest.mark.parametrize("key", [None, "", " \t"])
def test_missing_credentials(sdk, monkeypatch, key):
    if key is None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENAI_API_KEY", key)
    with pytest.raises(module.MissingCredentialsError):
        module.OpenAIJobClient()
    sdk.assert_not_called()


@pytest.mark.parametrize("output", [None, {}, "invalid"])
def test_malformed_output(sdk, output):
    sdk.return_value.responses.parse.return_value.output_parsed = output
    with pytest.raises(module.InvalidJobOutputError):
        module.OpenAIJobClient().analyze_job("Job")


def test_invalid_model_is_revalidated(sdk):
    sdk.return_value.responses.parse.return_value.output_parsed.required_skills.append(123)
    with pytest.raises(module.InvalidJobOutputError):
        module.OpenAIJobClient().analyze_job("Job")


def test_refusal(sdk):
    sdk.return_value.responses.parse.return_value.output = [
        SimpleNamespace(type="message", content=[SimpleNamespace(type="refusal")])
    ]
    with pytest.raises(module.JobAnalysisRefusalError):
        module.OpenAIJobClient().analyze_job("Job")


@pytest.mark.parametrize("status", ["incomplete", "failed"])
def test_incomplete_response(sdk, status):
    sdk.return_value.responses.parse.return_value.status = status
    with pytest.raises(module.InvalidJobOutputError):
        module.OpenAIJobClient().analyze_job("Job")


@pytest.mark.parametrize("kind", ["timeout", "api", "parse"])
def test_sdk_errors_are_explicit_without_fallback(sdk, kind):
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    error, expected = {
        "timeout": (APITimeoutError(request), module.JobAnalysisTimeoutError),
        "api": (APIError("private upstream details", request, body=None), module.JobAnalysisAPIError),
        "parse": (ValueError("invalid JSON"), module.InvalidJobOutputError),
    }[kind]
    sdk.return_value.responses.parse.side_effect = error
    with pytest.raises(expected) as raised:
        module.OpenAIJobClient().analyze_job("Job")
    assert "private upstream details" not in str(raised.value)
    sdk.return_value.responses.parse.assert_called_once()


@pytest.mark.parametrize("description", ["", " \n"])
def test_blank_input_never_calls_api(sdk, description):
    with pytest.raises(ValueError):
        module.OpenAIJobClient().analyze_job(description)
    sdk.return_value.responses.parse.assert_not_called()


def test_import_and_mock_agents_need_no_credentials(monkeypatch):
    import openai
    from src.ai.agents.job_agent import JobAnalysisAgent
    from src.ai.agents.resume_agent import ResumeAnalysisAgent
    from src.ai.client import MockLLMClient, MockResumeLLMClient

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    constructor = Mock(side_effect=AssertionError("Unexpected SDK construction"))
    with monkeypatch.context() as context:
        context.setattr(openai, "OpenAI", constructor)
        importlib.reload(module)
        JobAnalysisAgent(MockLLMClient()).analyze("Job")
        ResumeAnalysisAgent(MockResumeLLMClient()).analyze("Resume")
        constructor.assert_not_called()
    importlib.reload(module)


def test_job_prompt_separates_qualifications(sdk):
    module.OpenAIJobClient().analyze_job('PhD required, 8 years industry experience, SAR.')
    instructions = sdk.return_value.responses.parse.call_args.kwargs['instructions']
    assert 'never include degrees' in instructions
    assert 'years of employment' in instructions
    assert 'Preferred experience is not a minimum requirement' in instructions
    assert 'Required education:' in instructions
