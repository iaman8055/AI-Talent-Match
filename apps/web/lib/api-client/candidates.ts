import { apiFetch } from "./client";
import type { components } from "./schema";

export type CandidateResponse = components["schemas"]["CandidateResponse"];
export type UpdateProfileRequest =
  components["schemas"]["UpdateProfileRequest"];
export type ResumeResponse = components["schemas"]["ResumeResponse"];
export type DownloadUrlResponse = components["schemas"]["DownloadUrlResponse"];

export async function getMyProfile(): Promise<CandidateResponse> {
  return apiFetch<CandidateResponse>("/candidates/me");
}

export async function updateMyProfile(
  body: UpdateProfileRequest,
): Promise<CandidateResponse> {
  return apiFetch<CandidateResponse>("/candidates/me/profile", {
    method: "PATCH",
    body,
  });
}

export async function listMyResumes(): Promise<ResumeResponse[]> {
  return apiFetch<ResumeResponse[]>("/candidates/me/resume");
}

export async function getMyResume(resumeId: string): Promise<ResumeResponse> {
  return apiFetch<ResumeResponse>(`/candidates/me/resume/${resumeId}`);
}

export async function uploadResume(file: File): Promise<ResumeResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<ResumeResponse>("/candidates/me/resume", {
    method: "POST",
    formData,
  });
}

export async function getResumeDownloadUrl(
  resumeId: string,
): Promise<DownloadUrlResponse> {
  return apiFetch<DownloadUrlResponse>(
    `/candidates/me/resume/${resumeId}/download-url`,
  );
}
