"""Safe response models for local-only AI preview endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.ai.job_requirements import JobRequirements
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


class JobRequirementsResponse(BaseModel):
    """GET /jobs/{job_id}/requirements's response. Deliberately separate
    from _AIEndpointResponse/ResumeRecommendationResponse/AIReviewResponse
    above -- this wraps the Phase 9A deterministic extractor's own
    self-contained JobRequirements model unchanged, rather than reshaping
    it to match the Phase 7 mock-fixture response shape (which has
    different, OpenAI-schema-driven fields and a fixed 'mock' analysis
    mode that doesn't apply here).

    `is_demo_record` and `source` are record-identity metadata about the
    job itself, kept separate from `requirements` (the extraction result)
    per design -- extract_job_requirements() never sees or depends on
    either of them. `is_demo_record=False` means only "not a known
    example.com placeholder" -- never proof that a posting is live,
    current, or still accepting applications.
    """

    model_config = ConfigDict(strict=True)

    requirements: JobRequirements
    is_demo_record: bool
    source: str | None