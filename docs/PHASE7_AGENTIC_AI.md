# Phase 7: Mock-based agent workflow

## Phase 7G.1: Optional OpenAI client foundation

`src/ai/openai_client.py` adds a standalone `OpenAIJobClient` implementing the
existing `LLMClient` contract. It is not wired into orchestration; the workflow
continues to use mock clients and `analysis_mode="mock"`. Do not inject the real
client into that workflow until real-mode reporting is implemented.

The default `OPENAI_MODEL` is `gpt-4.1-mini`, a lower-cost model supporting
[Responses and structured outputs](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
Override it through the environment with a model supporting those capabilities.
Credentials come only from `OPENAI_API_KEY` in the process environment. This
adapter does not load `.env` files or log credentials. Existing `.gitignore`
already excludes `.env`; never commit credential files.

The SDK is pinned to `openai==3.27.0`, tested with Pydantic 2.13.5 and the project's
existing httpx2 dependency. It uses `responses.parse(text_format=JobAnalysis)`
and `output_parsed`, as described in the
[structured outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).
Importing the module and constructing the client make no API requests. Calling
`analyze_job()` explicitly is the only request path. Mock clients remain independent.

Requests use a 30-second SDK timeout, zero automatic retries, a 1,000-token output
cap, and `store=False`. A token-limited/incomplete response raises an error.
Missing credentials, refusals, invalid output, timeouts, and API/connection errors
have explicit adapter exceptions; none silently substitute mock data. Error
messages omit upstream response bodies. The prompt treats the description as
untrusted input, distinguishes required/preferred skills, and prohibits invented
requirements or experience. Unspecified experience must be null.

Tests mock SDK responses and block network sockets. No live API validation has
been performed; account access and extraction quality remain unverified. The
following sections describe the existing mock workflow, which is unchanged.

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

## Phase 7G.5A: Qualification separation and critic accuracy

Job extraction now requests technical competencies only in skill lists. Required
professional years belong in `minimum_experience_years`; preferred years must not
be promoted to a minimum. Required education is preserved in the existing summary
using `Required education: <qualification>.`, with preferred education labeled
separately. The JobAnalysis schema remains unchanged.

The deterministic critic checks legacy degree entries in required skills against
resume education and recognizes explicitly labeled required education in summaries.
Year-bearing entries are excluded from technical skill comparison; only structured
minimum years and the matching professional-experience track drive comparisons.
Missing track evidence is reported without assuming zero or borrowing another track.

Technical comparisons normalize case, punctuation, spacing, and limited introductory
wording. Explicit alias groups cover SAR/structure-activity relationship(s),
PROTAC(s)/proteolysis-targeting chimera(s), and TPD/targeted protein degradation.
Medicinal chemistry does not establish structure-based drug design or other
unlisted competencies. No deterministic matching-engine aliases or weights changed.

Remaining limitations: there is no dedicated education-requirement field, so free
prose education requirements outside the labeled summary convention or legacy skill
entries are not reliably parsed. Degree comparisons are conservative normalized
text comparisons, not degree equivalency decisions; alternatives, degree status,
and field equivalence need human review. The critic cannot verify whether the LLM
correctly extracted required versus preferred qualifications. Year-bearing legacy
skill entries without a structured minimum trigger an insufficient-evidence warning
rather than inferred years. Skill aliases are an explicit limited list, not semantic
inference. Prompt regression tests verify request instructions, not live extraction
accuracy. No live API calls were made for this change. Workflow-level human review
and `pending_review` status remain mandatory in both modes, even if the critic has
no warnings. CandidateProfile and discovery behavior remain unchanged.

## Phase 7G.5B: Deterministic resume recommendation

`src/ai/resume_selector.py` exposes `recommend_resume(job, variants)` for an already
analyzed and evaluated opportunity. Supply a nonempty mapping of `pharma`, `data`,
and/or `scientific_ai` to existing ResumeAnalysis objects. These are presentations
of the same candidate, not separate candidates. Variant identifiers confer no bonus.
The function has no discovery, persistence, network, application, or profile access.
It is standalone and is not yet called by the orchestrator.

Scoring is additive and independent of Phase 1–6 matching weights:

- Each unique evidenced required technical skill: 4 points.
- Each unique evidenced preferred technical skill: 1 point, excluding required skills.
- Each evidenced required education qualification: 2 points.
- Meeting the structured minimum with valid years on the job's track: 2 points total.
- Explicit resume-domain membership in the documented code's small track-domain
  vocabulary: 1 point total, regardless of the number of matches.

The selector reuses the critic's normalization and explicit SAR/PROTAC/TPD aliases.
Required education uses legacy degree entries or the labeled summary convention.
No experience is inferred from skills, training, projects, headlines, or names.
Missing employment is visible but does not disqualify a variant. Each variant's
claims stay separate. Differing explicit year values for the same track produce a
conflict limitation and suppress experience points for that track across variants;
missing entries alone do not establish a conflict. Human reconciliation is required.

The result contains ordered rankings, matched/missing evidence, score explanations,
and limitations. Equal scores use stable display order pharma, data, scientific_ai;
this is not a substantive preference. Top ties have no single recommendation.
When no variant earns direct qualification points, evidence is insufficient and
there is no recommendation even if domain relevance differs. Every report requires
human review and remains pending_review. Missing qualifications do not remove a
resume from the ranking, nor can the selector remove an opportunity from discovery.

Limitations: input claims are not independently verified. Skills lack project versus
employment provenance, and education matching is conservative. Scientific AI has
no dedicated JobAnalysis track; explicit technical skills drive that recommendation.
The domain vocabulary is deliberately small, and scores are evidence counts rather
than probabilities. These checks do not establish degree equivalency, employment
chronology, or factual consistency beyond differing explicit track-year claims.
Future orchestration should call selection only after discovery and suitability
evaluation, then present the recommendation for human review without overwriting
CandidateProfile or changing opportunity scores.
