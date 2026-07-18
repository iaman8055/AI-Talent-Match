import { z } from "zod";

// Mirrors apps/api/src/api/v1/auth/schemas.py — keep in sync by hand (small surface, not
// worth codegen for validation rules specifically; schema.d.ts already covers shape/types).
export const registerSchema = z
  .object({
    email: z.email(),
    password: z.string().min(8, "Password must be at least 8 characters"),
    role: z.enum(["candidate", "recruiter"]),
    full_name: z.string().min(1).max(200),
    company_name: z.string().min(1).max(200).optional(),
  })
  .refine((data) => data.role !== "recruiter" || !!data.company_name, {
    message: "Company name is required when registering as a recruiter",
    path: ["company_name"],
  });

export type RegisterFormValues = z.infer<typeof registerSchema>;

export const loginSchema = z.object({
  email: z.email(),
  password: z.string().min(1, "Password is required"),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
