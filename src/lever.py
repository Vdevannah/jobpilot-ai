import requests

from src.utils import is_us_location, matches_target_role


def get_lever_jobs(site, company_name, target_roles):
    url = f"https://api.lever.co/v0/postings/{site}?mode=json"

    try:
        response = requests.get(url)
        response.raise_for_status()
        jobs = response.json()
    except requests.RequestException as error:
        print(f"Lever API error for {company_name}: {error}")
        return []

    matching_jobs = []

    for job in jobs:
        title = job["text"]
        location = job["categories"]["location"]

        if is_us_location(location) and matches_target_role(title, target_roles):
            normalized_job = {
                "title": title,
                "company": company_name,
                "location": location,
                "url": job["hostedUrl"],
                "source": "lever"
            }
            matching_jobs.append(normalized_job)

    return matching_jobs
