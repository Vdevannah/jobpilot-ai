"""Coordinate analysis agents and return a report awaiting human review."""

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.ai.agents.critic_agent import CriticAgent
from src.ai.agents.job_agent import JobAnalysisAgent
from src.ai.agents.research_agent import ResearchAgent
from src.ai.agents.resume_agent import ResumeAnalysisAgent
from src.ai.resume_selector import ResumeRecommendation, recommend_resume
from src.ai.schemas import (
    CriticReport,
    JobAnalysis,
    ResearchReport,
    ResumeAnalysis,
    WorkflowReport,
)


class ResumeSelectionReport(BaseModel):
    """Rank already-analyzed resume variants against one freshly analyzed job.

    Accepts structured ResumeAnalysis evidence directly -- never raw resume
    text or PDF files -- so ranking the same resumes against many jobs never
    re-sends resume content anywhere. Produce each variant's ResumeAnalysis
    once, locally, via the orchestrator's existing resume_agent (which keeps
    the existing privacy/approval gate for live analysis unchanged); this
    report only reuses that already-computed evidence. Wraps
    resume_selector.recommend_resume() unchanged: no new scoring weights and
    no career-track reclassification are introduced here.
    """

    model_config = ConfigDict(strict=True, revalidate_instances="always")

    job_analysis: JobAnalysis
    recommendation: ResumeRecommendation
    requires_human_review: Literal[True] = True
    status: Literal["pending_review"] = "pending_review"
    analysis_mode: Literal["mock", "openai"]


class JobPilotOrchestrator:
    def __init__(
        self,
        job_agent: JobAnalysisAgent,
        resume_agent: ResumeAnalysisAgent,
        research_agent: ResearchAgent,
        critic_agent: CriticAgent,
        analysis_mode: Literal["mock", "openai"] = "mock",
    ) -> None:
        if analysis_mode not in ("mock", "openai"):
            raise ValueError("analysis_mode must be 'mock' or 'openai'.")
        self.analysis_mode = analysis_mode
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
            analysis_mode=self.analysis_mode,
        )

    def rank_resumes_for_job(
        self, job_description: str, resume_variants: Mapping[str, ResumeAnalysis]
    ) -> ResumeSelectionReport:
        """Analyze the job once, then rank already-analyzed resume variants.

        Job analysis never depends on which or how many variants are
        supplied, matching job discovery's existing independence from resume
        selection. resume_variants must already be structured ResumeAnalysis
        evidence -- produced once, locally, by calling self.resume_agent.analyze()
        on approved text -- not raw resume text or PDFs; this method makes no
        resume-analysis AI request itself, so ranking many jobs against the
        same resumes never resends resume content anywhere. Scoring is
        delegated unchanged to resume_selector.recommend_resume().
        """
        if not isinstance(job_description, str):
            raise TypeError("Job description must be a string.")
        if not job_description.strip():
            raise ValueError("Job description must not be empty or blank.")

        job = JobAnalysis.model_validate(self.job_agent.analyze(job_description))
        recommendation = recommend_resume(job, resume_variants)
        return ResumeSelectionReport(
            job_analysis=job,
            recommendation=recommendation,
            requires_human_review=True,
            status="pending_review",
            analysis_mode=self.analysis_mode,
        )


def create_workflow(analysis_mode: Literal["mock", "openai"] = "mock") -> JobPilotOrchestrator:
    """Choose analysis clients explicitly; research and criticism stay deterministic."""
    if analysis_mode == "mock":
        from src.ai.client import MockLLMClient, MockResumeLLMClient

        job_client = MockLLMClient()
        resume_client = MockResumeLLMClient()
    elif analysis_mode == "openai":
        from src.ai.openai_client import OpenAIJobClient, OpenAIResumeClient

        job_client = OpenAIJobClient()
        resume_client = OpenAIResumeClient()
    else:
        raise ValueError("analysis_mode must be 'mock' or 'openai'.")
    return JobPilotOrchestrator(
        JobAnalysisAgent(job_client), ResumeAnalysisAgent(resume_client),
        ResearchAgent(), CriticAgent(), analysis_mode=analysis_mode,
    )
