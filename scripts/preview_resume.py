"""Preview a local UTF-8 text resume without approval, credentials, or API access."""

import argparse
from getpass import getpass
from pathlib import Path
import sys
import warnings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.resume_privacy import preview_resume, PUBLICATIONS_SECTION


class _InsufficientContentError(ValueError):
    """Sanitized output fell below the minimum reviewable-line floor."""


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Invalid arguments. Use --help for instructions.\n')


def main(argv: list[str] | None = None) -> int:
    parser = SafeParser(description=__doc__)
    parser.add_argument('path', nargs='?', help='Local UTF-8 .txt resume; PDF is unsupported.')
    parser.add_argument('--preview', action='store_true', help='Read and display sanitized text locally; never approve it.')
    args = parser.parse_args(argv)
    if not args.preview:
        print('Nothing read or displayed. Use --preview with a local .txt path; see --help.')
        return 0
    try:
        if not args.path or Path(args.path).suffix.casefold() != '.txt':
            raise ValueError('Unsupported input')
        raw = Path(args.path).read_text(encoding='utf-8-sig')
        if not raw.strip() or raw.lstrip().startswith('%PDF') or any(
            not char.isprintable() and char not in '\n\r\t' for char in raw
        ):
            raise ValueError('Invalid plain text')
        print('Enter each known name, city, or address variant at the hidden prompt. Blank ends the list.')
        identifiers = []
        # Fail closed if the terminal cannot suppress identifier echo.
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            while True:
                identifier = getpass('Identifier to remove (hidden): ').strip()
                if not identifier:
                    break
                identifiers.append(identifier)
        sanitized = preview_resume(raw, identifiers=identifiers)
        if len(sanitized.splitlines()) < 3:
            raise _InsufficientContentError('No reviewable qualifications')
    except _InsufficientContentError:
        print('Unable to prepare a local preview: too little content survived privacy sanitization. '
              'This usually means recognized section headers (Skills/Education/Professional '
              'experience/Projects/Qualifications) are missing or were merged with other text during '
              'extraction, or every remaining line matched one of the identifiers you entered. Review '
              'the text file\'s section headers locally and retry. No content approved.', file=sys.stderr)
        return 1
    except (Exception, KeyboardInterrupt):
        print('Unable to prepare a local preview. Check the text file and retry. No content approved.', file=sys.stderr)
        return 1
    print('WARNING: Automated sanitization may miss identifiers. Review every line locally. '
          'Only Delaware, USA is permitted as candidate location. This preview is NOT approved; '
          'remove any remaining identifiers before external analysis.')
    if PUBLICATIONS_SECTION in {ln.casefold().rstrip(':') for ln in sanitized.splitlines()}:
        print('NOTE: Publications/Patents citations shown below are preserved for local review '
              'but are excluded from external AI payloads by default. Including them requires a '
              'separate, explicit approval decision (include_citations=True), never implied by '
              'approving the rest of this resume.')
    print(sanitized)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
