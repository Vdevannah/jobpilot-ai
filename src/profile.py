from dataclasses import dataclass


@dataclass
class CandidateProfile:
    target_roles: list[str]
    skills: list[str]
    domains_by_track: dict[str, list[str]]
    preferred_locations: list[str]
    experience_by_domain: dict[str, float]
