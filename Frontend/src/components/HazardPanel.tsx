import type { HazardDetection, HazardItem } from "@/types";
import type { Selection, Status } from "@/context/AppContext";
import LoadingState from "./LoadingState";
import ErrorState from "./ErrorState";
import DataUnavailable from "./DataUnavailable";
import { fmtCoord, fmtNum, pickString } from "@/utils/format";
import { AlertIcon, ShieldIcon } from "./icons";

function ConfidenceCell({ item }: { item: HazardItem }) {
  const confType = item.confidence_type;
  if (confType === "deterministic_gradient") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded bg-surface/80 px-2 py-0.5 font-mono text-[11px] text-slate-300 border border-divider">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
        Deterministic DEM
      </span>
    );
  }
  if (confType === "heuristic_indicator") {
    const val = typeof item.confidence === "number" ? item.confidence : null;
    const pct = val !== null ? Math.round(val * 100) : null;
    return (
      <span className="inline-flex items-center gap-1.5 rounded bg-surface/80 px-2 py-0.5 font-mono text-[11px] text-slate-300 border border-divider">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
        Heuristic Index{pct !== null ? `: ${pct}%` : ""}
      </span>
    );
  }

  const value = typeof item.confidence === "number" ? item.confidence : null;
  if (value === null || value === undefined) {
    return <span className="text-warn text-[11px]">uncalibrated</span>;
  }
  const pct = Math.max(0, Math.min(100, value * 100));
  return (
    <span className="flex items-center gap-2">
      <span className="h-1.5 w-16 overflow-hidden rounded bg-elevated">
        <span
          className="block h-full rounded bg-gradient-to-r from-[#737373] to-[#F1F1EF]"
          style={{ width: `${pct}%` }}
        />
      </span>
      <span className="font-mono text-[11px] text-slate-300">{fmtNum(pct, 0)}% (ML)</span>
    </span>
  );
}

function ItemTable({
  title,
  subtitle,
  items,
  columns,
  emptyMessage,
}: {
  title: string;
  subtitle?: string;
  items: HazardItem[] | null;
  columns: { label: string; render: (i: HazardItem) => string }[];
  emptyMessage: string;
}) {
  return (
    <div className="panel p-5">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold tracking-wide text-slate-200">{title}</h3>
        {subtitle && <span className="text-[11px] text-muted">{subtitle}</span>}
      </div>
      {items === null ? (
        <div className="mt-3">
          <DataUnavailable label="Optical detection unavailable for this location (no intersecting orbital imagery)" />
        </div>
      ) : items.length === 0 ? (
        <p className="mt-3 text-[13px] text-muted">{emptyMessage}</p>
      ) : (
        <div className="mt-3 max-h-64 overflow-auto rounded-lg border border-line/70">
          <table className="w-full min-w-[500px] text-left text-[12px]">
            <thead className="sticky top-0 bg-elevated text-muted">
              <tr>
                <th className="px-3 py-2 font-medium">ID</th>
                {columns.map((c) => (
                  <th key={c.label} className="px-3 py-2 font-medium">
                    {c.label}
                  </th>
                ))}
                <th className="px-3 py-2 font-medium">Method / Confidence</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, idx) => (
                <tr key={it.id ?? idx} className="border-t border-divider hover:bg-white/5">
                  <td className="px-3 py-2 font-mono text-ink font-semibold">{it.id ?? `#${idx + 1}`}</td>
                  {columns.map((c) => (
                    <td key={c.label} className="px-3 py-2 font-mono text-slate-200">
                      {c.render(it)}
                    </td>
                  ))}
                  <td className="px-3 py-2">
                    <ConfidenceCell item={it} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function HazardPanel({
  hazards,
  status,
  error,
  onRetry,
  selection,
}: {
  hazards: HazardDetection | null;
  status: Status;
  error: string | null;
  onRetry?: () => void;
  selection: Selection;
}) {
  if (status === "loading") {
    return (
      <div className="panel p-6">
        <LoadingState label="Running hazard detection pipeline (POST /api/hazards/predict)…" />
      </div>
    );
  }
  if (status === "error") {
    return <ErrorState title="Hazard detection failed" message={error} onRetry={onRetry} />;
  }
  if (!hazards) {
    return (
      <div className="panel p-6 text-sm text-muted">
        No hazard detection has been run yet for {fmtCoord(selection.latitude, selection.longitude)}.
      </div>
    );
  }

  const overlay = pickString(hazards, ["overlay_image", "image_url", "overlay", "image"]);
  const craters = Array.isArray(hazards.craters) ? hazards.craters : null;
  const rocks = Array.isArray(hazards.rocks) ? hazards.rocks : null;
  const topoHazards = Array.isArray(hazards.topographic_hazards) ? hazards.topographic_hazards : [];
  const model = pickString(hazards, ["model", "model_name"]) ?? "YOLOv8n-Detection & DEM Morphological Engine";
  const limitations = Array.isArray(hazards.limitations) ? (hazards.limitations as string[]) : [];
  const warnings = Array.isArray(hazards.warnings) ? (hazards.warnings as string[]) : [];
  const summary = hazards.summary;
  const opticalStatus = hazards.optical_status ?? (overlay ? "success" : "not_available");
  const productId = pickString(hazards, ["source_product_id"]) ?? "N/A";
  const resolutionM = hazards.source_resolution_m ?? null;
  const coverageZone = hazards.coverage_zone ?? "core";

  return (
    <div className="space-y-6">

      {/* ===== SECTION HEADER METRICS ===== */}
      <div className="grid gap-4 sm:grid-cols-4">
        {/* Optical Craters */}
        <div className="panel p-5 text-center">
          <p className="font-mono text-3xl font-semibold text-ink">
            {craters === null ? (
              <span className="text-base font-normal text-warn">n/a</span>
            ) : (
              craters.length
            )}
          </p>
          <p className="mt-1.5 kicker text-[10px]">
            {craters === null ? "optical scan n/a" : "craters detected (optical)"}
          </p>
        </div>

        {/* Optical Boulders */}
        <div className="panel p-5 text-center">
          <p className="font-mono text-3xl font-semibold text-ink">
            {rocks === null ? (
              <span className="text-base font-normal text-warn">n/a</span>
            ) : (
              rocks.length
            )}
          </p>
          <p className="mt-1.5 kicker text-[10px]">
            {rocks === null ? "optical scan n/a" : "boulders detected (optical)"}
          </p>
        </div>

        {/* Steep Escarpments */}
        <div className="panel p-5 text-center">
          <p className="font-mono text-3xl font-semibold text-ink">
            {summary && typeof summary.steep_slope_cells === "number" ? (
              summary.steep_slope_cells
            ) : (
              topoHazards.filter((h) => h.type === "escarpment").length
            )}
          </p>
          <p className="mt-1.5 kicker text-[10px]">steep slope cells (&gt;15°)</p>
        </div>

        {/* Overall Rating */}
        <div className="panel p-5 text-center">
          <p className="truncate font-mono text-lg font-semibold uppercase text-ink">
            {summary?.overall_hazard_level ? String(summary.overall_hazard_level) : "Low Risk"}
          </p>
          <p className="mt-1.5 kicker text-[10px]">overall hazard level</p>
        </div>
      </div>

      {/* Warnings & Operational Notices */}
      {warnings.length > 0 && (
        <div className="rounded-lg border border-amber-900/40 bg-amber-950/20 p-4">
          <div className="flex items-start gap-2.5">
            <AlertIcon className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
            <div className="space-y-1">
              <p className="text-xs font-semibold text-amber-200">Operational Notices &amp; Data Provenance</p>
              {warnings.map((w, idx) => (
                <p key={idx} className="text-xs text-amber-300/80 leading-relaxed">
                  {w}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ===== SECTION B: OPTICAL DETECTION OVERLAY ===== */}
      <div className="panel p-5">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-divider pb-3">
          <h3 className="flex items-center gap-2 text-sm font-semibold tracking-wide text-ink">
            <ShieldIcon className="h-4 w-4 text-ink" /> Section B · Optical Detection Overlay (LROC NAC / ML)
          </h3>
          <div className="flex items-center gap-2">
            <span className="chip text-[11px] font-mono">
              Status: {opticalStatus === "success" ? "ONLINE (Image processed)" : "OFFLINE (No imagery)"}
            </span>
            {productId !== "N/A" && (
              <span className="chip text-[11px] font-mono">Product: {productId}</span>
            )}
            {resolutionM && (
              <span className="chip text-[11px] font-mono">{resolutionM} m/px</span>
            )}
          </div>
        </div>

        {overlay ? (
          <div className="mt-4">
            <div className="relative overflow-hidden rounded-lg border border-divider bg-black">
              <img
                src={overlay}
                alt={`LROC NAC hazard detection overlay for ${productId}`}
                className="max-h-[480px] w-full object-contain"
              />
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted">
              <p>
                Authentic NASA LROC NAC polar orbital frame with YOLOv8n crater (cyan) and boulder (amber) annotations.
              </p>
              <p className="font-mono">
                Centroid: {fmtCoord(selection.latitude, selection.longitude)}
              </p>
            </div>
          </div>
        ) : (
          <div className="mt-4 flex flex-col items-center justify-center rounded-lg border border-dashed border-divider bg-surface/50 px-6 py-12 text-center">
            <ShieldIcon className="h-8 w-8 text-muted mb-3 opacity-60" />
            <h4 className="text-sm font-medium text-slate-300">
              Detection imagery unavailable — no georeferenced optical analysis was performed.
            </h4>
            <p className="mt-2 max-w-lg text-xs leading-relaxed text-muted">
              High-resolution LROC NAC optical images (0.5–2.0 m/pixel) are targeted and non-global.
              No calibrated nadir orbital frame is registered on disk for this exact coordinate.
              Morphological terrain hazards below are derived from digital elevation models (DEM).
            </p>
          </div>
        )}
      </div>

      {/* ===== SECTION A: DETECTED OPTICAL & TOPOGRAPHIC ITEMS ===== */}
      <div className="grid gap-5 lg:grid-cols-2">
        <ItemTable
          title="Detected Craters (Optical)"
          subtitle="YOLOv8n on high-resolution LROC NAC orbital frames"
          items={craters}
          emptyMessage="Optical scan completed: zero craters satisfying detection confidence threshold."
          columns={[
            { label: "Lat", render: (i) => (typeof i.latitude === "number" ? fmtNum(i.latitude, 4) : "n/a") },
            { label: "Lon", render: (i) => (typeof i.longitude === "number" ? fmtNum(i.longitude, 4) : "n/a") },
            {
              label: "Diameter (m)",
              render: (i) => {
                const d = typeof i.diameter_m === "number" ? i.diameter_m : typeof i.radius_m === "number" ? i.radius_m * 2 : null;
                return d === null ? "n/a" : fmtNum(d, 1);
              },
            },
            { label: "Severity", render: (i) => (typeof i.severity === "string" ? i.severity : "medium") },
          ]}
        />

        <ItemTable
          title="Detected Boulders (Optical)"
          subtitle="Shadow length & reflectance bounding boxes"
          items={rocks}
          emptyMessage="Optical scan completed: zero boulders satisfying detection confidence threshold."
          columns={[
            { label: "Lat", render: (i) => (typeof i.latitude === "number" ? fmtNum(i.latitude, 4) : "n/a") },
            { label: "Lon", render: (i) => (typeof i.longitude === "number" ? fmtNum(i.longitude, 4) : "n/a") },
            {
              label: "Est. Size (m)",
              render: (i) => {
                const s = typeof i.size_m === "number" ? i.size_m : typeof i.diameter_m === "number" ? i.diameter_m : null;
                return s === null ? "n/a" : fmtNum(s, 2);
              },
            },
            { label: "Severity", render: (i) => (typeof i.severity === "string" ? i.severity : "medium") },
          ]}
        />
      </div>

      {/* Topographic Hazards Table (DEM-derived) */}
      {topoHazards.length > 0 && (
        <ItemTable
          title="DEM Morphological Terrain Hazards"
          subtitle="Horn gradient slope escarpments, RMS roughness anomalies, curvature depressions"
          items={topoHazards}
          emptyMessage="No steep escarpments or extreme roughness anomalies in evaluated radius."
          columns={[
            { label: "Type", render: (i) => (i.type ? String(i.type).replace(/_/g, " ") : "hazard") },
            { label: "Lat", render: (i) => (typeof i.latitude === "number" ? fmtNum(i.latitude, 4) : "n/a") },
            { label: "Lon", render: (i) => (typeof i.longitude === "number" ? fmtNum(i.longitude, 4) : "n/a") },
            {
              label: "Parameter & Unit",
              render: (i) => {
                if (typeof i.measurement_value === "number") {
                  const unit = i.measurement_unit === "deg" ? "°" : ` ${i.measurement_unit ?? "m"}`;
                  const name = i.measurement_name ? ` (${i.measurement_name})` : "";
                  return `${fmtNum(i.measurement_value, 1)}${unit}${name}`;
                }
                if (typeof i.size_m === "number" && i.size_m > 0) {
                  return `${fmtNum(i.size_m, 1)} m`;
                }
                return "n/a";
              },
            },
            {
              label: "Footprint",
              render: (i) => (typeof i.feature_extent_m === "number" ? `${fmtNum(i.feature_extent_m, 0)} m span` : (i.cell_count ? `${i.cell_count} cells` : "—")),
            },
            { label: "Severity", render: (i) => (typeof i.severity === "string" ? i.severity : "medium") },
          ]}
        />
      )}

      {/* ===== SECTION C: DATA COVERAGE & PROVENANCE ===== */}
      <div className="panel p-5">
        <h3 className="text-sm font-semibold tracking-wide text-ink border-b border-divider pb-3">
          Section C · Dataset Coverage &amp; Provenance
        </h3>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs">
          <div className="rounded border border-divider bg-surface/40 p-3">
            <span className="text-muted block text-[11px]">Exploration Coverage Zone</span>
            <span className="font-semibold text-ink capitalize mt-0.5 block">{coverageZone} South Pole</span>
            <span className="text-[11px] text-muted mt-1 block">
              {coverageZone === "core" ? "Core corridor (-90° to -80°)" : coverageZone === "extended" ? "Extended (-80° to -75°)" : "Context (-75° to -70°)"}
            </span>
          </div>
          <div className="rounded border border-divider bg-surface/40 p-3">
            <span className="text-muted block text-[11px]">Optical Observation Frame</span>
            <span className="font-mono text-ink mt-0.5 block truncate" title={productId}>{productId !== "N/A" ? productId : "No intersecting frame"}</span>
            <span className="text-[11px] text-muted mt-1 block">
              {resolutionM ? `${resolutionM} m/pixel spatial resolution` : "Optical resolution uncalibrated"}
            </span>
          </div>
          <div className="rounded border border-divider bg-surface/40 p-3">
            <span className="text-muted block text-[11px]">Altimetry Topographic Model</span>
            <span className="font-mono text-ink mt-0.5 block">LOLA DEM (ESRI:104903)</span>
            <span className="text-[11px] text-muted mt-1 block">
              Horn 8-neighbor gradient &amp; RMS roughness
            </span>
          </div>
          <div className="rounded border border-divider bg-surface/40 p-3">
            <span className="text-muted block text-[11px]">Detection Engine</span>
            <span className="font-mono text-ink mt-0.5 block truncate" title={model}>
              {opticalStatus === "success" ? "YOLOv8n Polar Neural Detector" : "DEM Morphological Engine"}
            </span>
            <span className="text-[11px] text-muted mt-1 block">
              {opticalStatus === "success" ? "PyTorch/ONNX Online · Optical Frame Processed" : "Optical Offline · DEM Morphology Active"}
            </span>
          </div>
        </div>
      </div>

      {/* ===== SECTION D: SCIENTIFIC LIMITATIONS & OPERATIONAL CAVEATS ===== */}
      <div className="panel panel-warn p-5">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-warn">
          <AlertIcon className="h-4 w-4" /> Section D · Scientific Limitations &amp; Operational Caveats
        </h3>
        {limitations.length > 0 ? (
          <ul className="mt-3 list-disc space-y-2 pl-5 text-[13px] leading-relaxed text-muted">
            {limitations.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-[13px] text-muted">
            Optical hazard detection models trained on Apollo equatorial photography are invalidated at the South Pole
            due to grazing solar incidence (&lt;1.5°), severe elongated shadows, and permanently shadowed regions (PSRs).
          </p>
        )}
        <div className="mt-4 border-t border-divider/60 pt-3 text-[11px] italic text-muted">
          DISCLAIMER: Suitability evaluations and hazard predictions provided by Moonscape are preliminary engineering
          research models derived from orbital remote sensing measurements (NASA LRO LOLA/LROC). These outputs do NOT
          constitute certified landing safety clearance for lunar flight missions.
        </div>
      </div>

    </div>
  );
}
