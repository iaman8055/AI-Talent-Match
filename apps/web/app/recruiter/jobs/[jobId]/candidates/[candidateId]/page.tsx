"use client";

import {
  ArrowLeft,
  Briefcase,
  Check,
  GraduationCap,
  Mail,
  MapPin,
  X,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { MatchScore } from "@/components/dashboard/match-score";
import { PipelineStepper } from "@/components/dashboard/pipeline-stepper";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useCandidateDetail,
  useInterviewApplication,
  useInviteCandidate,
  useOfferApplication,
  useRejectApplication,
  useScreenApplication,
} from "@/hooks/use-applications";
import { ApiError } from "@/lib/api-client/client";
import { cn } from "@/lib/utils";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const chars =
    parts.length > 1
      ? [parts[0][0], parts[parts.length - 1][0]]
      : [parts[0]?.[0]];
  return chars.join("").toUpperCase() || "?";
}

export default function CandidateDetailPage() {
  const { jobId, candidateId } = useParams<{
    jobId: string;
    candidateId: string;
  }>();

  const { data: detail, isLoading } = useCandidateDetail(jobId, candidateId);
  const inviteCandidate = useInviteCandidate(jobId);
  const screenApplication = useScreenApplication(jobId, candidateId);
  const interviewApplication = useInterviewApplication(jobId, candidateId);
  const offerApplication = useOfferApplication(jobId, candidateId);
  const rejectApplication = useRejectApplication(jobId, candidateId);
  const [pendingAction, setPendingAction] = useState<string | null>(null);

  const runAction = async (
    key: string,
    action: () => Promise<unknown>,
    message: string,
  ) => {
    setPendingAction(key);
    try {
      await action();
      toast.success(message);
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.message
          : "Action failed. Please try again.",
      );
    } finally {
      setPendingAction(null);
    }
  };

  if (isLoading || !detail) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  const { candidate, match, matched_skills, missing_skills, application } =
    detail;
  const matchedSet = new Set(matched_skills);

  return (
    <div className="flex flex-col gap-6">
      <Link
        href={`/recruiter/jobs/${jobId}`}
        className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        Back to job
      </Link>

      <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Avatar size="lg">
            <AvatarFallback className="bg-primary/10 text-lg text-primary">
              {initials(candidate.full_name ?? "?")}
            </AvatarFallback>
          </Avatar>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {candidate.full_name ?? "Unnamed candidate"}
            </h1>
            {candidate.headline && (
              <p className="text-sm text-muted-foreground">
                {candidate.headline}
              </p>
            )}
          </div>
        </div>
        {application && (
          <Badge variant="outline" className="capitalize">
            {application.status}
          </Badge>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Profile</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-5">
              {candidate.summary && (
                <p className="text-sm text-muted-foreground">
                  {candidate.summary}
                </p>
              )}

              <div className="flex flex-wrap gap-4 text-sm">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Briefcase className="size-4" />
                  {candidate.total_experience_years != null
                    ? `${candidate.total_experience_years} years experience`
                    : "Experience not specified"}
                </div>
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <MapPin className="size-4" />
                  {[
                    candidate.location.city,
                    candidate.location.region,
                    candidate.location.country,
                  ]
                    .filter(Boolean)
                    .join(", ") || "Location not specified"}
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <p className="text-sm font-medium">Skills</p>
                <div className="flex flex-wrap gap-1.5">
                  {candidate.skills.map((skill) => (
                    <Badge
                      key={skill}
                      variant={matchedSet.has(skill) ? "default" : "outline"}
                      className="gap-1"
                    >
                      {matchedSet.has(skill) && <Check className="size-3" />}
                      {skill}
                    </Badge>
                  ))}
                </div>
                {missing_skills.length > 0 && (
                  <div className="flex flex-col gap-1.5 pt-1">
                    <p className="text-xs font-medium text-muted-foreground">
                      Missing from job requirements
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {missing_skills.map((skill) => (
                        <Badge
                          key={skill}
                          variant="outline"
                          className="gap-1 border-dashed text-muted-foreground"
                        >
                          <X className="size-3" />
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {candidate.work_experience.length > 0 && (
                <div className="flex flex-col gap-3">
                  <p className="flex items-center gap-1.5 text-sm font-medium">
                    <Briefcase className="size-4" />
                    Work experience
                  </p>
                  <div className="flex flex-col gap-3 border-l pl-4">
                    {candidate.work_experience.map((item, index) => (
                      <div key={index} className="text-sm">
                        <p className="font-medium">
                          {item.title} · {item.company}
                        </p>
                        {item.description && (
                          <p className="text-muted-foreground">
                            {item.description}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {candidate.education.length > 0 && (
                <div className="flex flex-col gap-3">
                  <p className="flex items-center gap-1.5 text-sm font-medium">
                    <GraduationCap className="size-4" />
                    Education
                  </p>
                  <div className="flex flex-col gap-3 border-l pl-4">
                    {candidate.education.map((item, index) => (
                      <div key={index} className="text-sm">
                        <p className="font-medium">{item.institution}</p>
                        {item.degree && (
                          <p className="text-muted-foreground">
                            {item.degree}
                            {item.field_of_study
                              ? `, ${item.field_of_study}`
                              : ""}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Pipeline</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-5">
              {application ? (
                <PipelineStepper status={application.status} />
              ) : (
                <p className="text-sm text-muted-foreground">
                  This candidate hasn&apos;t been invited yet.
                </p>
              )}
              <div className="flex flex-wrap items-center gap-2">
                {!application && (
                  <Button
                    disabled={pendingAction === "invite"}
                    onClick={() =>
                      runAction(
                        "invite",
                        () =>
                          inviteCandidate.mutateAsync({
                            candidate_id: candidate.id,
                          }),
                        "Invite sent",
                      )
                    }
                  >
                    <Mail />
                    Invite to apply
                  </Button>
                )}
                {application?.status === "invited" && (
                  <Button
                    variant="outline"
                    disabled={pendingAction === "invite"}
                    onClick={() =>
                      runAction(
                        "invite",
                        () =>
                          inviteCandidate.mutateAsync({
                            candidate_id: candidate.id,
                          }),
                        "Invite resent",
                      )
                    }
                  >
                    <Mail />
                    Resend invite
                  </Button>
                )}
                {application?.status === "applied" && (
                  <Button
                    disabled={pendingAction === "screen"}
                    onClick={() =>
                      runAction(
                        "screen",
                        () => screenApplication.mutateAsync(application.id),
                        "Moved to screening",
                      )
                    }
                  >
                    Move to screening
                  </Button>
                )}
                {application?.status === "screening" && (
                  <Button
                    disabled={pendingAction === "interview"}
                    onClick={() =>
                      runAction(
                        "interview",
                        () => interviewApplication.mutateAsync(application.id),
                        "Advanced to interview",
                      )
                    }
                  >
                    Advance to interview
                  </Button>
                )}
                {application?.status === "interview" && (
                  <Button
                    disabled={pendingAction === "offer"}
                    onClick={() =>
                      runAction(
                        "offer",
                        () => offerApplication.mutateAsync(application.id),
                        "Offer extended",
                      )
                    }
                  >
                    Extend offer
                  </Button>
                )}
                {application && application.status !== "rejected" && (
                  <Button
                    variant="destructive"
                    disabled={pendingAction === "reject"}
                    onClick={() =>
                      runAction(
                        "reject",
                        () => rejectApplication.mutateAsync(application.id),
                        "Application rejected",
                      )
                    }
                  >
                    Reject
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Match</CardTitle>
            </CardHeader>
            <CardContent>
              {!match ? (
                <p className="text-sm text-muted-foreground">
                  Not matched against this job yet.
                </p>
              ) : (
                <div className="flex flex-col gap-5">
                  <MatchScore score={match.overall_score} size="lg" />
                  <div className="flex flex-col gap-3 text-sm">
                    {[
                      {
                        label: "Semantic similarity",
                        value: match.semantic_score,
                      },
                      {
                        label: "Skill overlap",
                        value: match.skill_overlap_score,
                      },
                      {
                        label: "Experience fit",
                        value: match.experience_fit_score,
                      },
                      { label: "Salary fit", value: match.salary_fit_score },
                      {
                        label: "Location fit",
                        value: match.location_fit_score,
                      },
                      ...(match.rerank_score != null
                        ? [{ label: "Reranker", value: match.rerank_score }]
                        : []),
                    ].map((row) => (
                      <div key={row.label} className="flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">
                            {row.label}
                          </span>
                          <span className="font-medium tabular-nums">
                            {Math.round(row.value)}%
                          </span>
                        </div>
                        <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
                          <div
                            className={cn("h-full rounded-full bg-primary")}
                            style={{ width: `${Math.round(row.value)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
