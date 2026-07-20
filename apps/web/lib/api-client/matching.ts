import { apiFetch } from "./client";
import type { components } from "./schema";

export type JobCandidateMatchResponse =
  components["schemas"]["JobCandidateMatchResponse"];
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
