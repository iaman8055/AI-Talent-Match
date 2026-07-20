"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useRef, useState } from "react";
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
import { Textarea } from "@/components/ui/textarea";
import {
  useCandidateProfile,
  useResumes,
  useUpdateProfile,
  useUploadResume,
} from "@/hooks/use-candidate";
import { ApiError } from "@/lib/api-client/client";
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

export default function CandidateProfilePage() {
  const { data: profile, isLoading: profileLoading } = useCandidateProfile();
  const updateProfile = useUpdateProfile();
  const { data: resumes } = useResumes();
  const uploadResume = useUploadResume();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [skillsText, setSkillsText] = useState("");

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { isSubmitting },
  } = useForm<UpdateProfileFormValues>({
    resolver: zodResolver(updateProfileSchema),
  });

  useEffect(() => {
    if (!profile) return;
    reset({
      full_name: profile.full_name ?? "",
      headline: profile.headline ?? "",
      summary: profile.summary ?? "",
      skills: profile.skills,
      location: {
        country: profile.location.country ?? "",
        region: profile.location.region ?? "",
        city: profile.location.city ?? "",
      },
    });
    setSkillsText(profile.skills.join(", "));
  }, [profile, reset]);

  const onSubmit = async (values: UpdateProfileFormValues) => {
    await updateProfile.mutateAsync(values);
  };

  const onSkillsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSkillsText(event.target.value);
    const skills = event.target.value
      .split(",")
      .map((skill) => skill.trim())
      .filter(Boolean);
    setValue("skills", skills, { shouldDirty: true });
  };

  const onFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    try {
      await uploadResume.mutateAsync(file);
    } catch (error) {
      setUploadError(
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
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading profile…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold">Your profile</h1>

      <Card>
        <CardHeader>
          <CardTitle>Profile details</CardTitle>
          <CardDescription>
            These fields are extracted from your resume automatically, and you
            can edit any of them at any time.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="full_name">Full name</Label>
              <Input id="full_name" {...register("full_name")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="headline">Headline</Label>
              <Input id="headline" {...register("headline")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="summary">Summary</Label>
              <Textarea id="summary" rows={4} {...register("summary")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="skills">Skills (comma-separated)</Label>
              <Input
                id="skills"
                value={skillsText}
                onChange={onSkillsChange}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="location.city">City</Label>
                <Input id="location.city" {...register("location.city")} />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="location.country">Country</Label>
                <Input
                  id="location.country"
                  {...register("location.country")}
                />
              </div>
            </div>
            {updateProfile.isError && (
              <p className="text-sm text-destructive">
                Could not save changes. Please try again.
              </p>
            )}
            <Button type="submit" disabled={isSubmitting} className="w-fit">
              {isSubmitting ? "Saving…" : "Save changes"}
            </Button>
          </form>
        </CardContent>
      </Card>

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
              className="text-sm"
            />
            {uploadResume.isPending && (
              <span className="text-sm text-muted-foreground">Uploading…</span>
            )}
          </div>
          {uploadError && (
            <p className="text-sm text-destructive">{uploadError}</p>
          )}

          <div className="flex flex-col gap-2">
            {(resumes ?? []).length === 0 && (
              <p className="text-sm text-muted-foreground">
                No resumes uploaded yet.
              </p>
            )}
            {(resumes ?? []).map((resume) => (
              <div
                key={resume.id}
                className="flex items-center justify-between rounded-lg border p-3 text-sm"
              >
                <div>
                  <p className="font-medium">
                    {resume.original_filename} (v{resume.version})
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
