def is_us_location(location):
    us_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC"
    }
    us_state_names = {
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
        "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
        "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
        "maine", "maryland", "massachusetts", "michigan", "minnesota",
        "mississippi", "missouri", "montana", "nebraska", "nevada",
        "new hampshire", "new jersey", "new mexico", "new york",
        "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
        "pennsylvania", "rhode island", "south carolina", "south dakota",
        "tennessee", "texas", "utah", "vermont", "virginia", "washington",
        "west virginia", "wisconsin", "wyoming", "washington dc"
    }

    location_lower = location.lower()

    if "united states" in location_lower or "usa" in location_lower:
        return True

    if "," in location:
        state = location.split(",")[-1].strip()
        state_upper = state.upper()
        state_lower = state.lower()

        if state_upper in us_states or state_lower in us_state_names:
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


def deduplicate_jobs(jobs):
    unique_jobs = []
    seen = set()

    for job in jobs:
        key = (
            job["company"].strip().lower(),
            job["title"].strip().lower(),
            job["location"].strip().lower()
        )

        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    return unique_jobs
