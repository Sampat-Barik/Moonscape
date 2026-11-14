import { useEffect } from "react";
import type { Route } from "@/hooks/useHashRoute";
import { useApp } from "@/context/AppContext";
import CoordinateSelector from "@/components/CoordinateSelector";
import TerrainCard from "@/components/TerrainCard";
import SuitabilityScore from "@/components/SuitabilityScore";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import { fmtCoord, pickBool, pickNumber, pickString } from "@/utils/format";
import {
  ArrowRightIcon,
  GlobeIcon,
  MountainIcon,
  RefreshIcon,
  RocketIcon,
  ShieldIcon,
  SlopeIcon,
  SparkIcon,
  SunIcon,
  TableIcon,
  WavesIcon,
} from "@/components/icons";

export default function Dashboard({ navigate }: { navigate: (r: Route) => void }) {
  const {
    analysis,
    analysisStatus,
    analysisError,
    selection,
    setSelection,
    runAnalysis,
    runScore,
    score,
    scoreStatus,
    scoreError,
    runHazards,
  } = useApp();

  // Whenever an analysis exists, request the preliminary score (POST /api/score).
  useEffect(() => {
    if (analysis && scoreStatus === "idle") void runScore(selection);
  }, [analysis, scoreStatus, runScore, selection]);

  // Score: prefer the /api/score response, fall back to a score embedded in the analysis.
  const embeddedScore = analysis
    ? {
        score: pickNumber(analysis, ["score", "suitability_score"]),
        grade: pickString(analysis, ["grade"]),
        label: pickString(analysis, ["score_label", "label"]),
        breakdown: (analysis.breakdown ?? analysis.score_breakdown) as
          | Record<string, number | null>
          | undefined,
        disclaimer: pickString(analysis, ["disclaimer", "score_disclaimer"]),
      }
    : null;
  const scoreData = scoreStatus === "ready" && score ? score : embeddedScore;
  const scoreLoading = Boolean(analysis) && scoreStatus === "loading" && !embeddedScore;
  const scoreFailed = scoreStatus === "error" && !embeddedScore;

  const onReRun = () => void runAnalysis(selection);
  const goHazards = async () => {
    await runHazards(selection);
    navigate("/hazards");
  };

  // ------------------------- no analysis yet -------------------------
  if (!analysis) {
    return (
      <div className="relative flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-6 py-20">
        {/* Background texture */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: "url('/assets/lunar/lunar-landscape.jpg')",
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        <div className="relative z-10 w-full max-w-lg text-center">
          <span className="kicker">Analysis Dashboard</span>
          <h1 className="mt-3 font-display text-4xl font-semibold text-ink">
            No analysis session
          </h1>
          <p className="mx-auto mt-4 max-w-sm text-sm leading-relaxed text-muted">
            Select coordinates in the Lunar Explorer or enter them here, then run a terrain analysis.
          </p>
          <div className="divider mx-auto mt-8 w-32" />

          <div className="panel mx-auto mt-8 max-w-md p-6 text-left">
            <span className="kicker mb-4 block">Coordinates</span>
            <CoordinateSelector value={selection} onChange={setSelection} />
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                className="btn-primary flex-1 justify-center"
                onClick={() => void runAnalysis(selection)}
                disabled={analysisStatus === "loading"}
              >
                {analysisStatus === "loading" ? <span className="spinner" /> : <RocketIcon className="h-5 w-5" />}
                Run analysis
              </button>
              <button className="btn-ghost" onClick={() => navigate("/explorer")}>
                <GlobeIcon className="h-4 w-4" />
                Open Explorer
              </button>
            </div>
            {analysisStatus === "loading" && (
              <div className="mt-4">
                <LoadingState label="Running analysis (POST /api/analysis/run)…" />
              </div>
            )}
            {analysisStatus === "error" && (
              <div className="mt-4">
                <ErrorState title="Analysis failed" message={analysisError} onRetry={() => void runAnalysis(selection)} />
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // --------------------------- cards data ----------------------------
  const el = analysis.elevation ?? null;
  const sl = analysis.slope ?? null;
  const rg = analysis.roughness ?? null;
  const il = analysis.illumination ?? null;
  const globalSources = Array.isArray(analysis.data_sources) ? analysis.data_sources.join(", ") : null;
  const sourceOf = (block: object | null) => pickString(block, ["source", "dataset"]) ?? globalSources;
  const psr = pickBool(il, ["psr", "psr_nearby", "has_psr"]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">

      {/* ===== Top context bar ===== */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-divider pb-5">
        <div>
          <span className="kicker">Analysis Dashboard</span>
          <h1 className="mt-1 font-display text-2xl font-semibold text-ink">
            Terrain &amp; Environment
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {analysis.analysis_id && <span className="chip font-mono">ID: {analysis.analysis_id}</span>}
          {analysis.timestamp && <span className="chip font-mono">{String(analysis.timestamp)}</span>}
          <button
            className="btn-ghost !px-4 !py-2 !text-xs"
            onClick={onReRun}
            disabled={analysisStatus === "loading"}
          >
            {analysisStatus === "loading" ? <span className="spinner !h-4 !w-4" /> : <RefreshIcon className="h-4 w-4" />}
            Re-run
          </button>
        </div>
      </div>

      {/* ===== Location context strip ===== */}
      <div className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-divider pb-4 text-[13px] text-muted">
        <span className="font-mono text-cyan">{fmtCoord(selection.latitude, selection.longitude)}</span>
        <span>radius: <span className="font-mono text-ink">{selection.radius_m} m</span></span>
        {globalSources && <span>sources: <span className="text-ink">{globalSources}</span></span>}
      </div>

      {/* Re-run feedback */}
      {analysisStatus === "loading" && (
        <div className="panel mb-6 p-5">
          <LoadingState label="Re-running analysis (POST /api/analysis/run)…" />
        </div>
      )}
      {analysisStatus === "error" && (
        <div className="mb-6">
          <ErrorState title="Analysis failed" message={analysisError} onRetry={onReRun} />
        </div>
      )}

      {/* ===== 4 Terrain metric cards ===== */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <TerrainCard
          title="Elevation"
          icon={<MountainIcon className="h-5 w-5" />}
          value={pickNumber(el, ["mean_m", "mean", "elevation_m", "value", "elevation"])}
          unit="m"
          digits={1}
          available={el !== null && el !== undefined}
          source={sourceOf(el)}
          stats={[
            { label: "Min", value: pickNumber(el, ["min_m", "min"]), unit: "m", digits: 1 },
            { label: "Max", value: pickNumber(el, ["max_m", "max"]), unit: "m", digits: 1 },
            { label: "Std dev", value: pickNumber(el, ["stddev_m", "stddev", "std"]), unit: "m" },
          ]}
        />
        <TerrainCard
          title="Slope"
          icon={<SlopeIcon className="h-5 w-5" />}
          value={pickNumber(sl, ["mean_deg", "mean", "slope_deg", "value"])}
          unit="°"
          digits={2}
          available={sl !== null && sl !== undefined}
          source={sourceOf(sl)}
          stats={[
            { label: "Max", value: pickNumber(sl, ["max_deg", "max"]), unit: "°", digits: 1 },
            { label: "P95", value: pickNumber(sl, ["p95_deg", "p95"]), unit: "°", digits: 1 },
          ]}
        />
        <TerrainCard
          title="Roughness"
          icon={<WavesIcon className="h-5 w-5" />}
          value={pickNumber(rg, ["rms_m", "rms", "value"])}
          unit="m"
          digits={2}
          available={rg !== null && rg !== undefined}
          source={sourceOf(rg)}
          stats={[{ label: "Max", value: pickNumber(rg, ["max_m", "max"]), unit: "m" }]}
        />
        <TerrainCard
          title="Illumination & Comm"
          icon={<SunIcon className="h-5 w-5" />}
          value={pickNumber(il, ["sunlight_percent", "sunlit_percent", "illumination_percent", "percent_sunlit", "percent", "value"])}
          unit="% sunlit"
          digits={1}
          available={il !== null && il !== undefined}
          source={sourceOf(il)}
          stats={[
            { label: "Solar elevation", value: pickNumber(il, ["solar_elevation_deg", "solar_elevation", "sun_elevation_deg"]), unit: "°", digits: 1 },
            { label: "Duration", value: pickNumber(il, ["sunlight_duration_days", "duration_days", "duration"]), unit: "days", digits: 1 },
          ]}
          extras={[
            { label: "PSR nearby", text: psr === null ? null : psr ? "yes" : "no" },
            { label: "Earth Comm LOS", text: pickString(analysis, ["earth_visibility", "earth_visibility_state"]) ?? (pickBool(analysis, ["earth_visible", "has_earth_los"]) !== null ? (pickBool(analysis, ["earth_visible", "has_earth_los"]) ? "Direct LOS" : "Obscured") : null) },
            { label: "Next sunset", text: pickString(il, ["sunset_time", "next_sunset", "sunset"]) },
          ]}
          note={pickString(il, ["note", "description"])}
        />
      </div>

      {/* ===== Availability strip ===== */}
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-divider pt-4">
        <span className="kicker mr-2 opacity-60">Availability</span>
        {(
          [
            ["elevation", analysis.elevation],
            ["slope", analysis.slope],
            ["roughness", analysis.roughness],
            ["illumination", analysis.illumination],
          ] as const
        ).map(([key, block]) => (
          <span key={key} className="chip">
            <span className={`h-1.5 w-1.5 rounded-full ${block ? "bg-good" : "bg-warn"}`} />
            {key}: {block ? "available" : "unavailable"}
          </span>
        ))}
      </div>

      {/* ===== Suitability Score ===== */}
      <div className="mt-6">
        <SuitabilityScore
          score={scoreData?.score ?? null}
          grade={scoreData?.grade ?? null}
          label={scoreData?.label ?? null}
          breakdown={scoreData?.breakdown ?? null}
          disclaimer={scoreData?.disclaimer ?? null}
          loading={scoreLoading}
          error={scoreFailed ? scoreError : null}
          onRetry={() => void runScore(selection)}
        />
      </div>

      {/* ===== Next steps ===== */}
      <div className="mt-6">
        <div className="divider mb-5" />
        <span className="kicker mb-4 block">Next Steps</span>
        <div className="grid gap-3 sm:grid-cols-3">
          <button
            className="panel group flex items-center justify-between gap-3 p-5 text-left transition-colors hover:border-accent/40"
            onClick={() => void goHazards()}
          >
            <span className="flex items-center gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-accent/10 text-cyan">
                <ShieldIcon className="h-5 w-5" />
              </span>
              <span>
                <span className="block text-sm font-semibold text-ink">Hazard Analysis</span>
                <span className="block text-[11px] text-muted">POST /api/hazards/predict</span>
              </span>
            </span>
            <ArrowRightIcon className="h-4 w-4 shrink-0 text-muted transition-transform group-hover:translate-x-1 group-hover:text-cyan" />
          </button>
          <button
            className="panel group flex items-center justify-between gap-3 p-5 text-left transition-colors hover:border-accent/40"
            onClick={() => navigate("/report")}
          >
            <span className="flex items-center gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-accent/10 text-cyan">
                <SparkIcon className="h-5 w-5" />
              </span>
              <span>
                <span className="block text-sm font-semibold text-ink">AI Report</span>
                <span className="block text-[11px] text-muted">POST /api/ai/explain</span>
              </span>
            </span>
            <ArrowRightIcon className="h-4 w-4 shrink-0 text-muted transition-transform group-hover:translate-x-1 group-hover:text-cyan" />
          </button>
          <button
            className="panel group flex items-center justify-between gap-3 p-5 text-left transition-colors hover:border-accent/40"
            onClick={() => navigate("/compare")}
          >
            <span className="flex items-center gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-accent/10 text-cyan">
                <TableIcon className="h-5 w-5" />
              </span>
              <span>
                <span className="block text-sm font-semibold text-ink">Site Comparison</span>
                <span className="block text-[11px] text-muted">POST /api/sites/compare</span>
              </span>
            </span>
            <ArrowRightIcon className="h-4 w-4 shrink-0 text-muted transition-transform group-hover:translate-x-1 group-hover:text-cyan" />
          </button>
        </div>
      </div>
    </div>
  );
}
