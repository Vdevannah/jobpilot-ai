"""Rank resume presentations after opportunity evaluation; never filter jobs."""

from collections.abc import Mapping
from math import isfinite
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.ai.agents.critic_agent import _is_education, _is_experience, _normalize, _skill
from src.ai.schemas import JobAnalysis, ResumeAnalysis

Variant = Literal['pharma', 'data', 'scientific_ai']
VARIANTS = ('pharma', 'data', 'scientific_ai')
TRACK_DOMAINS = {
    'pharma': {'pharma', 'pharmaceutical research', 'medicinal chemistry', 'drug discovery', 'oncology'},
    'data': {'data', 'data science', 'data engineering', 'analytics', 'data analytics',
             'business analysis', 'business intelligence', 'software engineering'},
    'scientific_ai': {'scientific_ai', 'cheminformatics', 'computational chemistry',
                       'computational drug discovery', 'molecular machine learning'},
}


class ResumeRanking(BaseModel):
    model_config = ConfigDict(strict=True)
    variant: Variant
    score: int
    matched_evidence: list[str]
    missing_evidence: list[str]
    reasons: list[str]
    limitations: list[str]


class ResumeRecommendation(BaseModel):
    rankings: list[ResumeRanking]
    recommended_variant: Variant | None
    tied_variants: list[Variant]
    insufficient_evidence: bool
    limitations: list[str]
    requires_human_review: Literal[True] = True
    status: Literal['pending_review'] = 'pending_review'


def recommend_resume(job: JobAnalysis, variants: Mapping[str, ResumeAnalysis]) -> ResumeRecommendation:
    """Score supplied variants independently; identifiers confer no scoring bonus."""
    job = JobAnalysis.model_validate(job)
    if not variants or any(name not in VARIANTS for name in variants):
        raise ValueError('Supply at least one of pharma, data, scientific_ai.')
    resumes = {name: ResumeAnalysis.model_validate(value) for name, value in variants.items()}
    required = {_skill(s) for s in job.required_skills if s.strip() and not _is_education(s) and not _is_experience(s)}
    preferred = {_skill(s) for s in job.preferred_skills if s.strip() and not _is_education(s) and not _is_experience(s)} - required
    education = {_normalize(s) for s in job.required_skills if _is_education(s)}
    education.update(_normalize(s) for s in re.findall(
        r'Required education:\s*([^\n]+?)(?:\.(?:\s|$)|$)', job.summary, re.I))
    conflicts = set()
    for track in VARIANTS:
        claims = {r.professional_experience_years[track] for r in resumes.values()
                  if track in r.professional_experience_years}
        if len(claims) > 1:
            conflicts.add(track)
    limitations = ['Scores compare resume evidence, not candidate suitability or hiring probability.',
                   'Skills have no employment/project provenance; education uses conservative text matching.']
    limitations.extend(f'Conflicting {track} employment claims: no experience points for this track.' for track in sorted(conflicts))
    rankings = []
    direct_scores = []
    for name in VARIANTS:
        if name not in resumes:
            continue
        resume = resumes[name]
        skills = {_skill(s) for s in resume.skills if s.strip()}
        matched, missing, reasons, limits = [], [], [], []
        score = 0
        for label, expected, available, points in (
            ('Required skill', required, skills, 4),
            ('Preferred skill', preferred, skills, 1),
            ('Required education', education, {_normalize(s) for s in resume.education}, 2),
        ):
            hits = expected & available
            matched.extend(f'{label}: {s}' for s in sorted(hits))
            missing.extend(f'{label}: {s}' for s in sorted(expected - available))
            score += len(hits) * points
            reasons.append(f'{label}: {len(hits)} matched x {points} points.')
        years = resume.professional_experience_years.get(job.job_track)
        minimum = job.minimum_experience_years
        if job.job_track == 'unknown':
            limits.append('Unknown job track; professional experience cannot be compared.')
        elif job.job_track in conflicts:
            limits.append('Conflicting employment evidence requires human reconciliation; no claims merged.')
        elif years is None:
            missing.append(f'Professional experience for {job.job_track}: not evidenced, not assumed zero.')
        elif not isfinite(years) or years < 0:
            limits.append('Invalid professional experience years; no experience points.')
        elif minimum is not None and minimum >= 0:
            if years >= minimum:
                score += 2
                matched.append(f'Professional experience for {job.job_track}: {years:g} years meets {minimum}.')
                reasons.append('Track-specific minimum met: 2 points.')
            else:
                missing.append(f'Experience gap for {job.job_track}: {years:g} years evidenced, {minimum} required.')
        if minimum is None or minimum < 0:
            limits.append('No valid structured experience minimum; no experience points.')
        direct_scores.append(score)
        domains = {_normalize(s) for s in resume.domains} & TRACK_DOMAINS.get(job.job_track, set())
        if domains:
            score += 1
            matched.append('Track domain: ' + ', '.join(sorted(domains)))
            reasons.append('Explicit track-domain relevance: 1 point (capped).')
        limits.append('No employment inferred from education, skills, projects, training, or resume name.')
        rankings.append(ResumeRanking(variant=name, score=score, matched_evidence=matched,
                                      missing_evidence=missing, reasons=reasons, limitations=limits))
    rankings.sort(key=lambda item: (-item.score, VARIANTS.index(item.variant)))
    insufficient = not any(direct_scores)
    leaders = [row.variant for row in rankings if row.score == rankings[0].score]
    return ResumeRecommendation(
        rankings=rankings, recommended_variant=leaders[0] if len(leaders) == 1 and not insufficient else None,
        tied_variants=leaders if len(leaders) > 1 else [], insufficient_evidence=insufficient,
        limitations=limitations,
    )
