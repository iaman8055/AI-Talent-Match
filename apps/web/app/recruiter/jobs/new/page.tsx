"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useMyCompany } from "@/hooks/use-company";
import { useCreateJob } from "@/hooks/use-jobs";
import { ApiError } from "@/lib/api-client/client";
import {
  createJobSchema,
  type CreateJobFormValues,
} from "@/lib/validators/job";

export default function NewJobPage() {
  const router = useRouter();
  const { company } = useMyCompany();
  const createJob = useCreateJob();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateJobFormValues>({ resolver: zodResolver(createJobSchema) });

  const onSubmit = async (values: CreateJobFormValues) => {
    if (!company) {
      setServerError("No company found for your account.");
      return;
    }
    setServerError(null);
    try {
      const job = await createJob.mutateAsync({
        company_id: company.id,
        ...values,
      });
      router.push(`/recruiter/jobs/${job.id}`);
    } catch (error) {
      setServerError(
        error instanceof ApiError
          ? error.message
          : "Something went wrong. Please try again.",
      );
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold">New job</h1>
      <Card>
        <CardHeader>
          <CardTitle>Job details</CardTitle>
          <CardDescription>
            Paste the job description below — we&apos;ll parse it automatically
            and you can review or edit the extracted fields afterwards.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="title">Title</Label>
              <Input id="title" {...register("title")} />
              {errors.title && (
                <p className="text-sm text-destructive">
                  {errors.title.message}
                </p>
              )}
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="raw_description">Job description</Label>
              <Textarea
                id="raw_description"
                rows={12}
                {...register("raw_description")}
              />
              {errors.raw_description && (
                <p className="text-sm text-destructive">
                  {errors.raw_description.message}
                </p>
              )}
            </div>
            {serverError && (
              <p className="text-sm text-destructive">{serverError}</p>
            )}
            <Button type="submit" disabled={isSubmitting} className="w-fit">
              {isSubmitting ? "Creating…" : "Create job"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
