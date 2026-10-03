import { ButtonLink } from "@/components/ui/Button";
import ChunkStripDemo from "./ChunkStripDemo";

export default function Hero() {
  return (
    <header className="space-y-12">
      <div className="max-w-4xl">
        <h1 className="font-display text-5xl font-semibold leading-[0.98] tracking-[-0.035em] text-ink sm:text-7xl lg:text-[5.5rem]">
          Cleaner viewing, without the wait.
        </h1>
        <p className="mt-7 max-w-xl text-lg leading-8 text-muted">
          CensorNet detects sensitive visuals and language as your video plays. Jump anywhere, and the
          exact moment you need moves to the front of the queue.
        </p>
        <div className="mt-9 flex flex-wrap gap-3">
          <ButtonLink href="/upload">Start a project</ButtonLink>
          <ButtonLink href="#how-it-works" variant="secondary">See how it works</ButtonLink>
        </div>
      </div>
      {/* <ChunkStripDemo /> */}
    </header>
  );
}
