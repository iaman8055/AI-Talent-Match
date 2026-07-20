"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as jobsApi from "@/lib/api-client/jobs";
import type { CreateJobRequest, UpdateJobRequest } from "@/lib/api-client/jobs";

const jobsKey = (companyId: string) => ["jobs", companyId];
const jobKey = (jobId: string) => ["job", jobId];

export function useJobs(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? jobsKey(companyId) : ["jobs"],
    queryFn: () => jobsApi.listJobs(companyId as string),
    enabled: !!companyId,
  });
}

export function useJob(jobId: string | undefined) {
  return useQuery({
    queryKey: jobId ? jobKey(jobId) : ["job"],
    queryFn: () => jobsApi.getJob(jobId as string),
    enabled: !!jobId,
  });
}

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateJobRequest) => jobsApi.createJob(body),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: jobsKey(data.company_id),
      });
    },
  });
}

export function useUpdateJob(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateJobRequest) => jobsApi.updateJob(jobId, body),
    onSuccess: (data) => {
      queryClient.setQueryData(jobKey(jobId), data);
      void queryClient.invalidateQueries({
        queryKey: jobsKey(data.company_id),
      });
    },
  });
}

function useJobLifecycleAction(
  jobId: string,
  action: (jobId: string) => Promise<jobsApi.JobResponse>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => action(jobId),
    onSuccess: (data) => {
      queryClient.setQueryData(jobKey(jobId), data);
      void queryClient.invalidateQueries({
        queryKey: jobsKey(data.company_id),
      });
    },
  });
}

export function usePublishJob(jobId: string) {
  return useJobLifecycleAction(jobId, jobsApi.publishJob);
}

export function useCloseJob(jobId: string) {
  return useJobLifecycleAction(jobId, jobsApi.closeJob);
}

export function useReopenJob(jobId: string) {
  return useJobLifecycleAction(jobId, jobsApi.reopenJob);
}

export function useDeleteJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ jobId }: { jobId: string; companyId: string }) =>
      jobsApi.deleteJob(jobId),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: jobsKey(variables.companyId),
      });
    },
  });
}
