from unittest.mock import Mock, call

import pytest
from pydantic import ValidationError

from src.ai.agents.critic_agent import CriticAgent
from src.ai.agents.job_agent import JobAnalysisAgent
from src.ai.agents.research_agent import ResearchAgent
from src.ai.agents.resume_agent import ResumeAnalysisAgent
from src.ai.client import MockLLMClient, MockResumeLLMClient
from src.ai.orchestrator import JobPilotOrchestrator
from src.ai.schemas import CriticReport, ResearchReport, WorkflowReport


@pytest.fixture(params=["mock", "openai"])
def workflow(request):
    calls = Mock()
    agents = [Mock(spec=cls) for cls in (
        JobAnalysisAgent, ResumeAnalysisAgent, ResearchAgent, CriticAgent
    )]
    for name, agent in zip(("job", "resume", "research", "critic"), agents):
        calls.attach_mock(agent, name)
    agents[0].analyze.return_value = MockLLMClient().analyze_job("Job")
    agents[1].analyze.return_value = MockResumeLLMClient().analyze_resume("Resume")
    agents[2].analyze.return_value = ResearchReport(
        missing_information=[], research_questions=[], summary="Complete fields."
    )
    agents[3].analyze.return_value = CriticReport(
        warnings=[], requires_human_review=False, summary="No warnings."
    )
    return JobPilotOrchestrator(*agents, analysis_mode=request.param), agents, calls


def test_success_and_agent_call_order(workflow):
    orchestrator, agents, calls = workflow
    job, resume, research, critic = [agent.analyze.return_value for agent in agents]

    result = orchestrator.run("  Job description\n", "  Resume text\n")

    assert isinstance(result, WorkflowReport)
    assert result.analysis_mode == orchestrator.analysis_mode
    assert result.model_dump()["analysis_mode"] == orchestrator.analysis_mode
    assert calls.mock_calls == [
        call.job.analyze("  Job description\n"),
        call.resume.analyze("  Resume text\n"),
        call.research.analyze(job),
        call.critic.analyze(job, resume),
    ]
    assert result.job_analysis == job
    assert result.resume_analysis == resume
    assert result.research_report == research
    assert result.critic_report == critic
    assert result.status == "pending_review"


@pytest.mark.parametrize("blank", ["", " ", "\n\t"])
@pytest.mark.parametrize("input_index", [0, 1])
def test_blank_input_rejected_before_any_agent(workflow, blank, input_index):
    orchestrator, _, calls = workflow
    inputs = ["Job", "Resume"]
    inputs[input_index] = blank
    with pytest.raises(ValueError, match="must not be empty or blank"):
        orchestrator.run(*inputs)
    assert calls.mock_calls == []


@pytest.mark.parametrize("input_index", [0, 1])
def test_non_string_input_rejected_before_any_agent(workflow, input_index):
    orchestrator, _, calls = workflow
    inputs = ["Job", "Resume"]
    inputs[input_index] = None
    with pytest.raises(TypeError, match="must be a string"):
        orchestrator.run(*inputs)
    assert calls.mock_calls == []


@pytest.mark.parametrize("agent_index", range(4))
@pytest.mark.parametrize("output", [None, {}, "invalid"])
def test_invalid_agent_output_stops_workflow(workflow, agent_index, output):
    orchestrator, agents, _ = workflow
    agents[agent_index].analyze.return_value = output
    with pytest.raises(ValidationError):
        orchestrator.run("Job", "Resume")
    for agent in agents[agent_index + 1:]:
        agent.analyze.assert_not_called()


@pytest.mark.parametrize("agent_index", range(4))
def test_agent_exception_propagates_without_continuing(workflow, agent_index):
    orchestrator, agents, _ = workflow
    error = RuntimeError("Agent failed")
    agents[agent_index].analyze.side_effect = error
    with pytest.raises(RuntimeError) as raised:
        orchestrator.run("Job", "Resume")
    assert raised.value is error
    for agent in agents[agent_index + 1:]:
        agent.analyze.assert_not_called()


@pytest.mark.parametrize("critic_review", [False, True])
def test_workflow_always_requires_review_and_preserves_critic(workflow, critic_review):
    orchestrator, agents, _ = workflow
    agents[3].analyze.return_value.requires_human_review = critic_review
    result = orchestrator.run("Job", "Resume")
    assert result.requires_human_review is True
    assert result.critic_report.requires_human_review is critic_review
    assert result.status == "pending_review"


def test_final_report_revalidates_nested_output(workflow):
    orchestrator, agents, _ = workflow

    def corrupt_job(job, resume):
        job.required_skills.append(123)
        return agents[3].analyze.return_value

    agents[3].analyze.side_effect = corrupt_job
    with pytest.raises(ValidationError):
        orchestrator.run("Job", "Resume")


def test_real_agents_with_mock_clients_are_offline_and_preserve_inputs(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Workflow attempted external I/O")

    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("io.open", forbidden)
    monkeypatch.setattr("os.open", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    orchestrator = JobPilotOrchestrator(
        JobAnalysisAgent(MockLLMClient()),
        ResumeAnalysisAgent(MockResumeLLMClient()),
        ResearchAgent(),
        CriticAgent(),
    )
    result = orchestrator.run("Data role", "Resume text")
    assert result.resume_analysis.professional_experience_years == {"pharma": 8.0, "data": 1.0}
    assert any("Experience gap for data" in warning for warning in result.critic_report.warnings)
    assert result.requires_human_review
    assert result.analysis_mode == "mock"
    assert result == orchestrator.run("Data role", "Resume text")


def test_agent_owned_analyses_are_not_overwritten(workflow):
    orchestrator, agents, _ = workflow
    before = [agent.analyze.return_value.model_dump() for agent in agents]
    result = orchestrator.run("Job", "Resume")
    assert [agent.analyze.return_value.model_dump() for agent in agents] == before
    assert result.resume_analysis.professional_experience_years == {"pharma": 8.0, "data": 1.0}
