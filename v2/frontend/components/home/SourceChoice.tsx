import Link from "next/link";

const icons = {
  upload: (
    <path d="M12 16V4m0 0l-4 4m4-4l4 4M5 20h14" />
  ),
  link: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="4" />
      <path d="M10 9.5v5l4.5-2.5L10 9.5z" />
    </>
  ),
};

const options = [
  {
    href: "/upload",
    icon: "upload" as const,
    title: "Upload a video",
    text: "Bring an MP4 from your machine and start watching while it is being secured.",
  },
  {
    href: "/upload?tab=youtube",
    icon: "link" as const,
    title: "Use a YouTube link",
    text: "Paste a link and let CensorNet fetch, analyze, and prepare it for playback.",
  },
];

export default function SourceChoice() {
  return (
    <section aria-label="Choose a source" className="grid gap-4 md:grid-cols-2">
      {options.map((o) => (
        <Link
          key={o.href}
          href={o.href}
          className="group relative flex items-start gap-5 overflow-hidden rounded-2xl border border-line bg-surface p-6 transition duration-300 hover:-translate-y-1 hover:border-accent/50 hover:shadow-[0_20px_40px_-20px_rgb(var(--c-accent)/0.45)]"
        >
          <span
            aria-hidden
            className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-accent/10 blur-2xl transition duration-300 group-hover:bg-accent2/25"
          />
          <span className="relative grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-accent to-accent2 text-white shadow-lg shadow-accent/30">
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              {icons[o.icon]}
            </svg>
          </span>
          <div className="relative flex-1">
            <h2 className="font-display text-2xl font-semibold tracking-tight">{o.title}</h2>
            <p className="mt-2 max-w-sm text-sm leading-6 text-muted">{o.text}</p>
          </div>
          <span className="relative mt-1 text-2xl leading-none text-muted transition group-hover:translate-x-1 group-hover:text-accent" aria-hidden>→</span>
        </Link>
      ))}
    </section>
  );
}
