"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  useCandidateDetail,
  useInterviewApplication,
  useInviteCandidate,
  useOfferApplication,
  useRejectApplication,
  useScreenApplication,
} from "@/hooks/use-applications";
import { ApiError } from "@/lib/api-client/client";

const APPLICATION_STATUS_VARIANT: Record<
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

type ScoreKey =
  | "semantic_score"
  | "skill_overlap_score"
  | "experience_fit_score"
  | "salary_fit_score"
  | "location_fit_score";

const SCORE_ROWS: { key: ScoreKey; label: string }[] = [
  { key: "semantic_score", label: "Semantic similarity" },
  { key: "skill_overlap_score", label: "Skill overlap" },
  { key: "experience_fit_score", label: "Experience fit" },
  { key: "salary_fit_score", label: "Salary fit" },
  { key: "location_fit_score", label: "Location fit" },
];

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

  if (isLoading || !detail) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading candidate…</p>
      </div>
    );
  }

  const { candidate, match, missing_skills, application } = detail;
  const missingSet = new Set(missing_skills);

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">
          {candidate.full_name ?? "Unnamed candidate"}
        </h1>
        {application && (
          <Badge
            variant={
              APPLICATION_STATUS_VARIANT[application.status] ?? "outline"
            }
          >
            {application.status}
          </Badge>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          {candidate.headline && (
            <CardDescription>{candidate.headline}</CardDescription>
          )}
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {candidate.summary && <p className="text-sm">{candidate.summary}</p>}

          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium">Skills</p>
            <div className="flex flex-wrap gap-1.5">
              {candidate.skills.map((skill) => (
                <Badge
                  key={skill}
                  variant={missingSet.has(skill) ? "outline" : "default"}
                >
                  {skill}
                </Badge>
              ))}
            </div>
            {missing_skills.length > 0 && (
              <p className="text-sm text-muted-foreground">
                Missing required skills: {missing_skills.join(", ")}
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Experience</p>
              <p>
                {candidate.total_experience_years != null
                  ? `${candidate.total_experience_years} years`
                  : "Not specified"}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Location</p>
              <p>
                {[
                  candidate.location.city,
                  candidate.location.region,
                  candidate.location.country,
                ]
                  .filter(Boolean)
                  .join(", ") || "Not specified"}
              </p>
            </div>
          </div>

          {candidate.work_experience.length > 0 && (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium">Work experience</p>
              {candidate.work_experience.map((item, index) => (
                <div key={index} className="text-sm">
                  <p className="font-medium">
                    {item.title} · {item.company}
                  </p>
                  {item.description && (
                    <p className="text-muted-foreground">{item.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {candidate.education.length > 0 && (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium">Education</p>
              {candidate.education.map((item, index) => (
                <div key={index} className="text-sm">
                  <p className="font-medium">{item.institution}</p>
                  {item.degree && (
                    <p className="text-muted-foreground">
                      {item.degree}
                      {item.field_of_study ? `, ${item.field_of_study}` : ""}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Match</CardTitle>
        </CardHeader>
        <CardContent>
          {!match && (
            <p className="text-sm text-muted-foreground">
              This candidate hasn&apos;t been matched against this job yet.
            </p>
          )}
          {match && (
            <div className="flex flex-col gap-2 text-sm">
              <div className="flex items-center justify-between">
                <p className="font-medium">Overall score</p>
                <Badge>{Math.round(match.overall_score)}%</Badge>
              </div>
              {SCORE_ROWS.map((row) => (
                <div
                  key={row.key}
                  className="flex items-center justify-between"
                >
                  <p className="text-muted-foreground">{row.label}</p>
                  <p>{Math.round(match[row.key])}%</p>
                </div>
              ))}
              {match.rerank_score != null && (
                <div className="flex items-center justify-between">
                  <p className="text-muted-foreground">Reranker score</p>
                  <p>{Math.round(match.rerank_score)}%</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Pipeline</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {!application && (
              <Button
                disabled={inviteCandidate.isPending}
                onClick={() =>
                  runAction(() =>
                    inviteCandidate.mutateAsync({ candidate_id: candidate.id }),
                  )
                }
              >
                {inviteCandidate.isPending ? "Inviting…" : "Invite to apply"}
              </Button>
            )}
            {application?.status === "invited" && (
              <Button
                variant="outline"
                disabled={inviteCandidate.isPending}
                onClick={() =>
                  runAction(() =>
                    inviteCandidate.mutateAsync({ candidate_id: candidate.id }),
                  )
                }
              >
                {inviteCandidate.isPending ? "Resending…" : "Resend invite"}
              </Button>
            )}
            {application?.status === "applied" && (
              <Button
                disabled={screenApplication.isPending}
                onClick={() =>
                  runAction(() => screenApplication.mutateAsync(application.id))
                }
              >
                Move to screening
              </Button>
            )}
            {application?.status === "screening" && (
              <Button
                disabled={interviewApplication.isPending}
                onClick={() =>
                  runAction(() =>
                    interviewApplication.mutateAsync(application.id),
                  )
                }
              >
                Advance to interview
              </Button>
            )}
            {application?.status === "interview" && (
              <Button
                disabled={offerApplication.isPending}
                onClick={() =>
                  runAction(() => offerApplication.mutateAsync(application.id))
                }
              >
                Extend offer
              </Button>
            )}
            {application && application.status !== "rejected" && (
              <Button
                variant="destructive"
                disabled={rejectApplication.isPending}
                onClick={() =>
                  runAction(() => rejectApplication.mutateAsync(application.id))
                }
              >
                Reject
              </Button>
            )}
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
