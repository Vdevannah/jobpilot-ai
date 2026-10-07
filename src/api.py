from fastapi import FastAPI, HTTPException

from src.candidate import candidate_profile
from src.matching import match_job
from src.repository import get_all_jobs, get_job_by_id
from src.schemas import JobResponse, MatchResponse


app = FastAPI(title="JobPilot AI")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/jobs", response_model=list[JobResponse])
def get_jobs():
    return get_all_jobs()


@app.get("/matches", response_model=list[MatchResponse])
def get_matches():
    ranked_matches = []

    for job in get_all_jobs():
        job_dict = {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "source": job.source,
            "description": job.description or "",
        }
        match_result = match_job(candidate_profile, job_dict)
        ranked_matches.append(
            {
                "job_id": job.id,
                **job_dict,
                **match_result,
            }
        )

    return sorted(
        ranked_matches,
        key=lambda result: result["overall_score"],
        reverse=True,
    )


@app.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    responses={404: {"description": "Job not found"}},
)
def get_job(job_id: int):
    job = get_job_by_id(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job
