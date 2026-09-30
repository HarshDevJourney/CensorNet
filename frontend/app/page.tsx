"use client";
import Link from "next/link";

export default function Home() {
  return (
    <div className="space-y-10">
      <header className="pt-6">
        <h1 className="text-4xl font-semibold tracking-tight">
          Watch while it processes.
        </h1>
        <p className="mt-3 text-white/70 max-w-2xl">
          Upload a video or paste a YouTube link. The pipeline blurs nudity and
          beeps profanity chunk by chunk. Scrub ahead and the part you're watching
          gets processed next — no waiting for the whole file.
        </p>
      </header>

      <div className="grid md:grid-cols-2 gap-6">
        <Link
          href="/upload"
          className="rounded-2xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] p-8 transition"
        >
          <div className="text-3xl">📤</div>
          <h2 className="mt-3 text-xl font-medium">Upload a file</h2>
          <p className="mt-2 text-sm text-white/60">Drop an MP4 from your machine.</p>
        </Link>

        <Link
          href="/upload?tab=youtube"
          className="rounded-2xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] p-8 transition"
        >
          <div className="text-3xl">▶️</div>
          <h2 className="mt-3 text-xl font-medium">Paste a YouTube link</h2>
          <p className="mt-2 text-sm text-white/60">
            We'll fetch it with yt-dlp and process it the same way.
          </p>
        </Link>
      </div>

      <section className="rounded-2xl border border-white/10 p-6 text-sm text-white/60">
        <h3 className="text-white/90 font-medium mb-2">How it works</h3>
        <ol className="list-decimal list-inside space-y-1">
          <li>Audio is transcribed once and profanity is flagged.</li>
          <li>The video is split into ~6s chunks stored in Postgres as a priority queue.</li>
          <li>Only a few chunks are dispatched at a time; each is blurred + beeped + encoded to HLS.</li>
          <li>The browser plays a growing HLS playlist — scrubbing reprioritizes pending chunks.</li>
        </ol>
      </section>
    </div>
  );
}
