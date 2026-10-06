from src.greenhouse import get_jobs
from src.lever import get_lever_jobs
from src.repository import save_jobs
from src.utils import deduplicate_jobs


target_roles = [
    "data engineer",
    "data scientist",
    "data analyst",
    "analytics",
    "business intelligence",
    "business analyst",
    "medicinal chemist",
    "senior scientist",
    "process chemist",
    "process scientist",
    "senior research scientist",
    "principal scientist",
    "senior chemist",
    "organic chemist"
]

greenhouse_jobs = get_jobs("airbnb", target_roles)

lever_jobs = get_lever_jobs("leverdemo", "Lever Demo", target_roles)

all_jobs = greenhouse_jobs + lever_jobs
unique_jobs = deduplicate_jobs(all_jobs)
added_count = save_jobs(unique_jobs)

print("Greenhouse jobs:", len(greenhouse_jobs))
print("Lever jobs:", len(lever_jobs))
print("Total combined jobs:", len(all_jobs))
print("Unique jobs:", len(unique_jobs))
print("New jobs saved:", added_count)
