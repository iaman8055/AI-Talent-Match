import { apiFetch } from "./client";
import type { JobResponse } from "./jobs";
import type { components } from "./schema";

// `has_pending_outreach_draft` was added to the backend response (Phase 7) after schema.d.ts was
// last generated — intersected here rather than regenerating, same rationale as lib/api-client/
// agent.ts. Regenerate schema.d.ts (`npm run generate:api-types`) once the API is running to fold
// this back in.
export type JobCandidateMatchResponse =
  components["schemas"]["JobCandidateMatchResponse"] & {
    has_pending_outreach_draft: boolean;
  };
// `job` is overridden with the patched JobResponse (see lib/api-client/jobs.ts) so the new
// source/external_* fields are visible here too, same regen note as above.
export type RecommendedJobResponse = Omit<
  components["schemas"]["RecommendedJobResponse"],
  "job"
> & { job: JobResponse };

// Not in schema.d.ts at all (added after the last generation) — defined by hand from the
// backend's JobSearchResultResponse (api/v1/matching/schemas.py). `match` is null when the
// background matching pipeline hasn't scored this job against the candidate yet.
export type JobSearchResultResponse = {
  job: JobResponse;
  match: components["schemas"]["MatchScoreDetail"] | null;
};

export async function listJobCandidates(
  jobId: string,
): Promise<JobCandidateMatchResponse[]> {
  return apiFetch<JobCandidateMatchResponse[]>(`/jobs/${jobId}/candidates`);
}

export async function listRecommendedJobs(): Promise<RecommendedJobResponse[]> {
  return apiFetch<RecommendedJobResponse[]>("/candidates/me/recommended-jobs");
}

export async function searchJobs(params: {
  q?: string;
  location?: string;
}): Promise<JobSearchResultResponse[]> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.location) search.set("location", params.location);
  const qs = search.toString();
  return apiFetch<JobSearchResultResponse[]>(
    `/candidates/me/jobs/search${qs ? `?${qs}` : ""}`,
  );
}

export async function getJobForCandidate(
  jobId: string,
): Promise<JobSearchResultResponse> {
  return apiFetch<JobSearchResultResponse>(`/candidates/me/jobs/${jobId}`);
}
