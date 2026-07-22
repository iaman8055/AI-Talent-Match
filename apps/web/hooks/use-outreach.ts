"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as outreachApi from "@/lib/api-client/outreach";
import type { UpdateOutreachDraftRequest } from "@/lib/api-client/outreach";

const OUTREACH_DRAFTS_KEY = ["outreachDrafts"];

export function useOutreachDrafts() {
  return useQuery({
    queryKey: OUTREACH_DRAFTS_KEY,
    queryFn: () => outreachApi.listOutreachDrafts(),
  });
}

export function useUpdateOutreachDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      draftId,
      body,
    }: {
      draftId: string;
      body: UpdateOutreachDraftRequest;
    }) => outreachApi.updateOutreachDraft(draftId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: OUTREACH_DRAFTS_KEY });
    },
  });
}

export function useSendOutreachDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (draftId: string) => outreachApi.sendOutreachDraft(draftId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: OUTREACH_DRAFTS_KEY });
    },
  });
}

export function useDiscardOutreachDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (draftId: string) => outreachApi.discardOutreachDraft(draftId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: OUTREACH_DRAFTS_KEY });
    },
  });
}
