import { useState } from "react";
import { useApp } from "@/context/AppContext";
import type { DetectedLandingZone } from "@/types";
import LoadingState from "./LoadingState";
import ErrorState from "./ErrorState";
import { fmtCoord, fmtNum } from "@/utils/format";
import { CrosshairIcon, RefreshIcon } from "./icons";

export default function CandidateRegionsPanel() {
  const {
    selection,
    setSelection,
    detectedZones,
    detectStatus,
    detectError,
    runDetectSites,
    runAnalysis,
  } = useApp();

  const [maxSlope, setMaxSlope] = useState(8.0);
  const [minDiameter, setMinDiameter] = useState(50.0);

  const handleDetect = () => {
    void runDetectSites(selection, {
      max_slope_deg: maxSlope,
      min_landing_diameter_meters: minDiameter,
    });
  };

  const handleSelectZone = (zone: DetectedLandingZone) => {
    const newSel = {
      latitude: Math.round(zone.centroid_lat * 1e4) / 1e4,
      longitude: Math.round(zone.centroid_lon * 1e4) / 1e4,
      radius_m: Math.max(50, Math.round(zone.effective_diameter_m / 2)),
    };
    setSelection(newSel);
    void runAnalysis(newSel);
  };

  return (
    <div className="panel p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-divider pb-4">
        <div>
          <span className="kicker">Touchdown Corridors</span>
          <h3 className="font-display text-base font-semibold text-ink">
            Contiguous Safe Landing Regions
          </h3>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip font-mono">POST /api/sites/detect</span>
          <button
            className="btn-ghost !px-3 !py-1.5 !text-xs"
            onClick={handleDetect}
            disabled={detectStatus === "loading"}
          >
            {detectStatus === "loading" ? (
              <span className="spinner !h-3.5 !w-3.5" />
            ) : (
              <RefreshIcon className="h-3.5 w-3.5" />
            )}
            Detect Zones
          </button>
        </div>
      </div>

      {/* Detection constraints controls */}
      <div className="mt-4 grid grid-cols-2 gap-4 rounded-lg border border-divider/60 bg-elevated/30 p-3 sm:grid-cols-4">
        <div>
          <label className="text-[10px] uppercase tracking-wider text-muted block">Max Slope</label>
          <div className="mt-1 flex items-center gap-1.5">
            <input
              type="number"
              min="2"
              max="15"
              step="0.5"
              value={maxSlope}
              onChange={(e) => setMaxSlope(Number(e.target.value))}
              className="input !py-1 !px-2 text-xs font-mono w-20"
            />
            <span className="text-xs text-muted">deg</span>
          </div>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-muted block">Min Diameter</label>
          <div className="mt-1 flex items-center gap-1.5">
            <input
              type="number"
              min="20"
              max="200"
              step="10"
              value={minDiameter}
              onChange={(e) => setMinDiameter(Number(e.target.value))}
              className="input !py-1 !px-2 text-xs font-mono w-20"
            />
            <span className="text-xs text-muted">m</span>
          </div>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-muted block">Search Radius</label>
          <p className="mt-1 text-xs font-mono text-ink">{selection.radius_m || 1500} m</p>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-muted block">Detection Status</label>
          <p className="mt-1 text-xs font-mono text-cyan">
            {detectedZones.length > 0 ? `${detectedZones.length} safe zones` : "No active scan"}
          </p>
        </div>
      </div>

      {detectStatus === "loading" && (
        <div className="mt-5">
          <LoadingState label="Scanning NASA LOLA raster for contiguous flat corridors…" />
        </div>
      )}

      {detectStatus === "error" && (
        <div className="mt-5">
          <ErrorState
            title="Candidate region detection failed"
            message={detectError}
            onRetry={handleDetect}
          />
        </div>
      )}

      {detectStatus === "ready" && detectedZones.length === 0 && (
        <p className="mt-5 text-center text-xs text-muted">
          No contiguous landing patches with diameter &ge; {minDiameter}m and slope &le; {maxSlope}° were found in this {selection.radius_m}m radius window.
        </p>
      )}

      {detectedZones.length > 0 && (
        <div className="mt-5 space-y-2.5">
          <div className="max-h-60 overflow-y-auto rounded-lg border border-divider/60">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-elevated text-muted">
                <tr>
                  <th className="px-3 py-2 font-medium">Rank</th>
                  <th className="px-3 py-2 font-medium">Zone ID</th>
                  <th className="px-3 py-2 font-medium">Centroid</th>
                  <th className="px-3 py-2 font-medium">Diameter</th>
                  <th className="px-3 py-2 font-medium">Mean Slope</th>
                  <th className="px-3 py-2 font-medium">Roughness</th>
                  <th className="px-3 py-2 font-medium">MCDA Score</th>
                  <th className="px-3 py-2 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-divider font-mono">
                {detectedZones.slice(0, 8).map((zone) => (
                  <tr key={zone.zone_id} className="hover:bg-white/5 transition-colors">
                    <td className="px-3 py-2">
                      <span className="flex h-5 w-5 items-center justify-center rounded bg-accent/15 text-[11px] font-semibold text-cyan">
                        #{zone.safety_rank}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-ink">{zone.zone_id}</td>
                    <td className="px-3 py-2 text-muted">
                      {fmtCoord(zone.centroid_lat, zone.centroid_lon)}
                    </td>
                    <td className="px-3 py-2 text-slate-200">
                      {fmtNum(zone.effective_diameter_m, 1)} m
                    </td>
                    <td className="px-3 py-2 text-slate-200">
                      {fmtNum(zone.mean_slope_deg, 2)}°
                    </td>
                    <td className="px-3 py-2 text-slate-200">
                      {fmtNum(zone.mean_roughness_m, 2)} m
                    </td>
                    <td className="px-3 py-2">
                      <span className="font-semibold text-good">
                        {fmtNum(zone.suitability_score, 1)}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        className="btn-ghost !px-2.5 !py-1 !text-[11px]"
                        onClick={() => handleSelectZone(zone)}
                        title="Center map and run analysis on this candidate zone"
                      >
                        <CrosshairIcon className="h-3 w-3" />
                        Target Zone
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
