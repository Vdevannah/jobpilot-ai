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

from src.ai.api_schemas import AIReviewResponse, JobRequirementsResponse, ResumeRecommendationResponse
from src.ai.job_requirements import extract_job_requirements
from src.ai.mock_fixtures import FICTIONAL_RESUME_VARIANTS
from src.ai.orchestrator import create_workflow
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
    allow_methods=["GET"],
    allow_headers=["*"],
)

MAX_PAGE_SIZE = 100
MOCK_ANALYSIS_WARNING = (
    "The job analysis is fixed mock sample output and does not analyze the stored description."
)
MOCK_ANALYSIS_LIMITATION = (
    "Resume evidence is fictional structured fixture data; this is not a verified or personalized recommendation."
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
