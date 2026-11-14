import { useEffect } from "react";
import type { Route } from "@/hooks/useHashRoute";
import { useApp } from "@/context/AppContext";
import HazardPanel from "@/components/HazardPanel";
import { fmtCoord } from "@/utils/format";
import { GlobeIcon, RefreshIcon, ShieldIcon } from "@/components/icons";

export default function Hazards({ navigate }: { navigate: (r: Route) => void }) {
  const { analysis, selection, hazards, hazardsStatus, hazardsError, runHazards } = useApp();

  // Auto-run hazard detection when an analysis already exists.
  useEffect(() => {
    if (analysis && hazardsStatus === "idle") void runHazards(selection);
  }, [analysis, hazardsStatus, runHazards, selection]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">

      {/* ===== Page header ===== */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-divider pb-6">
        <div>
          <span className="kicker">Hazard Analysis</span>
          <h1 className="mt-1 font-display text-2xl font-semibold text-ink">
            Craters, rocks &amp; detection confidence
          </h1>
          {analysis && (
            <p className="mt-1 text-[13px] text-muted">
              {fmtCoord(selection.latitude, selection.longitude)} · r = {selection.radius_m} m ·{" "}
              <span className="chip font-mono">POST /api/hazards/predict</span>
            </p>
          )}
        </div>
        {analysis && (
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
            Re-run detection
          </button>
        )}
      </div>

      {/* ===== No analysis empty state ===== */}
      {!analysis ? (
        <div className="relative overflow-hidden rounded-lg border border-divider">
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.04]"
            style={{
              backgroundImage: "url('/assets/lunar/moon-terrain.jpg')",
              backgroundSize: "cover",
              backgroundPosition: "center",
            }}
          />
          <div className="relative flex flex-col items-center px-8 py-20 text-center">
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full border border-divider bg-elevated">
              <ShieldIcon className="h-8 w-8 text-muted" />
            </div>
            <span className="kicker mb-3">No Analysis Session</span>
            <h2 className="font-display text-xl font-semibold text-ink">
              No analysis has been run yet
            </h2>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-muted">
              Hazard detection requires an active analysis session. Select a landing site in the
              Lunar Explorer, run an analysis — the hazard detection will then run automatically
              here.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <button
                className="btn-primary"
                onClick={() => navigate("/explorer")}
              >
                <GlobeIcon className="h-4 w-4" />
                Open Lunar Explorer
              </button>
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
