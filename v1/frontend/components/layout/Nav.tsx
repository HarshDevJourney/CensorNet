import Link from "next/link";
import Logo from "@/components/ui/Logo";
import ThemeToggle from "@/components/ui/ThemeToggle";

const API_DOCS = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`;

export default function Nav() {
  return (
    <nav className="sticky top-0 z-20 border-b border-line bg-paper/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3.5 sm:gap-6 sm:px-6">
        <Link href="/" className="rounded-md" aria-label="CensorNet home">
          <Logo />
        </Link>
        <div className="ml-auto flex items-center gap-0.5 text-sm sm:gap-1">
          <Link href="/upload" className="whitespace-nowrap rounded-lg px-2 py-2 font-medium text-ink transition hover:bg-ink/5 sm:px-3">
            <span className="sm:hidden">New</span>
            <span className="hidden sm:inline">New project</span>
          </Link>
          <Link href="/architecture" className="rounded-lg px-2 py-2 text-muted transition hover:bg-ink/5 hover:text-ink sm:px-3">
            Architecture
          </Link>
          <a
            href={API_DOCS}
            target="_blank"
            rel="noreferrer"
            className="hidden rounded-lg px-3 py-2 text-muted transition hover:bg-ink/5 hover:text-ink sm:block"
          >
            API
          </a>
          <ThemeToggle />
        </div>
      </div>
    </nav>
  );
}
