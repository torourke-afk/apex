"use client";
import { useEffect, useMemo, useRef } from "react";

/**
 * Atmosphere — the "luxury" background (DESIGN.md §4).
 * Three drifting aura blobs + a 450-dot ambient starfield with cursor-repel.
 * Dot positions/timings are generated ONCE (useMemo) so re-renders never restart
 * the animations. Outer wrapper carries the float drift (alternate); inner <i>
 * carries twinkle + the JS repel transform, so they compose.
 * ~18% of dots are bright cyan accent stars. Fully disabled by prefers-reduced-motion.
 */
const FLOATS = ["floatA", "floatB", "floatC", "floatD", "floatE", "floatF"];
const COUNT = 450;
const R = 130; // repel radius (px)
const MAX = 40; // max repel distance (px)

interface Dot {
  x: number; y: number; float: string; dur: number; delay: number;
  twDur: number; twDelay: number; star: boolean; size: number; glow: number;
}

export function Atmosphere() {
  const innersRef = useRef<(HTMLElement | null)[]>([]);

  const dots = useMemo<Dot[]>(() => {
    // deterministic PRNG so SSR/CSR match and positions are stable across re-renders
    let seed = 1337;
    const rnd = (a = 0, b = 1) => {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      return a + (seed / 0x7fffffff) * (b - a);
    };
    return Array.from({ length: COUNT }, () => {
      const star = rnd() < 0.18;
      return {
        x: rnd(0.4, 99.6),
        y: rnd(0.4, 99.6),
        float: FLOATS[Math.floor(rnd() * FLOATS.length)],
        dur: rnd(16, 42),
        delay: -rnd(0, 42),
        twDur: rnd(5, 11),
        twDelay: -rnd(0, 8),
        star,
        size: star ? rnd(1.8, 2.6) : rnd(0.7, 1.6),
        glow: star ? rnd(5, 8) : rnd(2, 4),
      };
    });
  }, []);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    let mx = -9999, my = -9999;
    const onMove = (e: MouseEvent) => {
      mx = e.clientX; my = e.clientY;
      if (!raf) raf = requestAnimationFrame(apply);
    };
    const apply = () => {
      raf = 0;
      const w = window.innerWidth, h = window.innerHeight;
      innersRef.current.forEach((inner, i) => {
        if (!inner) return;
        const d = dots[i];
        const px = (d.x / 100) * w, py = (d.y / 100) * h;
        const dx = px - mx, dy = py - my;
        const dist = Math.hypot(dx, dy) || 1;
        if (dist < R) {
          const p = ((R - dist) / R) * MAX;
          inner.style.transform = `translate(${((dx / dist) * p).toFixed(1)}px,${((dy / dist) * p).toFixed(1)}px)`;
        } else if (inner.style.transform) {
          inner.style.transform = "";
        }
      });
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => { window.removeEventListener("mousemove", onMove); if (raf) cancelAnimationFrame(raf); };
  }, [dots]);

  return (
    <div className="atmo" aria-hidden>
      <div className="atmo__aura atmo__aura--1" />
      <div className="atmo__aura atmo__aura--2" />
      <div className="atmo__aura atmo__aura--3" />
      {dots.map((d, i) => (
        <div
          key={i}
          className="atmo__dot"
          style={{
            left: `${d.x.toFixed(2)}%`,
            top: `${d.y.toFixed(2)}%`,
            animation: `${d.float} ${d.dur.toFixed(1)}s ease-in-out ${d.delay.toFixed(1)}s infinite alternate`,
          }}
        >
          <i
            ref={(node) => { innersRef.current[i] = node; }}
            style={{
              width: `${d.size.toFixed(2)}px`,
              height: `${d.size.toFixed(2)}px`,
              background: d.star ? "var(--color-accent)" : "var(--dot)",
              boxShadow: `0 0 ${d.glow.toFixed(0)}px ${d.star ? "var(--color-accent)" : "var(--dot)"}`,
              animation: `twinkle ${d.twDur.toFixed(1)}s ease-in-out ${d.twDelay.toFixed(1)}s infinite`,
            }}
          />
        </div>
      ))}
      <div className="atmo__vignette" />
    </div>
  );
}
