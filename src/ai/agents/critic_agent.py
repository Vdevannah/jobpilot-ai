"""Check structured evidence without inferring employment or combining tracks."""

from math import isfinite

from src.ai.schemas import CriticReport, JobAnalysis, ResumeAnalysis


class CriticAgent:
    def analyze(self, job: JobAnalysis, resume: ResumeAnalysis) -> CriticReport:
        job = JobAnalysis.model_validate(job)
        resume = ResumeAnalysis.model_validate(resume)
        warnings = []
        required_years = job.minimum_experience_years

        if required_years is None:
            warnings.append("Job experience requirement is unspecified; do not assume zero years.")
        elif required_years < 0:
            warnings.append("Job experience requirement is invalid.")

        if job.job_track == "unknown":
            warnings.append("Job track is unknown; a track-specific experience comparison is unsupported.")
        else:
            years = resume.professional_experience_years.get(job.job_track)
            if years is None:
                warnings.append(
                    f"Candidate professional experience for {job.job_track} is missing; "
                    "do not assume zero or substitute education or another track."
                )
            elif not isfinite(years) or years < 0:
                warnings.append(f"Candidate professional experience for {job.job_track} is invalid.")
            elif required_years is not None and required_years >= 0 and years < required_years:
                warnings.append(
                    f"Experience gap for {job.job_track}: candidate has {years:g} years; "
                    f"job requires {required_years} years."
                )

        if not job.required_skills or any(not skill.strip() for skill in job.required_skills):
            warnings.append("Required job skills are absent or unclear; skill alignment is uncertain.")
        candidate_skills = {skill.strip().casefold() for skill in resume.skills if skill.strip()}
        if not candidate_skills:
            warnings.append("Candidate skill evidence is missing.")
        missing_skills = sorted({
            skill.strip().casefold() for skill in job.required_skills
            if skill.strip() and skill.strip().casefold() not in candidate_skills
        })
        if missing_skills:
            warnings.append("Required skills not evidenced in the resume: " + ", ".join(missing_skills) + ".")

        if any(
            marker in summary.casefold()
            for summary in (job.summary, resume.summary)
            for marker in ("mock", "sample", "fictional", "fake")
        ):
            warnings.append("Analysis is labeled as mock or sample data; it cannot support a real recommendation.")

        return CriticReport(
            warnings=warnings,
            requires_human_review=bool(warnings),
            summary=(
                "Available evidence does not support an automated recommendation without human review."
                if warnings else
                "The supplied skills and track-specific experience support an automated preliminary assessment."
            ) + " These checks do not verify source accuracy or establish overall suitability.",
        )
