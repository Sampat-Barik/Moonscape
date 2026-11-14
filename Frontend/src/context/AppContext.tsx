/**
 * AppContext — shared application state for all pages.
 *
 * It owns:
 *  - the backend connection mode ("checking" | "live" | "mock"),
 *  - the candidate sites list,
 *  - the currently selected coordinates (shared across Explorer, Dashboard, Hazards, Compare, Report),
 *  - dataset coverage status (Feature 4),
 *  - terrain analysis results (Feature 5),
 *  - hazard detection results (Feature 6),
 *  - automated contiguous candidate landing regions (Feature 7),
 *  - mission date/time configuration & solar/Earth visibility simulation (Features 8, 9, 10),
 *  - suitability score & constraint evaluation (Feature 11),
 *  - site comparison results,
 *  - AI explanation synthesis,
 *  - and report dossier generation.
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
import { ApiError, api, getApiMode, probeBackend, setApiMode } from "@/services/api";
import type {
  AnalysisResponse,
  CompareResponse,
  DataCoverageResponse,
  DetectedLandingZone,
  DetectLandingSitesRequest,
  ExplanationResponse,
  HazardDetection,
  HealthResponse,
  ReportResponse,
  ScoreResponse,
  Site,
  TerrainResponse,
  VisibilitySimulationRequest,
  VisibilitySimulationResponse,
} from "@/types";

export type Status = "idle" | "loading" | "error" | "ready";

export interface Selection {
  latitude: number;
  longitude: number;
  radius_m: number;
}

export interface MissionConfig {
  startEpoch: string;
  durationDays: number;
  stepHours: number;
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

  coverage: DataCoverageResponse | null;
  coverageStatus: Status;
  coverageError: string | null;
  checkCoverage: (sel?: Selection) => Promise<void>;

  terrain: TerrainResponse | null;
  terrainStatus: Status;
  terrainError: string | null;
  refreshTerrain: (sel?: Selection) => Promise<void>;

  analysis: AnalysisResponse | null;
  analysisStatus: Status;
  analysisError: string | null;
  runAnalysis: (sel?: Selection) => Promise<boolean>;

  detectedZones: DetectedLandingZone[];
  detectStatus: Status;
  detectError: string | null;
  runDetectSites: (sel?: Selection, params?: Partial<DetectLandingSitesRequest>) => Promise<void>;

  missionConfig: MissionConfig;
  setMissionConfig: (cfg: Partial<MissionConfig>) => void;

  simulation: VisibilitySimulationResponse | null;
  simulationStatus: Status;
  simulationError: string | null;
  runSimulation: (customConfig?: Partial<VisibilitySimulationRequest>) => Promise<void>;

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
const DEFAULT_SELECTION: Selection = { latitude: -89.44, longitude: 222.5, radius_m: 1000 };
const DEFAULT_MISSION: MissionConfig = {
  startEpoch: "2026-10-15T00:00:00Z",
  durationDays: 14,
  stepHours: 2,
};

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

  const [coverage, setCoverage] = useState<DataCoverageResponse | null>(null);
  const [coverageStatus, setCoverageStatus] = useState<Status>("idle");
  const [coverageError, setCoverageError] = useState<string | null>(null);

  const [terrain, setTerrain] = useState<TerrainResponse | null>(null);
  const [terrainStatus, setTerrainStatus] = useState<Status>("idle");
  const [terrainError, setTerrainError] = useState<string | null>(null);

  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(() =>
    loadJSON<AnalysisResponse>(LS_ANALYSIS)
  );
  const [analysisStatus, setAnalysisStatus] = useState<Status>("idle");
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const [detectedZones, setDetectedZones] = useState<DetectedLandingZone[]>([]);
  const [detectStatus, setDetectStatus] = useState<Status>("idle");
  const [detectError, setDetectError] = useState<string | null>(null);

  const [missionConfig, setMissionConfigState] = useState<MissionConfig>(DEFAULT_MISSION);

  const [simulation, setSimulation] = useState<VisibilitySimulationResponse | null>(null);
  const [simulationStatus, setSimulationStatus] = useState<Status>("idle");
  const [simulationError, setSimulationError] = useState<string | null>(null);

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

  // Keep refs of active values to prevent closures from using stale coordinates
  const selectionRef = useRef(selection);
  selectionRef.current = selection;

  const missionConfigRef = useRef(missionConfig);
  missionConfigRef.current = missionConfig;

  // Debounce ref for rapid coordinate updates (e.g. typing or scrubbing)
  const coverageDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    return () => {
      if (coverageDebounceRef.current) clearTimeout(coverageDebounceRef.current);
    };
  }, []);

  // Probe the backend once on startup
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

  const checkCoverage = useCallback(async (sel?: Selection) => {
    const s = sel ?? selectionRef.current;
    setCoverageStatus("loading");
    setCoverageError(null);
    try {
      const cov = await api.checkCoverage(s.latitude, s.longitude);
      setCoverage(cov);
      setCoverageStatus("ready");
    } catch (e) {
      if (e instanceof ApiError && e.status === 499) {
        // Superseded by newer coordinate selection; suppress error banner
        return;
      }
      setCoverageError(errMsg(e));
      setCoverageStatus("error");
    }
  }, []);

  const refreshTerrain = useCallback(async (sel?: Selection) => {
    const s = sel ?? selectionRef.current;
    setTerrainStatus("loading");
    setTerrainError(null);
    try {
      setTerrain(await api.getTerrain(s.latitude, s.longitude, s.radius_m));
      setTerrainStatus("ready");
    } catch (e) {
      if (e instanceof ApiError && e.status === 499) {
        return;
      }
      setTerrainError(errMsg(e));
      setTerrainStatus("error");
    }
  }, []);

  // Update selection with automatic invalidation of stale location-dependent metrics
  const setSelection = useCallback(
    (s: Selection) => {
      const prev = selectionRef.current;
      const coordChanged =
        Math.abs(prev.latitude - s.latitude) > 0.0001 ||
        Math.abs(prev.longitude - s.longitude) > 0.0001;

      setSelectionState(s);
      try {
        localStorage.setItem(LS_SELECTION, JSON.stringify(s));
      } catch {
        /* storage unavailable — ignore */
      }

      if (coordChanged) {
        // Invalidate stale scores, hazards, simulations, and detected zones from previous locations
        setScore(null);
        setScoreStatus("idle");
        setHazards(null);
        setHazardsStatus("idle");
        setSimulation(null);
        setSimulationStatus("idle");
        setDetectedZones([]);
        setDetectStatus("idle");

        // Debounce network coverage check by 200ms to avoid flooding backend during rapid scrubbing
        if (coverageDebounceRef.current) {
          clearTimeout(coverageDebounceRef.current);
        }
        coverageDebounceRef.current = setTimeout(() => {
          void checkCoverage(s);
        }, 200);
      }
    },
    [checkCoverage]
  );

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

  const runDetectSites = useCallback(
    async (sel?: Selection, params?: Partial<DetectLandingSitesRequest>) => {
      const s = sel ?? selectionRef.current;
      setDetectStatus("loading");
      setDetectError(null);
      try {
        const res = await api.detectLandingSites({
          center_lat: s.latitude,
          center_lon: s.longitude,
          search_radius_meters: s.radius_m || 1500.0,
          ...params,
        });
        setDetectedZones(res.candidate_zones || []);
        setDetectStatus("ready");
      } catch (e) {
        setDetectError(errMsg(e));
        setDetectStatus("error");
      }
    },
    []
  );

  const setMissionConfig = useCallback((cfg: Partial<MissionConfig>) => {
    setMissionConfigState((prev) => ({ ...prev, ...cfg }));
  }, []);

  const runSimulation = useCallback(
    async (customConfig?: Partial<VisibilitySimulationRequest>) => {
      const s = selectionRef.current;
      const m = missionConfigRef.current;
      setSimulationStatus("loading");
      setSimulationError(null);
      try {
        const sim = await api.simulateVisibility({
          lat: s.latitude,
          lon: s.longitude,
          start_epoch_iso: customConfig?.start_epoch_iso ?? m.startEpoch,
          duration_days: customConfig?.duration_days ?? m.durationDays,
          step_hours: customConfig?.step_hours ?? m.stepHours,
        });
        setSimulation(sim);
        setSimulationStatus("ready");
      } catch (e) {
        if (e instanceof ApiError && e.status === 499) {
          return;
        }
        setSimulationError(errMsg(e));
        setSimulationStatus("error");
      }
    },
    []
  );

  const runAnalysis = useCallback(
    async (sel?: Selection): Promise<boolean> => {
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

        // Trigger downstream analysis chain for this verified location
        void runScore(s);
        void runDetectSites(s);
        void runSimulation();
        return true;
      } catch (e) {
        setAnalysisError(errMsg(e));
        setAnalysisStatus("error");
        return false;
      }
    },
    [runScore, runDetectSites, runSimulation]
  );

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

  // Initial coverage check on load
  useEffect(() => {
    if (mode !== "checking") {
      void checkCoverage();
    }
  }, [mode, checkCoverage]);

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
      coverage,
      coverageStatus,
      coverageError,
      checkCoverage,
      terrain,
      terrainStatus,
      terrainError,
      refreshTerrain,
      analysis,
      analysisStatus,
      analysisError,
      runAnalysis,
      detectedZones,
      detectStatus,
      detectError,
      runDetectSites,
      missionConfig,
      setMissionConfig,
      simulation,
      simulationStatus,
      simulationError,
      runSimulation,
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
      mode,
      health,
      cycleMode,
      sites,
      sitesStatus,
      sitesError,
      refreshSites,
      selection,
      setSelection,
      coverage,
      coverageStatus,
      coverageError,
      checkCoverage,
      terrain,
      terrainStatus,
      terrainError,
      refreshTerrain,
      analysis,
      analysisStatus,
      analysisError,
      runAnalysis,
      detectedZones,
      detectStatus,
      detectError,
      runDetectSites,
      missionConfig,
      setMissionConfig,
      simulation,
      simulationStatus,
      simulationError,
      runSimulation,
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
    ]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
