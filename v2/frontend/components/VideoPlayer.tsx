"use client";
import Hls from "hls.js";
import { useEffect, useRef, useState } from "react";
import { hlsUrl, playhead, seek } from "@/lib/api";

interface Props {
  videoId: number;
  /** only start loading when the backend has published the playlist */
  ready: boolean;
}

/**
 * The player never needs to know which chunks are processed. It asks for segments like for any HLS
 * stream; the server holds a request until that chunk is censored and moves it to the front of the Redis
 * queue. We additionally tell the server about seeks and about the playback position, so the chunks that
 * come AFTER the playhead are always the next ones to be processed.
 */
export default function VideoPlayer({ videoId, ready }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [buffering, setBuffering] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !ready) return;
    const url = hlsUrl(videoId);
    let hls: Hls | null = null;

    if (Hls.isSupported()) {
      // Segments may have to wait for a worker, so give them a long time-to-first-byte.
      const patient = {
        default: {
          maxTimeToFirstByteMs: 90_000,
          maxLoadTimeMs: 120_000,
          timeoutRetry: { maxNumRetry: 5, retryDelayMs: 0, maxRetryDelayMs: 0 },
          errorRetry: { maxNumRetry: 6, retryDelayMs: 1000, maxRetryDelayMs: 8000 },
        },
      };
      hls = new Hls({
        maxBufferLength: 20, // seconds buffered ahead (= how many chunks the player pulls early)
        maxMaxBufferLength: 40,
        backBufferLength: 30,
        manifestLoadPolicy: { default: { ...patient.default, maxTimeToFirstByteMs: 20_000 } },
        fragLoadPolicy: patient,
      });
      hls.on(Hls.Events.ERROR, (_e, data) => {
        if (!data.fatal) return;
        if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
          setError(`Network/segment error: ${data.details}. Retrying…`);
          hls?.startLoad();
        } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
          hls?.recoverMediaError();
        } else {
          setError(`Playback error: ${data.details}`);
          hls?.destroy();
        }
      });
      hls.on(Hls.Events.FRAG_LOADED, () => setError(null));
      hls.loadSource(url);
      hls.attachMedia(video);
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = url; // Safari
    }

    const onSeeking = () => seek(videoId, video.currentTime).catch(() => {});
    const onWaiting = () => setBuffering(true);
    const onPlaying = () => setBuffering(false);
    video.addEventListener("seeking", onSeeking);
    video.addEventListener("waiting", onWaiting);
    video.addEventListener("playing", onPlaying);
    video.addEventListener("canplay", onPlaying);
    const ping = setInterval(() => {
      if (!video.paused) playhead(videoId, video.currentTime);
    }, 3000);

    return () => {
      clearInterval(ping);
      video.removeEventListener("seeking", onSeeking);
      video.removeEventListener("waiting", onWaiting);
      video.removeEventListener("playing", onPlaying);
      video.removeEventListener("canplay", onPlaying);
      hls?.destroy();
    };
  }, [videoId, ready]);

  return (
    <div className="relative rounded-2xl overflow-hidden bg-black aspect-video">
      <video ref={videoRef} controls playsInline className="w-full h-full" />
      {(!ready || buffering) && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <div className="animate-spin h-8 w-8 border-2 border-white/30 border-t-white rounded-full mx-auto" />
            <div className="mt-3 text-sm text-white/80">
              {ready ? "Censoring this part…" : "Preparing video…"}
            </div>
          </div>
        </div>
      )}
      {error && (
        <div className="absolute bottom-0 inset-x-0 bg-red-900/80 text-red-100 text-xs px-3 py-2">{error}</div>
      )}
    </div>
  );
}
