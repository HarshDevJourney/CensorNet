import { JobInfo } from "@/lib/api";
import { chunkColor } from "@/lib/status";
import Panel from "@/components/ui/Panel";

export default function ChunkGrid({ job }: { job: JobInfo }) {
  return (
    <Panel className="p-5">
      <h2 className="font-display text-lg font-semibold">Chunks</h2>
      <p className="mb-4 text-sm text-muted">The ringed chunk is the playhead.</p>
      <div className="grid grid-cols-10 gap-1 sm:grid-cols-12">
        {job.chunks.map(c => {
          const color = c.status === "processing" ? `${chunkColor.processing} animate-pulse-soft` : chunkColor[c.status];
          const urgent = c.status === "pending" && c.priority !== null && c.priority < -500_000;
          return (
            <div
              key={c.index}
              title={`#${c.index} · ${c.status}${c.priority !== null ? ` · priority ${c.priority}` : ""}`}
              className={`h-6 rounded ${color} ${urgent ? "ring-2 ring-accent" : ""} ${
                c.index === job.playhead ? "ring-2 ring-ink ring-offset-1 ring-offset-surface" : ""
              }`}
            />
          );
        })}
      </div>
      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted">
        <Legend color={chunkColor.completed} label="censored & ready" />
        <Legend color={chunkColor.processing} label="processing" />
        <Legend color={chunkColor.pending} label="queued" />
        <Legend color={chunkColor.failed} label="failed" />
        <span className="inline-flex items-center gap-1.5">
          <span className={`inline-block h-3 w-3 rounded ${chunkColor.pending} ring-2 ring-accent`} /> urgent (next up)
        </span>
      </div>
    </Panel>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`inline-block h-3 w-3 rounded ${color}`} />
      {label}
    </span>
  );
}
