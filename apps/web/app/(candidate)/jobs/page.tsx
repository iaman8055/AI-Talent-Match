"use client";

import { CheckCircle2, Search, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/dashboard/empty-state";
import { MatchScore } from "@/components/dashboard/match-score";
import { PageHeader } from "@/components/dashboard/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApplyToJob, useMyApplications } from "@/hooks/use-applications";
import { useRecommendedJobs } from "@/hooks/use-matching";
import { ApiError } from "@/lib/api-client/client";

export default function RecommendedJobsPage() {
  const { data: recommended, isLoading } = useRecommendedJobs();
  const { data: myApplications } = useMyApplications();
  const applyToJob = useApplyToJob();
  const [applyingJobId, setApplyingJobId] = useState<string | null>(null);

  const appliedJobIds = useMemo(
    () => new Set((myApplications ?? []).map((entry) => entry.job.id)),
    [myApplications],
  );

  const onApply = async (jobId: string, title: string) => {
    setApplyingJobId(jobId);
    try {
      await applyToJob.mutateAsync({ job_id: jobId });
      toast.success(`Applied to ${title}`);
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.message
          : "Could not apply. Please try again.",
      );
    } finally {
      setApplyingJobId(null);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Recommended jobs"
        description="Ranked by how well your profile matches each role."
      />

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-44 w-full" />
          ))}
        </div>
      )}

      {!isLoading && (recommended ?? []).length === 0 && (
        <EmptyState
          icon={Search}
          title="No recommendations yet"
          description="Make sure your profile and resume are up to date — new matches appear automatically once they're computed."
        />
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {(recommended ?? []).map(({ job, match }) => {
          const applied = appliedJobIds.has(job.id);
          return (
            <Card key={job.id} className="flex flex-col">
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle>{job.title}</CardTitle>
                    {job.summary && (
                      <CardDescription className="mt-1 line-clamp-2">
                        {job.summary}
                      </CardDescription>
                    )}
                  </div>
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Sparkles className="size-4.5" />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex flex-1 flex-col justify-between gap-4">
                <div className="flex flex-col gap-4">
                  <MatchScore score={match.overall_score} />
                  {job.required_skills.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {job.required_skills.slice(0, 6).map((skill) => (
                        <Badge key={skill} variant="outline">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
                <Button
                  className="w-fit"
                  variant={applied ? "secondary" : "default"}
                  disabled={applied || applyingJobId === job.id}
                  onClick={() => onApply(job.id, job.title)}
                >
                  {applied ? (
                    <>
                      <CheckCircle2 />
                      Applied
                    </>
                  ) : applyingJobId === job.id ? (
                    "Applying…"
                  ) : (
                    "Apply"
                  )}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
