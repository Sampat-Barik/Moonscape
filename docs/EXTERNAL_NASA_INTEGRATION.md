# NASA JPL Horizons, Moon Trek WMTS, and LROC QuickMap Integration Manual

**System:** Moonscape Lunar South Pole Landing Site Evaluation Platform  
**Architecture Status:** Production Grade / Live External NASA Integrated  
**Standards:** OGC WMTS 1.0.0, IAU 2000 / IAU MOON_ME, JPL Horizons API DE441  

---

## 1. Architectural Overview

Moonscape bridges high-performance local raster analysis (LOLA DEM, slope, roughness, and crater hazards) with three official NASA planetary computing services:

```
                                  +------------------------------------------+
                                  |            Moonscape Frontend            |
                                  |   (React 19 / Three.js / TypeScript)     |
                                  +--------------------+---------------------+
                                                       |
                                      REST API (Port 8000) & Tile Proxy
                                                       |
                                  +--------------------+---------------------+
                                  |         FastAPI Gateway & Core           |
                                  +----+---------------+---------------+-----+
                                       |               |               |
               +-----------------------+               |               +----------------------+
               |                                       |                                      |
               v                                       v                                      v
  +--------------------------+           +--------------------------+           +--------------------------+
  |    NASA JPL Horizons     |           |     NASA Moon Trek       |           |   NASA LROC QuickMap     |
  |  Ephemeris System        |           |  OGC WMTS Tile Engine    |           |   & PDS DTM Catalog      |
  +--------------------------+           +--------------------------+           +--------------------------+
  | • Topocentric Moon obs   |           | • LROC WAC Global Mosaic |           | • Artemis III candidate  |
  | • Body 301 coord frame   |           | • LROC NAC South Pole    |           |   stereo DTM footprints  |
  | • Solar/Earth Az & El    |           | • LOLA Polar Altimetry   |           | • Polar Stereographic    |
  | • DE441 Numerical Int.   |           | • LRU In-Memory Tile Cax |           |   interactive deep links |
  +--------------------------+           +--------------------------+           +--------------------------+
```

---

## 2. Ephemeris Coordinate Frames & Geodesy

### Planetary Observer Reference Frame: `coord@301`
Standard Earth-centered or solar system barycentric coordinates (ICRF) are fundamentally invalid for lunar surface landed assets. Lunar surface observers experience:
- Diurnal solar rotation of 29.53059 Earth days (synodic month).
- Extreme low solar elevation angles at polar latitudes ($0^\circ$ to $1.5^\circ$).
- Complex optical and physical lunar libration ($\pm 8^\circ$ in longitude, $\pm 6.7^\circ$ in latitude) creating nodding and swinging motions of the Earth above the local horizon.

### Geodesy Parameters
- **Lunar Center Body Code:** `301`
- **Observer Coordinate Type:** `GEODETIC` on the Moon's IAU reference ellipsoid:
  - Mean Equator / Principal Axis System (IAU MOON_ME)
  - Reference Mean Radius: $R_{moon} = 1737.400\text{ km}$
  - Polar Axis: $-90.0^\circ$ to $+90.0^\circ$ latitude
  - Positive Longitude: $0.0^\circ$ to $360.0^\circ$ East

---

## 3. NASA JPL Horizons Integration Specification

- **Endpoint URL:** `https://ssd.jpl.nasa.gov/api/horizons.api`
- **Method:** `GET` with structured query parameters.
- **Protocol:** HTTPS with SSL validation.

### Request Parameters
| Parameter | Value | Scientific Description |
| :--- | :--- | :--- |
| `format` | `json` | Structured JSON wrapper around tabular ephemeris block |
| `COMMAND` | `'10'` (Sun) or `'399'` (Earth) | Target celestial body identifier |
| `CENTER` | `'coord@301'` | Topocentric surface observer on body 301 (Moon) |
| `COORD_TYPE`| `'GEODETIC'` | Geodetic latitude, longitude, and elevation |
| `SITE_COORD`| `'<lon_east>,<lat>,<alt_km>'` | Positive East longitude (0–360°), latitude (-90 to +90°), altitude above 1737.4 km sphere |
| `START_TIME`| `'YYYY-MM-DD HH:MM'` | Beginning of observation temporal window in UTC |
| `STOP_TIME` | `'YYYY-MM-DD HH:MM'` | End of observation temporal window in UTC |
| `STEP_SIZE` | `'<step> h'` or `'<step> m'` | Query sampling interval |
| `QUANTITIES`| `'4,20'` | **Quantity 4:** Apparent Azimuth & Elevation; **Quantity 20:** Observer-target range & range rate |
| `REF_SYSTEM`| `'ICRF'` | Celestial reference system |
| `ANG_FORMAT`| `'DEG'` | Angles formatted as decimal degrees |

### Response Parsing
The ASCII block bounded between `$$SOE` (Start of Ephemeris) and `$$EOE` (End of Ephemeris) is extracted and parsed into `HorizonsEphemerisPoint` data models:
```
$$SOE
 2026-Nov-15 00:00     m  251.9213   1.3824  0.989123456789  0.01234
 2026-Nov-15 02:00     m  254.5120   1.4110  0.989123556789  0.01235
$$EOE
```
Columns parsed:
1. `Timestamp`: UTC Epoch (`YYYY-Mon-DD HH:MM`)
2. `Solar Presence / Moon Presence`: Lighting flag (`m` = refracted/apparent)
3. `Azimuth`: Degrees East of North ($0^\circ$ to $360^\circ$)
4. `Elevation`: Angle above local horizontal plane ($-90^\circ$ to $+90^\circ$)
5. `Distance`: Astronomical Units (AU) for Sun; kilometers for Earth
6. `Range Rate`: Target relative line-of-sight velocity in km/s

---

## 4. NASA Moon Trek WMTS Specification

- **Base Service Endpoint:** `https://trek.nasa.gov/moon/TrekServices/ws/index`
- **Capabilities Schema:** OGC WMTS 1.0.0 standard
- **Tile Matrix Set:** `default028mm` (standard standardized OGC pixel dimensions)

### Verified Layers Catalog
1. **LRO WAC Global Morphologic Mosaic:**
   - Layer ID: `trek_wac_global_mosaic`
   - Resolution: 100 meters/pixel (303 pixels per degree)
   - Projection: Equirectangular `EPSG::104903`
   - Template: `https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm/{z}/{y}/{x}.jpg`
2. **LRO NAC South Pole Mosaic:**
   - Layer ID: `trek_nac_south_pole_mosaic`
   - Resolution: 1.0 meter/pixel
   - Projection: Polar Stereographic `urn:ogc:def:crs:IAU2000::30120`
   - Coverage: $85.5^\circ\text{S}$ to $90.0^\circ\text{S}$
   - Template: `https://trek.nasa.gov/tiles/Moon/SP/LRO_NAC_Mosaic_SPole85.5_1mp/1.0.0/default/default028mm/{z}/{y}/{x}.png`
3. **LOLA Polar Laser Altimetric Shot Density:**
   - Layer ID: `trek_lola_count_south_pole`
   - Resolution: 5.0 meters/pixel
   - Projection: Polar Stereographic `urn:ogc:def:crs:IAU2000::30120`
   - Coverage: $87.5^\circ\text{S}$ to $90.0^\circ\text{S}$
   - Template: `https://trek.nasa.gov/tiles/Moon/SP/LRO_LOLA_Count_SPole875_5mp_v04/1.0.0/default/default028mm/{z}/{y}/{x}.png`

### Reverse Proxy & Tile Cache Endpoint
To avoid browser CORS blocks and provide instant response times:
`GET /api/external/moon-trek/tile/{layer_id}/{z}/{y}/{x}`
Proxies tiles directly to the client with upstream HTTP headers and caches image chunks in an in-memory bounded LRU cache (128 tiles capacity).

---

## 5. LROC QuickMap and Targeted DTM Archive Integration

- **QuickMap Portal:** `https://quickmap.lroc.im-ldi.com`
- **PDS RDR Archive:** `https://data.lroc.im-ldi.com/lroc/view_rdr/SHAPEFILE_NAC_DTMS`

### Deep Link URL Synthesis
For any selected South Pole coordinate, Moonscape generates an active polar stereographic projection deep link:
```
https://quickmap.lroc.im-ldi.com/?center={lon_180},{lat}&zoom=6&proj=southpole&layers=lroc_color_poles_85s
```
- Coordinate Format: Longitude in $-180^\circ$ to $+180^\circ$, latitude in $-90^\circ$ to $-80^\circ$.
- Projection Parameter: `proj=southpole` forces QuickMap into its official lunar South Pole stereographic viewer.

### Footprint Coverage Discovery
Moonscape references high-resolution stereo NAC DTM footprints across all 10 Artemis III candidate exploration zones (Shackleton Connecting Ridge, de Gerlache Rim, Haworth, Malapert Massif, Peak Near Shackleton).
- If coordinates fall inside a DTM bounding polygon: Reports `is_covered: true` with DTM product name, PDS archive URL, and optical hazard validation support.
- If outside all footprints: Calculates the geodetic distance in kilometers to the nearest NAC DTM centroid and surfaces a fallback recommendation.

---

## 6. Reliability, Caching, and Resilient Fallback Strategy

1. **Thread-Safe Bounded LRU Cache:**
   - Both Horizons ephemeris results and Moon Trek tiles are cached in Python `collections.OrderedDict` structures protected by re-entrant thread locks (`threading.Lock`).
   - Eviction policy: Oldest unused entry evicted when capacity (128 entries) is reached.
   - Cache hit latency: `< 1.0 ms`.
2. **Network Timeout & Circuit Isolation:**
   - Outbound HTTP requests use strict 10–12 second socket timeouts via `httpx`.
   - If NASA servers are unreachable, rate-limited, or offline:
     - Ephemeris simulation gracefully falls back to the local high-precision analytical ephemeris engine (`JPL DE421 / Meeus Analytical`).
     - Terrain analysis and hazard evaluation continue unaffected without disruption.
     - The response explicitly flags the active ephemeris provider (`Horizons` vs `Analytical`).

---

## 7. Frontend Integration & Usage Guide

1. **Basemap Layer Switching in 3D Map:**
   - Click the **BASEMAP / TREK WAC 100M** toggle in the top-right HUD of the Moonscape Explorer.
   - Instantly swaps between the default high-contrast lunar globe texture and the NASA Moon Trek controlled WAC Global Morphologic Mosaic at 100m/pixel.
2. **LROC NAC Stereo DTM & QuickMap Deep Link:**
   - In the Explorer sidebar, view the **NASA External Archives** section.
   - If the selected site is covered by an LROC NAC DTM, a green **COVERED** badge appears with product information.
   - Click **Open in LROC QuickMap ↗** to open the exact coordinates in Arizona State University's official polar QuickMap tool.
3. **Ephemeris Status Badge:**
   - Top-left HUD displays: `HORIZONS DE441 · MOON TREK WMTS` indicating live NASA celestial propagation.
