"""Refreshes stored Job.description values with genuinely structured text,
re-fetched live from each job's original Greenhouse posting.

Why this exists: every description currently in the database was flattened
to a single space-joined line by the old src.utils.clean_html_text() during
collection (see Phase 8H.3.2's investigation). The paragraph/heading/list
structure in the *source* posting was never stored anywhere locally -- it
can only be recovered by re-fetching the posting's raw HTML from
Greenhouse's public API and re-converting it with the new
src.utils.extract_structured_text(), which preserves that structure.

Scope and safety:
  - Only Greenhouse-sourced jobs are refreshable this way (Lever jobs
    already get structured descriptions going forward from
    src/lever.py -- re-collection, not a refresh script, is what would
    update those). A job whose URL is the demo-seeded example.com
    placeholder domain is skipped entirely: there is no real posting to
    re-fetch, and refreshing it would be touching a fixture, not data.
  - The Greenhouse job id is read from the job's own stored `url` query
    string (?gh_jid=...), and the board token defaults to the job's
    company name, lowercased with non-alphanumeric characters removed
    (e.g. "Airbnb" -> "airbnb") -- override per company with
    --board-token "Company Name=slug" if that default is ever wrong.
  - Every write is a single UPDATE of the description column on the
    *existing* row, matched by that row's own primary key id (never an
    INSERT, so this can never create a duplicate job). No other column is
    ever touched -- not title, company, location, url, source, nor
    anything in a different table (CandidateProfile, matches, scores).
  - Defaults to a dry run: fetches live content, computes the new
    description, and prints a before/after diff summary for every
    candidate row, but writes nothing. Pass --apply to actually commit
    the updates after reviewing the dry run.

Usage:
    .venv/bin/python scripts/refresh_job_descriptions.py                              # dry run, all eligible jobs
    .venv/bin/python scripts/refresh_job_descriptions.py --job-id 4                    # dry run, one job
    .venv/bin/python scripts/refresh_job_descriptions.py --job-id 4 --job-id 6         # dry run, an explicit allowlist
    .venv/bin/python scripts/refresh_job_descriptions.py --job-id 4 --job-id 6 --apply # write, but only those ids
"""

import argparse
import sys
from urllib.parse import parse_qs, urlparse

import requests

from src.database import SessionLocal
from src.models import Job
from src.utils import extract_structured_text

GREENHOUSE_DETAIL_URL = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"
DEMO_HOSTNAMES = {"example.com", "www.example.com"}


def default_board_token(company):
    return "".join(ch for ch in company.lower() if ch.isalnum())


def extract_greenhouse_job_id(url):
    query = parse_qs(urlparse(url).query)
    values = query.get("gh_jid")
    return values[0] if values else None


def is_demo_record(url):
    try:
        return urlparse(url).hostname in DEMO_HOSTNAMES
    except ValueError:
        return False


def find_refreshable_jobs(session, job_ids=None):
    """job_ids, when given, is an explicit allowlist (Job.id IN (...)) --
    not a hint or a filter applied after the fact. Any id in that list that
    turns out to be a demo record, non-Greenhouse, or missing a gh_jid is
    silently excluded by the checks below, same as in the unrestricted
    case; the caller can tell by comparing len(result) against len(job_ids).
    """
    query = session.query(Job).filter(Job.source == "greenhouse")
    if job_ids is not None:
        query = query.filter(Job.id.in_(job_ids))

    eligible = []
    for job in query.order_by(Job.id).all():
        if is_demo_record(job.url):
            continue
        gh_jid = extract_greenhouse_job_id(job.url)
        if gh_jid is None:
            continue
        eligible.append((job, gh_jid))
    return eligible


def fetch_structured_description(board_token, gh_jid):
    url = GREENHOUSE_DETAIL_URL.format(board_token=board_token, job_id=gh_jid)
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    content = response.json().get("content", "")
    return extract_structured_text(content)


def summarize_change(job, new_description):
    old = job.description or ""
    if old == new_description:
        return "unchanged"
    gained_structure = "\n" in new_description
    structure_note = "now has paragraph/list structure" if gained_structure else "still a single line"
    return f"would update: {len(old)} chars -> {len(new_description)} chars ({structure_note})"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--job-id",
        type=int,
        action="append",
        default=None,
        dest="job_ids",
        help="Restrict to this job id. Repeat --job-id to build an explicit allowlist (e.g. "
        "--job-id 4 --job-id 6). Omit entirely to consider every eligible job.",
    )
    parser.add_argument(
        "--board-token",
        action="append",
        default=[],
        metavar="COMPANY=SLUG",
        help="Override the derived Greenhouse board token for a company, e.g. --board-token 'Acme Corp=acmecorp'.",
    )
    parser.add_argument("--apply", action="store_true", help="Actually write updates (default: dry run only).")
    args = parser.parse_args()

    board_token_overrides = {}
    for pair in args.board_token:
        if "=" not in pair:
            print(f"Ignoring malformed --board-token value: {pair!r} (expected COMPANY=SLUG)")
            continue
        company, slug = pair.split("=", 1)
        board_token_overrides[company.strip()] = slug.strip()

    session = SessionLocal()
    try:
        candidates = find_refreshable_jobs(session, job_ids=args.job_ids)
        if not candidates:
            print("No refreshable jobs found (Greenhouse-sourced, non-demo, with a gh_jid in the URL).")
            return

        if args.job_ids is not None:
            found_ids = {job.id for job, _gh_jid in candidates}
            requested_ids = set(args.job_ids)
            if found_ids != requested_ids:
                print(
                    f"REFUSING TO PROCEED: requested job ids {sorted(requested_ids)} but only "
                    f"{sorted(found_ids)} are eligible (Greenhouse-sourced, non-demo, with a gh_jid). "
                    f"Not eligible: {sorted(requested_ids - found_ids)}. Fix the allowlist and re-run."
                )
                return

        print(f"{'APPLY MODE' if args.apply else 'DRY RUN'} -- {len(candidates)} candidate job(s)\n")

        updated = 0
        for job, gh_jid in candidates:
            board_token = board_token_overrides.get(job.company, default_board_token(job.company))
            print(f"Job {job.id}: {job.title!r} at {job.company!r} (gh_jid={gh_jid}, board={board_token!r})")

            try:
                new_description = fetch_structured_description(board_token, gh_jid)
            except requests.RequestException as error:
                print(f"  SKIPPED -- could not fetch live posting: {error}")
                continue

            if not new_description:
                print("  SKIPPED -- live posting returned no content; refusing to overwrite with emptiness.")
                continue

            print(f"  {summarize_change(job, new_description)}")
            preview = new_description[:160].replace("\n", " / ")
            print(f"  preview: {preview}{'...' if len(new_description) > 160 else ''}")

            if args.apply and job.description != new_description:
                job.description = new_description
                updated += 1

        if args.apply:
            session.commit()
            print(f"\nApplied: updated the description of {updated} job row(s). No other fields were changed.")
        else:
            print("\nDry run complete -- no database changes were made. Re-run with --apply to write these updates.")
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
