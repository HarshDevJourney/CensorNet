import { STAGES, type Sim } from "@/lib/arch/engine";

/** The seven stages, matching the numbered badges on the diagram. A stage lights up while it is happening. */
export default function Stepper({ sim }: { sim: Sim }) {
  return (
    <ol className="flex gap-1.5 overflow-x-auto pb-1" aria-label="Pipeline stages">
      {STAGES.map((label, i) => {
        const n = i + 1;
        const active = sim.focus.includes(n) || (sim.lastFocus[n] !== undefined && sim.tick - sim.lastFocus[n] < 2);
        return (
          <li
            key={label}
            className={`flex shrink-0 items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors duration-300 ${
              active ? "border-accent bg-accent text-surface" : "border-line text-muted"
            }`}
          >
            <span className={`grid h-4 w-4 place-items-center rounded-full text-[10px] font-bold ${active ? "bg-surface text-accent" : "bg-ink/10 text-ink"}`}>{n}</span>
            {label}
          </li>
        );
      })}
    </ol>
  );
}
