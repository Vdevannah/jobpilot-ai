# Mandatory resume privacy boundary

Never send original PDF files or unreviewed extracted resume text to an external
provider. Keep personal source documents and extracted text in ignored
`private_resumes/`; local previews belong in ignored `private_resume_previews/`.
Ignore rules are safeguards, not a substitute for reviewing staged files. Never
commit personal resumes, credentials, or unsanitized extracts anywhere else.

`preview_resume(text, identifiers=...)` runs locally. Supply every known full-name,
header/body name variant, city, and address identifier. The minimizer discards
headers before an allowed qualifications/skills/education/professional experience/
projects section, drops known identifying lines and detected contact or immigration
lines, and inserts exactly `Location: Delaware, USA`. Whole-line removal may remove
useful qualifications: review the minimized result locally rather than forwarding
raw text to recover them.

This is NOT a universal identity detector. Unknown city names, address forms,
unlabeled identifiers, and personal information embedded in narrative require
human review. Only job-relevant qualifications, skills, education, professional
experience, and projects may remain. Remove all citizenship, visa, immigration,
residency, sponsorship, and work-authorization details. If this cannot be verified,
do not approve. `approve_resume(..., confirmed=True)` is an explicit attestation
by the calling UI/operator, not an automatic sanitization result. It must never be
called automatically for personal content. Approval applies to the exact in-memory
text; ordinary strings and modified strings are blocked by OpenAIResumeClient.
The Python approval marker is an application boundary, not a security sandbox
against trusted code deliberately forging approvals.

The live sample scripts show a local-only preview and require typing APPROVE before
loading credentials or creating clients. These scripts accept only the repository's
synthetic sample; they are not personal PDF upload tools. The workflow script
obtains approval before either job or resume API requests. Programmatic callers
must preview and explicitly approve sanitized resume text themselves. Mock analysis
remains local. API errors omit content; known sensitive patterns in provider output
are blocked. Unknown identifiers or model-invented personal details cannot be
universally verified by pattern matching; reports still require local human review
before sharing. No logging of originals or credential values is added.

Tests use reserved placeholder identifiers and example.invalid, never real people
or contact details. No live API calls were performed during implementation.

## Local-only preview CLI (Phase 7G.5D)

From the project root, run:

```sh
.venv/bin/python scripts/preview_resume.py private_resumes/resume.txt --preview
```

Use `--help` for usage. Without `--preview`, the script reads nothing and displays
no resume content. Only UTF-8 `.txt` files are accepted; PDF, binary/control-character
input, decoding errors, and sanitizer failures produce generic errors without raw
content or paths. No OpenAI client, credentials, approval function, or network
operation is used. No output files or logs are created.

The CLI asks for known name, city, and address variants through hidden terminal
prompts (one per prompt, blank to finish). Do not put personal identifiers in shell
arguments. If hidden input is unavailable, preview fails closed. It reuses the
existing sanitizer and shows only its output, preceded by a privacy warning.
Candidate location is normalized to `Delaware, USA`; unidentified locations can
still survive automated filtering, so review and remove them locally. This is not
a guarantee of complete anonymization and does not grant external-analysis approval.
The existing strict boolean approval requirement is unchanged.

Use a private terminal without session recording, output redirection, or log capture:
terminal scrollback and externally configured recording are outside CLI control.
The script never prints the raw source, but missed identifiers may remain in the
sanitized preview. Only inspect content you are authorized to review locally.

## PDF section-heading repair (Phase 7G.5F)

`src/ai/resume_text_repair.py` adds a conservative, local, pure-text repair step
for a known PDF extraction artifact: section headings (e.g. "Technical Skills",
"Employment History") rendered merged onto the same line as their content,
which caused the sanitizer's exact-line section allowlist in this module to
never activate and silently drop the whole section. `repair_section_headings()`
recognizes a fixed list of common heading phrases (Professional Summary,
Summary of Skills, Technical Skills, Technical & Scientific Skills,
Professional Experience, Employment History, Education, Projects, Selected AI/
Data Science & Application Projects, Publications and Patents), maps the ones
with a safe existing equivalent onto this module's `skills`/`education`/
`professional experience`/`projects`/`qualifications` labels, and — only when
a merge is unambiguous (an explicit colon, or a no-space/ALL-CAPS PDF artifact
immediately followed by a new token) — splits the heading onto its own line.
It never invents, rewrites, or summarizes resume content; ambiguous merges and
headings with no safe existing category (Publications and Patents has none,
since publications/patents are neither employment, education, training, nor
an independent project) are left as local text and reported for manual review,
never guessed. This module does not change `SECTIONS`, `SENSITIVE`, or any
approval logic in this file.

`scripts/prepare_resume_pdfs.py` applies this repair to newly extracted PDF
text before writing it, and prints only generic category labels and counts
(never resume content) when manual review is recommended. The three private
text files already staged before this phase are not touched automatically;
rerun extraction with explicit approval to apply the repair to them:

```sh
.venv/bin/python scripts/prepare_resume_pdfs.py --overwrite
```

### One-time setup: local PDF source configuration

The script reads which three PDFs to extract from a local, git-ignored JSON
file at `private_resumes/pdf_sources.json` -- it is never hard-coded in
source, since real filenames or paths may themselves be identifying. Set it
up once:

```sh
mkdir -p private_resumes
cp config/pdf_sources.example.json private_resumes/pdf_sources.json
```

Then edit `private_resumes/pdf_sources.json` locally (it is covered by the
existing `private_resumes/` ignore rule, so it is never committed) to point
`pharma`, `data`, and `scientific_ai` at your three real local PDF paths,
for example:

```json
{
  "pharma": "~/Desktop/your_pharma_resume.pdf",
  "data": "~/Desktop/your_data_resume.pdf",
  "scientific_ai": "~/Desktop/your_scientific_ai_resume.pdf"
}
```

`config/pdf_sources.example.json` is the only tracked copy and contains
fictional placeholder paths only. The script never prints the configured
paths, the JSON file's contents, or PDF content -- only the fixed variant
names (`pharma`/`data`/`scientific_ai`) and generic status text appear in
its output, including in error messages for a missing, invalid, or
not-found configuration entry.

This re-reads the same three PDFs (no PDF content changes) and only replaces
`private_resumes/*.txt` because `--overwrite` was given explicitly; nothing
is sent anywhere, and no approval occurs. Preview and
review the result afterward exactly as before, with `scripts/preview_resume.py`.

## Publicly available professional information policy (Phase 7G.5G)

The candidate has clarified that publicly available professional information
is permitted and should not be stripped alongside personal/private data.
**Preserved** (including when it would otherwise match a removal
identifier): employer and university names; professional employment and
education locations; scientific accomplishments, degrees, and technical
qualifications; names appearing in published scientific articles and
patents, including coauthor names and the candidate's own name within a
citation. **Always removed, regardless of section**: personal name in resume
headers/contact sections, personal email and phone, home address and ZIP,
personal LinkedIn/GitHub profile URLs, and immigration/visa/citizenship/
residency/work-authorization status. The candidate's general location is
always represented only as `Delaware, USA`; this is unrelated to -- and does
not replace -- an employer's or university's own city/state, which is
preserved as written.

Mechanically, `src/ai/resume_privacy.py` now recognizes a sixth section,
`publications and patents` (mapped from headings like "Publications and
Patents" by `resume_text_repair.py`), and exempts `education`,
`professional experience`, and `publications and patents` from
identifier-substring removal -- the `SENSITIVE` contact/immigration pattern
removal and the header/contact structural check still apply there
unconditionally, and `skills`/`projects`/`qualifications` remain fully
identifier-sensitive as before. This is what resolves the earlier failure
mode where a personal city identifier (e.g. a hometown that coincides with a
PhD institution's city) could wipe out an entire Education or Experience
section down to nothing.

**Citations get an additional, separate gate for external use.** A
publication/patent citation combines the candidate's name with coauthors and
an exact title -- a stronger identifying fingerprint than structured skills/
education/experience facts -- so `approve_resume()` excludes the
`publications and patents` section from its output by default, even after
`confirmed=True`. Including it requires a second, explicit, separate
decision: `approve_resume(preview, confirmed=True, include_citations=True)`.
`require_approved_resume()` (the gate in front of `OpenAIResumeClient`) only
re-validates shape/safety on an already-approved `ApprovedResumeText`; it
never silently re-strips or re-adds citations, so whichever decision was
made at approval time is exactly what is sent. No live resume analysis was
performed to implement this: all tests use mocked SDK responses offline.
