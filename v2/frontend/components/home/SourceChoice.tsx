import Link from "next/link";

const options = [
  {
    href: "/upload",
    title: "Upload a video",
    text: "Bring an MP4 from your machine and start watching while it is being secured.",
  },
  {
    href: "/upload?tab=youtube",
    title: "Use a YouTube link",
    text: "Paste a link and let CensorNet fetch, analyze, and prepare it for playback.",
  },
];

export default function SourceChoice() {
  return (
    <section aria-label="Choose a source" className="grid overflow-hidden rounded-2xl border border-line bg-surface md:grid-cols-2">
      {options.map((o, i) => (
        <Link
          key={o.href}
          href={o.href}
          className={`group flex items-start justify-between gap-6 p-7 transition hover:bg-ink hover:text-surface ${
            i > 0 ? "border-t border-line md:border-l md:border-t-0" : ""
          }`}
        >
          <div>
            <h2 className="font-display text-2xl font-semibold tracking-tight">{o.title}</h2>
            <p className="mt-2 max-w-sm text-sm leading-6 text-muted transition group-hover:text-surface/70">{o.text}</p>
          </div>
          <span className="mt-1 text-2xl leading-none transition group-hover:translate-x-1" aria-hidden>→</span>
        </Link>
      ))}
    </section>
  );
}
