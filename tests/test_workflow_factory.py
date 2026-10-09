from unittest.mock import Mock

import pytest

from src.ai import openai_client
from src.ai.agents.critic_agent import CriticAgent
from src.ai.agents.research_agent import ResearchAgent
from src.ai.client import MockLLMClient, MockResumeLLMClient
from src.ai.orchestrator import create_workflow, JobPilotOrchestrator
from scripts import test_openai_workflow as script


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unexpected network access")
    monkeypatch.setattr("socket.socket", forbidden)


def test_mock_factory_never_reads_credentials_or_constructs_sdk(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Mock workflow accessed credentials or OpenAI")
    monkeypatch.setattr(openai_client.os, "getenv", forbidden)
    monkeypatch.setattr(openai_client, "OpenAIJobClient", forbidden)
    monkeypatch.setattr(openai_client, "OpenAIResumeClient", forbidden)
    workflow = create_workflow()
    assert isinstance(workflow.job_agent.client, MockLLMClient)
    assert isinstance(workflow.resume_agent.client, MockResumeLLMClient)
    assert workflow.run("Job", "Resume").analysis_mode == "mock"


def test_openai_factory_uses_explicit_clients(monkeypatch):
    job = Mock(return_value=MockLLMClient())
    resume = Mock(return_value=MockResumeLLMClient())
    monkeypatch.setattr(openai_client, "OpenAIJobClient", job)
    monkeypatch.setattr(openai_client, "OpenAIResumeClient", resume)
    workflow = create_workflow("openai")
    job.assert_called_once_with()
    resume.assert_called_once_with()
    assert type(workflow.research_agent) is ResearchAgent
    assert type(workflow.critic_agent) is CriticAgent
    report = workflow.run("Job", "Resume")
    assert report.analysis_mode == "openai"
    assert report.requires_human_review
    assert report.status == "pending_review"


def test_constructor_defaults_to_mock():
    workflow = create_workflow()
    legacy = JobPilotOrchestrator(workflow.job_agent, workflow.resume_agent,
                                 workflow.research_agent, workflow.critic_agent)
    assert legacy.analysis_mode == "mock"


@pytest.mark.parametrize("mode", ["invalid", None])
def test_invalid_mode_rejected(mode):
    with pytest.raises(ValueError):
        create_workflow(mode)
    with pytest.raises(ValueError):
        JobPilotOrchestrator(Mock(), Mock(), Mock(), Mock(), analysis_mode=mode)


def test_missing_credentials_propagate(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(openai_client.MissingCredentialsError):
        create_workflow("openai")


@pytest.mark.parametrize("stage", ["job", "resume"])
def test_openai_errors_propagate_without_fallback(monkeypatch, stage):
    job, resume = Mock(), Mock()
    job.analyze_job.return_value = MockLLMClient().analyze_job("Job")
    resume.analyze_resume.return_value = MockResumeLLMClient().analyze_resume("Resume")
    error = openai_client.JobAnalysisAPIError("failure") if stage == "job" else openai_client.ResumeAnalysisTimeoutError("failure")
    (job.analyze_job if stage == "job" else resume.analyze_resume).side_effect = error
    monkeypatch.setattr(openai_client, "OpenAIJobClient", Mock(return_value=job))
    monkeypatch.setattr(openai_client, "OpenAIResumeClient", Mock(return_value=resume))
    with pytest.raises(type(error)) as raised:
        create_workflow("openai").run("Job", "Resume")
    assert raised.value is error
    if stage == "job":
        resume.analyze_resume.assert_not_called()


def test_script_without_flag_does_nothing(monkeypatch, capsys):
    factory, loader = Mock(), Mock()
    monkeypatch.setattr(script, "create_workflow", factory)
    monkeypatch.setattr(script, "load_dotenv", loader)
    assert script.main([]) == 0
    factory.assert_not_called()
    loader.assert_not_called()
    assert "--live" in capsys.readouterr().out


def test_script_live_branch_with_fake_workflow(monkeypatch, capsys):
    report = create_workflow().run("Job", "Resume")
    report.analysis_mode = "openai"
    factory, loader = Mock(), Mock()
    factory.return_value.run.return_value = report
    monkeypatch.setattr(script, "create_workflow", factory)
    monkeypatch.setattr(script, "load_dotenv", loader)
    assert script.main(["--live"]) == 0
    loader.assert_called_once_with(script.PROJECT_ROOT / ".env", override=False)
    factory.assert_called_once_with("openai")
    factory.return_value.run.assert_called_once()
    assert capsys.readouterr().out.endswith(report.model_dump_json(indent=2) + "\n")


def test_script_failure_is_nonzero_and_sanitized(monkeypatch, capsys):
    monkeypatch.setattr(script, "load_dotenv", Mock())
    monkeypatch.setattr(script, "create_workflow", Mock(side_effect=openai_client.JobAnalysisAPIError("private")))
    assert script.main(["--live"]) == 1
    output = capsys.readouterr()
    assert "JobAnalysisAPIError" in output.err
    assert "private" not in output.err
    assert "LOCAL PRIVACY PREVIEW" in output.out


@pytest.fixture(autouse=True)
def approve_synthetic_preview(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "APPROVE")
