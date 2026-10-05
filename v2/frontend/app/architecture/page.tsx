import type { Metadata } from "next";
import ArchitectureLab from "@/components/architecture/ArchitectureLab";

export const metadata: Metadata = {
  title: "Architecture | CensorNet",
  description: "An interactive animation of how CensorNet moves video chunks through Redis, workers and PostgreSQL.",
};

export default function ArchitecturePage() {
  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface/70 px-3 py-1 text-xs font-medium text-muted backdrop-blur">
          <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-accent" />
          Interactive architecture
        </span>
        <h1 className="mt-5 font-display text-4xl font-semibold leading-[1.02] tracking-[-0.03em] sm:text-6xl">
          How the system <span className="text-gradient">works</span>
        </h1>
        <p className="mt-5 text-lg leading-8 text-muted">
          A video is cut into small chunks. <span className="text-redis font-medium">Redis</span> decides which chunk is censored next,
          separate <span className="font-medium text-accent">workers</span> do the work, and{" "}
          <span className="text-pg font-medium">PostgreSQL</span> keeps the permanent record of every chunk. Jump around in the player and
          watch the queue follow you.
        </p>
      </header>
      <ArchitectureLab />
    </div>
  );
}
