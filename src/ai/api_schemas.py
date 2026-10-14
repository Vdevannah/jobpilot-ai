"""Safe response models for local-only AI preview endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.ai.resume_selector import ResumeRecommendation
from src.ai.schemas import CriticReport, JobAnalysis, ResearchReport


class _AIEndpointResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    job_id: int
    job_analysis: JobAnalysis | None
    recommendation: ResumeRecommendation | None
    analysis_mode: Literal['mock'] = 'mock'
    evidence_source: Literal['fictional_mock_fixture', 'not_available']
    personalized: Literal[False] = False
    requires_human_review: Literal[True] = True
    status: Literal['pending_review'] = 'pending_review'
    warnings: list[str]
    limitations: list[str]


class ResumeRecommendationResponse(_AIEndpointResponse):
    pass


class AIReviewResponse(_AIEndpointResponse):
    research_report: ResearchReport | None
    critic_reports: dict[str, CriticReport] | None