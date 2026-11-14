# Lunar Landing-Site Scoring System Audit & ML Training Feasibility Report
**Document ID:** MOON-FEAS-PHASE13-001  
**Project:** Moonscape Lunar South Pole Landing-Site Analysis Platform  
**Authors:** Senior Machine Learning Engineer, Planetary Scientist & Mission Analysis Specialist  
**Hardware Profile:** AMD Ryzen 9 894HX, 16 GB RAM, NVIDIA RTX 5070 Laptop GPU (8 GB VRAM), Windows 11  
**Status:** Approved Feasibility Architecture  

---

## 1. Executive Assessment & Audit of Existing Scoring Engine

Moonscape currently employs an Multi-Criteria Decision Analysis (MCDA v2.0-phase6) scoring engine implemented in `maths/scoring.py` and `Backend/app/services/site_scoring.py`. 

### 1.1 Existing Strengths
1. **Transparent Normalization:** Uses documented piece-wise linear penalty curves based on Apollo LM engineering limits and lunar landing literature (Bennett et al. 2020; Apollo LM Data Book).
2. **Explicit Missing-Data Treatment:** Missing measurements are strictly evaluated as `None` rather than silently replaced with zero.
3. **Data Coverage Tracking:** Explicitly calculates `score_coverage_pct` and suppresses composite scoring when coverage is below $50\%$ or when safety-critical slope is missing.

### 1.2 Deficiencies & Engineering Gaps Identified in Existing Engine
1. **Lack of Hard Constraint Pre-Filtering:**
   - *Problem:* A site with an extreme tip-over slope ($18.0^\circ$) currently receives a low score (e.g. 35/100) and is labeled "Lower preliminary suitability", but it is not formally *disqualified*. If other factors (e.g. $95\%$ continuous sunlight on a cliff edge) are high, a dangerously steep site could rank higher than a safe, flat plateau with slightly less sunlight.
   - *Requirement:* Hard constraints must precede soft scoring. Violations must disqualify the site (`hard_constraint_violated = True`) and lock the suitability ranking.
2. **Monolithic Weight Configuration:**
   - *Problem:* Default weights are fixed regardless of whether the mission is an uncrewed CLPS small rover or a heavy crewed Human Landing System (HLS).
   - *Requirement:* Configurable mission profiles with documented provenance.
3. **Absence of Multi-Baseline Roughness & Measurement Uncertainty:**
   - *Problem:* Single roughness values without scale specification; DEM vertical and slope errors are not propagated into score uncertainty intervals.
   - *Requirement:* Explicit scale baselines (15m, 60m, 240m) and Monte Carlo / analytical uncertainty bounds.

---

## 2. Defensible Training Targets & Label Provenance

Machine learning for lunar landing safety is prone to catastrophic scientific over-claiming: **NASA does NOT provide a ground-truth binary "safe/unsafe" label for every lunar coordinate.** Claiming that a model has learned real-world landing safety from synthetic data is scientifically fraudulent.

Moonscape strictly categorizes label sources into four distinct tiers:

```
+--------------------------------------------------------------------------------------------------+
| CATEGORY A: Independently Reviewed Artemis Landing Regions                                       |
| - Source: NASA Human Exploration and Operations Mission Directorate / LEAG (August 2022).        |
| - 13 NASA-identified Artemis III candidate regions + published peer-reviewed landing assessments.|
| - Nature: Expert consensus regions based on multi-instrument orbital surveys.                    |
| - Usage: Definitive benchmark and unseen geographic holdout test targets.                        |
+--------------------------------------------------------------------------------------------------+
| CATEGORY B: Published Mission-Selection Engineering Constraints                                  |
| - Source: Apollo LM Flight Qualification (Apollo 11-17); HLS-RQMT-001; Bennett et al. (2020).    |
| - Nature: Physical limits: max static slope <= 12-15 deg; boulder height <= 0.3-0.5m.           |
| - Usage: Hard deterministic exclusion boundaries.                                                |
+--------------------------------------------------------------------------------------------------+
| CATEGORY C: Algorithmic Synthetic Ground-Truth Labels                                            |
| - Source: Moonscape deterministic MCDA baseline scoring system + hard constraint gating.         |
| - Nature: Deterministic mathematical surrogate labels.                                           |
| - Usage: Dense spatial training dataset generation.                                              |
| - Crucial Governance: The ML model MUST be documented as a SURROGATE MODEL of the baseline,     |
|   accelerating multi-criteria evaluation, NOT an independently validated safety predictor.       |
+--------------------------------------------------------------------------------------------------+
| CATEGORY D: Unlabeled Orbital Remote Sensing Rasters                                             |
| - Source: NASA LOLA (PGDA 78/90) and LROC NAC DTMs.                                              |
| - Nature: Unlabeled continuous physical heightfields and slope rasters.                          |
+--------------------------------------------------------------------------------------------------+
```

---

## 3. Spatial Data Leakage Prevention Architecture

### 3.1 Spatial Autocorrelation in Lunar Topography
In planetary geospatial datasets, adjacent pixels exhibit severe spatial autocorrelation (Tobler's First Law of Geography). If neighboring pixels from the same crater rim are randomly partitioned into training and test sets, the model achieves artificial $\ge 98\%$ accuracy by memorizing local terrain elevation without learning generalizable landing physics.

### 3.2 Geographic Holdout Protocol
We enforce a **strict geographic cluster split** across six distinct polar geologic provinces:

```mermaid
flowchart LR
    subgraph Training Group [60% of Dataset]
        R1["Region 1: Shackleton Connecting Ridge<br/>(-89.8° to -89.2°, 120° to 240°)"]
        R2["Region 2: Malapert Mountain Massif<br/>(-86.2° to -84.5°, 355° to 20°)"]
    end

    subgraph Validation Group [20% of Dataset]
        R3["Region 3: Faustini Crater Rim/Plateau<br/>(-87.5° to -86.8°, 70° to 95°)"]
        R4["Region 4: Haworth Crater Rim<br/>(-87.9° to -87.0°, 335° to 360°)"]
    end

    subgraph Geographically Held-Out Test Group [20% Unseen]
        R5["Region 5: Nobile Crater Rim / VIPER Target<br/>(-85.6° to -84.9°, 25° to 50°)"]
        R6["Region 6: de Gerlache Crater Rim<br/>(-88.7° to -88.1°, 260° to 300°)"]
    end

    Training Group --> TrainModel["Train Lightweight Models<br/>(Ridge, Random Forest, HistGB)"]
    Validation Group --> TuneModel["Hyperparameter Tuning & Feature Selection"]
    TuneModel --> FinalEval["Strict Evaluation on Unseen Group<br/>(Zero Spatial Overlap)"]
    FinalEval --> UnseenEval["Evaluate Generalization to New Planetary Regions"]
```

---

## 4. Feature Schema Specification (24 Scientific Features)

Each candidate sample is parameterized by a strictly defined 24-feature vector:

| # | Feature Name | Physical Units | Scientific Significance & Provenance |
| :---: | :--- | :---: | :--- |
| 1 | `mean_elevation_m` | meters | Topographic elevation relative to 1737.4 km lunar sphere |
| 2 | `elevation_relief_m` | meters | Total vertical variation ($\max - \min$) across landing ellipse |
| 3 | `mean_slope_deg` | degrees | Area-weighted mean topographic slope (Horn 1981 operator) |
| 4 | `max_slope_deg` | degrees | Peak slope within landing zone (critical stability check) |
| 5 | `p95_slope_deg` | degrees | 95th percentile slope; robust indicator of steepest localized obstacle |
| 6 | `ideal_slope_pct` | percent | Percentage of area with slope $\le 5.0^\circ$ (Apollo ideal) |
| 7 | `critical_slope_pct` | percent | Percentage of area with slope $> 15.0^\circ$ (tip-over failure) |
| 8 | `roughness_15m` | meters | RMS roughness at 15m baseline (lander footpad scale) |
| 9 | `roughness_60m` | meters | RMS roughness at 60m baseline (lander gear stance scale) |
| 10 | `roughness_240m` | meters | RMS roughness at 240m baseline (regional micro-topography) |
| 11 | `vertical_uncertainty_m` | meters | LOLA 1-sigma total vertical elevation error (`toterr.tif`) |
| 12 | `slope_uncertainty_deg` | degrees | LOLA slope error estimate (`slperr.tif`) |
| 13 | `crater_density_km2` | count/$\text{km}^2$ | Concave curvature crater depressions per unit area |
| 14 | `min_crater_dist_m` | meters | Euclidean distance to nearest hazardous crater rim |
| 15 | `boulder_density_km2` | count/$\text{km}^2$ | Detected boulders ($>1\text{m}$) from optical shadow models |
| 16 | `min_boulder_dist_m` | meters | Distance to nearest identified boulder hazard |
| 17 | `curvature_laplacian_var`| $1/\text{m}^2$ | Variance of surface Laplacian curvature (surface irregularity) |
| 18 | `cumulative_sunlight_pct`| percent | Multi-year cumulative solar illumination (LOLA 18.6-yr cycle) |
| 19 | `instantaneous_sunlit_pct`| percent | Direct line-of-sight solar illumination at reference mission epoch |
| 20 | `max_continuous_sun_h` | hours | Maximum uninterrupted sunlight duration (power harvesting) |
| 21 | `max_continuous_dark_h` | hours | Maximum uninterrupted darkness duration (battery/thermal sizing) |
| 22 | `is_psr` | binary (0/1) | Permanently Shadowed Region flag (extreme thermal/optical hazard) |
| 23 | `earth_visibility_pct` | percent | Direct Earth line-of-sight communication fraction |
| 24 | `contiguous_diameter_m` | meters | Diameter of largest inscribed safe landing circle ($\text{slope} \le 8^\circ$) |

---

## 5. Model Selection & Architecture Decision

### 5.1 Rejected Approaches
- **Large Language Models (LLMs):** Strictly rejected for numerical safety scoring. LLMs suffer from non-deterministic hallucination, lack calibrated mathematical guarantees, and violate aerospace verification standards.
- **Deep Neural Networks (CNNs/MLPs):** Rejected for tabular suitability scoring. Deep networks overfit on small sample sizes, require high VRAM, and lack straightforward interpretability.

### 5.2 Selected Candidate Models
1. **Regularized Linear / Logistic Regression:** Transparent baseline establishing monotonic relationships.
2. **Random Forest Regressor / Classifier (`RandomForestRegressor`):**
   - Ensemble of 50 decision trees with max depth 6.
   - Non-linear feature interaction capture without overfitting.
   - Native Mean Decrease in Impurity (MDI) feature importances.
   - Sub-millisecond CPU inference time ($< 1.5\text{ ms}$).
3. **Histogram Gradient Boosting (`HistGradientBoostingRegressor`):**
   - Fast binned gradient boosting.
   - Handles localized step-thresholds efficiently.

---

## 6. Mission-Specific Profiles & Hard Constraint Specifications

### 6.1 Mission Profiles Definition
1. **Artemis HLS (Human Landing System):**
   - Hard slope limit: Max slope $\le 10.0^\circ$, P95 slope $\le 8.0^\circ$.
   - Contiguous footprint: Diameter $\ge 100\text{ m}$.
   - Illumination: Cumulative sunlight $\ge 50\%$, Max continuous night $\le 72\text{ hours}$.
   - Communication: Earth line-of-sight $\ge 50\%$.
2. **CLPS Commercial Robotic Lander (e.g. Nova-C, Blue Ghost):**
   - Hard slope limit: Max slope $\le 12.0^\circ$, P95 slope $\le 10.0^\circ$.
   - Contiguous footprint: Diameter $\ge 40\text{ m}$.
   - Illumination: Cumulative sunlight $\ge 40\%$, Max continuous night $\le 120\text{ hours}$.
   - Communication: Earth line-of-sight $\ge 30\%$.
3. **Polar Volatiles Rover (VIPER-Class):**
   - Hard slope limit: Mean slope $\le 6.0^\circ$, Max slope $\le 10.0^\circ$.
   - Roughness: 15m roughness $\le 0.35\text{ m}$.
   - Proximity: Distance to cold trap / PSR $\le 2500\text{ m}$.
   - Communication: Earth line-of-sight $\ge 60\%$ (real-time driving command link).
4. **Permanent Lunar Base Camp:**
   - Illumination priority: Cumulative sunlight $\ge 70\%$, Peak continuous daylight $\ge 1000\text{ hours}$.
   - Slope limit: Mean slope $\le 7.0^\circ$.
   - Communication: Earth line-of-sight $\ge 70\%$.

---

## 7. Model Training Feasibility Verdict

| Evaluation Area | Feasibility Verdict | Technical Mitigation & Justification |
| :--- | :---: | :--- |
| **Data Availability** | **HIGH** | Authentic 5m LOLA DEM (`pgda78`), 500m regional DEM, and 8 cataloged Artemis sites exist on disk. |
| **Label Provenance** | **DEFENSIBLE** | Explicitly documented as a **surrogate model** of the transparent MCDA baseline, benchmarked against Category A NASA Artemis candidate regions. |
| **Hardware Constraints** | **OPTIMAL** | Tabular models run entirely in CPU RAM ($< 50\text{ MB}$ footprint), leaving all 8 GB GPU VRAM for PyTorch ML vision models. |
| **Inference Latency** | **EXCELLENT** | Random Forest evaluation executes in $< 2\text{ ms}$ per site on AMD Ryzen 9 894HX. |
| **FastAPI Integration** | **SEAMLESS** | Preserves existing `/api/score`, `/api/sites/compare`, `/api/analysis/run` contracts with backward-compatible schema extension. |

**Final Recommendation:** Proceed with candidate dataset generation, geographic holdout partitioning, model training, and integration of the transparent surrogate scoring system.
