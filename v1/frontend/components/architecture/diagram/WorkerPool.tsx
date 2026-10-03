import { RAIL_END_Y, TILE_H, TILE_W, WORKER_H, WORKER_W, WORKER_X, tilePos, workerY, BOX } from "@/lib/arch/layout";
import { N, segName, workerProgress, type Sim, type WorkerSim } from "@/lib/arch/engine";

function Bar({ x, y, w, label, value }: { x: number; y: number; w: number; label: string; value: number }) {
  return (
    <g>
      <text x={x} y={y + 5} fontSize={8.5} className="fill-muted">{label}</text>
      <rect x={x + 42} y={y} width={w} height={5} rx={2.5} className="fill-ink/10" />
      <rect x={x + 42} y={y} width={Math.max(0, w * value)} height={5} rx={2.5} className="fill-accent" style={{ transition: "width 500ms ease-out" }} />
    </g>
  );
}

function WorkerCard({ w }: { w: WorkerSim }) {
  const p = workerProgress(w);
  const busy = !!w.task;
  const prep = w.task?.kind === "prepare";
  return (
    <g transform={`translate(${WORKER_X} ${workerY(w.id)})`}>
      <rect width={WORKER_W} height={WORKER_H} rx={11} strokeWidth={busy ? 1.6 : 1} className={busy ? "fill-accent/[0.07] stroke-accent" : "fill-surface stroke-line"} />
      <text x={12} y={19} fontSize={11.5} fontWeight={650} className="fill-ink">Worker {w.id + 1}</text>
      <circle cx={WORKER_W - 14} cy={15} r={4} className={busy ? "fill-working arch-breathe" : "fill-queued"} />
      <text x={12} y={34} fontSize={10} className={busy ? "fill-ink font-mono" : "fill-muted"}>
        {!w.task ? "idle · waiting for work" : prep ? "p:1 · probe + split" : `c:1:${w.task.index}`}
      </text>
      <Bar x={12} y={44} w={86} label={prep ? "probe" : "frames"} value={p.a} />
      <Bar x={12} y={57} w={86} label={prep ? "split" : "speech"} value={p.b} />
      <Bar x={12} y={70} w={86} label={prep ? "" : "render"} value={p.c} />
    </g>
  );
}

export default function WorkerPool({ sim }: { sim: Sim }) {
  const { pool } = BOX;
  return (
    <g>
      {sim.workers.map((w) => (
        <WorkerCard key={w.id} w={w} />
      ))}

      {/* disk */}
      <text x={WORKER_X + 26} y={RAIL_END_Y - 5} fontSize={9.5} className="fill-muted font-mono">disk · storage/hls</text>
      <text x={pool.x + pool.w - 12} y={RAIL_END_Y - 6} textAnchor="end" fontSize={9.5} className="fill-muted font-mono">
        {sim.segments.filter(Boolean).length}/{N}
      </text>
      {Array.from({ length: N }).map((_, i) => {
        const t = tilePos(i);
        const ready = sim.segments[i];
        return (
          <g key={i} transform={`translate(${t.x} ${t.y})`}>
            <rect width={TILE_W} height={TILE_H} rx={5} fill="none" strokeWidth={1} strokeDasharray="2 3" className="stroke-line" />
            {ready && (
              <g key={sim.segmentTick[i] ?? 0} className="arch-pop">
                <title>{segName(i)}</title>
                <rect width={TILE_W} height={TILE_H} rx={5} strokeWidth={1.2} className="fill-ready/25 stroke-ready" />
                <text x={TILE_W / 2} y={14} textAnchor="middle" fontSize={9.5} fontWeight={600} className="fill-ink font-mono">{i}</text>
              </g>
            )}
          </g>
        );
      })}
    </g>
  );
}
