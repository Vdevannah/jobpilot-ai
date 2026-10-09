"""Stage local PDF resume variants as private, UNAPPROVED plain text.

Reads a local, git-ignored JSON configuration naming exactly three PDFs (one
each for pharma/data/scientific_ai), extracts text locally with pypdf, and
writes each to private_resumes/<variant>.txt. This utility performs NO
privacy approval: output is raw extracted text, still subject to the
existing preview_resume.py / approve_resume() boundary before any analysis.
It never reads preview_resume.py's sanitizer, never constructs an OpenAI
client, and makes no network requests. OCR is not used; image-only or
encrypted PDFs are rejected rather than processed.

Configuration: copy config/pdf_sources.example.json to
private_resumes/pdf_sources.json and edit it locally to point at your three
real PDFs. That directory is git-ignored, so the configuration -- which
necessarily contains candidate-identifying local file paths -- is never
committed. This script never prints the configured paths or PDF content;
only the three fixed variant names (pharma/data/scientific_ai) ever appear
in its output.
"""

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.resume_text_repair import RepairReport, repair_section_headings

VARIANTS = ('pharma', 'data', 'scientific_ai')
OUTPUT_DIR = PROJECT_ROOT / 'private_resumes'
CONFIG_PATH = OUTPUT_DIR / 'pdf_sources.json'
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / 'config' / 'pdf_sources.example.json'
MIN_EXTRACTED_CHARS = 20


class PdfPrepError(ValueError):
    """Local PDF staging could not complete. Messages never include raw PDF

    content, configured file paths, or JSON configuration contents -- only
    the fixed variant names (pharma/data/scientific_ai) and generic text.
    """


def _load_pypdf():
    if importlib.util.find_spec('pypdf') is None:
        raise PdfPrepError(
            "Missing dependency 'pypdf'. Install it into the project virtual "
            'environment (it is already listed in requirements.txt) before '
            'running this script; no automatic installation is performed.'
        )
    import pypdf
    return pypdf


def is_gitignored(path: Path) -> bool:
    """True only if `git check-ignore` confirms the path is ignored in this repo."""
    try:
        result = subprocess.run(
            ['git', 'check-ignore', '-q', str(path)],
            cwd=PROJECT_ROOT,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def load_pdf_sources(config_path: Path) -> dict[str, Path]:
    """Load and validate the local PDF source configuration.

    Never includes a configured path or JSON content in any error message;
    only the fixed variant names and generic descriptions are reported.
    """
    if not is_gitignored(config_path):
        raise PdfPrepError(
            'Refusing to read the local PDF source configuration: its location is '
            'not confirmed git-ignored. Check that the private_resumes/ rule in '
            '.gitignore is intact before proceeding.'
        )
    try:
        raw = config_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        raise PdfPrepError(
            'No local PDF source configuration found. Copy '
            'config/pdf_sources.example.json to private_resumes/pdf_sources.json '
            'and edit it locally to point at your three real PDFs.'
        ) from None
    except OSError:
        raise PdfPrepError('Local PDF source configuration could not be read.') from None

    try:
        config = json.loads(raw)
    except json.JSONDecodeError:
        raise PdfPrepError(
            'Local PDF source configuration is not valid JSON. See '
            'config/pdf_sources.example.json for the expected format.'
        ) from None
    if not isinstance(config, dict):
        raise PdfPrepError('Local PDF source configuration must be a JSON object.')

    missing_variants = [v for v in VARIANTS if not isinstance(config.get(v), str) or not config.get(v).strip()]
    if missing_variants:
        raise PdfPrepError(
            'Local PDF source configuration is missing or has an invalid entry for: '
            + ', '.join(missing_variants) + '. All three variants are required.'
        )

    resolved: dict[str, Path] = {}
    invalid_variants: list[str] = []
    for variant in VARIANTS:
        candidate = Path(config[variant]).expanduser()
        if candidate.is_file() and candidate.suffix.casefold() == '.pdf':
            resolved[variant] = candidate
        else:
            invalid_variants.append(variant)
    if invalid_variants:
        raise PdfPrepError(
            'Configured source for variant(s) ' + ', '.join(invalid_variants)
            + ' was not found or is not a PDF file. (The configured path itself is '
            'not shown here; check it locally in private_resumes/pdf_sources.json.)'
        )
    return resolved


def extract_text_from_pdf(path: Path) -> tuple[str, RepairReport]:
    """Extract text locally. Rejects encrypted, unreadable, or image-only PDFs.

    Applies the conservative local heading repair before returning, so common
    PDF extraction artifacts (section headings merged onto the same line as
    their content) do not silently defeat the privacy sanitizer's section
    allowlist. Returns the repaired text together with a report describing
    which headings were recognized -- never the resume content itself.
    """
    pypdf = _load_pypdf()
    try:
        reader = pypdf.PdfReader(str(path))
    except Exception:
        raise PdfPrepError('Unreadable PDF for this variant.') from None

    if getattr(reader, 'is_encrypted', False):
        try:
            decrypt_result = reader.decrypt('')
        except Exception:
            decrypt_result = 0
        if not decrypt_result:
            raise PdfPrepError('Encrypted PDF cannot be opened locally without a password.')

    try:
        pages_text = [page.extract_text() or '' for page in reader.pages]
    except Exception:
        raise PdfPrepError('Unreadable PDF for this variant.') from None

    text = '\n'.join(pages_text).strip()
    if len(text) < MIN_EXTRACTED_CHARS:
        raise PdfPrepError(
            'No reliable extractable text found (likely image-only/scanned; OCR is not used).'
        )
    result = repair_section_headings(text)
    return result.text, result.report


def write_private_resume(key: str, text: str, *, output_dir: Path, overwrite: bool) -> Path:
    if key not in VARIANTS:
        raise PdfPrepError('Unsupported resume key; refusing to write.')
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(output_dir, 0o700)
    except OSError:
        pass

    target = (output_dir / f'{key}.txt').resolve()
    if target.parent != output_dir.resolve():
        raise PdfPrepError('Unsafe output path rejected.')
    if not is_gitignored(target):
        raise PdfPrepError('Refusing to write: output location is not confirmed git-ignored.')
    if target.exists() and not overwrite:
        raise PdfPrepError(f'{target.name} already exists; rerun with --overwrite to replace it.')

    target.write_text(text, encoding='utf-8')
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--overwrite', action='store_true',
        help='Allow replacing an existing private_resumes/<variant>.txt file.',
    )
    args = parser.parse_args(argv)

    try:
        sources = load_pdf_sources(CONFIG_PATH)
    except PdfPrepError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    staged: list[str] = []
    had_failure = False
    for key, pdf_path in sources.items():
        try:
            text, report = extract_text_from_pdf(pdf_path)
            write_private_resume(key, text, output_dir=OUTPUT_DIR, overwrite=args.overwrite)
            staged.append(key)
            print(f'{key}: extracted locally and staged -> private_resumes/{key}.txt (content not displayed)')
            if report.mapped_headings:
                print(f'  heading repair recognized: {", ".join(sorted(set(report.mapped_headings)))}')
            if report.needs_manual_review:
                print(
                    f'  manual review recommended: {len(report.unmapped_headings)} unmapped heading(s), '
                    f'{report.ambiguous_count} ambiguous line(s) left untouched (see docs/RESUME_PRIVACY.md).'
                )
        except PdfPrepError as exc:
            had_failure = True
            print(f'{key}: {exc}', file=sys.stderr)

    if staged:
        print(
            '\nNot approved for analysis. Preview each file locally and inspect it '
            'yourself before anything is shared with any AI client:'
        )
        for key in staged:
            print(f'  .venv/bin/python scripts/preview_resume.py private_resumes/{key}.txt --preview')

    return 1 if had_failure else 0


if __name__ == '__main__':
    raise SystemExit(main())
