"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowLeft,
  CheckCircle2,
  Loader2,
  RotateCcw,
  Save,
  Trash2,
  Users,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import { EmptyState } from "@/components/dashboard/empty-state";
import { MatchScore } from "@/components/dashboard/match-score";
import { PageHeader } from "@/components/dashboard/page-header";
import { PipelineBadgeCompact } from "@/components/dashboard/pipeline-stepper";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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

  const onInvite = async () => {
    try {
      await inviteCandidate.mutateAsync({ candidate_id: entry.candidate.id });
      toast.success(`Invited ${entry.candidate.full_name ?? "candidate"}`);
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.message
          : "Could not invite. Please try again.",
      );
    }
  };

  return (
    <TableRow>
      <TableCell className="font-medium">
        <Link
          href={`/recruiter/jobs/${jobId}/candidates/${entry.candidate.id}`}
          className="hover:underline"
        >
          {entry.candidate.full_name ?? "Unnamed candidate"}
        </Link>
        {entry.candidate.headline && (
          <p className="text-xs font-normal text-muted-foreground">
            {entry.candidate.headline}
          </p>
        )}
      </TableCell>
      <TableCell>
        <MatchScore score={entry.match.overall_score} />
      </TableCell>
      <TableCell className="text-right">
        <Button
          size="sm"
          variant="outline"
          disabled={inviteCandidate.isPending}
          onClick={onInvite}
        >
          {inviteCandidate.isPending ? "Inviting…" : "Invite"}
        </Button>
      </TableCell>
    </TableRow>
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
    <TableRow>
      <TableCell className="font-medium">
        <Link
          href={`/recruiter/jobs/${jobId}/candidates/${application.candidate_id}`}
          className="hover:underline"
        >
          {detail?.candidate.full_name ?? "…"}
        </Link>
      </TableCell>
      <TableCell>
        <PipelineBadgeCompact status={application.status} />
      </TableCell>
      <TableCell className="text-right">
        <Link
          href={`/recruiter/jobs/${jobId}/candidates/${application.candidate_id}`}
          className="text-sm text-muted-foreground hover:text-foreground hover:underline"
        >
          View
        </Link>
      </TableCell>
    </TableRow>
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

  const [deleting, setDeleting] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    control,
    formState: { isSubmitting, isDirty },
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
    try {
      await updateJob.mutateAsync(values);
      toast.success("Job updated");
    } catch {
      toast.error("Could not save changes. Please try again.");
    }
  };

  const runLifecycleAction = async (
    action: () => Promise<unknown>,
    message: string,
  ) => {
    try {
      await action();
      toast.success(message);
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.message
          : "Action failed. Please try again.",
      );
    }
  };

  const onDelete = async () => {
    if (!job) return;
    setDeleting(true);
    try {
      await deleteJob.mutateAsync({ jobId: job.id, companyId: job.company_id });
      toast.success("Job deleted");
      router.push("/recruiter/jobs");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Could not delete this job.",
      );
      setDeleting(false);
    }
  };

  if (jobLoading || !job) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

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
        title={job.title}
        description={
          job.lifecycle_status === "draft" && job.processing_status !== "ready"
            ? "Waiting for the job description to finish parsing before it can be published."
            : undefined
        }
        actions={
          <>
            <Badge
              variant={LIFECYCLE_VARIANT[job.lifecycle_status] ?? "outline"}
            >
              {job.lifecycle_status}
            </Badge>
            <Badge
              variant={PROCESSING_VARIANT[job.processing_status] ?? "outline"}
            >
              {job.processing_status}
            </Badge>
            {job.lifecycle_status === "draft" && (
              <>
                <Button
                  size="sm"
                  disabled={
                    job.processing_status !== "ready" || publishJob.isPending
                  }
                  onClick={() =>
                    runLifecycleAction(
                      () => publishJob.mutateAsync(),
                      "Job published",
                    )
                  }
                >
                  <CheckCircle2 />
                  Publish
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={deleting}
                  onClick={onDelete}
                >
                  {deleting ? <Loader2 className="animate-spin" /> : <Trash2 />}
                  Delete
                </Button>
              </>
            )}
            {job.lifecycle_status === "published" && (
              <Button
                size="sm"
                variant="outline"
                disabled={closeJob.isPending}
                onClick={() =>
                  runLifecycleAction(() => closeJob.mutateAsync(), "Job closed")
                }
              >
                <XCircle />
                Close
              </Button>
            )}
            {job.lifecycle_status === "closed" && (
              <Button
                size="sm"
                variant="outline"
                disabled={reopenJob.isPending}
                onClick={() =>
                  runLifecycleAction(
                    () => reopenJob.mutateAsync(),
                    "Job reopened",
                  )
                }
              >
                <RotateCcw />
                Reopen
              </Button>
            )}
          </>
        }
      />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="candidates">
            Candidates
            {(candidates ?? []).length > 0 && (
              <Badge variant="secondary" className="ml-1">
                {candidates?.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="applications">
            Applications
            {(applications ?? []).length > 0 && (
              <Badge variant="secondary" className="ml-1">
                {applications?.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle>Job details</CardTitle>
              <CardDescription>
                These fields are extracted from the job description
                automatically, and you can edit any of them at any time.
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
                      setValue(
                        "required_skills",
                        textToList(event.target.value),
                        {
                          shouldDirty: true,
                        },
                      )
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
                      setValue(
                        "responsibilities",
                        textToList(event.target.value),
                        { shouldDirty: true },
                      )
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
                      setValue(
                        "qualifications",
                        textToList(event.target.value),
                        {
                          shouldDirty: true,
                        },
                      )
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
                      {...register("min_experience_years", {
                        valueAsNumber: true,
                      })}
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="employment_type">Employment type</Label>
                    <Input
                      id="employment_type"
                      {...register("employment_type")}
                    />
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
                        <SelectTrigger id="work_mode" className="w-full">
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
                    <Input
                      id="location.region"
                      {...register("location.region")}
                    />
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
                <Button
                  type="submit"
                  disabled={isSubmitting || !isDirty}
                  className="w-fit"
                >
                  {isSubmitting ? (
                    <Loader2 className="animate-spin" />
                  ) : (
                    <Save />
                  )}
                  {isSubmitting ? "Saving…" : "Save changes"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="candidates" className="mt-4">
          {job.processing_status !== "ready" && (
            <EmptyState
              icon={Users}
              title="Matching hasn't run yet"
              description="It starts automatically once the job finishes parsing."
            />
          )}
          {job.processing_status === "ready" && candidatesLoading && (
            <Skeleton className="h-48 w-full" />
          )}
          {job.processing_status === "ready" &&
            !candidatesLoading &&
            (candidates ?? []).length === 0 && (
              <EmptyState
                icon={Users}
                title="No candidates yet"
                description="No candidates clear your company's match threshold yet."
              />
            )}
          {job.processing_status === "ready" &&
            !candidatesLoading &&
            (candidates ?? []).length > 0 && (
              <Card>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Candidate</TableHead>
                        <TableHead>Match</TableHead>
                        <TableHead className="text-right">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(candidates ?? []).map((entry) => (
                        <CandidateRow
                          key={entry.candidate.id}
                          jobId={jobId}
                          entry={entry}
                        />
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            )}
        </TabsContent>

        <TabsContent value="applications" className="mt-4">
          {applicationsLoading && <Skeleton className="h-48 w-full" />}
          {!applicationsLoading && (applications ?? []).length === 0 && (
            <EmptyState
              icon={Users}
              title="No applications yet"
              description="Invite a candidate or wait for one to apply."
            />
          )}
          {!applicationsLoading && (applications ?? []).length > 0 && (
            <Card>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Candidate</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(applications ?? []).map((application) => (
                      <ApplicationRow
                        key={application.id}
                        jobId={jobId}
                        application={application}
                      />
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
