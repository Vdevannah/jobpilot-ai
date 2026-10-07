import re

from src.profile import CandidateProfile


SKILL_KEYWORDS = (
    "python",
    "sql",
    "mysql",
    "postgresql",
    "pandas",
    "numpy",
    "fastapi",
    "flask",
    "react",
    "javascript",
    "tableau",
    "power bi",
    "excel",
    "aws",
    "azure",
    "gcp",
    "spark",
    "pyspark",
    "airflow",
    "kafka",
    "docker",
    "git",
    "machine learning",
    "data analysis",
    "data engineering",
    "medicinal chemistry",
    "organic chemistry",
    "synthetic organic chemistry",
    "organic synthesis",
    "multi-step synthesis",
    "small molecules",
    "drug discovery",
    "lead optimization",
    "sar",
    "structure-based drug design",
    "molecular design",
    "protac",
    "protacs",
    "targeted protein degradation",
    "tpd",
    "degrader",
    "degraders",
    "crbn",
    "vhl",
    "chemical biology",
    "assay development",
    "western blot",
    "proteomics",
    "hit identification",
    "hit-to-lead",
    "chromatography",
    "hplc",
    "lc-ms",
    "nmr",
    "antibody-drug conjugate",
    "antibody-drug conjugates",
    "adc",
    "adcs",
    "degrader-antibody conjugate",
    "degrader-antibody conjugates",
    "degrader antibody conjugate",
    "degrader antibody conjugates",
    "dac",
    "dacs",
    "payload",
    "payload-linker",
    "linker chemistry",
    "conjugation",
    "inhibitor",
    "inhibitors",
    "small molecule inhibitor",
    "allosteric inhibitor",
    "protein degradation",
    "molecular glue",
    "e3 ligase",
    "structure-based design",
    "structure-activity relationship",
    "biomarker",
    "biomarkers",
    "cell-based assay",
    "cytotoxicity assay",
)

SKILL_ALIASES = {
    "adc": "antibody-drug conjugate",
    "adcs": "antibody-drug conjugate",
    "antibody-drug conjugates": "antibody-drug conjugate",
    "dac": "degrader-antibody conjugate",
    "dacs": "degrader-antibody conjugate",
    "degrader-antibody conjugates": "degrader-antibody conjugate",
    "degrader antibody conjugate": "degrader-antibody conjugate",
    "degrader antibody conjugates": "degrader-antibody conjugate",
    "protacs": "protac",
    "tpd": "targeted protein degradation",
    "protein degradation": "targeted protein degradation",
    "structure-activity relationship": "sar",
    "degraders": "degrader",
    "inhibitors": "inhibitor",
    "biomarkers": "biomarker",
}


def normalize_skill(skill):
    normalized_skill = skill.strip().lower()
    return SKILL_ALIASES.get(normalized_skill, normalized_skill)


def extract_skills(description):
    if not description:
        return []

    found_skills = []
    seen_skills = set()
    normalized_description = description.lower()

    for skill in SKILL_KEYWORDS:
        pattern = rf"(?<!\w){re.escape(skill)}(?!\w)"
        if re.search(pattern, normalized_description):
            normalized_skill = normalize_skill(skill)
            if normalized_skill not in seen_skills:
                found_skills.append(normalized_skill)
                seen_skills.add(normalized_skill)

    return found_skills


def extract_years_experience(description):
    if not description:
        return None

    pattern = re.compile(
        r"\b(\d+)\s*\+?\s*years?\b"
        r"(?:\s+(?:of\s+)?(?:relevant\s+)?(?:work\s+)?experience\b)?",
        re.IGNORECASE,
    )
    years = [int(match.group(1)) for match in pattern.finditer(description)]
    return max(years) if years else None


def calculate_skill_score(candidate_skills, required_skills):
    if not required_skills:
        return 50.0

    candidate_skill_set = {normalize_skill(skill) for skill in candidate_skills}
    normalized_required_skills = list(
        dict.fromkeys(normalize_skill(skill) for skill in required_skills)
    )
    matched_count = sum(
        skill in candidate_skill_set for skill in normalized_required_skills
    )
    return round(matched_count / len(normalized_required_skills) * 100, 1)


def calculate_experience_score(candidate_years, required_years):
    if required_years is None:
        return 50.0
    if candidate_years >= required_years:
        return 100.0

    return round(candidate_years / required_years * 100, 1)


def calculate_role_score(job_title, target_roles):
    if not target_roles:
        return 100.0

    normalized_title = job_title.lower()
    if any(
        role.lower() in normalized_title or normalized_title in role.lower()
        for role in target_roles
    ):
        return 100.0
    return 0.0


def calculate_domain_score(description, domains):
    if not domains:
        return 100.0

    normalized_description = description.lower()
    matched_domains = sum(
        domain.lower() in normalized_description for domain in domains
    )
    return round(matched_domains / len(domains) * 100, 1)


def calculate_location_score(job_location, preferred_locations):
    if not preferred_locations:
        return 100.0

    if any(location.lower() == "anywhere in usa" for location in preferred_locations):
        return 100.0

    normalized_location = job_location.lower()
    if any(
        location.lower() in normalized_location
        for location in preferred_locations
    ):
        return 100.0
    return 0.0


def determine_job_track(job_title, description):
    normalized_title = job_title.lower()
    normalized_description = description.lower()

    data_title_indicators = (
        "data scientist",
        "data analyst",
        "data engineer",
        "business analyst",
        "analytics",
    )
    pharma_title_indicators = (
        "medicinal chemistry",
        "medicinal chemist",
        "organic chemistry",
        "organic synthesis",
        "principal scientist",
        "senior scientist",
        "scientist",
    )

    if any(indicator in normalized_title for indicator in data_title_indicators):
        return "data"
    if any(indicator in normalized_title for indicator in pharma_title_indicators):
        return "pharma"

    pharma_description_indicators = (
        "medicinal chemistry",
        "medicinal chemist",
        "organic chemistry",
        "organic synthesis",
        "drug discovery",
        "pharmaceutical",
        "chemical biology",
        "protac",
        "targeted protein degradation",
    )
    data_description_indicators = (
        "data scientist",
        "data analyst",
        "data engineer",
        "analytics",
        "business analyst",
        "python",
        "sql",
        "data engineering",
        "machine learning",
    )

    if any(indicator in normalized_description for indicator in pharma_description_indicators):
        return "pharma"
    if any(indicator in normalized_description for indicator in data_description_indicators):
        return "data"
    return None


def _experience_for_track(profile, job_track):
    if job_track is None:
        return 0.0
    return profile.experience_by_domain.get(job_track, 0.0)


def get_relevant_experience(profile, job_title, description, job_track=None):
    if job_track is None:
        job_track = determine_job_track(job_title, description)
    return _experience_for_track(profile, job_track)


def get_relevant_domains(profile, job_track):
    if job_track is None:
        return []
    return profile.domains_by_track.get(job_track, [])


def get_match_recommendation(overall_score):
    if overall_score >= 80:
        return "Strong Match"
    if overall_score >= 65:
        return "Worth Reviewing"
    if overall_score >= 50:
        return "Possible Match"
    return "Low Priority"


def build_match_reasons(match_result):
    reasons = []

    if match_result["skill_score"] >= 80:
        reasons.append("Strong detected skill alignment")
    if match_result["role_score"] == 100:
        reasons.append("Target role alignment")
    if match_result["location_score"] == 100:
        reasons.append("Location preference matched")

    required_years = match_result["required_years"]
    candidate_years = match_result["candidate_years"]
    if required_years is not None and candidate_years < required_years:
        reasons.append(
            f"Experience gap: job requests {required_years} years; candidate has "
            f"{candidate_years:.1f} years in this track"
        )

    missing_skills = match_result["missing_skills"]
    if missing_skills:
        reasons.append(f"Missing detected skills: {', '.join(missing_skills)}")
    if not match_result["required_skills"]:
        reasons.append("Job description provided limited skill evidence")
    if required_years is None:
        reasons.append("Experience requirement not detected")

    return reasons


def match_job(profile: CandidateProfile, job):
    required_skills = extract_skills(job["description"])
    required_years = extract_years_experience(job["description"])
    job_track = determine_job_track(job["title"], job["description"])
    candidate_years = get_relevant_experience(
        profile, job["title"], job["description"], job_track=job_track
    )
    candidate_skill_set = {normalize_skill(skill) for skill in profile.skills}
    matched_skills = [
        skill for skill in required_skills if normalize_skill(skill) in candidate_skill_set
    ]
    missing_skills = [
        skill for skill in required_skills if normalize_skill(skill) not in candidate_skill_set
    ]
    skill_score = calculate_skill_score(profile.skills, required_skills)
    experience_score = calculate_experience_score(
        candidate_years, required_years
    )
    role_score = calculate_role_score(job["title"], profile.target_roles)
    relevant_domains = get_relevant_domains(profile, job_track)
    domain_score = calculate_domain_score(job["description"], relevant_domains)
    location_score = calculate_location_score(
        job["location"], profile.preferred_locations
    )
    overall_score = round(
        skill_score * 0.45
        + experience_score * 0.20
        + role_score * 0.15
        + domain_score * 0.10
        + location_score * 0.10,
        1,
    )
    recommendation = get_match_recommendation(overall_score)

    match_result = {
        "overall_score": overall_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "role_score": role_score,
        "domain_score": domain_score,
        "location_score": location_score,
        "job_track": job_track,
        "candidate_years": candidate_years,
        "relevant_domains": relevant_domains,
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "required_years": required_years,
    }
    match_result["recommendation"] = recommendation
    match_result["reasons"] = build_match_reasons(match_result)
    return match_result
