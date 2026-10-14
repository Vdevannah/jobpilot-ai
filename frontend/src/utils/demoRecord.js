// Identifies demo/sample job records already present in the local
// development database (company names like "Acme", "Test Company", "Demo
// Company") vs. genuinely collected postings. This is never inferred from
// the company name -- it checks the job's URL, since every demo record
// seeded during development points at https://example.com/... (the
// IANA-reserved example domain, RFC 2606), while every genuine record
// collected by the Greenhouse/Lever pipelines points at that employer's own
// careers site. A real employer could coincidentally be named "Acme"; this
// check does not assume otherwise.
const DEMO_HOSTNAMES = new Set(["example.com", "www.example.com"]);

export function isDemoRecord(job) {
  if (!job?.url) return false;
  try {
    return DEMO_HOSTNAMES.has(new URL(job.url).hostname);
  } catch {
    return false;
  }
}
