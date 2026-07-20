"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const CANDIDATE_LINKS = [
  { href: "/profile", label: "Profile" },
  { href: "/jobs", label: "Recommended jobs" },
  { href: "/applications", label: "My applications" },
];

const RECRUITER_LINKS = [
  { href: "/recruiter/jobs", label: "Jobs" },
  { href: "/recruiter/company", label: "Company" },
];

export function NavBar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  if (!user) return null;

  const links = user.role === "candidate" ? CANDIDATE_LINKS : RECRUITER_LINKS;

  return (
    <header className="border-b bg-background">
      <div className="mx-auto flex max-w-5xl items-center justify-between p-4">
        <div className="flex items-center gap-6">
          <span className="font-semibold">AI Talent Match</span>
          <nav className="flex gap-4 text-sm">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "text-muted-foreground hover:text-foreground",
                  pathname === link.href && "font-medium text-foreground",
                )}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
        <Button variant="outline" onClick={logout}>
          Log out
        </Button>
      </div>
    </header>
  );
}
