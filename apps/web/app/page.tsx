import { Briefcase, Sparkles, Target, Zap } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const FEATURES = [
  {
    icon: Target,
    title: "Semantic matching",
    description:
      "Candidates and jobs are ranked by meaning, not keywords — powered by embeddings and a reranking model.",
  },
  {
    icon: Zap,
    title: "Explainable scores",
    description:
      "Every match breaks down into skill overlap, experience fit, salary fit, and location fit.",
  },
  {
    icon: Briefcase,
    title: "Built-in pipeline",
    description:
      "Invite, screen, interview, and offer — track every candidate's status in one place.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <div className="relative flex flex-1 flex-col items-center justify-center overflow-hidden px-4 py-24">
        <div
          className="pointer-events-none absolute inset-0 -z-10 opacity-60"
          style={{
            background:
              "radial-gradient(60% 50% at 50% 0%, color-mix(in oklch, var(--primary), transparent 88%), transparent)",
          }}
        />
        <div className="flex flex-col items-center gap-6 text-center">
          <div className="flex items-center gap-2 rounded-full border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
            <Sparkles className="size-3.5 text-primary" />
            AI-first recruiting
          </div>
          <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            Find the right match, not just the right keywords
          </h1>
          <p className="max-w-lg text-balance text-muted-foreground">
            AI Talent Match pairs candidates and recruiters using semantic
            resume and job matching — with a fully transparent, explainable
            score behind every recommendation.
          </p>
          <div className="flex gap-3">
            <Link href="/register" className={buttonVariants({ size: "lg" })}>
              Get started
            </Link>
            <Link
              href="/login"
              className={buttonVariants({ variant: "outline", size: "lg" })}
            >
              Log in
            </Link>
          </div>
        </div>

        <div className="mt-20 grid w-full max-w-4xl gap-4 sm:grid-cols-3">
          {FEATURES.map((feature) => (
            <Card key={feature.title}>
              <CardContent className="flex flex-col gap-3">
                <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <feature.icon className="size-4.5" />
                </div>
                <div className="flex flex-col gap-1">
                  <p className="font-medium">{feature.title}</p>
                  <p className="text-sm text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
