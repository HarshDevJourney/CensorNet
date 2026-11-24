import { tickToSeconds, type LogTone, type Sim } from "@/lib/arch/engine";

const TONE: Record<LogTone, string> = {
  info: "text-muted",
  queue: "text-redis",
  db: "text-pg",
  worker: "text-accent",
  play: "text-ready",
  seek: "text-working",
};

/** The last few commands, as they would appear in the Redis / PostgreSQL / API logs. */
export default function EventLog({ sim, rows = 7 }: { sim: Sim; rows?: number }) {
  const lines = sim.log.slice(-rows).reverse();
  return (
    <section className="rounded-2xl border border-line bg-surface p-5 sm:p-6" aria-label="Event log">
      <h3 className="font-display text-xl font-semibold tracking-tight">What just ran</h3>
      <ul className="mt-3 space-y-1.5 font-mono text-[11.5px] leading-5">
        {lines.length === 0 && <li className="text-muted">nothing yet</li>}
        {lines.map((l, i) => (
          <li key={`${l.tick}-${i}`} className={`flex gap-3 ${i === 0 ? "" : "opacity-80"}`}>
            <span className="w-10 shrink-0 text-muted/80">{tickToSeconds(l.tick).toFixed(1)}s</span>
            <span className={TONE[l.tone]}>{l.text}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
