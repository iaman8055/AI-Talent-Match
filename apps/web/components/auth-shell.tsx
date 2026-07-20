import { Sparkles } from "lucide-react";
import type { ReactNode } from "react";

const HIGHLIGHTS = [
  "Semantic matching across resumes and job descriptions",
  "Explainable scores — skill, experience, salary, and location fit",
  "A full hiring pipeline from invite to offer",
];

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-svh flex-1">
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-sidebar p-10 text-sidebar-foreground lg:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            background:
              "radial-gradient(60% 50% at 20% 0%, color-mix(in oklch, var(--primary), transparent 82%), transparent)",
          }}
        />
        <div className="relative flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Sparkles className="size-4.5" />
          </div>
          <span className="font-heading text-lg font-semibold">
            AI Talent Match
          </span>
        </div>
        <div className="relative flex flex-col gap-6">
          <p className="max-w-sm text-2xl font-medium text-balance">
            Semantic matching that explains itself, for candidates and
            recruiters alike.
          </p>
          <ul className="flex flex-col gap-3">
            {HIGHLIGHTS.map((highlight) => (
              <li
                key={highlight}
                className="flex items-start gap-2 text-sm text-sidebar-foreground/80"
              >
                <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" />
                {highlight}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-sidebar-foreground/50">
          &copy; {new Date().getFullYear()} AI Talent Match
        </p>
      </div>
      <div className="flex w-full flex-1 items-center justify-center bg-background p-4 lg:w-1/2">
        {children}
      </div>
    </div>
  );
}
