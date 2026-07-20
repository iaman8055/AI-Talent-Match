import { z } from "zod";

// Mirrors apps/api/src/api/v1/companies/schemas.py UpdateCompanyRequest.
export const updateCompanySchema = z.object({
  name: z.string().min(1).max(200).optional(),
  match_threshold: z.number().min(0).max(100).optional(),
});

export type UpdateCompanyFormValues = z.infer<typeof updateCompanySchema>;

// Mirrors apps/api/src/api/v1/companies/schemas.py InviteMemberRequest.
export const inviteMemberSchema = z.object({
  email: z.email(),
  role: z.enum(["owner", "admin", "member"]),
});

export type InviteMemberFormValues = z.infer<typeof inviteMemberSchema>;
