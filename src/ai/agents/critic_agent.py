"""Check structured evidence without inferring employment or combining tracks."""

from math import isfinite
import re

from src.ai.job_track_classifier import classify_scientific_ai
from src.ai.schemas import CriticReport, JobAnalysis, ResumeAnalysis


def _normalize(text: str) -> str:
    text = re.sub(r"\bph\.?\s*d\.?\b", "phd", text.casefold())
    text = re.sub(r"[^\w+#]+", " ", text).strip()
    text = re.sub(r"^(?:expertise|experience|proficiency) (?:in|with) ", "", text)
    return text


def _skill(text: str) -> str:
    text = _normalize(text)
    aliases = {
        "sar": "sar", "structure activity relationship": "sar",
        "structure activity relationships": "sar", "sar analysis": "sar",
        "structure activity relationship analysis": "sar",
        "protac": "protac", "protacs": "protac",
        "proteolysis targeting chimera": "protac", "proteolysis targeting chimeras": "protac",
        "tpd": "tpd", "targeted protein degradation": "tpd",
    }
    return aliases.get(text, text)


def _is_education(text: str) -> bool:
    return bool(re.match(r"^(?:phd|doctorate|doctor of philosophy|bachelor|master)\b", _normalize(text)))


def _is_experience(text: str) -> bool:
    return bool(re.search(r"\b\d+(?:\.\d+)?\s*\+?\s*years?\b", text.casefold()))


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
            if classify_scientific_ai(job.required_skills, job.preferred_skills, job.summary):
                warnings.append(
                    "Required/preferred skills and summary show combined scientific-domain and "
                    "computational/AI signals consistent with a Scientific AI / Cheminformatics role; "
                    "consider human reclassification to scientific_ai. This is a suggestion only and "
                    "does not change job_track automatically."
                )
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
        education = [skill for skill in job.required_skills if _is_education(skill)]
        education.extend(re.findall(r"Required education:\s*([^\n]+?)(?:\.(?:\s|$)|$)", job.summary, re.I))
        for qualification in dict.fromkeys(education):
            expected = _normalize(qualification)
            if not any(expected == _normalize(item) for item in resume.education):
                warnings.append(f"Required education not evidenced in the resume: {qualification}.")
        legacy_experience = [skill for skill in job.required_skills if _is_experience(skill)]
        if legacy_experience and required_years is None:
            warnings.append("Experience appears in skill fields without a structured minimum; insufficient evidence for comparison.")
        candidate_skills = {_skill(skill) for skill in resume.skills if skill.strip()}
        if not candidate_skills:
            warnings.append("Candidate skill evidence is missing.")
        missing_skills = sorted({
            skill.strip().casefold() for skill in job.required_skills
            if skill.strip() and not _is_education(skill) and not _is_experience(skill)
            and _skill(skill) not in candidate_skills
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
