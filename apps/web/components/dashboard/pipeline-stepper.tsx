import { CheckIcon, XCircleIcon } from "lucide-react";

import { cn } from "@/lib/utils";

const STAGES = [
  { key: "invited", label: "Invited" },
  { key: "applied", label: "Applied" },
  { key: "screening", label: "Screening" },
  { key: "interview", label: "Interview" },
  { key: "offer", label: "Offer" },
] as const;

type Stage = (typeof STAGES)[number]["key"];

export function PipelineStepper({ status }: { status: string }) {
  if (status === "rejected") {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
        <XCircleIcon className="size-4 shrink-0" />
        <span className="font-medium">Rejected</span>
      </div>
    );
  }

  const currentIndex = STAGES.findIndex((stage) => stage.key === status);

  return (
    <div className="flex items-center">
      {STAGES.map((stage, index) => {
        const isComplete = index < currentIndex;
        const isCurrent = index === currentIndex;
        return (
          <div
            key={stage.key}
            className="flex items-center last:flex-none flex-1"
          >
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={cn(
                  "flex size-6 shrink-0 items-center justify-center rounded-full border-2 text-xs font-medium",
                  isComplete &&
                    "border-primary bg-primary text-primary-foreground",
                  isCurrent && "border-primary text-primary",
                  !isComplete &&
                    !isCurrent &&
                    "border-muted-foreground/30 text-muted-foreground",
                )}
              >
                {isComplete ? <CheckIcon className="size-3.5" /> : index + 1}
              </div>
              <span
                className={cn(
                  "text-[11px] whitespace-nowrap",
                  isCurrent
                    ? "font-medium text-foreground"
                    : "text-muted-foreground",
                )}
              >
                {stage.label}
              </span>
            </div>
            {index < STAGES.length - 1 && (
              <div
                className={cn(
                  "mx-1.5 h-0.5 flex-1 rounded-full",
                  isComplete ? "bg-primary" : "bg-muted",
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export function PipelineBadgeCompact({ status }: { status: string }) {
  if (status === "rejected") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-destructive">
        <XCircleIcon className="size-3.5" />
        Rejected
      </span>
    );
  }
  const index = STAGES.findIndex((stage) => stage.key === status);
  const label = STAGES[index]?.label ?? status;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
      <span className="flex size-1.5 rounded-full bg-primary" />
      {label}
    </span>
  );
}

export type { Stage };
