# Moonscape AI Scientific Explainer Guide (Phase 7)
**Document Version:** 1.0-phase7  
**Module:** `backend/services/ai_explainer.py` / `Backend/app/services/ai_providers.py`  
**Classification:** System Architecture, Provider Evaluation, Prompt Engineering & Reliability Guide

---

## 1. Architecture & Design Principles

The **Moonscape AI Scientific Explainer** transforms complex backend geospatial, topographic, and multi-criteria suitability measurements into clear, accessible language for mission planners and aerospace researchers.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Web Layer                             │
│                     POST /api/ai/explain                               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        AIExplainerService                              │
│  - Analysis Retrieval (from AnalysisStore by analysis_id)              │
│  - Measurement Grounding & Anti-Hallucination Prompt Assembly          │
│  - Fallback Orchestration & Structured Output Validation               │
└───────────────┬───────────────────────────────────┬────────────────────┘
                │ (Configured Provider)             │ (Automatic Fallback)
                ▼                                   ▼
┌───────────────────────────────────┐   ┌────────────────────────────────┐
│       Remote LLM Providers        │   │ Offline Deterministic Engine   │
│  - Google Gemini 1.5/2.0 Flash    │   │  - Zero network, zero cost     │
│  - OpenAI GPT-4o-mini             │   │  - 100% deterministic physics  │
│  - (Configurable via BaseAdapter) │   │  - Resilient test & dev mode   │
└───────────────────────────────────┘   └────────────────────────────────┘
```

### Core Architecture Directives
1. **Explain Backend Data Only:** The AI service explains actual backend measurements (`elevation`, `slope`, `roughness`, `illumination`, `hazards`, `suitability`). It is **never** permitted to generate or hallucinate independent scientific measurements.
2. **Never Overwrite Backend Scores:** The multi-criteria suitability score (0–100) calculated by the Phase 6 MCDA engine is authoritative. The AI is forbidden from altering or recalculating it.
3. **Strict Decoupling via Provider Adapters:** The LLM integration is built on an abstract `BaseAIProvider` interface. Switching between Google Gemini, OpenAI, or an offline rule engine requires only a single environment variable (`MOONSCAPE_AI_PROVIDER`).
4. **Security & Zero Key Exposure:** API keys reside exclusively in backend environment variables (`.env`). They are **never** passed to the frontend or included in HTTP responses.
5. **Fail-Safe Reliability:** If the remote LLM experiences timeouts, rate limits, or network failures, the service seamlessly falls back to its built-in **Offline Deterministic Rule Engine**, ensuring the frontend never crashes.

---

## 2. LLM Provider Evaluation & Cost Breakdown

| Provider | Model | Free Development Tier | Commercial Pricing (Pay-as-you-go) | Latency | Evaluation & Recommendation |
|---|---|---|---|---|---|
| **Google Gemini (Recommended)** | `gemini-1.5-flash` / `gemini-2.0-flash` | **15 RPM** (Requests / Min)<br>**1,500 RPD** (Requests / Day)<br>**1,000,000 TPM** | **\$0.075** / 1M input tokens<br>**\$0.300** / 1M output tokens | ~1.2s | **(Primary Recommended)** Excellent free development quota on Google AI Studio without credit card requirement. Native JSON mode and fast inference. |
| **OpenAI** | `gpt-4o-mini` | No permanent free tier (credit-based trial) | **\$0.150** / 1M input tokens<br>**\$0.600** / 1M output tokens | ~1.5s | **(Supported Alternative)** Industry standard; reliable JSON output. Requires funded OpenAI platform balance. |
| **Offline Deterministic Engine** | `Rule Engine v1.0` | **Unlimited (Local CPU)** | **\$0.00** (Free forever) | < 0.01s | **(Built-in Fallback)** Zero dependencies, zero network latency. Operates even when laptop is offline or API quotas are exhausted. |

---

## 3. Environment Configuration & Setup

### Setting up Google Gemini (Free Development Tier)

1. Visit [Google AI Studio](https://aistudio.google.com/) and create a free API key.
2. Open `Backend/.env` in VS Code and populate your key:
   ```env
   # AI Scientific Explainer Configuration
   MOONSCAPE_AI_PROVIDER="gemini"
   GEMINI_API_KEY="AIzaSyYourGeminiApiKeyHere..."
   MOONSCAPE_AI_MODEL="gemini-1.5-flash"
   MOONSCAPE_AI_TIMEOUT_SECONDS=15.0
   MOONSCAPE_AI_TEMPERATURE=0.2
   ```
3. If `GEMINI_API_KEY` is left blank, the system automatically falls back to `"mock"` (Offline Deterministic Rule Engine), allowing completely seamless local development with zero external setup.

---

## 4. Prompt Engineering & Anti-Hallucination Strategy

To prevent hallucinations, the system uses a **Grounding-First** prompt architecture:

### System Prompt Guardrails
```markdown
1. EXPLAIN ONLY GIVEN DATA: Never fabricate or invent measurements or percentages.
2. DISTINGUISH FACTS FROM PREDICTIONS: Clearly distinguish measured physical facts (LOLA altimetry) from model predictions or synthetic proxies.
3. DO NOT CERTIFY LANDING SAFETY: Never declare a site 'safe for landing'. Explicitly describe the evaluation as a 'preliminary computational screening assessment'.
4. RESPECT THE SUITABILITY SCORE: Never alter or recalculate the backend's computed suitability score.
5. HIGHLIGHT MISSING DATA: Explicitly call out any missing, unmeasured, or uncalibrated factors.
6. INSUFFICIENT DATA NOTICE: If slope is missing or score coverage is below 50%, explicitly state that data is currently insufficient for reliable landing site evaluation.
```

### Dynamic Context Injection
Only verified measurements extracted from the `AnalysisRunResponse` are provided in the prompt:
- Regional coordinates and physical analysis radius.
- Topographic elevation range, mean elevation, and relief variation.
- Topographic slope statistics, slope calculation operator (Horn 1981), and slope distribution percentages.
- Surface micro-roughness (RMS residual height deviation over 15m baseline).
- Solar illumination percentages (cumulative and instantaneous) and PSR cold-trap status.
- Preliminary suitability score, score coverage percentage, evaluated criteria subscores, and missing factors.
- Spatial dataset attribution (NASA Product 78 LOLA 5m DEM / 80m DEM).

---

## 5. Structured Output Schema

The API enforces strict Pydantic validation on the LLM output:

```json
{
  "analysis_id": "analysis_001",
  "explanation": "Clear, accessible narrative explanation synthesizing the terrain, illumination, and suitability measurements.",
  "positive_factors": [
    "Benign local slope averaging 6.8 deg is within acceptable nominal landing gear stability tolerances.",
    "Strong solar illumination (86.4%) provides reliable photovoltaic array power and mitigates severe cryogenic cooling."
  ],
  "risk_factors": [
    "Low grazing solar angles (< 2 deg) produce dynamic, elongated shadows that complicate optical navigation.",
    "Sub-pixel boulder fields require terminal hazard detection and avoidance (HDA) maneuvers."
  ],
  "limitations": [
    "Analysis is a preliminary computational screening indicator and does NOT constitute NASA-certified flight clearance.",
    "High-resolution optical crater and boulder hazard counts are uncalibrated or pending orbital ground-truth validation."
  ],
  "conclusion": "Preliminary assessment only. Candidate site warrants high-resolution LROC photogrammetric validation."
}
```

---

## 6. Scientific Limitations & Domain Boundaries

1. **Screening Indicator Only:** The AI explainer acts purely as a narrative translation interface for computational measurements. It does not replace flight dynamics simulations, trajectory dispersion analysis, or hazard relative navigation (TRN) flight software.
2. **Resolution Limits:** Regional 80m and high-resolution 5m LOLA DEMs cannot resolve boulders smaller than ~10m without sub-pixel curvature modeling or optical LROC NAC photogrammetry. The explainer explicitly reminds users of this sub-pixel limit.
3. **Seasonal Illumination Dynamics:** Lunar South Pole illumination varies with the Moon's 1.54° obliquity and 18.6-year draconic nodal precession. Annual cumulative illumination does not guarantee continuous instantaneous power during a specific landing epoch.
