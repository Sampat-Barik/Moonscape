/**
 * Small, dependency-free formatting / field-access helpers.
 *
 * The backend contract does not fix exact field names for nested metric
 * blocks, so `pickNumber` / `pickString` look through a list of candidate
 * keys and only ever return values that are actually present in the API
 * response. Nothing is invented here.
 */

export function asNumber(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export function asString(v: unknown): string | null {
  return typeof v === "string" && v.trim().length > 0 ? v : null;
}

export function asBool(v: unknown): boolean | null {
  return typeof v === "boolean" ? v : null;
}

/** First finite number found under any of the candidate keys. */
export function pickNumber(obj: unknown, keys: string[]): number | null {
  if (!obj || typeof obj !== "object") return null;
  const rec = obj as Record<string, unknown>;
  for (const k of keys) {
    const n = asNumber(rec[k]);
    if (n !== null) return n;
  }
  return null;
}

/** First non-empty string found under any of the candidate keys. */
export function pickString(obj: unknown, keys: string[]): string | null {
  if (!obj || typeof obj !== "object") return null;
  const rec = obj as Record<string, unknown>;
  for (const k of keys) {
    const s = asString(rec[k]);
    if (s !== null) return s;
  }
  return null;
}

export function pickBool(obj: unknown, keys: string[]): boolean | null {
  if (!obj || typeof obj !== "object") return null;
  const rec = obj as Record<string, unknown>;
  for (const k of keys) {
    const b = asBool(rec[k]);
    if (b !== null) return b;
  }
  return null;
}

/** Format a number for display (no trailing zeroes). */
export function fmtNum(v: number, digits = 2): string {
  return v.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

/** Format lat/lon as e.g. "89.500° S, 000.000° E". */
export function fmtCoord(lat: number, lon: number): string {
  const la = `${Math.abs(lat).toFixed(3)}°${lat >= 0 ? "N" : "S"}`;
  const lo = `${Math.abs(lon).toFixed(3)}°${lon >= 0 ? "E" : "W"}`;
  return `${la}, ${lo}`;
}

/** Format a signed number with unit, e.g. "-5234.2 m". */
export function fmtSigned(v: number, digits = 1, unit = ""): string {
  const s = v.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return unit ? `${s} ${unit}` : s;
}

export function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}
