/** Wordmark: the bar over the "e" is a redaction bar. */
export default function Logo() {
  return (
    <span className="flex items-center gap-2.5">
      <span className="relative grid h-8 w-8 place-items-center rounded-lg bg-ink" aria-hidden>
        <span className="h-1.5 w-4 rounded-sm bg-surface" />
        <span className="absolute bottom-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-accent" />
      </span>
      <span className="font-display text-lg font-semibold tracking-tight text-ink">CensorNet</span>
    </span>
  );
}
