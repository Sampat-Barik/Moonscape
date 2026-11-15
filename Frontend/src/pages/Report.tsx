import { useEffect, useState } from "react";
import type { Route } from "@/hooks/useHashRoute";
import { useApp } from "@/context/AppContext";
import { api } from "@/services/api";
import AIExplanation from "@/components/AIExplanation";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import { fmtCoord } from "@/utils/format";
import {
  DocIcon,
  DownloadIcon,
  GlobeIcon,
  RefreshIcon,
  SparkIcon,
} from "@/components/icons";

export default function Report({ navigate }: { navigate: (r: Route) => void }) {
  const {
    analysis,
    selection,
    explanation,
    explainStatus,
    explainError,
    explain,
    report,
    reportStatus,
    reportError,
    generateReportAction,
  } = useApp();

  const [analysisId, setAnalysisId] = useState("");
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  // Prefill the analysis id whenever a new analysis arrives.
  useEffect(() => {
    setAnalysisId(analysis?.analysis_id ?? "");
  }, [analysis?.analysis_id]);

  const canExplain = analysisId.trim().length > 0;

  const downloadReport = () => {
    const payload = report?.content ?? report;
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `moonscape-report-${analysisId.trim() || "analysis"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadPdf = async () => {
    const targetId = analysisId.trim();
    if (!targetId) return;
    setPdfLoading(true);
    setPdfError(null);
    try {
      const blob = await api.downloadPdfReport(targetId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `moonscape_report_${targetId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setPdfError(e instanceof Error ? e.message : String(e));
    } finally {
      setPdfLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      {/* ================= Document Header ================= */}
      <div className="mb-8 border-b border-divider pb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="kicker">Aerospace Research Dossier</span>
              <span className="chip font-mono">NASA LRO MISSION DATA</span>
            </div>
            <h1 className="mt-2 font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl">
              Lunar Landing-Site Feasibility Report
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Consolidated terrain telemetry, numerical suitability evaluation, and automated
              decision-support analysis for lunar polar surface operations.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="btn-ghost !px-3.5 !py-2 !text-xs"
              onClick={handlePrint}
              title="Print or export as PDF"
            >
              <DocIcon className="h-4 w-4" />
              Print / PDF
            </button>
            <button
              className="btn-ghost !px-3.5 !py-2 !text-xs"
              onClick={() => navigate("/explorer")}
            >
              <GlobeIcon className="h-4 w-4" />
              Explorer
            </button>
          </div>
        </div>

        {/* Technical Metadata Row */}
        <div className="mt-6 grid grid-cols-2 gap-4 rounded-lg border border-divider/60 bg-elevated/40 p-4 sm:grid-cols-4">
          <div>
            <span className="text-[10px] uppercase tracking-wider text-muted">Target Site</span>
            <p className="mt-0.5 font-mono text-xs font-semibold text-ink">
              {fmtCoord(selection.latitude, selection.longitude)}
            </p>
          </div>
          <div>
            <span className="text-[10px] uppercase tracking-wider text-muted">Evaluation Radius</span>
            <p className="mt-0.5 font-mono text-xs text-ink">{selection.radius_m} m</p>
          </div>
          <div>
            <span className="text-[10px] uppercase tracking-wider text-muted">Session ID</span>
            <p className="mt-0.5 font-mono text-xs text-ink">
              {analysis?.analysis_id ?? (analysisId || "None")}
            </p>
          </div>
          <div>
            <span className="text-[10px] uppercase tracking-wider text-muted">Classification</span>
            <p className="mt-0.5 font-mono text-xs text-good">OPEN SCIENCE / DEMO</p>
          </div>
        </div>
      </div>

      {/* ================= Empty State Warning ================= */}
      {!analysis && (
        <div className="panel mb-8 flex items-start gap-4 p-6">
          <DocIcon className="mt-1 h-6 w-6 shrink-0 text-ink" />
          <div className="flex-1">
            <h3 className="font-display text-sm font-semibold text-ink">
              No active analysis session in memory
            </h3>
            <p className="mt-1 text-xs leading-relaxed text-muted">
              Select coordinates in the Lunar Explorer and run an analysis to automatically populate
              this dossier. You can also paste an existing <span className="font-mono text-ink">analysis_id</span>{" "}
              below to retrieve historical reports.
            </p>
            <button
              className="btn-primary mt-4 !px-4 !py-2 !text-xs"
              onClick={() => navigate("/explorer")}
            >
              <GlobeIcon className="h-3.5 w-3.5" />
              Open Lunar Explorer
            </button>
          </div>
        </div>
      )}

      {/* ================= Report Controls Toolbar ================= */}
      <div className="panel mb-8 p-6">
        <label
          htmlFor="analysis-id"
          className="kicker mb-2 block text-xs"
        >
          Session Target ID
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            id="analysis-id"
            className="input flex-1"
            placeholder="e.g. analysis_001"
            value={analysisId}
            onChange={(e) => setAnalysisId(e.target.value)}
          />
          <button
            className="btn-primary !px-4 !py-2.5 !text-xs"
            disabled={!canExplain || explainStatus === "loading"}
            onClick={() => void explain(analysisId.trim())}
          >
            {explainStatus === "loading" ? (
              <span className="spinner !h-4 !w-4" />
            ) : (
              <SparkIcon className="h-4 w-4" />
            )}
            Generate AI Explanation
          </button>
          <button
            className="btn-ghost !px-4 !py-2.5 !text-xs"
            disabled={!canExplain || reportStatus === "loading"}
            onClick={() => void generateReportAction(analysisId.trim(), "json")}
          >
            {reportStatus === "loading" ? (
              <span className="spinner !h-4 !w-4" />
            ) : (
              <RefreshIcon className="h-4 w-4" />
            )}
            Generate Full Report
          </button>
          <button
            className="btn-primary !px-4 !py-2.5 !text-xs"
            disabled={!canExplain || pdfLoading}
            onClick={() => void downloadPdf()}
            title="Download official binary PDF report compiled by FastAPI"
          >
            {pdfLoading ? (
              <span className="spinner !h-4 !w-4" />
            ) : (
              <DownloadIcon className="h-4 w-4" />
            )}
            Download Official PDF
          </button>
        </div>
        {pdfError && (
          <p className="mt-2 text-xs text-bad">PDF export error: {pdfError}</p>
        )}
      </div>

      {/* ================= Section 1: AI Explanation ================= */}
      <div className="mb-8">
        <AIExplanation
          explanation={explanation}
          status={explainStatus}
          error={explainError}
          onRetry={() => canExplain && void explain(analysisId.trim())}
        />
        {explainStatus === "idle" && (
          <div className="panel p-6 text-center text-xs text-muted">
            No narrative explanation synthesized yet. Click “Generate AI Explanation” above.
          </div>
        )}
      </div>

      {/* ================= Section 2: Technical JSON Report ================= */}
      <div className="mb-8">
        {reportStatus === "loading" && (
          <div className="panel p-8 text-center">
            <LoadingState label="Compiling technical mission dossier (POST /api/reports/generate)…" />
          </div>
        )}
        {reportStatus === "error" && (
          <ErrorState
            title="Dossier compilation failed"
            message={reportError}
            onRetry={() => canExplain && void generateReportAction(analysisId.trim(), "json")}
          />
        )}
        {reportStatus === "ready" && report && (
          <div className="panel p-6 sm:p-8">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-divider pb-4">
              <div>
                <span className="kicker">Telemetry Export</span>
                <h3 className="font-display text-base font-semibold text-ink">
                  Full Technical JSON Dossier
                </h3>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {report.report_id && (
                  <span className="chip font-mono">id: {report.report_id}</span>
                )}
                {report.format && (
                  <span className="chip uppercase font-mono">{String(report.format)}</span>
                )}
                <button
                  className="btn-primary !px-4 !py-2 !text-xs"
                  onClick={downloadReport}
                >
                  <DownloadIcon className="h-4 w-4" />
                  Download JSON
                </button>
              </div>
            </div>

            {report.download_url && (
              <p className="mt-3 font-mono text-xs text-muted">
                Direct URL:{" "}
                <a
                  className="text-ink underline hover:text-white"
                  href={String(report.download_url)}
                  target="_blank"
                  rel="noreferrer"
                >
                  {String(report.download_url)}
                </a>
              </p>
            )}

            <pre className="mt-4 max-h-96 overflow-auto rounded-lg border border-divider bg-space/80 p-4 font-mono text-xs leading-relaxed text-slate-200">
              {JSON.stringify(report.content ?? report, null, 2)}
            </pre>
          </div>
        )}
        {reportStatus === "idle" && (
          <div className="panel p-6 text-center text-xs text-muted">
            No technical JSON report generated yet. Click “Generate Full Report” above.
          </div>
        )}
      </div>

      {/* ================= Section 3: Data Provenance & Heritage ================= */}
      <div className="panel p-6">
        <span className="kicker mb-2 block">Data Provenance &amp; Sensor Heritage</span>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded border border-divider/60 bg-elevated/30 p-3.5">
            <h4 className="font-display text-xs font-semibold text-ink">LRO LOLA</h4>
            <p className="mt-1 text-[11px] leading-relaxed text-muted">
              Lunar Orbiter Laser Altimeter altimetry profiles providing topographic elevation,
              slope gradients, and RMS surface roughness.
            </p>
          </div>
          <div className="rounded border border-divider/60 bg-elevated/30 p-3.5">
            <h4 className="font-display text-xs font-semibold text-ink">LRO LROC NAC</h4>
            <p className="mt-1 text-[11px] leading-relaxed text-muted">
              Narrow Angle Camera high-resolution optical imagery for surface crater and boulder
              hazard detection down to sub-meter scales.
            </p>
          </div>
          <div className="rounded border border-divider/60 bg-elevated/30 p-3.5">
            <h4 className="font-display text-xs font-semibold text-ink">Solar Illumination Models</h4>
            <p className="mt-1 text-[11px] leading-relaxed text-muted">
              Time-averaged solar visibility calculations assessing permanently shadowed regions
              (PSRs) and peaks of eternal light at the South Pole.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
