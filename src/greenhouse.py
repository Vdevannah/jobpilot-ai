import requests

def is_us_location(location):
    us_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC"
    }

    location_lower = location.lower()

    if "united states" in location_lower or "usa" in location_lower:
        return True

    if "," in location:
        state = location.split(",")[-1].strip().upper()

        if state in us_states:
            return True

    return False

def matches_target_role(title, target_roles):
    title = title.lower()
    excluded_phrases = [
        "strategic finance",
        "financial planning",
        "investment banking"
    ]

    if any(phrase in title for phrase in excluded_phrases):
        return False

    return any(role.lower() in title for role in target_roles)

def get_jobs(company, target_roles):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"

    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    jobs = data["jobs"]
    matching_jobs = []

    for job in jobs:
        title = job["title"]
        location = job["location"]["name"]

        if is_us_location(location) and matches_target_role(title, target_roles):
            normalized_job = {
                "title": job["title"],
                "company": job["company_name"],
                "location": location,
                "url": job["absolute_url"],
                "source": "greenhouse"
            }
            matching_jobs.append(normalized_job)

    return matching_jobs
