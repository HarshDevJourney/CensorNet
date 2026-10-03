import { LEASE_Y, QUEUE_W, QUEUE_X, SLOT_H, slotY } from "@/lib/arch/layout";
import { fmtScore, sortedQueue, type QueueEntry, type Sim, type Tier } from "@/lib/arch/engine";

const BAR: Record<Tier, string> = {
  prepare: "fill-working",
  stall: "fill-accent",
  urgent: "fill-accent/60",
  ahead: "fill-muted/45",
  behind: "fill-queued",
};
const TAG: Record<Tier, string> = { prepare: "PREPARE", stall: "STALL", urgent: "URGENT", ahead: "AHEAD", behind: "BEHIND" };
const TAG_CLS: Record<Tier, string> = {
  prepare: "fill-working",
  stall: "fill-accent",
  urgent: "fill-accent",
  ahead: "fill-muted",
  behind: "fill-muted/70",
};

function Entry({ e, rank, tick }: { e: QueueEntry; rank: number; tick: number }) {
  const fresh = tick - e.changedTick < 2 && e.changedTick > 0;
  const hot = e.tier === "stall" || e.tier === "urgent" || e.tier === "prepare";
  return (
    <g className="arch-move" style={{ transform: `translate(${QUEUE_X}px, ${slotY(rank)}px)` }}>
      <g className="arch-enter" style={{ animationDelay: `${e.kind === "chunk" ? e.index * 40 : 0}ms` }}>
        <rect width={QUEUE_W} height={SLOT_H} rx={7} className={`fill-surface ${hot ? "stroke-accent/50" : "stroke-line"}`} strokeWidth={1} />
        <rect x={0} y={0} width={5} height={SLOT_H} rx={2.5} className={BAR[e.tier]} />
        <text x={14} y={16} fontSize={11} fontWeight={600} className="fill-ink font-mono">{e.member}</text>
        <text x={76} y={15.5} fontSize={7.5} fontWeight={700} letterSpacing={0.5} className={TAG_CLS[e.tier]}>{TAG[e.tier]}</text>
        <text x={QUEUE_W - 8} y={16} fontSize={10.5} textAnchor="end" className="fill-ink font-mono">{fmtScore(e.score)}</text>
        {fresh && (
          <rect key={e.changedTick} width={QUEUE_W} height={SLOT_H} rx={7} fill="none" strokeWidth={2} className="arch-flash stroke-accent" />
        )}
      </g>
    </g>
  );
}

export default function RedisQueue({ sim }: { sim: Sim }) {
  const sorted = sortedQueue(sim);
  return (
    <g>
      <text x={QUEUE_X} y={101} fontSize={9.5} className="fill-muted font-mono">vc:queue · lowest score first</text>

      {/* empty slots, so the list always looks like a queue */}
      {Array.from({ length: 12 }).map((_, i) => (
        <rect key={i} x={QUEUE_X} y={slotY(i)} width={QUEUE_W} height={SLOT_H} rx={7} fill="none" strokeWidth={1} strokeDasharray="2 4" className="stroke-line" />
      ))}
      {sorted.length === 0 && (
        <text x={QUEUE_X + QUEUE_W / 2} y={slotY(3)} textAnchor="middle" fontSize={11} className="fill-muted">queue is empty</text>
      )}

      {sorted.map((e, rank) => (
        <Entry key={e.member} e={e} rank={rank} tick={sim.tick} />
      ))}

      {/* "next out" marker */}
      {sorted.length > 0 && (
        <path d={`M${QUEUE_X + QUEUE_W + 4} ${slotY(0) + 6} l7 6 l-7 6 z`} className="fill-accent" />
      )}

      {/* leases */}
      <text x={QUEUE_X} y={LEASE_Y - 8} fontSize={9.5} className="fill-muted font-mono">vc:inflight · leases (90 s)</text>
      {Array.from({ length: 3 }).map((_, k) => {
        const lease = sim.leases[k];
        const x = QUEUE_X + k * 63;
        const w = sim.workers.find((wk) => wk.id === lease?.worker);
        const left = lease && w ? Math.max(0, 1 - w.step / Math.max(1, lease.total)) : 0;
        return (
          <g key={k} transform={`translate(${x} ${LEASE_Y})`}>
            <rect width={58} height={26} rx={7} fill="none" strokeWidth={1} strokeDasharray={lease ? undefined : "2 4"} className={lease ? "fill-working/10 stroke-working" : "stroke-line"} />
            {lease && (
              <g className="arch-enter">
                <text x={7} y={11} fontSize={8.5} fontWeight={600} className="fill-ink font-mono">{lease.member}</text>
                <rect x={7} y={17} width={44} height={3.5} rx={1.75} className="fill-ink/10" />
                <rect x={7} y={17} width={44 * left} height={3.5} rx={1.75} className="fill-working" />
              </g>
            )}
          </g>
        );
      })}
    </g>
  );
}
