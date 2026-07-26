"use client";

import { CheckCircle2, ExternalLink, Search, Sparkles } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useMemo, useState } from "react";
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
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useApplyToJob, useMyApplications } from "@/hooks/use-applications";
import { useJobSearch, useRecommendedJobs } from "@/hooks/use-matching";
import { ApiError } from "@/lib/api-client/client";
import type { JobResponse } from "@/lib/api-client/jobs";

function JobCard({
  job,
  matchScore,
  applied,
  applying,
  onApply,
}: {
  job: JobResponse;
  matchScore: number | null;
  applied: boolean;
  applying: boolean;
  onApply: (jobId: string, title: string) => void;
}) {
  const isExternal = job.source !== "native";

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Link href={`/jobs/${job.id}`} className="hover:underline">
                <CardTitle>{job.title}</CardTitle>
              </Link>
              {isExternal && <Badge variant="secondary">LinkedIn</Badge>}
            </div>
            {isExternal && job.external_company_name && (
              <p className="mt-1 text-sm text-muted-foreground">
                {job.external_company_name}
              </p>
            )}
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
          {matchScore === null ? (
            <p className="text-xs text-muted-foreground">Not yet matched</p>
          ) : (
            <MatchScore score={matchScore} />
          )}
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
        {isExternal ? (
          <Button
            className="w-fit"
            variant="outline"
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
            className="w-fit"
            variant={applied ? "secondary" : "default"}
            disabled={applied || applying}
            onClick={() => onApply(job.id, job.title)}
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
      </CardContent>
    </Card>
  );
}

export default function RecommendedJobsPage() {
  const [queryInput, setQueryInput] = useState("");
  const [locationInput, setLocationInput] = useState("");
  const [submitted, setSubmitted] = useState<{
    q: string;
    location: string;
  } | null>(null);
  const isSearching = submitted !== null;

  const { data: recommended, isLoading: recommendedLoading } =
    useRecommendedJobs();
  const { data: searchResults, isLoading: searchLoading } = useJobSearch({
    q: submitted?.q,
    location: submitted?.location,
    enabled: isSearching,
  });
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

  const onSearchSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!queryInput.trim() && !locationInput.trim()) {
      setSubmitted(null);
      return;
    }
    setSubmitted({ q: queryInput.trim(), location: locationInput.trim() });
  };

  const onClearSearch = () => {
    setQueryInput("");
    setLocationInput("");
    setSubmitted(null);
  };

  const isLoading = isSearching ? searchLoading : recommendedLoading;
  const results = isSearching
    ? (searchResults ?? []).map(({ job, match }) => ({
        job,
        matchScore: match?.overall_score ?? null,
      }))
    : (recommended ?? []).map(({ job, match }) => ({
        job,
        matchScore: match.overall_score,
      }));

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={isSearching ? "Job search" : "Recommended jobs"}
        description={
          isSearching
            ? "Every published job matching your search, with your match score where it's already been computed."
            : "Ranked by how well your profile matches each role."
        }
      />

      <Card>
        <CardContent>
          <form
            onSubmit={onSearchSubmit}
            className="flex flex-col gap-3 sm:flex-row sm:items-end"
          >
            <div className="flex flex-1 flex-col gap-2">
              <label htmlFor="job-search-q" className="text-sm font-medium">
                Job title or keyword
              </label>
              <Input
                id="job-search-q"
                placeholder="e.g. Backend Engineer"
                value={queryInput}
                onChange={(event) => setQueryInput(event.target.value)}
              />
            </div>
            <div className="flex flex-1 flex-col gap-2">
              <label
                htmlFor="job-search-location"
                className="text-sm font-medium"
              >
                Location
              </label>
              <Input
                id="job-search-location"
                placeholder="e.g. Bangalore"
                value={locationInput}
                onChange={(event) => setLocationInput(event.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button type="submit">
                <Search />
                Search
              </Button>
              {isSearching && (
                <Button type="button" variant="outline" onClick={onClearSearch}>
                  Clear
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-44 w-full" />
          ))}
        </div>
      )}

      {!isLoading && results.length === 0 && (
        <EmptyState
          icon={Search}
          title={isSearching ? "No jobs found" : "No recommendations yet"}
          description={
            isSearching
              ? "Try a different keyword or location, or clear the search to see your recommendations."
              : "Make sure your profile and resume are up to date — new matches appear automatically once they're computed."
          }
        />
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {results.map(({ job, matchScore }) => (
          <JobCard
            key={job.id}
            job={job}
            matchScore={matchScore}
            applied={appliedJobIds.has(job.id)}
            applying={applyingJobId === job.id}
            onApply={onApply}
          />
        ))}
      </div>
    </div>
  );
}
