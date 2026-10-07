from src.candidate import candidate_profile
from src.matching import match_job
from src.repository import get_all_jobs


def rank_jobs():
    ranked_jobs = []

    for job in get_all_jobs():
        job_dict = {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "source": job.source,
            "description": job.description or "",
        }
        match_result = match_job(candidate_profile, job_dict)
        ranked_jobs.append({**job_dict, **match_result})

    return sorted(
        ranked_jobs,
        key=lambda result: result["overall_score"],
        reverse=True,
    )


def print_ranked_jobs(ranked_jobs):
    for rank, result in enumerate(ranked_jobs, start=1):
        matched_skills = ", ".join(result["matched_skills"]) or "None detected"
        missing_skills = ", ".join(result["missing_skills"]) or "None detected"
        required_years = result["required_years"]
        required_years_display = (
            f"{required_years} years" if required_years is not None else "Not detected"
        )

        print("-" * 50)
        print(
            f"#{rank} | {result['overall_score']:.1f}% MATCH | "
            f"{result['recommendation']}"
        )
        print(result["title"])
        print(result["company"])
        print(f"Location: {result['location']}")
        print()
        print(f"Track: {result['job_track'] or 'Not detected'}")
        print(f"Skill score: {result['skill_score']:.1f}")
        print(f"Experience score: {result['experience_score']:.1f}")
        print(f"Role score: {result['role_score']:.1f}")
        print(f"Domain score: {result['domain_score']:.1f}")
        print(f"Location score: {result['location_score']:.1f}")
        print()
        print("Why:")
        for reason in result["reasons"]:
            print(f"- {reason}")
        print()
        print("Matched skills:")
        print(matched_skills)
        print()
        print("Missing skills:")
        print(missing_skills)
        print()
        print("Experience:")
        print(f"Candidate: {result['candidate_years']:.1f} years")
        print(f"Job requirement: {required_years_display}")
        print()
        print("URL:")
        print(result["url"])


if __name__ == "__main__":
    ranked_jobs = rank_jobs()
    print_ranked_jobs(ranked_jobs)
