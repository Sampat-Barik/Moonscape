/**
 * Stars — lightweight animated canvas starfield used as a page background.
 * Stars twinkle via requestAnimationFrame; with `parallax` they also drift
 * slightly with the mouse. Purely decorative (aria-hidden).
 */
import { useEffect, useRef } from "react";

interface Star {
  x: number;
  y: number;
  r: number;
  base: number;
  amp: number;
  speed: number;
  phase: number;
  layer: number;
}

export default function Stars({
  className,
  density = 140,
  parallax = false,
}: {
  className?: string;
  /** Roughly one star per (density * 90) px². */
  density?: number;
  parallax?: boolean;
}) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx || !canvas.parentElement) return;

    let raf = 0;
    let w = 0;
    let h = 0;
    const stars: Star[] = [];
    let mx = 0.5;
    let my = 0.5;

    const resize = () => {
      const parent = canvas.parentElement;
      if (!parent) return;
      w = parent.clientWidth;
      h = parent.clientHeight;
      const dpr = Math.min(window.devicePixelRatio, 2);
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      stars.length = 0;
      const n = Math.max(24, Math.round((w * h) / (density * 90)));
      for (let i = 0; i < n; i++) {
        stars.push({
          x: Math.random() * w,
          y: Math.random() * h,
          r: Math.random() * 1.3 + 0.3,
          base: 0.22 + Math.random() * 0.5,
          amp: Math.random() * 0.32,
          speed: 0.4 + Math.random() * 1.2,
          phase: Math.random() * Math.PI * 2,
          layer: 0.35 + Math.random() * 0.65,
        });
      }
    };

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas.parentElement);

    const onMove = (e: globalThis.MouseEvent) => {
      mx = e.clientX / window.innerWidth;
      my = e.clientY / window.innerHeight;
    };
    if (parallax) window.addEventListener("mousemove", onMove);

    const tick = (t: number) => {
      ctx.clearRect(0, 0, w, h);
      for (const s of stars) {
        const a = s.base + Math.sin((t / 1000) * s.speed + s.phase) * s.amp;
        const ox = parallax ? (mx - 0.5) * 26 * s.layer : 0;
        const oy = parallax ? (my - 0.5) * 18 * s.layer : 0;
        ctx.globalAlpha = Math.max(0.05, Math.min(1, a));
        ctx.fillStyle = "#cfe8ff";
        ctx.beginPath();
        ctx.arc(s.x + ox, s.y + oy, s.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      if (parallax) window.removeEventListener("mousemove", onMove);
    };
  }, [density, parallax]);

  return <canvas ref={ref} className={className} aria-hidden="true" />;
}
