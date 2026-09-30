"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import VideoPlayer, { VideoPlayerHandle } from "@/components/VideoPlayer";
import BufferBar from "@/components/BufferBar";
import SeekBar from "@/components/SeekBar";
import { contiguousEnd, getJob, JobInfo, seek as seekApi } from "@/lib/api";

export default function VideoPage() {
  const params = useParams<{ jobId: string }>();
  const videoId = Number(params.jobId);

  const playerRef = useRef<VideoPlayerHandle>(null);
  const [job, setJob] = useState<JobInfo | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const j = await getJob(videoId);
        if (alive) setJob(j);
      } catch (e: any) {
        if (alive) setErr(e.message ?? String(e));
      }
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => { alive = false; clearInterval(id); };
  }, [videoId]);

  const readyEnd = useMemo(() => (job ? contiguousEnd(job) : 0), [job]);

  async function handleSeek(t: number) {
    if (!job) return;
    seekApi(videoId, t).catch(() => {});
    if (t <= readyEnd) {
      playerRef.current?.seek(t);
    } else {
      playerRef.current?.queueSeek(t);
    }
  }

  if (err) {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-red-500/10 text-red-200 p-6">
        {err}
      </div>
    );
  }

  if (!job) {
    return <div className="text-white/60">Loading…</div>;
  }

  const totalDuration =
    job.duration || job.chunks.at(-1)?.end_time || 0;
  const processing = job.status !== "completed";

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-xl font-medium">
          Video #{videoId}
          <span className="ml-3 text-xs uppercase tracking-wider text-white/50">
            {job.source_type}
          </span>
        </h1>
        <div className="text-sm">
          {processing ? (
            <span className="text-amber-300">
              {job.chunks.filter(c => c.status === "completed").length}/
              {job.chunks.length} chunks
            </span>
          ) : (
            <span className="text-emerald-400">Ready</span>
          )}
        </div>
      </div>

      <VideoPlayer
        ref={playerRef}
        videoId={videoId}
        readyEnd={readyEnd}
        totalDuration={totalDuration}
      />

      <BufferBar job={job} />

      <SeekBar
        duration={totalDuration}
        readyEnd={readyEnd}
        onSeek={handleSeek}
      />

      <ChunkGrid job={job} />
    </div>
  );
}

function ChunkGrid({ job }: { job: JobInfo }) {
  return (
    <div className="rounded-2xl border border-white/10 p-4">
      <div className="text-xs uppercase tracking-wider text-white/50 mb-3">
        Chunk status
      </div>
      <div className="grid grid-cols-12 gap-1">
        {[...job.chunks]
          .sort((a, b) => a.index - b.index)
          .map(c => {
            const color =
              c.status === "completed" ? "bg-emerald-500" :
              c.status === "processing" ? "bg-amber-400 animate-pulse" :
              c.status === "failed" ? "bg-red-500" : "bg-white/10";
            return (
              <div
                key={c.index}
                title={`#${c.index} · ${c.status} · priority=${c.priority.toFixed(1)}`}
                className={`h-5 rounded ${color}`}
              />
            );
          })}
      </div>
      <div className="mt-3 flex gap-4 text-xs text-white/50">
        <Legend color="bg-emerald-500" label="completed" />
        <Legend color="bg-amber-400" label="processing" />
        <Legend color="bg-white/10" label="pending" />
        <Legend color="bg-red-500" label="failed" />
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
