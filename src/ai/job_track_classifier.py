"""Deterministic Scientific AI / Cheminformatics job-track recognition.

Operates only on a job's own extracted required/preferred skills and summary
text -- never on resume content, CandidateProfile, or the separate,
unrelated deterministic job-discovery matching engine in src/matching.py
(whose own job_track concept is untouched by this module).

This is advisory, not authoritative: it never mutates JobAnalysis.job_track.
Callers (see CriticAgent) use it only to surface a human-reviewable
suggestion when job_track is already "unknown"; an already-confident
pharma/data classification from a client is never second-guessed.

Recognition requires a meaningful combination of a scientific/computational-
chemistry domain signal and a computational/AI-ML signal -- never a single
generic term alone (Python, "AI", "chemistry", or "data science" mentioned
in isolation must not trigger a match). A genuinely hybrid or ambiguous
description -- one that only juxtaposes separate pharma-style and data/ML
terms without an explicit combined signal -- deliberately does not match,
preserving uncertainty for human review rather than forcing a classification.
"""

import re

# Explicit compound phrases that alone establish Scientific AI combination
# evidence -- each phrase already combines a science-domain concept with a
# computational/AI concept, so no second signal is required.
_STRONG_PHRASES = (
    r'cheminformatics',
    r'chemoinformatics',
    r'chem[- ]informatics',
    r'computational drug discovery',
    r'computational medicinal chemistry',
    r'molecular machine learning',
    r'ai[- ]?(?:driven\s+)?drug discovery',
    r'ai[- ]?(?:driven\s+)?medicinal chemistry',
    r'molecular property prediction',
    r'machine learning[- ]driven drug discovery',
)

# Narrower computational/molecular-science domain terms. Deliberately
# excludes generic pharma terms ("medicinal chemistry", "drug discovery",
# "synthetic chemistry") that are common to conventional, non-computational
# pharma roles; those only count toward Scientific AI via the explicit
# compound _STRONG_PHRASES above, not this looser combination rule.
_COMPUTATIONAL_SCIENCE_TERMS = (
    r'computational chemistry',
    r'molecular model(?:l?ing)',
    r'molecular dynamics',
    r'molecular docking',
    r'virtual screening',
    r'structure[- ]based drug design',
    r'\bqsar\b',
    r'quantitative structure[- ]activity relationship',
    r'protein structure prediction',
    r'de novo (?:molecular )?design',
)

# Computational / AI / ML signal terms used only in combination with one of
# the domain terms above; never sufficient alone.
_AI_ML_TERMS = (
    r'machine learning',
    r'deep learning',
    r'artificial intelligence',
    r'neural network',
    r'generative model',
    r'predictive model',
    r'\bai\b',
)


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def classify_scientific_ai(
    required_skills: list[str], preferred_skills: list[str], summary: str,
) -> bool:
    """True only when science-domain and computational/AI signals combine.

    Mentioning Python, "AI", "chemistry", or "data science" alone -- or
    conventional medicinal/synthetic chemistry, general data engineering/
    data science, or business analysis text with no computational-science
    signal -- never returns True. A hybrid description that merely places
    separate pharma and data/ML terms side by side (without an explicit
    combined signal) also returns False, preserving uncertainty.
    """
    text = ' '.join([*required_skills, *preferred_skills, summary])
    if _matches_any(text, _STRONG_PHRASES):
        return True
    return _matches_any(text, _COMPUTATIONAL_SCIENCE_TERMS) and _matches_any(text, _AI_ML_TERMS)
