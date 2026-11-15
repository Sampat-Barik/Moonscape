import { useApp } from "@/context/AppContext";
import { API_BASE_URL } from "@/services/api";
import LogoMark from "./Logo";

export default function Footer() {
  const { mode, health } = useApp();
  return (
    <footer className="glass-footer">
      <div className="mx-auto grid max-w-[1400px] gap-10 px-6 py-12 md:grid-cols-3 lg:px-8">
        <div>
          <div className="flex items-center gap-2.5">
            <LogoMark className="h-7 w-7" />
            <span className="font-display text-sm font-semibold tracking-[0.2em] text-ink">
              MOONSCAPE
            </span>
          </div>
          <p className="mt-4 max-w-xs text-[13px] leading-relaxed text-muted">
            AI-assisted analysis of preliminary lunar South Pole landing sites —
            explore the map, measure the terrain, compare candidates.
          </p>
        </div>
        <div>
          <h4 className="font-mono text-[0.68rem] tracking-[0.2em] text-ink uppercase">
            Backend Telemetry
          </h4>
          <p className="mt-3 font-mono text-xs text-muted">
            API: {API_BASE_URL}
          </p>
          <p className="mt-1 font-mono text-xs text-muted">
            Mode: {mode}
            {health?.version ? ` · v${health.version}` : ""}
          </p>
        </div>
        <div>
          <h4 className="font-mono text-[0.68rem] tracking-[0.2em] text-ink uppercase">
            Data Provenance
          </h4>
          <p className="mt-3 text-xs leading-relaxed text-muted">
            Imagery: NASA/GSFC/ASU (LRO LROC, LOLA). 3D lunar planetary visualization
            rendered with Three.js &amp; CesiumJS. Independent educational mission analysis project —
            not affiliated with NASA.
          </p>
        </div>
      </div>
      <div className="divider" />
      <div className="py-5 text-center text-[0.65rem] tracking-[0.05em] text-muted/60">
        MoonScape 2026 · Lunar Landing Navigator
      </div>
    </footer>
  );
}
