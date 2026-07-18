"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as candidatesApi from "@/lib/api-client/candidates";
import type {
  ResumeResponse,
  UpdateProfileRequest,
} from "@/lib/api-client/candidates";

const PROFILE_QUERY_KEY = ["candidate", "profile"];
const RESUMES_QUERY_KEY = ["candidate", "resumes"];
const TERMINAL_RESUME_STATUSES = new Set(["ready", "failed"]);

export function useCandidateProfile() {
  return useQuery({
    queryKey: PROFILE_QUERY_KEY,
    queryFn: candidatesApi.getMyProfile,
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateProfileRequest) =>
      candidatesApi.updateMyProfile(body),
    onSuccess: (data) => {
      queryClient.setQueryData(PROFILE_QUERY_KEY, data);
    },
  });
}

export function useResumes() {
  return useQuery({
    queryKey: RESUMES_QUERY_KEY,
    queryFn: candidatesApi.listMyResumes,
    refetchInterval: (query) => {
      const resumes = (query.state.data ?? []) as ResumeResponse[];
      const hasPending = resumes.some(
        (r) => !TERMINAL_RESUME_STATUSES.has(r.status),
      );
      return hasPending ? 3000 : false;
    },
  });
}

export function useUploadResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => candidatesApi.uploadResume(file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: RESUMES_QUERY_KEY });
    },
  });
}
