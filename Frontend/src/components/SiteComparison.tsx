import { useState } from "react";
import { useApp } from "@/context/AppContext";
import type { CompareSite } from "@/types";
import LoadingState from "./LoadingState";
import ErrorState from "./ErrorState";
import DataUnavailable from "./DataUnavailable";
import { fmtCoord, fmtNum, pickNumber } from "@/utils/format";
import { AlertIcon, CheckIcon, ScaleIcon } from "./icons";

interface MetricRow {
  label: string;
  category: "Suitability" | "Topography" | "Slope & Roughness" | "Illumination";
  unit: string;
  digits?: number;
  maxVal?: number; // for visual comparison bar
  better?: "high" | "low";
  get: (s: CompareSite) => number | null;
}

const METRICS: MetricRow[] = [
  {
    category: "Suitability",
    label: "Suitability Score",
    unit: "/100",
    digits: 0,
    maxVal: 100,
    better: "high",
    get: (s) => pickNumber(s, ["score", "suitability_score", "suitability"]),
  },
  {
    category: "Topography",
    label: "Elevation (mean)",
    unit: "m",
    digits: 1,
    get: (s) => pickNumber(s.elevation, ["mean_m", "mean", "elevation_m", "value"]),
  },
  {
    category: "Slope & Roughness",
    label: "Slope (mean)",
    unit: "°",
    digits: 2,
    maxVal: 35,
    better: "low",
    get: (s) => pickNumber(s.slope, ["mean_deg", "mean", "slope_deg", "value"]),
  },
  {
    category: "Slope & Roughness",
    label: "Slope (max)",
    unit: "°",
    digits: 1,
    maxVal: 45,
    better: "low",
    get: (s) => pickNumber(s.slope, ["max_deg", "max", "value"]),
  },
  {
    category: "Slope & Roughness",
    label: "Roughness (RMS)",
    unit: "m",
    digits: 2,
    maxVal: 5,
    better: "low",
    get: (s) => pickNumber(s.roughness, ["rms_m", "rms", "value"]),
  },
  {
    category: "Illumination",
    label: "Sunlight",
    unit: "%",
    digits: 1,
    maxVal: 100,
    better: "high",
    get: (s) =>
      pickNumber(s.illumination, [
        "sunlight_percent",
        "sunlit_percent",
        "illumination_percent",
        "percent",
        "value",
      ]),
  },
];

export default function SiteComparison() {
  const {
    sites,
    sitesStatus,
    sitesError,
    refreshSites,
    comparison,
    compareStatus,
    compareError,
    compare,
  } = useApp();

  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const toggle = (id: string) =>
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  const selectAll = () => setSelectedIds(sites.map((s) => s.site_id));
  const clearAll = () => setSelectedIds([]);

  const rows: CompareSite[] = (() => {
    if (!comparison) return [];
    if (Array.isArray(comparison.sites)) return comparison.sites;
    if (Array.isArray(comparison.results)) return comparison.results;
    return [];
  })();

  // Compute best value per metric across rows
  const getBest = (m: MetricRow): number | null => {
    if (!m.better || rows.length < 2) return null;
    const vals = rows
      .map((s) => m.get(s))
      .filter((v): v is number => typeof v === "number" && !isNaN(v));
    if (vals.length === 0) return null;
    return m.better === "high" ? Math.max(...vals) : Math.min(...vals);
  };

  return (
    <div className="space-y-8">
      {/* ---------------- Candidate Selection Panel ---------------- */}
      <div className="panel p-6">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-divider pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="kicker">Candidate Selection</span>
              <span className="chip font-mono">GET /api/sites</span>
            </div>
            <h2 className="mt-1 font-display text-lg font-semibold text-ink">
              Select sites to evaluate side-by-side
            </h2>
            <p className="mt-1 text-xs text-muted">
              Choose 2 or more landing site candidates to run comparative telemetry analysis.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {sites.length > 0 && (
              <>
                <button
                  type="button"
                  className="chip cursor-pointer transition-colors hover:border-accent/40 hover:text-cyan"
                  onClick={selectAll}
                >
                  Select All ({sites.length})
                </button>
                {selectedIds.length > 0 && (
                  <button
                    type="button"
                    className="chip cursor-pointer transition-colors hover:border-bad/40 hover:text-bad"
                    onClick={clearAll}
                  >
                    Clear ({selectedIds.length})
                  </button>
                )}
              </>
            )}
            <button
              className="btn-primary !px-5 !py-2.5 !text-xs"
              disabled={selectedIds.length < 2 || compareStatus === "loading"}
              onClick={() => void compare(selectedIds)}
            >
              {compareStatus === "loading" ? (
                <span className="spinner !h-4 !w-4" />
              ) : (
                <ScaleIcon className="h-4 w-4" />
              )}
              Compare {selectedIds.length >= 2 ? `${selectedIds.length} Sites` : "Sites"}
            </button>
          </div>
        </div>

        {sitesStatus === "loading" && (
          <div className="mt-6">
            <LoadingState label="Loading candidate landing sites (GET /api/sites)…" />
          </div>
        )}
        {sitesStatus === "error" && (
          <div className="mt-6">
            <ErrorState title="Could not load sites" message={sitesError} onRetry={refreshSites} />
          </div>
        )}
        {sitesStatus === "ready" && (
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {sites.map((s) => {
              const active = selectedIds.includes(s.site_id);
              return (
                <button
                  key={s.site_id}
                  onClick={() => toggle(s.site_id)}
                  type="button"
                  className={`group relative rounded border p-4 text-left transition-all ${active
                      ? "border-accent/60 bg-accent/8 shadow-[0_0_20px_-6px_rgba(21,158,234,0.3)]"
                      : "border-divider bg-transparent hover:border-accent/30 hover:bg-elevated/40"
                    }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="font-display text-sm font-semibold text-ink group-hover:text-cyan">
                      {s.name ?? s.site_id}
                    </span>
                    <span
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors ${active
                          ? "border-accent bg-accent text-space"
                          : "border-divider text-transparent group-hover:border-accent/50"
                        }`}
                    >
                      <CheckIcon className="h-3.5 w-3.5" />
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-xs text-cyan">
                    {fmtCoord(s.latitude, s.longitude)}
                  </p>
                  {s.description && (
                    <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted">
                      {s.description}
                    </p>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ---------------- Comparison Results ---------------- */}
      {compareStatus === "loading" && (
        <div className="panel p-8 text-center">
          <LoadingState label="Executing comparative analysis (POST /api/sites/compare)…" />
        </div>
      )}
      {compareStatus === "error" && (
        <ErrorState
          title="Comparison request failed"
          message={compareError}
          onRetry={() => void compare(selectedIds)}
        />
      )}

      {compareStatus === "ready" && rows.length > 0 && (
        <div className="space-y-6">
          {/* Header Strip */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-divider pb-4">
            <div>
              <span className="kicker">Telemetry Matrix</span>
              <h2 className="mt-1 font-display text-xl font-semibold text-ink">
                Comparative Site Analysis
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <span className="chip font-mono">POST /api/sites/compare</span>
              {comparison?.compared_at && (
                <span className="chip font-mono">
                  {String(comparison.compared_at)}
                </span>
              )}
            </div>
          </div>

          {/* Side-by-side Table with Visual Bars */}
          <div className="panel overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px] text-left text-sm">
                <thead>
                  <tr className="border-b border-divider bg-elevated/60">
                    <th className="w-1/4 px-5 py-4 font-condensed text-xs uppercase tracking-wider text-muted">
                      Metric / Property
                    </th>
                    {rows.map((s) => (
                      <th key={s.site_id} className="px-5 py-4 align-top">
                        <div className="font-display font-semibold text-ink">
                          {s.name ?? s.site_id}
                        </div>
                        <div className="mt-0.5 font-mono text-[11px] font-normal text-cyan">
                          {typeof s.latitude === "number" && typeof s.longitude === "number"
                            ? fmtCoord(s.latitude, s.longitude)
                            : "coords n/a"}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-divider">
                  {METRICS.map((m) => {
                    const bestVal = getBest(m);
                    return (
                      <tr key={m.label} className="transition-colors hover:bg-elevated/20">
                        <td className="px-5 py-3.5">
                          <span className="block font-medium text-ink">{m.label}</span>
                          <span className="text-[11px] uppercase tracking-wider text-muted/70">
                            {m.category} · {m.unit}
                          </span>
                        </td>
                        {rows.map((s) => {
                          const v = m.get(s);
                          const isBest = bestVal !== null && v !== null && v === bestVal;
                          const pct =
                            m.maxVal && v !== null
                              ? Math.min(100, Math.max(0, (v / m.maxVal) * 100))
                              : null;

                          return (
                            <td key={s.site_id} className="px-5 py-3.5">
                              {v === null ? (
                                <DataUnavailable label="unavailable" />
                              ) : (
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span
                                      className={`font-mono text-base font-semibold ${isBest ? "text-cyan" : "text-ink"
                                        }`}
                                    >
                                      {fmtNum(v, m.digits ?? 2)}
                                      <span className="ml-1 text-xs font-normal text-muted">
                                        {m.unit}
                                      </span>
                                    </span>
                                    {isBest && (
                                      <span className="rounded bg-accent/15 px-1.5 py-0.5 font-condensed text-[10px] uppercase tracking-wider text-cyan">
                                        Advantage
                                      </span>
                                    )}
                                  </div>
                                  {pct !== null && (
                                    <div className="mt-1.5 h-1 w-28 overflow-hidden rounded bg-elevated">
                                      <div
                                        className={`h-full rounded ${isBest
                                            ? "bg-gradient-to-r from-accent to-cyan"
                                            : "bg-muted/40"
                                          }`}
                                        style={{ width: `${pct}%` }}
                                      />
                                    </div>
                                  )}
                                </div>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Scientific disclaimer footer */}
            <div className="flex items-start gap-3 border-t border-divider bg-space/40 px-5 py-4">
              <AlertIcon className="mt-0.5 h-4 w-4 shrink-0 text-warn" />
              <p className="text-xs leading-relaxed text-muted">
                Measurements are derived from official NASA LRO/LOLA altimetry data. Preliminary
                suitability scores and advantage flags reflect relative model metrics and do not
                constitute landing safety certification or guarantee mission success.
              </p>
            </div>
          </div>
        </div>
      )}

      {compareStatus === "ready" && rows.length === 0 && (
        <div className="panel p-6 text-sm text-muted">
          The comparison response contained no site entries.
        </div>
      )}
    </div>
  );
}
