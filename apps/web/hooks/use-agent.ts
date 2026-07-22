"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as agentApi from "@/lib/api-client/agent";
import type { UpdateAgentConfigRequest } from "@/lib/api-client/agent";

const CONFIG_QUERY_KEY = ["agent", "config"];
const DECISIONS_QUERY_KEY = ["agent", "decisions"];

export function useAgentConfig() {
  return useQuery({
    queryKey: CONFIG_QUERY_KEY,
    queryFn: agentApi.getMyAgentConfig,
  });
}

export function useUpdateAgentConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateAgentConfigRequest) =>
      agentApi.updateMyAgentConfig(body),
    onSuccess: (data) => {
      queryClient.setQueryData(CONFIG_QUERY_KEY, data);
    },
  });
}

export function useAgentDecisions() {
  return useQuery({
    queryKey: DECISIONS_QUERY_KEY,
    queryFn: agentApi.listMyAgentDecisions,
  });
}
