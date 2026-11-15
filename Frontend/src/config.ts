/**
 * Central environment configuration.
 *
 * The backend base URL is configured ONLY here, via Vite environment
 * variables (see `.env` / `.env.example`). Never hardcode backend URLs
 * anywhere else in the app — import from this file instead.
 *
 * Ports used by this project:
 *   - Frontend dev server (Vite): http://localhost:5173
 *   - Backend (FastAPI):          http://localhost:8000  (agreed contract)
 */

export const API_BASE_URL: string =
  ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "").replace(/\/+$/, "") ||
  "http://127.0.0.1:8000";

export type ApiMode = "auto" | "live" | "mock";

export const API_MODE: ApiMode =
  (import.meta.env.VITE_API_MODE as ApiMode | undefined) ?? "live";

export const REQUEST_TIMEOUT_MS: number = Number(
  (import.meta.env.VITE_API_TIMEOUT_MS as string | undefined) ?? 30000
);
