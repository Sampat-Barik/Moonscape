import type { Selection } from "@/context/AppContext";
import { clamp, fmtCoord } from "@/utils/format";

const PRESETS: { label: string; lat: number; lon: number }[] = [
  { label: "South Pole", lat: -90, lon: 0 },
  { label: "Shackleton Rim", lat: -89.9, lon: 0 },
  { label: "Connecting Ridge", lat: -89.42, lon: 34 },
  { label: "Faustini Rim", lat: -87.2, lon: 80 },
  { label: "Malapert Massif", lat: -86.5, lon: 0 },
];

const RADII = [250, 500, 1000, 2000];

/**
 * CoordinateSelector — numeric lat/lon inputs, radius selector and quick
 * presets. Emits a validated Selection upward; it never calls the API itself.
 */
export default function CoordinateSelector({
  value,
  onChange,
  showPresets = true,
}: {
  value: Selection;
  onChange: (v: Selection) => void;
  showPresets?: boolean;
}) {
  const set = (patch: Partial<Selection>) => onChange({ ...value, ...patch });
  const parse = (raw: string, min: number, max: number): number | null => {
    const n = parseFloat(raw);
    if (!Number.isFinite(n)) return null;
    return clamp(n, min, max);
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="cs-lat" className="mb-1 block text-[11px] uppercase tracking-wider text-muted">
            Latitude (−90…90)
          </label>
          <input
            id="cs-lat"
            className="input"
            type="number"
            step="0.01"
            min={-90}
            max={90}
            value={value.latitude}
            onChange={(e) => {
              const n = parse(e.target.value, -90, 90);
              if (n !== null) set({ latitude: n });
            }}
          />
        </div>
        <div>
          <label htmlFor="cs-lon" className="mb-1 block text-[11px] uppercase tracking-wider text-muted">
            Longitude (−180…360)
          </label>
          <input
            id="cs-lon"
            className="input"
            type="number"
            step="0.01"
            min={-180}
            max={360}
            value={value.longitude}
            onChange={(e) => {
              const n = parse(e.target.value, -180, 360);
              if (n !== null) set({ longitude: n });
            }}
          />
        </div>
      </div>
      <div>
        <label htmlFor="cs-radius" className="mb-1 block text-[11px] uppercase tracking-wider text-muted">
          Analysis radius
        </label>
        <select
          id="cs-radius"
          className="input"
          value={value.radius_m}
          onChange={(e) => set({ radius_m: Number(e.target.value) })}
        >
          {RADII.map((r) => (
            <option key={r} value={r}>
              {r} m
            </option>
          ))}
        </select>
      </div>
      <p className="font-mono text-xs text-cyan">
        {fmtCoord(value.latitude, value.longitude)} · r = {value.radius_m} m
      </p>
      {showPresets && (
        <div className="flex flex-wrap gap-1.5">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              className="chip cursor-pointer transition-colors hover:border-accent/40 hover:text-cyan"
              onClick={() => set({ latitude: p.lat, longitude: p.lon })}
            >
              {p.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
