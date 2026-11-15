# MoonScape — Lunar Hazard Annotation Protocol & Guidelines

**Document ID:** `DOC-HAZ-GUIDE-2026-002`  
**Target Modalities:** LROC NAC Panchromatic Nadir Orbital Imagery ($1.2\text{ m/pixel}$ to $1.8\text{ m/pixel}$) & Chandrayaan-2 OHRC ($0.25\text{ m/pixel}$)  
**Target Classes:** Class 0 (`crater`), Class 1 (`boulder`)  
**Status:** Certified Planetary Science Annotation Standard  

---

## 1. Scientific Objectives & Safety-Critical Philosophy

In lunar landing-site qualification, unmapped hazards pose catastrophic mission risks:
1. **Crater Bowls:** Structural slopes exceeding landing-gear slope limits ($> 12^\circ$ to $15^\circ$) or deep bowls causing footpad drop-off and vehicle tip-over.
2. **Boulders / Rocky Ejecta:** Surface rocks exceeding vehicle ground clearance ($> 0.3\text{ m}$ to $0.5\text{ m}$) capable of puncturing tanks, crushing engine bells, or inducing landing gear shear failure.

The annotation protocol enforces **scientific truthfulness**: every bounding box represents a verified physical morphological object rather than an unverified pixel anomaly.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       OPTICAL HAZARD ANNOTATION RULES                       │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ CLASS 0 · CRATER                     │ CLASS 1 · BOULDER                    │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ • Rim-to-rim outer crest box         │ • Sun-facing facet + shadow pair     │
│ • Must show concave shadow profile   │ • Shadow must align with sun azimuth │
│ • Delineate degraded & sharp rims    │ • Min size: ≥ 1.0 physical pixel     │
│ • Sub-pixel depressions excluded     │ • Topographic rubble piles EXCLUDED  │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. Crater Delineation Protocol (Class 0)

### 2.1 Geometric Boundary Definition
* The bounding box must span the **outer diameter of the raised rim crest**.
* When grazing sunlight illuminates one rim wall while casting the opposing wall in shadow, the box must enclose the complete circular/elliptical perimeter defined by the rim crest line, not merely the shadow patch.
* **Degraded Craters:** Craters with eroded, rounded rims should be included if their depression morphology is discernible from context lighting.
* **Minimum Resolvable Diameter:**
  - In $1.2\text{ mpp}$ imagery: $D_{\text{min}} = 6.0\text{ m}$ (5 physical pixels).
  - Features smaller than 4 pixels cannot be reliably distinguished from micro-roughness noise.

### 2.2 Rejection Criteria for Craters
* Do NOT annotate broad regional tectonic valleys, grabens, or inter-mountain depressions as craters.
* Do NOT annotate craters whose boundaries are entirely contained within permanent shadow unless secondary scattered light reveals rim morphology.

---

## 3. Boulder Delineation Protocol (Class 1)

### 3.1 The Sun-Shadow Reflectance Pair Rule
A pixel cluster is certified as a physical boulder if and only if it exhibits the **canonical reflectance-shadow pair**:
1. **Bright Facet:** High-albedo reflectance pixel(s) facing the solar azimuth direction.
2. **Down-Sun Shadow:** An elongated zero-DN or near-zero shadow extending in the exact opposite direction of solar azimuth ($\phi_{\text{shadow}} = \phi_{\text{sun}} + 180^\circ$).

$$\text{Confidence} = f\left(\text{Facet Contrast}, \frac{L_{\text{shadow}}}{\tan(90^\circ - \theta_{\text{inc}})}, \Delta \phi_{\text{azimuth}}\right)$$

### 3.2 Bounding Box Enclosure
* The bounding box must tightly enclose the **rock facet AND its immediately contiguous shadow origin**.
* Do NOT extend the bounding box across the entire tip of an extremely elongated shadow cast down an incline; enclose the physical rock footprint and proximal shadow anchor.

### 3.3 Strict Prohibition on Topographic Roughness Conflation
* High elevation variance or RMS roughness from digital elevation models (LOLA DEM) indicates **surface terrain roughness**, NOT individual boulders.
* An annotator or automated pipeline must **NEVER** convert a DEM roughness anomaly into a boulder bounding box.
* Roughness anomalies are classified strictly as `topographic_hazards` in the altimetric processing tier.

---

## 4. Human-in-the-Loop Review & Validation Workflow

For extended South Pole regions ($-80^\circ$ to $-75^\circ$) and context regions ($-75^\circ$ to $-70^\circ$) where pre-existing ground truth is absent:

### 4.1 Annotation Task Generation
1. Automated proposal algorithms generate candidate bounding boxes with status `unreviewed_proposal` and `reviewed: false`.
2. Proposals are saved to `data/hazard_training/annotations/unreviewed_proposals/` alongside task metadata.

### 4.2 Human Review Checklist
Every proposal file includes an explicit four-point scientific checklist that human reviewers must validate before inclusion in official training splits:
* [ ] **Rim Crest Integrity:** Crater rim is clearly delineated and verified against local slope gradients.
* [ ] **Shadow-Sun Alignment:** Shadow azimuth exactly matches the observation ephemeris vector.
* [ ] **No Roughness Conflation:** Rocky cluster is physically distinct, not a diffuse rubble field.
* [ ] **Normalization Check:** Normalized coordinates $[x_{\text{center}}, y_{\text{center}}, w, h]$ strictly satisfy $[0.0, 1.0]$.

### 4.3 Data Formats
Annotations are maintained in standard YOLO normalized format (`.txt`):
```
<class_id> <x_center> <y_center> <width> <height>
```
With companion GeoJSON and metadata manifests linking each bounding box to original spacecraft observation frames and LOLA terrain metrics.
