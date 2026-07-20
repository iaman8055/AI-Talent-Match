"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { NavBar } from "@/components/nav-bar";
import { useAuth } from "@/hooks/use-auth";

export default function RecruiterLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login");
    } else if (user.role !== "recruiter") {
      router.replace("/profile");
    }
  }, [isLoading, user, router]);

  if (isLoading || !user || user.role !== "recruiter") {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <>
      <NavBar />
      {children}
    </>
  );
}
