const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type ChunkStatus = "pending" | "processing" | "completed" | "failed";

export interface ChunkInfo {
  index: number;
  start_time: number;
  end_time: number;
  status: ChunkStatus;
  priority: number;
}

export interface JobInfo {
  id: number;
  video_id: number;
  status: string;
  duration: number;
  source_type: "upload" | "youtube";
  chunks: ChunkInfo[];
}

export interface IngestResponse {
  id: number;
  source_type: "upload" | "youtube";
  source_url: string | null;
  duration: number;
  job_id: number | null;
  playlist_url: string | null;
}

async function jsonOrThrow<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${await r.text()}`);
  return r.json();
}

export async function uploadVideo(file: File): Promise<IngestResponse> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${API}/videos/upload`, { method: "POST", body: fd });
  return jsonOrThrow<IngestResponse>(r);
}

export async function ingestYouTube(url: string): Promise<IngestResponse> {
  const r = await fetch(`${API}/videos/youtube`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ url }),
  });
  return jsonOrThrow<IngestResponse>(r);
}

export async function getJob(videoId: number): Promise<JobInfo> {
  const r = await fetch(`${API}/videos/${videoId}/job`, { cache: "no-store" });
  return jsonOrThrow<JobInfo>(r);
}

export async function seek(
  videoId: number,
  timestamp: number,
): Promise<{ reprioritized: number }> {
  const r = await fetch(`${API}/videos/${videoId}/seek`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ timestamp }),
  });
  return jsonOrThrow(r);
}

export function hlsUrl(videoId: number): string {
  return `${API}/videos/${videoId}/index.m3u8`;
}

export function contiguousEnd(job: JobInfo): number {
  let end = 0;
  for (const c of [...job.chunks].sort((a, b) => a.index - b.index)) {
    if (c.status !== "completed") break;
    end = c.end_time;
  }
  return end;
}
