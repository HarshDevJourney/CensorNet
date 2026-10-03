export type Tab = "file" | "youtube";

const labels: Record<Tab, string> = { file: "Upload file", youtube: "YouTube URL" };

export default function SourceTabs({ tab, onChange }: { tab: Tab; onChange: (t: Tab) => void }) {
  return (
    <div role="tablist" aria-label="Video source" className="mb-6 inline-flex rounded-xl border border-line bg-paper p-1">
      {(["file", "youtube"] as Tab[]).map(t => (
        <button
          key={t}
          role="tab"
          aria-selected={tab === t}
          onClick={() => onChange(t)}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            tab === t ? "bg-ink text-surface" : "text-muted hover:text-ink"
          }`}
        >
          {labels[t]}
        </button>
      ))}
    </div>
  );
}
