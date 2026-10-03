"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import VideoPlayer from "@/components/VideoPlayer";
import BufferBar from "@/components/BufferBar";
import { formatTime, getJob, JobInfo } from "@/lib/api";

export default function VideoPage() {
  const params = useParams<{ videoId: string }>();
  const videoId = Number(params.videoId);
  const [job, setJob] = useState<JobInfo | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const j = await getJob(videoId);
        if (alive) { setJob(j); setErr(null); }
      } catch (e: any) {
        if (alive) setErr(e.message ?? String(e));
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => { alive = false; clearInterval(id); };
  }, [videoId]);

  if (err && !job) {
    return <div className="rounded-2xl border border-red-500/30 bg-red-500/10 text-red-200 p-6">{err}</div>;
  }
  if (!job) return <div className="text-white/60">Loading…</div>;

  const ready = job.total > 0 && job.status !== "failed";
  const running = job.status === "processing" || job.status === "preparing" || job.status === "downloading";

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-xl font-medium">
          Video #{videoId}
          <span className="ml-3 text-xs uppercase tracking-wider text-white/50">{job.source_type}</span>
        </h1>
        <div className="text-sm">
          {job.status === "completed" && <span className="text-emerald-400">Fully censored</span>}
          {running && (
            <span className="text-amber-300">
              {job.status === "downloading" ? "Downloading…" : `${job.completed}/${job.total} chunks`}
            </span>
          )}
          {job.status === "failed" && <span className="text-red-400">Failed</span>}
        </div>
      </div>

      {job.error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 text-red-200 text-sm px-4 py-3">{job.error}</div>
      )}
      {running && job.workers === 0 && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-200 text-sm px-4 py-3">
          No worker is running, so nothing will be processed. Start one:{" "}
          <code>python run_workers.py</code>
        </div>
      )}

      <VideoPlayer videoId={videoId} ready={ready} />
      <BufferBar job={job} />

      <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-white/50">
        <span>Length {formatTime(job.duration)}</span>
        <span>Playhead: chunk #{job.playhead}</span>
        <span>Workers online: {job.workers}</span>
        <span>Queue: {job.queue_length}</span>
      </div>
      <ChunkGrid job={job} />
    </div>
  );
}

function ChunkGrid({ job }: { job: JobInfo }) {
  return (
    <div className="rounded-2xl border border-white/10 p-4">
      <div className="text-xs uppercase tracking-wider text-white/50 mb-3">Chunks (white ring = playhead)</div>
      <div className="grid grid-cols-12 gap-1">
        {job.chunks.map(c => {
          const color =
            c.status === "completed" ? "bg-emerald-500" :
            c.status === "processing" ? "bg-amber-400 animate-pulse" :
            c.status === "failed" ? "bg-red-500" : "bg-white/10";
          const urgent = c.status === "pending" && c.priority !== null && c.priority < -500_000;
          return (
            <div
              key={c.index}
              title={`#${c.index} · ${c.status}${c.priority !== null ? ` · priority ${c.priority}` : ""}`}
              className={`h-5 rounded ${color} ${urgent ? "ring-1 ring-sky-400" : ""} ${
                c.index === job.playhead ? "ring-2 ring-white" : ""
              }`}
            />
          );
        })}
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-xs text-white/50">
        <Legend color="bg-emerald-500" label="censored & ready" />
        <Legend color="bg-amber-400" label="processing" />
        <Legend color="bg-white/10" label="queued" />
        <Legend color="bg-red-500" label="failed" />
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded bg-white/10 ring-1 ring-sky-400" /> urgent (next up)
        </span>
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`inline-block w-3 h-3 rounded ${color}`} />
      {label}
    </span>
  );
}
