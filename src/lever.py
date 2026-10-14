import requests

from src.utils import extract_structured_text, is_us_location, matches_target_role


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
            description_blocks = []
            plain_description = job.get("descriptionPlain", "").strip()
            if plain_description:
                description_blocks.append(plain_description)
            for item in job.get("lists", []):
                section_heading = item.get("text", "").strip()
                if section_heading:
                    description_blocks.append(section_heading)
                section_content = extract_structured_text(item.get("content", ""))
                if section_content:
                    description_blocks.append(section_content)
            description = "\n\n".join(description_blocks)

            normalized_job = {
                "title": title,
                "company": company_name,
                "location": location,
                "url": job["hostedUrl"],
                "source": "lever",
                "description": description,
            }
            matching_jobs.append(normalized_job)

    return matching_jobs
