"use client";
import { useEffect, useRef, type MutableRefObject } from "react";
import { polyLength, pointAt } from "@/lib/arch/layout";
import { TICK_MS, type Flight, type FlightKind } from "@/lib/arch/engine";

/* Every class is written out in full so Tailwind can see it. */
const LOOK: Record<FlightKind, { fill: string; stroke: string }> = {
  upload: { fill: "fill-surface", stroke: "stroke-ink" },
  doc: { fill: "fill-pg/15", stroke: "stroke-pg" },
  task: { fill: "fill-redis/15", stroke: "stroke-redis" },
  pop: { fill: "fill-redis/15", stroke: "stroke-redis" },
  claim: { fill: "fill-pg/15", stroke: "stroke-pg" },
  result: { fill: "fill-pg/25", stroke: "stroke-pg" },
  segment: { fill: "fill-ready/20", stroke: "stroke-ready" },
  serve: { fill: "fill-ready/20", stroke: "stroke-ready" },
  seek: { fill: "fill-accent", stroke: "stroke-accent" },
};
const TEXT_ON_SOLID = "fill-surface";

const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

interface Props {
  flights: Flight[];
  /** simulation clock in ms; stops while paused, so packets freeze with everything else */
  clockRef: MutableRefObject<number>;
  speed: number;
  reduced: boolean;
}

/**
 * Packets. Their motion is driven from requestAnimationFrame straight onto the SVG nodes (no React render per frame):
 * each flight walks along its polyline with ease-in-out.
 */
export default function FlightLayer({ flights, clockRef, speed, reduced }: Props) {
  const nodes = useRef(new Map<number, SVGGElement>());
  const starts = useRef(new Map<number, number>());
  const live = useRef<Flight[]>(flights);
  live.current = flights;

  useEffect(() => {
    let raf = 0;
    const frame = () => {
      const now = clockRef.current;
      for (const f of live.current) {
        const el = nodes.current.get(f.id);
        if (!el) continue;
        let t0 = starts.current.get(f.id);
        if (t0 === undefined) {
          t0 = now;
          starts.current.set(f.id, t0);
        }
        const dur = reduced ? 1 : TICK_MS * f.dur;
        const total = polyLength(f.pts);
        const p = (now - t0) / dur;
        if (p <= 0 || p >= 1.04) {
          el.setAttribute("visibility", "hidden");
        } else {
          const [x, y] = pointAt(f.pts, ease(Math.min(1, p)) * total);
          el.setAttribute("transform", `translate(${x.toFixed(1)} ${y.toFixed(1)})`);
          el.setAttribute("visibility", "visible");
        }
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [clockRef, speed, reduced]);

  // forget bookkeeping for flights that left the sim
  useEffect(() => {
    const ids = new Set(flights.map((f) => f.id));
    for (const id of [...starts.current.keys()]) if (!ids.has(id)) starts.current.delete(id);
    for (const id of [...nodes.current.keys()]) if (!ids.has(id)) nodes.current.delete(id);
  }, [flights]);

  return (
    <g pointerEvents="none" aria-hidden>
      {flights.map((f) => {
        const w = Math.max(24, f.label.length * 5.7 + 14);
        const look = LOOK[f.kind];
        const solid = f.kind === "seek";
        return (
          <g
            key={f.id}
            visibility="hidden"
            ref={(el) => {
              if (el) nodes.current.set(f.id, el);
            }}
          >
            <rect x={-w / 2} y={-9} width={w} height={18} rx={6} className={`${look.fill} ${look.stroke}`} strokeWidth={1.4} />
            <text textAnchor="middle" y={3.4} className={`font-mono ${solid ? TEXT_ON_SOLID : "fill-ink"}`} fontSize={9.5} fontWeight={600}>
              {f.label}
            </text>
          </g>
        );
      })}
    </g>
  );
}
