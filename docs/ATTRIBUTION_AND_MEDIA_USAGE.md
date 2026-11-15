# MoonScape — Scientific Attribution, Data Licensing & Media Usage Policy

**Document ID:** POL-ATTR-001  
**Project:** MoonScape (Autonomous Lunar South Pole Landing Site Analysis Platform)  
**Classification:** Scientific Provenance, Intellectual Property & Legal Licensing Documentation  
**Date of Audit:** November 15, 2026  
**Status:** **ACTIVE & AUDITED**  

---

## 1. Executive Summary & Purpose

MoonScape is an independent planetary geospatial analysis and mission feasibility software suite developed for academic research, computational geomorphology, and preliminary landing site decision support for the lunar South Pole.

To maintain uncompromising scientific transparency and legal compliance, this document specifies:
1. The governing legal framework and intellectual property rights for all NASA, JPL, and PDS datasets utilized within MoonScape.
2. Instrument-level citations, acknowledging the principal investigator institutions and data repositories.
3. Open-source software licenses for the client, backend, machine learning, and visualization dependencies.
4. Font and design typography licensing terms.
5. Mandatory institutional non-affiliation and flight safety disclaimers.

---

## 2. NASA Open Data Policy & U.S. Government Works

### 2.1 Public Domain Status of NASA Works (17 U.S.C. § 105)
Under Title 17, Section 105 of the United States Code, works created by officers and employees of the United States Government—including the National Aeronautics and Space Administration (NASA)—as part of their official duties are not eligible for domestic copyright protection and reside in the public domain.

NASA's official data policy explicitly encourages the unrestricted scientific, educational, and commercial redistribution, reformatting, and algorithmic analysis of planetary observations:
> *"NASA data, imagery, and software products are made openly available to the worldwide scientific community and the general public to stimulate innovation, discovery, and scientific advancement."*

MoonScape complies fully with this mandate by:
- Ingesting and processing official NASA planetary data without altering instrument calibration metrics.
- Accompanying all rendered data products with authoritative citations to the original instrument principal investigators.
- Preserving full traceability back to official NASA Planetary Data System (PDS) archive products.

### 2.2 NASA Insignia & Identity Guidelines (14 CFR § 1212.100)
Pursuant to Title 14 of the Code of Federal Regulations (14 CFR § 1212.100):
- MoonScape does **not** display the NASA "Meatball" insignia, the NASA "Worm" logotype, or official Artemis Program brand identifiers as project trademarks.
- Mention of NASA, GSFC, JPL, LRO, and other project designations is strictly confined to factual scientific attribution, geodetic citation, and data source documentation.
- The MoonScape user interface contains no graphical elements that could falsely imply official government sponsorship, contractual partnership, or formal endorsement by the United States Government.

---

## 3. Planetary Mission Data Provenance & Instrument Citations

### 3.1 Lunar Orbiter Laser Altimeter (LOLA)
- **Host Mission:** Lunar Reconnaissance Orbiter (LRO)
- **Principal Investigator Institution:** NASA Goddard Space Flight Center (GSFC), Greenbelt, MD
- **Data Repository:** PDS Geosciences Node (Washington University in St. Louis)
- **Products Utilized:**
  1. `LDEM_80S_80MPP_ADJ` (Product 90) — Regional polar stereographic digital elevation model (80 m/px, 80°S to 90°S).
  2. `Site01_final_adj_5mpp` (Product 78) — High-resolution Artemis Candidate Site 01 terrain, slope, and error GeoTIFFs (5 m/px).
- **Attribution Citation:**
  > Smith, D. E., Zuber, M. T., Neumann, G. A., Lemoine, F. G., Mazarico, E., Torrence, M. H., McGarry, J. F., Rowlands, D. D., Head, J. W., Duxbury, T. H., Aharonson, O., Lucey, P. G., Robinson, M. S., Barnouin, O. S., Cavanaugh, J. F., Sun, X., Liiva, P., Mao, D., Smith, J. C., & Bartels, A. E. (2010). *Initial findings from the Lunar Orbiter Laser Altimeter (LOLA) on the Lunar Reconnaissance Orbiter (LRO) mission.* Geophysical Research Letters, 37(18), L18204. https://doi.org/10.1029/2010GL043751
  > 
  > Barker, M. K., Mazarico, E., Neumann, G. A., Zuber, M. T., Haruyama, J., & Smith, D. E. (2021). *Improved LOLA elevation models for Artemis candidate landing sites.* Planetary and Space Science, 203, 105119. https://doi.org/10.1016/j.pss.2020.105119

### 3.2 Lunar Reconnaissance Orbiter Camera (LROC)
- **Host Mission:** Lunar Reconnaissance Orbiter (LRO)
- **Principal Investigator Institution:** Arizona State University (ASU) School of Earth and Space Exploration, Tempe, AZ
- **Products Utilized:**
  1. `WAC_GLOBAL_E000N0000` — Wide Angle Camera morphologic 100 m albedo mosaic, sub-sampled to 2048×1024 for Three.js global rendering (`lroc_color_2k.jpg`).
  2. `NAC Polar Stereo DTM Archive` — Targeted sub-meter Narrow Angle Camera stereo digital terrain models referenced via QuickMap API integration.
- **Attribution Citation:**
  > Robinson, M. S., Brylow, S. M., Tschimmel, M., Humm, D., Lawrence, S. J., Thomas, P. C., Denevi, B. W., Bowman-Cisneros, E., Zerr, J., Ravine, M. A., Caplinger, M. A., Ghaemi, F. T., Schaffner, J. A., Malin, M. C., Mahanti, P., Bartels, A., Anderson, J., Tran, T. N., Eliason, E. M., & Turtle, E. P. (2010). *Lunar Reconnaissance Orbiter Camera (LROC) Instrument Overview.* Space Science Reviews, 150(1–4), 81–124. https://doi.org/10.1007/s11214-010-9634-2
  > 
  > Henriksen, M. R., Manheim, M. R., Burns, K. N., Seybold, P., Chojnacki, M., & Robinson, M. S. (2017). *Extracting Topography from LROC Stereo Images.* Icarus, 283, 122–137. https://doi.org/10.1016/j.icarus.2016.05.012

### 3.3 JPL Horizons On-Line Ephemeris System & DE421/DE441 Kernels
- **Provider:** NASA Jet Propulsion Laboratory (JPL) Solar System Dynamics Group, California Institute of Technology, Pasadena, CA
- **Products Utilized:**
  1. DE421 / DE441 Development Ephemerides analytical orbital integration routines.
  2. Horizons REST Web API v2.0 (`https://ssd.jpl.nasa.gov/api/horizons.api`) for topocentric observer state vector queries.
- **Attribution Citation:**
  > Giorgini, J. D., Yeomans, D. K., Chamberlin, A. B., Chodas, P. W., Jacobson, R. A., Keesey, M. S., Lieske, J. H., Ostro, S. J., Standish, E. M., & Wimberly, R. N. (1996). *JPL's On-Line Solar System Data Service.* Bulletin of the American Astronomical Society, 28, 1158.
  > 
  > Folkner, W. M., Williams, J. G., Boggs, D. H., Park, R. S., & Kuchynka, P. (2014). *The Planetary and Lunar Ephemerides DE430 and DE431.* Interplanetary Network Progress Report, 42–196, 1–81.

### 3.4 NASA Scientific Visualization Studio (SVS Entry 4720)
- **Provider:** NASA Goddard Space Flight Center (GSFC) Scientific Visualization Studio, Greenbelt, MD
- **Product Utilized:** *CGI Moon Kit: Elevation and Albedo Mosaics* (SVS-4720).
- **Application:** 8-bit normalized height displacement map (`ldem_3_8bit.jpg`) used as a fragment shader lighting normal map on the Three.js spherical globe.
- **Terms:** Public Domain (NASA SVS Media Usage Guidelines).

### 3.5 NASA Solar System Treks (Moon Trek WMTS)
- **Provider:** NASA Solar System Exploration / Jet Propulsion Laboratory (JPL)
- **Product Utilized:** OGC Web Map Tile Service (WMTS) 1.0.0 for streaming lunar polar projection tiles.
- **Terms:** NASA Public Data API. Ingested tiles are cached locally via in-memory and disk LRU caches in `Backend/app/services/data_sources/moon_trek.py`.

---

## 4. Academic Literature & Design References

### 4.1 Lunar and Planetary Institute (LPI)
- **Provider:** Universities Space Research Association (USRA) / Lunar and Planetary Institute, Houston, TX
- **Reference:** *LPI Lunar South Pole Atlas* (Special Publication SP-2019-01).
- **Role in MoonScape:** Literature and nomenclature reference for candidate region boundaries, Permanently Shadowed Region (PSR) cold traps, and volatile deposit geological context.
- **Usage Notice:** Scientific reference only. No automated API queries or proprietary cartographic tiles are extracted from LPI servers.

### 4.2 Horn (1981) Finite-Difference Slope Operator
- **Reference:**
  > Horn, B. K. P. (1981). *Hill shading and the reflectance map.* Proceedings of the IEEE, 69(1), 14–47. https://doi.org/10.1109/PROC.1981.11918
- **Role in MoonScape:** Core mathematical algorithm implemented in `maths/` and `dem_service.py` to derive metric slope gradients from 8-neighbor DEM altitude matrices.

### 4.3 Moon 3D Map (`moon3dmap.com`)
- **Reference:** Public web application (`https://moon3dmap.com/en/lunar-south-pole/`).
- **Role in MoonScape:** Design inspiration for camera orbital constraints and coordinate picking UI ergonomics during early prototyping.
- **IP Integrity Declaration:** **Zero code, 3D meshes, shaders, or proprietary assets were copied from moon3dmap.com.** All MoonScape WebGL shaders, Three.js geometries, CesiumJS hooks, and terrain triangulation routines were authored independently.

---

## 5. Software & Technology Licensing Registry

MoonScape is built upon verified open-source libraries, each operating under permissive licensing:

| Package / Library | Version | Governing License | Project Role |
| :--- | :--- | :--- | :--- |
| **React** | 19.2 | MIT License | Declarative UI framework & state tree |
| **TypeScript** | 5.9 | Apache License 2.0 | Static typing & interface validation |
| **Three.js** | r187 | MIT License | 3D WebGL globe & physical DEM relief mesh |
| **CesiumJS** | 1.147 | Apache License 2.0 | Geodetic IAU lunar ellipsoid & coordinate maths |
| **Motion for React** | 14.14 | MIT License | Fluid physics animations & layout transitions |
| **Tailwind CSS** | 4.1 | MIT License | Monochromatic design tokens & layout engine |
| **FastAPI** | 0.115 | MIT License | Asynchronous scientific REST backend |
| **Pydantic** | 2.10 | MIT License | Strict numerical schema validation |
| **NumPy** | 2.1+ | BSD 3-Clause License | High-performance multi-dimensional array algebra |
| **SciPy** | 1.14+ | BSD 3-Clause License | Spatial KDTree search & finite convolutions |
| **Rasterio** | 1.4+ | BSD 3-Clause License | GDAL GeoTIFF parsing & projection math |
| **PyProj** | 3.6+ | MIT License | Cartographic transformations (`ESRI:104903`) |
| **Scikit-Learn** | 1.5+ | BSD 3-Clause License | Random Forest regressor for landing scoring |
| **PyTorch** | 2.5+ | Modified BSD License | Neural network runtime for hazard detection |
| **ONNX Runtime** | 1.19+ | MIT License | High-speed cross-platform model inference |
| **ReportLab** | 4.2+ | BSD License | Vector PDF compiler for mission dossiers |

---

## 6. Typography & Font Licensing

MoonScape utilizes four font families to maintain a documentary, aerospace aesthetic:

1. **Space Grotesk** — Florian Karsten (SIL Open Font License 1.1). Used for editorial titles, primary headings, and metric callouts.
2. **Inter** — Rasmus Andersson (SIL Open Font License 1.1). Used for running body prose, scientific descriptions, and narrative explanations.
3. **Rajdhani** — Indian Type Foundry (SIL Open Font License 1.1). Used for condensed uppercase button labels, telemetry pills, and table headers.
4. **IBM Plex Mono** — IBM Corporation (SIL Open Font License 1.1). Used for geospatial coordinates, product IDs, file paths, and mathematical notation.

*SIL Open Font License Summary:* Fonts may be used, modified, and redistributed freely in digital products, provided they are not sold individually as standalone font files.

---

## 7. Institutional Disclaimers & Flight Safety Notice

### 7.1 Non-Endorsement Notice
> **MOONSCAPE IS AN INDEPENDENT RESEARCH AND MISSION MODELING SYSTEM CREATED FOR ACADEMIC, FEASIBILITY, AND EDUCATIONAL PURPOSES.**  
> It is not affiliated with, sponsored by, authorized by, or endorsed by the National Aeronautics and Space Administration (NASA), the European Space Agency (ESA), the Indian Space Research Organisation (ISRO), the Japan Aerospace Exploration Agency (JAXA), or any government aerospace contractor.

### 7.2 Decision Support & Flight Qualification Limitation
> The terrain elevation models, slope matrices, illumination simulations, and landing suitability scores generated by MoonScape represent **computational decision-support models based on public orbital data**.  
> They do not constitute certified flight safety qualification, landing trajectory validation, or real-time autonomous terrain relative navigation (TRN) solutions. Actual flight operations require certified spacecraft guidance, navigation, and control (GNC) systems, real-time hazard detection sensors (LiDAR/optical), and authorized mission control oversight.

---

## 8. Summary of Legal & Compliance Verification

| Compliance Requirement | Governing Regulation | Verification Status | Notes |
| :--- | :--- | :--- | :--- |
| **NASA Open Data** | 17 U.S.C. § 105 | **COMPLIANT** | Public domain altimetry & optical data used without distortion |
| **NASA Insignia Restrictions** | 14 CFR § 1212.100 | **COMPLIANT** | Zero official NASA logos or misleading Artemis trade dress |
| **PDS / Instrument Citations** | PDS Data Policy | **COMPLIANT** | Full formal citations provided for LOLA, LROC, and JPL |
| **Open Source Licensing** | MIT / BSD / Apache | **COMPLIANT** | All client and backend libraries operate under permissive licenses |
| **Font Intellectual Property** | SIL OFL 1.1 | **COMPLIANT** | Space Grotesk, Inter, Rajdhani, and IBM Plex Mono adhere to OFL |
| **Independent Status Notice** | Trademark Fair Use | **COMPLIANT** | Prominent disclaimer of non-affiliation on UI and PDF reports |

---

*Verified and sealed by the MoonScape Project Architecture and Scientific Attribution Team.*
