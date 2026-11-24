"use client";
import type { Speed } from "@/lib/arch/useSimulation";

interface Props {
  playing: boolean;
  speed: Speed;
  canSeek: boolean;
  onToggle: () => void;
  onRestart: () => void;
  onSpeed: (s: Speed) => void;
  onJump: (dir: 1 | -1) => void;
}

const btn =
  "inline-flex items-center gap-2 rounded-lg border border-ink/20 px-3.5 py-2 text-sm font-medium text-ink transition hover:border-ink hover:bg-ink/5 disabled:cursor-not-allowed disabled:opacity-40";

const speedOptions: Array<{ value: Speed; label: number }> = [
  { value: 0.2, label: 0.5 },
  { value: 0.5, label: 1 },
  { value: 1, label: 1.5 },
];

export default function Controls({ playing, speed, canSeek, onToggle, onRestart, onSpeed, onJump }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button onClick={onToggle} className={`${btn} bg-ink text-surface shadow-[0_8px_24px_-8px_rgb(var(--c-accent)/0.6)] hover:bg-ink/90 hover:text-surface`} aria-label={playing ? "Pause animation" : "Play animation"}>
        {playing ? (
          <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="currentColor" aria-hidden><rect x="3" y="2" width="3.5" height="12" rx="1" /><rect x="9.5" y="2" width="3.5" height="12" rx="1" /></svg>
        ) : (
          <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="currentColor" aria-hidden><path d="M4 2.5v11l9-5.5z" /></svg>
        )}
        {playing ? "Pause" : "Play"}
      </button>
      <button onClick={onRestart} className={btn}>
        <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden><path d="M3 8a5 5 0 1 0 1.6-3.7M3 2.5V5h2.5" /></svg>
        Restart
      </button>

      <div role="group" aria-label="Speed" className="inline-flex rounded-lg border border-line bg-surface/70 p-0.5 backdrop-blur">
        {speedOptions.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => onSpeed(value)}
            aria-pressed={speed === value}
            className={`rounded-md px-2.5 py-1.5 text-xs font-semibold transition ${speed === value ? "bg-ink text-surface" : "text-muted hover:text-ink"}`}
          >
            {label}&times;
          </button>
        ))}
      </div>

      <span className="mx-1 hidden h-6 w-px bg-line sm:block" />
      <button onClick={() => onJump(1)} disabled={!canSeek} className={btn}>Seek ahead {"\u00BB"}</button>
      <button onClick={() => onJump(-1)} disabled={!canSeek} className={btn}>{"\u00AB"} Seek back</button>
    </div>
  );
}
