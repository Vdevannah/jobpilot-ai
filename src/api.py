from fastapi import FastAPI, HTTPException

from src.repository import get_all_jobs, get_job_by_id
from src.schemas import JobResponse


app = FastAPI(title="JobPilot AI")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/jobs", response_model=list[JobResponse])
def get_jobs():
    return get_all_jobs()


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
