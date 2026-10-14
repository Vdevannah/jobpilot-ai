import pytest
from pydantic import ValidationError

from src.ai.candidate_evidence import (
    CandidateEvidence, CandidateEvidenceItem, EmploymentPeriod,
)
from src.ai.candidate_evidence_fixtures import (
    CAREER_TRANSITION_CANDIDATE,
    CONFLICTING_DURATION_CANDIDATE,
    DATA_EMPLOYMENT_WITHOUT_PYTHON_CANDIDATE,
    DUPLICATE_ROLE_CANDIDATE,
    EMPTY_CANDIDATE_EVIDENCE,
    EXPERIENCED_QUALIFIED_CANDIDATE,
    NON_OVERLAPPING_PYTHON_ROLES_CANDIDATE,
    ONGOING_EMPLOYMENT_CANDIDATE,
    ONGOING_OVERLAPPING_CANDIDATE,
    OVERLAPPING_EXPERIENCE_CANDIDATE,
    OVERLAPPING_PYTHON_ROLES_CANDIDATE,
    PARTIAL_SKILL_DURATION_CANDIDATE,
    PROFESSIONAL_PYTHON_CANDIDATE,
    PYTHON_PORTFOLIO_ONLY_CANDIDATE,
    SPECIALIZED_EDUCATION_FIELD_MATCH_CANDIDATE,
    SPECIALIZED_EDUCATION_FIELD_MISMATCH_CANDIDATE,
    UNSPECIFIED_FIELD_EDUCATION_CANDIDATE,
    UNSPECIFIED_SKILL_DURATION_CANDIDATE,
)
from src.ai.job_requirements import JobRequirements, extract_job_requirements
from src.ai.requirement_matcher import compare_requirements


STRUCTURED_DESCRIPTION = """We are hiring a Senior Data Engineer.

Requirements:

- 5+ years of Python experience
- Strong SQL and AWS skills
- Master's degree in Computer Science required

Preferred Qualifications:

- Experience with Kafka
"""

ALTERNATIVE_EXPERIENCE_DESCRIPTION = """Requirements:

- 12+ years of relevant experience with a Bachelor's or Master's degree
OR
- 9+ years of relevant experience with a PhD"""


def _requirements(description=STRUCTURED_DESCRIPTION, title="Senior Data Engineer", job_id=1):
    return extract_job_requirements(job_id, title, description)


def _bare_requirements(**overrides) -> JobRequirements:
    """A minimal, directly-constructed JobRequirements for test scenarios
    (specialized-degree ambiguity, an unknown career track) that Phase 9A's
    text extractor itself does not produce from any description -- this
    tests requirement_matcher's own handling of such a requirement, not
    extract_job_requirements().
    """
    defaults = dict(
        job_id=1, job_title="Fictional Role",
        career_track="unknown", career_track_evidence=[],
        required_skills=[], required_skills_evidence={},
        preferred_skills=[], preferred_skills_evidence={},
        experience_requirements=[],
        required_education=[], required_education_evidence={},
        preferred_education=[], preferred_education_evidence={},
        responsibilities=[], responsibilities_evidence={},
        domain_expertise=[], domain_expertise_evidence={},
        location_requirement=None, remote_allowed=None, location_evidence=[],
        missing_information=[], ambiguous_information=[], limitations=[],
    )
    defaults.update(overrides)
    return JobRequirements(**defaults)


def _match(result, kind, description_substring):
    for match in result.matches:
        if match.requirement_kind == kind and description_substring.lower() in match.requirement_description.lower():
            return match
    raise AssertionError(f"No {kind} match found for {description_substring!r}")


# --- Candidate evidence model: enforcement of no inferred employment ---

def test_training_evidence_cannot_carry_professional_experience_years():
    with pytest.raises(ValidationError):
        CandidateEvidenceItem(
            claim="Python", source_category="technical_training",
            professional_experience_years=2.0,
        )


def test_portfolio_project_evidence_cannot_carry_employment_period():
    with pytest.raises(ValidationError):
        CandidateEvidenceItem(
            claim="Python", source_category="portfolio_project",
            employment_period=EmploymentPeriod(start_year=2020.0, end_year=2021.0),
        )


def test_professional_experience_item_may_carry_years_and_period():
    item = CandidateEvidenceItem(
        claim="Data Engineer", source_category="professional_experience",
        career_track="data", professional_experience_years=3.0,
        employment_period=EmploymentPeriod(start_year=2020.0, end_year=2023.0),
    )
    assert item.professional_experience_years == 3.0


# --- Skills: supported, missing, required vs preferred ---

def test_supported_skill_from_technical_skill_category():
    requirements = _requirements()
    result = compare_requirements(requirements, EXPERIENCED_QUALIFIED_CANDIDATE)
    sql = _match(result, "skill", "sql")
    assert sql.status == "supported"
    assert sql.is_required is True


def test_missing_skill_evidence_is_not_demonstrated_not_proof_of_absence():
    requirements = _requirements()
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    aws = _match(result, "skill", "aws")
    assert aws.status == "not_demonstrated"
    assert any("not proof" in limitation for limitation in aws.limitations)


def test_required_vs_preferred_skill_distinction_preserved():
    requirements = _requirements()
    kafka = _match(compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE), "skill", "kafka")
    aws = _match(compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE), "skill", "aws")
    assert kafka.is_required is False
    assert aws.is_required is True


# --- Training/project skills never become professional experience ---

def test_training_and_project_skill_does_not_count_as_professional_use():
    requirements = _requirements()  # "5+ years of Python experience" ties python to professional use
    result = compare_requirements(requirements, CAREER_TRANSITION_CANDIDATE)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "partially_supported"
    assert all(item.source_category != "professional_experience" for item in python_match.candidate_evidence)


def test_training_and_project_skill_supports_plain_skill_requirement():
    requirements = _requirements()  # SQL has no attached years cue
    result = compare_requirements(requirements, CAREER_TRANSITION_CANDIDATE)
    sql_match = _match(result, "skill", "sql")
    assert sql_match.status == "supported"


def test_career_transition_candidate_has_no_demonstrated_professional_data_experience():
    requirements = _requirements()
    result = compare_requirements(requirements, CAREER_TRANSITION_CANDIDATE)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "not_demonstrated"
    assert not any(
        item.source_category == "professional_experience" for item in experience_match.candidate_evidence
    )


# --- Education: degree-level normalization ---

@pytest.mark.parametrize("claim", ["BS in Computer Science (fictional)", "BSc in Computer Science (fictional)",
                                    "Bachelor's degree in Computer Science (fictional)"])
def test_bachelor_level_aliases_are_recognized(claim):
    requirements = _requirements(description="Requirements:\n\n- Bachelor's degree required\n")
    evidence = CandidateEvidence(items=[CandidateEvidenceItem(claim=claim, source_category="education")])
    result = compare_requirements(requirements, evidence)
    education_match = _match(result, "education", "Bachelor")
    assert education_match.status == "supported"


@pytest.mark.parametrize("claim", ["MS in Computer Science (fictional)", "MSc in Data Science (fictional)",
                                    "Master's degree in Statistics (fictional)"])
def test_master_level_aliases_are_recognized(claim):
    # No field of study in the job text, so only the degree-level alias is
    # exercised here; field-of-study matching has its own dedicated tests.
    requirements = _requirements(description="Requirements:\n\n- Master's degree required\n")
    evidence = CandidateEvidence(items=[CandidateEvidenceItem(claim=claim, source_category="education")])
    result = compare_requirements(requirements, evidence)
    education_match = _match(result, "education", "Master")
    assert education_match.status == "supported"


@pytest.mark.parametrize("claim", ["PhD in Chemistry (fictional)", "Ph.D. in Physics (fictional)",
                                    "Doctorate in Biology (fictional)"])
def test_phd_level_aliases_are_recognized(claim):
    requirements = _requirements(description="Requirements:\n\n- PhD required\n")
    evidence = CandidateEvidence(items=[CandidateEvidenceItem(claim=claim, source_category="education")])
    result = compare_requirements(requirements, evidence)
    education_match = _match(result, "education", "PhD")
    assert education_match.status == "supported"


def test_bachelor_degree_does_not_satisfy_master_requirement():
    requirements = _requirements()  # requires Master's degree
    evidence = CandidateEvidence(items=[
        CandidateEvidenceItem(claim="Bachelor's degree in Computer Science (fictional)", source_category="education"),
    ])
    result = compare_requirements(requirements, evidence)
    education_match = _match(result, "education", "Master")
    assert education_match.status == "partially_supported"


def test_specialized_education_ambiguity_requires_review():
    requirements = _bare_requirements(required_education=["MD degree"])
    evidence = CandidateEvidence(items=[
        CandidateEvidenceItem(claim="MD (fictional)", source_category="education"),
    ])
    result = compare_requirements(requirements, evidence)
    education_match = _match(result, "education", "MD")
    assert education_match.status == "requires_review"


def test_doctorate_does_not_blindly_satisfy_other_ambiguous_degree_text():
    requirements = _bare_requirements(required_education=["JD degree"])
    evidence = CandidateEvidence(items=[
        CandidateEvidenceItem(claim="PhD in Organic Chemistry (fictional)", source_category="education"),
    ])
    result = compare_requirements(requirements, evidence)
    education_match = _match(result, "education", "JD")
    assert education_match.status == "requires_review"


# --- Professional experience: below minimum, missing, overlapping ---

def test_experience_below_minimum_is_partially_supported():
    requirements = _requirements(description="Requirements:\n\n- 10+ years of Python experience\n")
    evidence = CandidateEvidence(items=[
        CandidateEvidenceItem(
            claim="Data Engineer, Fictional Co", source_category="professional_experience",
            career_track="data", professional_experience_years=4.0,
        ),
    ])
    result = compare_requirements(requirements, evidence)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "partially_supported"
    assert "below" in experience_match.explanation


def test_missing_professional_years_is_not_demonstrated_not_assumed_zero():
    requirements = _requirements()
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "not_demonstrated"
    assert "0" not in experience_match.explanation.split("found")[0]


def test_professional_experience_item_with_no_stated_duration_requires_review():
    requirements = _requirements()
    evidence = CandidateEvidence(items=[
        CandidateEvidenceItem(
            claim="Data Engineer, Fictional Co", source_category="professional_experience",
            career_track="data",
        ),
    ])
    result = compare_requirements(requirements, evidence)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "requires_review"


def test_overlapping_employment_periods_require_review_not_summed():
    requirements = _requirements()
    result = compare_requirements(requirements, OVERLAPPING_EXPERIENCE_CANDIDATE)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "requires_review"
    assert "overlapping" in experience_match.explanation.lower()


def test_non_overlapping_multiple_roles_are_summed():
    requirements = _requirements(description="Requirements:\n\n- 6+ years of Python experience\n")
    evidence = CandidateEvidence(items=[
        CandidateEvidenceItem(
            claim="Data Analyst, Fictional Co A", source_category="professional_experience",
            career_track="data", professional_experience_years=3.0,
            employment_period=EmploymentPeriod(start_year=2015.0, end_year=2018.0),
        ),
        CandidateEvidenceItem(
            claim="Data Engineer, Fictional Co B", source_category="professional_experience",
            career_track="data", professional_experience_years=4.0,
            employment_period=EmploymentPeriod(start_year=2018.0, end_year=2022.0),
        ),
    ])
    result = compare_requirements(requirements, evidence)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "supported"


def test_experience_in_a_different_track_is_not_counted():
    requirements = _requirements()  # data track
    evidence = CandidateEvidence(items=[
        CandidateEvidenceItem(
            claim="Medicinal Chemist, Fictional Pharma Co", source_category="professional_experience",
            career_track="pharma", professional_experience_years=8.0,
        ),
    ])
    result = compare_requirements(requirements, evidence)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "not_demonstrated"


# --- Conditional experience alternatives ---

def test_education_dependent_alternative_resolves_through_phd_branch():
    requirements = _requirements(description=ALTERNATIVE_EXPERIENCE_DESCRIPTION, title="Senior Scientist")
    evidence = CandidateEvidence(items=[
        CandidateEvidenceItem(
            claim="Scientist, Fictional Pharma Co", source_category="professional_experience",
            career_track="pharma", professional_experience_years=9.0,
        ),
        CandidateEvidenceItem(claim="PhD in Organic Chemistry (fictional)", source_category="education"),
    ])
    result = compare_requirements(requirements, evidence)
    experience_matches = [m for m in result.matches if m.requirement_kind == "experience"]
    assert len(experience_matches) == 2
    groups = {m.alternative_group for m in experience_matches}
    assert len(groups) == 1 and None not in groups
    phd_branch = next(m for m in experience_matches if "PhD" in m.requirement_description)
    assert phd_branch.status == "supported"
    assert result.unresolved_alternative_groups == []


def test_unresolved_alternative_group_when_no_branch_fully_supported():
    requirements = _requirements(description=ALTERNATIVE_EXPERIENCE_DESCRIPTION, title="Senior Scientist")
    evidence = CandidateEvidence(items=[
        CandidateEvidenceItem(
            claim="Scientist, Fictional Pharma Co", source_category="professional_experience",
            career_track="pharma", professional_experience_years=5.0,
        ),
        CandidateEvidenceItem(claim="Bachelor of Science (fictional)", source_category="education"),
    ])
    result = compare_requirements(requirements, evidence)
    assert result.unresolved_alternative_groups != []
    experience_matches = [m for m in result.matches if m.requirement_kind == "experience"]
    assert all(m.status != "supported" for m in experience_matches)


def test_alternatives_are_not_collapsed_into_one_minimum():
    requirements = _requirements(description=ALTERNATIVE_EXPERIENCE_DESCRIPTION, title="Senior Scientist")
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    experience_matches = [m for m in result.matches if m.requirement_kind == "experience"]
    descriptions = {m.requirement_description for m in experience_matches}
    assert len(descriptions) == 2  # distinct branches, never flattened to one


# --- Contradictory evidence / evidence provenance and integrity ---

def test_contradictory_evidence_flagged_requires_review():
    requirements = _requirements()
    result = compare_requirements(requirements, OVERLAPPING_EXPERIENCE_CANDIDATE)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "requires_review"
    # Both conflicting items are surfaced, never silently dropped or merged.
    assert len(experience_match.candidate_evidence) == 2


def test_candidate_evidence_in_match_is_always_a_subset_of_supplied_evidence():
    requirements = _requirements()
    evidence = EXPERIENCED_QUALIFIED_CANDIDATE
    result = compare_requirements(requirements, evidence)
    for match in result.matches:
        for item in match.candidate_evidence:
            assert item in evidence.items


def test_no_fabricated_candidate_claims_appear_in_any_match():
    requirements = _requirements()
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    for match in result.matches:
        assert match.candidate_evidence == []


# --- Empty evidence / unknown job track ---

def test_empty_candidate_evidence_never_fabricates_support():
    requirements = _requirements()
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    assert all(match.status in ("not_demonstrated", "requires_review") for match in result.matches)


def test_unknown_job_track_requires_review_for_experience():
    from src.ai.job_requirements import ExperienceRequirement

    requirements = _bare_requirements(
        career_track="unknown",
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=5.0, education_qualifier=None, is_required=True,
                alternative_group=None, evidence=[],
            ),
        ],
    )
    result = compare_requirements(requirements, EXPERIENCED_QUALIFIED_CANDIDATE)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "requires_review"


# --- Result-level structure ---

def test_comparison_result_metadata():
    requirements = _requirements()
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    assert result.job_id == requirements.job_id
    assert result.analysis_mode == "deterministic"
    assert result.requires_human_review is True
    assert result.status == "pending_review"
    assert result.overall_limitations


# =====================================================================
# Phase 9B.3 hardening
# =====================================================================

# --- Task 1: professional skill evidence ---

def test_professional_skills_cannot_be_set_on_non_professional_item():
    with pytest.raises(ValidationError):
        CandidateEvidenceItem(
            claim="Python", source_category="technical_training", professional_skills=["Python"],
        )


def test_explicitly_documented_professional_python_use_is_supported():
    requirements = _requirements()  # "5+ years of Python experience" required
    result = compare_requirements(requirements, PROFESSIONAL_PYTHON_CANDIDATE)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "supported"
    assert all(item.source_category == "professional_experience" for item in python_match.candidate_evidence)


def test_generic_job_title_does_not_imply_a_skill():
    requirements = _requirements()  # "5+ years of Python experience" required
    result = compare_requirements(requirements, DATA_EMPLOYMENT_WITHOUT_PYTHON_CANDIDATE)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "not_demonstrated"
    # The role documents SQL, not Python -- that must never leak into a Python match.
    assert all(item.source_category != "professional_experience" for item in python_match.candidate_evidence)


def test_python_portfolio_project_alone_never_becomes_professional_experience():
    requirements = _requirements()  # ties Python to "5+ years ... experience"
    result = compare_requirements(requirements, PYTHON_PORTFOLIO_ONLY_CANDIDATE)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "partially_supported"
    assert all(item.source_category == "portfolio_project" for item in python_match.candidate_evidence)


def test_professional_skill_with_insufficient_role_duration_is_partially_supported():
    requirements = _requirements(description="Requirements:\n\n- 10+ years of Python experience\n")
    result = compare_requirements(requirements, PROFESSIONAL_PYTHON_CANDIDATE)  # role only has 5 years
    python_match = _match(result, "skill", "python")
    assert python_match.status == "partially_supported"


def test_professional_skill_with_unresolvable_role_duration_requires_review():
    requirements = _requirements()  # "5+ years of Python experience"
    evidence = CandidateEvidence(items=[
        CandidateEvidenceItem(
            claim="Data Engineer, Fictional Co", source_category="professional_experience",
            career_track="data", professional_skills=["Python"],  # no professional_experience_years
        ),
    ])
    result = compare_requirements(requirements, evidence)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "requires_review"


# --- Task 2: education field-of-study ---

def test_specialized_field_match_is_supported():
    requirements = _requirements(description="Requirements:\n\n- PhD in Organic Chemistry required\n")
    result = compare_requirements(requirements, SPECIALIZED_EDUCATION_FIELD_MATCH_CANDIDATE)
    education_match = _match(result, "education", "PhD")
    assert education_match.status == "supported"


def test_specialized_field_mismatch_is_partially_supported_not_supported():
    requirements = _requirements(description="Requirements:\n\n- PhD in Organic Chemistry required\n")
    result = compare_requirements(requirements, SPECIALIZED_EDUCATION_FIELD_MISMATCH_CANDIDATE)
    education_match = _match(result, "education", "PhD")
    assert education_match.status == "partially_supported"
    assert "does not match" in education_match.explanation


def test_unspecified_candidate_field_requires_review_when_job_field_specified():
    requirements = _requirements(description="Requirements:\n\n- PhD in Organic Chemistry required\n")
    result = compare_requirements(requirements, UNSPECIFIED_FIELD_EDUCATION_CANDIDATE)
    education_match = _match(result, "education", "PhD")
    assert education_match.status == "requires_review"


def test_unspecified_job_field_of_study_only_checks_level():
    requirements = _requirements(description="Requirements:\n\n- PhD required\n")
    result = compare_requirements(requirements, UNSPECIFIED_FIELD_EDUCATION_CANDIDATE)
    education_match = _match(result, "education", "PhD")
    assert education_match.status == "supported"
    assert "does not specify a field" in education_match.explanation


def test_higher_degree_level_is_not_sufficient_when_field_is_unresolved():
    # A PhD (higher than Master's) must not auto-satisfy a specialized
    # Master's-in-a-field requirement when the candidate's field is unknown.
    requirements = _requirements(description="Requirements:\n\n- Master's degree in Biostatistics required\n")
    result = compare_requirements(requirements, UNSPECIFIED_FIELD_EDUCATION_CANDIDATE)
    education_match = _match(result, "education", "Master")
    assert education_match.status == "requires_review"


# --- Task 3: experience integrity ---

def test_duplicate_role_entries_are_never_double_counted():
    requirements = _requirements()  # "5+ years of Python experience" among others; use raw experience req
    result = compare_requirements(requirements, DUPLICATE_ROLE_CANDIDATE)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "requires_review"


def test_ongoing_single_role_is_not_blocked_by_missing_end_date():
    requirements = _requirements(description="Requirements:\n\n- 4+ years of Python experience\n")
    result = compare_requirements(requirements, ONGOING_EMPLOYMENT_CANDIDATE)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "supported"


def test_ongoing_role_overlap_requires_review_not_summed():
    requirements = _requirements()
    result = compare_requirements(requirements, ONGOING_OVERLAPPING_CANDIDATE)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "requires_review"
    assert "overlapping" in experience_match.explanation.lower()


def test_conflicting_duration_claims_require_review():
    requirements = _requirements()
    result = compare_requirements(requirements, CONFLICTING_DURATION_CANDIDATE)
    experience_match = _match(result, "experience", "years")
    assert experience_match.status == "requires_review"


# --- Task 4: requirement uncertainty ---

def test_job_extraction_missing_information_is_carried_into_overall_limitations():
    requirements = _requirements(description="We are hiring a great teammate.")
    assert requirements.missing_information
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    assert any("carried over from extraction" in limitation for limitation in result.overall_limitations)


def test_job_extraction_ambiguous_information_is_carried_into_overall_limitations():
    requirements = _requirements(description="Requirements:\n\n- Several years of relevant experience\n")
    assert requirements.ambiguous_information
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    assert any(
        "Job posting ambiguity" in limitation and "carried over from extraction" in limitation
        for limitation in result.overall_limitations
    )


def test_missing_evidence_is_never_phrased_as_a_definitive_lack():
    requirements = _requirements()
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    for match in result.matches:
        if match.status == "not_demonstrated":
            assert "does not have" not in match.explanation.lower()
            assert "lacks" not in match.explanation.lower()


# --- Task 5: evidence provenance ---

def test_provenance_filter_drops_items_not_in_supplied_evidence():
    from src.ai.requirement_matcher import _filter_provenance

    real_item = CandidateEvidenceItem(claim="Python", source_category="technical_skill")
    foreign_item = CandidateEvidenceItem(claim="Rust", source_category="technical_skill")
    evidence = CandidateEvidence(items=[real_item])
    filtered = _filter_provenance(evidence, [real_item, foreign_item])
    assert filtered == [real_item]


def test_every_match_candidate_evidence_item_is_provenanced_across_all_fixtures():
    requirements = _requirements()
    for fixture in (
        CAREER_TRANSITION_CANDIDATE, EXPERIENCED_QUALIFIED_CANDIDATE, OVERLAPPING_EXPERIENCE_CANDIDATE,
        PROFESSIONAL_PYTHON_CANDIDATE, DATA_EMPLOYMENT_WITHOUT_PYTHON_CANDIDATE,
        PYTHON_PORTFOLIO_ONLY_CANDIDATE, DUPLICATE_ROLE_CANDIDATE, ONGOING_EMPLOYMENT_CANDIDATE,
        ONGOING_OVERLAPPING_CANDIDATE, CONFLICTING_DURATION_CANDIDATE, EMPTY_CANDIDATE_EVIDENCE,
    ):
        result = compare_requirements(requirements, fixture)
        for match in result.matches:
            for item in match.candidate_evidence:
                assert item in fixture.items


# --- Task 6: empty evidence sanity across the hardened engine ---

def test_empty_evidence_never_supported_after_hardening():
    requirements = _requirements()
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    assert all(match.status in ("not_demonstrated", "requires_review") for match in result.matches)


# =====================================================================
# Phase 9B.3a hardening -- skill-specific professional duration
# =====================================================================

# --- Task 2: schema enforcement ---

def test_professional_skill_years_cannot_be_set_on_non_professional_item():
    with pytest.raises(ValidationError):
        CandidateEvidenceItem(
            claim="Python", source_category="technical_training",
            professional_skill_years={"Python": 2.0},
        )


def test_professional_skill_years_key_must_be_in_professional_skills():
    with pytest.raises(ValidationError):
        CandidateEvidenceItem(
            claim="Data Engineer", source_category="professional_experience", career_track="data",
            professional_skills=["SQL"], professional_skill_years={"Python": 2.0},
        )


def test_professional_skill_years_must_be_nonnegative():
    with pytest.raises(ValidationError):
        CandidateEvidenceItem(
            claim="Data Engineer", source_category="professional_experience", career_track="data",
            professional_skills=["Python"], professional_skill_years={"Python": -1.0},
        )


def test_professional_skill_years_cannot_exceed_role_duration():
    with pytest.raises(ValidationError):
        CandidateEvidenceItem(
            claim="Data Engineer", source_category="professional_experience", career_track="data",
            professional_experience_years=3.0,
            professional_skills=["Python"], professional_skill_years={"Python": 5.0},
        )


def test_professional_skill_years_allowed_without_a_stated_role_duration():
    # The role's own tenure is unknown, so there is nothing to bound
    # against -- the skill-specific duration still stands on its own.
    item = CandidateEvidenceItem(
        claim="Data Engineer", source_category="professional_experience", career_track="data",
        professional_skills=["Python"], professional_skill_years={"Python": 2.0},
    )
    assert item.professional_skill_years == {"Python": 2.0}


# --- Task 3: experience-based skill matching ---

def test_full_duration_professional_skill_use_is_supported():
    requirements = _requirements()  # "5+ years of Python experience"
    result = compare_requirements(requirements, PROFESSIONAL_PYTHON_CANDIDATE)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "supported"
    assert "5" in python_match.explanation


def test_partial_duration_professional_skill_use_is_partially_supported():
    requirements = _requirements()  # "5+ years of Python experience"
    result = compare_requirements(requirements, PARTIAL_SKILL_DURATION_CANDIDATE)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "partially_supported"
    assert "2" in python_match.explanation


def test_skill_listed_without_its_own_duration_requires_review():
    requirements = _requirements()  # "5+ years of Python experience"
    result = compare_requirements(requirements, UNSPECIFIED_SKILL_DURATION_CANDIDATE)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "requires_review"
    # The role's own 5-year tenure must never be silently credited to the skill.
    assert "5" not in python_match.explanation.replace("5+", "")


def test_role_tenure_is_never_silently_inherited_by_an_unspecified_skill_duration():
    requirements = _requirements(description="Requirements:\n\n- 1+ years of Python experience\n")
    result = compare_requirements(requirements, UNSPECIFIED_SKILL_DURATION_CANDIDATE)
    python_match = _match(result, "skill", "python")
    # Even though the role's 5-year tenure trivially exceeds a 1-year ask,
    # the skill's own duration is unknown, so this must stay requires_review,
    # never "supported" by borrowing the role's number.
    assert python_match.status == "requires_review"


def test_portfolio_evidence_never_invents_employment_years_for_a_skill():
    requirements = _requirements()  # "5+ years of Python experience"
    result = compare_requirements(requirements, PYTHON_PORTFOLIO_ONLY_CANDIDATE)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "partially_supported"
    assert all(item.source_category != "professional_experience" for item in python_match.candidate_evidence)


def test_no_python_evidence_at_all_is_not_demonstrated():
    requirements = _requirements()
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "not_demonstrated"


def test_two_non_overlapping_roles_sum_skill_specific_durations():
    requirements = _requirements()  # "5+ years of Python experience" (3+3=6 >= 5)
    result = compare_requirements(requirements, NON_OVERLAPPING_PYTHON_ROLES_CANDIDATE)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "supported"


def test_overlapping_roles_with_skill_evidence_require_review_not_summed():
    requirements = _requirements()
    result = compare_requirements(requirements, OVERLAPPING_PYTHON_ROLES_CANDIDATE)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "requires_review"
    assert "overlapping" in python_match.explanation.lower()


def test_duplicate_role_entries_never_double_count_skill_duration():
    requirements = _requirements()
    duplicate_with_skill = CandidateEvidence(items=[
        CandidateEvidenceItem(
            claim="Data Engineer, Fictional Duplicate Co", source_category="professional_experience",
            career_track="data", professional_experience_years=4.0,
            employment_period=EmploymentPeriod(start_year=2020.0, end_year=2024.0),
            professional_skills=["Python"], professional_skill_years={"Python": 4.0},
        ),
        CandidateEvidenceItem(
            claim="Data Engineer, Fictional Duplicate Co", source_category="professional_experience",
            career_track="data", professional_experience_years=4.0,
            employment_period=EmploymentPeriod(start_year=2020.0, end_year=2024.0),
            professional_skills=["Python"], professional_skill_years={"Python": 4.0},
        ),
    ])
    result = compare_requirements(requirements, duplicate_with_skill)
    python_match = _match(result, "skill", "python")
    assert python_match.status == "requires_review"


# --- Task 4: preserved behavior regression ---

def test_plain_skill_requirement_still_supported_by_training_or_portfolio():
    requirements = _requirements()  # SQL has no years cue in STRUCTURED_DESCRIPTION
    result = compare_requirements(requirements, CAREER_TRANSITION_CANDIDATE)
    sql_match = _match(result, "skill", "sql")
    assert sql_match.status == "supported"


def test_education_field_of_study_logic_is_unaffected():
    requirements = _requirements(description="Requirements:\n\n- PhD in Organic Chemistry required\n")
    matched = compare_requirements(requirements, SPECIALIZED_EDUCATION_FIELD_MATCH_CANDIDATE)
    mismatched = compare_requirements(requirements, SPECIALIZED_EDUCATION_FIELD_MISMATCH_CANDIDATE)
    assert _match(matched, "education", "PhD").status == "supported"
    assert _match(mismatched, "education", "PhD").status == "partially_supported"


def test_experience_alternatives_remain_independent_after_hardening():
    requirements = _requirements(description=ALTERNATIVE_EXPERIENCE_DESCRIPTION, title="Senior Scientist")
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    experience_matches = [m for m in result.matches if m.requirement_kind == "experience"]
    assert len({m.requirement_description for m in experience_matches}) == 2


def test_ambiguous_requirements_remain_reviewable_after_hardening():
    requirements = _bare_requirements(required_education=["MD degree"])
    result = compare_requirements(requirements, EMPTY_CANDIDATE_EVIDENCE)
    education_match = _match(result, "education", "MD")
    assert education_match.status == "requires_review"


def test_returned_candidate_evidence_retains_valid_provenance_after_hardening():
    requirements = _requirements()
    for fixture in (
        PROFESSIONAL_PYTHON_CANDIDATE, PARTIAL_SKILL_DURATION_CANDIDATE,
        UNSPECIFIED_SKILL_DURATION_CANDIDATE, NON_OVERLAPPING_PYTHON_ROLES_CANDIDATE,
        OVERLAPPING_PYTHON_ROLES_CANDIDATE,
    ):
        result = compare_requirements(requirements, fixture)
        for match in result.matches:
            for item in match.candidate_evidence:
                assert item in fixture.items


def test_missing_skill_duration_evidence_never_becomes_assumed_zero():
    requirements = _requirements()
    result = compare_requirements(requirements, UNSPECIFIED_SKILL_DURATION_CANDIDATE)
    python_match = _match(result, "skill", "python")
    assert "0" not in python_match.explanation
