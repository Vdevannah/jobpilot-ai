"""Fictional structured candidate evidence for local testing of
src.ai.requirement_matcher only. Every name, employer, and project below is
invented for this fixture file; none of it is derived from any real
resume, and nothing under private_resumes/ was read to produce it (mirrors
the existing convention in src/ai/mock_fixtures.py).
"""

from src.ai.candidate_evidence import CandidateEvidence, CandidateEvidenceItem, EmploymentPeriod

EMPTY_CANDIDATE_EVIDENCE = CandidateEvidence(items=[])

# Fictional Candidate A -- a career-transition candidate with Python/SQL
# training and portfolio projects, but no documented professional data
# engineering employment. Used to verify training/projects can support a
# *skill* claim without ever being misread as professional experience.
CAREER_TRANSITION_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Python",
        source_category="technical_training",
        career_track="data",
        detail="Completed 'Python for Data Engineering' online certificate course (fictional).",
    ),
    CandidateEvidenceItem(
        claim="SQL",
        source_category="technical_training",
        career_track="data",
        detail="Completed 'SQL for Data Analysis' online certificate course (fictional).",
    ),
    CandidateEvidenceItem(
        claim="Python",
        source_category="portfolio_project",
        career_track="data",
        detail="Built a personal ETL pipeline project using Python and SQL (fictional, unpublished).",
    ),
    CandidateEvidenceItem(
        claim="Kafka",
        source_category="portfolio_project",
        career_track="data",
        detail="Experimented with Kafka in a personal side project (fictional).",
    ),
])

# Fictional Candidate B -- documented professional experience in a single,
# non-overlapping role, plus a qualifying degree. Used for the
# straightforward "supported" path, including an education-gated
# alternative-experience match.
EXPERIENCED_QUALIFIED_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Analytics Corp",
        source_category="professional_experience",
        career_track="data",
        detail="Six years as a data engineer at a fictional company.",
        professional_experience_years=6.0,
        employment_period=EmploymentPeriod(start_year=2018.0, end_year=2024.0),
        professional_skills=["Python", "SQL", "AWS"],
        professional_skill_years={"Python": 6.0, "SQL": 6.0, "AWS": 6.0},
    ),
    CandidateEvidenceItem(
        claim="MS in Computer Science (fictional)",
        source_category="education",
        detail="Fictional graduate degree.",
    ),
])

# Fictional Candidate D -- professional Python use explicitly documented on
# a role, WITH its own skill-specific duration stated (not just inherited
# from the role's overall tenure). The counterpart to Candidate E below:
# the only difference is whether "Python" appears in professional_skills.
PROFESSIONAL_PYTHON_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Streaming Co",
        source_category="professional_experience",
        career_track="data",
        detail="Fictional role with explicitly documented Python use.",
        professional_experience_years=5.0,
        employment_period=EmploymentPeriod(start_year=2019.0, end_year=2024.0),
        professional_skills=["Python", "SQL"],
        professional_skill_years={"Python": 5.0, "SQL": 5.0},
    ),
])

# Fictional Candidate E -- a "Data Engineer" title and documented data
# employment, but Python is never asserted among professional_skills. Used
# to verify a generic job title never implies a skill.
DATA_EMPLOYMENT_WITHOUT_PYTHON_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Warehouse Co",
        source_category="professional_experience",
        career_track="data",
        detail="Fictional role; only SQL is explicitly documented as used professionally.",
        professional_experience_years=5.0,
        employment_period=EmploymentPeriod(start_year=2019.0, end_year=2024.0),
        professional_skills=["SQL"],
        professional_skill_years={"SQL": 5.0},
    ),
])

# Fictional Candidate D2 -- Python explicitly listed among professional_skills
# on a 5-year role, but with NO skill-specific duration recorded. Used to
# verify the role's tenure is never silently inherited by the skill.
UNSPECIFIED_SKILL_DURATION_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Unspecified Co",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=5.0,
        employment_period=EmploymentPeriod(start_year=2019.0, end_year=2024.0),
        professional_skills=["Python"],
    ),
])

# Fictional Candidate D3 -- Python used professionally for only part of a
# longer role's tenure, explicitly stated as such.
PARTIAL_SKILL_DURATION_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Partial Co",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=5.0,
        employment_period=EmploymentPeriod(start_year=2019.0, end_year=2024.0),
        professional_skills=["Python"],
        professional_skill_years={"Python": 2.0},
    ),
])

# Fictional Candidate D4 -- two non-overlapping roles, each with Python
# explicitly used for a stated, partial duration, summing to a total that
# meets a typical "5+ years of Python" requirement.
NON_OVERLAPPING_PYTHON_ROLES_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Data Analyst, Fictional First Co",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=3.0,
        employment_period=EmploymentPeriod(start_year=2015.0, end_year=2018.0),
        professional_skills=["Python"],
        professional_skill_years={"Python": 3.0},
    ),
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Second Co",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=4.0,
        employment_period=EmploymentPeriod(start_year=2018.0, end_year=2022.0),
        professional_skills=["Python"],
        professional_skill_years={"Python": 3.0},
    ),
])

# Fictional Candidate D5 -- two roles with overlapping employment periods,
# both documenting Python use with stated skill-specific durations. Must
# never be summed; the overlap alone forces requires_review.
OVERLAPPING_PYTHON_ROLES_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Data Analyst, Fictional Overlap Co A",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=3.0,
        employment_period=EmploymentPeriod(start_year=2019.0, end_year=2022.0),
        professional_skills=["Python"],
        professional_skill_years={"Python": 3.0},
    ),
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Overlap Co B",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=4.0,
        employment_period=EmploymentPeriod(start_year=2020.0, end_year=2023.0),
        professional_skills=["Python"],
        professional_skill_years={"Python": 4.0},
    ),
])

# Fictional Candidate F -- a Python portfolio project with no professional
# employment at all. The simplest possible "training/project only" case.
PYTHON_PORTFOLIO_ONLY_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Python",
        source_category="portfolio_project",
        detail="Personal data-visualization project built with Python (fictional, unpublished).",
    ),
])

# Fictional Candidate G -- two literally duplicated role entries (same
# employer, years, and dates). Used to verify duplicates are never summed
# into double the actual experience.
DUPLICATE_ROLE_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Duplicate Co",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=4.0,
        employment_period=EmploymentPeriod(start_year=2020.0, end_year=2024.0),
    ),
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Duplicate Co",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=4.0,
        employment_period=EmploymentPeriod(start_year=2020.0, end_year=2024.0),
    ),
])

# Fictional Candidate H -- a single, currently ongoing role (no end date).
# Used to confirm an open employment_period never blocks a normal,
# single-role comparison and is never used to invent an end date.
ONGOING_EMPLOYMENT_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Ongoing Co",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=5.0,
        employment_period=EmploymentPeriod(start_year=2019.0, end_year=None),
    ),
])

# Fictional Candidate I -- two roles for the same track where one is still
# ongoing (open-ended) and overlaps the other's start. The open end must
# never be read as "already over," so this must still resolve to
# requires_review, not a confident sum.
ONGOING_OVERLAPPING_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Data Analyst, Fictional First Co",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=3.0,
        employment_period=EmploymentPeriod(start_year=2017.0, end_year=None),
    ),
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Second Co",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=4.0,
        employment_period=EmploymentPeriod(start_year=2020.0, end_year=2024.0),
    ),
])

# Fictional Candidate J -- two professional_experience items for the same
# track with conflicting stated years and no employment_period on either,
# so neither overlap nor a safe sum can be established.
CONFLICTING_DURATION_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Co (per resume variant 1)",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=5.0,
    ),
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Co (per resume variant 2)",
        source_category="professional_experience",
        career_track="data",
        professional_experience_years=8.0,
    ),
])

# Fictional Candidate K -- a PhD with an explicitly matching specialized
# field of study.
SPECIALIZED_EDUCATION_FIELD_MATCH_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="PhD in Organic Chemistry (fictional)",
        source_category="education",
    ),
])

# Fictional Candidate L -- a PhD, but in a different, explicitly named
# field than the one required. Degree level is sufficient; field is not.
SPECIALIZED_EDUCATION_FIELD_MISMATCH_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="PhD in Immunology (fictional)",
        source_category="education",
    ),
])

# Fictional Candidate M -- a PhD with no field of study named at all, so a
# specialized-field requirement cannot be confirmed OR denied.
UNSPECIFIED_FIELD_EDUCATION_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="PhD (fictional)",
        source_category="education",
    ),
])

# Fictional Candidate C -- conflicting/overlapping professional_experience
# evidence for the same track. Used to verify the matcher never sums
# overlapping roles into one total and instead flags requires_review.
OVERLAPPING_EXPERIENCE_CANDIDATE = CandidateEvidence(items=[
    CandidateEvidenceItem(
        claim="Data Analyst, Fictional Insights Co",
        source_category="professional_experience",
        career_track="data",
        detail="Fictional first role.",
        professional_experience_years=3.0,
        employment_period=EmploymentPeriod(start_year=2019.0, end_year=2022.0),
    ),
    CandidateEvidenceItem(
        claim="Data Engineer, Fictional Platform Inc",
        source_category="professional_experience",
        career_track="data",
        detail="Fictional second, overlapping role.",
        professional_experience_years=4.0,
        employment_period=EmploymentPeriod(start_year=2020.0, end_year=2023.0),
    ),
])

# Phase 9B.4 -- the one fixed, fictional candidate GET
# /jobs/{job_id}/requirement-comparison compares every job against. Chosen
# because it is the most "ordinary" of the fixtures above (a single,
# qualified, non-overlapping role plus a matching degree), so the endpoint's
# output is not dominated by an edge case. The id/label exist purely for
# API response labeling -- requirement_matcher.compare_requirements() never
# sees or depends on either of them.
DEFAULT_DEMO_CANDIDATE = EXPERIENCED_QUALIFIED_CANDIDATE
DEFAULT_DEMO_CANDIDATE_ID = "fictional-candidate-b-experienced-qualified"
DEFAULT_DEMO_CANDIDATE_LABEL = (
    "Fictional Candidate B -- Experienced & Qualified Data Engineer (demonstration data only, "
    "not a real person or real resume)"
)
