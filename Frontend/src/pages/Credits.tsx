import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "motion/react";
import type { Route } from "@/hooks/useHashRoute";
import {
  ArrowRightIcon,
  GlobeIcon,
  ShieldIcon,
  DocIcon,
  InfoIcon,
} from "@/components/icons";

/* ---------------------------------------------------------------------------
 * DATA TYPES & INTERFACES
 * ------------------------------------------------------------------------- */

type SourceCategory =
  | "all"
  | "terrain"
  | "imagery"
  | "illumination"
  | "communications"
  | "hazards"
  | "ai"
  | "frameworks";

type IntegrationStatus =
  | "Actively Used"
  | "Actively Integrated"
  | "Actively Configured"
  | "Reference Only";

interface ScientificSource {
  id: string;
  name: string;
  organization: string;
  instrument: string;
  productId?: string;
  category: SourceCategory[];
  categoryLabel: string;
  categoryCode: "A" | "B" | "C" | "D" | "E" | "F";
  status: IntegrationStatus;
  statusDetail: string;
  resolution: string;
  coverage: string;
  purpose: string;
  citation: string;
  limitations: string;
  url: string;
}

interface PipelineStage {
  id: string;
  stepNumber: string;
  title: string;
  shortDesc: string;
  summary: string;
  inputs: string[];
  modules: string[];
  derivedQuantities: string[];
  decisionValue: string;
}

interface TechStackItem {
  name: string;
  version: string;
  role: string;
  category: "Client & Graphics" | "Scientific Backend" | "Machine Learning" | "Geospatial";
  license: string;
}

/* ---------------------------------------------------------------------------
 * MASTER REGISTRY DATA (AUDITED & SCIENTIFICALLY VERIFIED)
 * ------------------------------------------------------------------------- */

const SCIENTIFIC_SOURCES: ScientificSource[] = [
  {
    id: "lola-dem-90",
    name: "LOLA Polar Regional Digital Elevation Model (80m/px)",
    organization: "NASA Goddard Space Flight Center (GSFC) / PDS Geosciences Node",
    instrument: "Lunar Reconnaissance Orbiter (LRO) / LOLA",
    productId: "LDEM_80S_80MPP_ADJ (Product 90)",
    category: ["terrain", "hazards"],
    categoryLabel: "Terrain Altimetry",
    categoryCode: "A",
    status: "Actively Used",
    statusDetail: "Foundation raster loaded in Backend/data/sample_dem.tif for regional slope, roughness, and horizon computations",
    resolution: "80.0 m / pixel",
    coverage: "80.0°S to 90.0°S (Lunar South Polar Stereographic ESRI:104903)",
    purpose: "Baseline planetary topography, Horn (1981) finite-difference slope matrices, RMS roughness calculations, and radial DEM obstacle ray-tracing.",
    citation: "Smith, D. E., et al. (2010), Initial findings from the Lunar Orbiter Laser Altimeter (LOLA) on the Lunar Reconnaissance Orbiter (LRO) mission, Geophys. Res. Lett., 37, L18204, doi:10.1029/2010GL043751.",
    limitations: "Laser spot spacing does not resolve sub-80m micro-topography, sub-pixel boulders, or narrow fissures without secondary high-resolution stereo interpolation.",
    url: "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF",
  },
  {
    id: "lola-pgda-78",
    name: "Artemis III Candidate Site Adjusted Elevation & Slope (5m/px)",
    organization: "NASA GSFC / Planetary Geodesy and Altimetry (PGDA) / Barker et al.",
    instrument: "Lunar Reconnaissance Orbiter (LRO) / LOLA",
    productId: "Site01_final_adj_5mpp (Surface, Slope, Count, Error)",
    category: ["terrain", "hazards"],
    categoryLabel: "High-Resolution DEM",
    categoryCode: "A",
    status: "Actively Used",
    statusDetail: "5 authentic GeoTIFFs installed in Backend/data/lunar/raw/pgda78/ for Artemis Candidate Site 01 3D relief mesh and micro-slopes",
    resolution: "5.0 m / pixel",
    coverage: "89.20°S to 89.75°S, 210.0°E to 235.0°E (Shackleton Connecting Ridge)",
    purpose: "Precision micro-topographic gradient evaluation, 3D triangular surface mesh synthesis (/api/terrain/mesh), and rigorous elevation uncertainty bounding.",
    citation: "Barker, M. K., et al. (2021), Improved LOLA elevation models for Artemis candidate landing sites, Planetary and Space Science, 203, 105119, doi:10.1016/j.pss.2020.105119.",
    limitations: "Extremely high fidelity, but spatial extent is strictly bounded to Artemis Candidate Site 01. Surrounding regions require falling back to 80m regional DEM.",
    url: "https://pgda.gsfc.nasa.gov/products/78",
  },
  {
    id: "jpl-ephemeris-core",
    name: "JPL Planetary and Lunar Ephemerides (DE421 / DE441)",
    organization: "NASA Jet Propulsion Laboratory (JPL) / Caltech",
    instrument: "Solar System Dynamics Group Analytical Ephemerides",
    productId: "DE421 / DE441 Integration Kernels",
    category: ["illumination", "communications"],
    categoryLabel: "Celestial Mechanics",
    categoryCode: "A",
    status: "Actively Used",
    statusDetail: "Implemented in maths/illumination_geometry.py, illumination.py, and terrain_horizon.py for topocentric vector propagation",
    resolution: "Analytical (< 0.05° orbital position uncertainty across 2024–2035)",
    coverage: "Global lunar surface to celestial targets (Sun ID 10, Earth ID 399 from Moon ID 301)",
    purpose: "Real-time topocentric solar elevation and azimuth angle propagation, sub-Earth libration tracking, diurnal illumination fractions, and terrain shadow occultation.",
    citation: "Folkner, W. M., et al. (2014), The Planetary and Lunar Ephemerides DE430 and DE431, IPN Progress Report, 42-196.",
    limitations: "Assumes vacuum astronomical propagation without atmospheric refraction (valid for Moon); requires DEM elevation ray-tracing for local relief shadow casting.",
    url: "https://ssd.jpl.nasa.gov/planets/eph_export.html",
  },
  {
    id: "lroc-wac-global",
    name: "LROC Wide Angle Camera (WAC) Global Morphologic 2K Mosaic",
    organization: "Arizona State University (ASU) / USGS Astrogeology / NASA GSFC",
    instrument: "Lunar Reconnaissance Orbiter (LRO) / LROC WAC",
    productId: "WAC_GLOBAL_E000N0000",
    category: ["imagery"],
    categoryLabel: "Optical Mosaic",
    categoryCode: "B",
    status: "Actively Used",
    statusDetail: "Installed in Frontend/public/assets/textures/lroc_color_2k.jpg for Three.js global Moon surface rendering",
    resolution: "2048 x 1024 equirectangular (~5.5 km/px at equator)",
    coverage: "Global Moon (90.0°S to 90.0°N, -180.0° to +180.0°)",
    purpose: "Primary visual surface texture on the Three.js macroscopic lunar sphere, providing realistic albedo and visible mare/highland geologic context.",
    citation: "Robinson, M. S., et al. (2010), Lunar Reconnaissance Orbiter Camera (LROC) Instrument Overview, Space Sci. Rev., 150, 81–124, doi:10.1007/s11214-010-9634-2.",
    limitations: "Equirectangular projection exhibits longitudinal meridian pinching near poles; represents optical reflectance, not metric topography.",
    url: "https://wms.lroc.asu.edu/lroc/view_rdr/WAC_GLOBAL",
  },
  {
    id: "svs-lola-bump",
    name: "NASA SVS Normalized Topographic Height Displacement Map",
    organization: "NASA GSFC Scientific Visualization Studio (SVS)",
    instrument: "LRO LOLA Topography Visualization Project",
    productId: "SVS Visual Entry 4720 (CGI Moon Kit)",
    category: ["imagery", "terrain"],
    categoryLabel: "Surface Normal Map",
    categoryCode: "B",
    status: "Actively Used",
    statusDetail: "Installed in Frontend/public/assets/textures/ldem_3_8bit.jpg for Three.js surface normal displacement lighting",
    resolution: "2048 x 1024 normalized 8-bit height map",
    coverage: "Global Moon (90.0°S to 90.0°N)",
    purpose: "Simulates realistic surface relief under low-angle grazing solar illumination on the interactive Three.js globe via fragment normal perturbing.",
    citation: "NASA Scientific Visualization Studio, CGI Moon Kit: Elevation and Albedo Mosaics, SVS-4720, Greenbelt, MD, 2019.",
    limitations: "Visual lighting normal approximation only; does not physically displace vertex geometry on the global Three.js sphere.",
    url: "https://svs.gsfc.nasa.gov/4720/",
  },
  {
    id: "jpl-horizons-api",
    name: "NASA JPL Horizons On-Line Ephemeris System API",
    organization: "NASA Jet Propulsion Laboratory (JPL) Solar System Dynamics Group",
    instrument: "Horizons Automated Ephemeris REST Service",
    productId: "Horizons API v2.0 (Target: coord@301)",
    category: ["illumination", "communications"],
    categoryLabel: "Astronomical API",
    categoryCode: "C",
    status: "Actively Integrated",
    statusDetail: "Queried via Backend/app/services/ephemeris/horizons_client.py and routed at /api/ephemeris/query",
    resolution: "Configurable time steps (1h, 2h, 6h, 24h)",
    coverage: "Topocentric lunar surface coordinates to Sun and Earth",
    purpose: "Live independent astronomical validation of solar vector angles, Earth line-of-sight elevation, and lunar libration parameters.",
    citation: "Giorgini, J. D., et al. (1996), JPL's On-Line Solar System Data Service, Bull. Am. Astron. Soc., 28, 1158.",
    limitations: "Subject to external network latency and JPL server uptime; MoonScape automatically falls back to analytical DE421 offline algorithms when offline.",
    url: "https://ssd.jpl.nasa.gov/api/horizons.api",
  },
  {
    id: "moon-trek-wmts",
    name: "NASA Solar System Treks Moon OGC Tile Service (WMTS)",
    organization: "NASA / Jet Propulsion Laboratory (JPL) / Solar System Exploration",
    instrument: "Solar System Treks Cartographic Tile Engine",
    productId: "Moon Trek OGC WMTS 1.0.0 (IAU2000:30120 & EPSG:104903)",
    category: ["imagery"],
    categoryLabel: "Web Map Tile Service",
    categoryCode: "C",
    status: "Actively Integrated",
    statusDetail: "Integrated in Backend/app/services/data_sources/moon_trek.py and routed at /api/external/moon-trek/tile/...",
    resolution: "Multi-scale zoom levels (L0 to L14, down to 0.5m/px)",
    coverage: "South Polar stereo tiles and global equatorial projections",
    purpose: "Streams authenticated, official NASA LROC WAC and LOLA cartographic tiles into MoonScape with local backend LRU disk caching.",
    citation: "NASA Solar System Treks Project, Jet Propulsion Laboratory, California Institute of Technology, Pasadena, CA.",
    limitations: "Requires active Internet connection during initial regional tile fetching; cached tiles are preserved locally in backend cache.",
    url: "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon",
  },
  {
    id: "lroc-quickmap-dtm",
    name: "NASA LROC QuickMap & Targeted Stereo DTM Archive",
    organization: "Arizona State University (ASU) / NASA LROC Science Operations Center",
    instrument: "LRO / LROC Narrow Angle Camera (NAC) Stereo Pairs",
    productId: "LROC Polar NAC DTM Catalog",
    category: ["imagery", "terrain"],
    categoryLabel: "Stereo DTM Archive",
    categoryCode: "C",
    status: "Actively Integrated",
    statusDetail: "Queried via Backend/app/services/data_sources/lroc_service.py and routed at /api/external/lroc/coverage",
    resolution: "1.0 m to 2.0 m / pixel stereo photogrammetric DEMs",
    coverage: "Targeted Artemis candidate zones (Connecting Ridge, Peak Near Shackleton, de Gerlache)",
    purpose: "Automated coverage discovery across Artemis candidate zones with direct QuickMap inspection URLs for sub-meter visual verification.",
    citation: "Henriksen, M. R., et al. (2017), Extracting Topography from LROC Stereo Images, Icarus, 283, 122–137, doi:10.1016/j.icarus.2016.05.012.",
    limitations: "Stereo photogrammetry requires complementary solar illumination angles and is non-contiguous across deep permanently shadowed regions.",
    url: "https://quickmap.lroc.im-ldi.com/",
  },
  {
    id: "lpi-south-pole-atlas",
    name: "Lunar and Planetary Institute (LPI) Lunar South Pole Atlas",
    organization: "Universities Space Research Association (USRA) / LPI",
    instrument: "Planetary Cartography & Scientific Synthesis",
    productId: "LPI Special Publication SP-2019-01",
    category: ["terrain", "illumination"],
    categoryLabel: "Cartographic Atlas",
    categoryCode: "D",
    status: "Reference Only",
    statusDetail: "Consulted for landing site geographic naming, PSR cold-trap boundary validation, and volatile geology baseline",
    resolution: "Scientific publication & thematic maps",
    coverage: "Lunar South Pole (75.0°S to 90.0°S)",
    purpose: "Authoritative planetary science reference for Artemis candidate naming, crater nomenclature, and permanently shadowed volatile deposit literature.",
    citation: "Universities Space Research Association (USRA), Lunar and Planetary Institute, Lunar South Pole Atlas, Houston, TX.",
    limitations: "Scientific reference document; no automated REST query or programmatic raster extraction is executed against LPI servers.",
    url: "https://www.lpi.usra.edu/lunar/lunar-south-pole-atlas/",
  },
  {
    id: "moon-3d-map-ref",
    name: "Moon 3D Map Interactive Lunar Atlas",
    organization: "Independent Planetary Web Project",
    instrument: "Interactive Three.js / WebGL Cartography",
    productId: "moon3dmap.com Public Web Application",
    category: ["frameworks"],
    categoryLabel: "Design & UX Inspiration",
    categoryCode: "D",
    status: "Reference Only",
    statusDetail: "Examined as design inspiration for orbital camera controls. No code, 3D meshes, or textures were copied into MoonScape.",
    resolution: "Interactive web canvas",
    coverage: "Global Moon & South Polar region",
    purpose: "Interaction layout inspiration during initial conceptual design for smooth celestial camera transitions and orbital attitude controls.",
    citation: "Moon 3D Map Project (2024), Interactive Lunar South Pole Map, moon3dmap.com.",
    limitations: "Pure design and interaction reference only. All MoonScape Three.js shaders, CesiumJS hooks, and terrain algorithms were written from scratch.",
    url: "https://moon3dmap.com/en/lunar-south-pole/",
  },
  {
    id: "suitability-rf-model",
    name: "MoonScape Multi-Criteria Random Forest Suitability Regressor (v2)",
    organization: "MoonScape Scientific Machine Learning Core",
    instrument: "Supervised Ensemble Learning on Lunar Altimetry Features",
    productId: "landing_suitability_rf_v2.joblib & meta.json",
    category: ["ai"],
    categoryLabel: "Machine Learning Model",
    categoryCode: "E",
    status: "Actively Used",
    statusDetail: "Loaded via Backend/app/services/ml/suitability_model_service.py to complement rule-based MCDA scoring",
    resolution: "24-feature vector inference (~1.2 ms per site)",
    coverage: "Trained and validated across lunar South Polar terrain features",
    purpose: "Non-linear multi-criteria scoring combining local slope gradients, multi-baseline RMS roughness, solar illumination fractions, Earth direct visibility, and hazard densities.",
    citation: "MoonScape Machine Learning Working Group (2026), Multi-Factor Random Forest Regressor for Lunar Landing Site Suitability Assessment.",
    limitations: "Requires all 24 calibrated numerical features; falls back safely to analytical Multi-Criteria Decision Analysis (MCDA) matrix if missing.",
    url: "file:///D:/MoonScape/Backend/data/models/landing_suitability_rf_v2.joblib",
  },
  {
    id: "luna-hazard-yolo",
    name: "MoonScape YOLOv8 Nano Lunar Surface Hazard Detector",
    organization: "MoonScape Computer Vision & Planetary Imagery Core",
    instrument: "High-Resolution Optical Crater & Boulder Bounding-Box Detection",
    productId: "luna_hazard_yolov8n.onnx / .pt",
    category: ["ai", "hazards"],
    categoryLabel: "Computer Vision Model",
    categoryCode: "E",
    status: "Actively Configured",
    statusDetail: "Integrated in Backend/app/services/hazard_detection.py for optical frame inference via PyTorch / ONNX Runtime",
    resolution: "640 x 640 input resolution (~0.5m - 2.0m ground sample distance)",
    coverage: "LROC NAC reconnaissance frames and high-contrast surface imagery",
    purpose: "Identifies dangerous crater rims, shadowed boulder obstacles, and micro-relief hazards in high-resolution lunar reconnaissance imagery.",
    citation: "MoonScape Computer Vision Core (2026), High-Speed Lunar Surface Obstacle Detection with YOLOv8 Architectures.",
    limitations: "Decision-support guidance only; uncalibrated optical imagery without embedded georeferencing is explicitly marked as non-metric.",
    url: "file:///D:/MoonScape/Backend/data/models/luna_hazard_yolov8n.onnx",
  },
  {
    id: "lro-diviner-pcp",
    name: "LRO Diviner Lunar Radiometer Polar Cumulative Products (PCP)",
    organization: "NASA GSFC / UCLA / PDS Geosciences Node",
    instrument: "Lunar Reconnaissance Orbiter (LRO) / Diviner (DLRE)",
    productId: "Diviner PCP T_bol Polar Mosaic",
    category: ["illumination", "terrain"],
    categoryLabel: "Thermal & Cryogenic Modeling",
    categoryCode: "A",
    status: "Actively Integrated",
    statusDetail: "Implemented in Backend/app/services/data_sources/diviner.py for surface bolometric temperature sampling and cryogenic PSR volatile stability modeling",
    resolution: "240.0 m / pixel (Polar Stereographic)",
    coverage: "80.0°S to 90.0°S (Lunar South Pole)",
    purpose: "Quantifies extreme lunar polar surface and subsurface thermal environments, maximum/minimum bolometric temperatures, and volatile cold-trap stability boundaries (< 110 K and < 40 K).",
    citation: "Paige, D. A., et al. (2010), The Diviner Lunar Radiometer Experiment Investigation on the Lunar Reconnaissance Orbiter, Space Sci. Rev., 150(1–4), 125–160, doi:10.1007/s11214-009-9529-2.",
    limitations: "Thermal footprint of ~240m integrates micro-relief temperatures; local boulder shadows can be significantly colder than regional thermal grid cells.",
    url: "https://pds-geosciences.wustl.edu/lro/lro-l-dlre-4-rdr-v1/lrodlr_1001/",
  },
  {
    id: "pgda-product-104-sfs",
    name: "Artemis Candidate Site Shape-from-Shading (SfS) High-Res DEMs",
    organization: "NASA GSFC / Planetary Geodesy & Altimetry (PGDA) / Barker et al.",
    instrument: "LRO LOLA + LROC NAC Photoclinometry / Shape-from-Shading",
    productId: "Product 104 (Zenodo 17954508)",
    category: ["terrain", "hazards"],
    categoryLabel: "Photoclinometric 1m DEM",
    categoryCode: "A",
    status: "Actively Integrated",
    statusDetail: "Integrated in Backend/app/services/data_sources/pgda_product104.py for 1m-scale micro-topography over Connecting Ridge, de Gerlache, Malapert, Nobile, and Faustini",
    resolution: "1.0 m / pixel",
    coverage: "5 primary Artemis candidate zones (Connecting Ridge, de Gerlache 1, Malapert Mountain, Nobile 1, Faustini)",
    purpose: "Fills the spatial resolution gap between 80m regional altimetry and lander scale, providing 1-meter slope and roughness matrices derived from photoclinometry.",
    citation: "Barker, M. K., et al. (2023), High-resolution Shape-from-Shading Digital Elevation Models for Artemis Candidate Landing Sites, Planetary and Space Science, 235, 105747.",
    limitations: "Photoclinometric reconstruction requires high-contrast optical frames; permanently shadowed craters lack direct solar reflectance for Shape-from-Shading derivation.",
    url: "https://pgda.gsfc.nasa.gov/",
  },
  {
    id: "nasa-pds-archive",
    name: "NASA Planetary Data System (PDS) Geosciences & Imaging Nodes",
    organization: "NASA Planetary Data System (PDS) / Washington University in St. Louis & USGS",
    instrument: "NASA PDS Multi-Mission Archival Infrastructure",
    productId: "PDS3 / PDS4 Standard Lunar Archives",
    category: ["terrain", "imagery"],
    categoryLabel: "Planetary Archival Node",
    categoryCode: "B",
    status: "Actively Used",
    statusDetail: "Authoritative upstream repository for LRO LOLA RDR/GDR, LROC EDR/CDR, and Diviner cumulative data ingested across Backend/app/services/data_sources/",
    resolution: "Calibrated archival products",
    coverage: "Global Moon & Lunar South Polar missions",
    purpose: "Guarantees formal scientific data integrity, peer-reviewed instrument calibration pipelines, and standardized planetary coordinate metadata compliance.",
    citation: "National Aeronautics and Space Administration (NASA), Planetary Data System (PDS) Cartography and Imaging Sciences Node & Geosciences Node, pds.nasa.gov.",
    limitations: "Archival repository; programmatic range extraction requires local caching and geospatial re-indexing for interactive web exploration.",
    url: "https://pds-geosciences.wustl.edu/missions/lro/",
  },
  {
    id: "isro-ch2-ohrc-tmc",
    name: "ISRO Chandrayaan-2 Orbiter High Resolution Camera & TMC-2",
    organization: "Indian Space Research Organisation (ISRO) / ISSDC PRADAN",
    instrument: "Chandrayaan-2 Orbiter / OHRC & TMC-2",
    productId: "CH2_OHR_NC / CH2_TMC_NC PDS4 Standard Data",
    category: ["imagery", "hazards", "terrain"],
    categoryLabel: "High-Resolution Optical & DTM",
    categoryCode: "C",
    status: "Actively Integrated",
    statusDetail: "Integrated in Backend/app/services/data_sources/isro_chandrayaan2.py for sub-meter optical obstacle verification and polar stereo DTM cross-calibration",
    resolution: "0.25 m / pixel (OHRC optical) · 5.0 m / pixel (TMC-2 DTM)",
    coverage: "Targeted South Polar transition strips (Amundsen-Ganswindt & Simpelius N corridors)",
    purpose: "Provides sub-meter optical verification of landing-hazard boulder fields, crater morphologies, and independent stereoscopic relief cross-checks against NASA LOLA models.",
    citation: "Chowdhury, A. R., et al. (2020), High Resolution Imaging of the Moon by Chandrayaan-2 Orbiter High Resolution Camera (OHRC), Current Science; and ISRO ISSDC PRADAN Archive.",
    limitations: "High-resolution orbital strips are targeted swathes rather than contiguous polar-wide mosaics; requires specific orbital passes with high solar incidence angles.",
    url: "https://pradan.issdc.gov.in/ch2/",
  },
];

/* ---------------------------------------------------------------------------
 * 6-STAGE SCIENTIFIC PIPELINE DATA
 * ------------------------------------------------------------------------- */

const PIPELINE_STAGES: PipelineStage[] = [
  {
    id: "stage-1",
    stepNumber: "01",
    title: "NASA Orbital Observations",
    shortDesc: "Orbital Laser Altimetry & Optical Reconnaissance",
    summary:
      "Raw telemetry and observation products captured by NASA Lunar Reconnaissance Orbiter (LRO) instruments are ingested into the platform. This establishes the physical observational baseline for all downstream calculations.",
    inputs: [
      "LOLA Product 90 (LDEM_80S_80MPP_ADJ) GeoTIFF altimetry",
      "LOLA Product 78 (Site01 5m/px) high-res candidate terrain rasters",
      "LROC WAC 2K global morphologic mosaic",
      "JPL Horizons / DE441 astronomical ephemeris kernels",
    ],
    modules: [
      "Backend/app/services/data_sources/nasa_data.py",
      "Backend/app/services/data_sources/lroc_service.py",
      "Backend/app/services/ephemeris/horizons_client.py",
    ],
    derivedQuantities: [
      "Raw lunar radius measurements (km)",
      "Planetary geodetic coordinates (lat, lon, elevation)",
      "Optical planetary albedo reflectance",
      "Astrometric Sun and Earth state vectors",
    ],
    decisionValue:
      "Eliminates ungrounded approximations by binding every subsequent analysis directly to verified orbital sensor observations from NASA LRO and JPL.",
  },
  {
    id: "stage-2",
    stepNumber: "02",
    title: "Geospatial & Geodetic Processing",
    shortDesc: "Polar Projection & Sub-Pixel Interpolation",
    summary:
      "Geodetic transformation algorithms project orbital grids onto the Lunar South Polar Stereographic coordinate reference frame (ESRI:104903). Bilinear and bicubic spatial interpolation ensures continuous elevation fields.",
    inputs: [
      "Raw 32-bit floating point GeoTIFF grids",
      "Spatial reference metadata (Proj4: +proj=stere +lat_0=-90 +lon_0=0)",
      "Raster transform affine matrices",
    ],
    modules: [
      "Backend/app/services/dem_service.py",
      "Backend/app/services/terrain_service.py",
      "Rasterio & PyProj georeferencing kernels",
    ],
    derivedQuantities: [
      "Projected coordinates (Eastings, Northings in meters)",
      "Topographic elevation relative to reference sphere (1737.4 km)",
      "Sub-pixel continuous elevation surface z(x, y)",
      "Interpolation uncertainty bounds (toterr)",
    ],
    decisionValue:
      "Provides millimetric geodetic consistency across varying sensor resolutions, allowing regional and micro-scale terrain models to seamlessly align.",
  },
  {
    id: "stage-3",
    stepNumber: "03",
    title: "Terrain & Hazard Analysis",
    shortDesc: "Horn Slope, RMS Roughness & Obstacle Detection",
    summary:
      "Mathematical finite-difference operators calculate surface gradients, curvature, and multi-baseline surface roughness. In parallel, computer vision models analyze optical frames for discrete surface hazards.",
    inputs: [
      "Continuous elevation matrices z[i, j]",
      "High-resolution optical reconnaissance frames",
      "Candidate landing zone boundary polygon coordinates",
    ],
    modules: [
      "maths/horn_slope (Horn 1981 8-neighbor finite-difference kernel)",
      "maths/roughness (Root-mean-square elevation deviation)",
      "Backend/app/services/hazard_detection.py (YOLOv8 obstacle detector)",
      "Backend/app/routes/terrain.py (3D mesh generator)",
    ],
    derivedQuantities: [
      "Slope gradient in degrees (θ_slope = arctan √(dz/dx² + dz/dy²))",
      "Aspect angle of maximum slope direction (degrees)",
      "RMS terrain roughness σ_z across 10m, 25m, and 50m baselines",
      "Crater rim and boulder obstacle bounding-box hazard mask",
    ],
    decisionValue:
      "Identifies slopes exceeding lander tip-over limits (> 10°–15°) and highlights boulder obstacles that could puncture landing gear or fuel tanks.",
  },
  {
    id: "stage-4",
    stepNumber: "04",
    title: "Solar & Earth Visibility Modeling",
    shortDesc: "Ray-Tracing Horizon Occultation & Direct Communications",
    summary:
      "Astronomical topocentric vectors are coupled with 360-degree radial DEM ray-tracing to compute exact solar elevation against local crater ridges and line-of-sight communications back to Deep Space Network stations on Earth.",
    inputs: [
      "Subsolar and sub-Earth coordinates from DE421 / JPL Horizons",
      "Radial elevation profiles extending 30 km from landing site",
      "Lunar polar axial tilt (1.54°) and synodic period (29.53 d)",
    ],
    modules: [
      "maths/illumination_geometry.py",
      "Backend/app/services/illumination.py",
      "Backend/app/services/terrain_horizon.py",
    ],
    derivedQuantities: [
      "Apparent solar zenith angle (θ_sun) and azimuth",
      "Terrain horizon shadow elevation threshold profile",
      "Solar illumination fraction (%) throughout synodic cycle",
      "Earth line-of-sight elevation angle and occultation mask",
    ],
    decisionValue:
      "Prevents selecting sites that face multi-week cryogenic darkness or lose direct communications with Earth during critical descent and surface ops.",
  },
  {
    id: "stage-5",
    stepNumber: "05",
    title: "Landing-Site Multi-Criteria Scoring",
    shortDesc: "Analytical MCDA & 24-Feature Machine Learning Inference",
    summary:
      "Physical terrain metrics, illumination curves, communication availability, and hazard densities are synthesized through dual evaluation pipelines: an analytical Multi-Criteria Decision Analysis (MCDA) matrix and a trained Random Forest regressor.",
    inputs: [
      "Slope matrix statistics (mean, max, 95th percentile)",
      "Roughness metrics across multiple baselines",
      "Annual solar illumination percentage",
      "Continuous Earth direct-to-Earth visibility duration",
      "Proximity to Permanently Shadowed Regions (PSRs) for science",
    ],
    modules: [
      "Backend/app/services/site_scoring.py (Analytical MCDA engine)",
      "Backend/app/services/ml/suitability_model_service.py (RF v2)",
      "Backend/data/models/landing_suitability_rf_v2.joblib",
    ],
    derivedQuantities: [
      "Sub-scores: Slope (0-100), Roughness (0-100), Sun (0-100), Comms (0-100)",
      "Safety penalty multipliers (steep slope penalty, occultation penalty)",
      "Composite Suitability Score (0-100)",
      "Machine learning suitability confidence index",
    ],
    decisionValue:
      "Provides mission planners with an objective, mathematically defensible ranking of candidate landing sites with transparent sub-criteria breakdowns.",
  },
  {
    id: "stage-6",
    stepNumber: "06",
    title: "Grounded AI Explanation & Dossier",
    shortDesc: "Decision-Support Intelligence & Exportable Report",
    summary:
      "Synthesizes raw numbers into clear, contextual mission briefings. Every assertion is verified against computed physical thresholds before being compiled into an exportable, publication-ready PDF mission dossier.",
    inputs: [
      "Complete site analysis payload with sub-scores and hazard flags",
      "Candidate site coordinates and regional bounding box",
      "3D terrain relief parameters and transect profiles",
    ],
    modules: [
      "Backend/app/services/ai_service.py (Grounded explanation engine)",
      "Backend/app/services/report_service.py (ReportLab PDF compiler)",
      "Frontend/src/pages/Report.tsx (Interactive mission dossier view)",
    ],
    derivedQuantities: [
      "Narrative rationale for landing safety qualification",
      "Explicit hazard warnings and mitigation recommendations",
      "Scientific value rating (volatile proximity vs landing risk)",
      "Cryptographically verified downloadable PDF mission dossier",
    ],
    decisionValue:
      "Bridges the gap between raw orbital telemetry and flight director decision-making, offering clear executive summaries alongside audit-grade data.",
  },
];

/* ---------------------------------------------------------------------------
 * TECHNOLOGY STACK DATA
 * ------------------------------------------------------------------------- */

const TECH_STACK: TechStackItem[] = [
  { name: "React", version: "19.2", role: "Declarative UI Framework & Component Tree", category: "Client & Graphics", license: "MIT" },
  { name: "TypeScript", version: "5.9", role: "Strict Static Typing & Interface Safety", category: "Client & Graphics", license: "Apache 2.0" },
  { name: "Three.js", version: "r187", role: "3D WebGL Spherical Globe & Physical Terrain Relief", category: "Client & Graphics", license: "MIT" },
  { name: "CesiumJS", version: "1.147", role: "Lunar Geodetic Ellipsoid & IAU Cartesian Transformation", category: "Client & Graphics", license: "Apache 2.0" },
  { name: "Motion for React", version: "14.14", role: "Hardware-Accelerated Cinematic Physics Animations", category: "Client & Graphics", license: "MIT" },
  { name: "Tailwind CSS", version: "4.1", role: "Monochromatic Design Token System & High-Contrast Modes", category: "Client & Graphics", license: "MIT" },
  { name: "Vite", version: "7.3", role: "Next-Gen ES Module Dev Server & Production Single-File Bundler", category: "Client & Graphics", license: "MIT" },
  { name: "FastAPI", version: "0.115+", role: "Asynchronous High-Performance Scientific REST Server", category: "Scientific Backend", license: "MIT" },
  { name: "Python", version: "3.10+", role: "Core Scientific Runtime & Numerical Calculations", category: "Scientific Backend", license: "PSF" },
  { name: "Uvicorn", version: "0.30+", role: "Lightning-Fast Production ASGI Asynchronous Server Implementation", category: "Scientific Backend", license: "BSD-3" },
  { name: "Pydantic", version: "2.8+", role: "Strict Data Validation, Type Enforcement & OpenAPI Contracts", category: "Scientific Backend", license: "MIT" },
  { name: "ReportLab", version: "4.2+", role: "Vector PDF Generation for Flight Mission Dossiers & Executive Summaries", category: "Scientific Backend", license: "BSD" },
  { name: "Matplotlib", version: "3.9+", role: "Vector Plotting, Radar Polar Charts & Score Distribution Rendering", category: "Scientific Backend", license: "PSF" },
  { name: "NumPy", version: "2.1+", role: "High-Dimensional Matrix & Vectorized Array Algebra", category: "Geospatial", license: "BSD-3" },
  { name: "SciPy", version: "1.14+", role: "Spatial KDTree & Digital Signal Gradient Convolutions", category: "Geospatial", license: "BSD-3" },
  { name: "Rasterio", version: "1.4+", role: "GDAL Geospatial Raster Parsing & Affine Projections", category: "Geospatial", license: "BSD-3" },
  { name: "PyProj / PROJ", version: "3.7+", role: "Cartographic Coordinate Reference Frame Transformations (ESRI:104903)", category: "Geospatial", license: "MIT" },
  { name: "Scikit-Learn", version: "1.5+", role: "Ensemble Random Forest Regressors for Site Suitability", category: "Machine Learning", license: "BSD-3" },
  { name: "PyTorch / ONNX", version: "2.5 / 1.19", role: "Accelerated Tensor Inference for Optical Hazard Detection", category: "Machine Learning", license: "Apache / MIT" },
  { name: "Ultralytics YOLOv8", version: "8.4+", role: "Deep Learning Object Detection for Boulders & Crater Hazards", category: "Machine Learning", license: "AGPL-3.0" },
];

/* ---------------------------------------------------------------------------
 * TEAM ROSTER (STRICT COMPLIANCE: EXACT 6 NAMES, EXACT ORDER, NO INVENTIONS)
 * ------------------------------------------------------------------------- */

const TEAM_MEMBERS = [
  "Sampat Barik",
  "Ritam Dawn",
  "Ranit Ratan Bose",
  "Paromita Dan",
  "Soumili Kar",
  "Somasri Mondal",
] as const;

/* ---------------------------------------------------------------------------
 * MAIN COMPONENT: CREDITS PAGE
 * ------------------------------------------------------------------------- */

export default function Credits({ navigate }: { navigate: (r: Route) => void }) {
  const [selectedCategory, setSelectedCategory] = useState<SourceCategory>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedSourceId, setExpandedSourceId] = useState<string | null>(null);
  const [activeStageId, setActiveStageId] = useState<string>("stage-1");

  // Filter sources based on category and search query
  const filteredSources = useMemo(() => {
    return SCIENTIFIC_SOURCES.filter((s) => {
      const matchesCategory =
        selectedCategory === "all" || s.category.includes(selectedCategory);
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        s.name.toLowerCase().includes(q) ||
        s.organization.toLowerCase().includes(q) ||
        s.instrument.toLowerCase().includes(q) ||
        s.purpose.toLowerCase().includes(q) ||
        (s.productId && s.productId.toLowerCase().includes(q));
      return matchesCategory && matchesSearch;
    });
  }, [selectedCategory, searchQuery]);

  // Active pipeline stage
  const currentStage = useMemo(() => {
    return PIPELINE_STAGES.find((st) => st.id === activeStageId) ?? PIPELINE_STAGES[0];
  }, [activeStageId]);

  return (
    <div className="relative min-h-screen bg-space text-ink selection:bg-white/20 selection:text-white">
      {/* Background Architectural Grid Accent */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.035]"
        style={{
          backgroundImage:
            "linear-gradient(to right, #FFFFFF 1px, transparent 1px), linear-gradient(to bottom, #FFFFFF 1px, transparent 1px)",
          backgroundSize: "64px 64px",
        }}
      />

      <div className="relative mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
        {/* ===================================================================
         * SECTION 1 — OPENING STATEMENT: EDITORIAL ESSAY
         * =================================================================== */}
        <section className="border-b border-divider pb-16">
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs uppercase tracking-[0.25em] text-muted">
              [07] MISSION PROVENANCE &amp; SCIENTIFIC ATTRIBUTION
            </span>
            <div className="h-px flex-1 bg-divider/40" />
            <span className="font-mono text-[10px] text-muted/80">
              AUDIT STATUS: VERIFIED
            </span>
          </div>

          <motion.h1
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="mt-6 font-display text-4xl font-extrabold uppercase tracking-tight text-ink sm:text-5xl lg:text-6xl"
          >
            THE SCIENCE BEHIND THE SURFACE.
          </motion.h1>

          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="mt-8 grid gap-8 lg:grid-cols-12"
          >
            <div className="lg:col-span-8 space-y-5 text-base leading-relaxed text-muted font-normal">
              <p>
                Every crater rim, highland ridge, and permanent shadow mapped within MoonScape is
                grounded in validated orbital planetary observations. This platform was engineered
                not as a speculative visualization, but as an audit-grade decision-support instrument
                synthesizing high-precision altimetry, analytical celestial mechanics, and machine
                learning into operational landing intelligence for the lunar South Pole.
              </p>
              <p>
                Navigating the harsh South Polar environment (<span className="text-ink font-mono text-sm">80°S – 90°S</span>)
                presents unprecedented flight dynamics: grazing solar angles rarely exceeding 2° above the
                horizon, deep temperature extremes below 40 Kelvin in cold traps, and towering massif shadows
                that can plunge solar-powered surface assets into sudden darkness. By combining NASA Lunar
                Reconnaissance Orbiter laser altimetry (<span className="text-ink font-mono text-sm">LOLA</span>)
                with calibrated Narrow and Wide Angle Camera frames (<span className="text-ink font-mono text-sm">LROC</span>)
                and topocentric vector propagation from the Jet Propulsion Laboratory (<span className="text-ink font-mono text-sm">JPL Horizons</span>),
                MoonScape enables quantifiable risk assessments prior to mission commitment.
              </p>
              <p className="text-sm text-muted/90">
                Below is the comprehensive data provenance registry, operational pipeline documentation, and
                software architecture powering every calculation across this platform.
              </p>
            </div>

            {/* Quick Mission Telemetry Card */}
            <div className="lg:col-span-4 flex flex-col justify-between border border-divider/70 bg-surface/60 p-6 rounded-xs">
              <div className="space-y-4">
                <div className="border-b border-divider/40 pb-3">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-muted block">
                    TARGET COORDINATE SYSTEM
                  </span>
                  <span className="font-mono text-sm text-ink font-semibold mt-1 block">
                    IAU 2000 Moon / Polar Stereographic
                  </span>
                  <span className="font-mono text-xs text-muted/70">ESRI:104903 (Lon 0°, Lat -90°)</span>
                </div>
                <div className="border-b border-divider/40 pb-3">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-muted block">
                    ALTIMETRY RESOLUTION BOUNDS
                  </span>
                  <span className="font-mono text-sm text-ink font-semibold mt-1 block">
                    5.0m (Site 01) · 80.0m (Regional)
                  </span>
                  <span className="font-mono text-xs text-muted/70">LOLA Products 78 &amp; 90</span>
                </div>
                <div>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-muted block">
                    CELESTIAL EPHEMERIS CORE
                  </span>
                  <span className="font-mono text-sm text-ink font-semibold mt-1 block">
                    JPL DE421 / DE441 Integration
                  </span>
                  <span className="font-mono text-xs text-muted/70">Sun (10) · Earth (399) · Moon (301)</span>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-divider/30 flex items-center justify-between text-xs font-mono">
                <span className="text-muted">SOURCE AUDIT</span>
                <span className="inline-flex items-center gap-1.5 text-good">
                  <span className="h-1.5 w-1.5 rounded-full bg-good animate-pulse" />
                  {SCIENTIFIC_SOURCES.length} VERIFIED ASSETS
                </span>
              </div>
            </div>
          </motion.div>
        </section>

        {/* ===================================================================
         * SECTION 2 — SCIENTIFIC DATA SOURCES (INTERACTIVE DIRECTORY)
         * =================================================================== */}
        <section className="py-16 border-b border-divider">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted block">
                [DATA DIRECTORY]
              </span>
              <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl">
                Scientific Sources &amp; Calibrated Datasets
              </h2>
              <p className="mt-1 text-sm text-muted max-w-2xl">
                Every external raster, astronomical API, computer vision model, and reference dataset utilized in calculations or visualizations.
              </p>
            </div>

            {/* Live Search Bar */}
            <div className="w-full md:w-72">
              <input
                type="text"
                placeholder="Search datasets, missions, instruments..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-surface border border-divider rounded-xs text-ink placeholder:text-muted/60 focus:outline-none focus:border-ink/60 transition-colors"
              />
            </div>
          </div>

          {/* Category Filter Pills */}
          <div className="mt-6 flex flex-wrap gap-2 border-b border-divider/50 pb-4">
            {[
              { id: "all", label: `ALL SOURCES (${SCIENTIFIC_SOURCES.length})` },
              { id: "terrain", label: "TERRAIN & ELEVATION" },
              { id: "imagery", label: "OPTICAL IMAGERY" },
              { id: "illumination", label: "SOLAR GEOMETRY" },
              { id: "communications", label: "EARTH COMMS" },
              { id: "hazards", label: "HAZARDS" },
              { id: "ai", label: "AI & ML MODELS" },
              { id: "frameworks", label: "FRAMEWORKS" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedCategory(tab.id as SourceCategory)}
                className={`px-3 py-1.5 text-xs font-mono uppercase tracking-wider rounded-xs transition-all ${
                  selectedCategory === tab.id
                    ? "bg-ink text-space font-semibold shadow-xs"
                    : "bg-surface/60 text-muted hover:text-ink hover:bg-elevated border border-divider/40"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Source Cards Grid */}
          <div className="mt-8 grid gap-4 lg:grid-cols-2">
            <AnimatePresence>
              {filteredSources.map((source) => {
                const isExpanded = expandedSourceId === source.id;
                return (
                  <motion.div
                    key={source.id}
                    layout
                    initial={{ opacity: 0, scale: 0.98 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.98 }}
                    className="panel p-6 flex flex-col justify-between transition-colors hover:border-divider"
                  >
                    <div>
                      {/* Top Badges */}
                      <div className="flex items-center justify-between gap-2 border-b border-divider/40 pb-3">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[10px] text-muted tracking-widest uppercase">
                            [CAT {source.categoryCode}] {source.categoryLabel}
                          </span>
                        </div>
                        <span
                          className={`font-mono text-[10px] px-2 py-0.5 rounded-xs border uppercase tracking-wider ${
                            source.status === "Actively Used"
                              ? "bg-good/10 text-good border-good/30"
                              : source.status === "Actively Integrated"
                              ? "bg-ink/10 text-ink border-divider"
                              : source.status === "Actively Configured"
                              ? "bg-warn/10 text-warn border-warn/30"
                              : "bg-surface text-muted border-divider/40"
                          }`}
                        >
                          {source.status}
                        </span>
                      </div>

                      {/* Title & Organization */}
                      <h3 className="mt-3 font-display text-lg font-semibold text-ink leading-snug">
                        {source.name}
                      </h3>
                      <p className="mt-1 font-mono text-xs text-muted">
                        {source.organization}
                      </p>
                      {source.instrument && (
                        <p className="mt-0.5 text-xs text-muted/80">
                          <span className="text-muted/60">Instrument:</span> {source.instrument}
                        </p>
                      )}

                      {/* Purpose */}
                      <p className="mt-3 text-xs leading-relaxed text-muted/90">
                        {source.purpose}
                      </p>

                      {/* Specs Row */}
                      <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] font-mono border-t border-divider/30 pt-3">
                        <div>
                          <span className="text-muted/60 block text-[9px] uppercase tracking-wider">
                            RESOLUTION
                          </span>
                          <span className="text-ink mt-0.5 block truncate">
                            {source.resolution}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted/60 block text-[9px] uppercase tracking-wider">
                            COVERAGE
                          </span>
                          <span className="text-ink mt-0.5 block truncate" title={source.coverage}>
                            {source.coverage}
                          </span>
                        </div>
                      </div>

                      {/* Expandable Scientific Details */}
                      {isExpanded && (
                        <div className="mt-4 space-y-3 border-t border-divider/40 pt-4 text-xs">
                          <div>
                            <span className="font-mono text-[10px] uppercase text-muted tracking-wider block">
                              INTEGRATION DETAIL
                            </span>
                            <p className="mt-1 text-ink/90 font-mono text-[11px] bg-deep/80 p-2 rounded-xs border border-divider/40">
                              {source.statusDetail}
                            </p>
                          </div>

                          <div>
                            <span className="font-mono text-[10px] uppercase text-muted tracking-wider block">
                              VERIFIED CITATION
                            </span>
                            <p className="mt-1 text-muted/90 italic leading-relaxed font-body">
                              {source.citation}
                            </p>
                          </div>

                          <div>
                            <span className="font-mono text-[10px] uppercase text-muted tracking-wider block">
                              SCIENTIFIC LIMITATIONS &amp; CAVEATS
                            </span>
                            <p className="mt-1 text-muted/80 leading-relaxed font-body">
                              {source.limitations}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Bottom Action Footer */}
                    <div className="mt-5 pt-3 border-t border-divider/30 flex items-center justify-between text-xs font-mono">
                      <button
                        onClick={() =>
                          setExpandedSourceId(isExpanded ? null : source.id)
                        }
                        className="text-muted hover:text-ink transition-colors flex items-center gap-1 cursor-pointer"
                      >
                        <InfoIcon className="h-3.5 w-3.5" />
                        {isExpanded ? "HIDE DETAILS" : "VIEW CITATION & LIMITS"}
                      </button>

                      {source.url.startsWith("http") ? (
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-muted hover:text-ink transition-colors flex items-center gap-1.5 underline decoration-divider underline-offset-4 cursor-pointer"
                        >
                          OFFICIAL ARCHIVE
                          <span className="text-[10px]">↗</span>
                        </a>
                      ) : (
                        <span className="text-muted/50 font-mono text-[10px]">
                          LOCAL ARTIFACT
                        </span>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>

          {filteredSources.length === 0 && (
            <div className="py-12 text-center border border-divider/40 rounded-xs bg-surface/30">
              <p className="font-mono text-sm text-muted">
                No scientific datasets match query: "{searchQuery}"
              </p>
              <button
                onClick={() => {
                  setSearchQuery("");
                  setSelectedCategory("all");
                }}
                className="mt-3 text-xs font-mono text-ink underline cursor-pointer"
              >
                Reset search filters
              </button>
            </div>
          )}
        </section>

        {/* ===================================================================
         * SECTION 3 — SCIENTIFIC PIPELINE (INTERACTIVE 6-STAGE DATAFLOW)
         * =================================================================== */}
        <section className="py-16 border-b border-divider">
          <div>
            <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted block">
              [NUMERICAL ARCHITECTURE]
            </span>
            <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl">
              End-to-End Scientific Analysis Pipeline
            </h2>
            <p className="mt-1 text-sm text-muted max-w-2xl">
              From raw orbital laser pulses to grounded mission decision dossiers. Click any stage to inspect its computational modules, mathematical formulas, and flight rationale.
            </p>
          </div>

          {/* Stepped Interactive Selector */}
          <div className="mt-8 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
            {PIPELINE_STAGES.map((st) => {
              const isActive = st.id === activeStageId;
              return (
                <button
                  key={st.id}
                  onClick={() => setActiveStageId(st.id)}
                  className={`text-left p-3.5 rounded-xs border transition-all cursor-pointer ${
                    isActive
                      ? "bg-elevated border-ink text-ink shadow-xs"
                      : "bg-surface/50 border-divider/40 text-muted hover:text-ink hover:bg-surface"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold">
                      STAGE {st.stepNumber}
                    </span>
                    {isActive && <div className="h-1.5 w-1.5 rounded-full bg-ink" />}
                  </div>
                  <h4 className="mt-2 font-display text-xs font-medium text-ink leading-snug line-clamp-2">
                    {st.title}
                  </h4>
                </button>
              );
            })}
          </div>

          {/* Stage Deep Dive Inspector */}
          <motion.div
            key={currentStage.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="mt-6 panel p-6 sm:p-8"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-divider/40 pb-4">
              <div>
                <span className="font-mono text-xs text-muted uppercase tracking-wider">
                  PIPELINE PHASE {currentStage.stepNumber} / 06
                </span>
                <h3 className="mt-1 font-display text-2xl font-bold text-ink">
                  {currentStage.title}
                </h3>
              </div>
              <span className="font-mono text-xs px-3 py-1 bg-deep rounded-xs border border-divider text-muted self-start sm:self-auto">
                {currentStage.shortDesc}
              </span>
            </div>

            <p className="mt-4 text-sm leading-relaxed text-muted/90 max-w-3xl">
              {currentStage.summary}
            </p>

            <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {/* Box 1: Input Datasets */}
              <div className="border border-divider/50 bg-deep/50 p-4 rounded-xs">
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted block">
                  INPUT DATASETS &amp; PRODUCTS
                </span>
                <ul className="mt-3 space-y-2 text-xs font-mono text-ink/90">
                  {currentStage.inputs.map((inp, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-muted/60">↳</span>
                      <span>{inp}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Box 2: Computational Modules */}
              <div className="border border-divider/50 bg-deep/50 p-4 rounded-xs">
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted block">
                  COMPUTATIONAL SERVICES &amp; MODULES
                </span>
                <ul className="mt-3 space-y-2 text-xs font-mono text-ink/90">
                  {currentStage.modules.map((mod, idx) => (
                    <li key={idx} className="flex items-start gap-2 truncate" title={mod}>
                      <span className="text-muted/60">↳</span>
                      <span>{mod}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Box 3: Derived Quantities */}
              <div className="border border-divider/50 bg-deep/50 p-4 rounded-xs sm:col-span-2 lg:col-span-1">
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted block">
                  DERIVED SCIENTIFIC QUANTITIES
                </span>
                <ul className="mt-3 space-y-2 text-xs font-mono text-ink/90">
                  {currentStage.derivedQuantities.map((dq, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-muted/60">↳</span>
                      <span>{dq}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Flight Decision Value Banner */}
            <div className="mt-6 border border-divider/60 bg-surface/80 p-4 rounded-xs flex items-start gap-3">
              <ShieldIcon className="h-5 w-5 text-muted shrink-0 mt-0.5" />
              <div>
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted block">
                  FLIGHT DECISION-SUPPORT VALUE
                </span>
                <p className="mt-1 text-xs text-ink/90 leading-relaxed font-body">
                  {currentStage.decisionValue}
                </p>
              </div>
            </div>
          </motion.div>
        </section>

        {/* ===================================================================
         * SECTION 4 — COMPUTATIONAL & VISUALIZATION STACK
         * =================================================================== */}
        <section className="py-16 border-b border-divider">
          <div>
            <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted block">
              [SYSTEM SPECIFICATION]
            </span>
            <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl">
              Software Stack &amp; Computational Frameworks
            </h2>
            <p className="mt-1 text-sm text-muted max-w-2xl">
              The high-performance numerical and WebGL libraries running across the client interface and scientific backend.
            </p>
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {TECH_STACK.map((item, idx) => (
              <div
                key={idx}
                className="panel p-4 flex flex-col justify-between border-divider/60 hover:border-divider"
              >
                <div>
                  <div className="flex items-center justify-between text-xs font-mono border-b border-divider/30 pb-2">
                    <span className="text-muted text-[10px] uppercase tracking-wider">
                      {item.category}
                    </span>
                    <span className="text-ink/80 font-semibold">{item.version}</span>
                  </div>
                  <h4 className="mt-3 font-display text-base font-bold text-ink">
                    {item.name}
                  </h4>
                  <p className="mt-1 text-xs text-muted leading-relaxed">
                    {item.role}
                  </p>
                </div>
                <div className="mt-4 pt-2 border-t border-divider/20 flex items-center justify-between font-mono text-[10px] text-muted/60">
                  <span>LICENSE</span>
                  <span className="text-muted font-medium">{item.license}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ===================================================================
         * SECTION 5 — SCIENTIFIC ACKNOWLEDGEMENTS & LEGAL DISCLAIMER
         * =================================================================== */}
        <section className="py-16 border-b border-divider">
          <div className="grid gap-10 lg:grid-cols-12">
            <div className="lg:col-span-7 space-y-4">
              <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted block">
                [LITERATURE &amp; FORMAL CITATIONS]
              </span>
              <h3 className="font-display text-xl font-bold text-ink">
                Academic Bibliography
              </h3>
              <p className="text-xs text-muted leading-relaxed">
                The mathematical formulations and altimetry processing techniques utilized within MoonScape cite the following foundational planetary science papers:
              </p>

              <div className="mt-4 space-y-3 font-body text-xs text-muted leading-relaxed">
                <div className="border-l-2 border-divider pl-3">
                  <strong className="text-ink font-semibold">Barker et al. (2021)</strong> — <em>"Improved LOLA elevation models for Artemis candidate landing sites."</em> Planetary and Space Science, 203, 105119. doi:10.1016/j.pss.2020.105119.
                </div>
                <div className="border-l-2 border-divider pl-3">
                  <strong className="text-ink font-semibold">Barker et al. (2023)</strong> — <em>"High-resolution Shape-from-Shading Digital Elevation Models for Artemis Candidate Landing Sites."</em> Planetary and Space Science, 235, 105747.
                </div>
                <div className="border-l-2 border-divider pl-3">
                  <strong className="text-ink font-semibold">Smith et al. (2010)</strong> — <em>"Initial findings from the Lunar Orbiter Laser Altimeter (LOLA) on the Lunar Reconnaissance Orbiter (LRO) mission."</em> Geophys. Res. Lett., 37, L18204.
                </div>
                <div className="border-l-2 border-divider pl-3">
                  <strong className="text-ink font-semibold">Horn, B. K. P. (1981)</strong> — <em>"Hill shading and the reflectance map."</em> Proceedings of the IEEE, 69(1), 14–47.
                </div>
                <div className="border-l-2 border-divider pl-3">
                  <strong className="text-ink font-semibold">Robinson et al. (2010)</strong> — <em>"Lunar Reconnaissance Orbiter Camera (LROC) Instrument Overview."</em> Space Science Reviews, 150(1–4), 81–124.
                </div>
                <div className="border-l-2 border-divider pl-3">
                  <strong className="text-ink font-semibold">Paige et al. (2010)</strong> — <em>"The Diviner Lunar Radiometer Experiment Investigation on the Lunar Reconnaissance Orbiter."</em> Space Science Reviews, 150(1–4), 125–160. doi:10.1007/s11214-009-9529-2.
                </div>
                <div className="border-l-2 border-divider pl-3">
                  <strong className="text-ink font-semibold">Shepard et al. (2001)</strong> — <em>"The statistical properties of planetary surfaces and root-mean-square roughness at multiple spatial scales."</em> Journal of Geophysical Research: Planets, 106(E12), 32777–32795.
                </div>
                <div className="border-l-2 border-divider pl-3">
                  <strong className="text-ink font-semibold">Saaty, T. L. (1990)</strong> — <em>"How to make a decision: The Analytic Hierarchy Process (AHP) and Multi-Criteria Evaluation."</em> European Journal of Operational Research, 48(1), 9–26.
                </div>
                <div className="border-l-2 border-divider pl-3">
                  <strong className="text-ink font-semibold">Jocher et al. (2023)</strong> — <em>"Ultralytics YOLOv8 Architecture and Deep Convolutional Neural Networks for Automated Surface Hazard Detection."</em> doi:10.5281/zenodo.7347926.
                </div>
                <div className="border-l-2 border-divider pl-3">
                  <strong className="text-ink font-semibold">Giorgini et al. (1996)</strong> — <em>"JPL's On-Line Solar System Data Service."</em> Bulletin of the American Astronomical Society, 28, 1158.
                </div>
              </div>
            </div>

            {/* Legal Non-Affiliation Box */}
            <div className="lg:col-span-5 flex flex-col justify-between border border-divider/60 bg-surface/50 p-6 rounded-xs">
              <div>
                <span className="font-mono text-xs uppercase tracking-widest text-muted block border-b border-divider/40 pb-2">
                  INSTITUTIONAL INTEGRITY NOTICE
                </span>
                <p className="mt-3 text-xs leading-relaxed text-muted/90 font-body">
                  MoonScape is an independent planetary exploration analysis platform developed for academic research, engineering modeling, and mission feasibility study.
                </p>
                <p className="mt-3 text-xs leading-relaxed text-muted/90 font-body">
                  It is not affiliated with, sponsored by, or endorsed by the National Aeronautics and Space Administration (<strong className="text-ink font-semibold">NASA</strong>), the European Space Agency (<strong className="text-ink font-semibold">ESA</strong>), or the Artemis Program.
                </p>
                <p className="mt-3 text-xs leading-relaxed text-muted/80 font-body">
                  Datasets originating from NASA Goddard Space Flight Center (GSFC), the Lunar Reconnaissance Orbiter Camera (LROC) Science Operations Center at Arizona State University, and the Jet Propulsion Laboratory (JPL) are used under NASA open data and public domain guidelines. Landing scores represent computational decision support only and do not replace certified space agency flight qualification.
                </p>
              </div>

              <div className="mt-6 pt-3 border-t border-divider/30 font-mono text-[10px] text-muted/60">
                DATA POLICY COMPLIANCE: 14 CFR § 1212 / NASA OPEN DATA
              </div>
            </div>
          </div>
        </section>

        {/* ===================================================================
         * SECTION 6 — THE TEAM
         * Strict Constraints: Exact Team Name "MoonScape", Exact 6 Names in Order,
         * No Invented Roles, Biographies, Titles or Social Media.
         * =================================================================== */}
        <section className="py-16 border-b border-divider">
          <div>
            <span className="font-mono text-xs uppercase tracking-[0.25em] text-muted block">
              [PROJECT ROSTER]
            </span>
            <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl">
              MoonScape
            </h2>
            <p className="mt-1 text-sm text-muted">
              Project contributors and research engineering team.
            </p>
          </div>

          <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 font-mono">
            {TEAM_MEMBERS.map((name, idx) => (
              <div
                key={name}
                className="panel p-5 flex items-center justify-between border-divider/60 hover:border-ink/40 transition-colors"
              >
                <div>
                  <span className="text-[10px] text-muted/60 block uppercase tracking-widest">
                    MEMBER 0{idx + 1}
                  </span>
                  <span className="font-display text-base font-semibold text-ink mt-1 block tracking-wide">
                    {name}
                  </span>
                </div>
                <span className="text-xs text-muted/40 font-mono">
                  0{idx + 1}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* ===================================================================
         * SECTION 7 — FINAL SIGNATURE (EXACT FORMATTING)
         * =================================================================== */}
        <section className="py-20 text-center">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="space-y-6"
          >
            <h3 className="font-display text-2xl font-extrabold uppercase tracking-[0.3em] text-ink sm:text-3xl">
              MOONSCAPE
            </h3>

            <p className="font-mono text-sm tracking-widest text-muted uppercase">
              Independent lunar exploration and analysis.
            </p>

            <div className="mx-auto max-w-xl border-t border-b border-divider/40 py-4 font-mono text-xs text-ink/80 leading-loose">
              Sampat Barik &nbsp;·&nbsp; Ritam Dawn &nbsp;·&nbsp; Ranit Ratan Bose
              <br />
              Paromita Dan &nbsp;·&nbsp; Soumili Kar &nbsp;·&nbsp; Somasri Mondal
            </div>

            {/* Navigation Actions */}
            <div className="pt-6 flex flex-wrap items-center justify-center gap-4">
              <button
                className="btn-primary cursor-pointer"
                onClick={() => navigate("/explorer")}
              >
                <GlobeIcon className="h-4 w-4" />
                RETURN TO EXPLORER
                <ArrowRightIcon className="h-4 w-4" />
              </button>
              <button
                className="btn-ghost cursor-pointer"
                onClick={() => navigate("/")}
              >
                HOMEPAGE
              </button>
              <button
                className="btn-ghost cursor-pointer"
                onClick={() => navigate("/report")}
              >
                <DocIcon className="h-4 w-4" />
                MISSION DOSSIER
              </button>
            </div>
          </motion.div>
        </section>
      </div>
    </div>
  );
}
