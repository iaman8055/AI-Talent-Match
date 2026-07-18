import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 bg-zinc-50 dark:bg-black">
      <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">
        AI Talent Match
      </h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        AI-first recruiting platform for candidates and recruiters.
      </p>
      <div className="flex gap-3">
        <Link href="/login" className={buttonVariants({ variant: "default" })}>
          Log in
        </Link>
        <Link
          href="/register"
          className={buttonVariants({ variant: "outline" })}
        >
          Sign up
        </Link>
      </div>
    </div>
  );
}
