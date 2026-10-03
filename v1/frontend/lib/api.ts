export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type ChunkStatus = "pending" | "processing" | "completed" | "failed";

export interface ChunkInfo {
  index: number;
  start_time: number;
  end_time: number;
  status: ChunkStatus;
  priority: number | null; // queue score while pending (lower = sooner)
}

export interface JobInfo {
  id: number;
  video_id: number;
  status: string;
  error: string | null;
  duration: number;
  source_type: "upload" | "youtube";
  playhead: number;
  completed: number;
  total: number;
  workers: number;
  queue_length: number;
  chunks: ChunkInfo[];
}

export interface IngestResponse {
  id: number;
  source_type: "upload" | "youtube";
  source_url: string | null;
  duration: number;
  playlist_url: string;
}

async function jsonOrThrow<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${await r.text()}`);
  return r.json();
}

export async function uploadVideo(file: File): Promise<IngestResponse> {
  const fd = new FormData();
  fd.append("file", file);
  return jsonOrThrow(await fetch(`${API}/videos/upload`, { method: "POST", body: fd }));
}

export async function ingestYouTube(url: string): Promise<IngestResponse> {
  return jsonOrThrow(
    await fetch(`${API}/videos/youtube`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ url }),
    }),
  );
}

export async function getJob(videoId: number): Promise<JobInfo> {
  return jsonOrThrow(await fetch(`${API}/videos/${videoId}/job`, { cache: "no-store" }));
}

/** User jumped: this chunk (and the next ones) go to the front of the Redis queue. */
export async function seek(videoId: number, timestamp: number) {
  return jsonOrThrow<{ chunk: number; reprioritized: number; ready: boolean }>(
    await fetch(`${API}/videos/${videoId}/seek`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ timestamp }),
    }),
  );
}

/** Periodic "I am watching here" ping while playing. */
export function playhead(videoId: number, timestamp: number): void {
  fetch(`${API}/videos/${videoId}/playhead`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ timestamp }),
  }).catch(() => {});
}

export function hlsUrl(videoId: number): string {
  return `${API}/videos/${videoId}/index.m3u8`;
}

export function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60).toString().padStart(2, "0");
  return `${m}:${sec}`;
}
