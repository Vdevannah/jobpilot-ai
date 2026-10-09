# Phase 7G.5 Part F: Broad career discovery

Resume variants are presentation choices, never job-discovery filters. Discover
and evaluate an opportunity first, then select the most appropriate resume.
Discovery must not depend on which resume is available, selected, or analyzed.

Preserve opportunities across data science (including junior roles), data
engineering (including junior roles), data analysis, business intelligence,
business and technical business analysis, Python development, software
engineering, medicinal chemistry, senior/principal scientist roles,
cheminformatics, computational chemistry, and scientific AI.

Lack of professional data engineering employment is an experience gap, not an
automatic rejection of data opportunities. Consider supported technical skills,
completed projects, and transferable scientific research evidence when evaluating
fit. Describe that evidence separately from professional employment years. Never
convert degrees, training, or projects into employment, or add pharmaceutical
years to data years. Preserve missing information rather than inventing years.

Distinguish required professional experience from preferred qualifications in
structured evaluation. Keep stretch opportunities visible with their skill and
experience gaps and explain the ranking. Resume selection must not change the
approved profile, discovery target roles, ingested job set, or deterministic scores.
Human review remains required; no autonomous applications or messaging are enabled.

## Existing behavior and limits

Greenhouse and Lever collectors take configured target roles and locations, not
resume selections. The current ranking function evaluates every stored job and
sorts by score, without a minimum-score rejection filter. Matching credits approved
skills independently of the experience score and reports detected experience gaps.
The approved profile includes technical skills and separate pharma/data years.

There is currently no multi-resume selection implementation or project-evidence
scoring layer. The approved target-role list does not explicitly include every
career title above. The existing substring filters accept those titles when
configured, but these tests do not establish that every title is currently searched.
The deterministic experience extractor also does not distinguish required from
preferred years; changing that behavior is outside this preservation-only scope.
These limitations remain future work, not reasons to narrow discovery by resume.

`tests/test_career_discovery.py` covers configured title breadth, both collectors
with mocked HTTP responses, stable discovery and scores across resume analyses,
unchanged approved profile, and retained data opportunities with skill credit and
explicit experience gaps. Future multi-resume work must extend these tests through
the actual selector once one exists, including selection after opportunity evaluation.

No ingestion, title-filter, matching-weight, profile, or search API changes are
introduced by Part F.

## Phase 7G.5B update

A standalone deterministic selector now exists in `src/ai/resume_selector.py`.
The earlier absence of selection describes the Part F baseline. It ranks resume
presentations only after opportunity evaluation; integration into the orchestrator
is future work. All supplied variants remain eligible, including data presentations
without professional data employment. Technical evidence earns credit without
turning training or projects into employment years. Conflicting claims are flagged,
not combined. Top ties and insufficient evidence produce no single recommendation.

Collector regression tests now invoke the selector after discovering and evaluating
synthetic opportunities, and verify unchanged discovery results, matching results,
and the approved profile. No selector output is used as a discovery filter. Existing
title-list coverage and deterministic-extractor limitations above remain unchanged.
See PHASE7_AGENTIC_AI.md for the independent point scheme and evidence limitations.
