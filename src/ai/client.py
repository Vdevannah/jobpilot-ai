"""Client contract and an offline sample implementation."""

from typing import Protocol

from src.ai.schemas import JobAnalysis, ResumeAnalysis


class LLMClient(Protocol):
    def analyze_job(self, description: str) -> JobAnalysis:
        """Return structured analysis for a job description."""
        ...


class MockLLMClient:
    """Return fixed sample data without analyzing the description or calling AI."""

    def analyze_job(self, description: str) -> JobAnalysis:
        return JobAnalysis(
            required_skills=["python", "sql"],
            preferred_skills=["aws"],
            minimum_experience_years=3,
            job_track="data",
            summary=(
                "MOCK SAMPLE: A data role requiring Python, SQL, and 3 years "
                "of experience, with AWS preferred. This is fixed sample data, "
                "not genuine AI analysis of the supplied description."
            ),
        )


class ResumeLLMClient(Protocol):
    def analyze_resume(self, resume_text: str) -> ResumeAnalysis:
        """Return resume facts without combining tracks or inventing experience.

        Omit unknown experience entries; education/training alone is not employment.
        """
        ...


class MockResumeLLMClient:
    """Return fixed sample data without extracting facts from the supplied resume."""

    def analyze_resume(self, resume_text: str) -> ResumeAnalysis:
        return ResumeAnalysis(
            skills=["medicinal chemistry", "python"],
            professional_experience_years={"pharma": 8.0, "data": 1.0},
            domains=["drug discovery", "data analysis"],
            education=["PhD in Chemistry (sample education)"],
            summary=(
                "MOCK SAMPLE: Fictional candidate with 8 years of pharmaceutical "
                "employment and 1 year of data employment, kept separate. "
                "Education is not counted as employment. This is fixed sample "
                "data, not actual resume extraction."
            ),
        )
