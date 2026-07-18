import { z } from "zod";

// Mirrors apps/api/src/api/v1/candidates/schemas.py UpdateProfileRequest.
export const updateProfileSchema = z.object({
  full_name: z.string().max(200).optional(),
  headline: z.string().max(300).optional(),
  summary: z.string().max(4000).optional(),
  skills: z.array(z.string()).optional(),
  total_experience_years: z.number().min(0).max(80).optional(),
  location: z
    .object({
      country: z.string().optional(),
      region: z.string().optional(),
      city: z.string().optional(),
    })
    .optional(),
  desired_salary_min: z.number().min(0).optional(),
  desired_salary_max: z.number().min(0).optional(),
  work_mode_preference: z.enum(["remote", "hybrid", "onsite"]).optional(),
});

export type UpdateProfileFormValues = z.infer<typeof updateProfileSchema>;
