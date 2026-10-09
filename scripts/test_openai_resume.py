"""Manually triggered live resume analysis; no request without --live."""

import argparse
from pathlib import Path
import sys

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Support direct execution from any working directory.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.openai_client import OpenAIResumeClient, OpenAIResumeClientError, MissingCredentialsError


SAMPLE_RESUME = (
    "FICTIONAL SAMPLE RESUME FOR TESTING. PhD in Organic Chemistry. "
    "8 years of pharmaceutical industry research experience in medicinal chemistry, "
    "oncology drug discovery, PROTACs, and SAR. Completed Python, SQL, and data "
    "engineering training. No professional data engineering employment."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Authorize one real OpenAI request.")
    args = parser.parse_args(argv)
    if not args.live:
        print("No API request made. Run with --live to authorize the live OpenAI smoke test.")
        return 0

    from src.ai.resume_privacy import review_sample_locally, ResumePrivacyError

    try:
        approved_resume = review_sample_locally(SAMPLE_RESUME)
    except ResumePrivacyError:
        print("Privacy review incomplete; no API calls made.", file=sys.stderr)
        return 1

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    try:
        result = OpenAIResumeClient().analyze_resume(approved_resume)
    except (OpenAIResumeClientError, MissingCredentialsError):
        print("OpenAI resume analysis failed. Check local configuration and API access.", file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
