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
          <h4 className="font-condensed text-[0.7rem] font-semibold tracking-[0.2em] text-accent uppercase">
            Backend Status
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
          <h4 className="font-condensed text-[0.7rem] font-semibold tracking-[0.2em] text-accent uppercase">
            Data &amp; Credits
          </h4>
          <p className="mt-3 text-xs leading-relaxed text-muted">
            Imagery: NASA/GSFC/ASU (LRO LROC, LOLA). Apollo mission photographs
            courtesy NASA. 3D globe rendered with three.js. Moonscape is an
            independent educational project — not affiliated with or endorsed by NASA.
          </p>
        </div>
      </div>
      <div className="divider" />
      <div className="py-5 text-center text-[0.65rem] tracking-[0.05em] text-muted/60">
        Preliminary decision support only — suitability scores are not a
        certification of landing safety.
      </div>
    </footer>
  );
}
