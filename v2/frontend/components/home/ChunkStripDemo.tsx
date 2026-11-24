const COUNT = 48;
const PLAYHEAD = 14;
const READY_UNTIL = 24; // chunks the queue has reached; the rest stay queued

/** Decorative preview of the real chunk grid: segments are censored in order, ahead of the playhead. */
export default function ChunkStripDemo() {
  return (
    <div aria-hidden className="rounded-2xl border border-line bg-[#101318] p-4 dark:bg-surface sm:p-5">
      <div className="flex gap-[3px]">
        {Array.from({ length: COUNT }).map((_, i) => (
          <div key={i} className="relative flex-1">
            <div
              className={`h-10 rounded-[3px] sm:h-14 ${i < READY_UNTIL ? "bg-white/15 animate-fill" : "bg-white/15"}`}
              style={i < READY_UNTIL ? { animationDelay: `${300 + i * 70}ms` } : undefined}
            />
            {i === PLAYHEAD && (
              <div className="absolute -inset-x-px -bottom-2 -top-2 rounded-[4px] ring-2 ring-white" />
            )}
          </div>
        ))}
      </div>
      <div className="mt-4 flex justify-between text-xs text-white/55">
        <span>Censored and ready</span>
        <span>Queued behind the playhead</span>
      </div>
    </div>
  );
}
