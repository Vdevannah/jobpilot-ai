# Phase 7: Mock-based agent workflow

## Purpose

Phase 7 adds structured job and resume analysis, evidence checks, and a reusable
workflow awaiting human review. It exercises integration boundaries without a
real LLM, credentials, new dependencies, or changes to deterministic matching.

## Architecture

`src/ai/orchestrator.py` accepts four agents through constructor injection:

| Component | Responsibility |
| --- | --- |
| `JobAnalysisAgent` | Delegates to `analyze_job_description()`, which rejects blank descriptions and validates client output. |
| `ResumeAnalysisAgent` | Rejects blank resume text and validates the injected resume client's output. |
| `ResearchAgent` | Identifies absent or unclear requirements and produces follow-up questions; performs no external research. |
| `CriticAgent` | Checks skills, relevant-track experience, missing evidence, invalid experience values, and explicitly labeled sample data. |

The workflow runs job analysis, resume analysis, research, then criticism. Research
receives the job analysis; criticism receives both job and resume analyses.
The critic does not consume the research report. All four results are retained
in the final report.

## Client protocols and dependency injection

`src/ai/client.py` defines two structural contracts:

- `LLMClient.analyze_job(description: str) -> JobAnalysis`
- `ResumeLLMClient.analyze_resume(resume_text: str) -> ResumeAnalysis`

Callers supply client instances to analysis agents and agent instances to the
orchestrator. Implementations need compatible methods, not inheritance from a
particular SDK. Tests can inject fake clients or agents.

`MockLLMClient` and `MockResumeLLMClient` return deterministic, explicitly labeled
samples. They do not extract information from the input. The job mock always
returns a data role requiring three years; the resume mock always returns eight
pharma years and one data year. These are fictional fixtures, including when the
input describes a medicinal chemistry role or only data training.

## Structured outputs and validation

`src/ai/schemas.py` defines:

- `JobAnalysis`: required/preferred skills, optional minimum years, track, summary.
- `ResumeAnalysis`: skills, professional experience by track, domains, education,
  summary.
- `ResearchReport`: missing information, research questions, summary.
- `CriticReport`: warnings, critic review flag, summary.
- `WorkflowReport`: all four nested results, workflow review flag,
  `status: Literal["pending_review"]`, and `analysis_mode: Literal["mock"]`.

The orchestrator explicitly sets `analysis_mode="mock"` on every report. This
machine-readable label identifies this phase as mock analysis, not real LLM
extraction, regardless of whether individual summaries mention sample data.

Models use Pydantic strict validation and `revalidate_instances="always"`.
The orchestrator validates each agent result and constructs a validated nested
report. Validation checks structure and types; it cannot establish whether a
claim is supported by the source text. The critic separately flags negative or
non-finite relevant experience values.

## Orchestration and errors

`JobPilotOrchestrator.run(job_description, resume_text)` validates both inputs
before invoking any agent. Non-string inputs raise `TypeError`; blank or
whitespace-only inputs raise `ValueError`. Original nonblank text is forwarded
unchanged. Invalid outputs raise Pydantic `ValidationError`. Agent exceptions
propagate, later stages do not run, and no partial workflow report is returned.
There are no retries, persistence, or approval actions.

## Experience and profile compatibility

Professional experience remains a mapping such as `{"pharma": 8.0, "data": 1.0}`.
The critic uses only the job's track. It does not total unrelated experience or
substitute pharma experience for data experience. Missing entries remain absent
and are not treated as zero. An explicit zero is a known value.

Education and training are separate from employment. A PhD or training program
does not add professional years. Future extraction clients must uphold this
contract; current schema validation cannot verify provenance. The mock's data
year is fictional sample employment, not a deduction from training text.

Experience keys align with `CandidateProfile.experience_by_domain`, but no
automatic profile conversion or overwrite occurs. Resume domains are a flat
list and are not automatically assigned to `CandidateProfile.domains_by_track`.
Existing matching scores, weights, and profile structures remain unchanged.

Fictional mock experience values must never overwrite the approved candidate
profile. Mock reports are demonstration artifacts, not authoritative candidate
facts, and must not be used to update approved employment history.

## Human review and boundaries

Every orchestrator result sets `requires_human_review=True` and
`status="pending_review"`, even when the critic reports no warnings. The critic's
own review flag is preserved separately. The workflow has no approval action,
application submission, email, messaging, database writes, or resume updates.
Injected implementations remain caller-controlled; injection is not a sandbox
that prevents arbitrary replacement agents from performing I/O.

## Current limitations

There is no real LLM, company research, salary/benefit lookup, or autonomous job
application. Research only examines supplied job fields. Criticism uses simple
rules and normalized exact skill names, not semantic equivalence. Sample
detection uses summary keywords and is not a provenance guarantee. A clear
critic report supports only a preliminary assessment of supplied fields, not a
verified hiring recommendation.

## Run the demonstration

From the repository root with existing dependencies installed:

```python
from src.ai.agents.job_agent import JobAnalysisAgent
from src.ai.agents.resume_agent import ResumeAnalysisAgent
from src.ai.agents.research_agent import ResearchAgent
from src.ai.agents.critic_agent import CriticAgent
from src.ai.client import MockLLMClient, MockResumeLLMClient
from src.ai.orchestrator import JobPilotOrchestrator

workflow = JobPilotOrchestrator(
    JobAnalysisAgent(MockLLMClient()),
    ResumeAnalysisAgent(MockResumeLLMClient()),
    ResearchAgent(),
    CriticAgent(),
)
report = workflow.run(
    "Principal Scientist in medicinal chemistry, requiring expertise in small-molecule drug discovery, structure-activity relationships, PROTACs, and 8 years of industry experience.",
    "PhD in Organic Chemistry with 8 years of pharmaceutical research experience in medicinal chemistry, oncology drug discovery, PROTACs, and structure-activity relationship analysis. Also completed training in Python, SQL, and data engineering.",
)
print(report.model_dump_json(indent=2))
```

The result is fixed mock data and may not reflect this text. Phase 7F validation
confirmed all four agents executed, status was `pending_review`, workflow review
was required, and pharma/data years remained separate. The demonstration ran
with network socket creation, file opening, and subprocess creation blocked.
No external calls or applications occurred. Its critic warnings concern the
sample data role, SQL evidence, and mock provenance, not the actual supplied role.

## Tests

Run from the repository root in the project environment:

```sh
python -m pytest -q
```

Or select the existing virtual environment explicitly:

```sh
.venv/bin/python -m pytest -q
```

Phase 7F regression result: **155 passed**. Coverage includes injected clients,
validation, agent order, exception propagation, mandatory review, track-specific
experience, unchanged input models, and offline execution with I/O guards.

## Future real LLM integration

Add clients implementing the existing protocols and inject them without changing
the agent execution order. Before enabling real analysis, explicitly extend the
workflow's mock-only mode contract so real results are labeled accurately.
A future implementation will need explicit configuration,
structured response parsing, evidence/provenance handling, and defined timeout
and failure behavior. Preserve missing values and separate employment tracks;
do not infer professional employment from education. Retain offline mock tests
and human review. Real research, persistence, and approval/application actions
are separate future work and are not enabled by replacing an analysis client.
