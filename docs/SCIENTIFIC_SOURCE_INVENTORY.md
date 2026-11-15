# MoonScape — Scientific Source Inventory & Data Provenance Registry

**Document ID:** SCI-SRC-INV-001  
**Project:** MoonScape (NASA Lunar South Pole Mission Site Analysis)  
**Authors:** Scientific Data Documentation Specialist, Senior Planetary GIS Specialist  
**Verification Date:** November 15, 2026  
**Status:** **AUDITED & OFFICIALLY VERIFIED**  

---

## 1. Inventory Classification Schema

Every scientific dataset, astronomical ephemeris service, optical mosaic, machine-learning artifact, and software framework in the MoonScape platform is classified into six rigorous operational categories:

- **Category A — Direct Scientific Computation:** Rasters, matrices, and analytical algorithms directly executed by Python scientific kernels (`Backend/app/services/`, `maths/`) to compute physical elevations, gradients, roughness, or visibility.
- **Category B — Visualization & Imagery:** Calibrated optical mosaics, bump maps, and historical photographic assets rendered by WebGL graphics engines (`Three.js`, `CesiumJS`) or UI layouts.
- **Category C — External Astronomical & Map Services:** Real-time web APIs and tile servers queried over HTTPS (`JPL Horizons API`, `Moon Trek WMTS`, `LROC QuickMap`).
- **Category D — Reference & Documentation:** Scientific publications, cartographic atlases, and design references consulted for validation boundaries.
- **Category E — Model Training & Evaluation:** Checkpoints, datasets, and feature matrices used for ML regression or computer vision inference.
- **Category F — Software & Visualization Frameworks:** Core runtime libraries and computational frameworks powering the full stack.

---

## 2. Master Scientific Source Registry

### Source 01: NASA LRO LOLA Product 90 Regional Polar DEM
- **Official Name:** Lunar Orbiter Laser Altimeter South Polar Digital Elevation Model (80m/pixel)
- **Organization:** NASA Goddard Space Flight Center (GSFC) / LRO Science Team / PDS Geosciences Node
- **Mission / Instrument:** Lunar Reconnaissance Orbiter (LRO) / Lunar Orbiter Laser Altimeter (LOLA)
- **Product ID:** `LDEM_80S_80MPP_ADJ` (Product 90)
- **Category:** **A. Direct Scientific Computation**
- **Integration Status:** **Actively Used** (Foundation raster loaded in `Backend/data/sample_dem.tif`, parsed by `dem_service.py` and `nasa_data.py`)
- **Data Type:** 32-bit floating point GeoTIFF elevation raster
- **Spatial Resolution:** $80.0\text{ meters per pixel}$
- **Geographic Coverage:** $80.0^\circ\text{S}$ to $90.0^\circ\text{S}$, $0.0^\circ$ to $360.0^\circ\text{E}$ (Lunar South Polar Stereographic `ESRI:104903`)
- **Use Case in MoonScape:** Baseline terrain elevation sampling, Horn (1981) finite-difference slope derivation, RMS surface roughness, and radial horizon obstacle ray-tracing.
- **Scientific Limitations:** Topographic features smaller than $80\text{ m}$ (sub-pixel boulder fields, micro-craters) are unobserved by this orbital laser altimeter profile.
- **Official URL:** https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF
- **Citation:** Smith, D. E., et al. (2010), "Initial findings from the Lunar Orbiter Laser Altimeter (LOLA) on the Lunar Reconnaissance Orbiter (LRO) mission", *Geophys. Res. Lett.*, 37, L18204, doi:10.1029/2010GL043751.
- **License / Terms:** NASA Open Data Policy (Public Domain).

---

### Source 02: NASA LRO LOLA PGDA Product 78 Candidate Landing Site Rasters
- **Official Name:** Artemis III Candidate Site High-Resolution Adjusted LOLA Elevation & Slope Models (Site 01 Shackleton Connecting Ridge)
- **Organization:** NASA GSFC / Barker et al. 2021 / Planetary Geodesy & Altimetry (PGDA)
- **Mission / Instrument:** Lunar Reconnaissance Orbiter (LRO) / LOLA
- **Product ID:** `Site01_final_adj_5mpp_surf`, `Site01_final_adj_5mpp_slp`, `Site01_final_adj_5mpp_ldec`, `Site01_final_adj_5mpp_toterr`, `Site01_final_adj_5mpp_slperr`
- **Category:** **A. Direct Scientific Computation**
- **Integration Status:** **Actively Used** (5 local GeoTIFFs installed in `Backend/data/lunar/raw/pgda78/`)
- **Data Type:** Multi-layer GeoTIFF rasters (Elevation, Slope, Count Density, Total Elevation Error, Slope Uncertainty)
- **Spatial Resolution:** $5.0\text{ meters per pixel}$
- **Geographic Coverage:** $89.20^\circ\text{S}$ to $89.75^\circ\text{S}$, $210.0^\circ\text{E}$ to $235.0^\circ\text{E}$
- **Use Case in MoonScape:** High-resolution candidate landing zone evaluation, micro-topography gradient analysis, 3D terrain relief mesh extraction (`POST /api/terrain/mesh`), and explicit uncertainty bounding.
- **Scientific Limitations:** High-resolution coverage bounded strictly to Artemis Candidate Site 01; other South Pole zones fall back to $80\text{ m}$ Product 90 DEM.
- **Official URL:** https://pgda.gsfc.nasa.gov/products/78
- **Citation:** Barker, M. K., et al. (2021), "Improved LOLA elevation models for Artemis candidate landing sites", *Planetary and Space Science*, 203, 105119, doi:10.1016/j.pss.2020.105119.
- **License / Terms:** NASA Open Data Policy (Public Domain).

---

### Source 03: NASA JPL DE421 / DE441 Ephemerides & Ephemeris Core
- **Official Name:** JPL Planetary and Lunar Ephemerides Development Ephemeris (DE421 / DE441)
- **Organization:** NASA Jet Propulsion Laboratory (JPL) / California Institute of Technology
- **Category:** **A. Direct Scientific Computation**
- **Integration Status:** **Actively Used** (Implemented in `maths/illumination_geometry.py`, `Backend/app/services/illumination.py`, and `Backend/app/services/terrain_horizon.py`)
- **Data Type:** Analytical topocentric vector astronomical models (subsolar coordinates, lunar libration angles, observer-target distance)
- **Spatial / Angular Accuracy:** $< 0.05^\circ$ orbital position uncertainty across 2024–2035 epochs
- **Geographic Coverage:** Global Moon surface to celestial targets (Sun target 10, Earth target 399 from lunar observer body 301)
- **Use Case in MoonScape:** Analytical solar elevation and azimuth angle propagation, sub-Earth line-of-sight tracking, synodic day calculation ($29.53\text{ d}$), and local terrain horizon shadow occultation.
- **Scientific Limitations:** Assumes spherical geometric horizon unless paired with radial DEM ray-tracing; atmospheric refraction is zero (vacuum body).
- **Official URL:** https://ssd.jpl.nasa.gov/planets/eph_export.html
- **Citation:** Folkner, W. M., et al. (2014), "The Planetary and Lunar Ephemerides DE430 and DE431", *IPN Progress Report*, 42-196.
- **License / Terms:** NASA JPL Open Access / Public Domain.

---

### Source 04: NASA LRO LROC Wide Angle Camera (WAC) Global Mosaic
- **Official Name:** Lunar Reconnaissance Orbiter Camera Global Morphologic 100m / 2K Map
- **Organization:** Arizona State University (ASU) / USGS Astrogeology Science Center / NASA GSFC
- **Mission / Instrument:** LRO / Lunar Reconnaissance Orbiter Camera (LROC) WAC
- **Category:** **B. Visualization & Imagery**
- **Integration Status:** **Actively Used** (Installed at `Frontend/public/assets/textures/lroc_color_2k.jpg` and `moon-2k.jpg`, used in Three.js `LunarMap.tsx` and `CinematicMoon.tsx`)
- **Data Type:** Calibrated equirectangular optical reflectance map ($2048 \times 1024$ pixels)
- **Spatial Resolution:** $\approx 5.5\text{ km/pixel}$ at equator; sub-sampled global mosaic
- **Geographic Coverage:** Global ($90^\circ\text{S}$ to $90^\circ\text{N}$, $-180^\circ$ to $+180^\circ$)
- **Use Case in MoonScape:** Macroscopic Three.js interactive Moon rendering, hero visual, and global basemap texturing.
- **Scientific Limitations:** Equirectangular projection exhibits extreme polar meridian pinching; purely photographic reflectance, not elevation or topography.
- **Official URL:** https://wms.lroc.asu.edu/lroc/view_rdr/WAC_GLOBAL
- **Citation:** Robinson, M. S., et al. (2010), "Lunar Reconnaissance Orbiter Camera (LROC) Instrument Overview", *Space Sci. Rev.*, 150, 81–124, doi:10.1007/s11214-010-9634-2.
- **License / Terms:** NASA Public Domain / LROC PDS Release.

---

### Source 05: NASA Scientific Visualization Studio (SVS Entry 4720) LOLA Bump Map
- **Official Name:** LRO LOLA Normalized Topographic Displacement Map
- **Organization:** NASA GSFC Scientific Visualization Studio (SVS)
- **Category:** **B. Visualization & Imagery**
- **Integration Status:** **Actively Used** (Installed at `Frontend/public/assets/textures/ldem_3_8bit.jpg`)
- **Data Type:** 8-bit grayscale normalized height displacement map
- **Use Case in MoonScape:** Subtle surface normal lighting bump map on Three.js global Moon spheres.
- **Scientific Limitations:** Visual approximation for lighting normals only; does not displace physical vertex geometry on the global sphere.
- **Official URL:** https://svs.gsfc.nasa.gov/4720/
- **Citation:** NASA Scientific Visualization Studio, "CGI Moon Kit", SVS Visual ID 4720, 2019.
- **License / Terms:** NASA Public Domain.

---

### Source 06: NASA JPL Horizons On-Line Ephemeris System API
- **Official Name:** JPL Horizons Web Application Programming Interface
- **Organization:** NASA Jet Propulsion Laboratory (JPL) Solar System Dynamics Group
- **Category:** **C. External Astronomical & Map Services**
- **Integration Status:** **Actively Integrated** (`Backend/app/services/ephemeris/horizons_client.py`, routed at `/api/ephemeris/query`)
- **Data Type:** HTTPS REST JSON API returning topocentric vector ephemeris (`coord@301`)
- **Temporal Resolution:** Configurable ($1\text{ h}$, $2\text{ h}$, $6\text{ h}$ steps)
- **Use Case in MoonScape:** Independent live astronomical verification of solar and Earth apparent azimuth, elevation, and range rate from lunar coordinates.
- **Official URL:** https://ssd.jpl.nasa.gov/api/horizons.api
- **Citation:** Giorgini, J. D., et al. (1996), "JPL's On-Line Solar System Data Service", *Bull. Am. Astron. Soc.*, 28, 1158.
- **License / Terms:** NASA JPL Open API.

---

### Source 07: NASA Solar System Treks (Moon Trek OGC WMTS)
- **Official Name:** NASA Solar System Treks Moon OGC Web Map Tile Service (WMTS)
- **Organization:** NASA / Jet Propulsion Laboratory (JPL) / Solar System Exploration
- **Category:** **C. External Astronomical & Map Services**
- **Integration Status:** **Actively Integrated** (`Backend/app/services/data_sources/moon_trek.py`, routed at `/api/external/moon-trek/tile/...`)
- **Data Type:** OGC WMTS 1.0.0 RESTful tile service (`IAU2000::30120` Polar Stereographic & `EPSG::104903` Equirectangular)
- **Use Case in MoonScape:** Streaming verified LROC WAC and LROC NAC map tiles directly into MoonScape's map layers with local LRU caching.
- **Official URL:** https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon
- **Citation:** NASA Solar System Treks Project, Jet Propulsion Laboratory, California Institute of Technology.
- **License / Terms:** NASA Public Data Service.

---

### Source 08: NASA LROC QuickMap & Targeted Stereo DTM Archive
- **Official Name:** LROC QuickMap & Targeted High-Resolution Stereo DTM Archive
- **Organization:** Arizona State University (ASU) / NASA LROC Science Operations Center
- **Category:** **C. External Astronomical & Map Services**
- **Integration Status:** **Actively Integrated** (`Backend/app/services/data_sources/lroc_service.py`, routed at `/api/external/lroc/coverage`)
- **Data Type:** Photogrammetric stereo DTM catalog and deep-linking engine
- **Spatial Resolution:** $1.0\text{ m} - 2.0\text{ m}$ per pixel
- **Use Case in MoonScape:** Automated coverage matching across 10 Artemis III candidate regions and direct QuickMap verification links.
- **Official URL:** https://quickmap.lroc.im-ldi.com/
- **Citation:** Henriksen, M. R., et al. (2017), "Extracting Topography from LROC Stereo Images", *Icarus*, 283, 122–137, doi:10.1016/j.icarus.2016.05.012.
- **License / Terms:** NASA / ASU Open Access.

---

### Source 09: Lunar and Planetary Institute (LPI) Lunar South Pole Atlas
- **Official Name:** LPI Lunar South Pole Atlas
- **Organization:** Universities Space Research Association (USRA) / Lunar and Planetary Institute
- **Category:** **D. Reference & Documentation**
- **Integration Status:** **Reference Only** (Consulted during site selection cataloging and PSR volatile inventory validation in `docs/`)
- **Notice:** Used as an authoritative planetary cartographic reference. No automated REST query is made to LPI servers.
- **Official URL:** https://www.lpi.usra.edu/lunar/lunar-south-pole-atlas/
- **Citation:** Universities Space Research Association (USRA), Lunar and Planetary Institute, Lunar South Pole Atlas.

---

### Source 10: Moon 3D Map (`moon3dmap.com`)
- **Official Name:** Moon 3D Map Interactive Lunar Atlas
- **Category:** **D. Reference & Documentation**
- **Integration Status:** **Design & Interaction Reference Only**
- **Notice:** Used as interaction layout inspiration during early UI prototyping. **No proprietary 3D models, textures, or code were copied or integrated into MoonScape.** All MoonScape 3D models are built from scratch with Three.js and CesiumJS.
- **Official URL:** https://moon3dmap.com/en/lunar-south-pole/

---

### Source 11: MoonScape Landing Suitability Model (`v2`)
- **Official Name:** MoonScape Multi-Criteria Random Forest Suitability Regressor
- **Organization:** MoonScape Scientific Machine Learning Core
- **Category:** **E. Model Training & Evaluation**
- **Integration Status:** **Actively Used** (`Backend/data/models/landing_suitability_rf_v2.joblib`, `Backend/app/services/ml/suitability_model_service.py`)
- **Model Architecture:** Scikit-Learn `RandomForestRegressor` (100 estimators, max depth 12)
- **Features (24):** Topographic slopes, surface roughness RMS across multiple baselines, solar illumination fractions, Earth LOS comms, and regional volatile accessibility.
- **Use Case in MoonScape:** Machine-learning landing site suitability inference complementing the rule-based MCDA scoring matrix.

---

### Source 12: Optical Crater & Boulder Hazard Detector (`luna_hazard_yolov8n`)
- **Official Name:** MoonScape YOLOv8 Nano Lunar Surface Hazard Detector
- **Organization:** MoonScape Computer Vision Core
- **Category:** **E. Model Training & Evaluation**
- **Integration Status:** **Actively Configured** (`Backend/data/models/luna_hazard_yolov8n.onnx` / `.pt`, `Backend/app/services/hazard_detection.py`)
- **Framework:** PyTorch / Ultralytics YOLOv8 / ONNX Runtime
- **Use Case in MoonScape:** Computer vision crater lip and surface boulder bounding-box detection on orbital optical frames.
- **Limitations:** Decision-support guidance only; uncalibrated optical imagery without pixel scale is explicitly flagged.
