import { ButtonLink } from "@/components/ui/Button";
import HeroScene from "./HeroScene";

const chips = ["Visual detection", "Language detection", "MP4 and YouTube"];

export default function Hero() {
  return (
    <header className="relative isolate">
      <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="max-w-2xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface/70 px-3 py-1 text-xs font-medium text-muted backdrop-blur">
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-ready" />
            Live scanning while you watch
          </span>
          <h1 className="mt-6 font-display text-5xl font-semibold leading-[0.98] tracking-[-0.035em] text-ink sm:text-7xl lg:text-[5.25rem]">
            Watch anything, without <span className="text-gradient">surprises.</span>
          </h1>
          <p className="mt-7 max-w-xl text-lg leading-8 text-muted">
            CensorNet scans video for sensitive visuals and language while it plays. Jump to any moment and
            that part gets checked first.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <ButtonLink href="/upload">Start a project</ButtonLink>
            <ButtonLink href="#how-it-works" variant="secondary">See how it works</ButtonLink>
          </div>
          <ul className="mt-8 flex flex-wrap gap-2">
            {chips.map((c) => (
              <li key={c} className="rounded-full border border-line bg-surface/60 px-3 py-1 text-xs font-medium text-muted backdrop-blur">
                {c}
              </li>
            ))}
          </ul>
        </div>

        <HeroScene />
      </div>
    </header>
  );
}
