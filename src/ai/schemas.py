"""Validated analysis and report models shared by AI components."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class JobAnalysis(BaseModel):
    model_config = ConfigDict(strict=True, revalidate_instances="always")

    required_skills: list[str]
    preferred_skills: list[str]
    minimum_experience_years: int | None
    job_track: Literal["data", "pharma", "unknown"]
    summary: str


class ResumeAnalysis(BaseModel):
    """Resume facts; experience stays separate by track, with unknown entries absent.

    Education and training alone do not establish professional employment years.
    Experience keys can match CandidateProfile.experience_by_domain (pharma/data).
    """

    model_config = ConfigDict(strict=True, revalidate_instances="always")

    skills: list[str]
    professional_experience_years: dict[str, float]
    domains: list[str]
    education: list[str]
    summary: str


class ResearchReport(BaseModel):
    model_config = ConfigDict(strict=True, revalidate_instances="always")

    missing_information: list[str]
    research_questions: list[str]
    summary: str


class CriticReport(BaseModel):
    model_config = ConfigDict(strict=True, revalidate_instances="always")

    warnings: list[str]
    requires_human_review: bool
    summary: str


class WorkflowReport(BaseModel):
    model_config = ConfigDict(strict=True, revalidate_instances="always")

    job_analysis: JobAnalysis
    resume_analysis: ResumeAnalysis
    research_report: ResearchReport
    critic_report: CriticReport
    requires_human_review: bool
    status: Literal["pending_review"]
    analysis_mode: Literal["mock"]
