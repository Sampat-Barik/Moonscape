import type { Route } from "@/hooks/useHashRoute";
import SiteComparison from "@/components/SiteComparison";
import { GlobeIcon } from "@/components/icons";

export default function Compare({ navigate }: { navigate: (r: Route) => void }) {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {/* Page Header */}
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b border-divider pb-6">
        <div>
          <span className="kicker">Site Comparison</span>
          <h1 className="mt-1 font-display text-2xl font-semibold text-ink sm:text-3xl">
            Candidate Landing Site Evaluation
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
            Evaluate candidate lunar South Pole landing sites side by side using real LOLA
            altimetry, surface slope gradients, and preliminary suitability scores (
            <span className="chip font-mono !py-0.5 !px-1.5 text-[11px]">POST /api/sites/compare</span>).
          </p>
        </div>
        <button
          className="btn-ghost !px-4 !py-2 !text-xs"
          onClick={() => navigate("/explorer")}
        >
          <GlobeIcon className="h-4 w-4" />
          Open Lunar Explorer
        </button>
      </div>

      <SiteComparison />
    </div>
  );
}
