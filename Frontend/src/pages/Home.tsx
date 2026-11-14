import { useState, useEffect, type MouseEvent as ReactMouseEvent } from "react";
import type { Route } from "@/hooks/useHashRoute";
import { useReveal } from "@/hooks/useReveal";
import { useApp } from "@/context/AppContext";
import { fmtCoord } from "@/utils/format";
import {
  ArrowRightIcon,
  CrosshairIcon,
  GlobeIcon,
  ScaleIcon,
  ShieldIcon,
} from "@/components/icons";

/* =========================================================================
 * HOMEPAGE — Cinematic lunar landing page
 * Three sections: Hero, Editorial workflow, Cinematic CTA
 * ========================================================================= */

export default function Home({ navigate }: { navigate: (r: Route) => void }) {
  return (
    <div>
      <HeroSection navigate={navigate} />
      <EditorialSection navigate={navigate} />
      <CinematicCTA navigate={navigate} />
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * HERO — Full-viewport cinematic lunar landscape
 * ------------------------------------------------------------------------- */
function HeroSection({ navigate }: { navigate: (r: Route) => void }) {
  const [p, setP] = useState({ x: 0, y: 0 });
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    // Trigger entrance animation after a short delay
    const t = setTimeout(() => setLoaded(true), 100);
    return () => clearTimeout(t);
  }, []);

  const onMove = (e: ReactMouseEvent) => {
    setP({
      x: e.clientX / window.innerWidth - 0.5,
      y: e.clientY / window.innerHeight - 0.5,
    });
  };

  return (
    <section
      className="relative flex min-h-screen flex-col overflow-hidden"
      onMouseMove={onMove}
    >
      {/* Background image with parallax */}
      <div
        className="absolute inset-0 will-change-transform"
        style={{
          transform: `translate3d(${p.x * -14}px, ${p.y * -10}px, 0) scale(1.05)`,
          transition: "transform 0.3s ease-out",
        }}
      >
        <img
          src="/assets/hero/lunar-south-pole.jpg"
          alt="NASA imagery of lunar South Pole terrain"
          className="h-full w-full object-cover object-[80%_center]"
          loading="eager"
        />
      </div>

      {/* Overlays for depth, negative space on the left, and readability */}
      <div className="absolute inset-0 bg-gradient-to-r from-space via-space/80 via-45% to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-space via-transparent to-space/40" />
      <div className="absolute inset-0 bg-gradient-to-b from-space/40 via-transparent to-space" />
      {/* Cold blue-white atmospheric lighting near the lunar horizon & limb */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-80 bg-gradient-to-t from-cyan/15 via-accent/5 to-transparent" />
      <div className="pointer-events-none absolute top-0 right-0 h-[60vh] w-[50vw] bg-[radial-gradient(ellipse_at_70%_25%,rgba(88,217,242,0.12),transparent_70%)]" />

      {/* Content */}
      <div className="relative z-10 mx-auto flex w-full max-w-[1400px] flex-1 flex-col justify-center px-6 pb-32 pt-28 lg:px-8">
        {/* Eyebrow */}
        <div
          className={`transition-all duration-700 ease-out ${
            loaded ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
          }`}
        >
          <span className="inline-flex items-center gap-3 font-condensed text-[0.7rem] font-semibold tracking-[0.3em] text-accent uppercase">
            <span className="h-px w-8 bg-accent" />
            AI-ASSISTED LUNAR EXPLORATION
          </span>
        </div>

        {/* Headline */}
        <h1
          className={`mt-7 font-display font-bold leading-[0.92] tracking-[-0.03em] text-ink transition-all duration-1000 ease-out ${
            loaded ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
          style={{ transitionDelay: "150ms" }}
        >
          <span className="block text-[clamp(3rem,10vw,7.5rem)]">
            EXPLORE THE
          </span>
          <span className="block text-[clamp(3rem,10vw,7.5rem)] text-gradient">
            LUNAR FRONTIER.
          </span>
        </h1>

        {/* Supporting copy */}
        <p
          className={`mt-8 max-w-lg text-base leading-relaxed text-muted sm:text-[1.05rem] transition-all duration-700 ease-out ${
            loaded ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
          }`}
          style={{ transitionDelay: "350ms" }}
        >
          Explore, analyse, and compare lunar South Pole landing sites through
          interactive terrain visualization and AI-assisted scientific insights.
        </p>

        {/* CTAs */}
        <div
          className={`mt-10 flex flex-wrap items-center gap-4 transition-all duration-700 ease-out ${
            loaded ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
          }`}
          style={{ transitionDelay: "500ms" }}
        >
          <button className="btn-primary" onClick={() => navigate("/explorer")}>
            START EXPLORING
            <ArrowRightIcon className="h-4 w-4" />
          </button>
          <button
            className="btn-ghost"
            onClick={() =>
              document
                .getElementById("editorial")
                ?.scrollIntoView({ behavior: "smooth" })
            }
          >
            DISCOVER THE MISSION
          </button>
        </div>
      </div>

      {/* Bottom scroll hint */}
      <div className="absolute bottom-8 left-1/2 z-10 flex -translate-x-1/2 flex-col items-center gap-2">
        <div className="h-8 w-px bg-gradient-to-b from-transparent to-accent/50" />
        <span className="font-condensed text-[0.6rem] tracking-[0.25em] text-muted uppercase">
          Scroll
        </span>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------------------
 * EDITORIAL — "A New Perspective on the Moon"
 * Three large, visually differentiated content areas (avoiding generic 3-card grid)
 * ------------------------------------------------------------------------- */
function EditorialSection({ navigate }: { navigate: (r: Route) => void }) {
  const { sites, setSelection } = useApp();
  const [ref1, vis1] = useReveal<HTMLDivElement>(0.1);
  const [ref2, vis2] = useReveal<HTMLDivElement>(0.1);
  const [ref3, vis3] = useReveal<HTMLDivElement>(0.1);
  const [ref4, vis4] = useReveal<HTMLDivElement>(0.1);

  return (
    <section id="editorial" className="relative scroll-mt-20">
      {/* Section header */}
      <div
        ref={ref1}
        className={`mx-auto max-w-[1400px] px-6 pt-32 pb-16 lg:px-8 reveal ${vis1 ? "visible" : ""}`}
      >
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <span className="kicker">Scientific Workflow</span>
            <h2 className="mt-4 max-w-3xl font-display text-[clamp(2.2rem,5vw,3.75rem)] font-bold leading-[1.04] tracking-[-0.02em] text-ink">
              A NEW PERSPECTIVE
              <br />
              ON THE MOON.
            </h2>
            <div className="mt-5 h-px w-20 bg-accent" />
          </div>
          <p className="max-w-md font-body text-sm leading-relaxed text-muted lg:pb-1">
            MOONSCAPE transforms raw planetary datasets into actionable landing site intelligence.
            From orbital reconnaissance to high-resolution hazard segmentation and multi-criteria
            matrices, each stage is engineered for rigorous mission support.
          </p>
        </div>
      </div>

      <div className="mx-auto max-w-[1400px] space-y-16 px-6 pb-32 lg:px-8">
        {/* ===================================================================
         * CONTENT AREA 1: EXPLORE THE LUNAR SURFACE
         * Wide panoramic split with interactive targeting & orbital telemetry
         * ================================================================= */}
        <div
          ref={ref2}
          className={`overflow-hidden rounded-md border border-divider bg-deep reveal ${
            vis2 ? "visible" : ""
          }`}
        >
          <div className="grid lg:grid-cols-12 items-stretch">
            {/* Left: Imagery with targeting overlay */}
            <div className="relative aspect-[16/10] lg:aspect-auto lg:col-span-7 overflow-hidden">
              <img
                src="/assets/lunar/lunar-landscape.jpg"
                alt="Apollo lunar surface photograph — NASA"
                className="h-full w-full object-cover transition-transform duration-700 hover:scale-105"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-deep via-transparent to-transparent lg:bg-gradient-to-r lg:from-transparent lg:to-deep" />
              {/* Telemetry reticle */}
              <div className="absolute inset-0 p-6 flex flex-col justify-between pointer-events-none">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[0.65rem] tracking-wider text-cyan bg-space/75 px-2.5 py-1 rounded-xs border border-divider">
                    LROC NAC · 0.5 M/PX
                  </span>
                  <span className="font-mono text-[0.65rem] text-muted bg-space/75 px-2.5 py-1 rounded-xs border border-divider">
                    TARGET: 89.900°S, 000.000°E
                  </span>
                </div>
                <div className="flex items-center gap-2 self-start font-mono text-[0.68rem] text-accent/90 bg-space/80 px-2 py-1 rounded-xs">
                  <CrosshairIcon className="h-3.5 w-3.5 text-accent animate-pulse" />
                  SHACKLETON CRATER RIM
                </div>
              </div>
            </div>

            {/* Right: Editorial description */}
            <div className="flex flex-col justify-between p-8 lg:p-12 lg:col-span-5">
              <div>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-accent">[01]</span>
                  <span className="font-condensed text-[0.7rem] font-semibold tracking-[0.2em] text-cyan uppercase">
                    ORBITAL RECONNAISSANCE
                  </span>
                </div>
                <h3 className="mt-4 font-display text-2xl font-bold tracking-[-0.01em] text-ink sm:text-3xl">
                  EXPLORE THE LUNAR SURFACE
                </h3>
                <p className="mt-4 text-sm leading-relaxed text-muted">
                  Navigate an interactive 3D globe of the Moon rendered directly in WebGL. Inspect
                  candidate coordinates across the South Pole's ridges and permanently shadowed
                  regions with true orbital elevation contours.
                </p>
                <div className="mt-6 grid grid-cols-2 gap-4 border-t border-divider pt-6 font-mono text-xs">
                  <div>
                    <span className="block text-[0.65rem] uppercase tracking-wider text-muted">Projection</span>
                    <span className="mt-1 block font-medium text-ink">Polar Stereographic</span>
                  </div>
                  <div>
                    <span className="block text-[0.65rem] uppercase tracking-wider text-muted">Source Instrument</span>
                    <span className="mt-1 block font-medium text-ink">LRO LOLA & LROC</span>
                  </div>
                </div>
              </div>

              <div className="mt-8 pt-4">
                <button
                  className="btn-primary w-full sm:w-auto"
                  onClick={() => navigate("/explorer")}
                >
                  <GlobeIcon className="h-4 w-4" />
                  LAUNCH 3D EXPLORER
                  <ArrowRightIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ===================================================================
         * CONTENT AREA 2: ANALYSE TERRAIN AND HAZARDS
         * Technical telemetry layout with elevation & detection specs
         * ================================================================= */}
        <div
          ref={ref3}
          className={`overflow-hidden rounded-md border border-divider bg-deep reveal ${
            vis3 ? "visible" : ""
          }`}
        >
          <div className="grid lg:grid-cols-12 items-stretch">
            {/* Left: Editorial content */}
            <div className="flex flex-col justify-between p-8 lg:p-12 lg:col-span-6 order-2 lg:order-1">
              <div>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-accent">[02]</span>
                  <span className="font-condensed text-[0.7rem] font-semibold tracking-[0.2em] text-cyan uppercase">
                    HAZARD SEGMENTATION
                  </span>
                </div>
                <h3 className="mt-4 font-display text-2xl font-bold tracking-[-0.01em] text-ink sm:text-3xl">
                  ANALYSE TERRAIN AND HAZARDS
                </h3>
                <p className="mt-4 text-sm leading-relaxed text-muted">
                  Execute server-side terrain qualification over candidate coordinates. Receive
                  deterministic metrics for elevation, slope angle, surface roughness, and solar
                  illumination alongside AI-detected crater and boulder distributions.
                </p>

                {/* Telemetry data readouts */}
                <div className="mt-6 space-y-2 border-t border-divider pt-6">
                  <div className="flex items-center justify-between py-1 border-b border-divider/40 font-mono text-xs">
                    <span className="text-muted">Slope Angle Threshold</span>
                    <span className="text-good font-medium">&lt; 10.0° (Acceptable)</span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-divider/40 font-mono text-xs">
                    <span className="text-muted">Crater / Boulder Detection</span>
                    <span className="text-cyan font-medium">Confidence ≥ 0.85</span>
                  </div>
                  <div className="flex items-center justify-between py-1 font-mono text-xs">
                    <span className="text-muted">Elevation Model</span>
                    <span className="text-ink font-medium">LOLA GLD100 DEM</span>
                  </div>
                </div>
              </div>

              <div className="mt-8 flex flex-wrap gap-4 pt-4">
                <button
                  className="btn-primary"
                  onClick={() => navigate("/dashboard")}
                >
                  <ShieldIcon className="h-4 w-4" />
                  ANALYSIS DASHBOARD
                  <ArrowRightIcon className="h-4 w-4" />
                </button>
                <button
                  className="btn-ghost"
                  onClick={() => navigate("/hazards")}
                >
                  HAZARD PREDICTOR
                </button>
              </div>
            </div>

            {/* Right: Technical visual */}
            <div className="relative aspect-[16/10] lg:aspect-auto lg:col-span-6 overflow-hidden order-1 lg:order-2">
              <img
                src="/assets/lunar/moon-terrain.jpg"
                alt="Lunar terrain elevation data — NASA LRO"
                className="h-full w-full object-cover transition-transform duration-700 hover:scale-105"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-deep via-transparent to-transparent lg:bg-gradient-to-l lg:from-transparent lg:to-deep" />
              <div className="absolute top-4 right-4 font-mono text-[0.65rem] tracking-wider text-accent bg-space/80 px-2.5 py-1 rounded-xs border border-divider">
                ELEVATION HEATMAP &amp; CONTOUR
              </div>
            </div>
          </div>
        </div>

        {/* ===================================================================
         * CONTENT AREA 3: COMPARE POTENTIAL LANDING SITES
         * Comparative intelligence area with live candidate site selection
         * ================================================================= */}
        <div
          ref={ref4}
          className={`overflow-hidden rounded-md border border-divider bg-deep reveal ${
            vis4 ? "visible" : ""
          }`}
        >
          <div className="p-8 lg:p-12">
            <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
              <div>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-accent">[03]</span>
                  <span className="font-condensed text-[0.7rem] font-semibold tracking-[0.2em] text-cyan uppercase">
                    MISSION EVALUATION
                  </span>
                </div>
                <h3 className="mt-4 font-display text-2xl font-bold tracking-[-0.01em] text-ink sm:text-3xl">
                  COMPARE POTENTIAL LANDING SITES
                </h3>
                <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
                  Weigh trade-offs between candidate landing zones. Compare solar illumination,
                  slope roughness, and Earth communications visibility side by side.
                </p>
              </div>
              <button
                className="btn-ghost self-start lg:self-end shrink-0"
                onClick={() => navigate("/compare")}
              >
                <ScaleIcon className="h-4 w-4" />
                FULL SITE MATRIX
                <ArrowRightIcon className="h-4 w-4" />
              </button>
            </div>

            {/* Candidate Sites Quick-Selector Strip */}
            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 pt-6 border-t border-divider">
              {(sites.length > 0
                ? sites.slice(0, 3)
                : [
                    { site_id: "site_001", name: "Shackleton Rim", latitude: -89.9, longitude: 0.0, description: "Rim of Shackleton crater near the south pole — prime illumination ridge." },
                    { site_id: "site_002", name: "Connecting Ridge", latitude: -89.42, longitude: 34.0, description: "Elevated ridge between Shackleton and Faustini craters." },
                    { site_id: "site_003", name: "Faustini Rim", latitude: -87.2, longitude: 80.0, description: "Faustini rim with direct access to permanent shadow regions." },
                  ]
              ).map((s) => (
                <div
                  key={s.site_id}
                  className="group relative flex flex-col justify-between rounded-xs border border-divider/60 bg-surface/50 p-5 transition-all duration-300 hover:border-accent/40 hover:bg-surface/80"
                >
                  <div>
                    <div className="flex items-center justify-between font-mono text-[0.65rem] text-muted">
                      <span className="text-cyan">{s.site_id.toUpperCase()}</span>
                      <span>{fmtCoord(s.latitude, s.longitude)}</span>
                    </div>
                    <h4 className="mt-2 font-display text-base font-semibold text-ink group-hover:text-accent transition-colors">
                      {s.name ?? s.site_id}
                    </h4>
                    {s.description && (
                      <p className="mt-2 text-xs leading-relaxed text-muted line-clamp-2">
                        {s.description}
                      </p>
                    )}
                  </div>
                  <button
                    className="mt-4 flex items-center gap-1.5 self-start font-condensed text-xs font-semibold tracking-wider text-accent uppercase hover:text-cyan transition-colors"
                    onClick={() => {
                      setSelection({ latitude: s.latitude, longitude: s.longitude, radius_m: 500 });
                      navigate("/explorer");
                    }}
                  >
                    <span>Inspect Coordinates</span>
                    <ArrowRightIcon className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------------------
 * CINEMATIC CTA — "The Surface Is Only the Beginning"
 * Large lunar visual + scroll-driven subtle movement + CTA
 * ------------------------------------------------------------------------- */
function CinematicCTA({ navigate }: { navigate: (r: Route) => void }) {
  const [ref, vis] = useReveal<HTMLElement>(0.1);
  const [offsetY, setOffsetY] = useState(0);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) return;

    let ticking = false;
    const onScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          if (ref.current) {
            const rect = ref.current.getBoundingClientRect();
            // Subtle scroll-driven movement
            const progress = (window.innerHeight - rect.top) / (window.innerHeight + rect.height);
            setOffsetY((progress - 0.5) * 35);
          }
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [ref]);

  return (
    <section
      ref={ref}
      className={`relative overflow-hidden reveal ${vis ? "visible" : ""}`}
    >
      {/* Background with scroll-driven movement */}
      <div
        className="absolute inset-0 will-change-transform"
        style={{
          transform: `translate3d(0, ${offsetY}px, 0) scale(1.08)`,
          transition: "transform 0.1s linear",
        }}
      >
        <img
          src="/images/hero-bg.jpg"
          alt="Lunar surface panoramic view"
          className="h-full w-full object-cover opacity-35"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-space via-space/80 to-space/90" />
      </div>

      <div className="relative z-10 mx-auto flex max-w-[1400px] flex-col items-center px-6 py-40 text-center lg:px-8 lg:py-52">
        <span className="kicker">Begin Your Analysis</span>
        <h2 className="mt-5 max-w-4xl font-display text-[clamp(2.2rem,5.5vw,4.25rem)] font-bold leading-[1.04] tracking-[-0.02em] text-ink">
          THE SURFACE IS ONLY
          <br />
          THE BEGINNING.
        </h2>
        <p className="mt-6 max-w-lg text-base leading-relaxed text-muted">
          Interactive terrain visualization, AI-powered hazard detection, and scientific
          site comparison — engineered for aerospace mission support.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <button
            className="btn-primary"
            onClick={() => navigate("/explorer")}
          >
            <GlobeIcon className="h-4 w-4" />
            LAUNCH EXPLORER
            <ArrowRightIcon className="h-4 w-4" />
          </button>
          <button
            className="btn-ghost"
            onClick={() => navigate("/report")}
          >
            AI SCIENTIFIC REPORTS
          </button>
        </div>
      </div>

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-space to-transparent" />
    </section>
  );
}
