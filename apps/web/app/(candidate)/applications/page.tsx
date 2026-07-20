"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useMyApplications } from "@/hooks/use-applications";

const STATUS_VARIANT: Record<
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

export default function MyApplicationsPage() {
  const { data: applications, isLoading } = useMyApplications();

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading applications…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold">My applications</h1>
      <Card>
        <CardHeader>
          <CardTitle>Applications</CardTitle>
          <CardDescription>
            Track the status of jobs you&apos;ve applied to.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {(applications ?? []).length === 0 && (
            <p className="text-sm text-muted-foreground">
              You haven&apos;t applied to any jobs yet.
            </p>
          )}
          {(applications ?? []).map(({ application, job }) => (
            <div
              key={application.id}
              className="flex items-center justify-between rounded-lg border p-3 text-sm"
            >
              <div>
                <p className="font-medium">{job.title}</p>
                {application.applied_at && (
                  <p className="text-muted-foreground">
                    Applied{" "}
                    {new Date(application.applied_at).toLocaleDateString()}
                  </p>
                )}
              </div>
              <Badge variant={STATUS_VARIANT[application.status] ?? "outline"}>
                {application.status}
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
