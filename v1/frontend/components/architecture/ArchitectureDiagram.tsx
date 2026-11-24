"use client";
import { useId, type MutableRefObject } from "react";
import { VB_H, VB_W, BOX, workerY, RAIL_END_Y } from "@/lib/arch/layout";
import type { Sim } from "@/lib/arch/engine";
import { TICK_MS } from "@/lib/arch/engine";
import Frame, { Badge } from "./diagram/Frame";
import RedisQueue from "./diagram/RedisQueue";
import WorkerPool from "./diagram/WorkerPool";
import PostgresTable from "./diagram/PostgresTable";
import Player from "./diagram/Player";
import DocCard from "./diagram/DocCard";
import FlightLayer from "./FlightLayer";

interface Props {
  sim: Sim;
  shown: number | null;
  selected: number | null;
  interactive: boolean;
  playing: boolean;
  speed: number;
  reduced: boolean;
  clockRef: MutableRefObject<number>;
  onSelect: (i: number | null) => void;
  onSeek: (i: number) => void;
}

/** The whole picture. Scales as one SVG; scrolls sideways on narrow screens instead of shrinking text to nothing. */
export default function ArchitectureDiagram({ sim, shown, selected, interactive, playing, speed, reduced, clockRef, onSelect, onSeek }: Props) {
  const arrowId = `arch-arrow-${useId().replace(/:/g, "")}`;
  const on = (n: number) => sim.focus.includes(n) || (sim.lastFocus[n] !== undefined && sim.tick - sim.lastFocus[n] < 2);
  const { upload, redis, pool, pg, player } = BOX;

  return (
    <div>
    <div className="overflow-x-auto rounded-2xl border border-line bg-surface/80 p-3 shadow-[0_30px_60px_-30px_rgb(var(--c-accent)/0.35)] backdrop-blur sm:p-5">
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        className="block h-auto w-full min-w-[980px]"
        style={{ ["--move" as string]: `${Math.round(TICK_MS * 0.9 / speed)}ms` }}
        data-paused={!playing}
        role="group"
        aria-label="Animated architecture: an uploaded video is split into chunks, queued in Redis, processed by workers, recorded in PostgreSQL and streamed to the player."
      >
        <Frame arrowId={arrowId} />
        <RedisQueue sim={sim} />
        <WorkerPool sim={sim} />
        <PostgresTable sim={sim} selected={selected ?? (interactive ? null : shown)} interactive={interactive} onSelect={onSelect} />
        <Player sim={sim} interactive={interactive} onSeek={onSeek} />
        <DocCard sim={sim} shown={shown} interactive={interactive} />

        <Badge x={upload.x + 12} y={upload.y} n={1} active={on(1)} />
        <Badge x={pg.x + 14} y={pg.y} n={2} active={on(2)} />
        <Badge x={redis.x + 14} y={redis.y} n={3} active={on(3)} />
        <Badge x={pool.x + 14} y={pool.y} n={4} active={on(4)} />
        <Badge x={pool.x + 24} y={RAIL_END_Y - 9} n={5} active={on(5)} />
        <Badge x={player.x + 12} y={player.y} n={6} active={on(6)} />
        <Badge x={130} y={workerY(2) + 120} n={7} active={on(7)} />

        <FlightLayer flights={sim.flights} clockRef={clockRef} speed={speed} reduced={reduced} />
      </svg>
    </div>
    <p className="mt-2 text-center text-xs text-muted lg:hidden">Swipe sideways to see the whole diagram {"\u2192"}</p>
    </div>
  );
}
