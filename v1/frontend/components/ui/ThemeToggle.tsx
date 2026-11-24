"use client";
import { useEffect, useState } from "react";

type Theme = "light" | "dark";

const icons: Record<Theme, JSX.Element> = {
  light: (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4" />
    </svg>
  ),
  dark: (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z" />
    </svg>
  ),
};

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  // The inline script in layout.tsx already set data-theme; read it back once mounted.
  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
  }, []);

  function choose(next: Theme) {
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch {}
  }

  return (
    <div role="group" aria-label="Colour theme" className="ml-1 inline-flex sm:ml-2 rounded-lg border border-line p-0.5">
      {(["light", "dark"] as Theme[]).map(t => (
        <button
          key={t}
          onClick={() => choose(t)}
          aria-pressed={theme === t}
          aria-label={t === "light" ? "Light theme" : "Dark theme"}
          className={`grid h-8 w-8 place-items-center rounded-md transition ${
            theme === t ? "bg-ink text-surface" : "text-muted hover:text-ink"
          }`}
        >
          {icons[t]}
        </button>
      ))}
    </div>
  );
}
