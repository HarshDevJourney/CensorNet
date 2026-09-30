"use client";
import Hls from "hls.js";
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { hlsUrl } from "@/lib/api";

export interface VideoPlayerHandle {
  seek: (t: number) => void;
  queueSeek: (t: number) => void;
}

interface Props {
  videoId: number;
  readyEnd: number;
  totalDuration: number;
}

const VideoPlayer = forwardRef<VideoPlayerHandle, Props>(
  ({ videoId, readyEnd, totalDuration }, ref) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const hlsRef = useRef<Hls | null>(null);
    const pendingRef = useRef<number | null>(null);
    const [waiting, setWaiting] = useState(false);

    useImperativeHandle(ref, () => ({
      seek(t) {
        if (videoRef.current) videoRef.current.currentTime = t;
      },
      queueSeek(t) {
        pendingRef.current = t;
        setWaiting(true);
      },
    }));

    useEffect(() => {
      const video = videoRef.current;
      if (!video) return;
      const url = hlsUrl(videoId);

      if (Hls.isSupported()) {
        const hls = new Hls({
          liveSyncDurationCount: 3,
          liveMaxLatencyDurationCount: 10,
          maxBufferLength: 30,
          backBufferLength: 30,
          lowLatencyMode: false,
          manifestLoadingMaxRetry: 6,
          fragLoadingMaxRetry: 8,
        });
        hlsRef.current = hls;

        hls.on(Hls.Events.ERROR, (_, data) => {
          if (!data.fatal) return;
          if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
            hls.startLoad();
          } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
            hls.recoverMediaError();
          } else {
            hls.destroy();
            hlsRef.current = null;
          }
        });

        hls.loadSource(url);        // ← called ONCE
        hls.attachMedia(video);
      } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = url;
      }

      return () => {
        hlsRef.current?.destroy();
        hlsRef.current = null;
      };
    }, [videoId]);

    useEffect(() => {
      const t = pendingRef.current;
      if (t == null) return;
      if (t <= readyEnd) {
        if (videoRef.current) videoRef.current.currentTime = t;
        pendingRef.current = null;
        setWaiting(false);
      }
    }, [readyEnd]);

    return (
      <div className="relative rounded-2xl overflow-hidden bg-black aspect-video">
        <video ref={videoRef} controls playsInline className="w-full h-full" />

        {waiting && (
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center pointer-events-none">
            <div className="text-center">
              <div className="animate-spin h-8 w-8 border-2 border-white/30 border-t-white rounded-full mx-auto" />
              <div className="mt-3 text-sm text-white/80">
                Processing the part you jumped to…
              </div>
              <div className="text-xs text-white/50 mt-1">
                ready up to {formatTime(readyEnd)} / {formatTime(totalDuration)}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }
);

VideoPlayer.displayName = "VideoPlayer";
export default VideoPlayer;

function formatTime(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60).toString().padStart(2, "0");
  return `${m}:${sec}`;
}
