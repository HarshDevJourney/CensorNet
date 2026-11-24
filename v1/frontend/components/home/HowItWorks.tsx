const steps = [
  { title: "Detect", text: "Visual and audio analysis" },
  { title: "Protect", text: "Blur and beep sensitive moments" },
  { title: "Stream", text: "Play each ready segment" },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-24 grid gap-10 lg:grid-cols-[1fr_1.2fr]">
      <div>
        <h2 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
          Safety that keeps up with the screen.
        </h2>
        <p className="mt-4 max-w-md leading-7 text-muted">
          Every video is split into small, prioritized tasks. The worker queue follows your playhead, so you
          can explore instead of waiting.
        </p>
      </div>
      <ol className="space-y-0 border-l-2 border-accent/40 pl-6">
        {steps.map((s, i) => (
          <li key={s.title} className="relative pb-8 last:pb-0">
            <span className="absolute -left-[2.0625rem] top-0.5 grid h-5 w-5 place-items-center rounded-full bg-gradient-to-br from-accent to-accent2 text-[11px] font-semibold text-white shadow-md shadow-accent/30">
              {i + 1}
            </span>
            <h3 className="font-display text-xl font-semibold">{s.title}</h3>
            <p className="mt-1 text-muted">{s.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
