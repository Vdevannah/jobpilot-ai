import requests

from src.utils import clean_html_text, is_us_location, matches_target_role


def get_jobs(company, target_roles):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        print(f"Greenhouse API error for {company}: {error}")
        return []

    jobs = data["jobs"]
    matching_jobs = []

    for job in jobs:
        title = job["title"]
        location = job["location"]["name"]

        if is_us_location(location) and matches_target_role(title, target_roles):
            detail_url = (
                f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/"
                f"{job['id']}"
            )
            try:
                detail_response = requests.get(detail_url)
                detail_response.raise_for_status()
                content = detail_response.json().get("content", "")
                description = clean_html_text(content)
            except requests.RequestException as error:
                print(f"Greenhouse detail API error for {company} job {job['id']}: {error}")
                description = ""

            normalized_job = {
                "title": job["title"],
                "company": job["company_name"],
                "location": location,
                "url": job["absolute_url"],
                "source": "greenhouse",
                "description": description,
            }
            matching_jobs.append(normalized_job)

    return matching_jobs
