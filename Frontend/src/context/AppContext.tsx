/**
 * AppContext — shared application state for all pages.
 *
 * It owns:
 *  - the backend connection mode ("checking" | "live" | "mock"),
 *  - the candidate sites list,
 *  - the currently selected coordinates,
 *  - and the results of every API call (terrain, analysis, score, hazards,
 *    comparison, AI explanation, report) together with their
 *    loading / error status so pages can show spinners and error panels.
 *
 * All network access happens inside `services/api.ts`; this context only
 * stores results and exposes actions.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api, getApiMode, probeBackend, setApiMode } from "@/services/api";
import type {
  AnalysisResponse,
  CompareResponse,
  ExplanationResponse,
  HazardDetection,
  HealthResponse,
  ReportResponse,
  ScoreResponse,
  Site,
  TerrainResponse,
} from "@/types";

export type Status = "idle" | "loading" | "error" | "ready";

export interface Selection {
  latitude: number;
  longitude: number;
  radius_m: number;
}

export interface AppContextValue {
  mode: "checking" | "live" | "mock";
  health: HealthResponse | null;
  cycleMode: () => void;

  sites: Site[];
  sitesStatus: Status;
  sitesError: string | null;
  refreshSites: () => Promise<void>;

  selection: Selection;
  setSelection: (s: Selection) => void;

  terrain: TerrainResponse | null;
  terrainStatus: Status;
  terrainError: string | null;
  refreshTerrain: (sel?: Selection) => Promise<void>;

  analysis: AnalysisResponse | null;
  analysisStatus: Status;
  analysisError: string | null;
  runAnalysis: (sel?: Selection) => Promise<boolean>;

  score: ScoreResponse | null;
  scoreStatus: Status;
  scoreError: string | null;
  runScore: (sel?: Selection) => Promise<void>;

  hazards: HazardDetection | null;
  hazardsStatus: Status;
  hazardsError: string | null;
  runHazards: (sel?: Selection) => Promise<void>;

  comparison: CompareResponse | null;
  compareStatus: Status;
  compareError: string | null;
  compare: (siteIds: string[]) => Promise<void>;

  explanation: ExplanationResponse | null;
  explainStatus: Status;
  explainError: string | null;
  explain: (analysisId: string) => Promise<void>;

  report: ReportResponse | null;
  reportStatus: Status;
  reportError: string | null;
  generateReportAction: (analysisId: string, format?: string) => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside <AppProvider>");
  return ctx;
}

const LS_SELECTION = "moonscape.selection";
const LS_ANALYSIS = "moonscape.analysis";
const DEFAULT_SELECTION: Selection = { latitude: -89.5, longitude: 0, radius_m: 500 };

function loadJSON<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<"checking" | "live" | "mock">("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const [sites, setSites] = useState<Site[]>([]);
  const [sitesStatus, setSitesStatus] = useState<Status>("idle");
  const [sitesError, setSitesError] = useState<string | null>(null);

  const [selection, setSelectionState] = useState<Selection>(
    () => loadJSON<Selection>(LS_SELECTION) ?? DEFAULT_SELECTION
  );

  const [terrain, setTerrain] = useState<TerrainResponse | null>(null);
  const [terrainStatus, setTerrainStatus] = useState<Status>("idle");
  const [terrainError, setTerrainError] = useState<string | null>(null);

  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(() =>
    loadJSON<AnalysisResponse>(LS_ANALYSIS)
  );
  const [analysisStatus, setAnalysisStatus] = useState<Status>("idle");
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [scoreStatus, setScoreStatus] = useState<Status>("idle");
  const [scoreError, setScoreError] = useState<string | null>(null);

  const [hazards, setHazards] = useState<HazardDetection | null>(null);
  const [hazardsStatus, setHazardsStatus] = useState<Status>("idle");
  const [hazardsError, setHazardsError] = useState<string | null>(null);

  const [comparison, setComparison] = useState<CompareResponse | null>(null);
  const [compareStatus, setCompareStatus] = useState<Status>("idle");
  const [compareError, setCompareError] = useState<string | null>(null);

  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [explainStatus, setExplainStatus] = useState<Status>("idle");
  const [explainError, setExplainError] = useState<string | null>(null);

  const [report, setReport] = useState<ReportResponse | null>(null);
  const [reportStatus, setReportStatus] = useState<Status>("idle");
  const [reportError, setReportError] = useState<string | null>(null);

  // Keep a ref of the selection so async actions never see a stale value.
  const selectionRef = useRef(selection);
  selectionRef.current = selection;

  // Probe the backend once on startup (auto mode falls back to mock).
  useEffect(() => {
    void (async () => {
      const res = await probeBackend();
      setMode(res.mode);
      setHealth(res.health);
    })();
  }, []);

  const refreshSites = useCallback(async () => {
    setSitesStatus("loading");
    setSitesError(null);
    try {
      setSites(await api.getSites());
      setSitesStatus("ready");
    } catch (e) {
      setSitesError(errMsg(e));
      setSitesStatus("error");
    }
  }, []);

  useEffect(() => {
    if (mode !== "checking") void refreshSites();
  }, [mode, refreshSites]);

  const cycleMode = useCallback(() => {
    const next = getApiMode() === "live" ? "mock" : "live";
    setApiMode(next);
    setMode(next);
  }, []);

  const setSelection = useCallback((s: Selection) => {
    setSelectionState(s);
    try {
      localStorage.setItem(LS_SELECTION, JSON.stringify(s));
    } catch {
      /* storage unavailable — ignore */
    }
  }, []);

  const refreshTerrain = useCallback(async (sel?: Selection) => {
    const s = sel ?? selectionRef.current;
    setTerrainStatus("loading");
    setTerrainError(null);
    try {
      setTerrain(await api.getTerrain(s.latitude, s.longitude));
      setTerrainStatus("ready");
    } catch (e) {
      setTerrainError(errMsg(e));
      setTerrainStatus("error");
    }
  }, []);

  const runAnalysis = useCallback(async (sel?: Selection): Promise<boolean> => {
    const s = sel ?? selectionRef.current;
    setAnalysisStatus("loading");
    setAnalysisError(null);
    try {
      const a = await api.runAnalysis(s);
      setAnalysis(a);
      setAnalysisStatus("ready");
      try {
        localStorage.setItem(LS_ANALYSIS, JSON.stringify(a));
      } catch {
        /* ignore */
      }
      return true;
    } catch (e) {
      setAnalysisError(errMsg(e));
      setAnalysisStatus("error");
      return false;
    }
  }, []);

  const runScore = useCallback(async (sel?: Selection) => {
    const s = sel ?? selectionRef.current;
    setScoreStatus("loading");
    setScoreError(null);
    try {
      setScore(await api.scoreSite(s));
      setScoreStatus("ready");
    } catch (e) {
      setScoreError(errMsg(e));
      setScoreStatus("error");
    }
  }, []);

  const runHazards = useCallback(async (sel?: Selection) => {
    const s = sel ?? selectionRef.current;
    setHazardsStatus("loading");
    setHazardsError(null);
    try {
      setHazards(await api.predictHazards(s));
      setHazardsStatus("ready");
    } catch (e) {
      setHazardsError(errMsg(e));
      setHazardsStatus("error");
    }
  }, []);

  const compare = useCallback(async (siteIds: string[]) => {
    setCompareStatus("loading");
    setCompareError(null);
    try {
      setComparison(await api.compareSites(siteIds));
      setCompareStatus("ready");
    } catch (e) {
      setCompareError(errMsg(e));
      setCompareStatus("error");
    }
  }, []);

  const explain = useCallback(async (analysisId: string) => {
    setExplainStatus("loading");
    setExplainError(null);
    try {
      setExplanation(await api.explainAnalysis(analysisId));
      setExplainStatus("ready");
    } catch (e) {
      setExplainError(errMsg(e));
      setExplainStatus("error");
    }
  }, []);

  const generateReportAction = useCallback(async (analysisId: string, format = "json") => {
    setReportStatus("loading");
    setReportError(null);
    try {
      setReport(await api.generateReport(analysisId, format));
      setReportStatus("ready");
    } catch (e) {
      setReportError(errMsg(e));
      setReportStatus("error");
    }
  }, []);

  const value = useMemo<AppContextValue>(
    () => ({
      mode,
      health,
      cycleMode,
      sites,
      sitesStatus,
      sitesError,
      refreshSites,
      selection,
      setSelection,
      terrain,
      terrainStatus,
      terrainError,
      refreshTerrain,
      analysis,
      analysisStatus,
      analysisError,
      runAnalysis,
      score,
      scoreStatus,
      scoreError,
      runScore,
      hazards,
      hazardsStatus,
      hazardsError,
      runHazards,
      comparison,
      compareStatus,
      compareError,
      compare,
      explanation,
      explainStatus,
      explainError,
      explain,
      report,
      reportStatus,
      reportError,
      generateReportAction,
    }),
    [
      mode, health, cycleMode, sites, sitesStatus, sitesError, refreshSites,
      selection, setSelection, terrain, terrainStatus, terrainError, refreshTerrain,
      analysis, analysisStatus, analysisError, runAnalysis, score, scoreStatus, scoreError,
      runScore, hazards, hazardsStatus, hazardsError, runHazards, comparison, compareStatus,
      compareError, compare, explanation, explainStatus, explainError, explain, report,
      reportStatus, reportError, generateReportAction,
    ]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
