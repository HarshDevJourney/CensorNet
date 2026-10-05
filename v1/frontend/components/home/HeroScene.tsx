"use client";
import { useEffect, useRef } from "react";

const SEGMENTS = 22;
const READY = 13;
const PLAYHEAD = 13;

/**
 * Decorative 3D "protected video" scene (pure CSS 3D, theme-token colours).
 * Motion: one requestAnimationFrame loop eases the scene toward the pointer anywhere on the page (so it
 * turns freely in every direction), keeps a gentle idle sway, and never snaps back when the pointer leaves.
 */
export default function HeroScene() {
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = root.current;
    if (!el) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let tx = 0, ty = 0;      // target from the pointer, -0.5..0.5
    let cx = 0, cy = 0;      // eased current value
    let last = performance.now();
    let raf = 0;

    const onMove = (e: PointerEvent) => {
      tx = e.clientX / window.innerWidth - 0.5;
      ty = e.clientY / window.innerHeight - 0.5;
      last = performance.now();
    };

    const tick = (t: number) => {
      const idle = t - last > 1800;
      const amp = idle ? 0.16 : 0.05;               // livelier sway when the pointer rests, subtle while it moves
      const gx = tx + Math.sin(t / 2300) * amp;
      const gy = ty + Math.cos(t / 1900) * amp * 0.8;
      cx += (gx - cx) * 0.055;                       // ease: this is what makes it fluid
      cy += (gy - cy) * 0.055;
      el.style.setProperty("--ry", `${-14 + cx * 46}deg`);
      el.style.setProperty("--rx", `${8 - cy * 34}deg`);
      el.style.setProperty("--rz", `${cx * -4 + cy * 2}deg`);
      el.style.setProperty("--mx", `${cx * 28}px`);  // parallax for the floating pieces
      el.style.setProperty("--my", `${cy * 22}px`);
      raf = requestAnimationFrame(tick);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    raf = requestAnimationFrame(tick);
    return () => {
      window.removeEventListener("pointermove", onMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  const par = (k: number) => ({ transform: `translate3d(calc(var(--mx, 0px) * ${k}), calc(var(--my, 0px) * ${k}), 0)` });

  return (
    <div
      aria-hidden
      className="scene relative mx-auto h-[300px] w-full max-w-[520px] select-none sm:h-[420px]"
    >
      <div ref={root} className="scene-tilt absolute inset-0 grid place-items-center">
        {/* back plate: ambient depth */}
        <div
          className="glass absolute h-[62%] w-[78%] rounded-3xl opacity-60"
          style={{ transform: "translateZ(-70px) translate(calc(26px + var(--mx, 0px) * -0.6), calc(22px + var(--my, 0px) * -0.6))" }}
        />

        {/* main video frame */}
        <div className="scene-layer glass relative w-[84%] rounded-3xl p-3" style={{ transform: "translateZ(0)" }}>
          <div className="relative aspect-video overflow-hidden rounded-2xl bg-gradient-to-br from-accent/80 via-accent2/70 to-ready/60">
            {/* simple landscape */}
            <div className="absolute right-[14%] top-[16%] h-10 w-10 rounded-full bg-white/80 blur-[1px] sm:h-14 sm:w-14" />
            <div className="absolute -bottom-6 -left-4 h-2/5 w-3/5 rounded-[50%] bg-black/25" />
            <div className="absolute -bottom-8 right-[-10%] h-1/2 w-3/5 rounded-[50%] bg-black/35" />

            {/* censored region */}
            <div className="absolute left-[18%] top-[34%] grid h-[34%] w-[34%] place-items-center overflow-hidden rounded-xl border border-white/40 bg-white/10 backdrop-blur-xl">
              <div className="absolute inset-0 bg-[repeating-linear-gradient(45deg,rgb(255_255_255/0.18)_0_6px,transparent_6px_12px)]" />
              <span className="relative rounded-full bg-black/55 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-white sm:text-[10px]">
                Blurred
              </span>
            </div>

            <div className="scan-line" />

            {/* audio bars (beep) */}
            <div className="absolute bottom-2 left-3 flex h-5 items-end gap-[3px]">
              {[0, 0.15, 0.3, 0.1, 0.4, 0.2, 0.35].map((d, i) => (
                <span key={i} className="bar-wave h-full w-[3px] rounded-full bg-white/85" style={{ animationDelay: `${d}s` }} />
              ))}
            </div>
          </div>

          {/* chunk timeline */}
          <div className="mt-3 flex gap-[3px] px-1">
            {Array.from({ length: SEGMENTS }).map((_, i) => (
              <div key={i} className="relative flex-1">
                <div
                  className={`h-3 rounded-[3px] sm:h-4 ${
                    i < READY ? "seg-ready bg-ready" : i === READY ? "bg-working" : "bg-ink/15"
                  }`}
                  style={i < READY ? { animationDelay: `${300 + i * 90}ms` } : undefined}
                />
                {i === PLAYHEAD && <div className="absolute -inset-x-px -inset-y-1 rounded-[4px] ring-2 ring-ink" />}
              </div>
            ))}
          </div>
          <div className="mt-2 flex justify-between px-1 text-[10px] font-medium text-muted">
            <span>Ready</span>
            <span>Next in queue</span>
          </div>
        </div>

        {/* floating shield */}
        <div className="scene-layer absolute right-[2%] top-[2%]" style={par(1.6)}>
         <div className="float-a" style={{ ["--z" as string]: "110px" }}>
          <div className="glass grid h-16 w-16 place-items-center rounded-2xl sm:h-20 sm:w-20">
            <svg viewBox="0 0 24 24" className="h-8 w-8 text-accent sm:h-10 sm:w-10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3l7 3v5c0 4.5-3 8.2-7 10-4-1.8-7-5.5-7-10V6l7-3z" />
              <path d="M9 12l2 2 4-4" />
            </svg>
          </div>
         </div>
        </div>

        {/* floating pills (echo the reference) */}
        <div className="scene-layer absolute bottom-[10%] left-[-2%]" style={par(-1.3)}>
          <div className="float-b" style={{ ["--z" as string]: "90px" }}>
            <div className="glass flex items-center gap-2 rounded-full py-2 pl-2 pr-4 text-xs font-semibold">
              <span className="h-5 w-5 rounded-full bg-gradient-to-br from-accent to-accent2" />
              Visual detection
            </div>
          </div>
        </div>
        <div className="scene-layer absolute bottom-[-2%] right-[6%]" style={par(1)}>
          <div className="float-a" style={{ ["--z" as string]: "70px", animationDelay: "-2s" }}>
            <div className="glass flex items-center gap-2 rounded-full py-2 pl-2 pr-4 text-xs font-semibold">
              <span className="h-5 w-5 rounded-full bg-ready" />
              Language beeped
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
