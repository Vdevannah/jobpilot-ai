import requests


def get_jobs(company, keywords):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"

    response = requests.get(url)
    data = response.json()

    jobs = data["jobs"]

    for job in jobs:
        title = job["title"].lower()

        if any(keyword.lower() in title for keyword in keywords):
            print("Title:", job["title"])
            print("Company:", job["company_name"])
            print("Location:", job["location"]["name"])
            print("URL:", job["absolute_url"])
            print("-" * 50)