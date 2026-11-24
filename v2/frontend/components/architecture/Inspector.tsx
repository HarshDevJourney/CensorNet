import { VIDEO_ID, clock, rowRecord, type DocField, type Sim } from "@/lib/arch/engine";

const FIELDS: { key: string; who: string; what: string }[] = [
  { key: "id", who: "database", what: "Primary key of the row (auto-numbered)." },
  { key: "video_id", who: "API", what: "Which video this slice belongs to." },
  { key: "index", who: "worker", what: "Position of the chunk. Chunk n covers n\u00D74 s to n\u00D74+4 s." },
  { key: "status", who: "worker", what: "pending \u2192 processing \u2192 completed (or failed). Changing it is the atomic claim." },
  { key: "attempts", who: "worker", what: "How often a worker started it. After 3 failed tries the chunk is marked failed." },
  { key: "worker", who: "worker", what: "Which process handled it." },
  { key: "started_at", who: "worker", what: "When the claim happened." },
  { key: "finished_at", who: "worker", what: "When the result was saved." },
  { key: "process_ms", who: "worker", what: "Total time spent on this chunk." },
  { key: "censored", who: "worker", what: "True if anything was blurred or beeped." },
  { key: "detections", who: "worker", what: "Each blur: label, score, start/end time, box (as fractions of the frame)." },
  { key: "audio_events", who: "worker", what: "Each beep: start/end time and the words that were replaced." },
  { key: "error", who: "worker", what: "Last failure message, if any." },
];

function Value({ v, depth = 0 }: { v: unknown; depth?: number }) {
  if (v === null || v === undefined) return <span className="text-muted/80">null</span>;
  if (typeof v === "number") return <span className="text-ink">{v}</span>;
  if (typeof v === "boolean") return <span className="text-working">{String(v)}</span>;
  if (typeof v === "string") return <span className="text-accent">&quot;{v}&quot;</span>;
  if (Array.isArray(v)) {
    if (v.length === 0) return <span className="text-muted/80">[]</span>;
    return (
      <span>
        [
        {v.map((item, i) => (
          <div key={i} style={{ paddingLeft: 16 }}>
            <Value v={item} depth={depth + 1} />
            {i < v.length - 1 ? "," : ""}
          </div>
        ))}
        ]
      </span>
    );
  }
  const entries = Object.entries(v as Record<string, unknown>);
  return (
    <span>
      {"{"}
      {entries.map(([k, val], i) => (
        <div key={k} style={{ paddingLeft: 16 }}>
          <span className="text-muted">{k}</span>: <Value v={val} depth={depth + 1} />
          {i < entries.length - 1 ? "," : ""}
        </div>
      ))}
      {"}"}
    </span>
  );
}

/** What PostgreSQL really stores for one chunk, plus who writes each column. */
export default function Inspector({ sim, shown, picked }: { sim: Sim; shown: number | null; picked: boolean }) {
  const rec: DocField[] | null = shown === null ? null : rowRecord(sim, shown);
  const byKey = new Map((rec ?? []).map((f) => [f.key, f.value]));

  return (
    <section className="rounded-2xl border border-line bg-surface p-5 sm:p-6" aria-label="Chunk row inspector">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-xl font-semibold tracking-tight">
          <span className="text-pg">PostgreSQL</span> row inspector
        </h3>
        <span className="text-xs text-muted">{picked ? "you opened this row" : "following the latest update \u00B7 click a row in the table to pin one"}</span>
      </div>

      {!rec || shown === null ? (
        <p className="mt-5 rounded-xl border border-dashed border-line p-6 text-sm text-muted">
          No chunk rows yet. They appear when the worker has split the video. Then click one in the PostgreSQL table to read what is stored.
        </p>
      ) : (
        <div className="mt-4 grid gap-5 lg:grid-cols-[1.05fr_1fr]">
          <div>
            <p className="mb-2 overflow-x-auto whitespace-nowrap font-mono text-[11px] text-muted">
              SELECT * FROM chunks WHERE video_id = {VIDEO_ID} AND index = {shown};
            </p>
            <div className="overflow-x-auto rounded-xl border border-line bg-paper/60 p-4 font-mono text-[12px] leading-[1.7]">
              {"{"}
              {rec.map((f, i) => (
                <div key={f.key} style={{ paddingLeft: 16 }}>
                  <span className="text-muted">{f.key}</span>: <Value v={f.value} />
                  {i < rec.length - 1 ? "," : ""}
                </div>
              ))}
              {"}"}
            </div>
            <p className="mt-2 text-xs text-muted">
              Chunk {shown} covers {clock(shown * 4)}&ndash;{clock(shown * 4 + 4)} of the video.
            </p>
          </div>

          <dl className="grid content-start gap-x-3 gap-y-2.5 text-sm sm:grid-cols-1">
            {FIELDS.map((f) => {
              const v = byKey.get(f.key);
              const filled = !(v === null || v === undefined || v === 0 || v === false || (Array.isArray(v) && v.length === 0));
              return (
                <div key={f.key} className="grid grid-cols-[8.5rem_1fr] items-baseline gap-3">
                  <dt className={`font-mono text-[12px] ${filled ? "text-ink" : "text-muted"}`}>
                    {f.key}
                    <span className="ml-1.5 rounded bg-ink/5 px-1 py-0.5 align-middle font-sans text-[9px] uppercase tracking-wide text-muted">{f.who}</span>
                  </dt>
                  <dd className="text-[13px] leading-5 text-muted">{f.what}</dd>
                </div>
              );
            })}
          </dl>
        </div>
      )}
    </section>
  );
}
