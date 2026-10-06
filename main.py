from src.greenhouse import get_jobs


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

jobs = get_jobs("airbnb", target_roles)

print("Total matching jobs:", len(jobs))