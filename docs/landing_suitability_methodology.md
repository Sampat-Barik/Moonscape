# Moonscape Lunar Landing-Site Suitability Methodology (Phase 6)
**Document Version:** 2.0-phase6  
**Module:** `backend/services/site_scoring.py` / `maths/scoring.py`  
**Classification:** Scientific Technical Documentation & Engineering Rationale  
**Target Mission Context:** NASA Artemis III / Commercial Lunar Payload Services (CLPS) Polar Landers

---

## 1. Executive Summary & Core Scientific Principles

The **Moonscape Landing-Site Suitability Engine** provides an automated, transparent, multi-criteria decision analysis (MCDA) framework for preliminary screening of lunar South Pole landing candidates.

### Critical Operational Disclaimer
> [!IMPORTANT]
> **PRELIMINARY COMPUTATIONAL SCREENING ONLY — NOT FLIGHT CERTIFICATION:**  
> The numerical suitability score (0–100) produced by this engine is an early-stage exploration and trade-off screening indicator. It does **not** constitute a NASA-certified landing safety clearance, terrain clearance guarantee, or flight qualification. All threshold values and scoring curves are **provisional engineering assumptions** based on published aerospace literature and must be verified against high-resolution orbital ground truth (e.g., LROC NAC stereophotogrammetry, mini-RF radar, and optical hazard cameras) prior to mission trajectory design.

### Core Architecture Tenets
1. **No Artificial Zero-Padding:** Unmeasured or missing criteria are **never** treated as zero (which would falsely punish or distort a site's evaluation).
2. **No Silent Weight Redistribution:** When criteria are omitted, weights are not silently re-allocated to remaining criteria; instead, the system tracks and explicitly reports **Score Coverage** ($\text{Coverage} \le 100\%$).
3. **Mandatory Safety Gates:** Topographic slope is the paramount physical tip-over risk factor. If slope data is missing or invalid, the engine **refuses to certify a score** (`overall_suitability_score = null`, category: `"Insufficient data"`).
4. **Coverage Thresholds:** If data coverage is below 50.0%, the composite score is marked as insufficient to prevent premature decisions on sparse data.

---

## 2. Multi-Criteria Evaluation Factors & Engineering Rationale

The engine synthesizes six physical, topographical, and environmental parameters into a unified suitability assessment:

```
                            ┌─────────────────────────────────────────┐
                            │   LUNAR LANDING SUITABILITY ENGINE      │
                            │             (Criteria v2.0)             │
                            └────────────────────┬────────────────────┘
                                                 │
         ┌──────────────────┬────────────────────┼───────────────────┬──────────────────┐
         ▼                  ▼                    ▼                   ▼                  ▼
   ┌───────────┐      ┌───────────┐        ┌───────────┐       ┌───────────┐      ┌───────────┐
   │ Topographic│      │  Terrain  │        │   Solar   │       │  Crater   │      │   Rock    │
   │   Slope   │      │ Roughness │        │Illuminat. │       │  Hazards  │      │  Hazards  │
   │ (Tip-over)│      │(Clearance)│        │  (Power)  │       │(Morphol.) │      │(Puncture) │
   └─────┬─────┘      └─────┬─────┘        └─────┬─────┘       └─────┬─────┘      └─────┬─────┘
         │                  │                    │                   │                  │
         └──────────────────┴─────────────┬──────┴───────────────────┴──────────────────┘
                                          ▼
                            ┌─────────────────────────┐
                            │    Safety Gate Check    │  (Slope present? Coverage >= 50%?)
                            └─────────────┬───────────┘
                                          │
                         Pass ┌───────────┴───────────┐ Fail
                              ▼                       ▼
                     [Composite MCDA Score]     [null / Insufficient Data]
```

### Factor 1: Topographic Slope (`slope_deg`)
* **Physical Phenomenon:** Local regional and sub-regional terrain inclination.
* **Engineering Impact:** Lander stability, dynamic footpad landing gear stroke limits, tip-over torque on contact, landing engine plume backpressure.
* **Aerospace Benchmark:**
  - Apollo Lunar Module (LM) structural tilt design limit was $12^\circ$ static tip-over margin.
  - NASA Artemis Human Landing System (HLS) operational guidelines target landing sites with local slopes $< 5^\circ$ (ideal), $< 8^\circ$ (nominal operational limit), and impose a hard critical cutoff at $15^\circ$ where dynamic tip-over risk escalates sharply.
* **Preference Direction:** *Lower is better* (strictly monotonically decreasing).

### Factor 2: Terrain Roughness (`roughness_m`)
* **Physical Phenomenon:** Micro-topographic height deviation (RMS residual from local mean surface, baseline 15m–25m).
* **Engineering Impact:** Sub-pixel boulders, decimeter-scale regolith undulations, differential landing leg crush-core stroking, structural clearance under lander descent engine bell.
* **Benchmark:** RMS roughness $< 0.15\text{ m}$ indicates smooth regolith; $0.15\text{ m} - 0.50\text{ m}$ represents nominal undulating terrain; $> 1.0\text{ m}$ presents severe landing gear clearance hazards.
* **Preference Direction:** *Lower is better*.

### Factor 3: Solar Illumination Availability (`illumination_pct`)
* **Physical Phenomenon:** Cumulative solar visibility over draconic and seasonal cycles (Barker et al. 2021).
* **Engineering Impact:** Photovoltaic power generation, battery energy storage mass sizing, thermal environment (avoiding severe cryogenic temperatures down to 40 K found in permanently shadowed regions).
* **Benchmark:** South Pole high-altitude rim massifs achieve $70\% - 92\%$ annual illumination; depressions and crater floors frequently drop below $20\%$ or are permanently shadowed ($0\%$).
* **Preference Direction:** *Higher is better*.

### Factor 4: Crater Hazard Density (`crater_count`)
* **Physical Phenomenon:** Number of detected impact craters with diameter exceeding lander footpad span ($D \ge 3\text{ m} - 5\text{ m}$) within the touchdown footprint.
* **Engineering Impact:** Footpad landing on crater rims or sloping crater interior walls induces severe touchdown tilt, roll rates, and potential structural overturning.
* **Benchmark:** 0 craters is pristine; $1 - 2$ craters requires precise hazard avoidance maneuvers (TRN/HDA); $\ge 5$ craters within landing footprint represents high risk.
* **Preference Direction:** *Lower is better*.

### Factor 5: Rock / Boulder Hazard Density (`rock_count`)
* **Physical Phenomenon:** Detected surface rocks/boulders exceeding minimum clearance height ($h \ge 0.3\text{ m} - 0.5\text{ m}$).
* **Engineering Impact:** Lander belly-pan rupture, fuel line impingement, footpad landing on rock apex inducing severe tipping torque.
* **Benchmark:** 0 rocks is ideal; $1 - 3$ rocks is manageable with hazard-relative navigation; $\ge 8$ rocks represents an unacceptably hazardous boulder field.
* **Preference Direction:** *Lower is better*.

### Factor 6: Surface Elevation Profile (`elevation_m`)
* **Physical Phenomenon:** Elevation in meters relative to lunar reference sphere ($R = 1737.4\text{ km}$).
* **Engineering Impact:** In the lunar South Pole environment, topography dictates visibility. Elevated massifs (e.g., Malapert Mountain at $+5000\text{ m}$, Connecting Ridge at $-120\text{ m}$) maintain sustained lines of sight to Earth (direct communications) and the Sun (power) compared to deep crater floors ($-3000\text{ m}$ to $-4000\text{ m}$).
* **Benchmark:** Scaled across South Pole elevation range $[-4000\text{ m}, +5000\text{ m}]$.
* **Preference Direction:** *Higher is better*.

---

## 3. Mathematical Normalization Functions

Every raw physical measurement $x$ is mapped to a normalized dimension-free subscore $s \in [0.0, 100.0]$ using continuous, piecewise-linear engineering curves:

### 3.1 Slope Normalization $f_{\text{slope}}(\theta)$
$$\theta = \text{slope in degrees}$$

$$
f_{\text{slope}}(\theta) = 
\begin{cases}
100.0 - 1.0 \cdot \theta & 0 \le \theta \le 5.0^\circ \quad (\text{Ideal: } 100 \to 95) \\
95.0 - \frac{35.0}{5.0}(\theta - 5.0) & 5.0^\circ < \theta \le 10.0^\circ \quad (\text{Acceptable: } 95 \to 60) \\
60.0 - \frac{40.0}{5.0}(\theta - 10.0) & 10.0^\circ < \theta \le 15.0^\circ \quad (\text{Marginal: } 60 \to 20) \\
\max\left(0.0, 20.0 - \frac{20.0}{10.0}(\theta - 15.0)\right) & 15.0^\circ < \theta \le 25.0^\circ \quad (\text{Hazardous: } 20 \to 0) \\
0.0 & \theta > 25.0^\circ
\end{cases}
$$

### 3.2 Roughness Normalization $f_{\text{roughness}}(r)$
$$r = \text{RMS roughness in meters}$$

$$
f_{\text{roughness}}(r) = 
\begin{cases}
100.0 - 40.0 \cdot r & 0.0 \le r \le 0.15\text{ m} \quad (100 \to 94) \\
94.0 - \frac{34.0}{0.35}(r - 0.15) & 0.15\text{ m} < r \le 0.50\text{ m} \quad (94 \to 60) \\
60.0 - \frac{40.0}{0.50}(r - 0.50) & 0.50\text{ m} < r \le 1.00\text{ m} \quad (60 \to 20) \\
\max\left(0.0, 20.0 - \frac{20.0}{1.00}(r - 1.00)\right) & 1.00\text{ m} < r \le 2.00\text{ m} \quad (20 \to 0) \\
0.0 & r > 2.00\text{ m}
\end{cases}
$$

### 3.3 Illumination Normalization $f_{\text{illum}}(I)$
$$I = \text{cumulative illumination percentage } [0, 100]$$

$$
f_{\text{illum}}(I) = \min(100.0, \max(0.0, I))
$$

### 3.4 Crater Hazard Normalization $f_{\text{crater}}(c)$
$$c = \text{integer crater count in landing footprint}$$

$$
f_{\text{crater}}(c) = 
\begin{cases}
100.0 & c = 0 \\
90.0 & c = 1 \\
75.0 & c = 2 \\
55.0 & c = 3 \\
35.0 & c = 4 \\
15.0 & c = 5 \\
\max(0.0, 15.0 - 3.0 \cdot (c - 5)) & c > 5
\end{cases}
$$

### 3.5 Rock Hazard Normalization $f_{\text{rock}}(k)$
$$k = \text{integer hazardous rock count in landing footprint}$$

$$
f_{\text{rock}}(k) = 
\begin{cases}
100.0 & k = 0 \\
92.0 & k = 1 \\
80.0 & k = 2 \\
65.0 & k = 3 \\
45.0 & k = 4 \\
25.0 & k = 5 \\
\max(0.0, 25.0 - 5.0 \cdot (k - 5)) & k > 5
\end{cases}
$$

### 3.6 Elevation Normalization $f_{\text{elev}}(h)$
$$h = \text{surface elevation in meters relative to reference sphere } [-4000\text{ m}, +5000\text{ m}]$$

$$
f_{\text{elev}}(h) = \min\left(100.0, \max\left(0.0, \frac{h - (-4000.0)}{5000.0 - (-4000.0)} \times 100.0\right)\right) = \frac{h + 4000.0}{90.0}
$$

---

## 4. Weighted MCDA Aggregation & Score Coverage

### 4.1 Configurable Weights Specification

The baseline weight distribution reflects landing safety priorities:

| Factor | Baseline Weight ($w_i$) | Rationale |
|---|---|---|
| **Topographic Slope** | $0.30$ | Primary lander tip-over constraint (Apollo / Artemis flight dynamics). |
| **Terrain Roughness** | $0.20$ | Landing gear clearance and differential footpad compaction. |
| **Solar Illumination** | $0.20$ | Long-term surface power and cryogenic thermal survival. |
| **Crater Hazards** | $0.10$ | Macro-topographic touchdown surface irregularities. |
| **Rock Hazards** | $0.10$ | Puncture and tipping obstacles exceeding ground clearance. |
| **Surface Elevation** | $0.10$ | Correlation with line-of-sight communications and horizon clearance. |
| **Total** | $\sum w_i = 1.00$ | Normalized baseline sum. |

### 4.2 Score Coverage Metric
Let $\mathcal{C}$ be the complete set of criteria, and $\mathcal{A} \subseteq \mathcal{C}$ be the set of criteria where valid measurements are available.

$$\text{Score Coverage (\%)} = \left( \frac{\sum_{i \in \mathcal{A}} w_i}{\sum_{j \in \mathcal{C}} w_j} \right) \times 100\%$$

### 4.3 Composite Suitability Formula
The composite score is calculated **strictly over available criteria**, normalized by the sum of available weights:

$$
S_{\text{composite}} = \frac{\sum_{i \in \mathcal{A}} w_i \cdot s_i}{\sum_{i \in \mathcal{A}} w_i}
$$

### 4.4 Safety-Gate Execution Rules
1. **Mandatory Slope Condition:** If $\text{slope} \notin \mathcal{A}$ or $\text{slope}$ is `null`:
   - $S_{\text{composite}} = \text{null}$
   - $\text{Category} = \text{"Insufficient data"}$
   - Warning issued: *"CRITICAL DATA DEFICIT: Topographic slope is unavailable. Landing safety suitability cannot be certified without terrain slope."*
2. **Minimum Coverage Condition:** If $\text{Coverage} < 50.0\%$:
   - $S_{\text{composite}} = \text{null}$
   - $\text{Category} = \text{"Insufficient data"}$
   - Warning issued: *"INSUFFICIENT DATA COVERAGE: Evaluated factors represent only X% of criteria weight (< 50% threshold)."*

---

## 5. Preliminary Suitability Categories

| Category | Score Interval | Operational Interpretation |
|---|---|---|
| **Higher preliminary suitability** | $S \ge 75.0$ | Favorable terrain; slopes $< 8^\circ$, low roughness, benign boulder/crater density, adequate illumination. Prime candidate for detailed trajectory analysis. |
| **Moderate preliminary suitability** | $50.0 \le S < 75.0$ | Acceptable operational envelope; may require advanced hazard detection and avoidance (HDA) maneuvers or localized terrain navigation. |
| **Lower preliminary suitability** | $S < 50.0$ | Significant operational risks; steep slopes, elevated roughness, hazardous crater/rock clusters, or prolonged shadow. |
| **Insufficient data** | `null` | Critical data absent (missing slope or coverage $< 50\%$). Precludes computational recommendation. |

---

## 6. Multi-Site Comparison Methodology

When comparing multiple landing sites via `POST /api/sites/compare`:
1. **Consistent Criteria Version:** All candidate sites are evaluated against an identical criteria version (`criteria_version = "2.0-phase6"`).
2. **Safety-Rank Sorting:** Sites are sorted in descending order of composite suitability score ($S$).
3. **Automated Trade-off Synthesis:** The engine generates an executive textual summary identifying the winning site, the specific margin of superiority, and notable vulnerabilities of competing sites.

---

## 7. Scientific Literature & Engineering References

1. **Apollo Lunar Module Operations Handbook:** *Volume 1: Subsystems Data*, Grumman Aerospace Corp. for NASA MSC, 1969. (Defines $12^\circ$ static touchdown stability envelope and leg stroking dynamics).
2. **Barker, M. K., Mazarico, E., et al. (2021):** *Improved Lunar South Pole Topography and Illumination Maps From Lunar Orbiter Laser Altimeter Data*, Planetary and Space Science, 203, 105252.
3. **Bennett, K. A., et al. (2020):** *Landing Site Evaluation for Lunar Polar Exploration*, 51st Lunar and Planetary Science Conference (LPSC), Houston, TX.
4. **Mazarico, E., et al. (2011):** *Illumination conditions of the lunar polar regions from Lunar Orbiter Laser Altimeter (LOLA) data*, Icarus, 211(2), 1066–1081.
5. **NASA Artemis Human Landing System Requirements (HLS-REQ-001):** *Touchdown dynamics, slope stability, and hazard avoidance performance envelopes*, NASA Marshall Space Flight Center, 2020.
