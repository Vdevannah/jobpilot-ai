"""Read-only FastAPI dashboard backend over the existing job-discovery and
deterministic matching engine (src.matching, src.candidate, src.repository).

job_track note (Phase 7G vs. Phase 1-6): the `job_track` returned by GET
/matches, and filterable via its `job_track` query parameter, is the
DETERMINISTIC classification from `src.matching.determine_job_track` --
simple keyword matching over a job's title/description, limited to the
values "pharma", "data", or null (no track detected). This is a separate,
unrelated concept from Phase 7's AI-derived `JobAnalysis.job_track` in
`src.ai.schemas` (set by an LLM client, or advisable via
`src.ai.job_track_classifier.classify_scientific_ai`, and also recognizing
"scientific_ai" and "unknown"). The two are never merged or cross-referenced
here; this API only ever surfaces the deterministic one. GET /jobs has no
job_track parameter at all, since the Job database model has no stored
track -- only /matches computes one, by running the matcher.
"""

from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.ai.agents.job_agent import JobAnalysisAgent
from src.ai.api_schemas import (
    AIReviewResponse,
    ApplicationAssistanceRequest,
    ApplicationAssistanceResponse,
    JobRequirementsResponse,
    PersonalizedAnalysisRequest,
    PersonalizedAnalysisResponse,
    RequirementComparisonAPIResponse,
    ResumePreviewRequest,
    ResumePreviewResponse,
    ResumeRecommendationResponse,
)
from src.ai.candidate_evidence_fixtures import (
    DEFAULT_DEMO_CANDIDATE,
    DEFAULT_DEMO_CANDIDATE_ID,
    DEFAULT_DEMO_CANDIDATE_LABEL,
)
from src.ai.client import MockLLMClient
from src.ai.job_requirements import extract_job_requirements
from src.ai.mock_fixtures import FICTIONAL_RESUME_VARIANTS
from src.ai.openai_client import OpenAIJobClient
from src.ai.orchestrator import create_workflow
from src.ai.personalized_client import (
    MockApplicationAssistanceClient,
    MockCandidateEvidenceClient,
    OpenAIApplicationAssistanceClient,
    OpenAICandidateEvidenceClient,
    summarize_job_requirements,
)
from src.ai.requirement_matcher import compare_requirements
from src.ai.resume_privacy import ResumePrivacyError, approve_resume, preview_resume
from src.candidate import candidate_profile
from src.demo_record import is_demo_record
from src.matching import match_job
from src.repository import get_all_jobs, get_job_by_id
from src.schemas import JobDetailResponse, JobResponse, MatchResponse


app = FastAPI(title="JobPilot AI")

# Explicit local-development allowlist for a React/Vite dashboard. Vite's
# default dev port is 5173, but it silently falls back to the next free port
# (5174, 5175, ...) when an earlier one is already taken by another local
# project, so known fallback ports used during this project's development
# are listed alongside it. Both the localhost and 127.0.0.1 forms are listed
# for each port because browsers treat them as distinct origins. No wildcard
# origins are used, and no credentialed requests are expected (there is no
# auth layer), so allow_credentials stays False.
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Vite falls back to the next free port when 5173/5174 are already in
    # use by another local project; 5175 is this frontend's current dev port.
    "http://localhost:5175",
    "http://127.0.0.1:5175",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    # POST is needed for the Phase 9C personalized-analysis endpoints, which
    # take resume text in the request body rather than query parameters;
    # they still never accept credentials and are not state-changing on the
    # server (no database writes), only compute-and-return.
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

MAX_PAGE_SIZE = 100
MOCK_ANALYSIS_WARNING = (
    "The job analysis is fixed mock sample output and does not analyze the stored description."
)
MOCK_ANALYSIS_LIMITATION = (
    "Resume evidence is fictional structured fixture data; this is not a verified or personalized recommendation."
)
REQUIREMENT_COMPARISON_LIMITATIONS = [
    "This compares the job posting against a fixed FICTIONAL candidate evidence fixture, not the "
    "user's actual resume or any real candidate data. No real resume was read, processed, or "
    "compared on this path.",
    "A job that is not a known example.com demo record is not thereby proven to be currently live "
    "or still accepting applications.",
]
PERSONALIZED_ANALYSIS_LIMITATIONS = [
    "This is a personalized analysis of the resume text you explicitly reviewed and approved in "
    "this same request -- it is not sent anywhere else, not stored in the database, and not "
    "reused for any other job or request.",
    "Live AI interpretation (live_job_analysis) and deterministic evidence comparison "
    "(requirement_comparison) are produced independently and may disagree; neither overrides the "
    "other, and both still require your own human review before acting on them.",
]
OPENAI_UNAVAILABLE_DETAIL = (
    "Live OpenAI analysis is unavailable. Confirm OPENAI_API_KEY is set in the backend "
    "environment and that the OpenAI API is reachable, or retry with mode=\"mock\"."
)


def _text_filter_matches(filter_value: str | None, field_value: str | None) -> bool:
    """Case-insensitive substring match; no filter means everything matches."""
    if filter_value is None:
        return True
    return filter_value.strip().lower() in (field_value or "").lower()


def _paginate(items: list, *, limit: int | None, offset: int | None) -> list:
    start = offset or 0
    end = start + limit if limit is not None else None
    return items[start:end]


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/jobs", response_model=list[JobResponse])
def get_jobs(
    location: str | None = Query(default=None, min_length=1, description="Case-insensitive substring match."),
    source: str | None = Query(default=None, min_length=1, description="Case-insensitive exact match, e.g. 'greenhouse'."),
    limit: int | None = Query(default=None, ge=1, le=MAX_PAGE_SIZE),
    offset: int | None = Query(default=None, ge=0),
):
    """List jobs. With no parameters, behavior is unchanged from before."""
    jobs = sorted(get_all_jobs(), key=lambda job: job.id)
    jobs = [
        job for job in jobs
        if _text_filter_matches(location, job.location) and _text_filter_matches(source, job.source)
    ]
    return _paginate(jobs, limit=limit, offset=offset)


@app.get(
    "/jobs/{job_id}",
    response_model=JobDetailResponse,
    responses={404: {"description": "Job not found"}},
)
def get_job(job_id: int):
    job = get_job_by_id(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


def _mock_resume_recommendation(job_id: int):
    job = get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    description = job.description
    if not isinstance(description, str) or not description.strip():
        return job, None, None

    try:
        workflow = create_workflow("mock")
        report = workflow.rank_resumes_for_job(description, FICTIONAL_RESUME_VARIANTS)
        return job, workflow, report
    except Exception:
        raise HTTPException(status_code=503, detail="Mock AI analysis unavailable.") from None


@app.get(
    "/jobs/{job_id}/resume-recommendation",
    response_model=ResumeRecommendationResponse,
    responses={404: {"description": "Job not found"}, 503: {"description": "Mock analysis unavailable"}},
)
def get_resume_recommendation(job_id: int):
    job, _, report = _mock_resume_recommendation(job_id)
    available = report is not None
    return ResumeRecommendationResponse(
        job_id=job.id,
        job_analysis=report.job_analysis if available else None,
        recommendation=report.recommendation if available else None,
        evidence_source="fictional_mock_fixture" if available else "not_available",
        warnings=[MOCK_ANALYSIS_WARNING] if available else [
            "Job description is missing; no job analysis or resume ranking was produced."
        ],
        limitations=[MOCK_ANALYSIS_LIMITATION],
    )


@app.get(
    "/jobs/{job_id}/ai-review",
    response_model=AIReviewResponse,
    responses={404: {"description": "Job not found"}, 503: {"description": "Mock analysis unavailable"}},
)
def get_ai_review(job_id: int):
    job, workflow, report = _mock_resume_recommendation(job_id)
    if report is None:
        return AIReviewResponse(
            job_id=job.id,
            job_analysis=None,
            recommendation=None,
            evidence_source="not_available",
            warnings=["Job description is missing; no AI review or resume ranking was produced."],
            limitations=[MOCK_ANALYSIS_LIMITATION],
            research_report=None,
            critic_reports=None,
        )

    try:
        research = workflow.research_agent.analyze(report.job_analysis)
        critics = {
            variant: workflow.critic_agent.analyze(report.job_analysis, resume_analysis)
            for variant, resume_analysis in FICTIONAL_RESUME_VARIANTS.items()
        }
    except Exception:
        raise HTTPException(status_code=503, detail="Mock AI review unavailable.") from None

    warnings = [MOCK_ANALYSIS_WARNING]
    warnings.extend(warning for critic in critics.values() for warning in critic.warnings)
    return AIReviewResponse(
        job_id=job.id,
        job_analysis=report.job_analysis,
        recommendation=report.recommendation,
        evidence_source="fictional_mock_fixture",
        warnings=list(dict.fromkeys(warnings)),
        limitations=[MOCK_ANALYSIS_LIMITATION],
        research_report=research,
        critic_reports=critics,
    )


@app.get(
    "/jobs/{job_id}/requirements",
    response_model=JobRequirementsResponse,
    responses={404: {"description": "Job not found"}},
)
def get_job_requirements(job_id: int):
    """Deterministic structured-requirement extraction over this job's own
    stored description (src.ai.job_requirements) -- unlike
    resume-recommendation/ai-review above, this analyzes the job's actual
    text rather than returning fixed mock output, but it is still never a
    live OpenAI call: extract_job_requirements() is pure, offline,
    regex/keyword-based analysis, called here exactly as it is defined.
    Never writes to the database; never fetches a fresh description from
    the job's original posting site.
    """
    job = get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    requirements = extract_job_requirements(job.id, job.title, job.description)
    return JobRequirementsResponse(
        requirements=requirements,
        is_demo_record=is_demo_record(job.url),
        source=job.source,
    )


@app.get(
    "/jobs/{job_id}/requirement-comparison",
    response_model=RequirementComparisonAPIResponse,
    responses={404: {"description": "Job not found"}},
)
def get_job_requirement_comparison(job_id: int):
    """Deterministic comparison (src.ai.requirement_matcher) of this job's
    own extracted requirements against one fixed, fictional CandidateEvidence
    fixture -- never the user's actual resume. Like /jobs/{job_id}/requirements,
    this analyzes the job's real stored description, not fixed mock output,
    but it is still never a live OpenAI call and never writes to the database.
    """
    job = get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    requirements = extract_job_requirements(job.id, job.title, job.description)
    comparison = compare_requirements(requirements, DEFAULT_DEMO_CANDIDATE)
    return RequirementComparisonAPIResponse(
        requirement_comparison=comparison,
        candidate_id=DEFAULT_DEMO_CANDIDATE_ID,
        candidate_label=DEFAULT_DEMO_CANDIDATE_LABEL,
        is_demo_record=is_demo_record(job.url),
        source=job.source,
        limitations=REQUIREMENT_COMPARISON_LIMITATIONS,
    )


def _candidate_evidence_client(mode: str):
    if mode == "mock":
        return MockCandidateEvidenceClient()
    try:
        return OpenAICandidateEvidenceClient()
    except Exception:
        raise HTTPException(status_code=503, detail=OPENAI_UNAVAILABLE_DETAIL) from None


def _job_analysis_client(mode: str):
    if mode == "mock":
        return MockLLMClient()
    try:
        return OpenAIJobClient()
    except Exception:
        raise HTTPException(status_code=503, detail=OPENAI_UNAVAILABLE_DETAIL) from None


def _application_assistance_client(mode: str):
    if mode == "mock":
        return MockApplicationAssistanceClient()
    try:
        return OpenAIApplicationAssistanceClient()
    except Exception:
        raise HTTPException(status_code=503, detail=OPENAI_UNAVAILABLE_DETAIL) from None


@app.post("/resume/preview", response_model=ResumePreviewResponse)
def preview_resume_text(request: ResumePreviewRequest):
    """Local-only sanitization preview (src.ai.resume_privacy.preview_resume).

    Never calls OpenAI and never persists `resume_text` anywhere -- nothing
    here writes to the database, and the sanitized `preview` string in the
    response is the only trace of this call, held only by the caller until
    they explicitly resubmit it with `confirmed=True` to one of the
    personalized-analysis endpoints below. The caller supplies `resume_text`
    directly; this backend never reads any local file, including anything
    under private_resumes/.
    """
    try:
        preview = preview_resume(request.resume_text, identifiers=request.identifiers)
    except ResumePrivacyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    return ResumePreviewResponse(preview=preview)


def _approve_or_400(request) -> str:
    try:
        return approve_resume(
            request.preview_text, confirmed=request.confirmed, include_citations=request.include_citations,
        )
    except ResumePrivacyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None


@app.post(
    "/jobs/{job_id}/personalized-analysis",
    response_model=PersonalizedAnalysisResponse,
    responses={
        400: {"description": "Resume not approved or invalid"},
        404: {"description": "Job not found"},
        503: {"description": "AI analysis unavailable"},
    },
)
def get_personalized_analysis(job_id: int, request: PersonalizedAnalysisRequest):
    """Personalized, evidence-based comparison against the caller's OWN
    approved resume text -- never the fictional fixture used by
    GET /jobs/{job_id}/requirement-comparison. Approval
    (resume_privacy.approve_resume) happens fresh in this one request; no
    prior approval state is trusted or stored. `mode="mock"` (the default)
    makes no OpenAI request at all; only `mode="openai"` does, and only
    because the caller explicitly asked for it here.

    The job's own requirements are still extracted deterministically
    (src.ai.job_requirements, same as the read-only GET endpoints above) --
    this never depends on OpenAI. Comparison reuses
    src.ai.requirement_matcher.compare_requirements() unchanged; only the
    candidate evidence source is new. `live_job_analysis` is a SEPARATE,
    independent interpretation of the job's own stored description (never
    of the resume), clearly distinguished by field name and by its own
    analysis_mode semantics from the deterministic comparison alongside it.
    """
    job = get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    approved = _approve_or_400(request)

    evidence_client = _candidate_evidence_client(request.mode)
    try:
        candidate_evidence = evidence_client.analyze_resume(approved)
    except Exception:
        raise HTTPException(status_code=503, detail="Resume analysis unavailable.") from None

    requirements = extract_job_requirements(job.id, job.title, job.description)
    comparison = compare_requirements(requirements, candidate_evidence)

    live_job_analysis = None
    if isinstance(job.description, str) and job.description.strip():
        job_client = _job_analysis_client(request.mode)
        try:
            live_job_analysis = JobAnalysisAgent(job_client).analyze(job.description)
        except Exception:
            raise HTTPException(status_code=503, detail="Live job analysis unavailable.") from None

    variant_matches_job_track = (
        None if requirements.career_track == "unknown" else requirements.career_track == request.variant
    )

    return PersonalizedAnalysisResponse(
        job_id=job.id,
        variant=request.variant,
        variant_matches_job_track=variant_matches_job_track,
        live_job_analysis=live_job_analysis,
        requirement_comparison=comparison,
        analysis_mode=request.mode,
        limitations=PERSONALIZED_ANALYSIS_LIMITATIONS,
    )


@app.post(
    "/jobs/{job_id}/application-assistance",
    response_model=ApplicationAssistanceResponse,
    responses={
        400: {"description": "Resume not approved or invalid"},
        404: {"description": "Job not found"},
        503: {"description": "AI analysis unavailable"},
    },
)
def get_application_assistance(job_id: int, request: ApplicationAssistanceRequest):
    """Optional, user-triggered resume-suggestion/cover-letter/interview-prep
    assistance grounded only in the caller's own approved resume evidence
    and this job's deterministically extracted requirements. Never writes
    to the database, never modifies any original resume, and never submits
    an application -- it only returns a draft for the caller's own review.
    """
    job = get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    approved = _approve_or_400(request)

    evidence_client = _candidate_evidence_client(request.mode)
    try:
        candidate_evidence = evidence_client.analyze_resume(approved)
    except Exception:
        raise HTTPException(status_code=503, detail="Resume analysis unavailable.") from None

    requirements = extract_job_requirements(job.id, job.title, job.description)
    summary = summarize_job_requirements(requirements)

    assistance_client = _application_assistance_client(request.mode)
    try:
        assistance = assistance_client.generate(summary, candidate_evidence)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Application assistance unavailable.") from None

    return ApplicationAssistanceResponse(job_id=job.id, variant=request.variant, assistance=assistance)


@app.get("/matches", response_model=list[MatchResponse])
def get_matches(
    location: str | None = Query(default=None, min_length=1, description="Case-insensitive substring match."),
    source: str | None = Query(default=None, min_length=1, description="Case-insensitive exact match, e.g. 'greenhouse'."),
    job_track: Literal["pharma", "data"] | None = Query(
        default=None,
        description="Deterministic Phase 1-6 track (src.matching), not the Phase 7 AI track.",
    ),
    min_score: float | None = Query(default=None, ge=0, le=100),
    limit: int | None = Query(default=None, ge=1, le=MAX_PAGE_SIZE),
    offset: int | None = Query(default=None, ge=0),
):
    """Rank jobs by match score. With no parameters, behavior is unchanged
    from before: every job is scored and returned, sorted by overall_score
    descending (now with a deterministic job_id tiebreak for equal scores)."""
    ranked_matches = []

    for job in get_all_jobs():
        if not (_text_filter_matches(location, job.location) and _text_filter_matches(source, job.source)):
            continue

        job_dict = {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "source": job.source,
            "description": job.description or "",
        }
        match_result = match_job(candidate_profile, job_dict)

        if job_track is not None and match_result["job_track"] != job_track:
            continue
        if min_score is not None and match_result["overall_score"] < min_score:
            continue

        ranked_matches.append(
            {
                "job_id": job.id,
                **job_dict,
                **match_result,
            }
        )

    ranked_matches.sort(key=lambda result: (-result["overall_score"], result["job_id"]))
    return _paginate(ranked_matches, limit=limit, offset=offset)
