import type { ChunkStatus } from "@/lib/api";

/** Tailwind background class for each chunk state. Shared by the progress bar, grid and legend. */
export const chunkColor: Record<ChunkStatus, string> = {
  completed: "bg-ready",
  processing: "bg-working",
  failed: "bg-failed",
  pending: "bg-queued",
};
