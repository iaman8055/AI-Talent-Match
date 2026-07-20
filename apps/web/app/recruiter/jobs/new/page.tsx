"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Loader2, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
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

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateJobFormValues>({ resolver: zodResolver(createJobSchema) });

  const onSubmit = async (values: CreateJobFormValues) => {
    if (!company) {
      toast.error("No company found for your account.");
      return;
    }
    try {
      const job = await createJob.mutateAsync({
        company_id: company.id,
        ...values,
      });
      toast.success("Job created — parsing in the background");
      router.push(`/recruiter/jobs/${job.id}`);
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Something went wrong. Please try again.",
      );
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/recruiter/jobs"
        className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        Back to jobs
      </Link>
      <PageHeader
        title="New job"
        description="Paste the job description — we'll extract the structured details automatically."
      />
      <Card className="max-w-2xl">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Sparkles className="size-4.5" />
            </div>
            <div>
              <CardTitle>Job details</CardTitle>
              <CardDescription>
                You can review or edit the extracted fields afterwards.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                placeholder="e.g. Senior Backend Engineer"
                {...register("title")}
              />
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
                placeholder="Paste the full job description here…"
                {...register("raw_description")}
              />
              {errors.raw_description && (
                <p className="text-sm text-destructive">
                  {errors.raw_description.message}
                </p>
              )}
            </div>
            <Button type="submit" disabled={isSubmitting} className="w-fit">
              {isSubmitting && <Loader2 className="animate-spin" />}
              {isSubmitting ? "Creating…" : "Create job"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
