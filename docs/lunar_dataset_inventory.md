# NASA Lunar Dataset Inventory — Moonscape Platform

This inventory documents all verified NASA and international planetary science datasets integrated or cataloged within the Moonscape platform.

---

## 1. NASA PGDA Product 90 — Regional South Pole Foundation (80m/px)

- **Dataset Name:** High-Resolution Topography for the Lunar South Pole (LOLA 20mpp/80mpp Product Suite)
- **Product ID:** NASA-PGDA-90
- **Mission:** Lunar Reconnaissance Orbiter (LRO)
- **Instrument:** Lunar Orbiter Laser Altimeter (LOLA)
- **Official Source Page:** https://pgda.gsfc.nasa.gov/products/90
- **Base Download Directory:** https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/
- **Spatial Coverage:** Latitude -90.0° to -80.0° (Full Lunar South Polar Disk)
- **Grid Resolution:** 80.0 meters/pixel (interpolated from 20m/pixel adjusted track solution)
- **Coordinate Reference System (CRS):** Lunar South Polar Stereographic
- **Reference Frame:** MOON_ME associated with DE421 ephemeris (Mean Earth / Polar Axis)
- **Reference Sphere:** Radius $R = 1,737,400.0\text{ m}$
- **Longitude Convention:** East positive, 0° to 360° or -180° to +180° (tangent at -90°S, central meridian 0°)
- **Units:** Elevation in meters relative to reference sphere; Slopes in degrees; Counts in integer observations; Errors in meters/degrees.
- **Nodata Value:** `-32768.0` (standard LOLA missing data sentinel)
- **File Format:** Cloud-Optimized GeoTIFF (COG), LZW compressed, Byte-Range accessible (`Accept-Ranges: bytes`)
- **Scientific Purpose:** Regional terrain screening, macro-slope profiling, landing corridor safety bounds, and solar illumination modeling.
- **Data Quality & Limitations:** 80 m/pixel is suitable for macro-topographic analysis and regional slope stability. It is NOT sufficient by itself to detect small boulders ($< 1\text{ m}$) or certify terminal landing safety.
- **Uncertainty Products:** Provided with explicit per-pixel vertical error (`ERR.TIF`), effective spatial resolution (`EFFRES.TIF`), and slope uncertainty (`slperr.tif`).
- **Citation:** Barker, M.K., Mazarico, E., Neumann, G.A., Zuber, M.T., et al. (2021). *Improved LOLA elevation maps for south pole landing sites: Error estimates and their impact on illumination conditions.* Planetary and Space Science, 203, 105119. doi:10.1016/j.pss.2020.105119.
- **Usage Conditions:** Open NASA Planetary Data System (PDS) public domain.
- **Access Method:** Local verified storage (Tier 1 & Tier 2) + on-demand HTTP byte-range reading (Tier 3).

### Key Files in Profile B (Total ~1.21 GB):
| File Name | Description | Size | Direct URL |
| :--- | :--- | :--- | :--- |
| `LDEM_80S_80MPP_ADJ.TIF` | Elevation Digital Elevation Model (DEM) | 180.40 MB | https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF |
| `LDSM_80S_80MPP_ADJ.TIF` | Topographic Slope Map (degrees) | 230.40 MB | https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDSM_80S_80MPP_ADJ.TIF |
| `LDEC_80S_80MPP_ADJ.TIF` | LOLA Altimetric Observation Counts | 110.30 MB | https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEC_80S_80MPP_ADJ.TIF |
| `LDEM_80S_80MPP_ADJ_ERR.TIF` | Elevation Total RMS Uncertainty (meters) | 243.00 MB | https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ_ERR.TIF |
| `LDEM_80S_80MPP_ADJ_EFFRES.TIF` | Effective Spatial Resolution Map (meters) | 238.64 MB | https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ_EFFRES.TIF |
| `LDSM_80S_80MPP_ADJ_ERR.TIF` | Topographic Slope Uncertainty (degrees) | 238.49 MB | https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDSM_80S_80MPP_ADJ_ERR.TIF |

---

## 2. NASA PGDA Product 78 — High-Resolution Candidate Landing Sites (5m/px)

- **Dataset Name:** High-Resolution LOLA Topography for Lunar South Pole Sites
- **Product ID:** NASA-PGDA-78
- **Mission:** Lunar Reconnaissance Orbiter (LRO)
- **Instrument:** LOLA
- **Official Source Page:** https://pgda.gsfc.nasa.gov/products/78
- **Base Download Directory:** https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/
- **Selected Region:** **Site 01** (Shackleton Rim / Connecting Ridge candidate region, centered at -89.44° lat, 222.50° lon)
- **Grid Resolution:** 5.0 meters/pixel
- **Coordinate Reference System:** Lunar South Polar Stereographic ($R = 1,737,400\text{ m}$)
- **Reference Frame:** MOON_ME (DE421)
- **Nodata Value:** `-32768.0`
- **File Format:** Cloud-Optimized GeoTIFF, byte-range enabled.
- **Scientific Purpose:** Detailed regional approach analysis, micro-cold-trap identification, ridge-top navigation.
- **Scientific Limitations:** Although raster spacing is 5 m/pixel, ~90% of cells are interpolated between laser altimetry ground tracks. Effective resolution is constrained by cross-track gaps. Interpolation uncertainty must be read alongside the surface elevation.
- **Citation:** Barker et al. (2021), *Planetary and Space Science*, doi:10.1016/j.pss.2020.105119.

### Key Files for Site 01 (Total ~195 MB):
| File Name | Description | Size | Direct URL |
| :--- | :--- | :--- | :--- |
| `Site01_final_adj_5mpp_surf.tif` | 5m Elevation Surface DEM | 39.08 MB | https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_surf.tif |
| `Site01_final_adj_5mpp_slp.tif` | 5m Topographic Slope Map | 39.08 MB | https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_slp.tif |
| `Site01_final_adj_5mpp_ldec.tif` | 5m Observation Count Density | 39.08 MB | https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_ldec.tif |
| `Site01_final_adj_5mpp_toterr.tif` | 5m Elevation Total Uncertainty | 39.08 MB | https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_toterr.tif |
| `Site01_final_adj_5mpp_slperr.tif` | 5m Slope Angle Uncertainty | 39.08 MB | https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_slperr.tif |

---

## 3. NASA PGDA Product 104 — Enhanced Shape-from-Shading (SfS) Terrain

- **Dataset Name:** Shape-from-Shading High-Resolution Digital Elevation Models of Candidate Artemis Landing Sites
- **Product ID:** NASA-PGDA-104 / Zenodo Record 17954508
- **Mission:** LRO (LOLA + LROC NAC fusion)
- **Source Pages:** https://pgda.gsfc.nasa.gov/products/104 | https://zenodo.org/records/17954508
- **Methodology:** Multi-image photoclinometry (Shape-from-Shading) controlled to LOLA geodetic laser altimetry tracks.
- **Layers Available:** Enhanced DEM, Vector Ruggedness Measure (VRM), Multiscale Slope, Sun-visibility illumination fractions.
- **Archive Size:** 26.6 GB full repository.
- **Phase 2 Status:** Cataloged with footprint discovery adapter. Individual regional packages are fetched on-demand with explicit user confirmation.
- **Citation:** Barker, M.K., et al. (2023), *Shape-from-Shading Topography of the Lunar South Pole*, NASA GSFC.

---

## 4. NASA LRO Diviner Lunar Radiometer Experiment — Thermal Environment

- **Dataset Name:** Diviner Lunar Radiometer Experiment Polar Cumulative Products (PCP)
- **Product ID:** LRO-L-DLRE-4-PCP-V1.0
- **Mission:** Lunar Reconnaissance Orbiter
- **Instrument:** Diviner Lunar Radiometer (Channels 3 through 9 infrared)
- **Official Sources:** https://pds-geosciences.wustl.edu/missions/lro/diviner.htm | https://www.diviner.ucla.edu/data
- **Spatial Coverage:** Poleward of 80°S
- **Grid Resolution:** 240 m to 500 m Polar Stereographic grids
- **Units:** Temperature in Kelvin ($K$)
- **Missing Value Sentinel:** `-9999.0`
- **Scientific Significance:** Delineates Permanently Shadowed Regions (PSRs) maintaining cryogenic temperatures ($< 110\text{ K}$) necessary for water-ice stability, and micro-cold traps ($< 50\text{ K}$) preserving volatile methane/ammonia.
- **Limitations:** Temperatures are binned historically over multi-year diurnal and draconic precession cycles; they represent aggregated physical brightness temperatures, not real-time conditions.
- **Citation:** Paige, D.A., et al. (2010), *Diviner Lunar Radiometer Experiment*, Space Science Reviews, 150(1-4), 125-160.

---

## 5. NASA LROC WAC — Regional Polar Visual Context

- **Dataset Name:** Lunar Reconnaissance Orbiter Camera (LROC) Wide Angle Camera South Pole Mosaic
- **Product ID:** LROC-WAC-GLR-SOUTHPOLE
- **Instrument:** LROC Wide Angle Camera (WAC)
- **Official Source:** https://data.lroc.im-ldi.com/lroc/view_rdr/WAC_GLOBAL/
- **Resolution:** 100 m/pixel to 400 m/pixel Polar Stereographic visual reflectance
- **Scientific Purpose:** Visual morphological context, albedo patterns, and macro-crater rim visual navigation.
- **Scientific Limitations:** Optical reflectance (albedo) does NOT measure elevation or hazard clearance. Long polar shadows cast by grazing sunlight must not be confused with physical depressions.

---

## 6. NASA LROC NAC — High-Resolution Targeted Imagery & Stereo DTMs

- **Dataset Name:** LROC Narrow Angle Camera Digital Terrain Models (NAC DTMs)
- **Product ID:** LROC-NAC-DTM-RDR
- **Instrument:** LROC Narrow Angle Camera (0.5 m/pixel optical resolution)
- **Official Catalog:** https://data.lroc.im-ldi.com/lroc/view_rdr/SHAPEFILE_NAC_DTMS
- **Resolution:** 1.0 m to 2.0 m/pixel stereo-photogrammetric DEMs (where overlapping stereo pairs exist)
- **Scientific Purpose:** Terminal hazard avoidance, boulder count verification, meter-scale landing pad site survey.
- **Scientific Limitations:** NAC DTMs cover only specific targeted swathes (non-global). Areas lacking stereo coverage or falling inside deep shadows have no elevation solution.
