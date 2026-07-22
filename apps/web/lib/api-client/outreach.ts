import { apiFetch } from "./client";

// Hand-written to mirror apps/api/src/api/v1/outreach/schemas.py — same rationale as
// lib/api-client/agent.ts (no server was started this session to regenerate schema.d.ts).

export type OutreachDraftStatus = "draft" | "sent" | "discarded";

export interface OutreachDraftResponse {
  id: string;
  candidate_id: string;
  candidate_name: string;
  job_id: string;
  job_title: string;
  candidate_summary: string;
  subject: string;
  body: string;
  status: OutreachDraftStatus;
  sent_at: string | null;
  created_at: string;
}

export interface UpdateOutreachDraftRequest {
  subject?: string;
  body?: string;
}

export async function listOutreachDrafts(
  jobId?: string,
): Promise<OutreachDraftResponse[]> {
  const query = jobId ? `?job_id=${jobId}` : "";
  return apiFetch<OutreachDraftResponse[]>(`/outreach-drafts${query}`);
}

export async function updateOutreachDraft(
  draftId: string,
  body: UpdateOutreachDraftRequest,
): Promise<OutreachDraftResponse> {
  return apiFetch<OutreachDraftResponse>(`/outreach-drafts/${draftId}`, {
    method: "PATCH",
    body,
  });
}

export async function sendOutreachDraft(
  draftId: string,
): Promise<OutreachDraftResponse> {
  return apiFetch<OutreachDraftResponse>(`/outreach-drafts/${draftId}/send`, {
    method: "POST",
  });
}

export async function discardOutreachDraft(
  draftId: string,
): Promise<OutreachDraftResponse> {
  return apiFetch<OutreachDraftResponse>(
    `/outreach-drafts/${draftId}/discard`,
    { method: "POST" },
  );
}
