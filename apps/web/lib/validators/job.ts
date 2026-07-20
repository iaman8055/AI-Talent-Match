import { z } from "zod";

// Mirrors apps/api/src/api/v1/jobs/schemas.py CreateJobRequest.
export const createJobSchema = z.object({
  title: z.string().min(1).max(200),
  raw_description: z.string().min(1).max(20000),
});

export type CreateJobFormValues = z.infer<typeof createJobSchema>;

// Mirrors apps/api/src/api/v1/jobs/schemas.py UpdateJobRequest.
export const updateJobSchema = z.object({
  title: z.string().min(1).max(200).optional(),
  raw_description: z.string().min(1).max(20000).optional(),
  summary: z.string().max(4000).optional(),
  required_skills: z.array(z.string()).optional(),
  nice_to_have_skills: z.array(z.string()).optional(),
  responsibilities: z.array(z.string()).optional(),
  qualifications: z.array(z.string()).optional(),
  min_experience_years: z.number().min(0).max(80).optional(),
  employment_type: z.string().max(50).optional(),
  work_mode: z.enum(["remote", "hybrid", "onsite"]).optional(),
  location: z
    .object({
      country: z.string().optional(),
      region: z.string().optional(),
      city: z.string().optional(),
    })
    .optional(),
  salary_min: z.number().min(0).optional(),
  salary_max: z.number().min(0).optional(),
});

export type UpdateJobFormValues = z.infer<typeof updateJobSchema>;
