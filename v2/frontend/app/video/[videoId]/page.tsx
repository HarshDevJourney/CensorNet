"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import VideoPlayer from "@/components/video/VideoPlayer";
import BufferBar from "@/components/video/BufferBar";
import ChunkGrid from "@/components/video/ChunkGrid";
import JobHeader from "@/components/video/JobHeader";
import JobStats from "@/components/video/JobStats";
import Alert from "@/components/ui/Alert";
import { getJob, JobInfo } from "@/lib/api";

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
    return <Alert>{err}</Alert>;
  }
  if (!job) return <div className="text-muted">Loading…</div>;

  const ready = job.total > 0 &&
    job.status !== "failed" &&
    job.completed >= Math.min(3, job.total);
  const running = job.status === "processing" || job.status === "preparing" || job.status === "downloading";

  return (
    <div className="space-y-6">
      <JobHeader videoId={videoId} job={job} running={running} />

      {job.error && <Alert>{job.error}</Alert>}
      {running && job.workers === 0 && (
        <Alert tone="warning">
          No worker is running, so nothing will be processed. Start one:{" "}
          <code className="rounded bg-ink/10 px-1.5 py-0.5">python run_workers.py</code>
        </Alert>
      )}

      <VideoPlayer videoId={videoId} ready={ready} />
      <BufferBar job={job} />
      <JobStats job={job} />
      <ChunkGrid job={job} />
    </div>
  );
}
