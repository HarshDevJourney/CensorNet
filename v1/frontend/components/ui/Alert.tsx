import type { ReactNode } from "react";

type Tone = "error" | "warning";

const tones: Record<Tone, string> = {
  error: "border-failed/40 bg-failed/10 text-[#7d1d16] dark:text-[#ffb4ac]",
  warning: "border-working/50 bg-working/15 text-[#6b4a00] dark:text-[#ffd98a]",
};

export default function Alert({ tone = "error", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`rounded-xl border px-4 py-3 text-sm ${tones[tone]}`}>
      {children}
    </div>
  );
}
