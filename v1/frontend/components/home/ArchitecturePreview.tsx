"use client";
import Link from "next/link";
import { useSimulation } from "@/lib/arch/useSimulation";
import ArchitectureDiagram from "@/components/architecture/ArchitectureDiagram";
import Caption from "@/components/architecture/Caption";
import Stepper from "@/components/architecture/Stepper";

/** Homepage version: plays by itself, read-only, with a link to the interactive page. */
export default function ArchitecturePreview() {
  const a = useSimulation({ initialSpeed: 0.5 });
  return (
    <section id="architecture" ref={a.wrapperRef} className="scroll-mt-24 space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-xl">
          <h2 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">Watch a video travel through the system.</h2>
          <p className="mt-3 leading-7 text-muted">
            Every chunk is a packet. It waits in Redis, gets picked up by a worker, is recorded in PostgreSQL and reaches your player.
            When you jump ahead, the queue re-orders itself.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={a.toggle}
            className="inline-flex items-center rounded-xl border border-ink/25 px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-ink hover:bg-ink/5"
          >
            {a.playing ? "Pause" : "Play"}
          </button>
          <Link href="/architecture" className="inline-flex items-center gap-2 rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-surface transition hover:bg-ink/85">
            Open the interactive version <span aria-hidden>&rarr;</span>
          </Link>
        </div>
      </div>

      <Stepper sim={a.sim} />
      <Caption sim={a.sim} />
      <ArchitectureDiagram
        sim={a.sim}
        shown={a.shown}
        selected={null}
        interactive={false}
        playing={a.playing}
        speed={a.speed}
        reduced={a.reduced}
        clockRef={a.clockRef}
        onSelect={a.select}
        onSeek={a.seekTo}
      />
    </section>
  );
}
