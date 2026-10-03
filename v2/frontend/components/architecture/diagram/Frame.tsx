import { BOX, BUS_X, RAIL_END_Y, RAIL_X, rectProps, slotY, workerY } from "@/lib/arch/layout";

const BOX_CLS = "fill-paper/55 stroke-line";
const CONNECT = "stroke-muted/45";

/** Small text label sitting on a connector. */
function Tag({ x, y, children, anchor = "middle" }: { x: number; y: number; children: string; anchor?: "start" | "middle" | "end" }) {
  return (
    <text x={x} y={y} textAnchor={anchor} fontSize={9} className="fill-muted font-mono" letterSpacing={0.2}>
      {children}
    </text>
  );
}

/** Step badge: lights up in the accent colour when that stage is active (matches the stepper above). */
export function Badge({ x, y, n, active }: { x: number; y: number; n: number; active: boolean }) {
  return (
    <g transform={`translate(${x} ${y})`} aria-hidden>
      <circle r={10} className={active ? "fill-accent stroke-accent" : "fill-surface stroke-muted/60"} strokeWidth={1.5} />
      <text textAnchor="middle" y={3.6} fontSize={10.5} fontWeight={700} className={active ? "fill-surface" : "fill-ink"}>
        {n}
      </text>
    </g>
  );
}

function Header({ x, y, title, sub, dot }: { x: number; y: number; title: string; sub: string; dot?: string }) {
  return (
    <g>
      {dot && <circle cx={x + 6} cy={y + 17} r={5} className={dot} />}
      <text x={x + (dot ? 18 : 0)} y={y + 21} fontSize={15} fontWeight={650} className="fill-ink font-display">
        {title}
      </text>
      <text x={x + (dot ? 18 : 0)} y={y + 35} fontSize={10} className="fill-muted">
        {sub}
      </text>
    </g>
  );
}

/** Static art: boxes, titles and the pipes the packets travel through. */
export default function Frame({ arrowId }: { arrowId: string }) {
  const { upload, api, redis, pool, pg } = BOX;
  const w2 = workerY(2);
  return (
    <g>
      <defs>
        <marker id={arrowId} viewBox="0 0 8 8" refX="6.5" refY="4" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0 0.8 L7 4 L0 7.2 Z" className="fill-muted/70" />
        </marker>
      </defs>

      {/* ---------------- pipes ---------------- */}
      <g fill="none" strokeWidth={1.4} className={CONNECT}>
        <path d={`M85 ${upload.y + upload.h} V${api.y}`} markerEnd={`url(#${arrowId})`} />
        <path d={`M${api.x + api.w} 262 H${redis.x - 2}`} markerEnd={`url(#${arrowId})`} />
        {/* API -> PostgreSQL along the corridor */}
        <path d="M40 340 V494 H955 V482" className="arch-flow" markerEnd={`url(#${arrowId})`} />
        {/* player -> API (segment requests, seeks) */}
        <path d={`M130 512 V300 H${api.x + api.w}`} className="arch-flow" />
        <path d="M130 340 V318" markerEnd={`url(#${arrowId})`} />
        {/* redis -> workers */}
        <path d={`M${redis.x + redis.w} ${slotY(0) + 12} H474 V${w2 + 44}`} />
        {[0, 1, 2].map((w) => (
          <path key={w} d={`M474 ${workerY(w) + 44} H${pool.x + 12}`} markerEnd={`url(#${arrowId})`} />
        ))}
        {/* workers -> PostgreSQL */}
        {[0, 1, 2].map((w) => (
          <path key={w} d={`M664 ${workerY(w) + 28} H${BUS_X}`} />
        ))}
        <path d={`M${BUS_X} ${workerY(0) + 28} V${w2 + 28}`} />
        <path d={`M${BUS_X} ${workerY(1) + 28} H${pg.x}`} markerEnd={`url(#${arrowId})`} />
        {/* workers -> disk (rail) */}
        {[0, 1, 2].map((w) => (
          <path key={w} d={`M664 ${workerY(w) + 66} H${RAIL_X}`} />
        ))}
        <path d={`M${RAIL_X} ${workerY(0) + 66} V${RAIL_END_Y}`} markerEnd={`url(#${arrowId})`} />
      </g>

      {/* ---------------- boxes ---------------- */}
      <rect {...rectProps(upload)} rx={14} className={BOX_CLS} />
      <rect {...rectProps(api)} rx={14} className={BOX_CLS} />
      <rect {...rectProps(redis)} rx={16} className={BOX_CLS} />
      <rect {...rectProps(pool)} rx={16} className={BOX_CLS} />
      <rect {...rectProps(pg)} rx={16} className={BOX_CLS} />
      {/* thin brand-coloured top edge for the two data stores */}
      <path d={`M${redis.x + 16} ${redis.y} H${redis.x + redis.w - 16}`} strokeWidth={3} strokeLinecap="round" className="stroke-redis" />
      <path d={`M${pg.x + 16} ${pg.y} H${pg.x + pg.w - 16}`} strokeWidth={3} strokeLinecap="round" className="stroke-pg" />

      {/* ---------------- titles ---------------- */}
      <Header x={upload.x + 30} y={upload.y + 6} title="Browser" sub="uploads demo.mp4" />
      {/* little file icon */}
      <g transform={`translate(${upload.x + 11} ${upload.y + 15})`} aria-hidden fill="none" strokeWidth={1.5} className="stroke-muted">
        <path d="M2 0 H9 L14 5 V17 H2 Z" />
        <path d="M9 0 V5 H14" />
      </g>
      <Header x={api.x + 30} y={api.y + 6} title="FastAPI" sub="routes" />
      {["POST /upload", "GET  /segments/N.ts", "POST /seek", "GET  /job"].map((t, i) => (
        <text key={t} x={api.x + 16} y={api.y + 70 + i * 17} fontSize={9.5} className="fill-muted font-mono" style={{ whiteSpace: "pre" }}>
          {t}
        </text>
      ))}
      <Header x={redis.x + 30} y={redis.y + 6} title="Redis" sub="fast priority queue" dot="fill-redis" />
      <Header x={pool.x + 30} y={pool.y + 6} title="Workers" sub="3 separate processes" dot="fill-accent" />
      <Header x={pg.x + 30} y={pg.y + 6} title="PostgreSQL" sub="permanent record" dot="fill-pg" />

      {/* ---------------- pipe labels ---------------- */}
      <Tag x={207} y={254}>enqueue</Tag>
      <Tag x={474} y={slotY(0) + 2}>ZPOPMIN</Tag>
      <Tag x={BUS_X} y={workerY(0) + 18}>SQL</Tag>
      <Tag x={RAIL_X + 2} y={workerY(0) + 56}>seg.ts</Tag>
      <Tag x={500} y={508}>register: video, job, chunks</Tag>
      <Tag x={118} y={420} anchor="end">GET / seek</Tag>
    </g>
  );
}
