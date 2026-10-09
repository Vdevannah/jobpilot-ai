"""Local-only CLI demo of the integrated deterministic resume selector.

Runs JobPilotOrchestrator.rank_resumes_for_job() against three fictional,
already-structured resume variants (pharma/data/scientific_ai) and either a
built-in fictional job example or custom fictional job-description text.
Mock mode only: no OpenAI client is constructed, no credentials are read, and
no network request is made. Never loads a private resume file, a PDF, or any
personal information; the three resume variants are hard-coded fictional
ResumeAnalysis objects, not text. Does not alter resume_selector's scoring,
career-track logic, CandidateProfile, or job discovery.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.agents.job_agent import JobAnalysisAgent
from src.ai.client import MockLLMClient
from src.ai.orchestrator import JobPilotOrchestrator, ResumeSelectionReport
from src.ai.schemas import JobAnalysis, ResumeAnalysis


FICTIONAL_VARIANTS: dict[str, ResumeAnalysis] = {
    'pharma': ResumeAnalysis(
        skills=['SAR', 'PROTACs', 'medicinal chemistry'],
        professional_experience_years={'pharma': 8.0},
        domains=['pharma'],
        education=['PhD in Organic Chemistry (fictional)'],
        summary='Fictional pharma resume variant for demonstration only.',
    ),
    'data': ResumeAnalysis(
        skills=['Python', 'SQL', 'data engineering'],
        professional_experience_years={'data': 3.0},
        domains=['data'],
        education=['BSc in Computer Science (fictional)'],
        summary='Fictional data resume variant for demonstration only.',
    ),
    'scientific_ai': ResumeAnalysis(
        skills=['Python', 'cheminformatics', 'RDKit', 'machine learning'],
        professional_experience_years={},
        domains=[],
        education=['PhD in Computational Chemistry (fictional)'],
        summary='Fictional scientific_ai resume variant for demonstration only.',
    ),
}

# Hand-authored fictional (description, JobAnalysis) pairs -- not run through
# any LLM -- so the three built-in examples deterministically favor their
# matching variant. job_track uses only existing literals ("pharma", "data",
# "unknown"); no new career-track value is introduced.
EXAMPLES: dict[str, tuple[str, JobAnalysis]] = {
    'medchem': (
        'Fictional Principal Scientist, Medicinal Chemistry. Requires SAR and '
        'PROTAC expertise with 5+ years of pharmaceutical industry research.',
        JobAnalysis(
            required_skills=['SAR', 'PROTACs'],
            preferred_skills=['structure-based drug design'],
            minimum_experience_years=5,
            job_track='pharma',
            summary='Fictional Principal Scientist, Medicinal Chemistry role.',
        ),
    ),
    'data_engineer': (
        'Fictional Data Engineer, Analytics team. Requires Python, SQL, and '
        'data engineering experience; AWS preferred; 2+ years required.',
        JobAnalysis(
            required_skills=['Python', 'SQL', 'data engineering'],
            preferred_skills=['AWS'],
            minimum_experience_years=2,
            job_track='data',
            summary='Fictional Data Engineer, Analytics role.',
        ),
    ),
    'scientific_ai': (
        'Fictional Scientific AI / Cheminformatics Research Scientist. '
        'Requires cheminformatics, RDKit, and machine learning; Python preferred.',
        JobAnalysis(
            required_skills=['cheminformatics', 'RDKit', 'machine learning'],
            preferred_skills=['Python'],
            minimum_experience_years=None,
            job_track='unknown',
            summary='Fictional Scientific AI / Cheminformatics Research Scientist role.',
        ),
    ),
}


class _FixedJobAgent:
    """Returns one fixed, hand-authored fictional JobAnalysis for this demo."""

    def __init__(self, job_analysis: JobAnalysis) -> None:
        self._job_analysis = job_analysis

    def analyze(self, description: str) -> JobAnalysis:
        return self._job_analysis


def run_demo(job_agent, job_description: str) -> ResumeSelectionReport:
    """Build a mock-mode orchestrator using only job_agent and run selection.

    The resume-analysis, research, and critic agents are never constructed or
    invoked by rank_resumes_for_job(); passing None here fails loudly if that
    ever changes, instead of silently touching an unrelated client.
    """
    orchestrator = JobPilotOrchestrator(
        job_agent, None, None, None, analysis_mode='mock',
    )
    return orchestrator.rank_resumes_for_job(job_description, FICTIONAL_VARIANTS)


def format_report(report: ResumeSelectionReport) -> str:
    """Render a concise, human-readable summary. Never includes resume text."""
    job = report.job_analysis
    rec = report.recommendation
    lines = [
        '=== Job requirements (fictional) ===',
        f'Track: {job.job_track}',
        f'Required skills: {", ".join(job.required_skills) or "(none)"}',
        f'Preferred skills: {", ".join(job.preferred_skills) or "(none)"}',
        'Minimum experience (years): ' + (
            str(job.minimum_experience_years) if job.minimum_experience_years is not None
            else '(unspecified)'
        ),
        f'Summary: {job.summary}',
        '',
        '=== Resume variant rankings ===',
    ]
    for row in rec.rankings:
        marker = (
            '  <= RECOMMENDED' if row.variant == rec.recommended_variant
            else '  (tied)' if row.variant in rec.tied_variants else ''
        )
        lines.append(f'- {row.variant}: score {row.score}{marker}')
        lines.append(f'    matched: {"; ".join(row.matched_evidence) or "(none)"}')
        lines.append(f'    missing: {"; ".join(row.missing_evidence) or "(none)"}')
    lines.append('')
    if rec.recommended_variant:
        lines.append(f'Recommended variant: {rec.recommended_variant}')
    elif rec.tied_variants:
        lines.append(f'Tied variants, no single recommendation: {", ".join(rec.tied_variants)}')
    else:
        lines.append('No recommendation: insufficient evidence.')
    if rec.limitations:
        lines.append('Limitations:')
        lines.extend(f'  - {item}' for item in rec.limitations)
    lines.append('')
    lines.append(f'requires_human_review={report.requires_human_review} status={report.status}')
    lines.append(
        'NOTE: Fictional structured resume data only; no private resume text, '
        'PDFs, or personal information were loaded or displayed.'
    )
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--example', choices=sorted(EXAMPLES),
        help='Run a built-in fictional job example (medchem, data_engineer, scientific_ai).',
    )
    group.add_argument(
        '--job-description',
        help='Run custom fictional job-description text instead of a built-in example.',
    )
    args = parser.parse_args(argv)

    if args.example is None and args.job_description is None:
        print(
            'No demo run. Specify --example {medchem,data_engineer,scientific_ai} '
            'or --job-description "..."; see --help.'
        )
        return 0

    if args.example is not None:
        description, job_analysis = EXAMPLES[args.example]
        job_agent = _FixedJobAgent(job_analysis)
    else:
        description = args.job_description
        if not description.strip():
            print('Job description must not be empty or blank.', file=sys.stderr)
            return 1
        print(
            "NOTE: mock mode returns MockLLMClient's fixed sample job data, not real "
            'extraction of the text you supplied; this is existing, documented mock behavior.'
        )
        job_agent = JobAnalysisAgent(MockLLMClient())

    try:
        report = run_demo(job_agent, description)
    except (TypeError, ValueError) as error:
        print(f'Unable to run the demo: {error}', file=sys.stderr)
        return 1

    print(format_report(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
