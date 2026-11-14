import type { HazardDetection, HazardItem } from "@/types";
import type { Selection, Status } from "@/context/AppContext";
import LoadingState from "./LoadingState";
import ErrorState from "./ErrorState";
import DataUnavailable from "./DataUnavailable";
import { fmtCoord, fmtNum, pickString } from "@/utils/format";
import { AlertIcon, ShieldIcon } from "./icons";

function ConfidenceBar({ value }: { value: number | null }) {
  if (value === null || value === undefined) {
    return <span className="text-warn">Data unavailable</span>;
  }
  const pct = Math.max(0, Math.min(100, value * 100));
  return (
    <span className="flex items-center gap-2">
      <span className="h-1.5 w-20 overflow-hidden rounded bg-elevated">
        <span
          className="block h-full rounded bg-gradient-to-r from-accent to-cyan"
          style={{ width: `${pct}%` }}
        />
      </span>
      <span className="font-mono text-[11px] text-slate-300">{fmtNum(pct, 0)}%</span>
    </span>
  );
}

function ItemTable({
  title,
  items,
  columns,
}: {
  title: string;
  items: HazardItem[] | null;
  columns: { label: string; render: (i: HazardItem) => string }[];
}) {
  return (
    <div className="panel p-5">
      <h3 className="text-sm font-semibold tracking-wide text-slate-200">{title}</h3>
      {items === null ? (
        <div className="mt-3">
          <DataUnavailable label="Detection list unavailable from backend" />
        </div>
      ) : items.length === 0 ? (
        <p className="mt-3 text-[13px] text-muted">No items detected in this region.</p>
      ) : (
        <div className="mt-3 max-h-64 overflow-auto rounded-lg border border-line/70">
          <table className="w-full min-w-[520px] text-left text-[12px]">
            <thead className="sticky top-0 bg-elevated text-muted">
              <tr>
                <th className="px-3 py-2 font-medium">ID</th>
                {columns.map((c) => (
                  <th key={c.label} className="px-3 py-2 font-medium">
                    {c.label}
                  </th>
                ))}
                <th className="px-3 py-2 font-medium">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, idx) => (
                <tr key={it.id ?? idx} className="border-t border-divider hover:bg-white/5">
                  <td className="px-3 py-2 font-mono text-cyan">{it.id ?? `#${idx + 1}`}</td>
                  {columns.map((c) => (
                    <td key={c.label} className="px-3 py-2 font-mono text-slate-200">
                      {c.render(it)}
                    </td>
                  ))}
                  <td className="px-3 py-2">
                    <ConfidenceBar value={typeof it.confidence === "number" ? it.confidence : null} />
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

/**
 * HazardPanel — results of POST /api/hazards/predict: detected craters and
 * rocks with confidence values, an overlay image when the backend provides
 * one, the model name and its stated limitations.
 */
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
        <LoadingState label="Running hazard detection (POST /api/hazards/predict)…" />
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
  const model = pickString(hazards, ["model", "model_name"]);
  const limitations = Array.isArray(hazards.limitations) ? (hazards.limitations as string[]) : [];
  const summary = hazards.summary;

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="panel p-5 text-center">
          <p className="font-mono text-3xl font-semibold text-ink">
            {craters === null ? <span className="text-base text-warn">n/a</span> : craters.length}
          </p>
          <p className="mt-1.5 kicker text-[10px]">craters detected</p>
        </div>
        <div className="panel p-5 text-center">
          <p className="font-mono text-3xl font-semibold text-ink">
            {rocks === null ? <span className="text-base text-warn">n/a</span> : rocks.length}
          </p>
          <p className="mt-1.5 kicker text-[10px]">rocks detected</p>
        </div>
        <div className="panel p-5 text-center">
          <p className="truncate font-mono text-sm text-cyan">{model ?? "model not reported"}</p>
          <p className="mt-1.5 kicker text-[10px]">detection model</p>
        </div>
      </div>

      {summary && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(summary).map(([k, v]) => (
            <span key={k} className="chip">
              <span className="text-muted">{k.replace(/_/g, " ")}:</span>
              <span className="font-mono text-slate-200">
                {typeof v === "number" ? fmtNum(v, 2) : String(v)}
              </span>
            </span>
          ))}
        </div>
      )}

      <div className="panel p-5">
        <h3 className="flex items-center gap-2 text-sm font-semibold tracking-wide text-slate-200">
          <ShieldIcon className="h-4 w-4 text-accentsoft" /> Detection overlay
        </h3>
        {overlay ? (
          <div className="mt-3">
            <img
              src={overlay}
              alt="Hazard detection overlay for the selected site"
              className="max-h-80 w-full rounded-lg border border-divider object-cover"
            />
            <p className="mt-2 text-[11px] text-muted">
              Overlay image returned by the backend for {fmtCoord(selection.latitude, selection.longitude)}.
            </p>
          </div>
        ) : (
          <div className="mt-3">
            <img
              src="/images/surface-closeup.jpg"
              alt="Illustrative lunar surface (not an analysis result)"
              className="max-h-56 w-full rounded-lg border border-divider object-cover opacity-50"
            />
            <p className="mt-2 flex items-start gap-1.5 text-[11px] text-warn">
              <AlertIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              No overlay image was returned by the backend for this run — the picture above is
              illustrative only and is not an analysis result.
            </p>
          </div>
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ItemTable
          title="Detected craters"
          items={craters}
          columns={[
            { label: "Lat", render: (i) => (typeof i.latitude === "number" ? fmtNum(i.latitude, 3) : "n/a") },
            { label: "Lon", render: (i) => (typeof i.longitude === "number" ? fmtNum(i.longitude, 3) : "n/a") },
            {
              label: "Diameter (m)",
              render: (i) => {
                const d = typeof i.diameter_m === "number" ? i.diameter_m : typeof i.radius_m === "number" ? i.radius_m * 2 : null;
                return d === null ? "n/a" : fmtNum(d, 1);
              },
            },
            { label: "Depth (m)", render: (i) => (typeof i.depth_m === "number" ? fmtNum(i.depth_m, 1) : "n/a") },
          ]}
        />
        <ItemTable
          title="Detected rocks / boulders"
          items={rocks}
          columns={[
            { label: "Lat", render: (i) => (typeof i.latitude === "number" ? fmtNum(i.latitude, 3) : "n/a") },
            { label: "Lon", render: (i) => (typeof i.longitude === "number" ? fmtNum(i.longitude, 3) : "n/a") },
            {
              label: "Size (m)",
              render: (i) => {
                const s = typeof i.size_m === "number" ? i.size_m : typeof i.diameter_m === "number" ? i.diameter_m : null;
                return s === null ? "n/a" : fmtNum(s, 2);
              },
            },
          ]}
        />
      </div>

      <div className="panel panel-warn p-5">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-warn">
          <AlertIcon className="h-4 w-4" /> Model limitations
        </h3>
        {limitations.length > 0 ? (
          <ul className="mt-3 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-muted">
            {limitations.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-[13px] text-muted">
            The backend did not report model limitations for this run. Treat all detections as
            preliminary.
          </p>
        )}
        <p className="mt-3 text-[11px] italic text-muted">
          Confidence values describe the detector, not the probability of impact or damage.
          Detections are preliminary decision support, not a safety certification.
        </p>
      </div>
    </div>
  );
}
