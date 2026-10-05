import type { Sim } from "@/lib/arch/engine";

/** One sentence that explains what is happening right now. Fixed height so the page does not jump. */
export default function Caption({ sim }: { sim: Sim }) {
  const c = sim.caption;
  return (
    <div className="flex min-h-[4.75rem] items-start gap-3 rounded-xl border border-line bg-surface/80 px-4 py-3 backdrop-blur" aria-live="polite">
      <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-gradient-to-br from-accent to-accent2 text-xs font-bold text-white shadow-md shadow-accent/30">{c.step}</span>
      <div>
        <p className="font-display text-base font-semibold leading-tight">{c.title}</p>
        <p className="mt-1 text-sm leading-6 text-muted">{c.text}</p>
      </div>
    </div>
  );
}
