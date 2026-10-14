// Reusable fetch wrapper for the JobPilot AI FastAPI backend.
//
// Base URL comes from VITE_API_BASE_URL (set in frontend/.env, see
// .env.example), defaulting to http://localhost:8000 for local development.
// Every call surfaces HTTP and network failures as a single ApiError so
// callers can render one consistent error state.

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, { status = null, cause = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.cause = cause;
  }
}

function buildQueryString(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params || {})) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

async function request(path, { params, method = "GET", body } = {}) {
  const url = `${API_BASE_URL}${path}${buildQueryString(params)}`;

  let response;
  try {
    response = await fetch(url, {
      method,
      headers: body !== undefined
        ? { Accept: "application/json", "Content-Type": "application/json" }
        : { Accept: "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    throw new ApiError(
      `Could not reach the JobPilot AI backend at ${API_BASE_URL}.`,
      { cause },
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body?.detail ? JSON.stringify(body.detail) : detail;
    } catch {
      // Response body wasn't JSON; fall back to statusText.
    }
    throw new ApiError(`Request to ${path} failed (${response.status}): ${detail}`, {
      status: response.status,
    });
  }

  return response.json();
}

export function getHealth() {
  return request("/health");
}

export function getJobs(params = {}) {
  return request("/jobs", { params });
}

export function getMatches(params = {}) {
  return request("/matches", { params });
}

export function getJobById(jobId) {
  return request(`/jobs/${encodeURIComponent(jobId)}`);
}

// Phase 8E mock-only endpoints: fixed sample AI output for demonstration,
// never a live OpenAI call and never real resume text. Each call is a
// distinct, explicit request -- callers must trigger these themselves, not
// as a side effect of loading a page.
export function getResumeRecommendation(jobId) {
  return request(`/jobs/${encodeURIComponent(jobId)}/resume-recommendation`);
}

export function getAIReview(jobId) {
  return request(`/jobs/${encodeURIComponent(jobId)}/ai-review`);
}

// Phase 9A/9B: deterministic (non-AI) analysis of the job's own stored
// description. Unlike the Phase 8E mock endpoints above, these never read
// or process any resume text, so there is no privacy reason to make them
// explicit/lazy -- callers may fetch them automatically when a job is
// selected, the same way getJobById() already is.
export function getJobRequirements(jobId) {
  return request(`/jobs/${encodeURIComponent(jobId)}/requirements`);
}

export function getJobRequirementComparison(jobId) {
  return request(`/jobs/${encodeURIComponent(jobId)}/requirement-comparison`);
}

// Phase 9C: personalized analysis against the caller's OWN resume text.
// Every call here is explicit and user-triggered (via useLazyRequest in the
// pages below) -- none of these run automatically on page load or when
// switching jobs, and the raw resume text is never sent anywhere except in
// the one /resume/preview call the caller makes directly.

export function previewResumeText(resumeText, identifiers = []) {
  return request("/resume/preview", {
    method: "POST",
    body: { resume_text: resumeText, identifiers },
  });
}

export function getPersonalizedAnalysis(jobId, { previewText, confirmed, variant, mode, includeCitations = false }) {
  return request(`/jobs/${encodeURIComponent(jobId)}/personalized-analysis`, {
    method: "POST",
    body: {
      preview_text: previewText, confirmed, variant, mode,
      include_citations: includeCitations,
    },
  });
}

export function getApplicationAssistance(jobId, { previewText, confirmed, variant, mode, includeCitations = false }) {
  return request(`/jobs/${encodeURIComponent(jobId)}/application-assistance`, {
    method: "POST",
    body: {
      preview_text: previewText, confirmed, variant, mode,
      include_citations: includeCitations,
    },
  });
}
