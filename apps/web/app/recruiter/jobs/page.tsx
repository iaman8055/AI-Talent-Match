"use client";

import {
  Briefcase,
  CheckCircle2,
  FileEdit,
  MoreHorizontal,
  Plus,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/dashboard/empty-state";
import { PageHeader } from "@/components/dashboard/page-header";
import { StatCard } from "@/components/dashboard/stat-card";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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

function JobActions({
  job,
  companyId,
}: {
  job: JobResponse;
  companyId: string;
}) {
  const publishJob = usePublishJob(job.id);
  const closeJob = useCloseJob(job.id);
  const reopenJob = useReopenJob(job.id);
  const deleteJob = useDeleteJob();

  const runAction = async (action: () => Promise<unknown>, message: string) => {
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

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" size="icon-sm">
            <MoreHorizontal />
          </Button>
        }
      />
      <DropdownMenuContent align="end">
        {job.lifecycle_status === "draft" && (
          <>
            <DropdownMenuItem
              disabled={
                job.processing_status !== "ready" || publishJob.isPending
              }
              onClick={() =>
                runAction(() => publishJob.mutateAsync(), "Job published")
              }
            >
              <CheckCircle2 />
              Publish
            </DropdownMenuItem>
            <DropdownMenuItem
              variant="destructive"
              disabled={deleteJob.isPending}
              onClick={() =>
                runAction(
                  () => deleteJob.mutateAsync({ jobId: job.id, companyId }),
                  "Job deleted",
                )
              }
            >
              <XCircle />
              Delete
            </DropdownMenuItem>
          </>
        )}
        {job.lifecycle_status === "published" && (
          <DropdownMenuItem
            disabled={closeJob.isPending}
            onClick={() =>
              runAction(() => closeJob.mutateAsync(), "Job closed")
            }
          >
            <XCircle />
            Close
          </DropdownMenuItem>
        )}
        {job.lifecycle_status === "closed" && (
          <DropdownMenuItem
            disabled={reopenJob.isPending}
            onClick={() =>
              runAction(() => reopenJob.mutateAsync(), "Job reopened")
            }
          >
            <CheckCircle2 />
            Reopen
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function RecruiterJobsPage() {
  const { company, isLoading: companyLoading } = useMyCompany();
  const { data: jobs, isLoading: jobsLoading } = useJobs(company?.id);

  const counts = useMemo(() => {
    const list = jobs ?? [];
    return {
      draft: list.filter((j) => j.lifecycle_status === "draft").length,
      published: list.filter((j) => j.lifecycle_status === "published").length,
      closed: list.filter((j) => j.lifecycle_status === "closed").length,
    };
  }, [jobs]);

  const isLoading = companyLoading || (!!company && jobsLoading);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Jobs"
        description="Manage your open roles and review their pipelines."
        actions={
          <Link href="/recruiter/jobs/new" className={buttonVariants()}>
            <Plus />
            New job
          </Link>
        }
      />

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {!isLoading && (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard icon={FileEdit} label="Draft" value={counts.draft} />
          <StatCard
            icon={CheckCircle2}
            label="Published"
            value={counts.published}
          />
          <StatCard icon={XCircle} label="Closed" value={counts.closed} />
        </div>
      )}

      {!isLoading && !company && (
        <EmptyState
          icon={Briefcase}
          title="No company found"
          description="Your account isn't linked to a company yet."
        />
      )}

      {!isLoading && company && (jobs ?? []).length === 0 && (
        <EmptyState
          icon={Briefcase}
          title="No jobs posted yet"
          description="Post your first job to start finding matched candidates."
          action={
            <Link
              href="/recruiter/jobs/new"
              className={buttonVariants({ variant: "outline" })}
            >
              <Plus />
              New job
            </Link>
          }
        />
      )}

      {!isLoading && company && (jobs ?? []).length > 0 && (
        <Card>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Processing</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {(jobs ?? []).map((job) => (
                  <TableRow key={job.id}>
                    <TableCell className="font-medium">
                      <Link
                        href={`/recruiter/jobs/${job.id}`}
                        className="hover:underline"
                      >
                        {job.title}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          LIFECYCLE_VARIANT[job.lifecycle_status] ?? "outline"
                        }
                      >
                        {job.lifecycle_status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          PROCESSING_VARIANT[job.processing_status] ?? "outline"
                        }
                      >
                        {job.processing_status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(job.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <JobActions job={job} companyId={company.id} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
