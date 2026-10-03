import Link from "next/link";

export default function Nav() {
  return (
    <nav className="sticky top-0 z-10 border-b border-white/10 bg-[#080b10]/75 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-4">
        <Link href="/" className="group flex items-center gap-2 font-semibold tracking-tight">
          <span className="grid h-8 w-8 place-items-center rounded-xl bg-emerald-400/15 text-emerald-300 ring-1 ring-emerald-300/25 transition group-hover:bg-emerald-400/25">
            CN
          </span>
          <span className="text-white">Censor<span className="text-emerald-400">Net</span></span>
        </Link>
        <div className="ml-auto flex items-center gap-5 text-sm text-white/60">
          <Link href="/upload" className="transition hover:text-white">New project</Link>
          <a
            href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`}
            target="_blank"
            rel="noreferrer"
            className="transition hover:text-white"
          >
            API
          </a>
        </div>
      </div>
    </nav>
  );
}
