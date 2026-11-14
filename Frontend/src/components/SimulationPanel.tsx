import { useState } from "react";
import { useApp } from "@/context/AppContext";
import LoadingState from "./LoadingState";
import ErrorState from "./ErrorState";
import { fmtNum } from "@/utils/format";
import { AlertIcon, CheckIcon, RefreshIcon } from "./icons";

const MISSION_PRESETS = [
  {
    label: "Artemis III Summer Peak (Oct 2026)",
    epoch: "2026-10-15T00:00:00Z",
    days: 14,
    step: 2,
  },
  {
    label: "Mid-Summer High Illumination (Dec 2026)",
    epoch: "2026-12-21T00:00:00Z",
    days: 14,
    step: 2,
  },
  {
    label: "Southern Winter Minimum (Jun 2026)",
    epoch: "2026-06-21T00:00:00Z",
    days: 14,
    step: 2,
  },
];

export default function SimulationPanel() {
  const {
    missionConfig,
    setMissionConfig,
    simulation,
    simulationStatus,
    simulationError,
    runSimulation,
  } = useApp();

  const [epochInput, setEpochInput] = useState(missionConfig.startEpoch);
  const [durationInput, setDurationInput] = useState(missionConfig.durationDays);
  const [stepInput, setStepInput] = useState(missionConfig.stepHours);

  const handleApplyConfig = () => {
    setMissionConfig({
      startEpoch: epochInput,
      durationDays: durationInput,
      stepHours: stepInput,
    });
    void runSimulation({
      start_epoch_iso: epochInput,
      duration_days: durationInput,
      step_hours: stepInput,
    });
  };

  const handlePreset = (p: typeof MISSION_PRESETS[0]) => {
    setEpochInput(p.epoch);
    setDurationInput(p.days);
    setStepInput(p.step);
    setMissionConfig({
      startEpoch: p.epoch,
      durationDays: p.days,
      stepHours: p.step,
    });
    void runSimulation({
      start_epoch_iso: p.epoch,
      duration_days: p.days,
      step_hours: p.step,
    });
  };

  // Data series calculations for SVG rendering
  const timeSeries = simulation?.time_series || [];
  const totalPoints = timeSeries.length;

  const minElev = -15;
  const maxElev = 15;
  const elevRange = maxElev - minElev;

  const svgWidth = 800;
  const svgHeight = 220;
  const padLeft = 40;
  const padRight = 20;
  const padTop = 20;
  const padBottom = 30;
  const chartW = svgWidth - padLeft - padRight;
  const chartH = svgHeight - padTop - padBottom;

  const getX = (idx: number) => padLeft + (idx / Math.max(1, totalPoints - 1)) * chartW;
  const getY = (deg: number) => {
    const clamped = Math.max(minElev, Math.min(maxElev, deg));
    const normalized = (clamped - minElev) / elevRange;
    return padTop + (1 - normalized) * chartH;
  };

  // Generate SVG path for Sun elevation
  const sunPath =
    totalPoints > 1
      ? timeSeries.reduce((acc, pt, idx) => {
          const x = getX(idx);
          const y = getY(pt.solar_elevation_deg);
          return idx === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
        }, "")
      : "";

  // Generate SVG path for Earth elevation
  const earthPath =
    totalPoints > 1
      ? timeSeries.reduce((acc, pt, idx) => {
          const x = getX(idx);
          const y = getY(pt.earth_elevation_deg);
          return idx === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
        }, "")
      : "";

  // Check if conditions are permanently continuous (no transitions)
  const isContinuousSun =
    simulation &&
    simulation.sunlight_percentage > 99.0 &&
    simulation.max_continuous_sunlight_hours >= simulation.duration_days * 24;

  const isContinuousDark =
    simulation &&
    simulation.sunlight_percentage < 1.0 &&
    simulation.max_continuous_darkness_hours >= simulation.duration_days * 24;

  return (
    <div className="panel p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-divider pb-4">
        <div>
          <span className="kicker">Ephemeris &amp; Horizon Dynamics</span>
          <h3 className="font-display text-base font-semibold text-ink">
            Mission Sunlight &amp; Earth Visibility Simulation
          </h3>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip font-mono">POST /api/simulation/visibility</span>
          <button
            className="btn-ghost !px-3 !py-1.5 !text-xs"
            onClick={handleApplyConfig}
            disabled={simulationStatus === "loading"}
          >
            {simulationStatus === "loading" ? (
              <span className="spinner !h-3.5 !w-3.5" />
            ) : (
              <RefreshIcon className="h-3.5 w-3.5" />
            )}
            Run Simulation
          </button>
        </div>
      </div>

      {/* Preset selector bar */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider text-muted">Presets:</span>
        {MISSION_PRESETS.map((p) => (
          <button
            key={p.label}
            className={`chip cursor-pointer transition-all ${
              epochInput === p.epoch
                ? "!border-accent !text-cyan bg-accent/10"
                : "hover:!border-accent/40 hover:!text-cyan"
            }`}
            onClick={() => handlePreset(p)}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Mission parameters controls */}
      <div className="mt-4 grid grid-cols-1 gap-3 rounded-lg border border-divider/60 bg-elevated/30 p-3.5 sm:grid-cols-4">
        <div className="sm:col-span-2">
          <label className="text-[10px] uppercase tracking-wider text-muted block">
            Start Epoch (UTC ISO)
          </label>
          <input
            type="text"
            className="input mt-1 !py-1.5 !px-2.5 font-mono text-xs w-full"
            value={epochInput}
            onChange={(e) => setEpochInput(e.target.value)}
            placeholder="e.g. 2026-10-15T00:00:00Z"
          />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-muted block">
            Duration (Earth Days)
          </label>
          <input
            type="number"
            min="1"
            max="60"
            className="input mt-1 !py-1.5 !px-2.5 font-mono text-xs w-full"
            value={durationInput}
            onChange={(e) => setDurationInput(Number(e.target.value))}
          />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-muted block">
            Time Step (Hours)
          </label>
          <select
            className="input mt-1 !py-1.5 !px-2.5 font-mono text-xs w-full"
            value={stepInput}
            onChange={(e) => setStepInput(Number(e.target.value))}
          >
            <option value="1">1 hour (High Res)</option>
            <option value="2">2 hours (Standard)</option>
            <option value="4">4 hours (Overview)</option>
            <option value="6">6 hours (Fast)</option>
          </select>
        </div>
      </div>

      {/* Loading & Error States */}
      {simulationStatus === "loading" && (
        <div className="mt-6">
          <LoadingState label="Propagating Meeus/SPICE solar vectors and ray-tracing DEM horizon occultation…" />
        </div>
      )}

      {simulationStatus === "error" && (
        <div className="mt-6">
          <ErrorState
            title="Visibility simulation failed"
            message={simulationError}
            onRetry={handleApplyConfig}
          />
        </div>
      )}

      {/* Polar lighting edge condition notices */}
      {isContinuousSun && (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-good/40 bg-good/10 p-3 text-xs text-good">
          <CheckIcon className="h-4 w-4 shrink-0" />
          <span>
            <strong>Continuous Polar Daylight:</strong> Solar elevation remains above local topography for the entire {durationInput}-day mission window. No sunset transition occurs.
          </span>
        </div>
      )}

      {isContinuousDark && (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-warn/40 bg-warn/10 p-3 text-xs text-warn">
          <AlertIcon className="h-4 w-4 shrink-0" />
          <span>
            <strong>Permanent Shadow / Polar Night:</strong> The Sun never rises above the surrounding massif crater rims during this temporal window. Battery storage or auxiliary power is mandatory.
          </span>
        </div>
      )}

      {/* Simulation Key Telemetry Metrics */}
      {simulationStatus === "ready" && simulation && (
        <div className="mt-6 space-y-6">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <div className="rounded-lg border border-divider/60 bg-elevated/40 p-3 text-center">
              <span className="text-[10px] uppercase tracking-wider text-muted block">Sunlight</span>
              <p className="mt-1 font-mono text-xl font-semibold text-cyan">
                {fmtNum(simulation.sunlight_percentage, 1)}%
              </p>
              <span className="text-[10px] text-muted font-mono">{fmtNum(simulation.total_sunlight_hours, 0)} hrs</span>
            </div>
            <div className="rounded-lg border border-divider/60 bg-elevated/40 p-3 text-center">
              <span className="text-[10px] uppercase tracking-wider text-muted block">Earth Comm LOS</span>
              <p className="mt-1 font-mono text-xl font-semibold text-good">
                {fmtNum(simulation.earth_comm_percentage, 1)}%
              </p>
              <span className="text-[10px] text-muted font-mono">{fmtNum(simulation.total_earth_comm_hours, 0)} hrs</span>
            </div>
            <div className="rounded-lg border border-divider/60 bg-elevated/40 p-3 text-center">
              <span className="text-[10px] uppercase tracking-wider text-muted block">Max Day Window</span>
              <p className="mt-1 font-mono text-xl font-semibold text-ink">
                {fmtNum(simulation.max_continuous_sunlight_hours, 1)} h
              </p>
              <span className="text-[10px] text-muted font-mono">continuous sun</span>
            </div>
            <div className="rounded-lg border border-divider/60 bg-elevated/40 p-3 text-center">
              <span className="text-[10px] uppercase tracking-wider text-muted block">Max Night Window</span>
              <p className="mt-1 font-mono text-xl font-semibold text-warn">
                {fmtNum(simulation.max_continuous_darkness_hours, 1)} h
              </p>
              <span className="text-[10px] text-muted font-mono">battery drain</span>
            </div>
            <div className="rounded-lg border border-divider/60 bg-elevated/40 p-3 text-center">
              <span className="text-[10px] uppercase tracking-wider text-muted block">Max Comm Blackout</span>
              <p className="mt-1 font-mono text-xl font-semibold text-bad">
                {fmtNum(simulation.max_continuous_comm_blackout_hours, 1)} h
              </p>
              <span className="text-[10px] text-muted font-mono">no direct line</span>
            </div>
            <div className="rounded-lg border border-divider/60 bg-elevated/40 p-3 text-center">
              <span className="text-[10px] uppercase tracking-wider text-muted block">Combined Ops</span>
              <p className="mt-1 font-mono text-xl font-semibold text-accent">
                {simulation.combined_ops_percentage !== null && simulation.combined_ops_percentage !== undefined
                  ? `${fmtNum(simulation.combined_ops_percentage, 1)}%`
                  : "n/a"}
              </p>
              <span className="text-[10px] text-muted font-mono">sun + comm</span>
            </div>
          </div>

          {/* Time Series SVG Chart */}
          <div className="rounded-lg border border-divider/60 bg-space/60 p-4">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="font-semibold text-ink">
                Solar Elevation &amp; Earth Line-of-Sight Time Series
              </span>
              <div className="flex items-center gap-4 text-[11px] font-mono">
                <span className="flex items-center gap-1.5 text-cyan">
                  <span className="h-2 w-3 rounded-sm bg-cyan inline-block" /> Sun Elevation (deg)
                </span>
                <span className="flex items-center gap-1.5 text-good">
                  <span className="h-2 w-3 rounded-sm bg-good inline-block" /> Earth Elevation (deg)
                </span>
                <span className="flex items-center gap-1.5 text-muted">
                  <span className="h-px w-3 border-t border-dashed border-muted inline-block" /> 0° Horizon
                </span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full min-w-[650px]">
                {/* Background grid */}
                {[-10, -5, 0, 5, 10].map((deg) => (
                  <g key={deg}>
                    <line
                      x1={padLeft}
                      y1={getY(deg)}
                      x2={svgWidth - padRight}
                      y2={getY(deg)}
                      stroke={deg === 0 ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.07)"}
                      strokeDasharray={deg === 0 ? "none" : "3,3"}
                    />
                    <text
                      x={padLeft - 6}
                      y={getY(deg) + 3}
                      textAnchor="end"
                      fill="#91A4B8"
                      fontSize="9"
                      fontFamily="'IBM Plex Mono', monospace"
                    >
                      {deg}°
                    </text>
                  </g>
                ))}

                {/* Day / Night background stripes */}
                {timeSeries.map((pt, idx) => {
                  if (idx % 2 !== 0 || idx >= totalPoints - 1) return null;
                  const x = getX(idx);
                  const nextX = getX(Math.min(totalPoints - 1, idx + 2));
                  const isDay = pt.is_sunlit;
                  return (
                    <rect
                      key={idx}
                      x={x}
                      y={padTop}
                      width={Math.max(1, nextX - x)}
                      height={chartH}
                      fill={isDay ? "rgba(88,217,242,0.04)" : "rgba(10,15,30,0.15)"}
                    />
                  );
                })}

                {/* Earth Elevation Curve */}
                {earthPath && (
                  <path
                    d={earthPath}
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                )}

                {/* Sun Elevation Curve */}
                {sunPath && (
                  <path
                    d={sunPath}
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                )}

                {/* X-axis labels */}
                {[0, Math.floor(totalPoints * 0.25), Math.floor(totalPoints * 0.5), Math.floor(totalPoints * 0.75), totalPoints - 1].map((idx) => {
                  if (idx >= totalPoints) return null;
                  const pt = timeSeries[idx];
                  return (
                    <text
                      key={idx}
                      x={getX(idx)}
                      y={svgHeight - 8}
                      textAnchor="middle"
                      fill="#91A4B8"
                      fontSize="9"
                      fontFamily="'IBM Plex Mono', monospace"
                    >
                      +{fmtNum(pt.elapsed_hours, 0)}h ({fmtNum(pt.elapsed_hours / 24, 1)}d)
                    </text>
                  );
                })}
              </svg>
            </div>
            <p className="mt-2 text-right text-[10px] text-muted">
              Model: {simulation.scientific_methodology || "NASA JPL Ephemeris & LOLA 80m Radial Ray-Tracing"}
            </p>
          </div>
        </div>
      )}

      {simulationStatus === "idle" && (
        <div className="mt-5 rounded-lg border border-divider/60 bg-elevated/20 p-5 text-center text-xs text-muted">
          Click “Run Simulation” to propagate solar illumination, local horizon shading, and Earth communication visibility over the selected mission timeline.
        </div>
      )}
    </div>
  );
}
