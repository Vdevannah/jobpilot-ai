from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: str
    url: str
    source: str

    model_config = ConfigDict(from_attributes=True)


class MatchResponse(BaseModel):
    job_id: int
    title: str
    company: str
    location: str
    url: str

    overall_score: float
    recommendation: str
    job_track: str | None

    skill_score: float
    experience_score: float
    role_score: float
    domain_score: float
    location_score: float

    candidate_years: float
    required_years: int | None

    matched_skills: list[str]
    missing_skills: list[str]
    reasons: list[str]
