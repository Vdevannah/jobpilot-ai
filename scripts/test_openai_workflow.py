"""Run the sample OpenAI workflow only with explicit --live authorization."""

import argparse
from pathlib import Path
import sys

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.orchestrator import create_workflow
from scripts.test_openai_job import JOB_DESCRIPTION
from scripts.test_openai_resume import SAMPLE_RESUME


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Authorize job and resume API requests.")
    args = parser.parse_args(argv)
    if not args.live:
        print("No API requests made. Run with --live to authorize the sample OpenAI workflow.")
        return 0

    from src.ai.openai_client import OpenAIJobClientError, OpenAIResumeClientError

    from src.ai.resume_privacy import review_sample_locally, ResumePrivacyError

    try:
        approved_resume = review_sample_locally(SAMPLE_RESUME)
    except ResumePrivacyError:
        print("Privacy review incomplete; no API calls made.", file=sys.stderr)
        return 1

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    try:
        report = create_workflow("openai").run(JOB_DESCRIPTION, approved_resume)
    except (OpenAIJobClientError, OpenAIResumeClientError) as error:
        print(f"OpenAI workflow failed ({type(error).__name__}). No fallback performed.", file=sys.stderr)
        return 1
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
