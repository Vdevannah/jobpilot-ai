import { isDemoRecord } from "./demoRecord";

// Whether a "View Original Posting" (or equivalent external) link should
// be shown for a job at all.
//
// Two independent reasons to hide it:
// 1. Demo-seeded records (Acme/Test Company/Demo Company, detected by
//    isDemoRecord -- never by company name) point at the placeholder
//    https://example.com domain. That page doesn't exist for this job, so
//    the link would always be a dead end.
// 2. Even for a genuine job, a non-empty `url` string isn't proof of a
//    real destination -- it must actually parse as an absolute http(s)
//    URL, which is the normal shape for every Greenhouse/Lever-collected
//    posting.
//
// This never invents or guesses a replacement URL; it only decides
// whether to show the one already on the record.
export function shouldShowPostingLink(job) {
  if (isDemoRecord(job)) return false;
  if (typeof job?.url !== "string" || job.url.trim() === "") return false;
  try {
    const parsed = new URL(job.url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}
