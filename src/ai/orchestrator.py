"""Coordinate analysis agents and return a report awaiting human review."""

from src.ai.agents.critic_agent import CriticAgent
from src.ai.agents.job_agent import JobAnalysisAgent
from src.ai.agents.research_agent import ResearchAgent
from src.ai.agents.resume_agent import ResumeAnalysisAgent
from src.ai.schemas import (
    CriticReport,
    JobAnalysis,
    ResearchReport,
    ResumeAnalysis,
    WorkflowReport,
)


class JobPilotOrchestrator:
    def __init__(
        self,
        job_agent: JobAnalysisAgent,
        resume_agent: ResumeAnalysisAgent,
        research_agent: ResearchAgent,
        critic_agent: CriticAgent,
    ) -> None:
        self.job_agent = job_agent
        self.resume_agent = resume_agent
        self.research_agent = research_agent
        self.critic_agent = critic_agent

    def run(self, job_description: str, resume_text: str) -> WorkflowReport:
        """Run in order, propagating failures without returning a partial report."""
        for name, value in (("Job description", job_description), ("Resume text", resume_text)):
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string.")
            if not value.strip():
                raise ValueError(f"{name} must not be empty or blank.")

        job = JobAnalysis.model_validate(self.job_agent.analyze(job_description))
        resume = ResumeAnalysis.model_validate(self.resume_agent.analyze(resume_text))
        research = ResearchReport.model_validate(self.research_agent.analyze(job))
        critic = CriticReport.model_validate(self.critic_agent.analyze(job, resume))

        return WorkflowReport(
            job_analysis=job,
            resume_analysis=resume,
            research_report=research,
            critic_report=critic,
            requires_human_review=True,
            status="pending_review",
            analysis_mode="mock",
        )
