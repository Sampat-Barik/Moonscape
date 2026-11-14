import type { ExplanationResponse } from "@/types";
import type { Status } from "@/context/AppContext";
import LoadingState from "./LoadingState";
import ErrorState from "./ErrorState";
import { AlertIcon, CheckIcon, InfoIcon, SparkIcon, XIcon } from "./icons";

function FactorList({
  title,
  subtitle,
  items,
  icon,
  badgeClass,
  badgeText,
}: {
  title: string;
  subtitle: string;
  items: string[] | undefined;
  icon: React.ReactNode;
  badgeClass: string;
  badgeText: string;
}) {
  return (
    <div className="panel flex flex-col justify-between p-5">
      <div>
        <div className="flex items-center justify-between">
          <h4 className="flex items-center gap-2 font-display text-sm font-semibold text-ink">
            {icon}
            {title}
          </h4>
          <span className={`chip text-[10px] ${badgeClass}`}>{badgeText}</span>
        </div>
        <p className="mt-1 text-[11px] text-muted">{subtitle}</p>
        {items && items.length > 0 ? (
          <ul className="mt-3.5 space-y-2">
            {items.map((t, i) => (
              <li
                key={i}
                className="flex items-start gap-2.5 text-xs leading-relaxed text-slate-200"
              >
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan/70" />
                <span>{t}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-xs italic text-muted">No factors reported in this category.</p>
        )}
      </div>
    </div>
  );
}

export default function AIExplanation({
  explanation,
  status,
  error,
  onRetry,
}: {
  explanation: ExplanationResponse | null;
  status: Status;
  error: string | null;
  onRetry?: () => void;
}) {
  if (status === "loading") {
    return (
      <div className="panel p-8 text-center">
        <LoadingState label="Synthesizing mission feasibility narrative (POST /api/ai/explain)…" />
      </div>
    );
  }
  if (status === "error") {
    return (
      <ErrorState
        title="AI explanation request failed"
        message={error}
        onRetry={onRetry}
      />
    );
  }
  if (!explanation) return null;

  const text = explanation.explanation ?? explanation.summary;

  return (
    <div className="space-y-6">
      {/* Narrative Section */}
      <div className="panel p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-divider pb-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded bg-accent/10 text-cyan">
              <SparkIcon className="h-4 w-4" />
            </span>
            <div>
              <span className="kicker">Synthesis</span>
              <h3 className="font-display text-base font-semibold text-ink">
                Automated Mission Feasibility Analysis
              </h3>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {explanation.model && (
              <span className="chip font-mono">model: {explanation.model}</span>
            )}
            {explanation.analysis_id && (
              <span className="chip font-mono">analysis: {explanation.analysis_id}</span>
            )}
            {explanation.generated_at && (
              <span className="chip font-mono">
                {String(explanation.generated_at)}
              </span>
            )}
          </div>
        </div>

        {text ? (
          <div className="mt-5 rounded-lg border border-divider/60 bg-space/50 p-5">
            <p className="font-body text-sm leading-relaxed text-slate-200 whitespace-pre-wrap">
              {text}
            </p>
          </div>
        ) : (
          <p className="mt-4 text-sm text-warn">
            Data unavailable — the backend returned no narrative summary.
          </p>
        )}

        {/* 4 Factor Categories */}
        <div className="mt-6">
          <span className="kicker mb-3 block">Categorical Assessment</span>
          <div className="grid gap-4 md:grid-cols-2">
            <FactorList
              title="Positive Factors"
              subtitle="Mission advantages & favorable environmental conditions"
              items={explanation.positive_factors}
              icon={<CheckIcon className="h-4 w-4 text-good" />}
              badgeClass="!border-good/30 !text-good"
              badgeText="Advantages"
            />
            <FactorList
              title="Risk Factors"
              subtitle="Terrain hazards & operational constraints"
              items={explanation.risk_factors}
              icon={<AlertIcon className="h-4 w-4 text-warn" />}
              badgeClass="!border-warn/30 !text-warn"
              badgeText="Hazards"
            />
            <FactorList
              title="Key Uncertainties"
              subtitle="Measurement variance & sensor coverage gaps"
              items={explanation.uncertainties}
              icon={<InfoIcon className="h-4 w-4 text-cyan" />}
              badgeClass="!border-cyan/30 !text-cyan"
              badgeText="Variance"
            />
            <FactorList
              title="Model & Data Limitations"
              subtitle="Algorithm scope & validation boundaries"
              items={explanation.limitations}
              icon={<XIcon className="h-4 w-4 text-bad" />}
              badgeClass="!border-bad/30 !text-bad"
              badgeText="Boundaries"
            />
          </div>
        </div>

        {/* Decision-support note */}
        <div className="mt-6 flex items-start gap-2.5 border-t border-divider pt-4 text-xs leading-relaxed text-muted">
          <AlertIcon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warn" />
          <span>
            This narrative synthesis is generated by the backend AI decision-support model (
            <span className="font-mono text-cyan">{explanation.model ?? "LLM"}</span>). It serves
            solely as preliminary exploration support and does not constitute human flight
            certification or independent engineering safety sign-off.
          </span>
        </div>
      </div>
    </div>
  );
}
