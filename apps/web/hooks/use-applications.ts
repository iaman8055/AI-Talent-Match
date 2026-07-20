"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import * as applicationsApi from "@/lib/api-client/applications";
import type {
  ApplicationResponse,
  ApplyToJobRequest,
  InviteCandidateRequest,
} from "@/lib/api-client/applications";

const candidateDetailKey = (jobId: string, candidateId: string) => [
  "candidateDetail",
  jobId,
  candidateId,
];
const jobApplicationsKey = (jobId: string) => ["jobApplications", jobId];
const MY_APPLICATIONS_KEY = ["myApplications"];

export function useCandidateDetail(
  jobId: string | undefined,
  candidateId: string | undefined,
) {
  return useQuery({
    queryKey:
      jobId && candidateId
        ? candidateDetailKey(jobId, candidateId)
        : ["candidateDetail"],
    queryFn: () =>
      applicationsApi.getCandidateDetail(
        jobId as string,
        candidateId as string,
      ),
    enabled: !!jobId && !!candidateId,
  });
}

export function useInviteCandidate(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: InviteCandidateRequest) =>
      applicationsApi.inviteCandidate(jobId, body),
    onSuccess: (data) => {
      queryClient.setQueryData(
        candidateDetailKey(jobId, data.candidate_id),
        (old: applicationsApi.CandidateDetailResponse | undefined) =>
          old ? { ...old, application: data } : old,
      );
      void queryClient.invalidateQueries({
        queryKey: jobApplicationsKey(jobId),
      });
    },
  });
}

export function useJobApplications(jobId: string | undefined) {
  return useQuery({
    queryKey: jobId ? jobApplicationsKey(jobId) : ["jobApplications"],
    queryFn: () => applicationsApi.listJobApplications(jobId as string),
    enabled: !!jobId,
  });
}

export function useApplyToJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ApplyToJobRequest) => applicationsApi.applyToJob(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: MY_APPLICATIONS_KEY });
      void queryClient.invalidateQueries({ queryKey: ["recommendedJobs"] });
    },
  });
}

export function useMyApplications() {
  return useQuery({
    queryKey: MY_APPLICATIONS_KEY,
    queryFn: applicationsApi.listMyApplications,
  });
}

function onTransitionSuccess(
  queryClient: QueryClient,
  jobId: string,
  candidateId: string,
  data: ApplicationResponse,
) {
  queryClient.setQueryData(
    candidateDetailKey(jobId, candidateId),
    (old: applicationsApi.CandidateDetailResponse | undefined) =>
      old ? { ...old, application: data } : old,
  );
  void queryClient.invalidateQueries({ queryKey: jobApplicationsKey(jobId) });
}

function useTransition(
  action: (applicationId: string) => Promise<ApplicationResponse>,
  jobId: string,
  candidateId: string,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (applicationId: string) => action(applicationId),
    onSuccess: (data) =>
      onTransitionSuccess(queryClient, jobId, candidateId, data),
  });
}

export function useScreenApplication(jobId: string, candidateId: string) {
  return useTransition(applicationsApi.screenApplication, jobId, candidateId);
}

export function useInterviewApplication(jobId: string, candidateId: string) {
  return useTransition(
    applicationsApi.interviewApplication,
    jobId,
    candidateId,
  );
}

export function useOfferApplication(jobId: string, candidateId: string) {
  return useTransition(applicationsApi.offerApplication, jobId, candidateId);
}

export function useRejectApplication(jobId: string, candidateId: string) {
  return useTransition(applicationsApi.rejectApplication, jobId, candidateId);
}
