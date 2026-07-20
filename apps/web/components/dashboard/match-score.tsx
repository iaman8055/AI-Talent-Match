import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

// Targets the Progress primitive's internal indicator by its data-slot attribute — the
// shadcn `Progress` wrapper always renders its own default track+indicator as siblings of
// `children`, so color can't be overridden by passing custom children; an attribute-selector
// override on a wrapping element is the supported escape hatch here.
function scoreColorClass(score: number): string {
  if (score >= 80) return "**:data-[slot=progress-indicator]:bg-emerald-500";
  if (score >= 60) return "**:data-[slot=progress-indicator]:bg-primary";
  if (score >= 40) return "**:data-[slot=progress-indicator]:bg-amber-500";
  return "**:data-[slot=progress-indicator]:bg-rose-500";
}

export function MatchScore({
  score,
  size = "sm",
  className,
}: {
  score: number;
  size?: "sm" | "lg";
  className?: string;
}) {
  const rounded = Math.round(score);

  if (size === "lg") {
    return (
      <div className={cn("flex flex-col gap-2", className)}>
        <div className="flex items-baseline justify-between">
          <span className="text-sm font-medium text-muted-foreground">
            Overall match
          </span>
          <span className="text-3xl font-semibold tabular-nums">
            {rounded}%
          </span>
        </div>
        <Progress
          value={rounded}
          className={cn(
            "**:data-[slot=progress-track]:h-2",
            scoreColorClass(rounded),
          )}
        />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex w-28 items-center gap-2",
        className,
        scoreColorClass(rounded),
      )}
    >
      <Progress value={rounded} className="flex-1" />
      <span className="w-9 shrink-0 text-right text-xs font-medium tabular-nums">
        {rounded}%
      </span>
    </div>
  );
}
