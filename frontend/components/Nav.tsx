import Link from "next/link";

export default function Nav() {
  return (
    <nav className="border-b border-white/10 bg-black/40 backdrop-blur sticky top-0 z-10">
      <div className="max-w-5xl mx-auto px-6 py-3 flex items-center gap-6">
        <Link href="/" className="font-semibold tracking-tight">
          🎬 Censor<span className="text-emerald-400">Stream</span>
        </Link>
        <div className="ml-auto flex gap-4 text-sm text-white/70">
          <Link href="/upload" className="hover:text-white">New</Link>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            className="hover:text-white"
          >
            API
          </a>
        </div>
      </div>
    </nav>
  );
}
