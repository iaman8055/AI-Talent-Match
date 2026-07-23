"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Bot, History, Loader2, Save } from "lucide-react";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { EmptyState } from "@/components/dashboard/empty-state";
import { PageHeader } from "@/components/dashboard/page-header";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useAgentConfig,
  useAgentDecisions,
  useUpdateAgentConfig,
} from "@/hooks/use-agent";
import type { AgentConfigResponse, WorkMode } from "@/lib/api-client/agent";
import {
  updateAgentConfigSchema,
  type UpdateAgentConfigFormValues,
} from "@/lib/validators/agent";

const WORK_MODE_OPTIONS: { value: WorkMode; label: string }[] = [
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "Onsite" },
];

function parseCommaList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function AgentPreferencesCard({
  config,
  updateConfig,
}: {
  config: AgentConfigResponse;
  updateConfig: ReturnType<typeof useUpdateAgentConfig>;
}) {
  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { isSubmitting, isDirty },
  } = useForm<UpdateAgentConfigFormValues>({
    resolver: zodResolver(updateAgentConfigSchema),
    defaultValues: {
      auto_apply_enabled: config.auto_apply_enabled,
      target_roles: config.target_roles,
      target_skills: config.target_skills,
      target_locations: config.target_locations,
      work_modes: config.work_modes,
      min_salary: config.min_salary ?? undefined,
      min_match_score: config.min_match_score,
      daily_apply_cap: config.daily_apply_cap,
    },
  });

  // Controlled local text for each comma-list field — see profile/page.tsx's ProfileDetailsCard
  // for why (Base UI's FieldControl warns if defaultValue changes on an already-mounted input;
  // this component instead remounts via a `key` on the config's updated_at when it truly changes).
  const [targetRolesText, setTargetRolesText] = useState(() =>
    config.target_roles.join(", "),
  );
  const [targetSkillsText, setTargetSkillsText] = useState(() =>
    config.target_skills.join(", "),
  );
  const [targetLocationsText, setTargetLocationsText] = useState(() =>
    config.target_locations.join(", "),
  );

  const autoApplyEnabled = useWatch({ control, name: "auto_apply_enabled" });
  const workModes = useWatch({ control, name: "work_modes" }) ?? [];

  const toggleWorkMode = (mode: WorkMode) => {
    const next = workModes.includes(mode)
      ? workModes.filter((m) => m !== mode)
      : [...workModes, mode];
    setValue("work_modes", next, { shouldDirty: true });
  };

  const onSubmit = async (values: UpdateAgentConfigFormValues) => {
    try {
      await updateConfig.mutateAsync(values);
      toast.success("Auto-apply settings saved");
    } catch {
      toast.error("Could not save settings. Please try again.");
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Bot className="size-4.5" />
          </div>
          <div>
            <CardTitle>Preferences</CardTitle>
            <CardDescription>
              Jobs are scanned every 15 minutes. Only jobs that clear all of
              these preferences and your minimum match score get applied to
              automatically.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5">
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div>
              <p className="text-sm font-medium">Enable auto-apply</p>
              <p className="text-sm text-muted-foreground">
                When off, the agent never applies on your behalf.
              </p>
            </div>
            <Switch
              checked={autoApplyEnabled ?? false}
              onCheckedChange={(checked) =>
                setValue("auto_apply_enabled", checked, { shouldDirty: true })
              }
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="flex flex-col gap-2">
              <Label htmlFor="min_match_score">Minimum match score (%)</Label>
              <Input
                id="min_match_score"
                type="number"
                min={0}
                max={100}
                {...register("min_match_score", { valueAsNumber: true })}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="daily_apply_cap">Daily apply cap</Label>
              <Input
                id="daily_apply_cap"
                type="number"
                min={1}
                max={100}
                {...register("daily_apply_cap", { valueAsNumber: true })}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="min_salary">Minimum salary (optional)</Label>
              <Input
                id="min_salary"
                type="number"
                min={0}
                {...register("min_salary", { valueAsNumber: true })}
              />
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="target_roles">Target roles (comma-separated)</Label>
            <Input
              id="target_roles"
              placeholder="e.g. Backend Engineer, Platform Engineer"
              value={targetRolesText}
              onChange={(event) => {
                setTargetRolesText(event.target.value);
                setValue("target_roles", parseCommaList(event.target.value), {
                  shouldDirty: true,
                });
              }}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="target_skills">
              Target skills (comma-separated)
            </Label>
            <Input
              id="target_skills"
              placeholder="e.g. Python, Kubernetes"
              value={targetSkillsText}
              onChange={(event) => {
                setTargetSkillsText(event.target.value);
                setValue("target_skills", parseCommaList(event.target.value), {
                  shouldDirty: true,
                });
              }}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="target_locations">
              Target locations (comma-separated)
            </Label>
            <Input
              id="target_locations"
              placeholder="e.g. United States, Remote"
              value={targetLocationsText}
              onChange={(event) => {
                setTargetLocationsText(event.target.value);
                setValue(
                  "target_locations",
                  parseCommaList(event.target.value),
                  { shouldDirty: true },
                );
              }}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label>Accepted work modes (any, if none selected)</Label>
            <div className="flex flex-wrap gap-2">
              {WORK_MODE_OPTIONS.map((option) => {
                const selected = workModes.includes(option.value);
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => toggleWorkMode(option.value)}
                    className="focus-visible:outline-none"
                  >
                    <Badge variant={selected ? "default" : "outline"}>
                      {option.label}
                    </Badge>
                  </button>
                );
              })}
            </div>
          </div>

          <Button
            type="submit"
            disabled={isSubmitting || !isDirty}
            className="w-fit"
          >
            {isSubmitting ? <Loader2 className="animate-spin" /> : <Save />}
            {isSubmitting ? "Saving…" : "Save changes"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function AgentPage() {
  const { data: config, isLoading: configLoading } = useAgentConfig();
  const updateConfig = useUpdateAgentConfig();
  const { data: decisions, isLoading: decisionsLoading } = useAgentDecisions();

  if (configLoading || !config) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Auto-Apply Agent"
        description="Configure autonomous job applications. Every decision — applied or skipped — is logged below."
      />

      <AgentPreferencesCard
        key={config.updated_at}
        config={config}
        updateConfig={updateConfig}
      />

      <div className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Decision history</h2>

        {decisionsLoading && <Skeleton className="h-48 w-full" />}

        {!decisionsLoading && (decisions ?? []).length === 0 && (
          <EmptyState
            icon={History}
            title="No decisions yet"
            description="Once the agent evaluates a newly published job against your preferences, applied and skipped decisions will show up here."
          />
        )}

        {!decisionsLoading && (decisions ?? []).length > 0 && (
          <Card>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Job</TableHead>
                    <TableHead>Decision</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead className="text-right">Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(decisions ?? []).map((decision) => (
                    <TableRow key={decision.id}>
                      <TableCell className="font-medium whitespace-normal">
                        {decision.job_title}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            decision.action === "applied"
                              ? "default"
                              : "secondary"
                          }
                        >
                          {decision.action === "applied"
                            ? "Applied"
                            : "Skipped"}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-md whitespace-normal text-muted-foreground">
                        {decision.reason}
                      </TableCell>
                      <TableCell className="text-right text-muted-foreground">
                        {new Date(decision.decided_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
