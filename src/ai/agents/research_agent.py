"""Identify questions from structured job data without external research."""

from src.ai.schemas import JobAnalysis, ResearchReport


class ResearchAgent:
    def analyze(self, job: JobAnalysis) -> ResearchReport:
        job = JobAnalysis.model_validate(job)
        missing = []
        questions = []

        if job.minimum_experience_years is None:
            missing.append("Minimum experience requirement is unspecified.")
            questions.append("How many years of professional experience are required?")
        elif job.minimum_experience_years < 0:
            missing.append("Minimum experience requirement is invalid.")
            questions.append("What is the correct nonnegative experience requirement?")

        if job.job_track == "unknown":
            missing.append("Job track is unknown.")
            questions.append("Is this a data or pharmaceutical role, or another track?")

        if not job.required_skills or any(not skill.strip() for skill in job.required_skills):
            missing.append("Required skills are absent or unclear.")
            questions.append("Which skills are required for this role?")

        return ResearchReport(
            missing_information=missing,
            research_questions=questions,
            summary=(
                "Follow-up is needed to clarify the supplied job requirements."
                if missing else "No missing information detected in the checked job fields."
            ) + " No external research was performed.",
        )
