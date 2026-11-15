import DataUnavailable from "./DataUnavailable";
import LoadingState from "./LoadingState";
import { AlertIcon } from "./icons";

/**
 * SuitabilityScore — preliminary score gauge (POST /api/score).
 * A null score renders "Data unavailable" and is NEVER treated as zero.
 * Always carries the disclaimer that this is not a landing-safety certification.
 */
export default function SuitabilityScore({
  score,
  max = 100,
  grade,
  label,
  breakdown,
  disclaimer,
  loading = false,
  error,
  onRetry,
}: {
  score: number | null;
  max?: number;
  grade?: string | null;
  label?: string | null;
  breakdown?: Record<string, number | null> | null;
  disclaimer?: string | null;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}) {
  if (loading) {
    return (
      <div className="panel p-6">
        <LoadingState label="Requesting preliminary score (POST /api/score)…" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="panel panel-bad p-6">
        <p className="text-sm font-semibold text-bad">Score request failed</p>
        <p className="mt-1 text-[13px] text-muted">{error}</p>
        {onRetry && (
          <button className="btn-ghost mt-3 !px-3 !py-1.5 !text-xs" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    );
  }

  const frac = score === null ? null : Math.max(0, Math.min(1, score / max));
  const arcLen = Math.PI * 80;

  return (
    <div className="panel p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-sm font-semibold tracking-wide text-ink font-display">
          <span className="flex h-8 w-8 items-center justify-center rounded border border-divider/60 bg-surface/70 text-ink">
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" />
            </svg>
          </span>
          Preliminary suitability score
        </h3>
        <span className="chip !border-warn/40 !text-warn">decision support only</span>
      </div>

      <div className="mt-3 flex flex-col items-center gap-6 sm:flex-row">
        <svg viewBox="0 0 200 118" className="w-56 shrink-0">
          <defs>
            <linearGradient id="scoreGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#777777" />
              <stop offset="100%" stopColor="#FFFFFF" />
            </linearGradient>
          </defs>
          <path d="M 20 110 A 80 80 0 0 1 180 110" fill="none" stroke="#262626" strokeWidth="12" strokeLinecap="round" />
          {frac !== null && (
            <path
              d="M 20 110 A 80 80 0 0 1 180 110"
              fill="none"
              stroke="url(#scoreGrad)"
              strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={`${arcLen * frac} ${arcLen}`}
            />
          )}
          <text x="100" y="94" textAnchor="middle" fill="#ffffff" fontSize="30" fontWeight="700" fontFamily="'IBM Plex Mono', monospace">
            {score === null ? "—" : Math.round(score)}
          </text>
          <text x="100" y="111" textAnchor="middle" fill="#91A4B8" fontSize="10" fontFamily="'IBM Plex Mono', monospace">
            {score === null ? "data unavailable" : `of ${max}`}
          </text>
        </svg>

        <div className="min-w-0 flex-1">
          {score === null ? (
            <DataUnavailable label="Score unavailable — a missing score is never treated as zero." />
          ) : (
            <div>
              <p className="font-display text-xl font-semibold text-white">
                {grade ? `Grade ${grade}` : "Preliminary score"}
              </p>
              {label && <p className="mt-0.5 text-sm text-muted">{label}</p>}
            </div>
          )}
          {breakdown && Object.keys(breakdown).length > 0 && (
            <div className="mt-4 space-y-2">
              {Object.entries(breakdown).map(([k, v]) => (
                <div key={k}>
                  <div className="flex justify-between text-[11px]">
                    <span className="capitalize text-muted">{k.replace(/_/g, " ")}</span>
                    <span className="font-mono text-slate-300">
                      {v === null || v === undefined ? "n/a" : Math.round(v)}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded bg-line/70">
                    <div
                      className="h-full rounded bg-gradient-to-r from-accent to-cyan"
                      style={{
                        width: `${v !== null && v !== undefined ? Math.max(0, Math.min(100, v)) : 0}%`,
                        opacity: v === null || v === undefined ? 0.25 : 1,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <p className="mt-4 flex items-start gap-2 border-t border-divider pt-3 text-[11px] leading-relaxed text-muted">
        <AlertIcon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warn" />
        {disclaimer ??
          "This is a preliminary decision-support score produced by the backend. It is not a certification or guarantee of landing safety."}
      </p>
    </div>
  );
}
