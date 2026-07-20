"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { useMyCompany } from "@/hooks/use-company";
import {
  useCloseJob,
  useDeleteJob,
  useJobs,
  usePublishJob,
  useReopenJob,
} from "@/hooks/use-jobs";
import { ApiError } from "@/lib/api-client/client";
import type { JobResponse } from "@/lib/api-client/jobs";

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

function JobRow({ job, companyId }: { job: JobResponse; companyId: string }) {
  const publishJob = usePublishJob(job.id);
  const closeJob = useCloseJob(job.id);
  const reopenJob = useReopenJob(job.id);
  const deleteJob = useDeleteJob();
  const [error, setError] = useState<string | null>(null);

  const runAction = async (action: () => Promise<unknown>) => {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Action failed. Please try again.",
      );
    }
  };

  return (
    <div className="flex flex-col gap-2 rounded-lg border p-3 text-sm">
      <div className="flex items-center justify-between gap-3">
        <Link
          href={`/recruiter/jobs/${job.id}`}
          className="font-medium hover:underline"
        >
          {job.title}
        </Link>
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
      <div className="flex items-center gap-2">
        {job.lifecycle_status === "draft" && (
          <>
            <Button
              size="sm"
              variant="outline"
              disabled={
                job.processing_status !== "ready" || publishJob.isPending
              }
              onClick={() => runAction(() => publishJob.mutateAsync())}
            >
              Publish
            </Button>
            <Button
              size="sm"
              variant="destructive"
              disabled={deleteJob.isPending}
              onClick={() =>
                runAction(() =>
                  deleteJob.mutateAsync({ jobId: job.id, companyId }),
                )
              }
            >
              Delete
            </Button>
          </>
        )}
        {job.lifecycle_status === "published" && (
          <Button
            size="sm"
            variant="outline"
            disabled={closeJob.isPending}
            onClick={() => runAction(() => closeJob.mutateAsync())}
          >
            Close
          </Button>
        )}
        {job.lifecycle_status === "closed" && (
          <Button
            size="sm"
            variant="outline"
            disabled={reopenJob.isPending}
            onClick={() => runAction(() => reopenJob.mutateAsync())}
          >
            Reopen
          </Button>
        )}
      </div>
      {error && <p className="text-destructive">{error}</p>}
    </div>
  );
}

export default function RecruiterJobsPage() {
  const { company, isLoading: companyLoading } = useMyCompany();
  const { data: jobs, isLoading: jobsLoading } = useJobs(company?.id);

  if (companyLoading || (company && jobsLoading)) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading jobs…</p>
      </div>
    );
  }

  if (!company) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">
          No company found for your account.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Jobs</h1>
        <Link
          href="/recruiter/jobs/new"
          className={buttonVariants({ variant: "default" })}
        >
          New job
        </Link>
      </div>
      <div className="flex flex-col gap-2">
        {(jobs ?? []).length === 0 && (
          <p className="text-sm text-muted-foreground">No jobs posted yet.</p>
        )}
        {(jobs ?? []).map((job) => (
          <JobRow key={job.id} job={job} companyId={company.id} />
        ))}
      </div>
    </div>
  );
}
