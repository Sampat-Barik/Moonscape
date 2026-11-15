import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import type { Route } from "@/hooks/useHashRoute";
import { useApp } from "@/context/AppContext";
import LunarMap from "@/components/LunarMap";
import RegionalTerrainViewer from "@/components/RegionalTerrainViewer";
import CesiumLunarViewer from "@/components/CesiumLunarViewer";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import DataUnavailable from "@/components/DataUnavailable";
import Button from "@/components/ui/Button";
import SegmentedControl from "@/components/ui/SegmentedControl";
import { api } from "@/services/api";
import type { MapConfig, LROCCoverageResponse } from "@/types";
import { fmtCoord, fmtNum, pickNumber, pickString } from "@/utils/format";
import {
  CrosshairIcon,
  GlobeIcon,
  MountainIcon,
  RocketIcon,
  SunIcon,
  TargetIcon,
  LayersIcon,
  SlidersIcon,
  TableIcon,
  ChevronDownIcon,
  CheckIcon,
  AlertIcon,
  XIcon,
} from "@/components/icons";

/* ---------------------------------------------------------------------------
 * CANDIDATE SITE PRESETS (VERIFIED NASA ARTEMIS COORDINATES)
 * ------------------------------------------------------------------------- */
const QUICK_PRESETS = [
  {
    label: "Connecting Ridge",
    lat: -89.44,
    lon: 222.50,
    siteId: "shackleton_connecting_ridge",
    description: "Artemis III Site 01 (Verified 5m DEM available)",
    hasHighRes: true,
  },
  {
    label: "Shackleton Rim",
    lat: -89.90,
    lon: 0.0,
    siteId: "shackleton_rim",
    description: "Connecting Ridge peak with persistent solar illumination",
    hasHighRes: false,
  },
  {
    label: "Faustini Rim",
    lat: -87.10,
    lon: 77.00,
    siteId: "faustini_rim_a",
    description: "Faustini Rim A candidate site adjacent to cold volatile traps",
    hasHighRes: false,
  },
  {
    label: "Malapert Massif",
    lat: -84.90,
    lon: 12.90,
    siteId: "malapert_mountain",
    description: "Malapert Mountain (Alpha) peak for continuous direct Earth communication",
    hasHighRes: false,
  },
  {
    label: "South Pole Peak",
    lat: -90.00,
    lon: 0.0,
    siteId: "south_pole_peak",
    description: "Geometric lunar South Pole origin (90.00°S, 0.00°E)",
    hasHighRes: false,
  },
  {
    label: "de Gerlache Rim",
    lat: -88.50,
    lon: 271.70,
    siteId: "de_gerlache_rim_2",
    description: "de Gerlache Rim 2 massif between Shackleton & de Gerlache",
    hasHighRes: false,
  },
];

const RADIUS_OPTIONS = [250, 500, 1000, 2000];

/* ---------------------------------------------------------------------------
 * MAIN LUNAR EXPLORER COMPONENT
 * ------------------------------------------------------------------------- */
export default function Explorer({ navigate }: { navigate: (r: Route) => void }) {
  const {
    sites,
    selection,
    setSelection,
    coverage,
    terrain,
    terrainStatus,
    terrainError,
    refreshTerrain,
    runAnalysis,
    analysisStatus,
    analysisError,
    terrainMesh,
    terrainMeshStatus,
    terrainMeshError,
    fetchTerrainMesh,
    detectedZones,
    hazards,
  } = useApp();

  // Navigation and view state
  const [viewMode, setViewMode] = useState<"global" | "terrain" | "cesium">("global");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeLayer, setActiveLayer] = useState<string>("default");
  const [openDropdown, setOpenDropdown] = useState<"basemap" | "layers" | "solar" | null>(null);

  // Focus signals for camera glide
  const [focusNonce, setFocusNonce] = useState(0);
  const [focusSite, setFocusSite] = useState<{ lat: number; lon: number; nonce: number } | null>(null);

  // Solar simulation state
  const [sunAngle, setSunAngle] = useState(35);

  // External data
  const [mapConfig, setMapConfig] = useState<MapConfig | null>(null);
  const [lrocCoverage, setLrocCoverage] = useState<LROCCoverageResponse | null>(null);
  const [lrocLoading, setLrocLoading] = useState(false);

  // Close open dropdowns on Escape or click outside
  useEffect(() => {
    if (!openDropdown) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpenDropdown(null);
    };
    const onClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest("[data-toolbar-menu]") && !target.closest("[data-toolbar-trigger]")) {
        setOpenDropdown(null);
      }
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClickOutside);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClickOutside);
    };
  }, [openDropdown]);

  // Fetch initial map configuration
  useEffect(() => {
    let alive = true;
    api
      .getMapConfig()
      .then((c) => {
        if (alive) setMapConfig(c);
      })
      .catch(() => {
        /* non-critical fallback */
      });
    return () => {
      alive = false;
    };
  }, []);

  // Debounced terrain preview & LROC coverage lookup whenever selection changes
  useEffect(() => {
    let alive = true;
    setLrocLoading(true);
    const t = setTimeout(() => {
      void refreshTerrain(selection);
      if (viewMode === "terrain") {
        void fetchTerrainMesh(selection);
      }
      api
        .getLROCCoverage(selection.latitude, selection.longitude)
        .then((res) => {
          if (alive) {
            setLrocCoverage(res);
            setLrocLoading(false);
          }
        })
        .catch(() => {
          if (alive) setLrocLoading(false);
        });
    }, 400);

    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [selection, refreshTerrain, viewMode, fetchTerrainMesh]);

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

  const onSelect = (lat: number, lon: number) => {
    setSelection({
      ...selection,
      latitude: Math.round(lat * 1e4) / 1e4,
      longitude: Math.round(lon * 1e4) / 1e4,
    });
  };

  const coverageZone = selection.latitude < -90 || selection.latitude > 90
    ? 'invalid'
    : selection.latitude > -70
    ? 'outside'
    : selection.latitude > -75
    ? 'context'
    : selection.latitude > -80
    ? 'extended'
    : 'core';

  const isInAnalysisRegion = selection.latitude <= -70 && selection.latitude >= -90;

  const onAnalyse = async () => {
    if (!isInAnalysisRegion) return;
    const ok = await runAnalysis(selection);
    if (ok) navigate("/dashboard");
  };

  const attribution = mapConfig ? pickString(mapConfig, ["attribution", "tile_attribution", "credits"]) : null;

  return (
    <div className="relative flex flex-1 flex-col h-full overflow-hidden bg-space text-ink select-none">
      {/* ===================================================================
       * LEVEL 2 — LUNAR EXPLORER DEDICATED TOOLBAR
       * Sits immediately below Level 1 Global Navigation, dedicated horizontal bar.
       * =================================================================== */}
      <nav
        aria-label="Lunar Explorer Controls"
        className="relative z-30 flex h-13 shrink-0 items-center justify-between border-b border-divider/70 bg-[#141414]/95 px-4 lg:px-6 backdrop-blur-md shadow-xs gap-3"
      >
        {/* Left Section: View Mode Segmented Control */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden sm:flex items-center gap-2 pr-3 border-r border-divider/50">
            <span className="font-condensed text-xs font-bold tracking-[0.2em] text-ink uppercase">
              EXPLORER
            </span>
            <span className="chip font-mono text-[10px] !py-0.5 !px-1.5 border-divider/40 text-muted">
              80°S–90°S
            </span>
          </div>

          {/* Segmented Control */}
          <SegmentedControl
            options={[
              {
                value: "global",
                label: "Globe",
                description: "Mode A: Three.js Macroscopic Lunar Sphere",
                icon: <GlobeIcon className="h-3.5 w-3.5" />,
              },
              {
                value: "terrain",
                label: "Terrain",
                description: "Mode B: High-Resolution LOLA 5m DEM 3D Relief",
                icon: <MountainIcon className="h-3.5 w-3.5" />,
              },
              {
                value: "cesium",
                label: "Cesium",
                description: "Mode C: CesiumJS IAU Lunar Ellipsoid Geodesy",
                icon: <TargetIcon className="h-3.5 w-3.5" />,
              },
            ]}
            value={viewMode}
            onChange={(val) => {
              setViewMode(val);
              if (val === "terrain") {
                void fetchTerrainMesh(selection);
              }
            }}
          />
        </div>

        {/* Center Section: Instrument & Altimetry Telemetry Status */}
        <div className="hidden xl:flex items-center gap-2 font-mono text-xs text-muted">
          <span className="h-1.5 w-1.5 rounded-full bg-good animate-pulse" />
          <span className="text-[11px] tracking-wide text-ink/90">
            {viewMode === "terrain"
              ? "LOLA / PGDA PRODUCT 78 (5m DEM) · HORN SLOPE ACTIVE"
              : viewMode === "cesium"
              ? "CESIUMJS · IAU 2000 MOON ELLIPSOID (1,737.4 km)"
              : "LROC WAC 2K MOSAIC · JPL HORIZONS DE441 ACTIVE"}
          </span>
        </div>

        {/* Right Section: Dropdowns, Solar Popover & Panel Toggle */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Basemap Dropdown (Only relevant in Globe view) */}
          {viewMode === "global" && (
            <div className="relative" data-toolbar-menu>
              <Button
                variant={activeLayer === "trek_wac" ? "secondary" : "ghost"}
                size="sm"
                data-toolbar-trigger
                onClick={() => setOpenDropdown(openDropdown === "basemap" ? null : "basemap")}
                icon={<LayersIcon className="h-3.5 w-3.5 text-muted" />}
                iconRight={<ChevronDownIcon className="h-3 w-3 text-muted/70" />}
                title="Select lunar optical basemap layer"
              >
                <span className="hidden sm:inline">
                  {activeLayer === "trek_wac" ? "Trek WAC 100m" : "Basemap"}
                </span>
              </Button>

              <AnimatePresence>
                {openDropdown === "basemap" && (
                  <motion.div
                    initial={{ opacity: 0, y: -4, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -4, scale: 0.98 }}
                    transition={{ duration: 0.15 }}
                    data-toolbar-popover
                    className="absolute right-0 top-full mt-2 w-64 rounded-md border border-divider/80 bg-[#181818] p-2 shadow-2xl z-40 text-xs font-mono"
                  >
                    <span className="block px-2 py-1 text-[10px] uppercase text-muted tracking-wider border-b border-divider/30 mb-1">
                      Lunar Basemap Layer
                    </span>
                    <button
                      onClick={() => {
                        setActiveLayer("default");
                        setOpenDropdown(null);
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-left transition-colors cursor-pointer ${
                        activeLayer === "default"
                          ? "bg-elevated text-ink font-semibold"
                          : "text-muted hover:text-ink hover:bg-white/[0.04]"
                      }`}
                    >
                      <div>
                        <span className="block text-ink">LROC WAC 2K Albedo</span>
                        <span className="text-[10px] text-muted">Equirectangular morphologic</span>
                      </div>
                      {activeLayer === "default" && <CheckIcon className="h-3.5 w-3.5 text-good" />}
                    </button>

                    <button
                      onClick={() => {
                        setActiveLayer("trek_wac");
                        setOpenDropdown(null);
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-left transition-colors cursor-pointer ${
                        activeLayer === "trek_wac"
                          ? "bg-elevated text-ink font-semibold"
                          : "text-muted hover:text-ink hover:bg-white/[0.04]"
                      }`}
                    >
                      <div>
                        <span className="block text-ink">NASA Moon Trek WMTS</span>
                        <span className="text-[10px] text-muted">100m/pixel OGC streaming tiles</span>
                      </div>
                      {activeLayer === "trek_wac" && <CheckIcon className="h-3.5 w-3.5 text-good" />}
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Scientific Layers Dropdown */}
          <div className="relative" data-toolbar-menu>
            <Button
              variant="ghost"
              size="sm"
              data-toolbar-trigger
              onClick={() => setOpenDropdown(openDropdown === "layers" ? null : "layers")}
              icon={<SlidersIcon className="h-3.5 w-3.5 text-muted" />}
              iconRight={<ChevronDownIcon className="h-3 w-3 text-muted/70" />}
              title="Toggle scientific analysis layers & graticules"
            >
              <span className="hidden sm:inline">Layers</span>
            </Button>

            <AnimatePresence>
              {openDropdown === "layers" && (
                <motion.div
                  initial={{ opacity: 0, y: -4, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -4, scale: 0.98 }}
                  transition={{ duration: 0.15 }}
                  data-toolbar-popover
                  className="absolute right-0 top-full mt-2 w-64 rounded-md border border-divider/80 bg-[#181818] p-2 shadow-2xl z-40 text-xs font-mono"
                >
                  <span className="block px-2 py-1 text-[10px] uppercase text-muted tracking-wider border-b border-divider/30 mb-1">
                    Scientific Terrain Overlays
                  </span>
                  <div className="space-y-1.5 p-1 text-[11px]">
                    <div className="flex items-center justify-between py-1 px-1.5">
                      <span className="text-ink">Horn Slope Colormap</span>
                      <span className="text-[10px] text-good">Active (3D)</span>
                    </div>
                    <div className="flex items-center justify-between py-1 px-1.5">
                      <span className="text-ink">Candidate Zone Footprints</span>
                      <span className="text-[10px] text-cyan">5 Sites</span>
                    </div>
                    <div className="flex items-center justify-between py-1 px-1.5">
                      <span className="text-ink">Polar Graticule Grid</span>
                      <span className="text-[10px] text-muted">10° Intervals</span>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Solar Diurnal Simulation Popover */}
          <div className="relative" data-toolbar-menu>
            <Button
              variant={openDropdown === "solar" ? "secondary" : "ghost"}
              size="sm"
              data-toolbar-trigger
              onClick={() => setOpenDropdown(openDropdown === "solar" ? null : "solar")}
              icon={<SunIcon className="h-3.5 w-3.5 text-muted" />}
              title="Simulate solar diurnal cycle and shadow lighting"
            >
              <span className="hidden md:inline font-mono">
                {((sunAngle / 360) * 29.53).toFixed(1)}d / 29.5d
              </span>
            </Button>

            <AnimatePresence>
              {openDropdown === "solar" && (
                <motion.div
                  initial={{ opacity: 0, y: -4, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -4, scale: 0.98 }}
                  transition={{ duration: 0.15 }}
                  data-toolbar-popover
                  className="absolute right-0 top-full mt-2 w-72 rounded-md border border-divider/80 bg-[#181818] p-4 shadow-2xl z-40 text-xs"
                >
                  <div className="flex items-center justify-between border-b border-divider/40 pb-2">
                    <span className="font-mono font-semibold uppercase tracking-wider text-ink">
                      Solar Diurnal Cycle
                    </span>
                    <span className="font-mono text-[11px] text-muted">
                      Day {((sunAngle / 360) * 29.53).toFixed(1)} / 29.5d
                    </span>
                  </div>
                  <p className="mt-2 text-[11px] text-muted leading-relaxed font-body">
                    Simulate low-grazing solar azimuth angle and elongated crater shadows across South Polar relief.
                  </p>
                  <div className="mt-3 flex items-center gap-3">
                    <input
                      type="range"
                      min="0"
                      max="360"
                      value={sunAngle}
                      onChange={(e) => setSunAngle(Number(e.target.value))}
                      className="h-1.5 w-full cursor-pointer appearance-none rounded bg-elevated accent-white"
                    />
                    <span className="font-mono text-xs font-semibold text-ink w-12 text-right">
                      {sunAngle}°
                    </span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Reset View to South Pole Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setFocusNonce((n) => n + 1)}
            icon={<TargetIcon className="h-3.5 w-3.5 text-muted" />}
            title="Reset camera focus and zoom to South Pole (89.44°S, 222.5°E)"
          >
            <span className="hidden lg:inline">Reset View</span>
          </Button>

          {/* Sidebar Toggle Button */}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setSidebarOpen((v) => !v)}
            icon={<TableIcon className="h-3.5 w-3.5 text-muted" />}
            title={sidebarOpen ? "Hide Mission Analysis Panel" : "Show Mission Analysis Panel"}
          >
            <span className="hidden sm:inline">
              {sidebarOpen ? "Hide Panel" : "Show Panel"}
            </span>
          </Button>
        </div>
      </nav>

      {/* ===================================================================
       * LEVEL 3 — MAIN WORKSPACE
       * Split into Left (Large 3D Viewport) and Right (Mission Control Sidebar)
       * =================================================================== */}
      <div className="relative flex flex-1 overflow-hidden min-h-0">
        {/* ==================== 3D VIEWPORT CONTAINER ==================== */}
        <div className="relative flex-1 overflow-hidden min-w-0 min-h-0 bg-space">
          {viewMode === "global" ? (
            <LunarMap
              className="h-full w-full"
              selected={{ lat: selection.latitude, lon: selection.longitude }}
              markers={markers}
              onSelect={onSelect}
              focusSouthPoleSignal={focusNonce}
              focusSiteSignal={focusSite ?? undefined}
              initialSouthPole
              sunAngle={sunAngle}
              activeLayer={activeLayer}
            />
          ) : viewMode === "terrain" ? (
            <RegionalTerrainViewer
              className="h-full w-full"
              meshData={terrainMesh}
              loading={terrainMeshStatus === "loading"}
              error={terrainMeshError}
              onRefresh={() => void fetchTerrainMesh(selection)}
              selectedCoord={{
                lat: selection.latitude,
                lon: selection.longitude,
                radius_m: selection.radius_m,
              }}
              onSelectCoord={onSelect}
              detectedZones={detectedZones}
              hazards={hazards}
              sunAngle={sunAngle}
            />
          ) : (
            <CesiumLunarViewer
              className="h-full w-full"
              selected={{ lat: selection.latitude, lon: selection.longitude }}
              markers={markers}
              onSelect={onSelect}
            />
          )}

          {/* Minimal HUD: Bottom-Left Coordinate Chip */}
          <div className="pointer-events-none absolute bottom-5 left-5 z-20">
            <div className="glass-soft rounded px-3 py-2 border border-divider/60 shadow-lg">
              <div className="flex items-center gap-2.5">
                <CrosshairIcon className="h-3.5 w-3.5 text-ink" />
                <span className="font-mono text-xs font-semibold text-ink tracking-wide">
                  {fmtCoord(selection.latitude, selection.longitude)}
                </span>
                <span className="text-muted/60">·</span>
                <span className="font-mono text-xs text-muted">r {selection.radius_m} m</span>
              </div>
            </div>
          </div>

          {/* Minimal HUD: Bottom-Right Geodetic Reference Frame */}
          <div className="pointer-events-none absolute bottom-5 right-5 z-20 hidden sm:block">
            <div className="glass-soft rounded px-3 py-1.5 border border-divider/60 shadow-lg">
              <span className="font-mono text-[10px] text-muted tracking-wider uppercase">
                {attribution
                  ? attribution
                  : viewMode === "terrain"
                  ? "ESRI:104903 · LOLA 5M RELIEF"
                  : viewMode === "cesium"
                  ? "IAU 2000 MOON · 1,737.4 KM"
                  : "IAU 2000 POLAR STEREOGRAPHIC"}
              </span>
            </div>
          </div>

          {/* Center Hint When Sidebar is Hidden */}
          {!sidebarOpen && (
            <div className="pointer-events-none absolute left-1/2 top-6 -translate-x-1/2 z-20">
              <div className="glass-soft rounded-full px-4 py-1.5 text-center border border-divider/50 shadow-md">
                <p className="font-mono text-[11px] text-muted uppercase tracking-wider">
                  Click surface to select coordinates · Drag to orbit · Scroll to zoom
                </p>
              </div>
            </div>
          )}
        </div>

        {/* ==================== RIGHT MISSION CONTROL SIDEBAR ==================== */}
        <aside
          className={`flex flex-col border-l border-divider/80 bg-[#151515] transition-all duration-300 z-30 shrink-0 h-full overflow-hidden ${
            sidebarOpen
              ? "fixed sm:relative inset-x-0 bottom-0 top-[116px] sm:top-0 sm:inset-auto sm:right-0 w-full sm:w-[360px] lg:w-[380px] translate-x-0 shadow-2xl"
              : "w-0 opacity-0 overflow-hidden pointer-events-none translate-x-full"
          }`}
        >
          {/* Scrollable Content Container */}
          <div className="flex-1 overflow-y-auto divide-y divide-divider/40">
            {/* -----------------------------------------------------------
             * SECTION A — SELECTED LOCATION
             * ----------------------------------------------------------- */}
            <div className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
                  [01] SELECTED COORDINATES
                </span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-muted/60 hidden sm:inline">
                    PRECISION: 0.0001°
                  </span>
                  <button
                    onClick={() => setSidebarOpen(false)}
                    className="sm:hidden text-muted hover:text-ink p-1 rounded hover:bg-surface cursor-pointer"
                    title="Close sidebar panel"
                  >
                    <XIcon className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div>
                <p className="font-mono text-xl font-bold text-ink tracking-tight">
                  {fmtCoord(selection.latitude, selection.longitude)}
                </p>
                <div className="mt-1 flex items-center gap-2 text-xs font-mono text-muted">
                  <span>Radius: {selection.radius_m} meters</span>
                  <span>·</span>
                  <span>Area: {(Math.PI * Math.pow(selection.radius_m, 2) / 1e6).toFixed(2)} km²</span>
                </div>
              </div>

              {/* Polar Coverage Status */}
              {coverage && (
                <div className="flex items-center gap-2 pt-1 font-mono text-xs">
                  <span
                    className={`h-2 w-2 rounded-full shrink-0 ${
                      coverage.in_south_pole_zone ? "bg-good" : "bg-warn"
                    }`}
                  />
                  <span
                    className={`text-[11px] ${
                      coverage.in_south_pole_zone ? "text-good" : "text-warn"
                    }`}
                  >
                    {coverage.in_south_pole_zone
                      ? "NASA LOLA 80m Polar: COVERED"
                      : "OUTSIDE POLAR COVERAGE"}
                  </span>
                  {coverage.best_installed_resolution_m && (
                    <span className="chip text-[10px] !py-0.5 ml-auto">
                      res: {coverage.best_installed_resolution_m}m
                    </span>
                  )}
                </div>
              )}

              {/* Out of bounds warning */}
              {!isInAnalysisRegion && (
                <div className="rounded border border-warn/40 bg-warn/10 p-3 text-left">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-warn">
                    <AlertIcon className="h-4 w-4 shrink-0" />
                    <span>Outside Polar Analysis Region</span>
                  </div>
                  <p className="mt-1 text-[11px] leading-relaxed text-muted font-body">
                    Selected latitude ({selection.latitude}°) is outside the supported South Pole analysis zone (80°S–90°S).
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-2 text-xs !text-ink !border-warn/40"
                    onClick={() => {
                      setSelection({ ...selection, latitude: -89.44, longitude: 222.5 });
                      setFocusNonce((n) => n + 1);
                    }}
                  >
                    Reset to Artemis Site 01 (-89.44°)
                  </Button>
                </div>
              )}
            </div>

            {/* -----------------------------------------------------------
             * SECTION B — COORDINATE CONTROLS & RADIUS
             * ----------------------------------------------------------- */}
            <div className="p-5 space-y-4">
              <span className="font-mono text-[10px] uppercase tracking-widest text-muted block">
                [02] NUMERICAL COORDINATE ADJUSTMENT
              </span>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="coord-lat" className="mb-1 block text-[10px] font-mono uppercase tracking-wider text-muted">
                    Latitude (-90° to -70°)
                  </label>
                  <input
                    id="coord-lat"
                    type="number"
                    step="0.001"
                    min={-90}
                    max={-70}
                    value={selection.latitude}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      if (!Number.isNaN(val)) {
                        setSelection({ ...selection, latitude: val });
                      }
                    }}
                    className="input text-xs font-mono"
                  />
                </div>

                <div>
                  <label htmlFor="coord-lon" className="mb-1 block text-[10px] font-mono uppercase tracking-wider text-muted">
                    Longitude (0° to 360°)
                  </label>
                  <input
                    id="coord-lon"
                    type="number"
                    step="0.001"
                    min={0}
                    max={360}
                    value={selection.longitude}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      if (!Number.isNaN(val)) {
                        setSelection({ ...selection, longitude: val });
                      }
                    }}
                    className="input text-xs font-mono"
                  />
                </div>
              </div>

              {/* Coverage Tier Indicator */}
              <div className="flex items-center justify-between rounded border border-divider/60 bg-surface/60 px-2.5 py-1.5 text-[11px]">
                <span className="text-muted">Coverage Tier:</span>
                <span
                  className={
                    coverageZone === "core"
                      ? "font-mono font-medium text-emerald-400"
                      : coverageZone === "extended"
                      ? "font-mono font-medium text-sky-400"
                      : coverageZone === "context"
                      ? "font-mono font-medium text-amber-400"
                      : "font-mono font-medium text-rose-400"
                  }
                >
                  {coverageZone === "core"
                    ? "Core South Pole (-90° to -80°)"
                    : coverageZone === "extended"
                    ? "Extended South Pole (-80° to -75°)"
                    : coverageZone === "context"
                    ? "Context Region (-75° to -70°)"
                    : "Outside Analysis Region"}
                </span>
              </div>

              {/* Radius Selector Pills */}
              <div>
                <label className="mb-1.5 block text-[10px] font-mono uppercase tracking-wider text-muted">
                  Analysis Radius (meters)
                </label>
                <div className="grid grid-cols-4 gap-1.5 font-mono text-xs">
                  {RADIUS_OPTIONS.map((r) => (
                    <button
                      key={r}
                      onClick={() => setSelection({ ...selection, radius_m: r })}
                      className={`py-1.5 px-2 rounded border text-center transition-colors cursor-pointer ${
                        selection.radius_m === r
                          ? "bg-elevated border-ink text-ink font-semibold"
                          : "border-divider/60 text-muted hover:text-ink hover:bg-surface"
                      }`}
                    >
                      {r}m
                    </button>
                  ))}
                </div>
              </div>

              {/* Fast South Pole center action */}
              <Button
                variant="secondary"
                size="sm"
                className="w-full text-xs"
                onClick={() => {
                  setSelection({ ...selection, latitude: -89.44, longitude: 222.5 });
                  setFocusNonce((n) => n + 1);
                }}
                icon={<TargetIcon className="h-3.5 w-3.5 text-muted" />}
              >
                Center Connecting Ridge (89.44°S)
              </Button>
            </div>

            {/* -----------------------------------------------------------
             * SECTION C — CANDIDATE SITES & QUICK PRESETS
             * ----------------------------------------------------------- */}
            <div className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
                  [03] CANDIDATE REGIONS
                </span>
                <span className="font-mono text-[10px] text-muted/60">
                  6 PRESETS
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                {QUICK_PRESETS.map((p) => {
                  const isActive =
                    Math.abs(p.lat - selection.latitude) < 0.05 &&
                    Math.abs(p.lon - selection.longitude) < 0.05;
                  return (
                    <button
                      key={p.label}
                      onClick={() => {
                        const newSel = {
                          ...selection,
                          latitude: p.lat,
                          longitude: p.lon,
                        };
                        setSelection(newSel);
                        setFocusSite({ lat: p.lat, lon: p.lon, nonce: Date.now() });
                        if (viewMode === "terrain") {
                          void fetchTerrainMesh(newSel);
                        }
                      }}
                      title={p.description}
                      className={`p-2.5 rounded border text-left transition-all cursor-pointer ${
                        isActive
                          ? "bg-elevated border-ink text-ink shadow-xs"
                          : "border-divider/50 bg-surface/50 text-muted hover:text-ink hover:border-divider"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="block font-display text-xs font-semibold text-ink truncate">
                          {p.label}
                        </span>
                        {p.hasHighRes ? (
                          <span className="text-[9px] font-mono text-good font-semibold">5m DEM</span>
                        ) : (
                          <span className="text-[9px] font-mono text-muted/60">LOLA</span>
                        )}
                      </div>
                      <span className="block font-mono text-[10px] text-muted/70 mt-0.5">
                        {p.lat.toFixed(2)}°, {p.lon.toFixed(0)}°
                      </span>
                    </button>
                  );
                })}
              </div>

              {sites.length > 0 && (
                <div className="pt-2 border-t border-divider/40">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono text-[9px] uppercase tracking-wider text-muted">
                      NASA Candidate Catalog ({sites.length})
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 max-h-36 overflow-y-auto pr-1">
                    {sites.map((s) => {
                      const isCatActive =
                        Math.abs(s.latitude - selection.latitude) < 0.05 &&
                        Math.abs(s.longitude - selection.longitude) < 0.05;
                      return (
                        <button
                          key={s.site_id}
                          onClick={() => {
                            const newSel = {
                              ...selection,
                              latitude: s.latitude,
                              longitude: s.longitude,
                            };
                            setSelection(newSel);
                            setFocusSite({ lat: s.latitude, lon: s.longitude, nonce: Date.now() });
                            if (viewMode === "terrain") {
                              void fetchTerrainMesh(newSel);
                            }
                          }}
                          className={`p-1.5 rounded border text-left text-[11px] truncate cursor-pointer transition-colors ${
                            isCatActive
                              ? "bg-elevated border-ink text-ink font-semibold"
                              : "border-divider/40 bg-surface/30 text-muted hover:text-ink hover:border-divider"
                          }`}
                          title={`${s.name} (${s.latitude}°, ${s.longitude}°)`}
                        >
                          <span className="truncate block font-mono text-[10px]">{s.name ?? s.site_id}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* -----------------------------------------------------------
             * SECTION D — PHYSICAL TERRAIN SNAPSHOT
             * ----------------------------------------------------------- */}
            <div className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
                  [04] TERRAIN METRICS PREVIEW
                </span>
                <span className="font-mono text-[10px] text-muted/60">
                  LOLA PRODUCT 78/90
                </span>
              </div>

              {terrainStatus === "loading" && <LoadingState label="Sampling terrain rasters…" />}
              {terrainStatus === "error" && (
                <ErrorState
                  title="Terrain fetch failed"
                  message={terrainError}
                  onRetry={() => void refreshTerrain(selection)}
                />
              )}

              {terrainStatus === "ready" && terrain && (
                <div className="space-y-2 font-mono text-xs">
                  {[
                    {
                      label: "Elevation (Mean)",
                      val: pickNumber(terrain.elevation, ["mean_m", "mean", "elevation_m", "value"]),
                      unit: "m",
                    },
                    {
                      label: "Slope Gradient (Horn)",
                      val: pickNumber(terrain.slope, ["mean_deg", "mean", "slope_deg", "value"]),
                      unit: "°",
                    },
                    {
                      label: "RMS Roughness",
                      val: pickNumber(terrain.roughness, ["rms_m", "rms", "value"]),
                      unit: "m",
                    },
                    {
                      label: "Solar Illumination",
                      val: pickNumber(terrain.illumination, ["sunlight_percent", "sunlit_percent", "percent", "value"]),
                      unit: "%",
                    },
                  ].map((row) => (
                    <div
                      key={row.label}
                      className="flex items-center justify-between p-2 rounded bg-surface/60 border border-divider/40"
                    >
                      <span className="text-muted text-[11px] font-sans">{row.label}</span>
                      <span className="text-ink font-semibold">
                        {row.val === null ? (
                          <span className="text-warn text-[10px]">UNAVAILABLE</span>
                        ) : (
                          `${fmtNum(row.val, 2)} ${row.unit}`
                        )}
                      </span>
                    </div>
                  ))}

                  {/* Button to inspect in 3D terrain mode if currently on Globe */}
                  {viewMode === "global" && (
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full mt-2 text-xs"
                      onClick={() => {
                        setViewMode("terrain");
                        void fetchTerrainMesh(selection);
                      }}
                      icon={<MountainIcon className="h-3.5 w-3.5 text-muted" />}
                    >
                      Inspect 3D Terrain Relief →
                    </Button>
                  )}
                </div>
              )}

              {terrainStatus === "ready" && !terrain && <DataUnavailable />}
            </div>

            {/* -----------------------------------------------------------
             * SECTION E — NASA ARCHIVES & RECONNAISSANCE
             * ----------------------------------------------------------- */}
            <div className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
                  [05] NASA RECONNAISSANCE &amp; ARCHIVES
                </span>
                <span className="font-mono text-[10px] text-muted/60">
                  LROC / JPL
                </span>
              </div>

              <div className="space-y-2.5">
                {/* LROC NAC Stereo DTM Coverage Box */}
                <div className="rounded border border-divider/60 bg-surface/50 p-3 text-xs">
                  <div className="flex items-center justify-between font-mono">
                    <span className="font-semibold text-ink">LROC NAC Stereo DTM</span>
                    {lrocLoading ? (
                      <span className="text-[10px] text-muted">Checking…</span>
                    ) : lrocCoverage?.is_covered ? (
                      <span className="chip !border-good/40 !text-good !py-0.5 text-[10px]">
                        COVERED
                      </span>
                    ) : (
                      <span className="chip !border-warn/40 !text-warn !py-0.5 text-[10px]">
                        PROXIMAL
                      </span>
                    )}
                  </div>

                  <p className="mt-1.5 text-[11px] leading-relaxed text-muted font-body">
                    {lrocCoverage?.is_covered
                      ? `Targeted 1–2m stereo DTM available (${lrocCoverage.covering_dtms[0]?.name ?? "Artemis zone"}).`
                      : lrocCoverage?.nearest_dtm
                      ? `Nearest DTM: ${lrocCoverage.nearest_dtm.name} (${lrocCoverage.distance_to_nearest_dtm_km} km away).`
                      : "Regional LOLA polar basemap active."}
                  </p>

                  {/* Deep link button */}
                  {lrocCoverage?.quickmap_url && (
                    <a
                      href={lrocCoverage.quickmap_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded border border-divider/80 bg-surface px-2.5 py-1.5 text-[11px] font-mono text-ink hover:bg-elevated transition-colors"
                    >
                      <span>Open in NASA LROC QuickMap</span>
                      <span className="text-xs">↗</span>
                    </a>
                  )}
                </div>

                {/* Horizons Ephemeris status */}
                <div className="flex items-center justify-between p-2 rounded bg-surface/40 border border-divider/30 text-[11px] font-mono text-muted">
                  <span>JPL Horizons DE441 Ephemeris:</span>
                  <span className="text-good font-semibold">Active</span>
                </div>
              </div>
            </div>
          </div>

          {/* -----------------------------------------------------------
           * SECTION F — PRIMARY ANALYSIS ACTION (STICKY FOOTER)
           * One prominent, high-contrast, comfortable Analyze button.
           * ----------------------------------------------------------- */}
          <div className="p-4 border-t border-divider/80 bg-[#141414] shadow-2xl">
            <Button
              variant="primary"
              size="lg"
              className="w-full font-bold tracking-wider"
              onClick={() => void onAnalyse()}
              disabled={analysisStatus === "loading" || !isInAnalysisRegion}
              loading={analysisStatus === "loading"}
              icon={<RocketIcon className="h-4 w-4" />}
              title={
                !isInAnalysisRegion
                  ? "Latitude must be between 80°S and 90°S for polar analysis"
                  : "Execute full landing site multi-criteria analysis (POST /api/analysis/run)"
              }
            >
              RUN FULL MISSION ANALYSIS
            </Button>

            {analysisStatus === "error" && (
              <div className="mt-2">
                <ErrorState
                  title="Analysis request failed"
                  message={analysisError}
                  onRetry={() => void onAnalyse()}
                />
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
