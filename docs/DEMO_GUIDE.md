# MOONSCAPE LIVE TECHNICAL DEMONSTRATION GUIDE
**Interactive Mission Simulation, Landing Site Suitability & Scientific Explainer**
**System Profile:** AMD Ryzen 9 894HX | 16 GB RAM | NVIDIA RTX 5070 GPU | Windows 11  
**Target Audience:** Mission Planners, Planetary Scientists, Aerospace Engineers, and Stakeholders

---

## 1. Quick Start & Local Execution

Both the backend and frontend run locally on your laptop without requiring external cloud servers or mandatory internet connectivity.

### Step 1: Start the FastAPI Backend
Open a PowerShell terminal in the repository root:
```powershell
cd D:\MoonScape
.\.venv\Scripts\Activate.ps1
python -m uvicorn Backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Backend URL:** [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

### Step 2: Start or Open the Frontend
Open a second PowerShell terminal:
```powershell
cd D:\MoonScape\Frontend
python -m http.server 3000
```
- Open Google Chrome or Microsoft Edge and navigate to: **[http://localhost:3000](http://localhost:3000)**

---

## 2. UI Layout & Architecture Overview

The Moonscape interface is structured into dedicated operational mission-planning panes:

```
+----------------------------------------------------------------------------------------------------+
| MOONSCAPE: Lunar South Pole Landing Site Evaluation & Mission Simulation Tool                       |
| Status: SYSTEM ONLINE (Green Badge)   |   NASA Dataset Coverage: PGDA 78 (5m) + PGDA 90 (20m)      |
+----------------------------------------------------------------------------------------------------+
|  LEFT PANEL: MISSION CONTROLS & GIS MAP      |  RIGHT PANEL: SCIENTIFIC RESULTS & SIMULATION      |
|  1. Demo Scenario Quick Buttons              |  1. Topographic Measurement & Uncertainty Card      |
|     - Scenario 1: Favorable Site (Shackleton)|  2. Hazard Detection & Apollo Validation Caveats   |
|     - Scenario 2: Severe Hazard (Faustini)   |  3. Temporal Sun & Earth Visibility Time-Series     |
|     - Scenario 3: Coverage Boundary (-78.5°) |  4. Automated Contiguous Landing Zone Detection     |
|  2. Interactive Polar Stereographic Canvas   |  5. Preliminary Suitability Scoring (MCDA + ML)    |
|     - Latitudes -90° to -80°, 8 Radials      |  6. Multi-Site Candidate Comparison Table           |
|     - Layer Switch: Elevation/Slope/Sunlight |  7. Grounded AI Scientific Assistant & Presets      |
|  3. Mission Architecture Profile Selector   |  8. Structured Scientific Report Exporter (PDF/JSON)|
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Step-by-Step Live Demonstration Script

### Act 1: System Health & Real-Time NASA Coverage
1. Show the top status bar:
   - Point out the glowing **System Operational** indicator verifying FastAPI connection.
   - Point out the **NASA Coverage Badge**: dynamically reflects installed LOLA 5m/pixel (PGDA 78) and 20m/pixel (PGDA 90) polar rasters.
2. Change the latitude in the input box to `-75.00`:
   - Watch the coverage badge immediately turn red with: *"Coordinate outside lunar South Pole (-90° to -80°)"*.
   - Explain to stakeholders that Moonscape enforces strict geodetic boundaries to prevent invalid spatial projections.

---

### Act 2: Interactive Lunar South Pole Canvas GIS
1. Reset coordinates by clicking on the **Lunar Map Canvas**:
   - Click near the center (South Pole, $-90.0^\circ$). Notice the crosshairs instantly follow your click, extracting exact $(\text{lat}, \text{lon})$ coordinates.
2. Use the **Map Layer Switcher** dropdown:
   - Select **LOLA High-Res Slope**: Displays steep crater rims highlighted in stark contrast to smooth ridge crests.
   - Select **Mean Solar Illumination**: Shows permanently shadowed regions (PSRs) inside Shackleton and Faustini craters alongside high-insolation connecting ridges.
3. Hover over candidate markers (Site 01, Site 04, Site 07) to view instant coordinate tooltips.

---

### Act 3: Scenario 1 — Favorable Landing Site (Shackleton Connecting Ridge)
1. In the Quick Demo Scenarios bar, click **Scenario 1: Favorable (Shackleton Ridge)**:
   - Automatically populates coordinates: Latitude `$-89.44^\circ$`, Longitude `$222.50^\circ$`.
   - Triggers the complete analysis pipeline.
2. Inspect the **Topographic Measurements Card**:
   - **Mean Slope:** `$1.73^\circ$` (Gentle, well below the $5.0^\circ$ ideal landing limit).
   - **RMS Roughness:** `$0.10\text{m}$` (Smooth local regolith; minimal engine plume obstruction).
   - **Elevation:** `$+1958.3\text{m}$` (Prominent polar highland plateau).
   - **Instrument Uncertainty Box:** Highlight the displayed LOLA laser altimetry precision ($\pm 0.34\text{m}$ vertical uncertainty, $\pm 2.32^\circ$ slope precision).
3. Inspect **Hazard Detection**:
   - Shows detected micro-craters and rock anomalies.
   - Point out the explicit scientific banner reminding mission engineers that models trained on Apollo surface photography must be validated against orbital LROC NAC imagery.
4. Run the **Sun & Earth Visibility Simulation**:
   - Click **Run Simulation**: The SVG time-series chart generates two smooth curves:
     - **Gold Curve:** Solar elevation angle with yellow daylight shading.
     - **Cyan Curve:** Earth elevation angle above local horizon.
     - **Green Markers:** Combined Operations Windows (simultaneous power generation and direct-to-Earth communications).
   - Note the stats: `$86.4\%$` sunlight availability and continuous Earth visibility with low libration dipping.
5. Inspect **Automated Contiguous Landing Zone Detection**:
   - Click **Detect Zones**: Moonscape segments contiguous slope patches meeting the $40\text{m}$ diameter threshold. Top candidate zone displays a rank of #1 with suitability score $> 85$.
6. Inspect the **Preliminary Suitability Score**:
   - **Hard Constraint Status:** **PASSED** (all 7 engineering constraints satisfied).
   - **MCDA Baseline Score:** `$100.0 / 100$`.
   - **Tabular ML Surrogate Prediction:** Active with sub-5ms inference and Monte Carlo uncertainty intervals.

---

### Act 4: Scenario 2 — Severe Hazard / Disqualification (Faustini Inner Wall)
1. In the Quick Demo Scenarios bar, click **Scenario 2: Hazard Disqualified (Faustini)**:
   - Automatically populates coordinates: Latitude `$-89.75^\circ$`, Longitude `$120.00^\circ$`.
2. Inspect the Results:
   - **Mean Slope:** `$21.50^\circ$`.
   - **Hard Constraint Gating:** Immediately flags **VIOLATED**.
   - **Violation Message:** *"Topographic slope (21.50°) exceeds universal Apollo/Artemis structural tip-over limit (15.00°)."*
   - **Suitability Score:** Severely penalized and capped at `$\le 35.0 / 100$`; classified as **"Disqualified (Safety Threshold Exceeded)"**.
   - **Scientific Takeaway:** Moonscape's hard mission constraints cannot be bypassed by high solar illumination or scientific value; flight safety criteria strictly override weighted MCDA averages.

---

### Act 5: Scenario 3 — Coverage Boundary / Out-of-Bounds
1. In the Quick Demo Scenarios bar, click **Scenario 3: Coverage Boundary (-78.5°)**:
   - Automatically populates coordinates: Latitude `$-78.50^\circ$`, Longitude `$45.00^\circ$`.
2. Observe System Resilience:
   - Dataset coverage badge indicates: *"Coordinate outside lunar South Pole (-90° to -80°)"*.
   - Point queries report `is_valid_point = false` with an explanatory note.
   - The application handles boundary conditions gracefully without throwing 500 errors or freezing the UI.

---

### Act 6: Grounded AI Scientific Assistant
1. Scroll to the **AI Scientific Assistant** card.
2. Click any of the **6 Preset Benchmark Question Pills**:
   - **"Primary Hazards":** Explains slope tip-over risk, regolith roughness, and sub-pixel boulders.
   - **"Earth Visibility":** Details lunar orbital libration ($\pm 8^\circ$) causing periodic terrain masking and the necessity for a $2^\circ$ RF multipath clearance margin.
   - **"1 Month Later":** Explains how lunar orbital obliquity ($1.54^\circ$) changes subsolar latitude and shifts shadow corridors across craters.
   - **"Key Uncertainties":** References LOLA vertical shot precision ($\pm 1.5\text{m}$ at 20m, $\pm 0.34\text{m}$ at 5m) and finite-difference slope limitations.
   - **"Additional Datasets":** Recommends targeted LROC NAC stereo DEMs (0.5–2.0m/pixel) and Diviner thermal radiometry.
   - **"Ranking Rationale":** Explains why Shackleton Connecting Ridge outranks crater floors based on slope stability and sunlight harvesting.
3. Type a custom query in the prompt box: *"Explain why permanent shadow is both a scientific asset and an operational hazard."*
   - Click **Submit Inquiry**: Receives a scientifically grounded narrative directly synthesizing backend data.

---

### Act 7: Multi-Site Comparative Trade-off Analysis
1. Scroll to the **Multi-Site Comparison** card.
2. Click **Run Multi-Site Comparison**:
   - Evaluates three candidate landing regions side-by-side:
     1. **Shackleton Connecting Ridge (Site 01)**
     2. **Malapert Mountain (Site 04)**
     3. **Nobile Rim 1 (Site 07)**
   - Displays comparative metrics across mean slope, roughness, illumination percentage, and Earth line-of-sight.
   - Highlights the top-ranked recommendation according to the active mission architecture profile.

---

### Act 8: Exporting Structured Scientific Reports
1. In the Report Export card, click **View Structured JSON Report**:
   - Opens the machine-readable JSON representation containing full metadata, raw measurements, MCDA subscores, and safety caveats.
2. Click **Download PDF Report**:
   - Triggers server-side PDF compilation via ReportLab.
   - Downloads a multi-page, formatted publication document (`moonscape_report_ANL-XXXX.pdf`) complete with:
     - Official report title, generated timestamp, and unique Analysis UUID.
     - Geodetic coordinates and physical analysis radius.
     - Topographic slope, roughness, and elevation breakdown.
     - Solar illumination and Earth comm visibility statistics.
     - Hazard detection summary and Apollo validation caveats.
     - Full MCDA subscore table with weights and directions of preference.
     - Prominent scientific screening disclaimer.

---

## 4. Troubleshooting & FAQ for Presenters

- **Q: Does the demo require internet access?**  
  *A:* No. All DEM sampling, ephemeris propagation, ML inference, and AI explanations run locally via offline deterministic rule engines and local model artifacts.
- **Q: How fast does the application respond?**  
  *A:* Point queries complete in $< 15\text{ms}$ (sub-millisecond when cached). Full 14-day temporal simulations complete in $< 100\text{ms}$. Tabular ML inference runs on CPU in $< 3\text{ms}$.
- **Q: Is the GPU required?**  
  *A:* No. The tabular Random Forest model runs efficiently on CPU threads, leaving your NVIDIA RTX 5070 GPU VRAM entirely free for heavy computer vision tasks or external local LLMs.
- **Q: Can we change spacecraft landing limits?**  
  *A:* Yes. Use the **Mission Profile** dropdown to toggle between Artemis HLS, CLPS Cargo Lander, Polar Rover, and Base Camp Staging. The hard constraints and scoring weights update immediately.
