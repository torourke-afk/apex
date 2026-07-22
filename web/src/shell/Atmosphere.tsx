import { useMemo, useEffect, useRef, useCallback } from "react";

const FLOAT_KF = ["floatA", "floatB", "floatC", "floatD", "floatE", "floatF"];
const DOT_COUNT = 450;
const REPEL_R = 130;
const REPEL_MAX = 40;

interface Dot {
  lx: number; ly: number;
  wrapStyle: React.CSSProperties;
  innerStyle: React.CSSProperties;
}

function rnd(a: number, b: number) { return a + Math.random() * (b - a); }

export function Atmosphere() {
  const rootRef = useRef<HTMLDivElement>(null);
  const mouseRef = useRef({ x: 0, y: 0 });
  const rafRef = useRef<number>(0);

  // Generate dot array ONCE — stable across re-renders
  const dots = useMemo<Dot[]>(() => {
    const out: Dot[] = [];
    for (let i = 0; i < DOT_COUNT; i++) {
      const accent = Math.random() < 0.18;
      const sz = accent ? rnd(1.8, 2.6) : rnd(0.7, 1.6);
      const dur = rnd(16, 42);
      const delay = -rnd(0, 42);
      const tw = rnd(5, 11);
      const twd = -rnd(0, 8);
      const col = accent ? "var(--cyan)" : "var(--dotStar)";
      const glow = accent ? rnd(5, 8) : rnd(2, 4);
      const lx = rnd(0.4, 99.6);
      const ly = rnd(0.4, 99.6);
      const kf = FLOAT_KF[Math.floor(Math.random() * FLOAT_KF.length)];

      out.push({
        lx, ly,
        wrapStyle: {
          position: "absolute",
          left: `${lx}%`,
          top: `${ly}%`,
          willChange: "transform",
          animation: `${kf} ${dur.toFixed(1)}s ease-in-out ${delay.toFixed(1)}s infinite alternate`,
        },
        innerStyle: {
          width: sz, height: sz,
          borderRadius: "50%",
          background: col,
          boxShadow: `0 0 ${glow.toFixed(0)}px ${col}`,
          transition: "transform .4s cubic-bezier(.22,1,.36,1)",
          willChange: "transform",
          animation: `twinkle ${tw.toFixed(1)}s ease-in-out ${twd.toFixed(1)}s infinite`,
        },
      });
    }
    return out;
  }, []);

  const repel = useCallback(() => {
    rafRef.current = 0;
    const root = rootRef.current;
    if (!root) return;
    const els = root.querySelectorAll<HTMLElement>("[data-dot]");
    if (!els.length) return;
    const rect = root.getBoundingClientRect();
    const mx = mouseRef.current.x - rect.left;
    const my = mouseRef.current.y - rect.top;

    for (let i = 0; i < els.length; i++) {
      const el = els[i];
      const px = (parseFloat(el.dataset.px!) / 100) * rect.width;
      const py = (parseFloat(el.dataset.py!) / 100) * rect.height;
      const dx = px - mx;
      const dy = py - my;
      const dist = Math.hypot(dx, dy) || 1;

      if (dist < REPEL_R) {
        const f = (REPEL_R - dist) / REPEL_R;
        const p = f * REPEL_MAX;
        el.style.transform = `translate(${(dx / dist * p).toFixed(1)}px,${(dy / dist * p).toFixed(1)}px)`;
      } else if (el.style.transform) {
        el.style.transform = "";
      }
    }
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
      if (!rafRef.current) rafRef.current = requestAnimationFrame(repel);
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => {
      window.removeEventListener("mousemove", onMove);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [repel]);

  return (
    <div
      ref={rootRef}
      aria-hidden
      className="fixed inset-0 pointer-events-none overflow-hidden"
      style={{ zIndex: 0 }}
    >
      {/* Aura blobs */}
      <div
        className="absolute w-[600px] h-[600px] rounded-full blur-[120px] opacity-60"
        style={{
          background: "radial-gradient(circle, var(--aura1), transparent 70%)",
          top: "-10%", right: "10%",
          animation: "aura1 32s ease-in-out infinite",
        }}
      />
      <div
        className="absolute w-[500px] h-[500px] rounded-full blur-[100px] opacity-50"
        style={{
          background: "radial-gradient(circle, var(--aura2), transparent 70%)",
          top: "40%", left: "-5%",
          animation: "aura2 38s ease-in-out infinite",
        }}
      />
      <div
        className="absolute w-[450px] h-[450px] rounded-full blur-[90px] opacity-40"
        style={{
          background: "radial-gradient(circle, var(--aura3), transparent 70%)",
          bottom: "5%", right: "25%",
          animation: "aura3 26s ease-in-out infinite",
        }}
      />

      {/* Dot field */}
      {dots.map((d, i) => (
        <div key={i} style={d.wrapStyle}>
          <div
            data-dot
            data-px={d.lx.toFixed(2)}
            data-py={d.ly.toFixed(2)}
            style={d.innerStyle}
          />
        </div>
      ))}

      {/* Vignette */}
      <div
        className="absolute inset-0"
        style={{
          background: "radial-gradient(ellipse at 50% 50%, transparent 52%, var(--bg) 100%)",
        }}
      />
    </div>
  );
}
