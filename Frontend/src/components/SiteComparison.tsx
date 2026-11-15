import { useState } from "react";
import { useApp } from "@/context/AppContext";
import type { CompareSite, ExplanationResponse } from "@/types";
import { api } from "@/services/api";
import AIExplanation from "./AIExplanation";
import LoadingState from "./LoadingState";
import ErrorState from "./ErrorState";
import DataUnavailable from "./DataUnavailable";
import { fmtCoord, fmtNum, pickNumber } from "@/utils/format";
import { AlertIcon, CheckIcon, DocIcon, DownloadIcon, ScaleIcon, SparkIcon } from "./icons";

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
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingSummaryPdf, setDownloadingSummaryPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [explanationError, setExplanationError] = useState<string | null>(null);
  const [showJsonDossier, setShowJsonDossier] = useState(false);

  const toggle = (id: string) =>
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  const selectAll = () => setSelectedIds(sites.map((s) => s.site_id));
  const clearAll = () => setSelectedIds([]);

  const handleCompareAll = () => {
    const allIds = sites.map((s) => s.site_id);
    setSelectedIds(allIds);
    void compare(allIds);
  };

  const handleExplainComparison = async () => {
    if (rows.length < 2 || explaining) return;
    setExplaining(true);
    setExplanationError(null);
    try {
      const siteIds = rows.map((r) => r.site_id);
      const res = await api.explainComparison(siteIds);
      setExplanation(res);
    } catch (err: any) {
      setExplanationError(err?.message || "Failed to synthesize comparative AI mission briefing");
    } finally {
      setExplaining(false);
    }
  };

  const handleDownloadSummaryPdf = async () => {
    if (rows.length < 2 || downloadingSummaryPdf) return;
    setDownloadingSummaryPdf(true);
    setPdfError(null);
    try {
      const siteIds = rows.map((r) => r.site_id);
      const blob = await api.downloadComparisonSummaryPdf(siteIds);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const today = new Date().toISOString().split("T")[0];
      a.download = `MoonScape_Comparison_Summary_${today}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err: any) {
      setPdfError(err?.message || "Failed to generate comparison summary PDF");
    } finally {
      setDownloadingSummaryPdf(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (rows.length < 2 || downloadingPdf) return;
    setDownloadingPdf(true);
    setPdfError(null);
    try {
      const siteIds = rows.map((r) => r.site_id);
      const blob = await api.downloadComparisonPdf(siteIds);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const today = new Date().toISOString().split("T")[0];
      a.download = `MoonScape_Comparison_${today}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err: any) {
      setPdfError(err?.message || "Failed to generate and download comparison PDF report");
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleDownloadJson = () => {
    if (!comparison) return;
    const blob = new Blob([JSON.stringify(comparison, null, 2)], { type: "application/json" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const today = new Date().toISOString().split("T")[0];
    a.download = `moonscape_comparison_${today}.json`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
  };

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
                  className="chip cursor-pointer transition-colors hover:border-ink/40 hover:text-ink"
                  onClick={selectAll}
                >
                  Select All ({sites.length})
                </button>
                <button
                  type="button"
                  className="chip cursor-pointer transition-colors hover:border-ink/60 hover:text-ink font-medium"
                  onClick={handleCompareAll}
                  disabled={sites.length < 2 || compareStatus === "loading"}
                >
                  Compare All Sites ({sites.length})
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
                    ? "border-ink/60 bg-white/5 shadow-[0_0_20px_-6px_rgba(255,255,255,0.12)]"
                    : "border-divider bg-transparent hover:border-white/30 hover:bg-elevated/40"
                    }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="font-display text-sm font-semibold text-ink group-hover:text-white">
                      {s.name ?? s.site_id}
                    </span>
                    <span
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors ${active
                        ? "border-ink bg-ink text-space"
                        : "border-divider text-transparent group-hover:border-white/40"
                        }`}
                    >
                      <CheckIcon className="h-3.5 w-3.5" />
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-xs text-muted">
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
            <div className="flex flex-wrap items-center gap-2">
              <span className="chip font-mono">POST /api/sites/compare</span>
              {comparison?.compared_at && (
                <span className="chip font-mono">
                  {String(comparison.compared_at)}
                </span>
              )}
              <button
                type="button"
                className="btn-primary !px-3.5 !py-2 !text-xs flex items-center gap-2 cursor-pointer transition-colors disabled:opacity-50"
                onClick={handleExplainComparison}
                disabled={explaining || rows.length < 2}
                title="Synthesize AI comparative mission briefing and trade-off assessment"
              >
                {explaining ? (
                  <span className="spinner !h-3.5 !w-3.5" />
                ) : (
                  <SparkIcon className="h-3.5 w-3.5" />
                )}
                <span>{explaining ? "Synthesizing AI…" : "Generate AI Summary"}</span>
              </button>
              <button
                type="button"
                className="btn-secondary !px-3.5 !py-2 !text-xs flex items-center gap-2 cursor-pointer transition-colors disabled:opacity-50"
                onClick={handleDownloadSummaryPdf}
                disabled={downloadingSummaryPdf || rows.length < 2}
                title="Download concise 2-page executive summary PDF"
              >
                {downloadingSummaryPdf ? (
                  <span className="spinner !h-3.5 !w-3.5" />
                ) : (
                  <DownloadIcon className="h-3.5 w-3.5" />
                )}
                <span>{downloadingSummaryPdf ? "Generating Summary…" : "Download Summary PDF"}</span>
              </button>
              <button
                type="button"
                className="btn-secondary !px-3.5 !py-2 !text-xs flex items-center gap-2 cursor-pointer transition-colors disabled:opacity-50"
                onClick={handleDownloadPdf}
                disabled={downloadingPdf || rows.length < 2}
                title="Download comprehensive 10-page comparison PDF report"
              >
                {downloadingPdf ? (
                  <span className="spinner !h-3.5 !w-3.5" />
                ) : (
                  <DownloadIcon className="h-3.5 w-3.5" />
                )}
                <span>{downloadingPdf ? "Generating PDF…" : "Download Full PDF"}</span>
              </button>
              <button
                type="button"
                className="btn-ghost !px-3 !py-2 !text-xs flex items-center gap-1.5 cursor-pointer"
                onClick={() => window.print()}
                title="Print or export current view"
              >
                <DocIcon className="h-3.5 w-3.5" />
                <span>Print</span>
              </button>
            </div>
          </div>

          {pdfError && (
            <div className="flex items-center justify-between rounded border border-bad/30 bg-bad/10 px-4 py-2.5 text-xs text-bad">
              <div className="flex items-center gap-2">
                <AlertIcon className="h-4 w-4 shrink-0" />
                <span>{pdfError}</span>
              </div>
              <button
                type="button"
                className="text-muted hover:text-ink text-xs underline ml-4 cursor-pointer"
                onClick={() => setPdfError(null)}
              >
                Dismiss
              </button>
            </div>
          )}

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
                        <div className="mt-0.5 font-mono text-[11px] font-normal text-muted">
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
                                      className={`font-mono text-base font-semibold ${isBest ? "text-white" : "text-ink"
                                        }`}
                                    >
                                      {fmtNum(v, m.digits ?? 2)}
                                      <span className="ml-1 text-xs font-normal text-muted">
                                        {m.unit}
                                      </span>
                                    </span>
                                    {isBest && (
                                      <span className="rounded border border-white/20 bg-white/10 px-1.5 py-0.5 font-condensed text-[10px] uppercase tracking-wider text-white">
                                        Advantage
                                      </span>
                                    )}
                                  </div>
                                  {pct !== null && (
                                    <div className="mt-1.5 h-1 w-28 overflow-hidden rounded bg-elevated">
                                      <div
                                        className={`h-full rounded ${isBest
                                          ? "bg-gradient-to-r from-[#888888] to-[#F1F1EF]"
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

          {/* ================= Section 1: AI Comparative Explanation ================= */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="kicker">Mission Debrief</span>
                <h3 className="font-display text-lg font-semibold text-ink">
                  Comparative AI Mission Synthesis
                </h3>
              </div>
              {!explanation && (
                <button
                  type="button"
                  className="btn-ghost !px-3 !py-1.5 !text-xs flex items-center gap-1.5 cursor-pointer"
                  onClick={handleExplainComparison}
                  disabled={explaining || rows.length < 2}
                >
                  <SparkIcon className="h-3.5 w-3.5 text-ink" />
                  Generate Briefing
                </button>
              )}
            </div>

            <AIExplanation
              explanation={explanation}
              status={explaining ? "loading" : explanation ? "ready" : "idle"}
              error={explanationError}
              onRetry={handleExplainComparison}
            />

            {!explanation && !explaining && !explanationError && (
              <div className="panel p-6 text-center text-xs text-muted">
                No comparative narrative synthesized yet. Click “Generate AI Summary” above to compile a grounded trade-off briefing.
              </div>
            )}
          </div>

          {/* ================= Section 2: Technical JSON Comparison Dossier ================= */}
          <div className="panel p-6 sm:p-8">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-divider pb-4">
              <div>
                <span className="kicker">Telemetry Export</span>
                <h3 className="font-display text-base font-semibold text-ink">
                  Full Technical Comparative JSON Dossier
                </h3>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="chip font-mono">CMP-{rows.length}SITES</span>
                <button
                  type="button"
                  className="btn-ghost !px-3 !py-1.5 !text-xs cursor-pointer"
                  onClick={() => setShowJsonDossier((prev) => !prev)}
                >
                  {showJsonDossier ? "Hide Raw JSON" : "Inspect Raw JSON"}
                </button>
                <button
                  type="button"
                  className="btn-primary !px-3.5 !py-1.5 !text-xs flex items-center gap-1.5 cursor-pointer"
                  onClick={handleDownloadJson}
                >
                  <DownloadIcon className="h-3.5 w-3.5" />
                  Download JSON
                </button>
              </div>
            </div>

            {showJsonDossier && (
              <pre className="mt-4 max-h-96 overflow-auto rounded-lg border border-divider bg-space/80 p-4 font-mono text-xs leading-relaxed text-slate-200">
                {JSON.stringify(comparison, null, 2)}
              </pre>
            )}
          </div>

          {/* ================= Section 3: Data Provenance & Sensor Heritage ================= */}
          <div className="panel p-6">
            <span className="kicker mb-2 block">Data Provenance &amp; Sensor Heritage</span>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded border border-divider/60 bg-elevated/30 p-3.5">
                <h4 className="font-display text-xs font-semibold text-ink">LRO LOLA DEM</h4>
                <p className="mt-1 text-[11px] leading-relaxed text-muted">
                  Lunar Orbiter Laser Altimeter SHDR 80m profiles providing topographic elevation,
                  Horn (1981) 3x3 slope gradients, and 15m RMS surface roughness.
                </p>
              </div>
              <div className="rounded border border-divider/60 bg-elevated/30 p-3.5">
                <h4 className="font-display text-xs font-semibold text-ink">LRO LROC NAC</h4>
                <p className="mt-1 text-[11px] leading-relaxed text-muted">
                  Narrow Angle Camera high-resolution optical imagery for surface crater and boulder
                  hazard detection inferred via fine-tuned YOLOv8n polar weights.
                </p>
              </div>
              <div className="rounded border border-divider/60 bg-elevated/30 p-3.5">
                <h4 className="font-display text-xs font-semibold text-ink">Solar &amp; Comms Models</h4>
                <p className="mt-1 text-[11px] leading-relaxed text-muted">
                  JPL Horizons DE430/SPICE orbital kernels calculating synodic sunlight exposure,
                  surface darkness intervals, and Direct-to-Earth line-of-sight visibility.
                </p>
              </div>
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
