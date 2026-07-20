import { apiFetch } from "./client";
import type { components } from "./schema";

export type JobResponse = components["schemas"]["JobResponse"];
export type CreateJobRequest = components["schemas"]["CreateJobRequest"];
export type UpdateJobRequest = components["schemas"]["UpdateJobRequest"];

export async function listJobs(companyId: string): Promise<JobResponse[]> {
  return apiFetch<JobResponse[]>(
    `/jobs?company_id=${encodeURIComponent(companyId)}`,
  );
}

export async function getJob(jobId: string): Promise<JobResponse> {
  return apiFetch<JobResponse>(`/jobs/${jobId}`);
}

export async function createJob(body: CreateJobRequest): Promise<JobResponse> {
  return apiFetch<JobResponse>("/jobs", { method: "POST", body });
}

export async function updateJob(
  jobId: string,
  body: UpdateJobRequest,
): Promise<JobResponse> {
  return apiFetch<JobResponse>(`/jobs/${jobId}`, { method: "PATCH", body });
}

export async function deleteJob(jobId: string): Promise<void> {
  return apiFetch<void>(`/jobs/${jobId}`, { method: "DELETE" });
}

export async function publishJob(jobId: string): Promise<JobResponse> {
  return apiFetch<JobResponse>(`/jobs/${jobId}/publish`, { method: "POST" });
}

export async function closeJob(jobId: string): Promise<JobResponse> {
  return apiFetch<JobResponse>(`/jobs/${jobId}/close`, { method: "POST" });
}

export async function reopenJob(jobId: string): Promise<JobResponse> {
  return apiFetch<JobResponse>(`/jobs/${jobId}/reopen`, { method: "POST" });
}
