"use client";
import { useState } from "react";

interface Props {
  duration: number;
  readyEnd: number;
  onSeek: (t: number) => void;
}

export default function SeekBar({ duration, readyEnd, onSeek }: Props) {
  const [val, setVal] = useState(0);

  if (duration <= 0) return null;

  const readyPct = (readyEnd / duration) * 100;

  return (
    <div className="space-y-2">
      <div className="relative h-8 flex items-center">
        <div className="absolute inset-x-0 h-1.5 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full bg-emerald-500/60"
            style={{ width: `${readyPct}%` }}
          />
        </div>
        <input
          type="range"
          min={0}
          max={duration}
          step={0.1}
          value={val}
          onChange={e => setVal(Number(e.target.value))}
          onMouseUp={e => onSeek(Number((e.target as HTMLInputElement).value))}
          onTouchEnd={e => onSeek(Number((e.target as HTMLInputElement).value))}
          className="relative w-full appearance-none bg-transparent cursor-pointer
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:bg-white
                     [&::-webkit-slider-thumb]:shadow"
        />
      </div>
      <div className="flex justify-between text-xs text-white/50">
        <span>Processed: {formatTime(readyEnd)}</span>
        <span>Total: {formatTime(duration)}</span>
      </div>
    </div>
  );
}

function formatTime(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60).toString().padStart(2, "0");
  return `${m}:${sec}`;
}
