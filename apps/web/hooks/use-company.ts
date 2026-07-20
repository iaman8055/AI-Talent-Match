"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as companiesApi from "@/lib/api-client/companies";
import type {
  InviteMemberRequest,
  UpdateCompanyRequest,
} from "@/lib/api-client/companies";

const MY_COMPANIES_KEY = ["companies", "me"];
const membersKey = (companyId: string) => ["companies", companyId, "members"];

export function useMyCompanies() {
  return useQuery({
    queryKey: MY_COMPANIES_KEY,
    queryFn: companiesApi.listMyCompanies,
  });
}

/** Assumes a single company per user — correct for both the register-creates-one-company path
 * and the invite-into-an-existing-company path; there's no company switcher in the product yet. */
export function useMyCompany() {
  const { data: companies, ...rest } = useMyCompanies();
  return { company: companies?.[0], ...rest };
}

export function useUpdateCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      companyId,
      body,
    }: {
      companyId: string;
      body: UpdateCompanyRequest;
    }) => companiesApi.updateCompany(companyId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: MY_COMPANIES_KEY });
    },
  });
}

export function useCompanyMembers(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? membersKey(companyId) : ["companies", "members"],
    queryFn: () => companiesApi.listCompanyMembers(companyId as string),
    enabled: !!companyId,
  });
}

export function useInviteMember(companyId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: InviteMemberRequest) =>
      companiesApi.inviteMember(companyId as string, body),
    onSuccess: () => {
      if (!companyId) return;
      void queryClient.invalidateQueries({ queryKey: membersKey(companyId) });
    },
  });
}
