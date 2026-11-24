import { BOX, PG_W, PG_X, ROW_H, rowY } from "@/lib/arch/layout";
import { N, VIDEO_SECONDS, VIDEO_ID, clock, type ChunkRow, type Sim } from "@/lib/arch/engine";

const PILL: Record<ChunkRow["status"], { box: string; text: string; label: string }> = {
  absent: { box: "fill-none stroke-line", text: "fill-muted", label: "\u2014" },
  pending: { box: "fill-queued/50 stroke-queued", text: "fill-muted", label: "pending" },
  processing: { box: "fill-working/20 stroke-working", text: "fill-ink", label: "processing" },
  completed: { box: "fill-ready/20 stroke-ready", text: "fill-ink", label: "completed" },
};

function Chip({ x, label, cls }: { x: number; label: string; cls: string }) {
  return (
    <g transform={`translate(${x} 4)`}>
      <rect width={label.length * 5.4 + 8} height={14} rx={4} strokeWidth={1} className={cls} />
      <text x={(label.length * 5.4 + 8) / 2} y={10.2} textAnchor="middle" fontSize={8.5} fontWeight={600} className="fill-ink">{label}</text>
    </g>
  );
}

interface Props {
  sim: Sim;
  selected: number | null;
  interactive: boolean;
  onSelect: (i: number | null) => void;
}

export default function PostgresTable({ sim, selected, interactive, onSelect }: Props) {
  const { pg } = BOX;
  const jobPill = sim.job.exists ? PILL[sim.job.status === "completed" ? "completed" : sim.job.status === "processing" ? "processing" : "pending"] : PILL.absent;
  return (
    <g>
      {/* videos + jobs */}
      <text x={PG_X} y={pg.y + 58} fontSize={9.5} className="fill-muted font-mono">videos</text>
      <text x={PG_X + 52} y={pg.y + 58} fontSize={10} className="fill-ink font-mono">
        {sim.videoExists ? `#${VIDEO_ID}  demo.mp4  ${clock(VIDEO_SECONDS)}` : "\u2014"}
      </text>
      <text x={PG_X} y={pg.y + 76} fontSize={9.5} className="fill-muted font-mono">jobs</text>
      <g transform={`translate(${PG_X + 52} ${pg.y + 64})`}>
        <text y={12} fontSize={10} className="fill-ink font-mono">{sim.job.exists ? `#${VIDEO_ID}` : "\u2014"}</text>
        {sim.job.exists && (
          <g transform="translate(30 0)" key={sim.job.status}>
            <rect width={78} height={16} rx={5} strokeWidth={1} className={`arch-enter ${jobPill.box}`} />
            <text x={39} y={11.4} textAnchor="middle" fontSize={9} fontWeight={600} className="fill-ink">{sim.job.status}</text>
          </g>
        )}
        {sim.job.exists && <text x={118} y={12} fontSize={10} className="fill-ink font-mono">{sim.job.completed}/{sim.job.total || "?"}</text>}
      </g>

      {/* chunks table */}
      <text x={PG_X} y={rowY(0) - 18} fontSize={9.5} fontWeight={700} className="fill-pg font-mono">chunks</text>
      <g fontSize={8.5} className="fill-muted" letterSpacing={0.4}>
        <text x={PG_X + 10} y={rowY(0) - 6}>#</text>
        <text x={PG_X + 40} y={rowY(0) - 6}>STATUS</text>
        <text x={PG_X + 140} y={rowY(0) - 6}>WORKER</text>
        <text x={PG_X + 214} y={rowY(0) - 6}>CENSORED</text>
      </g>
      <path d={`M${PG_X} ${rowY(0) - 3} H${PG_X + PG_W}`} strokeWidth={1} className="stroke-line" />

      {sim.rows.map((r, i) => {
        const pill = PILL[r.status];
        const exists = r.status !== "absent";
        const sel = selected === i;
        const done = r.status === "completed";
        const visual = r.detections.length > 0;
        const audio = r.audioEvents.length > 0;
        return (
          <g
            key={i}
            transform={`translate(${PG_X} ${rowY(i)})`}
            role={interactive && exists ? "button" : undefined}
            tabIndex={interactive && exists ? 0 : undefined}
            aria-label={interactive && exists ? `Open the PostgreSQL row for chunk ${i}` : undefined}
            aria-pressed={interactive && exists ? sel : undefined}
            onClick={interactive && exists ? () => onSelect(sel ? null : i) : undefined}
            onKeyDown={interactive && exists ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(sel ? null : i); } } : undefined}
            className={interactive && exists ? "group cursor-pointer outline-none" : undefined}
          >
            <rect width={PG_W} height={ROW_H} rx={6} strokeWidth={sel ? 1.6 : 1} className={sel ? "fill-pg/10 stroke-pg" : exists ? "fill-transparent stroke-transparent group-hover:fill-ink/5 group-focus-visible:stroke-accent" : "fill-transparent stroke-transparent"} />
            {r.version > 0 && <rect key={r.version} width={PG_W} height={ROW_H} rx={6} className="arch-flash fill-pg/25" />}
            <text x={10} y={15} fontSize={10.5} className={exists ? "fill-ink font-mono" : "fill-muted/60 font-mono"}>{String(i).padStart(2, "0")}</text>
            <g transform="translate(40 3)">
              <rect width={80} height={16} rx={5} strokeWidth={1} strokeDasharray={exists ? undefined : "2 3"} className={pill.box} />
              <text x={40} y={11.3} textAnchor="middle" fontSize={9} fontWeight={600} className={pill.text}>{pill.label}</text>
            </g>
            <text x={140} y={15} fontSize={10} className={r.worker === null ? "fill-muted/60 font-mono" : "fill-ink font-mono"}>
              {r.worker === null ? "\u2014" : `worker-${r.worker + 1}`}
            </text>
            {done && !visual && !audio && <Chip x={214} label="clean" cls="fill-transparent stroke-line" />}
            {done && visual && <Chip x={214} label="blur" cls="fill-accent/15 stroke-accent" />}
            {done && audio && <Chip x={visual ? 250 : 214} label="beep" cls="fill-working/20 stroke-working" />}
            {!done && <text x={214} y={15} fontSize={10} className="fill-muted/60 font-mono">{"\u2014"}</text>}
            {interactive && exists && (
              <text x={PG_W - 12} y={15} textAnchor="end" fontSize={11} className="fill-pg opacity-0 group-hover:opacity-100">{"\u203A"}</text>
            )}
          </g>
        );
      })}

      <text x={PG_X + PG_W / 2} y={pg.y + pg.h - 14} textAnchor="middle" fontSize={9.5} className={interactive ? "fill-pg" : "fill-muted"}>
        {interactive ? "click a row to open its document" : `${N} rows, one per chunk`}
      </text>
    </g>
  );
}
