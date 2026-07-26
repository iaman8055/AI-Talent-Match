"use client";

import { useQuery } from "@tanstack/react-query";

import * as matchingApi from "@/lib/api-client/matching";

export function useJobCandidates(jobId: string | undefined) {
  return useQuery({
    queryKey: jobId ? ["jobCandidates", jobId] : ["jobCandidates"],
    queryFn: () => matchingApi.listJobCandidates(jobId as string),
    enabled: !!jobId,
  });
}

export function useRecommendedJobs() {
  return useQuery({
    queryKey: ["recommendedJobs"],
    queryFn: matchingApi.listRecommendedJobs,
  });
}

export function useJobSearch(params: {
  q?: string;
  location?: string;
  enabled?: boolean;
}) {
  return useQuery({
    queryKey: ["jobSearch", params.q ?? "", params.location ?? ""],
    queryFn: () => matchingApi.searchJobs(params),
    enabled: params.enabled ?? true,
  });
}

export function useJobForCandidate(jobId: string | undefined) {
  return useQuery({
    queryKey: jobId ? ["candidateJobDetail", jobId] : ["candidateJobDetail"],
    queryFn: () => matchingApi.getJobForCandidate(jobId as string),
    enabled: !!jobId,
  });
}
