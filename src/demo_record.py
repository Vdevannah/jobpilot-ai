"""Identifies demo/sample job records seeded during local development
(e.g. companies named "Acme", "Test Company", "Demo Company") -- never by
company name, only by the job's own URL pointing at the IANA-reserved
example.com domain (RFC 2606). A real employer could coincidentally be
named "Acme"; this never assumes otherwise.

Mirrors the identical, independently-maintained checks already used by
frontend/src/utils/demoRecord.js and scripts/refresh_job_descriptions.py's
local is_demo_record() helper -- this module doesn't replace either of
those (both are left exactly as they are), it just gives src/api.py (and
any other backend code) the same check without importing a script module.

This is presentation/labeling metadata only. It is never passed into, or
used by, src.ai.job_requirements.extract_job_requirements() -- requirement
extraction stays entirely independent of where a job's data came from.
A False result here is simply "not a known placeholder" -- it is not
evidence that the posting is live, current, or still accepting
applications.
"""

from urllib.parse import urlparse

DEMO_HOSTNAMES = frozenset({"example.com", "www.example.com"})


def is_demo_record(url: str | None) -> bool:
    if not url:
        return False
    try:
        return urlparse(url).hostname in DEMO_HOSTNAMES
    except ValueError:
        return False
