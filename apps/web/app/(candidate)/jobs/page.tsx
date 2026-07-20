"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useApplyToJob, useMyApplications } from "@/hooks/use-applications";
import { useRecommendedJobs } from "@/hooks/use-matching";
import { ApiError } from "@/lib/api-client/client";

export default function RecommendedJobsPage() {
  const { data: recommended, isLoading } = useRecommendedJobs();
  const { data: myApplications } = useMyApplications();
  const applyToJob = useApplyToJob();
  const [error, setError] = useState<string | null>(null);
  const [applyingJobId, setApplyingJobId] = useState<string | null>(null);

  const appliedJobIds = useMemo(
    () => new Set((myApplications ?? []).map((entry) => entry.job.id)),
    [myApplications],
  );

  const onApply = async (jobId: string) => {
    setError(null);
    setApplyingJobId(jobId);
    try {
      await applyToJob.mutateAsync({ job_id: jobId });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not apply. Please try again.",
      );
    } finally {
      setApplyingJobId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">
          Loading recommended jobs…
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold">Recommended jobs</h1>
      {error && <p className="text-sm text-destructive">{error}</p>}

      {(recommended ?? []).length === 0 && (
        <p className="text-sm text-muted-foreground">
          No recommended jobs yet. Make sure your profile and resume are up to
          date — new matches appear automatically once they&apos;re computed.
        </p>
      )}

      {(recommended ?? []).map(({ job, match }) => {
        const applied = appliedJobIds.has(job.id);
        return (
          <Card key={job.id}>
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <CardTitle>{job.title}</CardTitle>
                <Badge>{Math.round(match.overall_score)}% match</Badge>
              </div>
              {job.summary && <CardDescription>{job.summary}</CardDescription>}
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {job.required_skills.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {job.required_skills.map((skill) => (
                    <Badge key={skill} variant="outline">
                      {skill}
                    </Badge>
                  ))}
                </div>
              )}
              <Button
                className="w-fit"
                disabled={applied || applyingJobId === job.id}
                onClick={() => onApply(job.id)}
              >
                {applied
                  ? "Applied"
                  : applyingJobId === job.id
                    ? "Applying…"
                    : "Apply"}
              </Button>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
