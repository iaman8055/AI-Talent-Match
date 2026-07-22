import { apiFetch } from "./client";

// Hand-written to mirror apps/api/src/api/v1/agent/schemas.py — schema.d.ts is generated from a
// running API server (`npm run generate:api-types`), which this session never started per the
// project's standing "don't run servers after making changes" instruction. Once the API is up,
// regenerate schema.d.ts and these can be swapped for `components["schemas"][...]` like every
// other api-client file.

export type WorkMode = "remote" | "hybrid" | "onsite";

export interface AgentConfigResponse {
  id: string;
  candidate_id: string;
  auto_apply_enabled: boolean;
  target_roles: string[];
  target_skills: string[];
  target_locations: string[];
  work_modes: WorkMode[];
  min_salary: number | null;
  min_match_score: number;
  daily_apply_cap: number;
  created_at: string;
  updated_at: string;
}

export interface UpdateAgentConfigRequest {
  auto_apply_enabled?: boolean;
  target_roles?: string[];
  target_skills?: string[];
  target_locations?: string[];
  work_modes?: WorkMode[];
  min_salary?: number | null;
  min_match_score?: number;
  daily_apply_cap?: number;
}

export type AgentDecisionAction = "applied" | "skipped";

export interface AgentDecisionResponse {
  id: string;
  job_id: string;
  job_title: string;
  action: AgentDecisionAction;
  reason: string;
  decided_at: string;
}

export async function getMyAgentConfig(): Promise<AgentConfigResponse> {
  return apiFetch<AgentConfigResponse>("/candidates/me/agent-config");
}

export async function updateMyAgentConfig(
  body: UpdateAgentConfigRequest,
): Promise<AgentConfigResponse> {
  return apiFetch<AgentConfigResponse>("/candidates/me/agent-config", {
    method: "PUT",
    body,
  });
}

export async function listMyAgentDecisions(): Promise<AgentDecisionResponse[]> {
  return apiFetch<AgentDecisionResponse[]>("/candidates/me/agent-decisions");
}
