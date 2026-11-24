"use client";
import { JobInfo } from "@/lib/api";
import { chunkColor } from "@/lib/status";

export default function BufferBar({ job }: { job: JobInfo }) {
  const total = job.duration || job.chunks[job.chunks.length - 1]?.end_time || 1;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="font-medium">Processing progress</span>
        <span className="text-muted">
          {job.completed}/{job.total} chunks
        </span>
      </div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-queued/50">
        {[...job.chunks]
          .sort((a, b) => a.index - b.index)
          .map(c => {
            const w = ((c.end_time - c.start_time) / total) * 100;
            return (
              <div
                key={c.index}
                className={`${chunkColor[c.status]} transition-colors`}
                style={{ width: `${w}%` }}
                title={`Chunk #${c.index} — ${c.status}`}
              />
            );
          })}
      </div>
    </div>
  );
}
