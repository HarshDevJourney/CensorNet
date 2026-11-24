"use client";
import { useSimulation } from "@/lib/arch/useSimulation";
import ArchitectureDiagram from "./ArchitectureDiagram";
import Caption from "./Caption";
import Controls from "./Controls";
import EventLog from "./EventLog";
import Inspector from "./Inspector";
import PriorityPanel from "./PriorityPanel";
import Stepper from "./Stepper";

/** The full, interactive version: controls, narration, the diagram, and the panels that explain Redis and PostgreSQL. */
export default function ArchitectureLab() {
  const a = useSimulation();
  const { sim } = a;

  return (
    <div ref={a.wrapperRef} className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Controls playing={a.playing} speed={a.speed} canSeek={sim.playerOn} onToggle={a.toggle} onRestart={a.restart} onSpeed={a.setSpeed} onJump={a.jump} />
        <p className="text-xs text-muted">
          Try it: <span className="font-medium text-ink">click the timeline</span> to seek, or{" "}
          <span className="font-medium text-ink">click a PostgreSQL row</span> to open it.
        </p>
      </div>

      <Stepper sim={sim} />
      <Caption sim={sim} />

      <ArchitectureDiagram
        sim={sim}
        shown={a.shown}
        selected={a.selected}
        interactive
        playing={a.playing}
        speed={a.speed}
        reduced={a.reduced}
        clockRef={a.clockRef}
        onSelect={a.select}
        onSeek={a.seekTo}
      />

      <Inspector sim={sim} shown={a.shown} picked={a.selected !== null} />

      <div className="grid gap-4 lg:grid-cols-2">
        <PriorityPanel sim={sim} />
        <EventLog sim={sim} />
      </div>
    </div>
  );
}
