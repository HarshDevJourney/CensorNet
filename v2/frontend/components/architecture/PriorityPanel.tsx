import { PREFETCH, SCORE, fmtScore, tierCounts, type Sim, type Tier } from "@/lib/arch/engine";

const ROWS: { tier: Tier; name: string; score: string; when: string; dot: string }[] = [
  { tier: "stall", name: "STALL", score: `${fmtScore(SCORE.stall)} + d`, when: "the player is waiting for this very chunk", dot: "bg-accent" },
  { tier: "urgent", name: "URGENT", score: `${fmtScore(SCORE.urgent)} + d`, when: `the playhead chunk and the next ${PREFETCH - 1}`, dot: "bg-accent/60" },
  { tier: "ahead", name: "AHEAD", score: "d", when: "everything after the playhead, nearest first", dot: "bg-muted/50" },
  { tier: "behind", name: "BEHIND", score: `+${SCORE.behind.toLocaleString("en-US")} + |d|`, when: "already watched; only needed if you scrub back", dot: "bg-queued" },
];

/** The scoring rules, with a live count of how many queued chunks are in each tier. */
export default function PriorityPanel({ sim }: { sim: Sim }) {
  const counts = tierCounts(sim);
  return (
    <section className="rounded-2xl border border-line bg-surface p-5 sm:p-6" aria-label="Redis priority tiers">
      <h3 className="font-display text-xl font-semibold tracking-tight">
        <span className="text-redis">Redis</span> priority tiers
      </h3>
      <p className="mt-1 text-sm text-muted">
        Lowest score goes first. <span className="font-mono text-ink">d</span> = chunk &minus; playhead (now chunk{" "}
        <span className="font-mono text-ink">{sim.playhead}</span>). A seek re-scores every queued chunk in one command.
      </p>
      <ul className="mt-4 space-y-2.5">
        {ROWS.map((r) => (
          <li key={r.tier} className="grid grid-cols-[auto_1fr_auto] items-center gap-3 text-sm">
            <span className={`h-3 w-3 rounded-sm ${r.dot}`} />
            <div>
              <p className="font-semibold">
                {r.name} <span className="ml-1 font-mono text-xs font-normal text-muted">{r.score}</span>
              </p>
              <p className="text-xs text-muted">{r.when}</p>
            </div>
            <span className="min-w-[2rem] rounded-md bg-ink/5 px-2 py-1 text-center font-mono text-xs font-semibold" aria-label={`${counts[r.tier]} queued`}>
              {counts[r.tier]}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
