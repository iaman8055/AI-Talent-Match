"use client";

import { ClipboardList } from "lucide-react";

import { EmptyState } from "@/components/dashboard/empty-state";
import { PageHeader } from "@/components/dashboard/page-header";
import { PipelineStepper } from "@/components/dashboard/pipeline-stepper";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useMyApplications } from "@/hooks/use-applications";

export default function MyApplicationsPage() {
  const { data: applications, isLoading } = useMyApplications();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="My applications"
        description="Track the status of every job you've applied to."
      />

      {isLoading && <Skeleton className="h-48 w-full" />}

      {!isLoading && (applications ?? []).length === 0 && (
        <EmptyState
          icon={ClipboardList}
          title="No applications yet"
          description="Apply to a recommended job to start tracking its status here."
        />
      )}

      {!isLoading && (applications ?? []).length > 0 && (
        <Card>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job</TableHead>
                  <TableHead>Pipeline</TableHead>
                  <TableHead className="text-right">Applied</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(applications ?? []).map(({ application, job }) => (
                  <TableRow key={application.id}>
                    <TableCell className="font-medium whitespace-normal">
                      {job.title}
                    </TableCell>
                    <TableCell className="min-w-72">
                      <PipelineStepper status={application.status} />
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {application.applied_at
                        ? new Date(application.applied_at).toLocaleDateString()
                        : "—"}
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
