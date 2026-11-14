# Lunar South Pole Illumination Analysis Guide
## Moonscape Phase 5: Scientific Solar Geometry, Topographic Shadowing, and Thermal Environment

> **Document Version:** 1.0.0  
> **Target Audience:** Planetary Scientists, Mission Planners, Backend Engineers  
> **Applicable Services:** `Backend/app/services/illumination.py`, `Backend/services/illumination.py`  
> **API Endpoints:** `POST /api/analysis/run`, `GET /api/terrain`  
> **Status:** Live & Tested (76/76 Automated Tests Passing)

---

## 1. Executive Summary & Objective

In **Moonscape Phase 5**, we developed a scientifically defensible illumination engine for candidate Artemis landing sites near the lunar South Pole. 

Because the Moon's spin axis is inclined by only $1.5424^\circ$ relative to the ecliptic normal, the Sun never rises high in the polar sky—it skims the horizon at maximum elevations between $+1.5^\circ$ and $-1.5^\circ$. Consequently, long-duration solar illumination is concentrated exclusively on elevated crater rims and mountain massifs (e.g., Shackleton Connecting Ridge, Malapert Mountain), while nearby depressions remain in permanent darkness.

This service provides:
1. **Instantaneous Solar Geometry & Horizon Ray Tracing:** Exact Sun position vector and local DEM ray-tracing shadow detection for any requested UTC epoch.
2. **Cumulative Multi-Year Illumination Modeling:** Peer-reviewed LOLA multi-year precession baseline ground truth for mission power planning.
3. **Permanently Shadowed Region (PSR) Detection:** Identification of cryogenic volatile-bearing cold traps.
4. **Thermal Brightness Environment:** Radiative equilibrium temperature estimation, with strict distinction between thermal radiance and direct optical sunlight.

---

## 2. Investigation of NASA Data Sources (Task 1)

| NASA Data Source | Data Type & Physical Measurement | Scientific Capability | Critical Limitations & Boundaries |
| :--- | :--- | :--- | :--- |
| **NASA LRO Diviner (DLRE)** | **Thermal Radiance / Brightness Temperature ($T_{bol}$ in Kelvin)**<br>Channels 3–9 ($7.55\,\mu\text{m}$ to $>400\,\mu\text{m}$). | Identifies cryogenic thermal stability zones and Permanently Shadowed Regions (PSRs) maintaining $T_{\max} < 110\text{ K}$ (water-ice stability) or $< 54\text{ K}$ (volatile methane/ammonia traps). | **NON-SUNLIGHT MEASUREMENT.** Governed by secondary scattered infrared re-radiation and regolith thermal inertia. **Must NEVER be treated as direct optical sunlight percentage.** |
| **NASA LRO LOLA Illumination Products** | **Modeled Optical Sunlight Fraction**<br>(Mazarico et al. 2011; Barker et al. 2021; Gläser et al. 2014). | Simulates spatiotemporal solar visibility over an 18.6-year draconic precession cycle using high-resolution DEMs. | Models assume idealized solar disk geometry; local sub-pixel micro-topography (< 5m) is unmodeled. |
| **NASA SPICE Kernels / NAIF Geometry** | **Planetary Ephemeris & Geodetic Geometry**<br>(DE421 / DE440 ephemerides, `MOON_ME` body-fixed frame). | Computes sub-solar coordinates $(\delta_{\odot}, \lambda_{\odot})$, Sun-Moon distance (AU), and unocculted spherical elevation angle $\alpha_{\text{sun}}$ for any UTC epoch. | Calculates geometry relative to a smooth reference sphere or ellipsoid. **Lacks topographic mountain shadowing without a paired DEM.** |
| **NASA PGDA Product 104 / LROC NAC Mosaics** | **Photoclinometry & Repeat Optical Imaging**<br>(Speyerer et al. 2016). | Empirical multi-epoch optical observations measuring temporal fraction of detected surface brightness. | Optical mosaics are affected by camera exposure, stray light, and limb reflectance artifacts. |

---

## 3. Four Distinct Illumination Regimes (Task 2)

A common mistake in lunar data engineering is conflating instantaneous sunlight with multi-year cumulative averages or thermal brightness. Moonscape enforces strict scientific boundaries among four distinct phenomena:

```
+---------------------------------------------------------------------------------------------------+
|                                  LUNAR POLAR SURFACE ENVIRONMENT                                  |
+---------------------------------------------------------------------------------------------------+
|  1. Instantaneous Horizon Geometry  |  Evaluated at a discrete UTC epoch t. Computed via          |
|     (Direct Sunlight vs. Shadow)    |  analytical solar ephemeris and DEM horizon ray-tracing.    |
|-------------------------------------+-------------------------------------------------------------|
|  2. Cumulative Temporal Modeling    |  Evaluated over a multi-year baseline (e.g. 18.6-year       |
|     (Solar Power Availability)      |  draconic precession cycle). Expressed as cumulative %.    |
|-------------------------------------+-------------------------------------------------------------|
|  3. Permanently Shadowed Regions    |  Topographic depressions where horizon angle > 1.81 deg     |
|     (PSRs / Cold Traps)             |  in all azimuthal directions; zero sunlight for > 10^9 yrs. |
|-------------------------------------+-------------------------------------------------------------|
|  4. Thermal Brightness Environment  |  Surface brightness temperature (Kelvin) measured by        |
|     (Diviner Radiometry)            |  Diviner DLRE. Governed by infrared radiative equilibrium.  |
+---------------------------------------------------------------------------------------------------+
```

---

## 4. Mathematical Methodology (Task 3)

### 4.1 Instantaneous Ephemeris Formulation
At epoch timestamp $t$, Julian centuries from J2000.0 are:
$$T = \frac{JD - 2451545.0}{36525.0}$$

Using JPL DE421 celestial mechanics, the Sun's ecliptic longitude $\odot_{\text{long}}$, ascending node $\Omega$, and lunar mean longitude $L'$ are evaluated. The sub-solar latitude on the Moon ($\delta_{\odot}$) follows Cassini's second law:
$$\delta_{\odot} = -I \cdot \sin(\odot_{\text{long}} - \Omega)$$
where $I = 1.5424^\circ$ is the inclination of the lunar equator to the ecliptic.

For any surface coordinate $(\phi, \lambda)$, the spherical solar elevation $\alpha_{\text{sph}}$ and azimuth $\phi_{\text{sun}}$ (clockwise from true North) are:
$$\sin(\alpha_{\text{sph}}) = \sin(\phi)\sin(\delta_{\odot}) + \cos(\phi)\cos(\delta_{\odot})\cos(\lambda - \lambda_{\odot})$$

### 4.2 Topographic Horizon Ray Tracing
Topography at the South Pole dominates illumination. To determine if local mountains block the Sun, a ray is cast along solar azimuth $\phi_{\text{sun}}$ across the DEM:
$$\theta_k = \arctan\left(\frac{z_k - z_0}{d_k}\right) - \frac{d_k}{2 R_{\text{moon}}}$$
where $d_k$ is distance in meters, $z_k$ is elevation, and $R_{\text{moon}} = 1,737,400\text{ m}$ corrects for lunar spherical curvature.

The maximum horizon angle is $\theta_{\text{horizon}} = \max_k \theta_k$. Accounting for the solar angular semi-diameter ($\rho_{\odot} \approx 0.2665^\circ$):
- **Full Direct Sunlight ($100\%$):** $\alpha_{\text{sph}} \ge \theta_{\text{horizon}} + \rho_{\odot}$
- **Full Topographic Shadow ($0\%$):** $\alpha_{\text{sph}} \le \theta_{\text{horizon}} - \rho_{\odot}$
- **Penumbra / Grazing Limb:** Partial disk visibility fraction $f \in (0.0, 1.0)$.

### 4.3 Cumulative Illumination & Data Integrity
For cataloged candidate landing sites (e.g. Shackleton Connecting Ridge, Malapert Mountain, Nobile Crater Rim), peer-reviewed LOLA multi-year cumulative percentages (Barker et al. 2021) are retrieved.
> **Scientific Integrity Mandate:** If an uncataloged point lacks a precomputed multi-year raster, `cumulative_illumination_pct` is strictly reported as `null` with an explanatory caveat. Numbers are **never fabricated**.

---

## 5. API Response Structure (Task 4)

Endpoint: `POST /api/analysis/run`

```json
{
  "analysis_id": "ANL-A1B2C3D4",
  "center_lat": -89.46,
  "center_lon": 222.0,
  "radius_meters": 1000.0,
  "illumination": {
    "status": "available",
    "solar_elevation_deg": 1.15,
    "solar_azimuth_deg": 218.4,
    "instantaneous_sunlit_fraction_pct": 100.0,
    "cumulative_illumination_pct": 86.4,
    "time_period_evaluated": "LRO LOLA multi-year draconic precession baseline (Barker et al. 2021) correlated to Shackleton Connecting Ridge",
    "is_permanently_shadowed_region": false,
    "estimated_surface_temp_k": 188.2,
    "sunlight_continuous_hours_max": 612.3,
    "methodology": "Dual-component scientific illumination: (1) Instantaneous analytical solar ephemeris with local DEM horizon ray-tracing, combined with (2) Peer-reviewed LOLA multi-year precession cumulative ground truth.",
    "source_attribution": "NASA LRO LOLA / Diviner / JPL DE421 Ephemeris",
    "scientific_caveats": [
      "SCIENTIFIC NOTICE: Surface temperature (Kelvin) is a thermal brightness measurement governed by secondary radiative equilibrium and regolith thermal inertia. It is NOT a direct optical sunlight percentage measurement."
    ]
  }
}
```

---

## 6. Scientific Limitations & Domain Boundaries

1. **Horizon Ray Baseline:** Ray-tracing is conducted within the local DEM bounding window ($\ge 2.5\text{ km}$ to $25\text{ km}$). Distant mountain massifs located $> 50\text{ km}$ away require regional 80m DEM tiles.
2. **Precession Seasonal Drift:** Because of the Moon's 18.6-year draconic precession, southern lunar summer drifts relative to the Gregorian calendar (e.g., in 2026, peak southern summer occurs around May, not December).
3. **Diviner Thermal Brightness:** Temperatures reported in Kelvin reflect bolometric energy balance, not optical illumination. Cryogenic cold traps ($T < 110\text{ K}$) remain cold even if exposed to grazing micro-flashes of sunlight.
