import { BOX, rectProps, CELL_H, CELL_PITCH, CELL_W, CELL_X0, CELL_Y, cellX } from "@/lib/arch/layout";
import { CHUNK_SECONDS, N, VIDEO_SECONDS, clock, segName, type Sim } from "@/lib/arch/engine";

interface Props {
  sim: Sim;
  interactive: boolean;
  onSeek: (i: number) => void;
}

/** Tiny stand-in for the video frame: a scene, plus the censoring that the current chunk really contains. */
function Screen({ sim }: { sim: Sim }) {
  const row = sim.rows[sim.playhead];
  const ready = sim.playerOn && sim.segments[sim.playhead] && sim.stalledOn === null;
  const dets = ready ? row.detections : [];
  const beep = ready && row.audioEvents.length > 0;
  const W = 124, H = 70;
  return (
    <g transform="translate(12 546)">
      <rect width={W} height={H} rx={8} className="fill-ink/[0.07] stroke-line" />
      {/* the "scene" */}
      <g className="fill-muted/35" clipPath="url(#arch-screen-clip)">
        <circle cx={34} cy={30} r={11} />
        <rect x={20} y={42} width={30} height={28} rx={9} />
        <rect x={72} y={34} width={36} height={36} rx={4} className="fill-muted/20" />
        <rect x={0} y={60} width={W} height={10} className="fill-muted/20" />
      </g>
      {!sim.playerOn && <text x={W / 2} y={H / 2 + 3} textAnchor="middle" fontSize={9.5} className="fill-muted">no video yet</text>}
      {sim.playerOn && !ready && (
        <g>
          <rect width={W} height={H} rx={8} className="fill-paper/70" />
          <g transform={`translate(${W / 2} ${H / 2 - 6})`}>
            <circle r={9} fill="none" strokeWidth={2.4} className="stroke-line" />
            <path d="M0 -9 A9 9 0 0 1 9 0" fill="none" strokeWidth={2.4} strokeLinecap="round" className="arch-spin stroke-accent" />
          </g>
          <text x={W / 2} y={H / 2 + 22} textAnchor="middle" fontSize={8.5} className="fill-muted">buffering</text>
        </g>
      )}
      {dets.map((d, k) =>
        d.box ? (
          <g key={k} className="arch-enter">
            <rect x={d.box[0] * W} y={d.box[1] * H} width={d.box[2] * W} height={d.box[3] * H} rx={4} className="fill-ink/45 stroke-ink/70" strokeWidth={1} />
            {[0, 1, 2].map((r) => [0, 1, 2, 3].map((c) => (
              (r + c) % 2 === 0 ? <rect key={`${r}${c}`} x={d.box![0] * W + (c * d.box![2] * W) / 4} y={d.box![1] * H + (r * d.box![3] * H) / 3} width={(d.box![2] * W) / 4} height={(d.box![3] * H) / 3} className="fill-surface/25" /> : null
            )))}
          </g>
        ) : null,
      )}
      {beep && (
        <g transform={`translate(${W - 22} 14)`} className="arch-enter">
          <rect x={-12} y={-9} width={34} height={18} rx={9} className="fill-working/25 stroke-working" strokeWidth={1.2} />
          <text x={5} y={3.5} textAnchor="middle" fontSize={9} fontWeight={700} className="fill-ink">BEEP</text>
        </g>
      )}
    </g>
  );
}

export default function Player({ sim, interactive, onSeek }: Props) {
  const { player } = BOX;
  const cur = sim.playhead;
  const status = !sim.playerOn
    ? "waiting for the first chunk list\u2026"
    : sim.stalledOn !== null
      ? `waiting for ${segName(sim.stalledOn)}`
      : sim.ended
        ? "ended"
        : `playing ${segName(cur)}`;

  return (
    <g>
      <defs><clipPath id="arch-screen-clip"><rect width={124} height={70} rx={8} /></clipPath></defs>
      <rect {...rectProps(player)} rx={14} className="fill-paper/55 stroke-line" />
      <circle cx={30} cy={player.y + 22} r={4} className="fill-failed/70" />
      <circle cx={44} cy={player.y + 22} r={4} className="fill-working/80" />
      <circle cx={58} cy={player.y + 22} r={4} className="fill-ready/80" />
      <text x={78} y={player.y + 26} fontSize={11} fontWeight={650} className="fill-ink font-display">Player</text>
      <text x={124} y={player.y + 26} fontSize={10} className="fill-muted">hls.js in the browser</text>
      <text x={player.x + player.w - 14} y={player.y + 26} textAnchor="end" fontSize={10} className={sim.stalledOn !== null ? "fill-working font-mono" : "fill-muted font-mono"}>
        {status}
      </text>

      <Screen sim={sim} />

      {/* timeline */}
      {Array.from({ length: N }).map((_, i) => {
        const ready = sim.segments[i];
        const proc = sim.rows[i].status === "processing";
        const now = i === cur && sim.playerOn;
        return (
          <g
            key={i}
            transform={`translate(${cellX(i)} ${CELL_Y})`}
            role={interactive && sim.playerOn ? "button" : undefined}
            tabIndex={interactive && sim.playerOn ? 0 : undefined}
            aria-label={interactive ? `Seek to ${clock(i * CHUNK_SECONDS)} (chunk ${i})` : undefined}
            onClick={interactive && sim.playerOn ? () => onSeek(i) : undefined}
            onKeyDown={interactive && sim.playerOn ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSeek(i); } } : undefined}
            className={interactive && sim.playerOn ? "group cursor-pointer outline-none" : undefined}
          >
            <title>{`${clock(i * CHUNK_SECONDS)} \u00B7 chunk ${i} \u00B7 ${ready ? "ready" : proc ? "processing" : "queued"}`}</title>
            <rect width={CELL_W} height={CELL_H} rx={6} className={ready ? "fill-ready" : proc ? "fill-working" : "fill-queued"} />
            {proc && <rect width={CELL_W} height={CELL_H} rx={6} className="arch-breathe fill-surface/30" />}
            <text x={CELL_W / 2} y={18} textAnchor="middle" fontSize={11} fontWeight={600} className={ready || proc ? "fill-surface font-mono" : "fill-muted font-mono"}>{i}</text>
            {interactive && sim.playerOn && <rect width={CELL_W} height={CELL_H} rx={6} fill="none" strokeWidth={2} className="stroke-transparent group-hover:stroke-accent group-focus-visible:stroke-accent" />}
            {now && <rect x={-3} y={-3} width={CELL_W + 6} height={CELL_H + 6} rx={8} fill="none" strokeWidth={2.4} className={sim.stalledOn === i ? "stroke-working arch-breathe" : "stroke-ink"} />}
          </g>
        );
      })}

      {/* playhead marker */}
      {sim.playerOn && (
        <g className="arch-move" style={{ transform: `translate(${cellX(cur) + CELL_W / 2}px, ${CELL_Y - 8}px)` }}>
          <path d="M-5 -6 H5 L0 1 Z" className="fill-ink" />
        </g>
      )}

      {/* time axis */}
      {[0, 3, 6, 9, 12].map((k) => (
        <text key={k} x={k === 12 ? CELL_X0 + 11 * CELL_PITCH + CELL_W : cellX(k)} y={CELL_Y + CELL_H + 17} textAnchor={k === 12 ? "end" : "start"} fontSize={9.5} className="fill-muted font-mono">
          {clock(k * CHUNK_SECONDS)}
        </text>
      ))}
      <text x={CELL_X0} y={CELL_Y + CELL_H + 38} fontSize={10} className={interactive ? "fill-accent" : "fill-muted"}>
        {interactive ? "click any segment to seek \u2192 watch the Redis queue re-order" : `${VIDEO_SECONDS} s video \u00B7 ${N} segments`}
      </text>
      <g transform={`translate(${player.x + player.w - 150} ${player.y + player.h - 28})`}>
        <rect width={7} height={7} rx={2} y={0} className="fill-ready" />
        <text x={11} y={7} fontSize={9} className="fill-muted">ready</text>
        <rect x={46} width={7} height={7} rx={2} className="fill-working" />
        <text x={57} y={7} fontSize={9} className="fill-muted">working</text>
        <rect x={104} width={7} height={7} rx={2} className="fill-queued" />
        <text x={115} y={7} fontSize={9} className="fill-muted">queued</text>
      </g>
    </g>
  );
}
