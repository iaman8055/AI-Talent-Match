import { apiFetch } from "./client";
import type { components } from "./schema";

export type CompanyResponse = components["schemas"]["CompanyResponse"];
export type CompanyMemberResponse =
  components["schemas"]["CompanyMemberResponse"];
export type CompanyInviteResponse =
  components["schemas"]["CompanyInviteResponse"];
export type UpdateCompanyRequest =
  components["schemas"]["UpdateCompanyRequest"];
export type InviteMemberRequest = components["schemas"]["InviteMemberRequest"];

export async function listMyCompanies(): Promise<CompanyResponse[]> {
  return apiFetch<CompanyResponse[]>("/companies/me");
}

export async function updateCompany(
  companyId: string,
  body: UpdateCompanyRequest,
): Promise<CompanyResponse> {
  return apiFetch<CompanyResponse>(`/companies/${companyId}`, {
    method: "PATCH",
    body,
  });
}

export async function listCompanyMembers(
  companyId: string,
): Promise<CompanyMemberResponse[]> {
  return apiFetch<CompanyMemberResponse[]>(`/companies/${companyId}/members`);
}

export async function inviteMember(
  companyId: string,
  body: InviteMemberRequest,
): Promise<CompanyInviteResponse> {
  return apiFetch<CompanyInviteResponse>(`/companies/${companyId}/members`, {
    method: "POST",
    body,
  });
}
