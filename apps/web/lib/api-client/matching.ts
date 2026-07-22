import { apiFetch } from "./client";
import type { components } from "./schema";

// `has_pending_outreach_draft` was added to the backend response (Phase 7) after schema.d.ts was
// last generated — intersected here rather than regenerating, same rationale as lib/api-client/
// agent.ts. Regenerate schema.d.ts (`npm run generate:api-types`) once the API is running to fold
// this back in.
export type JobCandidateMatchResponse =
  components["schemas"]["JobCandidateMatchResponse"] & {
    has_pending_outreach_draft: boolean;
  };
export type RecommendedJobResponse =
  components["schemas"]["RecommendedJobResponse"];

export async function listJobCandidates(
  jobId: string,
): Promise<JobCandidateMatchResponse[]> {
  return apiFetch<JobCandidateMatchResponse[]>(`/jobs/${jobId}/candidates`);
}

export async function listRecommendedJobs(): Promise<RecommendedJobResponse[]> {
  return apiFetch<RecommendedJobResponse[]>("/candidates/me/recommended-jobs");
}
