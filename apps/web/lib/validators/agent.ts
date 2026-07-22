import { z } from "zod";

// Mirrors apps/api/src/api/v1/agent/schemas.py UpdateAgentConfigRequest.
export const updateAgentConfigSchema = z.object({
  auto_apply_enabled: z.boolean(),
  target_roles: z.array(z.string()),
  target_skills: z.array(z.string()),
  target_locations: z.array(z.string()),
  work_modes: z.array(z.enum(["remote", "hybrid", "onsite"])),
  min_salary: z.number().min(0).optional(),
  min_match_score: z.number().min(0).max(100),
  daily_apply_cap: z.number().min(1).max(100),
});

export type UpdateAgentConfigFormValues = z.infer<
  typeof updateAgentConfigSchema
>;
