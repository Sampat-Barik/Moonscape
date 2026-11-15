import { useEffect } from "react";
import type { Route } from "@/hooks/useHashRoute";
import { useApp } from "@/context/AppContext";
import HazardPanel from "@/components/HazardPanel";
import { fmtCoord } from "@/utils/format";
import { GlobeIcon, RefreshIcon, ShieldIcon } from "@/components/icons";

export default function Hazards({ navigate }: { navigate: (r: Route) => void }) {
  const { analysis, selection, setSelection, hazards, hazardsStatus, hazardsError, runHazards } = useApp();

  // Auto-run hazard detection when an analysis already exists.
  useEffect(() => {
    if (analysis && hazardsStatus === "idle" && !hazards) void runHazards(selection);
  }, [analysis, hazardsStatus, hazards, runHazards, selection]);

  const hasSession = Boolean(analysis || hazards || hazardsStatus !== "idle");

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">

      {/* ===== Page header ===== */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-divider pb-6">
        <div>
          <span className="kicker">Hazard Analysis</span>
          <h1 className="mt-1 font-display text-2xl font-semibold text-ink">
            Craters, rocks &amp; detection confidence
          </h1>
          <p className="mt-1 text-[13px] text-muted">
            {fmtCoord(selection.latitude, selection.longitude)} · r = {selection.radius_m} m ·{" "}
            <span className="chip font-mono">POST /api/hazards/predict</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            className="btn-ghost !px-4 !py-2 !text-xs"
            onClick={() => void runHazards(selection)}
            disabled={hazardsStatus === "loading"}
          >
            {hazardsStatus === "loading" ? (
              <span className="spinner !h-4 !w-4" />
            ) : (
              <RefreshIcon className="h-4 w-4" />
            )}
            Run hazard scan
          </button>
        </div>
      </div>

      {/* ===== No analysis empty state ===== */}
      {!hasSession ? (
        <div className="relative overflow-hidden rounded-lg border border-divider">
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.04]"
            style={{
              backgroundImage: "url('/assets/lunar/moon-terrain.jpg')",
              backgroundSize: "cover",
              backgroundPosition: "center",
            }}
          />
          <div className="relative flex flex-col items-center px-8 py-16 text-center">
            <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-full border border-divider bg-elevated">
              <ShieldIcon className="h-7 w-7 text-muted" />
            </div>
            <span className="kicker mb-2">Hazard Detection Engine</span>
            <h2 className="font-display text-xl font-semibold text-ink">
              Ready for Lunar South Pole Hazard Scan
            </h2>
            <p className="mt-2 max-w-lg text-sm leading-relaxed text-muted">
              Analyze craters, boulders, and terrain slope hazards using authentic NASA LROC NAC and ISRO Chandrayaan-2 polar orbital imagery with trained YOLOv8n inference.
            </p>

            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <button
                className="btn-primary"
                onClick={() => void runHazards(selection)}
                disabled={hazardsStatus === "loading"}
              >
                {hazardsStatus === "loading" ? (
                  <span className="spinner !h-4 !w-4" />
                ) : (
                  <ShieldIcon className="h-4 w-4" />
                )}
                Run hazard scan at {fmtCoord(selection.latitude, selection.longitude)}
              </button>
              <button
                className="btn-secondary"
                onClick={() => navigate("/explorer")}
              >
                <GlobeIcon className="h-4 w-4" />
                Select on Lunar Explorer
              </button>
            </div>

            {/* Quick Candidate Presets */}
            <div className="mt-8 border-t border-divider/60 pt-6 w-full max-w-xl">
              <span className="text-[11px] font-medium tracking-wider uppercase text-muted block mb-3">
                Quick Verified Scientific Presets
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                <button
                  className="rounded border border-divider bg-surface/50 p-2.5 text-xs hover:border-slate-500 hover:bg-surface/80 transition-all"
                  onClick={() => {
                    const sel = { latitude: -87.4, longitude: -5.1, radius_m: 1000 };
                    setSelection(sel);
                    void runHazards(sel);
                  }}
                >
                  <span className="font-semibold text-ink block">Haworth Transition Rim</span>
                  <span className="text-[11px] text-muted block font-mono mt-0.5">87.400°S, 5.100°W · 1.8 mpp LROC NAC</span>
                </button>

                <button
                  className="rounded border border-divider bg-surface/50 p-2.5 text-xs hover:border-slate-500 hover:bg-surface/80 transition-all"
                  onClick={() => {
                    const sel = { latitude: -89.44, longitude: 222.5, radius_m: 1000 };
                    setSelection(sel);
                    void runHazards(sel);
                  }}
                >
                  <span className="font-semibold text-ink block">Shackleton Connecting Ridge</span>
                  <span className="text-[11px] text-muted block font-mono mt-0.5">89.440°S, 222.500°E · Site 01 1.2 mpp</span>
                </button>

                <button
                  className="rounded border border-divider bg-surface/50 p-2.5 text-xs hover:border-slate-500 hover:bg-surface/80 transition-all"
                  onClick={() => {
                    const sel = { latitude: -86.04, longitude: 2.7, radius_m: 1000 };
                    setSelection(sel);
                    void runHazards(sel);
                  }}
                >
                  <span className="font-semibold text-ink block">Malapert Mountain Summit</span>
                  <span className="text-[11px] text-muted block font-mono mt-0.5">86.040°S, 2.700°E · Site 02 Massif</span>
                </button>

                <button
                  className="rounded border border-divider bg-surface/50 p-2.5 text-xs hover:border-slate-500 hover:bg-surface/80 transition-all"
                  onClick={() => {
                    const sel = { latitude: -88.5, longitude: 275.0, radius_m: 1000 };
                    setSelection(sel);
                    void runHazards(sel);
                  }}
                >
                  <span className="font-semibold text-ink block">de Gerlache Crater Rim 1</span>
                  <span className="text-[11px] text-muted block font-mono mt-0.5">88.500°S, 275.000°E · Unseen Holdout</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <HazardPanel
          hazards={hazards}
          status={hazardsStatus}
          error={hazardsError}
          onRetry={() => void runHazards(selection)}
          selection={selection}
        />
      )}
    </div>
  );
}
