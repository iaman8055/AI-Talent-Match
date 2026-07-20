"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { Badge } from "@/components/ui/badge";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  useCandidateDetail,
  useInviteCandidate,
  useJobApplications,
} from "@/hooks/use-applications";
import {
  useCloseJob,
  useDeleteJob,
  useJob,
  usePublishJob,
  useReopenJob,
  useUpdateJob,
} from "@/hooks/use-jobs";
import { useJobCandidates } from "@/hooks/use-matching";
import { ApiError } from "@/lib/api-client/client";
import type { ApplicationResponse } from "@/lib/api-client/applications";
import type { JobCandidateMatchResponse } from "@/lib/api-client/matching";
import {
  updateJobSchema,
  type UpdateJobFormValues,
} from "@/lib/validators/job";

const LIFECYCLE_VARIANT: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  draft: "outline",
  published: "default",
  closed: "destructive",
};

const PROCESSING_VARIANT: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  pending: "secondary",
  parsing: "secondary",
  parsed: "secondary",
  embedding: "secondary",
  ready: "default",
  failed: "destructive",
};

const APPLICATION_STATUS_VARIANT: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  sourced: "outline",
  invited: "secondary",
  applied: "secondary",
  screening: "secondary",
  interview: "secondary",
  offer: "default",
  rejected: "destructive",
};

function listToText(values: string[] | undefined): string {
  return (values ?? []).join(", ");
}

function textToList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function CandidateRow({
  jobId,
  entry,
}: {
  jobId: string;
  entry: JobCandidateMatchResponse;
}) {
  const inviteCandidate = useInviteCandidate(jobId);
  const [error, setError] = useState<string | null>(null);

  const onInvite = async () => {
    setError(null);
    try {
      await inviteCandidate.mutateAsync({ candidate_id: entry.candidate.id });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not invite. Please try again.",
      );
    }
  };

  return (
    <div className="flex flex-col gap-1 rounded-lg border p-3 text-sm">
      <div className="flex items-center justify-between gap-3">
        <Link
          href={`/recruiter/jobs/${jobId}/candidates/${entry.candidate.id}`}
          className="font-medium hover:underline"
        >
          {entry.candidate.full_name ?? "Unnamed candidate"}
        </Link>
        <div className="flex items-center gap-2">
          <Badge>{Math.round(entry.match.overall_score)}% match</Badge>
          <Button
            size="sm"
            variant="outline"
            disabled={inviteCandidate.isPending}
            onClick={onInvite}
          >
            {inviteCandidate.isPending ? "Inviting…" : "Invite"}
          </Button>
        </div>
      </div>
      {error && <p className="text-destructive">{error}</p>}
    </div>
  );
}

function ApplicationRow({
  jobId,
  application,
}: {
  jobId: string;
  application: ApplicationResponse;
}) {
  const { data: detail } = useCandidateDetail(jobId, application.candidate_id);

  return (
    <Link
      href={`/recruiter/jobs/${jobId}/candidates/${application.candidate_id}`}
      className="flex items-center justify-between rounded-lg border p-3 text-sm hover:bg-muted"
    >
      <span className="font-medium">
        {detail?.candidate.full_name ?? "Loading…"}
      </span>
      <Badge
        variant={APPLICATION_STATUS_VARIANT[application.status] ?? "outline"}
      >
        {application.status}
      </Badge>
    </Link>
  );
}

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const router = useRouter();

  const { data: job, isLoading: jobLoading } = useJob(jobId);
  const updateJob = useUpdateJob(jobId);
  const publishJob = usePublishJob(jobId);
  const closeJob = useCloseJob(jobId);
  const reopenJob = useReopenJob(jobId);
  const deleteJob = useDeleteJob();
  const { data: candidates, isLoading: candidatesLoading } =
    useJobCandidates(jobId);
  const { data: applications, isLoading: applicationsLoading } =
    useJobApplications(jobId);

  const [lifecycleError, setLifecycleError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    control,
    formState: { isSubmitting },
  } = useForm<UpdateJobFormValues>({ resolver: zodResolver(updateJobSchema) });

  useEffect(() => {
    if (!job) return;
    reset({
      title: job.title,
      raw_description: job.raw_description,
      summary: job.summary ?? "",
      required_skills: job.required_skills,
      nice_to_have_skills: job.nice_to_have_skills,
      responsibilities: job.responsibilities,
      qualifications: job.qualifications,
      min_experience_years: job.min_experience_years ?? undefined,
      employment_type: job.employment_type ?? "",
      work_mode: job.work_mode ?? undefined,
      location: {
        country: job.location.country ?? "",
        region: job.location.region ?? "",
        city: job.location.city ?? "",
      },
      salary_min: job.salary_min ?? undefined,
      salary_max: job.salary_max ?? undefined,
    });
  }, [job, reset]);

  const onSubmit = async (values: UpdateJobFormValues) => {
    await updateJob.mutateAsync(values);
  };

  const runLifecycleAction = async (action: () => Promise<unknown>) => {
    setLifecycleError(null);
    try {
      await action();
    } catch (err) {
      setLifecycleError(
        err instanceof ApiError
          ? err.message
          : "Action failed. Please try again.",
      );
    }
  };

  const onDelete = async () => {
    if (!job) return;
    await runLifecycleAction(async () => {
      await deleteJob.mutateAsync({ jobId: job.id, companyId: job.company_id });
      router.push("/recruiter/jobs");
    });
  };

  if (jobLoading || !job) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading job…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">{job.title}</h1>
        <div className="flex items-center gap-2">
          <Badge variant={LIFECYCLE_VARIANT[job.lifecycle_status] ?? "outline"}>
            {job.lifecycle_status}
          </Badge>
          <Badge
            variant={PROCESSING_VARIANT[job.processing_status] ?? "outline"}
          >
            {job.processing_status}
          </Badge>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lifecycle</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            {job.lifecycle_status === "draft" && (
              <>
                <Button
                  variant="outline"
                  disabled={
                    job.processing_status !== "ready" || publishJob.isPending
                  }
                  onClick={() =>
                    runLifecycleAction(() => publishJob.mutateAsync())
                  }
                >
                  Publish
                </Button>
                <Button
                  variant="destructive"
                  disabled={deleteJob.isPending}
                  onClick={onDelete}
                >
                  Delete
                </Button>
              </>
            )}
            {job.lifecycle_status === "published" && (
              <Button
                variant="outline"
                disabled={closeJob.isPending}
                onClick={() => runLifecycleAction(() => closeJob.mutateAsync())}
              >
                Close
              </Button>
            )}
            {job.lifecycle_status === "closed" && (
              <Button
                variant="outline"
                disabled={reopenJob.isPending}
                onClick={() =>
                  runLifecycleAction(() => reopenJob.mutateAsync())
                }
              >
                Reopen
              </Button>
            )}
          </div>
          {job.lifecycle_status === "draft" &&
            job.processing_status !== "ready" && (
              <p className="text-sm text-muted-foreground">
                Waiting for the job description to finish parsing before it can
                be published.
              </p>
            )}
          {lifecycleError && (
            <p className="text-sm text-destructive">{lifecycleError}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Job details</CardTitle>
          <CardDescription>
            These fields are extracted from the job description automatically,
            and you can edit any of them at any time.
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
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="raw_description">Job description</Label>
              <Textarea
                id="raw_description"
                rows={8}
                {...register("raw_description")}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="summary">Summary</Label>
              <Textarea id="summary" rows={3} {...register("summary")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="required_skills">
                Required skills (comma-separated)
              </Label>
              <Input
                id="required_skills"
                defaultValue={listToText(job.required_skills)}
                onChange={(event) =>
                  setValue("required_skills", textToList(event.target.value), {
                    shouldDirty: true,
                  })
                }
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="nice_to_have_skills">
                Nice-to-have skills (comma-separated)
              </Label>
              <Input
                id="nice_to_have_skills"
                defaultValue={listToText(job.nice_to_have_skills)}
                onChange={(event) =>
                  setValue(
                    "nice_to_have_skills",
                    textToList(event.target.value),
                    { shouldDirty: true },
                  )
                }
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="responsibilities">
                Responsibilities (comma-separated)
              </Label>
              <Input
                id="responsibilities"
                defaultValue={listToText(job.responsibilities)}
                onChange={(event) =>
                  setValue("responsibilities", textToList(event.target.value), {
                    shouldDirty: true,
                  })
                }
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="qualifications">
                Qualifications (comma-separated)
              </Label>
              <Input
                id="qualifications"
                defaultValue={listToText(job.qualifications)}
                onChange={(event) =>
                  setValue("qualifications", textToList(event.target.value), {
                    shouldDirty: true,
                  })
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="min_experience_years">
                  Min. experience (years)
                </Label>
                <Input
                  id="min_experience_years"
                  type="number"
                  step="0.5"
                  {...register("min_experience_years", { valueAsNumber: true })}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="employment_type">Employment type</Label>
                <Input id="employment_type" {...register("employment_type")} />
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="work_mode">Work mode</Label>
              <Controller
                control={control}
                name="work_mode"
                render={({ field }) => (
                  <Select
                    value={field.value ?? null}
                    onValueChange={(value) =>
                      field.onChange(value ?? undefined)
                    }
                  >
                    <SelectTrigger id="work_mode">
                      <SelectValue placeholder="Select work mode" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="remote">Remote</SelectItem>
                      <SelectItem value="hybrid">Hybrid</SelectItem>
                      <SelectItem value="onsite">Onsite</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="location.city">City</Label>
                <Input id="location.city" {...register("location.city")} />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="location.region">Region</Label>
                <Input id="location.region" {...register("location.region")} />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="location.country">Country</Label>
                <Input
                  id="location.country"
                  {...register("location.country")}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="salary_min">Salary min</Label>
                <Input
                  id="salary_min"
                  type="number"
                  {...register("salary_min", { valueAsNumber: true })}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="salary_max">Salary max</Label>
                <Input
                  id="salary_max"
                  type="number"
                  {...register("salary_max", { valueAsNumber: true })}
                />
              </div>
            </div>
            {updateJob.isError && (
              <p className="text-sm text-destructive">
                Could not save changes. Please try again.
              </p>
            )}
            <Button type="submit" disabled={isSubmitting} className="w-fit">
              {isSubmitting ? "Saving…" : "Save changes"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ranked candidates</CardTitle>
          <CardDescription>
            Candidates whose match score clears your company&apos;s threshold,
            highest first.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {job.processing_status !== "ready" && (
            <p className="text-sm text-muted-foreground">
              Matching hasn&apos;t run yet — it starts automatically once the
              job finishes parsing.
            </p>
          )}
          {job.processing_status === "ready" && candidatesLoading && (
            <p className="text-sm text-muted-foreground">Loading candidates…</p>
          )}
          {job.processing_status === "ready" &&
            !candidatesLoading &&
            (candidates ?? []).length === 0 && (
              <p className="text-sm text-muted-foreground">
                No candidates above your match threshold yet.
              </p>
            )}
          {(candidates ?? []).map((entry) => (
            <CandidateRow
              key={entry.candidate.id}
              jobId={jobId}
              entry={entry}
            />
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Applications</CardTitle>
          <CardDescription>
            Everyone invited or who has applied to this job.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {applicationsLoading && (
            <p className="text-sm text-muted-foreground">
              Loading applications…
            </p>
          )}
          {!applicationsLoading && (applications ?? []).length === 0 && (
            <p className="text-sm text-muted-foreground">
              No applications yet.
            </p>
          )}
          {(applications ?? []).map((application) => (
            <ApplicationRow
              key={application.id}
              jobId={jobId}
              application={application}
            />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
