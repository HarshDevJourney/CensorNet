"use client";
import { JobInfo } from "@/lib/api";

export default function BufferBar({ job }: { job: JobInfo }) {
  const total = job.duration || job.chunks[job.chunks.length - 1]?.end_time || 1;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-white/50">
        <span>Processing progress</span>
        <span>
          {job.completed}/{job.total} chunks
        </span>
      </div>
      <div className="h-3 w-full rounded-full overflow-hidden flex bg-white/5">
        {[...job.chunks]
          .sort((a, b) => a.index - b.index)
          .map(c => {
            const w = ((c.end_time - c.start_time) / total) * 100;
            const color =
              c.status === "completed" ? "bg-emerald-500" :
              c.status === "processing" ? "bg-amber-400" :
              c.status === "failed" ? "bg-red-500" : "bg-white/10";
            return (
              <div
                key={c.index}
                className={`${color} transition-colors`}
                style={{ width: `${w}%` }}
                title={`Chunk #${c.index} — ${c.status}`}
              />
            );
          })}
      </div>
    </div>
  );
}
