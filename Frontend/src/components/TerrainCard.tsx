import type { ReactNode } from "react";
import DataUnavailable from "./DataUnavailable";
import { fmtNum } from "@/utils/format";

export interface CardStat {
  label: string;
  value: number | null;
  unit?: string;
  digits?: number;
}

export interface CardExtra {
  label: string;
  text: string | null;
}

/**
 * TerrainCard — one scientific metric (elevation / slope / roughness /
 * illumination). A null value renders "Data unavailable" — never zero.
 */
export default function TerrainCard({
  title,
  icon,
  value,
  unit,
  digits = 2,
  stats = [],
  extras = [],
  available,
  source,
  note,
}: {
  title: string;
  icon: ReactNode;
  value: number | null;
  unit: string;
  digits?: number;
  stats?: CardStat[];
  extras?: CardExtra[];
  available: boolean;
  source?: string | null;
  note?: string | null;
}) {
  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded border border-divider/60 bg-surface/70 text-ink">
            {icon}
          </span>
          <h3 className="text-sm font-semibold tracking-wide text-ink font-display">{title}</h3>
        </div>
        <span
          className={`h-2 w-2 rounded-full ${available ? "bg-good" : "bg-warn"}`}
          title={available ? "Dataset available" : "Dataset unavailable"}
        />
      </div>

      <div className="mt-4">
        {value === null ? (
          <DataUnavailable className="!text-base" />
        ) : (
          <p className="font-mono text-3xl font-semibold text-white">
            {fmtNum(value, digits)}
            <span className="ml-1.5 text-base font-normal text-muted">{unit}</span>
          </p>
        )}
      </div>

      {stats.length > 0 && (
        <dl className="mt-4 space-y-1.5 border-t border-divider pt-3">
          {stats.map((s) => (
            <div key={s.label} className="flex items-center justify-between gap-2 text-[13px]">
              <dt className="shrink-0 text-muted">{s.label}</dt>
              <dd className="text-right font-mono text-slate-200">
                {s.value === null ? (
                  <span className="text-warn">Data unavailable</span>
                ) : (
                  `${fmtNum(s.value, s.digits ?? 2)}${s.unit ? ` ${s.unit}` : ""}`
                )}
              </dd>
            </div>
          ))}
        </dl>
      )}

      {extras.length > 0 && (
        <dl className="mt-2 space-y-1.5 border-t border-divider pt-3">
          {extras.map((x) => (
            <div key={x.label} className="flex items-center justify-between gap-2 text-[13px]">
              <dt className="shrink-0 text-muted">{x.label}</dt>
              <dd className="text-right font-mono text-slate-200">
                {x.text === null ? <span className="text-warn">Data unavailable</span> : x.text}
              </dd>
            </div>
          ))}
        </dl>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-divider pt-3 text-[11px]">
        <span className={available ? "text-good" : "text-warn"}>
          {available ? "● available" : "● Data unavailable"}
        </span>
        <span className="truncate text-muted">source: {source ?? "not reported"}</span>
      </div>
      {note && <p className="mt-2 text-[11px] italic leading-snug text-muted">{note}</p>}
    </div>
  );
}
