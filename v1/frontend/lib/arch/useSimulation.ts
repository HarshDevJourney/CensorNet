"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { TICK_MS, director, initSim, jumpTarget, seek as seekSim, step, type Sim } from "./engine";

export type Speed = 0.2 | 0.5 | 1;

/**
 * Runs the simulation. One requestAnimationFrame loop owns a "sim clock" (ms) that only advances while the
 * animation is playing, visible on screen and the tab is in front. Every TICK_MS of sim time it advances the
 * engine one tick; the packet layer reads the very same clock, so pausing freezes everything together.
 */
export function useSimulation(opts: { startPaused?: boolean; initialSpeed?: Speed } = {}) {
  const [sim, setSim] = useState<Sim>(() => initSim());
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<Speed>(() => opts.initialSpeed ?? 1);
  const [selected, setSelected] = useState<number | null>(null);
  const [reduced, setReduced] = useState(false);

  const wrapperRef = useRef<HTMLDivElement>(null);
  const clockRef = useRef(0);
  const accRef = useRef(0);
  const playingRef = useRef(false);
  const speedRef = useRef<Speed>(opts.initialSpeed ?? 1);
  const visibleRef = useRef(true);

  playingRef.current = playing;
  speedRef.current = speed;

  // start playing (unless the visitor prefers reduced motion)
  useEffect(() => {
    const rm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setReduced(rm);
    setPlaying(!(rm || opts.startPaused));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // only animate while on screen
  useEffect(() => {
    const el = wrapperRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(([e]) => { visibleRef.current = e.isIntersecting; }, { threshold: 0.15 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    let raf = 0;
    let last = performance.now();
    const loop = (now: number) => {
      const dt = Math.min(100, now - last);
      last = now;
      if (playingRef.current && visibleRef.current && !document.hidden) {
        const d = dt * speedRef.current;
        clockRef.current += d;
        accRef.current += d;
        let guard = 0;
        while (accRef.current >= TICK_MS && guard++ < 4) {
          accRef.current -= TICK_MS;
          setSim((prev) => director(step(prev)));
        }
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  const toggle = useCallback(() => setPlaying((p) => !p), []);
  const restart = useCallback(() => {
    accRef.current = 0;
    setSim(initSim());
    setSelected(null);
    setPlaying(true);
  }, []);
  const seekTo = useCallback((i: number) => setSim((prev) => seekSim(prev, i, true)), []);
  const jump = useCallback((dir: 1 | -1) => setSim((prev) => seekSim(prev, jumpTarget(prev, dir), true)), []);
  const select = useCallback((i: number | null) => setSelected(i), []);

  // what the inspector shows: the row the visitor picked, otherwise whichever row just changed
  const shown = useMemo(() => selected ?? sim.lastTouched, [selected, sim.lastTouched]);

  return { sim, playing, toggle, restart, speed, setSpeed, seekTo, jump, selected, shown, select, wrapperRef, clockRef, reduced };
}
