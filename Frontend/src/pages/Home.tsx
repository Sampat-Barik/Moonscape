import { useEffect, useState } from "react";
import { motion } from "motion/react";
import type { Route } from "@/hooks/useHashRoute";
import { useApp } from "@/context/AppContext";
import CinematicMoon from "@/components/CinematicMoon";
import {
  ArrowRightIcon,
  CrosshairIcon,
  GlobeIcon,
  ScaleIcon,
  ShieldIcon,
} from "@/components/icons";

export default function Home({ navigate }: { navigate: (r: Route) => void }) {
  return (
    <div className="relative min-h-screen bg-space text-ink overflow-x-hidden selection:bg-white/20 selection:text-white">
      <HeroSection navigate={navigate} />
      <WorkflowEditorialSection navigate={navigate} />
      <MissionDossierSummary navigate={navigate} />
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * HERO SECTION — Monochromatic Cinematic Aerospace Composition
 * ------------------------------------------------------------------------- */
function HeroSection({ navigate }: { navigate: (r: Route) => void }) {
  const [currentTimeUTC, setCurrentTimeUTC] = useState("");

  useEffect(() => {
    const updateTime = () => {
      const d = new Date();
      setCurrentTimeUTC(
        d.toISOString().replace("T", " ").substring(0, 19) + " UTC"
      );
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <section className="relative flex min-h-[calc(100vh)] w-full items-center justify-between overflow-hidden px-6 pt-20 pb-16 lg:px-12 xl:px-16">
      {/* Background Star Ambient Texture */}
      <div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(ellipse_at_70%_50%,rgba(255,255,255,0.035)_0%,transparent_70%)]" />

      {/* Main Grid: Left Typography (45%), Right Massive 3D Moon (55%) */}
      <div className="relative z-10 mx-auto grid w-full max-w-[1520px] grid-cols-1 items-center gap-12 lg:grid-cols-12 lg:gap-8 xl:gap-12 min-h-[75vh]">
        {/* LEFT COLUMN: Editorial & Mission Briefing */}
        <motion.div
          initial={{ opacity: 0, x: -32 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col justify-center lg:col-span-6 xl:col-span-5"
        >
          {/* Eyebrow Technical Label */}
          <div className="flex items-center gap-3">
            <span className="inline-block h-px w-6 bg-muted/60" />
            <span className="font-mono text-[0.70rem] font-medium tracking-[0.22em] text-muted uppercase">
              // 01 · ARTEMIS CANDIDATE CORRIDORS
            </span>
          </div>

          {/* Large Architectural Headline */}
          <h1 className="mt-6 font-display text-[clamp(2.75rem,6.5vw,5.5rem)] font-bold leading-[0.94] tracking-[-0.035em] text-ink uppercase">
            MOON<br />
            <span className="text-gradient">SCAPE</span>
          </h1>

          {/* Elegant Project Introduction */}
          <p className="mt-6 max-w-lg font-body text-[0.925rem] leading-[1.65] text-muted sm:text-base">
            Precision lunar South Pole landing-site intelligence. Synthesize high-resolution
            LOLA altimetry, grazing-angle LROC reconnaissance, and deep-learning hazard detection
            into actionable touchdown decisions.
          </p>

          {/* Actions */}
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <button
              onClick={() => navigate("/explorer")}
              className="btn-primary group"
            >
              <span>EXPLORE SURFACE</span>
              <ArrowRightIcon className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />
            </button>

            <button
              onClick={() => {
                document
                  .getElementById("editorial-workflow")
                  ?.scrollIntoView({ behavior: "smooth" });
              }}
              className="btn-ghost"
            >
              MISSION DOSSIER
            </button>
          </div>

          {/* Technical Telemetry Microcopy */}
          <div className="mt-12 flex flex-wrap items-center gap-6 border-t border-divider/60 pt-6 font-mono text-[0.70rem] text-muted">
            <div>
              <span className="block text-[0.62rem] uppercase tracking-wider text-muted/60">Target Zone</span>
              <span className="mt-0.5 block text-ink">80°S — 90°S POLAR STEREO</span>
            </div>
            <div className="hidden sm:block h-6 w-px bg-divider/60" />
            <div>
              <span className="block text-[0.62rem] uppercase tracking-wider text-muted/60">Mission Clock</span>
              <span className="mt-0.5 block text-ink">{currentTimeUTC || "CALIBRATING…"}</span>
            </div>
            <div className="hidden sm:block h-6 w-px bg-divider/60" />
            <div>
              <span className="block text-[0.62rem] uppercase tracking-wider text-muted/60">Spatial Baseline</span>
              <span className="mt-0.5 block text-ink">1.2 — 1.8 M/PX GSD</span>
            </div>
          </div>
        </motion.div>

        {/* RIGHT COLUMN: Massive Photorealistic Interactive 3D Moon */}
        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.2, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="relative flex items-center justify-center lg:col-span-6 xl:col-span-7 h-[420px] sm:h-[540px] lg:h-[680px] xl:h-[760px]"
        >
          {/* Seamless Deep-Space Ambient Radial Glow behind the Moon */}
          <div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(closest-side_at_50%_50%,rgba(255,255,255,0.035)_0%,rgba(255,255,255,0.01)_50%,transparent_100%)]" />

          {/* Three.js Interactive Moon Globe */}
          <div className="relative z-10 h-full w-full">
            <CinematicMoon />
          </div>

          {/* Interactive Hint Micro-badge */}
          <div className="pointer-events-none absolute bottom-4 right-4 z-20 flex items-center gap-2 rounded-xs border border-divider/60 bg-surface/70 px-2.5 py-1 font-mono text-[0.62rem] tracking-[0.14em] text-muted/80 backdrop-blur-md">
            <span className="h-1.5 w-1.5 rounded-full bg-white/40 animate-pulse" />
            DRAG TO ROTATE CELESTIAL AXIS
          </div>
        </motion.div>
      </div>

      {/* BOTTOM BAR: Quiet Vertical Section Marker & Microcopy */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 z-10">
        <button
          onClick={() => {
            document
              .getElementById("editorial-workflow")
              ?.scrollIntoView({ behavior: "smooth" });
          }}
          className="flex flex-col items-center gap-2 group cursor-pointer focus:outline-none"
          aria-label="Scroll to editorial workflow"
        >
          <span className="font-mono text-[0.60rem] uppercase tracking-[0.25em] text-muted/70 group-hover:text-ink transition-colors">
            SCROLL TO INSPECT
          </span>
          <div className="h-8 w-px bg-gradient-to-b from-white/40 via-white/10 to-transparent group-hover:from-white group-hover:h-10 transition-all duration-300" />
        </button>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------------------
 * WORKFLOW EDITORIAL SECTION — Monochrome Architectural Layout
 * ------------------------------------------------------------------------- */
function WorkflowEditorialSection({ navigate }: { navigate: (r: Route) => void }) {
  const { sites, setSelection } = useApp();

  return (
    <section id="editorial-workflow" className="relative border-t border-divider/60 bg-deep py-28 scroll-mt-16">
      <div className="mx-auto max-w-[1440px] px-6 lg:px-12">
        {/* Section Header */}
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between border-b border-divider/60 pb-12">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="font-mono text-xs text-muted">// 02 · RECONNAISSANCE TO TOUCHDOWN</span>
            </div>
            <h2 className="mt-4 font-display text-[clamp(2.0rem,4.5vw,3.5rem)] font-bold tracking-tight text-ink uppercase">
              A NEW PERSPECTIVE<br />ON THE MOON.
            </h2>
          </div>
          <p className="max-w-md font-body text-sm leading-relaxed text-muted lg:pb-1">
            Raw planetary altimetry and optical orbital mosaics translated into verified terrain
            slope, surface roughness, optical hazard density, and multi-criteria landing matrices.
          </p>
        </div>

        {/* 3 Core Architectural Cards */}
        <div className="mt-16 space-y-12">
          {/* Item 1: 3D Surface Exploration */}
          <div className="panel grid lg:grid-cols-12 overflow-hidden items-stretch">
            <div className="relative aspect-[16/10] lg:aspect-auto lg:col-span-7 overflow-hidden border-b lg:border-b-0 lg:border-r border-divider/60">
              <img
                src="/assets/lunar/lunar-landscape.jpg"
                alt="NASA Apollo photographic survey archive"
                className="h-full w-full object-cover grayscale contrast-125 transition-transform duration-700 hover:scale-105"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-surface via-transparent to-transparent lg:bg-gradient-to-r lg:from-transparent lg:to-surface" />
              <div className="absolute top-4 left-4 font-mono text-[0.65rem] tracking-wider text-ink bg-surface/85 px-2.5 py-1 border border-divider">
                SURFACE ALBEDO · POLAR стерео
              </div>
            </div>
            <div className="flex flex-col justify-between p-8 lg:p-12 lg:col-span-5">
              <div>
                <span className="font-mono text-xs text-muted">[STEP 01] ORBITAL RECONNAISSANCE</span>
                <h3 className="mt-3 font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl uppercase">
                  3D Lunar Explorer
                </h3>
                <p className="mt-4 text-sm leading-relaxed text-muted">
                  Inspect candidate touchdown zones in an interactive polar stereographic 3D
                  environment. Probe real-time topographic elevation, slope steepness, and roughness
                  across Shackleton, Malapert, and de Gerlache craters.
                </p>
                <div className="mt-6 border-t border-divider/60 pt-4 font-mono text-xs text-muted space-y-2">
                  <div className="flex justify-between">
                    <span>Instrument:</span>
                    <span className="text-ink">LRO LOLA Altimetry (GLD100)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Target Region:</span>
                    <span className="text-ink">Lunar South Pole (&lt; -80° Lat)</span>
                  </div>
                </div>
              </div>
              <div className="mt-8 pt-4">
                <button
                  onClick={() => navigate("/explorer")}
                  className="btn-primary w-full sm:w-auto"
                >
                  <GlobeIcon className="h-4 w-4" />
                  <span>LAUNCH EXPLORER</span>
                  <ArrowRightIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Item 2: Optical Hazard Detection */}
          <div className="panel grid lg:grid-cols-12 overflow-hidden items-stretch">
            <div className="flex flex-col justify-between p-8 lg:p-12 lg:col-span-5 order-2 lg:order-1 border-t lg:border-t-0 lg:border-r border-divider/60">
              <div>
                <span className="font-mono text-xs text-muted">[STEP 02] COMPUTER VISION</span>
                <h3 className="mt-3 font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl uppercase">
                  Optical Hazard Analysis
                </h3>
                <p className="mt-4 text-sm leading-relaxed text-muted">
                  Automated crater and boulder detection executed by fine-tuned YOLOv8n models
                  trained strictly on polar grazing-angle orbital frames with spatial resolution
                  calibration in meters.
                </p>
                <div className="mt-6 border-t border-divider/60 pt-4 font-mono text-xs text-muted space-y-2">
                  <div className="flex justify-between">
                    <span>Crater Sensitivity:</span>
                    <span className="text-ink">75.5% Recall on Unseen Test Split</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Boulder Precision:</span>
                    <span className="text-ink">71.3% Precision</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Inference Latency:</span>
                    <span className="text-ink">18.2 ms on Ryzen 9 CPU</span>
                  </div>
                </div>
              </div>
              <div className="mt-8 pt-4 flex flex-wrap gap-3">
                <button
                  onClick={() => navigate("/hazards")}
                  className="btn-primary"
                >
                  <ShieldIcon className="h-4 w-4" />
                  <span>RUN HAZARD DETECTOR</span>
                </button>
                <button
                  onClick={() => navigate("/dashboard")}
                  className="btn-ghost"
                >
                  <span>DASHBOARD</span>
                </button>
              </div>
            </div>
            <div className="relative aspect-[16/10] lg:aspect-auto lg:col-span-7 overflow-hidden order-1 lg:order-2">
              <img
                src="/assets/lunar/moon-terrain.jpg"
                alt="Lunar crater elevation gradient"
                className="h-full w-full object-cover grayscale contrast-125 transition-transform duration-700 hover:scale-105"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-surface via-transparent to-transparent lg:bg-gradient-to-l lg:from-transparent lg:to-surface" />
              <div className="absolute top-4 right-4 font-mono text-[0.65rem] tracking-wider text-ink bg-surface/85 px-2.5 py-1 border border-divider">
                SHADOW &amp; OBSTACLE DELINEATION
              </div>
            </div>
          </div>

          {/* Item 3: Multi-Criteria Comparison */}
          <div className="panel p-8 lg:p-12">
            <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6 border-b border-divider/60 pb-8">
              <div>
                <span className="font-mono text-xs text-muted">[STEP 03] MCDA SCORING</span>
                <h3 className="mt-3 font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl uppercase">
                  Candidate Site Matrix
                </h3>
                <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
                  Weigh trade-offs across Artemis candidate sites. Compare solar illumination, slope
                  roughness, communication windows, and ML suitability scores side-by-side.
                </p>
              </div>
              <button
                onClick={() => navigate("/compare")}
                className="btn-ghost shrink-0"
              >
                <ScaleIcon className="h-4 w-4" />
                <span>FULL SITE MATRIX</span>
                <ArrowRightIcon className="h-4 w-4" />
              </button>
            </div>

            {/* Quick Candidate Site Selector Strip */}
            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {(sites.length > 0 ? sites.slice(0, 3) : [
                { site_id: "site_001", name: "Shackleton Connecting Ridge", latitude: -89.9, longitude: 0.0, description: "Prime illumination ridge near the South Pole rim." },
                { site_id: "site_002", name: "Connecting Ridge Extension", latitude: -89.42, longitude: 34.0, description: "Elevated plateau between Shackleton and Faustini." },
                { site_id: "site_003", name: "Faustini Rim Margin", latitude: -87.2, longitude: 80.0, description: "Rim flank with direct access to permanently shadowed regions." },
              ]).map((site) => (
                <div
                  key={site.site_id}
                  className="group relative flex flex-col justify-between border border-divider/60 bg-surface/40 p-5 transition-all duration-300 hover:border-white/40 hover:bg-surface/80 rounded-xs"
                >
                  <div>
                    <div className="flex items-center justify-between font-mono text-[0.65rem] text-muted">
                      <span>{site.site_id.toUpperCase()}</span>
                      <CrosshairIcon className="h-3 w-3 text-muted/60 group-hover:text-ink transition-colors" />
                    </div>
                    <h4 className="mt-2.5 font-display text-base font-semibold text-ink group-hover:text-white transition-colors">
                      {site.name}
                    </h4>
                    <p className="mt-2 font-body text-xs leading-relaxed text-muted line-clamp-2">
                      {site.description}
                    </p>
                  </div>
                  <div className="mt-5 flex items-center justify-between border-t border-divider/60 pt-3 font-mono text-[0.68rem]">
                    <span className="text-muted">
                      {site.latitude.toFixed(2)}°S, {site.longitude.toFixed(2)}°E
                    </span>
                    <button
                      onClick={() => {
                        setSelection({
                          latitude: site.latitude,
                          longitude: site.longitude,
                          radius_m: 500,
                        });
                        navigate("/explorer");
                      }}
                      className="text-ink hover:underline font-semibold"
                    >
                      INSPECT →
                    </button>
                  </div>
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
 * MISSION DOSSIER SUMMARY & CALL TO ACTION
 * ------------------------------------------------------------------------- */
function MissionDossierSummary({ navigate }: { navigate: (r: Route) => void }) {
  return (
    <section className="relative border-t border-divider/60 bg-space py-24 px-6 lg:px-12">
      <div className="mx-auto max-w-4xl text-center">
        <span className="font-mono text-xs uppercase tracking-[0.25em] text-muted">
          // 03 · READY FOR RECONNAISSANCE
        </span>
        <h2 className="mt-4 font-display text-[clamp(2.0rem,4vw,3.25rem)] font-bold tracking-tight text-ink uppercase">
          INITIATE LUNAR MISSION ANALYSIS
        </h2>
        <p className="mt-4 mx-auto max-w-xl text-sm leading-relaxed text-muted">
          Select target coordinates across the lunar South Pole, execute real LOLA digital
          elevation modeling, detect touchdown hazards, and generate AI-explained scientific dossiers.
        </p>

        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <button
            onClick={() => navigate("/explorer")}
            className="btn-primary"
          >
            <GlobeIcon className="h-4 w-4" />
            <span>LAUNCH 3D EXPLORER</span>
            <ArrowRightIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => navigate("/credits")}
            className="btn-ghost"
          >
            <span>DATA PROVENANCE &amp; CREDITS</span>
          </button>
        </div>
      </div>
    </section>
  );
}
