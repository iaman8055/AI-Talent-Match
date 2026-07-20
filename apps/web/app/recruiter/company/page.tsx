"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Save, Target, UserPlus, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
import { StatCard } from "@/components/dashboard/stat-card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
  const [inviteOpen, setInviteOpen] = useState(false);

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
      <div className="flex flex-col gap-6">
        <Skeleton className="h-9 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const onSaveDetails = async (values: UpdateCompanyFormValues) => {
    try {
      await updateCompany.mutateAsync({ companyId: company.id, body: values });
      toast.success("Company updated");
    } catch {
      toast.error("Could not save changes. Please try again.");
    }
  };

  const onInvite = async (values: InviteMemberFormValues) => {
    try {
      await inviteMember.mutateAsync(values);
      toast.success(`Invite sent to ${values.email}`);
      inviteForm.reset({ email: "", role: "member" });
      setInviteOpen(false);
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Could not send invite. Please try again.",
      );
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Company"
        description="Manage your company profile, matching threshold, and team."
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard icon={Users} label="Members" value={(members ?? []).length} />
        <StatCard
          icon={Target}
          label="Match threshold"
          value={`${company.match_threshold}%`}
        />
      </div>

      <Card className="max-w-2xl">
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
            <Button
              type="submit"
              disabled={detailsForm.formState.isSubmitting}
              className="w-fit"
            >
              {detailsForm.formState.isSubmitting ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Save />
              )}
              {detailsForm.formState.isSubmitting ? "Saving…" : "Save changes"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Members</CardTitle>
              <CardDescription>
                Everyone with access to this company&apos;s jobs and candidates.
              </CardDescription>
            </div>
            <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
              <DialogTrigger
                render={
                  <Button size="sm">
                    <UserPlus />
                    Invite
                  </Button>
                }
              />
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Invite a teammate</DialogTitle>
                  <DialogDescription>
                    They&apos;ll receive an email with a link to join.
                  </DialogDescription>
                </DialogHeader>
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
                  <Button
                    type="submit"
                    disabled={inviteForm.formState.isSubmitting}
                    className="w-fit"
                  >
                    {inviteForm.formState.isSubmitting ? (
                      <Loader2 className="animate-spin" />
                    ) : (
                      <UserPlus />
                    )}
                    {inviteForm.formState.isSubmitting
                      ? "Sending…"
                      : "Send invite"}
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {membersLoading && <Skeleton className="h-24 w-full" />}
          {!membersLoading && (members ?? []).length === 0 && (
            <p className="text-sm text-muted-foreground">No members yet.</p>
          )}
          {!membersLoading && (members ?? []).length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Member</TableHead>
                  <TableHead>Role</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(members ?? []).map((member) => (
                  <TableRow key={member.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Avatar size="sm">
                          <AvatarFallback className="bg-primary/10 text-primary">
                            {member.user_id.slice(0, 2).toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <span className="font-mono text-xs text-muted-foreground">
                          {member.user_id}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {member.role}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
