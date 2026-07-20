"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useCompanyMembers,
  useInviteMember,
  useMyCompany,
  useUpdateCompany,
} from "@/hooks/use-company";
import { ApiError } from "@/lib/api-client/client";
import {
  inviteMemberSchema,
  updateCompanySchema,
  type InviteMemberFormValues,
  type UpdateCompanyFormValues,
} from "@/lib/validators/company";

export default function CompanyPage() {
  const { company, isLoading: companyLoading } = useMyCompany();
  const updateCompany = useUpdateCompany();
  const { data: members, isLoading: membersLoading } = useCompanyMembers(
    company?.id,
  );
  const inviteMember = useInviteMember(company?.id);

  const [detailsError, setDetailsError] = useState<string | null>(null);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null);

  const detailsForm = useForm<UpdateCompanyFormValues>({
    resolver: zodResolver(updateCompanySchema),
  });

  useEffect(() => {
    if (!company) return;
    detailsForm.reset({
      name: company.name,
      match_threshold: company.match_threshold,
    });
  }, [company, detailsForm]);

  const inviteForm = useForm<InviteMemberFormValues>({
    resolver: zodResolver(inviteMemberSchema),
    defaultValues: { role: "member" },
  });

  if (companyLoading || !company) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading company…</p>
      </div>
    );
  }

  const onSaveDetails = async (values: UpdateCompanyFormValues) => {
    setDetailsError(null);
    try {
      await updateCompany.mutateAsync({ companyId: company.id, body: values });
    } catch (error) {
      setDetailsError(
        error instanceof ApiError
          ? error.message
          : "Could not save changes. Please try again.",
      );
    }
  };

  const onInvite = async (values: InviteMemberFormValues) => {
    setInviteError(null);
    setInviteSuccess(null);
    try {
      await inviteMember.mutateAsync(values);
      setInviteSuccess(`Invite sent to ${values.email}.`);
      inviteForm.reset({ email: "", role: "member" });
    } catch (error) {
      setInviteError(
        error instanceof ApiError
          ? error.message
          : "Could not send invite. Please try again.",
      );
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold">Company</h1>

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
          <CardDescription>
            The match threshold controls how high a candidate&apos;s score must
            be before they show up in your ranked candidates list.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={detailsForm.handleSubmit(onSaveDetails)}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">Company name</Label>
              <Input id="name" {...detailsForm.register("name")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="match_threshold">Match threshold (%)</Label>
              <Input
                id="match_threshold"
                type="number"
                min={0}
                max={100}
                {...detailsForm.register("match_threshold", {
                  valueAsNumber: true,
                })}
              />
            </div>
            {detailsError && (
              <p className="text-sm text-destructive">{detailsError}</p>
            )}
            <Button
              type="submit"
              disabled={detailsForm.formState.isSubmitting}
              className="w-fit"
            >
              {detailsForm.formState.isSubmitting ? "Saving…" : "Save changes"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {membersLoading && (
            <p className="text-sm text-muted-foreground">Loading members…</p>
          )}
          {!membersLoading && (members ?? []).length === 0 && (
            <p className="text-sm text-muted-foreground">No members yet.</p>
          )}
          {(members ?? []).map((member) => (
            <div
              key={member.id}
              className="flex items-center justify-between rounded-lg border p-3 text-sm"
            >
              <span>{member.user_id}</span>
              <Badge variant="outline">{member.role}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Invite a teammate</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={inviteForm.handleSubmit(onInvite)}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="invite-email">Email</Label>
              <Input
                id="invite-email"
                type="email"
                {...inviteForm.register("email")}
              />
              {inviteForm.formState.errors.email && (
                <p className="text-sm text-destructive">
                  {inviteForm.formState.errors.email.message}
                </p>
              )}
            </div>
            {inviteError && (
              <p className="text-sm text-destructive">{inviteError}</p>
            )}
            {inviteSuccess && (
              <p className="text-sm text-muted-foreground">{inviteSuccess}</p>
            )}
            <Button
              type="submit"
              disabled={inviteForm.formState.isSubmitting}
              className="w-fit"
            >
              {inviteForm.formState.isSubmitting ? "Sending…" : "Send invite"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
