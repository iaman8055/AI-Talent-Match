"use client";

import {
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  MapPin,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { MatchScore } from "@/components/dashboard/match-score";
import { PageHeader } from "@/components/dashboard/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApplyToJob, useMyApplications } from "@/hooks/use-applications";
import { useJobForCandidate } from "@/hooks/use-matching";
import { ApiError } from "@/lib/api-client/client";

function formatSalary(min: number | null, max: number | null): string | null {
  if (min == null && max == null) return null;
  if (min != null && max != null) return `${min.toLocaleString()} – ${max.toLocaleString()}`;
  return (min ?? max)!.toLocaleString();
}

function SkillList({ title, skills }: { title: string; skills: string[] }) {
  if (skills.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-medium">{title}</h3>
      <div className="flex flex-wrap gap-1.5">
        {skills.map((skill) => (
          <Badge key={skill} variant="outline">
            {skill}
          </Badge>
        ))}
      </div>
    </div>
  );
}

function TextList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-medium">{title}</h3>
      <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default function CandidateJobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const { data, isLoading } = useJobForCandidate(jobId);
  const { data: myApplications } = useMyApplications();
  const applyToJob = useApplyToJob();
  const [applying, setApplying] = useState(false);

  if (isLoading || !data) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  const { job, match } = data;
  const isExternal = job.source !== "native";
  const applied = (myApplications ?? []).some((entry) => entry.job.id === job.id);
  const location = [job.location.city, job.location.region, job.location.country]
    .filter(Boolean)
    .join(", ");
  const salary = formatSalary(job.salary_min ?? null, job.salary_max ?? null);

  const onApply = async () => {
    setApplying(true);
    try {
      await applyToJob.mutateAsync({ job_id: job.id });
      toast.success(`Applied to ${job.title}`);
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Could not apply. Please try again.",
      );
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/jobs"
        className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        Back to jobs
      </Link>

      <PageHeader
        title={job.title}
        description={isExternal ? job.external_company_name ?? undefined : undefined}
        actions={
          <>
            {isExternal && <Badge variant="secondary">LinkedIn</Badge>}
            {isExternal ? (
              <Button
                render={
                  <a
                    href={job.external_url ?? "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                  />
                }
              >
                <ExternalLink />
                Apply on LinkedIn
              </Button>
            ) : (
              <Button
                variant={applied ? "secondary" : "default"}
                disabled={applied || applying}
                onClick={onApply}
              >
                {applied ? (
                  <>
                    <CheckCircle2 />
                    Applied
                  </>
                ) : applying ? (
                  "Applying…"
                ) : (
                  "Apply"
                )}
              </Button>
            )}
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <div className="flex flex-col gap-4 md:col-span-2">
          <Card>
            <CardContent className="flex flex-col gap-4 pt-6">
              {job.summary && <p className="text-sm text-muted-foreground">{job.summary}</p>}
              <p className="whitespace-pre-wrap text-sm">{job.raw_description}</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex flex-col gap-5 pt-6">
              <SkillList title="Required skills" skills={job.required_skills} />
              <SkillList title="Nice to have" skills={job.nice_to_have_skills} />
              <TextList title="Responsibilities" items={job.responsibilities} />
              <TextList title="Qualifications" items={job.qualifications} />
            </CardContent>
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Your match</CardTitle>
            </CardHeader>
            <CardContent>
              {match ? (
                <MatchScore score={match.overall_score} size="lg" />
              ) : (
                <p className="text-sm text-muted-foreground">
                  Not yet matched against your profile.
                </p>
              )}
            </CardContent>
          </Card>

          {(location || salary || job.work_mode || job.min_experience_years != null) && (
            <Card>
              <CardContent className="flex flex-col gap-3 pt-6 text-sm">
                {location && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <MapPin className="size-4" />
                    {location}
                    {job.work_mode && ` · ${job.work_mode}`}
                  </div>
                )}
                {salary && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Wallet className="size-4" />
                    {salary}
                  </div>
                )}
                {job.min_experience_years != null && (
                  <p className="text-muted-foreground">
                    {job.min_experience_years}+ years experience
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
