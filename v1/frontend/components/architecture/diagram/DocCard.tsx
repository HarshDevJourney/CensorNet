import { BOX, rectProps } from "@/lib/arch/layout";
import { clock, rowRecord, type Sim } from "@/lib/arch/engine";

/** One-line rendering of a column value for the compact in-diagram card. */
function compact(key: string, v: unknown): { text: string; tone: "str" | "num" | "null" | "bool" } {
  if (v === null || v === undefined) return { text: "null", tone: "null" };
  if (typeof v === "boolean") return { text: String(v), tone: "bool" };
  if (typeof v === "number") return { text: String(v), tone: "num" };
  if (typeof v === "string") return { text: key.endsWith("_at") ? v.slice(11, 23) + "Z" : `"${v}"`, tone: "str" };
  if (Array.isArray(v)) {
    if (v.length === 0) return { text: "[]", tone: "null" };
    const first = v[0] as Record<string, unknown>;
    const body = key === "detections"
      ? `${first.label} ${first.score} @${clock(Number(first.t_start))}`
      : `${(first.words as string[]).join(",")} @${clock(Number(first.start))}`;
    return { text: `[${body}${v.length > 1 ? ` +${v.length - 1}` : ""}]`, tone: "str" };
  }
  return { text: JSON.stringify(v), tone: "str" };
}
const TONE = { str: "fill-accent", num: "fill-ink", null: "fill-muted/70", bool: "fill-working" } as const;
const SHOWN = ["id", "status", "worker", "attempts", "process_ms", "censored", "detections", "audio_events"];

export default function DocCard({ sim, shown, interactive }: { sim: Sim; shown: number | null; interactive: boolean }) {
  const { doc } = BOX;
  const rec = shown === null ? null : rowRecord(sim, shown);
  const fields = rec?.filter((f) => SHOWN.includes(f.key)) ?? [];
  return (
    <g>
      <rect {...rectProps(doc)} rx={14} className="fill-paper/55 stroke-pg/60" />
      <text x={doc.x + 16} y={doc.y + 24} fontSize={11} fontWeight={650} className="fill-ink font-display">
        {rec ? `chunks \u00B7 row ${shown}` : "chunks \u00B7 one row = one document"}
      </text>
      <text x={doc.x + doc.w - 14} y={doc.y + 24} textAnchor="end" fontSize={9.5} className="fill-muted font-mono">
        {rec ? (interactive ? "full view below" : "latest update") : ""}
      </text>
      {!rec && (
        <text x={doc.x + 16} y={doc.y + 62} fontSize={11} className="fill-muted">
          {interactive ? "Click a row in the table above to see exactly" : "Rows appear here as chunks are processed."}
        </text>
      )}
      {!rec && interactive && (
        <text x={doc.x + 16} y={doc.y + 80} fontSize={11} className="fill-muted">what PostgreSQL stores for that chunk.</text>
      )}
      {fields.map((f, i) => {
        const c = compact(f.key, f.value);
        return (
          <g key={f.key} transform={`translate(${doc.x + 16} ${doc.y + 44 + i * 11.8})`}>
            <text fontSize={9.5} className="fill-muted font-mono">{f.key}</text>
            <text x={92} fontSize={9.5} className={`${TONE[c.tone]} font-mono`}>{c.text.length > 34 ? c.text.slice(0, 33) + "\u2026" : c.text}</text>
          </g>
        );
      })}
    </g>
  );
}
