"""Safe response models for local-only AI preview endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.ai.job_requirements import JobRequirements
from src.ai.personalized_client import ApplicationAssistance
from src.ai.requirement_matcher import RequirementComparisonResult
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


class RequirementComparisonAPIResponse(BaseModel):
    """GET /jobs/{job_id}/requirement-comparison's response (Phase 9B.4).

    Wraps the Phase 9B requirement_matcher's own self-contained
    RequirementComparisonResult unchanged -- comparing the job's real,
    stored description (via extract_job_requirements(), same as
    JobRequirementsResponse above) against exactly one fixed FICTIONAL
    CandidateEvidence fixture. This is never a comparison against the
    user's actual resume; no resume text of any kind is read or processed
    on this path.

    `candidate_is_fictional`/`candidate_id`/`candidate_label`/
    `comparison_scope` describe the candidate side of the comparison.
    `is_demo_record`/`source` describe the JOB side, exactly as in
    JobRequirementsResponse -- the two facts are deliberately independent:
    a real, non-demo job can still only ever be compared against this
    fictional candidate in this endpoint, and `is_demo_record=False` here
    means only "not a known example.com placeholder", never proof that the
    posting is still live or accepting applications.
    """

    model_config = ConfigDict(strict=True)

    requirement_comparison: RequirementComparisonResult
    candidate_id: str
    candidate_label: str
    candidate_is_fictional: Literal[True] = True
    comparison_scope: Literal["fictional_demo"] = "fictional_demo"
    is_demo_record: bool
    source: str | None
    limitations: list[str]


# ---------------------------------------------------------------------------
# Phase 9C: personalized, approved-resume-based live analysis. Every model
# below is additive; none of the response classes above are changed.
# ---------------------------------------------------------------------------


class ResumePreviewRequest(BaseModel):
    """POST /resume/preview's request. Stateless and local-only -- never
    calls OpenAI and never persists `resume_text` anywhere; the sanitized
    `preview` in the response is the only trace, held only in the caller's
    own memory until they explicitly approve and resubmit it.
    """

    model_config = ConfigDict(strict=True)

    resume_text: str
    identifiers: list[str] = []


class ResumePreviewResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    preview: str


class PersonalizedAnalysisRequest(BaseModel):
    """POST /jobs/{job_id}/personalized-analysis's request.

    `preview_text` must be the exact sanitized text the user reviewed from
    a prior /resume/preview call (or a hand-written equivalent) -- the
    server re-derives approval from `confirmed` in this same request rather
    than trusting any stored, prior approval state, so approval is always
    scoped to this one request (see resume_privacy.approve_resume()).
    `mode` defaults to "mock" so a client must explicitly opt into a live
    OpenAI request; it is never implied by merely calling this endpoint.
    """

    model_config = ConfigDict(strict=True)

    preview_text: str
    confirmed: bool
    variant: Literal["pharma", "data", "scientific_ai"]
    include_citations: bool = False
    mode: Literal["mock", "openai"] = "mock"


class PersonalizedAnalysisResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    job_id: int
    variant: Literal["pharma", "data", "scientific_ai"]
    variant_matches_job_track: bool | None
    live_job_analysis: JobAnalysis | None
    requirement_comparison: RequirementComparisonResult
    candidate_is_fictional: Literal[False] = False
    comparison_scope: Literal["personalized"] = "personalized"
    analysis_mode: Literal["mock", "openai"]
    requires_human_review: Literal[True] = True
    status: Literal["pending_review"] = "pending_review"
    limitations: list[str]


class ApplicationAssistanceRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    preview_text: str
    confirmed: bool
    variant: Literal["pharma", "data", "scientific_ai"]
    include_citations: bool = False
    mode: Literal["mock", "openai"] = "mock"


class ApplicationAssistanceResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    job_id: int
    variant: Literal["pharma", "data", "scientific_ai"]
    assistance: ApplicationAssistance