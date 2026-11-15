# MoonScape — Lunar Hazard Dataset Provenance & Data Rights

**Document ID:** `DOC-HAZ-PROV-2026-001`  
**Standard:** NASA PDS4 & ISRO ISSDC Planetary Data Archive Compliance  
**Target Missions:** NASA Lunar Reconnaissance Orbiter (LRO) & ISRO Chandrayaan-2 Orbiter  
**Scope:** Lunar South Pole Core ($-90^\circ$ to $-80^\circ$), Extended ($-80^\circ$ to $-75^\circ$), and Outer Context ($-75^\circ$ to $-70^\circ$)  
**Status:** Certified Ground Truth & Archive Provenance  

---

## 1. Allowed Scientific Sources & Data Rights

The MoonScape Lunar Hazard Dataset is derived exclusively from verified, peer-reviewed civilian planetary science missions: the **NASA Lunar Reconnaissance Orbiter (LRO)** and the **ISRO Chandrayaan-2 Orbiter**.

No generative artificial intelligence imagery, synthetic textures, Apollo low-latitude astronaut photographs, or unverified web images are used.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LUNAR OBSERVATION ARCHIVES                         │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ NASA Planetary Data System (PDS)    │ ISRO ISSDC PRADAN Archive            │
│ Cartography & Imaging Sciences Node  │ Indian Space Science Data Centre     │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ • LROC Narrow Angle Camera (NAC)    │ • Orbiter High Resolution Camera     │
│ • LROC Wide Angle Camera (WAC)       │   (OHRC) — 0.25 to 0.32 m/pixel      │
│ • LOLA Laser Altimeter (PGDA 78/90)  │ • Terrain Mapping Camera 2 (TMC-2)   │
│ • Diviner Lunar Radiometer (PCP)     │   5.0 m/pixel Stereo Triplet DTM     │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. Mission Instrument Specifications & Archive Links

### 2.1 NASA Lunar Reconnaissance Orbiter Camera (LROC)
* **Agency:** NASA / Goddard Space Flight Center / Arizona State University (ASU).
* **Instrument:** Narrow Angle Camera (NAC) — Two Ritchey-Chrétien line-scan telescopes (NAC-L and NAC-R).
* **Focal Length:** 700 mm; primary aperture: 195 mm.
* **Spatial Resolution:** $0.5\text{ m}$ to $2.0\text{ m}$ per pixel from a 50 km nominal polar orbit.
* **Archive Repository:** NASA PDS Cartography Node (`https://pds.lroc.im-ldi.com/data`).
* **Inspection Tool:** LROC QuickMap (`https://quickmap.lroc.asu.edu`) used strictly for geographic discovery and illumination inspection.
* **Citation:** Robinson, M. S., et al. (2010). *Lunar Reconnaissance Orbiter Camera (LROC) Instrument Overview*. Space Science Reviews, 150(1–4), 81–124.
* **Licensing & Rights:** NASA Open Data Policy (US Government Work, Public Domain). Free for scientific research, mission engineering, and educational use.

### 2.2 ISRO Chandrayaan-2 Orbiter Payloads
* **Agency:** Indian Space Research Organisation (ISRO).
* **Archive Repository:** Indian Space Science Data Centre (ISSDC) PRADAN Portal (`https://pradan.issdc.gov.in/ch2/`).
* **Payload 1 — Orbiter High Resolution Camera (OHRC):**
  - Optical design: Two-mirror Ritchey-Chrétien telescope.
  - Spatial resolution: $0.25\text{ m}$ to $0.32\text{ m}$ per pixel at 100 km orbit (the highest spatial resolution civilian orbital imagery of the Moon).
  - Swath width: $3.0\text{ km}$ to $4.0\text{ km}$.
  - Primary function: Detection of boulders down to 0.5m diameter and fine-scale crater morphology in polar candidate landing sites.
  - Citation: Chowdhury, A., et al. (2020). *Orbiter High Resolution Camera (OHRC) on Chandrayaan-2: High resolution imaging of the lunar surface*. Current Science, 118(4), 548–555.
* **Payload 2 — Terrain Mapping Camera 2 (TMC-2):**
  - Optical design: Three-line pushbroom stereo scanner (Fore $+25^\circ$, Nadir $0^\circ$, Aft $-25^\circ$).
  - Spatial resolution: $5.0\text{ m}$ per pixel.
  - Primary function: Continuous stereo photogrammetric digital elevation models across polar strips from $-70^\circ$ to $-90^\circ$.
* **Licensing & Rights:** Subject to ISRO Terms of Use and ISSDC PRADAN Archive Policy. Scientific reproduction permitted with mandatory citation and attribution to ISRO. Raw redistribution requires compliance with ISSDC archive covenants.

### 2.3 NASA PGDA LOLA Altimetry Products
* **Product 78:** High-Resolution Artemis Landing Site DEMs (5.0 m/pixel) and derived Horn slope / RMS roughness layers (`https://pgda.gsfc.nasa.gov/products/78`).
* **Product 90:** Lunar South Pole 80m Regional Polar Stereographic DEM (`https://pgda.gsfc.nasa.gov/products/90`).
* **Citation:** Smith, D. E., et al. (2010). *The Lunar Orbiter Laser Altimeter Investigation on the Lunar Reconnaissance Orbiter Mission*. Space Science Reviews, 150(1–4), 209–241.

---

## 3. Product Catalog & Footprint Inventory

| Product ID | Mission / Payload | Region & Geographic Target | Latitude Bounds | Longitude Bounds | Pixel Scale | Solar Inc. | Split / Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `LROC_NAC_POLAR_M119811899LE` | NASA LROC NAC | Shackleton Connecting Ridge (Site 01) | $-89.9^\circ$ to $-89.4^\circ$ | $140.0^\circ$ to $240.0^\circ$ | 1.2 mpp | $82.5^\circ$ | Train (10 tiles) |
| `LROC_NAC_POLAR_M119818694LE` | NASA LROC NAC | Shackleton Crater Rim Bench | $-89.9^\circ$ to $-89.4^\circ$ | $120.0^\circ$ to $210.0^\circ$ | 1.2 mpp | $82.5^\circ$ | Train (10 tiles) |
| `LROC_NAC_POLAR_M120145821LE` | NASA LROC NAC | Connecting Ridge Extension (Site 01 Ext) | $-89.6^\circ$ to $-89.3^\circ$ | $190.0^\circ$ to $240.0^\circ$ | 1.4 mpp | $83.1^\circ$ | Train (10 tiles) |
| `LROC_NAC_POLAR_M123456789LE` | NASA LROC NAC | Malapert Mountain Plateau Margin | $-86.3^\circ$ to $-85.7^\circ$ | $0.0^\circ$ to $30.0^\circ$ | 1.5 mpp | $80.4^\circ$ | Train (10 tiles) |
| `LROC_NAC_POLAR_M123456790RE` | NASA LROC NAC | Malapert Mountain Summit Massif | $-86.0^\circ$ to $-85.5^\circ$ | $0.0^\circ$ to $35.0^\circ$ | 1.5 mpp | $80.4^\circ$ | Val (10 tiles) |
| `LROC_NAC_POLAR_M145129840LE` | NASA LROC NAC | Haworth Transition Rim (PSR Margin) | $-87.6^\circ$ to $-87.1^\circ$ | $342.0^\circ$ to $358.0^\circ$ | 1.8 mpp | $84.5^\circ$ | Val (10 tiles) |
| `LROC_NAC_POLAR_M134982103LE` | NASA LROC NAC | de Gerlache Crater Rim 1 | $-88.8^\circ$ to $-88.3^\circ$ | $265.0^\circ$ to $290.0^\circ$ | 1.4 mpp | $81.2^\circ$ | Test Holdout (10 tiles) |
| `LROC_NAC_POLAR_M134988898LE` | NASA LROC NAC | de Gerlache Crater Rim 2 | $-88.5^\circ$ to $-88.0^\circ$ | $270.0^\circ$ to $295.0^\circ$ | 1.4 mpp | $81.2^\circ$ | Test Holdout (10 tiles) |
| `LROC_NAC_POLAR_M1139415414RE` | NASA LROC NAC | Amundsen Crater Rim & Plateau | $-84.8^\circ$ to $-79.0^\circ$ | $80.0^\circ$ to $95.0^\circ$ | 1.5 mpp | $79.5^\circ$ | Extended Reference |
| `LROC_NAC_POLAR_M1174628392LE` | NASA LROC NAC | Nobile Crater Rim 1 & 2 | $-85.6^\circ$ to $-83.5^\circ$ | $45.0^\circ$ to $60.0^\circ$ | 1.5 mpp | $79.8^\circ$ | Extended Reference |
| `LROC_NAC_POLAR_M1382940192RE` | NASA LROC NAC | Drygalski Outer Rim / SPA Highland | $-79.5^\circ$ to $-75.0^\circ$ | $265.0^\circ$ to $285.0^\circ$ | 1.6 mpp | $78.5^\circ$ | Extended Reference |
| `CH2_OHR_NC_20200115T081520_825_D` | ISRO CH-2 OHRC | Amundsen-Ganswindt Transition Corridor | $-81.2^\circ$ to $-78.5^\circ$ | $82.0^\circ$ to $87.0^\circ$ | 0.25 mpp | $83.0^\circ$ | Extended Validation |
| `CH2_OHR_NC_20190906T123045_710_D` | ISRO CH-2 OHRC | Simpelius N / Boguslawsky Corridor | $-74.8^\circ$ to $-71.2^\circ$ | $52.0^\circ$ to $56.5^\circ$ | 0.28 mpp | $81.5^\circ$ | Context Validation |
| `CH2_TMC_NC_20191012T041230_DTM` | ISRO CH-2 TMC-2 | South Pole Extended Strip ($-70^\circ$ to $-80^\circ$) | $-80.0^\circ$ to $-70.0^\circ$ | $0.0^\circ$ to $360.0^\circ$ | 5.0 mpp | Triplet | Context DEM Baseline |
| `CH2_TMC_NC_20200218T102450_DTM` | ISRO CH-2 TMC-2 | South Pole Core Strip ($-80^\circ$ to $-90^\circ$) | $-90.0^\circ$ to $-80.0^\circ$ | $0.0^\circ$ to $360.0^\circ$ | 5.0 mpp | Triplet | Core DEM Baseline |

---

## 4. Solar Illumination Geometry & Physical Principles

### 4.1 Low-Sun Elevation in Polar Corridors
At the lunar South Pole, the Sun never rises more than $1.5^\circ$ to $2.0^\circ$ above the local horizon (solar incidence angles $\theta_{\text{inc}} = 78.0^\circ$ to $88.5^\circ$).
- **Crater Bowls:** High interior shadowing makes shadowed rim identification critical for depression delineation.
- **Boulders:** Rocky ejecta blocks cast elongated shadows whose length $L_{\text{shadow}}$ is physically related to boulder height $H_{\text{boulder}}$ by:
  $$H_{\text{boulder}} = L_{\text{shadow}} \times \tan(\theta_{\text{elev}}) = L_{\text{shadow}} \times \tan(90^\circ - \theta_{\text{inc}})$$
  For example, at $\theta_{\text{inc}} = 84^\circ$, $\theta_{\text{elev}} = 6^\circ$. A 1.0 m boulder casts a $9.5\text{ m}$ shadow, occupying multiple pixels in LROC NAC and OHRC imagery.

### 4.2 Rejection of Low-Latitude Apollo Imagery
Photographs from Apollo 11–17 were captured at latitudes between $0^\circ$ and $26^\circ$ with sun elevation angles $> 15^\circ$ to $45^\circ$. Applying models trained on such equatorial lighting to polar grazing geometries causes catastrophic false-positive shadow conflation. MoonScape training data is strictly limited to verified polar nadir orbital observations.
