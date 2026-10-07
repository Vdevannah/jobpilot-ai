from src.matching import (
    calculate_domain_score,
    calculate_experience_score,
    calculate_location_score,
    calculate_role_score,
    calculate_skill_score,
    determine_job_track,
    extract_skills,
    extract_years_experience,
    get_match_recommendation,
    get_relevant_experience,
    build_match_reasons,
    match_job,
)
from src.profile import CandidateProfile


def test_get_match_recommendation_boundaries():
    assert get_match_recommendation(80.0) == "Strong Match"
    assert get_match_recommendation(79.9) == "Worth Reviewing"
    assert get_match_recommendation(65.0) == "Worth Reviewing"
    assert get_match_recommendation(64.9) == "Possible Match"
    assert get_match_recommendation(50.0) == "Possible Match"
    assert get_match_recommendation(49.9) == "Low Priority"


def test_build_match_reasons_reports_alignment_and_gaps():
    reasons = build_match_reasons(
        {
            "skill_score": 80.0,
            "role_score": 100.0,
            "location_score": 100.0,
            "required_years": 2,
            "candidate_years": 0.0,
            "missing_skills": ["aws", "machine learning"],
            "required_skills": ["python", "aws", "machine learning"],
        }
    )

    assert reasons == [
        "Strong detected skill alignment",
        "Target role alignment",
        "Location preference matched",
        "Experience gap: job requests 2 years; candidate has 0.0 years in this track",
        "Missing detected skills: aws, machine learning",
    ]


def test_build_match_reasons_reports_missing_description_evidence():
    reasons = build_match_reasons(
        {
            "skill_score": 50.0,
            "role_score": 0.0,
            "location_score": 0.0,
            "required_years": None,
            "candidate_years": 0.0,
            "missing_skills": [],
            "required_skills": [],
        }
    )

    assert reasons == [
        "Job description provided limited skill evidence",
        "Experience requirement not detected",
    ]


def test_calculate_skill_score_returns_neutral_score_without_requirements():
    assert calculate_skill_score(["python"], []) == 50.0


def test_calculate_experience_score_returns_neutral_score_without_requirement():
    assert calculate_experience_score(0.0, None) == 50.0


def test_calculate_experience_score_preserves_detected_requirement_behavior():
    assert calculate_experience_score(0.0, 2) == 0.0
    assert calculate_experience_score(1.0, 5) == 20.0
    assert calculate_experience_score(5.0, 5) == 100.0
    assert calculate_experience_score(8.0, 5) == 100.0


def test_extract_skills_detects_multiple_skills_case_insensitively():
    description = "Experience with Python, SQL, AWS, and machine learning."

    assert extract_skills(description) == [
        "python",
        "sql",
        "aws",
        "machine learning",
    ]


def test_extract_skills_does_not_return_duplicates():
    description = "Python and python; SQL and SQL."

    assert extract_skills(description) == ["python", "sql"]


def test_extract_skills_returns_empty_list_for_empty_input():
    assert extract_skills("") == []
    assert extract_skills(None) == []


def test_extract_skills_respects_word_boundaries():
    assert extract_skills("The digital product team builds useful tools.") == []


def test_extract_years_experience_detects_plus_years():
    assert extract_years_experience("3+ years of experience") == 3


def test_extract_years_experience_detects_relevant_work_experience():
    assert extract_years_experience("5 years of relevant work experience") == 5


def test_extract_years_experience_returns_largest_requirement():
    description = "3+ years with Python and 5 years of experience"

    assert extract_years_experience(description) == 5


def test_extract_years_experience_returns_none_without_requirement():
    assert extract_years_experience("Python and SQL skills required") is None


def test_extract_years_experience_returns_none_for_empty_input():
    assert extract_years_experience("") is None
    assert extract_years_experience(None) is None


def test_extract_skills_normalizes_adc_aliases_once():
    skills = extract_skills("Experience with ADCs and antibody-drug conjugates.")

    assert skills.count("antibody-drug conjugate") == 1


def test_extract_skills_normalizes_dac_aliases_once():
    skills = extract_skills("DACs and degrader antibody conjugates")

    assert skills.count("degrader-antibody conjugate") == 1


def test_extract_skills_normalizes_protac_alias():
    assert extract_skills("Experience developing PROTACs.") == ["protac"]


def test_extract_skills_normalizes_tpd_aliases_once():
    skills = extract_skills(
        "Experience in targeted protein degradation (TPD)."
    )

    assert skills.count("targeted protein degradation") == 1


def test_extract_skills_normalizes_sar_aliases_once():
    skills = extract_skills(
        "Strong understanding of SAR and structure-activity relationship."
    )

    assert skills.count("sar") == 1


def test_match_job_matches_candidate_skill_aliases():
    profile = CandidateProfile(
        target_roles=[],
        skills=["ADC", "PROTACs", "TPD", "SAR"],
        domains_by_track={"pharma": [], "data": []},
        preferred_locations=[],
        experience_by_domain={"pharma": 5.0, "data": 5.0},
    )
    job = {
        "title": "Research Scientist",
        "location": "Remote",
        "description": (
            "Antibody-drug conjugates, protac, targeted protein degradation, "
            "and structure-activity relationship"
        )
    }

    result = match_job(profile, job)

    assert set(result["matched_skills"]) == {
        "antibody-drug conjugate",
        "protac",
        "targeted protein degradation",
        "sar",
    }
    assert result["missing_skills"] == []


def test_extract_skills_from_medicinal_chemistry_description():
    description = (
        "Medicinal chemistry and organic synthesis for drug discovery and lead "
        "optimization, including SAR, structure-based drug design, PROTACs, "
        "targeted protein degradation, CRBN, antibody-drug conjugates, linker "
        "chemistry, allosteric inhibitors, HPLC, LC-MS, and NMR."
    )

    assert extract_skills(description) == [
        "medicinal chemistry",
        "organic synthesis",
        "drug discovery",
        "lead optimization",
        "sar",
        "structure-based drug design",
        "protac",
        "targeted protein degradation",
        "crbn",
        "hplc",
        "lc-ms",
        "nmr",
        "antibody-drug conjugate",
        "linker chemistry",
        "inhibitor",
    ]


def test_calculate_role_score_matches_partial_titles_case_insensitively():
    assert calculate_role_score(
        "Principal Scientist, Medicinal Chemistry",
        ["Medicinal Chemist", "Principal Scientist"],
    ) == 100.0
    assert calculate_role_score(
        "Senior Data Scientist - Analytics",
        ["Data Scientist"],
    ) == 100.0
    assert calculate_role_score("Research Chemist", ["Data Scientist"]) == 0.0
    assert calculate_role_score("Research Chemist", []) == 100.0


def test_calculate_domain_score_counts_matching_candidate_domains():
    description = "Pharmaceutical drug discovery research focused on oncology."

    assert calculate_domain_score(
        description,
        ["pharmaceutical", "biotech", "oncology"],
    ) == 66.7
    assert calculate_domain_score(description, []) == 100.0


def test_calculate_location_score_matches_preferred_locations():
    assert calculate_location_score(
        "Philadelphia, Pennsylvania",
        ["Pennsylvania", "Delaware"],
    ) == 100.0
    assert calculate_location_score("Remote - United States", ["Remote"]) == 100.0
    assert calculate_location_score(
        "Boston, Massachusetts",
        ["Pennsylvania", "Delaware"],
    ) == 0.0
    assert calculate_location_score("Boston, Massachusetts", []) == 100.0
    assert calculate_location_score(
        "Boston, Massachusetts",
        ["Anywhere in USA"],
    ) == 100.0
    assert calculate_location_score(
        "San Francisco, California",
        ["Anywhere in USA"],
    ) == 100.0


def test_match_job_scores_medicinal_chemistry_alignment():
    profile = CandidateProfile(
        target_roles=[
            "Medicinal Chemist",
            "Senior Scientist",
            "Principal Scientist",
        ],
        skills=[
            "medicinal chemistry",
            "organic synthesis",
            "drug discovery",
            "lead optimization",
            "SAR",
            "PROTACs",
            "TPD",
            "ADC",
            "HPLC",
            "LC-MS",
            "NMR",
        ],
        domains_by_track={
            "pharma": ["pharmaceutical", "biotech", "oncology"],
            "data": [],
        },
        preferred_locations=["Pennsylvania", "Delaware", "Remote"],
        experience_by_domain={"pharma": 8.0, "data": 1.0},
    )
    job = {
        "title": "Principal Scientist, Medicinal Chemistry",
        "location": "Philadelphia, Pennsylvania",
        "description": (
            "Pharmaceutical oncology role in medicinal chemistry and organic "
            "synthesis, drug discovery, lead optimization, SAR, PROTACs, "
            "targeted protein degradation, antibody-drug conjugates, HPLC, "
            "LC-MS, NMR; 6+ years of experience."
        ),
    }

    result = match_job(profile, job)

    assert result["role_score"] == 100.0
    assert result["location_score"] == 100.0
    assert result["experience_score"] == 100.0
    assert result["domain_score"] == 66.7
    assert result["required_years"] == 6
    assert result["matched_skills"] == result["required_skills"]
    assert result["missing_skills"] == []
    assert {
        "protac",
        "targeted protein degradation",
        "antibody-drug conjugate",
    }.issubset(result["matched_skills"])
    assert result["overall_score"] == round(
        result["skill_score"] * 0.45
        + result["experience_score"] * 0.20
        + result["role_score"] * 0.15
        + result["domain_score"] * 0.10
        + result["location_score"] * 0.10,
        1,
    )


def test_determine_job_track_from_title_and_description():
    assert determine_job_track(
        "Principal Scientist, Medicinal Chemistry", ""
    ) == "pharma"
    assert determine_job_track("Senior Scientist, Drug Discovery", "") == "pharma"
    assert determine_job_track("Senior Data Scientist", "") == "data"
    assert determine_job_track("Data Engineer", "") == "data"
    assert determine_job_track("Office Coordinator", "General responsibilities") is None


def test_get_relevant_experience_uses_matching_track():
    profile = CandidateProfile(
        target_roles=[],
        skills=[],
        domains_by_track={"pharma": [], "data": []},
        preferred_locations=[],
        experience_by_domain={"pharma": 8.0, "data": 1.0},
    )

    assert get_relevant_experience(
        profile,
        "Principal Scientist, Medicinal Chemistry",
        "",
    ) == 8.0
    assert get_relevant_experience(profile, "Senior Data Scientist", "") == 1.0
    assert get_relevant_experience(
        profile,
        "Office Coordinator",
        "General responsibilities",
    ) == 0.0


def test_pharma_experience_does_not_inflate_data_job_experience():
    profile = CandidateProfile(
        target_roles=[],
        skills=["Python", "SQL"],
        domains_by_track={"pharma": [], "data": []},
        preferred_locations=[],
        experience_by_domain={"pharma": 8.0, "data": 1.0},
    )
    job = {
        "title": "Data Engineer",
        "location": "Remote",
        "description": "Requires 5+ years of experience with Python and SQL.",
    }

    result = match_job(profile, job)

    assert result["job_track"] == "data"
    assert result["candidate_years"] == 1.0
    assert result["required_years"] == 5
    assert result["experience_score"] == 20.0


def test_data_experience_does_not_reduce_pharma_job_experience():
    profile = CandidateProfile(
        target_roles=[],
        skills=["medicinal chemistry"],
        domains_by_track={"pharma": [], "data": []},
        preferred_locations=[],
        experience_by_domain={"pharma": 8.0, "data": 1.0},
    )
    job = {
        "title": "Medicinal Chemist",
        "location": "Philadelphia, Pennsylvania",
        "description": "Medicinal chemistry role requiring 5+ years of experience.",
    }

    result = match_job(profile, job)

    assert result["job_track"] == "pharma"
    assert result["candidate_years"] == 8.0
    assert result["required_years"] == 5
    assert result["experience_score"] == 100.0


def test_pharma_job_uses_only_pharma_domains():
    profile = CandidateProfile(
        target_roles=[],
        skills=[],
        domains_by_track={
            "pharma": ["pharmaceutical", "oncology", "drug discovery"],
            "data": ["data science", "data engineering"],
        },
        preferred_locations=[],
        experience_by_domain={"pharma": 8.0, "data": 1.0},
    )
    job = {
        "title": "Principal Scientist, Medicinal Chemistry",
        "location": "Philadelphia, Pennsylvania",
        "description": "Pharmaceutical oncology drug discovery position.",
    }

    result = match_job(profile, job)

    assert result["job_track"] == "pharma"
    assert result["relevant_domains"] == [
        "pharmaceutical",
        "oncology",
        "drug discovery",
    ]


def test_data_job_uses_only_data_domains():
    data_domains = ["data science", "data engineering"]
    profile = CandidateProfile(
        target_roles=[],
        skills=[],
        domains_by_track={
            "pharma": ["pharmaceutical", "oncology", "drug discovery"],
            "data": data_domains,
        },
        preferred_locations=[],
        experience_by_domain={"pharma": 8.0, "data": 1.0},
    )
    job = {
        "title": "Data Scientist",
        "location": "Remote",
        "description": "Data science and data engineering role.",
    }

    result = match_job(profile, job)

    assert result["job_track"] == "data"
    assert result["relevant_domains"] == data_domains
