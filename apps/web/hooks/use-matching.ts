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
