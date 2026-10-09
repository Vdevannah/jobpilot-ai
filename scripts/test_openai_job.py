"""Manually triggered live job analysis; no request without --live."""

import argparse
from pathlib import Path
import sys

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Support direct execution from any working directory.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.openai_client import OpenAIJobClient, OpenAIJobClientError


JOB_DESCRIPTION = (
    "Principal Scientist, Medicinal Chemistry. Requires a PhD in Organic Chemistry, "
    "8 years of pharmaceutical industry experience, expertise in small-molecule "
    "drug discovery, SAR analysis, PROTACs, and structure-based drug design."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Authorize one real OpenAI request.")
    args = parser.parse_args(argv)
    if not args.live:
        print("No API request made. Run with --live to authorize the live OpenAI smoke test.")
        return 0

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    try:
        result = OpenAIJobClient().analyze_job(JOB_DESCRIPTION)
    except OpenAIJobClientError:
        print("OpenAI job analysis failed. Check local configuration and API access.", file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
