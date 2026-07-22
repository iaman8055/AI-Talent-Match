"use client";

import { Loader2, Mail, Pencil, Send, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/dashboard/empty-state";
import { PageHeader } from "@/components/dashboard/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
import { Textarea } from "@/components/ui/textarea";
import {
  useDiscardOutreachDraft,
  useOutreachDrafts,
  useSendOutreachDraft,
  useUpdateOutreachDraft,
} from "@/hooks/use-outreach";
import { ApiError } from "@/lib/api-client/client";
import type { OutreachDraftResponse } from "@/lib/api-client/outreach";

const STATUS_VARIANT: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  draft: "secondary",
  sent: "default",
  discarded: "outline",
};

export default function OutreachPage() {
  const { data: drafts, isLoading } = useOutreachDrafts();
  const updateDraft = useUpdateOutreachDraft();
  const sendDraft = useSendOutreachDraft();
  const discardDraft = useDiscardOutreachDraft();

  const [editing, setEditing] = useState<OutreachDraftResponse | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  const openEditor = (draft: OutreachDraftResponse) => {
    setEditing(draft);
    setSubject(draft.subject);
    setBody(draft.body);
  };

  const onSave = async () => {
    if (!editing) return;
    try {
      await updateDraft.mutateAsync({
        draftId: editing.id,
        body: { subject, body },
      });
      toast.success("Draft saved");
      setEditing(null);
    } catch {
      toast.error("Could not save changes. Please try again.");
    }
  };

  const onSend = async (draftId: string) => {
    try {
      await sendDraft.mutateAsync(draftId);
      toast.success("Outreach email sent");
      setEditing(null);
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.message
          : "Could not send. Please try again.",
      );
    }
  };

  const onDiscard = async (draftId: string) => {
    try {
      await discardDraft.mutateAsync(draftId);
      toast.success("Draft discarded");
    } catch {
      toast.error("Could not discard. Please try again.");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Outreach"
        description="AI-drafted outreach messages for candidates who newly cleared your match threshold. Nothing is ever sent without your review."
      />

      {isLoading && <Skeleton className="h-64 w-full" />}

      {!isLoading && (drafts ?? []).length === 0 && (
        <EmptyState
          icon={Mail}
          title="No outreach drafts yet"
          description="When a candidate newly clears one of your jobs' match thresholds, a draft outreach message shows up here for you to review."
        />
      )}

      {!isLoading && (drafts ?? []).length > 0 && (
        <Card>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Candidate</TableHead>
                  <TableHead>Job</TableHead>
                  <TableHead>Subject</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(drafts ?? []).map((draft) => (
                  <TableRow key={draft.id}>
                    <TableCell className="font-medium">
                      {draft.candidate_name}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {draft.job_title}
                    </TableCell>
                    <TableCell className="max-w-xs truncate">
                      {draft.subject}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={STATUS_VARIANT[draft.status] ?? "outline"}
                        className="capitalize"
                      >
                        {draft.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {draft.status === "draft" && (
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openEditor(draft)}
                          >
                            <Pencil />
                            Review
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            disabled={discardDraft.isPending}
                            onClick={() => onDiscard(draft.id)}
                          >
                            <Trash2 />
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Dialog
        open={editing !== null}
        onOpenChange={(open) => !open && setEditing(null)}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Review outreach message</DialogTitle>
            <DialogDescription>{editing?.candidate_summary}</DialogDescription>
          </DialogHeader>
          {editing && (
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="outreach-subject">Subject</Label>
                <Input
                  id="outreach-subject"
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="outreach-body">Message</Label>
                <Textarea
                  id="outreach-body"
                  rows={8}
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              disabled={updateDraft.isPending}
              onClick={onSave}
            >
              {updateDraft.isPending ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Pencil />
              )}
              Save
            </Button>
            <Button
              disabled={sendDraft.isPending}
              onClick={() => editing && onSend(editing.id)}
            >
              {sendDraft.isPending ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Send />
              )}
              Send
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
