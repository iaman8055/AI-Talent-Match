"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { FileText, Loader2, Save, Upload, User } from "lucide-react";
import { useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  useCandidateProfile,
  useResumes,
  useUpdateProfile,
  useUploadResume,
} from "@/hooks/use-candidate";
import { ApiError } from "@/lib/api-client/client";
import type { CandidateResponse } from "@/lib/api-client/candidates";
import {
  updateProfileSchema,
  type UpdateProfileFormValues,
} from "@/lib/validators/candidate";

const STATUS_VARIANT: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  pending: "secondary",
  parsing: "secondary",
  parsed: "secondary",
  embedding: "secondary",
  ready: "default",
  failed: "destructive",
};

function ProfileDetailsCard({
  profile,
  updateProfile,
}: {
  profile: CandidateResponse;
  updateProfile: ReturnType<typeof useUpdateProfile>;
}) {
  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { isSubmitting, isDirty },
  } = useForm<UpdateProfileFormValues>({
    resolver: zodResolver(updateProfileSchema),
    defaultValues: {
      full_name: profile.full_name ?? "",
      headline: profile.headline ?? "",
      summary: profile.summary ?? "",
      skills: profile.skills,
      location: {
        country: profile.location.country ?? "",
        region: profile.location.region ?? "",
        city: profile.location.city ?? "",
      },
    },
  });

  // Controlled local text for the skills input — driven by RHF's parsed array via setValue on
  // change, not by defaultValue (which Base UI's FieldControl warns about if it ever changes on
  // an already-mounted input; this component instead remounts via a `key` on the profile's
  // updated_at whenever the underlying record legitimately changes).
  const [skillsText, setSkillsText] = useState(() => profile.skills.join(", "));
  const watchedSkills = useWatch({ control, name: "skills" }) ?? [];

  const onSubmit = async (values: UpdateProfileFormValues) => {
    try {
      await updateProfile.mutateAsync(values);
      toast.success("Profile updated");
    } catch {
      toast.error("Could not save changes. Please try again.");
    }
  };

  const onSkillsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSkillsText(event.target.value);
    const skills = event.target.value
      .split(",")
      .map((skill) => skill.trim())
      .filter(Boolean);
    setValue("skills", skills, { shouldDirty: true });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <Avatar size="lg">
            <AvatarFallback className="bg-primary/10 text-primary">
              <User className="size-5" />
            </AvatarFallback>
          </Avatar>
          <div>
            <CardTitle>Profile details</CardTitle>
            <CardDescription>
              Extracted from your resume automatically — edit anything at any
              time.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="full_name">Full name</Label>
              <Input id="full_name" {...register("full_name")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="headline">Headline</Label>
              <Input
                id="headline"
                placeholder="e.g. Senior Backend Engineer"
                {...register("headline")}
              />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="summary">Summary</Label>
            <Textarea id="summary" rows={4} {...register("summary")} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="skills">Skills (comma-separated)</Label>
            <Input id="skills" value={skillsText} onChange={onSkillsChange} />
            {watchedSkills.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {watchedSkills.map((skill) => (
                  <Badge key={skill} variant="secondary">
                    {skill}
                  </Badge>
                ))}
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="location.city">City</Label>
              <Input id="location.city" {...register("location.city")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="location.country">Country</Label>
              <Input id="location.country" {...register("location.country")} />
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

export default function CandidateProfilePage() {
  const { data: profile, isLoading: profileLoading } = useCandidateProfile();
  const updateProfile = useUpdateProfile();
  const { data: resumes, isLoading: resumesLoading } = useResumes();
  const uploadResume = useUploadResume();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const onFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      await uploadResume.mutateAsync(file);
      toast.success("Resume uploaded — parsing in the background");
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Upload failed. Please try again.",
      );
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  if (profileLoading || !profile) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-9 w-48" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Your profile"
        description="This is what recruiters see when you're matched to a job."
      />

      <ProfileDetailsCard
        key={profile.updated_at}
        profile={profile}
        updateProfile={updateProfile}
      />

      <Card>
        <CardHeader>
          <CardTitle>Resume</CardTitle>
          <CardDescription>
            Upload a PDF or DOCX resume. We&apos;ll parse it automatically and
            update your profile.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx"
              onChange={onFileSelected}
              className="hidden"
            />
            <Button
              type="button"
              variant="outline"
              disabled={uploadResume.isPending}
              onClick={() => fileInputRef.current?.click()}
            >
              {uploadResume.isPending ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Upload />
              )}
              {uploadResume.isPending ? "Uploading…" : "Upload resume"}
            </Button>
            <span className="text-xs text-muted-foreground">
              PDF or DOCX, up to 5MB
            </span>
          </div>

          <div className="flex flex-col gap-2">
            {resumesLoading && <Skeleton className="h-14 w-full" />}
            {!resumesLoading && (resumes ?? []).length === 0 && (
              <p className="text-sm text-muted-foreground">
                No resumes uploaded yet.
              </p>
            )}
            {(resumes ?? []).map((resume) => (
              <div
                key={resume.id}
                className="flex items-center gap-3 rounded-lg border p-3 text-sm"
              >
                <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted">
                  <FileText className="size-4 text-muted-foreground" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">
                    {resume.original_filename}{" "}
                    <span className="text-muted-foreground">
                      (v{resume.version})
                    </span>
                  </p>
                  {resume.error_message && (
                    <p className="text-destructive">{resume.error_message}</p>
                  )}
                </div>
                <Badge variant={STATUS_VARIANT[resume.status] ?? "outline"}>
                  {resume.status}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
