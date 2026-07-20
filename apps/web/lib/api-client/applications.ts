import { apiFetch } from "./client";
import type { components } from "./schema";

export type ApplicationResponse = components["schemas"]["ApplicationResponse"];
export type CandidateDetailResponse =
  components["schemas"]["CandidateDetailResponse"];
export type CandidateApplicationResponse =
  components["schemas"]["CandidateApplicationResponse"];
export type InviteCandidateRequest =
  components["schemas"]["InviteCandidateRequest"];
export type ApplyToJobRequest = components["schemas"]["ApplyToJobRequest"];

export async function getCandidateDetail(
  jobId: string,
  candidateId: string,
): Promise<CandidateDetailResponse> {
  return apiFetch<CandidateDetailResponse>(
    `/jobs/${jobId}/candidates/${candidateId}`,
  );
}

export async function inviteCandidate(
  jobId: string,
  body: InviteCandidateRequest,
): Promise<ApplicationResponse> {
  return apiFetch<ApplicationResponse>(`/jobs/${jobId}/invite`, {
    method: "POST",
    body,
  });
}

export async function listJobApplications(
  jobId: string,
): Promise<ApplicationResponse[]> {
  return apiFetch<ApplicationResponse[]>(`/jobs/${jobId}/applications`);
}

export async function applyToJob(
  body: ApplyToJobRequest,
): Promise<ApplicationResponse> {
  return apiFetch<ApplicationResponse>("/applications", {
    method: "POST",
    body,
  });
}

export async function listMyApplications(): Promise<
  CandidateApplicationResponse[]
> {
  return apiFetch<CandidateApplicationResponse[]>("/applications");
}

export async function screenApplication(
  applicationId: string,
): Promise<ApplicationResponse> {
  return apiFetch<ApplicationResponse>(
    `/applications/${applicationId}/screen`,
    { method: "POST" },
  );
}

export async function interviewApplication(
  applicationId: string,
): Promise<ApplicationResponse> {
  return apiFetch<ApplicationResponse>(
    `/applications/${applicationId}/interview`,
    { method: "POST" },
  );
}

export async function offerApplication(
  applicationId: string,
): Promise<ApplicationResponse> {
  return apiFetch<ApplicationResponse>(`/applications/${applicationId}/offer`, {
    method: "POST",
  });
}

export async function rejectApplication(
  applicationId: string,
): Promise<ApplicationResponse> {
  return apiFetch<ApplicationResponse>(
    `/applications/${applicationId}/reject`,
    { method: "POST" },
  );
}
