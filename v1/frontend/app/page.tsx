"use client";
import Link from "next/link";

export default function Home() {
  return (
    <div className="space-y-16">
      <header className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.045] px-7 py-12 shadow-2xl shadow-emerald-950/20 sm:px-12 sm:py-16">
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-emerald-400/10 blur-3xl" />
        <div className="relative max-w-3xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-emerald-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_12px_currentColor]" />
            Intelligent video safety
          </div>
          <h1 className="text-5xl font-semibold tracking-[-0.04em] text-white sm:text-7xl">
            Cleaner viewing,
            <span className="block bg-gradient-to-r from-emerald-300 via-teal-200 to-sky-300 bg-clip-text text-transparent">
              without the wait.
            </span>
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-7 text-white/65 sm:text-lg">
            CensorNet detects sensitive visuals and language as your video plays. Jump anywhere,
            and the exact moment you need moves to the front of the queue.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link href="/upload" className="rounded-xl bg-emerald-400 px-5 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-emerald-950/40 transition hover:bg-emerald-300">
              Start a project <span className="ml-2">→</span>
            </Link>
            <a href="#how-it-works" className="rounded-xl border border-white/15 bg-white/5 px-5 py-3 text-sm font-medium text-white/80 transition hover:bg-white/10 hover:text-white">
              See how it works
            </a>
          </div>
        </div>
      </header>

      <section className="grid gap-5 md:grid-cols-2">
        <Link
          href="/upload"
          className="group rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.08] to-white/[0.02] p-7 transition hover:-translate-y-1 hover:border-emerald-300/30 hover:bg-white/[0.09]"
        >
          <div className="flex items-center justify-between">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-400/15 text-xl text-emerald-300">↑</span>
            <span className="text-xl text-white/30 transition group-hover:translate-x-1 group-hover:text-emerald-300">↗</span>
          </div>
          <h2 className="mt-7 text-xl font-medium text-white">Upload a video</h2>
          <p className="mt-2 text-sm leading-6 text-white/55">Bring an MP4 from your machine and start watching while it is being secured.</p>
        </Link>

        <Link
          href="/upload?tab=youtube"
          className="group rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.08] to-white/[0.02] p-7 transition hover:-translate-y-1 hover:border-sky-300/30 hover:bg-white/[0.09]"
        >
          <div className="flex items-center justify-between">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-sky-400/15 text-xl text-sky-300">▶</span>
            <span className="text-xl text-white/30 transition group-hover:translate-x-1 group-hover:text-sky-300">↗</span>
          </div>
          <h2 className="mt-7 text-xl font-medium text-white">Use a YouTube link</h2>
          <p className="mt-2 text-sm leading-6 text-white/55">Paste a link and let CensorNet fetch, analyze, and prepare it for playback.</p>
        </Link>
      </section>

      <section id="how-it-works" className="grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Built for real-time playback</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">Safety that keeps up with the screen.</h2>
          <p className="mt-4 text-sm leading-7 text-white/55">Every video is split into small, prioritized tasks. The worker queue follows your playhead, so you can explore instead of waiting.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {[
            ["01", "Detect", "Visual and audio analysis"],
            ["02", "Protect", "Blur and beep sensitive moments"],
            ["03", "Stream", "Play each ready segment"],
          ].map(([number, title, text]) => (
            <div key={number} className="rounded-2xl border border-white/10 bg-black/20 p-5">
              <div className="text-xs font-semibold text-emerald-300">{number}</div>
              <h3 className="mt-8 font-medium text-white">{title}</h3>
              <p className="mt-2 text-xs leading-5 text-white/45">{text}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
