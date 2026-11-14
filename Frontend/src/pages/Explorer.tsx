import { useEffect, useMemo, useState } from "react";
import type { Route } from "@/hooks/useHashRoute";
import { useApp } from "@/context/AppContext";
import LunarMap from "@/components/LunarMap";
import CoordinateSelector from "@/components/CoordinateSelector";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import DataUnavailable from "@/components/DataUnavailable";
import { api } from "@/services/api";
import type { MapConfig } from "@/types";
import { fmtCoord, fmtNum, pickNumber, pickString } from "@/utils/format";
import {
  CrosshairIcon,
  RefreshIcon,
  RocketIcon,
  SunIcon,
  TargetIcon,
} from "@/components/icons";

export default function Explorer({ navigate }: { navigate: (r: Route) => void }) {
  const {
    sites,
    sitesStatus,
    sitesError,
    refreshSites,
    selection,
    setSelection,
    terrain,
    terrainStatus,
    terrainError,
    refreshTerrain,
    runAnalysis,
    analysisStatus,
    analysisError,
  } = useApp();

  const [focusNonce, setFocusNonce] = useState(0);
  const [focusSite, setFocusSite] = useState<{ lat: number; lon: number; nonce: number } | null>(null);
  const [mapConfig, setMapConfig] = useState<MapConfig | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sunSimOpen, setSunSimOpen] = useState(false);
  const [sunAngle, setSunAngle] = useState(35);

  // GET /api/map/config — used for attribution / initial focus hints.
  useEffect(() => {
    let alive = true;
    api
      .getMapConfig()
      .then((c) => {
        if (alive) setMapConfig(c);
      })
      .catch(() => {
        /* non-critical */
      });
    return () => {
      alive = false;
    };
  }, []);

  // Debounced terrain preview (GET /api/terrain) whenever the selection changes.
  useEffect(() => {
    const t = setTimeout(() => {
      void refreshTerrain(selection);
    }, 450);
    return () => clearTimeout(t);
  }, [selection, refreshTerrain]);

  const markers = useMemo(
    () =>
      sites.map((s) => ({
        lat: s.latitude,
        lon: s.longitude,
        label: s.name ?? s.site_id,
        color: "#fbbf24",
      })),
    [sites]
  );

  const onSelect = (lat: number, lon: number) =>
    setSelection({
      ...selection,
      latitude: Math.round(lat * 1e4) / 1e4,
      longitude: Math.round(lon * 1e4) / 1e4,
    });

  const onAnalyse = async () => {
    const ok = await runAnalysis(selection);
    if (ok) navigate("/dashboard");
  };

  const attribution = mapConfig ? pickString(mapConfig, ["attribution", "tile_attribution", "credits"]) : null;

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col overflow-hidden">
      {/* Full-screen flex: map + sidebar */}
      <div className="relative flex flex-1 overflow-hidden">

        {/* ======================== 3D MOON MAP ======================== */}
        <div className="relative flex-1 overflow-hidden bg-space">
          <LunarMap
            className="h-full w-full"
            selected={{ lat: selection.latitude, lon: selection.longitude }}
            markers={markers}
            onSelect={onSelect}
            focusSouthPoleSignal={focusNonce}
            focusSiteSignal={focusSite ?? undefined}
            initialSouthPole
            sunAngle={sunAngle}
          />

          {/* HUD: top-left label */}
          <div className="pointer-events-none absolute left-5 top-5 flex items-center gap-3">
            <div className="glass-soft rounded px-3 py-1.5">
              <p className="font-condensed text-xs font-semibold uppercase tracking-[0.22em] text-accent">
                MOONSCAPE EXPLORER
              </p>
            </div>
            {attribution && (
              <span className="chip hidden sm:inline-flex">{attribution}</span>
            )}
          </div>

          {/* HUD: top-right controls */}
          <div className="absolute right-5 top-5 flex items-center gap-2">
            <button
              className={`glass-soft rounded p-2 transition-colors ${
                sunSimOpen ? "text-cyan border-accent/40" : "text-muted hover:text-ink"
              }`}
              title="Toggle Solar Simulation & Shadow Angle"
              onClick={() => setSunSimOpen((v) => !v)}
            >
              <SunIcon className="h-4 w-4" />
            </button>
            <button
              className="glass-soft rounded p-2 text-muted transition-colors hover:text-ink"
              title="Reset to South Pole"
              onClick={() => setFocusNonce((n) => n + 1)}
            >
              <TargetIcon className="h-4 w-4" />
            </button>
            <button
              className="glass-soft rounded px-3 py-2 font-condensed text-xs font-semibold uppercase tracking-widest text-muted transition-colors hover:text-ink"
              onClick={() => setSidebarOpen((v) => !v)}
            >
              {sidebarOpen ? "HIDE PANEL" : "SHOW PANEL"}
            </button>
          </div>

          {/* HUD: Solar Diurnal Time Simulation Slider */}
          {sunSimOpen && (
            <div className="glass-soft absolute right-5 top-18 z-20 w-72 rounded-lg p-3.5 shadow-xl">
              <div className="flex items-center justify-between text-xs">
                <span className="font-condensed font-semibold uppercase tracking-wider text-cyan">
                  Solar Diurnal Cycle
                </span>
                <span className="font-mono text-[11px] text-muted">
                  Day {((sunAngle / 360) * 29.53).toFixed(1)} / 29.5d
                </span>
              </div>
              <p className="mt-1 text-[10px] leading-tight text-muted">
                Simulate moving solar azimuth and crater shadows across the South Pole.
              </p>
              <div className="mt-2.5 flex items-center gap-2">
                <input
                  type="range"
                  min="0"
                  max="360"
                  value={sunAngle}
                  onChange={(e) => setSunAngle(Number(e.target.value))}
                  className="h-1.5 w-full cursor-pointer appearance-none rounded bg-elevated accent-cyan"
                />
                <span className="font-mono text-xs font-semibold text-cyan w-10 text-right">
                  {sunAngle}°
                </span>
              </div>
            </div>
          )}

          {/* HUD: bottom-left coordinate readout */}
          <div className="pointer-events-none absolute bottom-5 left-5">
            <div className="glass-soft rounded px-3 py-2">
              <div className="flex items-center gap-2">
                <CrosshairIcon className="h-3.5 w-3.5 text-cyan" />
                <span className="font-mono text-xs text-cyan">
                  {fmtCoord(selection.latitude, selection.longitude)}
                </span>
                <span className="text-muted/60">·</span>
                <span className="font-mono text-xs text-muted">r {selection.radius_m} m</span>
              </div>
            </div>
          </div>

          {/* HUD: bottom-right attribution */}
          <div className="pointer-events-none absolute bottom-5 right-5">
            <div className="glass-soft rounded px-3 py-1.5">
              <span className="font-mono text-[10px] text-muted/70">
                THREE.JS · LUNAR SURFACE DATA
              </span>
            </div>
          </div>

          {/* Click hint if sidebar is hidden */}
          {!sidebarOpen && (
            <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
              <div className="glass-soft rounded-lg px-4 py-2 text-center">
                <p className="font-condensed text-xs uppercase tracking-widest text-muted">
                  Click surface to select · Drag to rotate · Scroll to zoom
                </p>
              </div>
            </div>
          )}
        </div>

        {/* ======================== SIDEBAR ======================== */}
        <aside
          className={`flex flex-col border-l border-divider transition-all duration-300 z-20 absolute sm:relative right-0 inset-y-0 ${
            sidebarOpen ? "w-full max-w-[340px] sm:w-80 opacity-100" : "w-0 opacity-0 overflow-hidden pointer-events-none"
          }`}
          style={{
            background: "linear-gradient(180deg, rgba(5,11,22,0.97) 0%, rgba(3,7,18,0.98) 100%)",
            backdropFilter: "blur(16px)",
          }}
        >
          <div className="flex-1 overflow-y-auto">
            {/* ---- Selected Site ---- */}
            <div className="border-b border-divider p-5">
              <div className="flex items-center justify-between">
                <span className="kicker">Selected Site</span>
                <TargetIcon className="h-4 w-4 text-accent" />
              </div>
              <p className="mt-2 font-mono text-lg font-semibold text-cyan">
                {fmtCoord(selection.latitude, selection.longitude)}
              </p>
              <p className="font-mono text-xs text-muted">radius: {selection.radius_m} m</p>
              <div className="mt-4">
                <CoordinateSelector value={selection} onChange={setSelection} showPresets={false} />
              </div>
              <div className="mt-4 flex gap-2">
                <button
                  className="btn-ghost flex-1 !px-3 !py-2 !text-xs"
                  onClick={() => setFocusNonce((n) => n + 1)}
                >
                  <TargetIcon className="h-3.5 w-3.5" />
                  South Pole
                </button>
                <button
                  className="btn-primary flex-1 !px-3 !py-2 !text-xs"
                  onClick={() => void onAnalyse()}
                  disabled={analysisStatus === "loading"}
                >
                  {analysisStatus === "loading" ? (
                    <span className="spinner !h-4 !w-4" />
                  ) : (
                    <RocketIcon className="h-3.5 w-3.5" />
                  )}
                  Analyse
                </button>
              </div>
              {analysisStatus === "error" && (
                <div className="mt-3">
                  <ErrorState
                    title="Analysis failed (POST /api/analysis/run)"
                    message={analysisError}
                    onRetry={() => void onAnalyse()}
                  />
                </div>
              )}
            </div>

            {/* ---- Preset Sites ---- */}
            <div className="border-b border-divider p-5">
              <div className="mb-3 flex items-center justify-between">
                <span className="kicker">Quick Presets</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { label: "South Pole", lat: -90, lon: 0 },
                  { label: "Shackleton Rim", lat: -89.9, lon: 0 },
                  { label: "Connecting Ridge", lat: -89.42, lon: 34 },
                  { label: "Faustini Rim", lat: -87.2, lon: 80 },
                  { label: "Malapert Massif", lat: -86.5, lon: 0 },
                ].map((p) => {
                  const active =
                    Math.abs(p.lat - selection.latitude) < 0.01 &&
                    Math.abs(p.lon - selection.longitude) < 0.01;
                  return (
                    <button
                      key={p.label}
                      className={`chip cursor-pointer transition-all ${
                        active
                          ? "!border-accent/50 !text-cyan"
                          : "hover:!border-accent/35 hover:!text-cyan"
                      }`}
                      onClick={() => {
                        setSelection({ ...selection, latitude: p.lat, longitude: p.lon });
                        setFocusSite({ lat: p.lat, lon: p.lon, nonce: Date.now() });
                      }}
                    >
                      {p.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ---- Terrain Preview ---- */}
            <div className="border-b border-divider p-5">
              <div className="mb-3 flex items-center justify-between">
                <span className="kicker">Terrain Preview</span>
                <span className="chip font-mono">GET /api/terrain</span>
              </div>
              {terrainStatus === "loading" && <LoadingState label="Fetching terrain…" />}
              {terrainStatus === "error" && (
                <ErrorState
                  title="Terrain request failed"
                  message={terrainError}
                  onRetry={() => void refreshTerrain(selection)}
                />
              )}
              {terrainStatus === "ready" && terrain && (
                <dl className="space-y-2">
                  {[
                    { label: "Elevation (mean)", v: pickNumber(terrain.elevation, ["mean_m", "mean", "elevation_m", "value"]), unit: "m" },
                    { label: "Slope (mean)", v: pickNumber(terrain.slope, ["mean_deg", "mean", "slope_deg", "value"]), unit: "°" },
                    { label: "Roughness (RMS)", v: pickNumber(terrain.roughness, ["rms_m", "rms", "value"]), unit: "m" },
                    { label: "Sunlight", v: pickNumber(terrain.illumination, ["sunlight_percent", "sunlit_percent", "illumination_percent", "percent", "value"]), unit: "%" },
                  ].map((r) => (
                    <div key={r.label} className="flex items-center justify-between gap-2 text-[13px]">
                      <dt className="text-muted">{r.label}</dt>
                      <dd className="font-mono text-ink">
                        {r.v === null ? (
                          <span className="text-warn text-[11px]">unavailable</span>
                        ) : (
                          `${fmtNum(r.v, 2)} ${r.unit}`
                        )}
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
              {terrainStatus === "ready" && !terrain && <DataUnavailable />}
              {terrainStatus === "idle" && (
                <p className="text-xs text-muted">Select a site to preview terrain.</p>
              )}
            </div>

            {/* ---- Candidate Sites ---- */}
            <div className="p-5">
              <div className="mb-3 flex items-center justify-between">
                <span className="kicker">Candidate Sites</span>
                <div className="flex items-center gap-2">
                  <span className="chip font-mono">GET /api/sites</span>
                  {sitesStatus === "error" && (
                    <button onClick={refreshSites} className="text-xs text-warn hover:text-bad">
                      <RefreshIcon className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
              {sitesStatus === "loading" && <LoadingState label="Loading sites…" />}
              {sitesStatus === "error" && (
                <ErrorState title="Could not load sites" message={sitesError} onRetry={refreshSites} />
              )}
              {sitesStatus === "ready" && (
                <ul className="space-y-1.5">
                  {sites.map((s) => {
                    const active =
                      Math.abs(s.latitude - selection.latitude) < 1e-6 &&
                      Math.abs(s.longitude - selection.longitude) < 1e-6;
                    return (
                      <li key={s.site_id}>
                        <button
                          onClick={() => {
                            setSelection({
                              latitude: s.latitude,
                              longitude: s.longitude,
                              radius_m: selection.radius_m,
                            });
                            setFocusSite({ lat: s.latitude, lon: s.longitude, nonce: Date.now() });
                          }}
                          className={`w-full rounded border p-3 text-left transition-all ${
                            active
                              ? "border-accent/60 bg-accent/8"
                              : "border-divider bg-transparent hover:border-accent/30 hover:bg-accent/5"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-semibold text-ink">
                              {s.name ?? s.site_id}
                            </span>
                            <span className="font-mono text-[10px] text-cyan">
                              {fmtCoord(s.latitude, s.longitude)}
                            </span>
                          </div>
                          {s.description && (
                            <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-muted">
                              {s.description}
                            </p>
                          )}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>

          {/* Sidebar footer: Analyse CTA */}
          <div className="border-t border-divider p-4">
            <button
              className="btn-primary w-full justify-center"
              onClick={() => void onAnalyse()}
              disabled={analysisStatus === "loading"}
            >
              {analysisStatus === "loading" ? (
                <span className="spinner !h-4 !w-4" />
              ) : (
                <RocketIcon className="h-4 w-4" />
              )}
              Run Analysis
            </button>
          </div>
        </aside>
      </div>
    </div>
  );
}
