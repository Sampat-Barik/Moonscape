# Model Card — Moonscape Lunar Landing Suitability Surrogate Model

**Model Identifier:** `landing_suitability_rf_v2`  
**Version:** `2.0.0`  
**Type:** Tabular Gradient-Boosted Decision Tree Regression (Surrogate Model)  
**Date:** November 2026  
**Standards Compliance:** NASA Planetary Data System (PDS), HLS-RQMT-001 Guidelines  

---

## 1. Model Details

- **Developer:** Moonscape Planetary Geospatial & Machine Learning Engineering Team.
- **Model Family:** Histogram-based Gradient Boosting Regressor (`HistGradientBoostingRegressor`).
- **Framework:** Python 3.14 / scikit-learn.
- **Artifact Files:**
  - Binary Estimator: `Backend/data/models/landing_suitability_rf_v2.joblib`
  - Metadata & Governance: `Backend/data/models/landing_suitability_rf_v2.meta.json`
- **Trained Features:** 24 standardized lunar topographical, morphological, illumination, and communication features.
- **Inference Runtime:** Local CPU (< 2ms per query; < 15ms with 50-sample Monte Carlo uncertainty propagation).

---

## 2. Intended Use & Scope

### 2.1 Primary Intended Use
- **Preliminary Engineering Screening:** Rapidly scoring candidate touchdown locations across the lunar South Pole ($[-90^\circ, -84^\circ]\text{ Latitude}$) within the Moonscape web interface.
- **Interactive Multi-Criteria Exploration:** Instantaneous feedback during user parameter tuning, contour dragging, and landing ellipse radius adjustments.
- **Algorithmic Surrogate Acceleration:** Approximating the deterministic multi-criteria decision analysis (MCDA) surface at $>1000\times$ the speed of full raster polygon flood-filling and ray-traced shadow simulations.

### 2.2 Out-of-Scope & Misuse Notice
> [!CAUTION]
> **NOT CERTIFIED FOR HUMAN SPACEFLIGHT LANDING CLEARANCE**
> 
> This model is an **algorithmic surrogate** designed for software visualization and preliminary site triage. It does **NOT** constitute NASA, ESA, ISRO, or JAXA flight qualification, nor does it guarantee touchdown survivability.
> 
> Prohibited applications:
> - Real-time terminal hazard detection and avoidance (HDA) during active descent.
> - Autonomous guidance, navigation, and control (GNC) target selection.
> - Extrapolation to equatorial or far-side lunar mare terrains without retrained regional models.

---

## 3. Factors, Features & Input Validation

### 3.1 Input Schema (24 Features)
The model accepts a standardized 24-dimensional feature vector:
1. `mean_elevation_m` (LOLA datum elevation)
2. `elevation_relief_m` ($z_{\max} - z_{\min}$)
3. `mean_slope_deg` (Horn 1981 slope)
4. `max_slope_deg` (Peak slope)
5. `p95_slope_deg` (95th percentile slope)
6. `ideal_slope_pct` ($\le 5^\circ$)
7. `critical_slope_pct` ($> 15^\circ$)
8. `roughness_15m` (RMS roughness at 15m)
9. `roughness_60m` (RMS roughness at 60m)
10. `roughness_240m` (RMS roughness at 240m)
11. `vertical_uncertainty_m` (LOLA radial error)
12. `slope_uncertainty_deg` (Slope error margin)
13. `crater_density_km2` (Detected basins per $\text{km}^2$)
14. `min_crater_dist_m` (Distance to nearest rim)
15. `boulder_density_km2` (Sub-meter rock hazard proxy)
16. `min_boulder_dist_m` (Distance to nearest boulder)
17. `curvature_laplacian_var` (Surface irregularity)
18. `cumulative_sunlight_pct` (Multi-year sunlight)
19. `instantaneous_sunlit_pct` (Epoch sunlit area)
20. `max_continuous_sun_h` (Max daylight hours)
21. `max_continuous_dark_h` (Max darkness hours)
22. `is_psr` (Permanently Shadowed Region flag)
23. `earth_visibility_pct` (Direct comms LOS)
24. `contiguous_diameter_m` (Safe landing circle)

### 3.2 Strict Input Validation & Missing Data Policy
- **Refusal on Missing Slope:** If `mean_slope_deg` is omitted, the service refuses prediction, returning `status: "insufficient_data"` and score `0.0`. Slope is non-negotiable for landing stability.
- **Zero Preservation:** Valid physical zeros (e.g., $0.0^\circ$ slope on flat plateaus, $0.0\%$ sunlight in PSRs, $0.0\text{ boulders}/\text{km}^2$) are preserved exactly and never replaced with non-zero defaults.
- **Completeness Reporting:** The model returns `data_completeness_pct` detailing the fraction of authentic observed features versus estimated parameters.

### 3.3 Hard Constraint Gating
Before returning a prediction, the model evaluates physical engineering limits (Apollo LM / Artemis HLS-RQMT-001):
- **Tip-over Limit:** If mean slope exceeds $15.0^\circ$, the score is strictly capped at $\le 35.0$ and classification is forced to `"disqualified"`.
- **Footprint Diameter:** If contiguous diameter is below mission requirements ($<100\text{ m}$ for Artemis HLS), the site is marked as disqualified regardless of high solar illumination.

---

## 4. Quantitative Performance Summary

Trained on 88 samples across Shackleton and Malapert; validated on 36 samples across Faustini and Haworth; tested on 34 completely held-out samples across Nobile and de Gerlache.

```
Metric                          Validation Set      Held-out Test Set
──────────────────────────────────────────────────────────────────────
Coefficient of Determination R²     0.8688              0.8747
Mean Absolute Error (MAE)           0.716 pts           1.225 pts
Root Mean Square Error (RMSE)       2.299 pts           2.862 pts
Spearman Rank Correlation (ρ)       0.6300              0.8579
NDCG @ 5 Ranking Fidelity           1.0000              1.0000
Spatial Data Leakage                0.00% (Verified)    0.00% (Verified)
──────────────────────────────────────────────────────────────────────
```

---

## 5. Explainability & Uncertainty Propagation

### 5.1 Local Feature Attribution
For every inference request, the service computes normalized deviations against nominal lunar reference baselines weighted by feature importances:
- `top_positive_features`: Identifies local topographical advantages (e.g., low slope, high solar illumination).
- `top_risk_features`: Flags landing hazards (e.g., proximity to crater rims, steep slope tails, high roughness).

### 5.2 Monte Carlo Noise Propagation
The service perturbs input measurements across documented instrument standard deviations ($N=50$ draws):
- Elevation noise: $\pm 1.5\text{ m}$ ($1\sigma$ LOLA radial error)
- Slope error: $\pm 1.2^\circ$
- Roughness error: $\pm 0.05\text{ m}$
- Illumination simulation error: $\pm 2.0\%$

**Outputs:**
- `uncertainty_score_std`: Score standard deviation ($\sigma$).
- `confidence_interval_95`: Empirical $[2.5\%, 97.5\%]$ confidence interval.
- `ranking_stability`: Categorized as `"high"` ($\sigma < 2.5$), `"moderate"` ($2.5 \le \sigma < 6.0$), or `"low"` ($\sigma \ge 6.0$).

---

## 6. Ground-Truth Requirements for True Flight Clearance Models

To build a flight-certified touchdown safety model rather than an MCDA surrogate, future mission systems require:

1. **6-DOF Multi-Body Touchdown Dynamics:**
   - Monte Carlo simulation of lander touchdown kinematics (mass, inertia tensor, leg stiffness, damper stroke, crushable aluminum honeycomb energy absorption).
   - Dynamic tip-over stability boundaries under $1.62\text{ m/s}^2$ gravity and regolith shear failure.
2. **Sub-Meter Resolution Stereo Topography:**
   - Stereo digital elevation models at $0.5\text{ m/pixel}$ (LROC NAC / Chandrayaan-2 OHRC) to resolve hazards between $0.3\text{ m}$ and $1.5\text{ m}$.
3. **Calibrated Historical Flight Telemetry:**
   - Touchdown acceleration and footpad penetration telemetry from Apollo LM 11–17, Surveyor 1–7, Chang'e 3–6, Chandrayaan-3 Vikram, and SLIM.
