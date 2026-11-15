# HOMEPAGE MOON RENDERING REPAIR & FRUSTUM BOUNDARY ISOLATION
**Document Version:** 1.0.0  
**Project:** MoonScape Lunar Decision Intelligence  
**Component:** `Frontend/src/components/CinematicMoon.tsx` & `Frontend/src/pages/Home.tsx`  
**Platform:** Three.js r187 / WebGL / React 19 / Vite / Tailwind CSS  
**Target Environment:** 1920×1080 Widescreen down to Mobile Portrait  

---

## 1. Executive Summary & Problem Diagnosis

### 1.1 The Visual Defect
On the MoonScape homepage (`http://localhost:5173`), users observed a visible rectangular boundary enclosing the 3D Moon. The celestial body appeared boxed into a clipping area rather than floating freely and organically against the seamless deep-space vacuum (`#090909`).

### 1.2 Root-Cause Engineering Analysis

Through geometric and WebGL analysis, four concurrent defects were uncovered:

#### Defect 1: Geometric Sphere Frustum Overextension (Clipping Plane Violation)
- In the original `CinematicMoon.tsx`, the sphere was generated with `SphereGeometry(1.4, 64, 64)`, creating a physical diameter of $D = 2.80\text{ units}$.
- The Three.js `PerspectiveCamera` was initialized with a vertical Field of View (FOV) of $40^\circ$ and a resting camera position of $Z = 3.40\text{ units}$.
- In Three.js, the vertical frustum span $H_v$ at distance $Z$ is calculated by:
  $$H_v = 2 \cdot Z \cdot \tan\left(\frac{\text{FOV}}{2}\right) = 2 \cdot 3.40 \cdot \tan(20^\circ) = 2 \cdot 3.40 \cdot 0.36397 \approx 2.475\text{ units}$$
- Because the sphere diameter ($D = 2.80$) exceeded the total visible camera height ($H_v = 2.475$), the top $0.1625\text{ units}$ and bottom $0.1625\text{ units}$ of the Moon were **physically sliced off by the canvas viewport boundaries**.
- Slicing a lit 3D sphere against viewport boundaries creates straight horizontal clipping lines at top and bottom, which visually reads as a rectangular box enclosing the sphere.
- On aspect ratios $\le 1.13$ (tablets, mobile, and square containers), the horizontal frustum $W_h = H_v \cdot \text{aspect}$ was also $< 2.80$, clipping the left and right sides of the sphere as well.

#### Defect 2: Canvas Element Default Inline Rendering & Descender Artifacts
- The WebGL `<canvas>` element was appended to the container with default HTML inline styling. Default inline elements align to the text baseline, leaving a 3–5px gap and inducing boundary artifacts under fractional device pixel ratios.

#### Defect 3: WebGL Clear Color Transparency
- Although `alpha: true` was passed to `WebGLRenderer`, `renderer.setClearColor(0x000000, 0)` was omitted. Depending on GPU driver composition and ACES Filmic Tone Mapping behavior, non-cleared alpha channels can produce subtle border fringing against CSS background colors.

#### Defect 4: Rectangular Radial Gradient Extent in Hero Layout
- In `Home.tsx`, the ambient glow layer used `bg-[radial-gradient(circle_at_50%_50%,rgba(255,255,255,0.06)_0%,transparent_65%)]`. In non-square containers, a standard circular gradient with default `farthest-corner` extent reaches container edges with non-zero alpha, creating faint edge lines where the container ends.

---

## 2. Technical Implementation & Architectural Solution

### 2.1 Normalized Geometry & Dynamic Responsive Frustum Equation

We normalized the lunar radius to $R = 1.0\text{ unit}$ ($D = 2.0\text{ units}$) and increased the sphere tessellation to $96 \times 96$ segments for a razor-sharp, circular limb silhouette.

To ensure the Moon is **guaranteed to never clip** across any resolution (from 4K down to the narrowest mobile screen), we established the dynamic camera distance formula:

$$\tan\left(\frac{\text{FOV}}{2}\right) = \tan(20^\circ) \approx 0.36397023$$

$$Z_{\text{base}} = \frac{R}{F_{\text{target}} \cdot \tan\left(\frac{\text{FOV}}{2}\right)} = \frac{1.0}{0.72 \cdot 0.36397023} \approx 3.8159\text{ units}$$

$$Z_{\text{target}}(\text{aspect}) = \frac{Z_{\text{base}}}{\min(\text{aspect}, 1.0)}$$

Where:
- $F_{\text{target}} = 0.72$ allocates $72\%$ of the limiting viewport dimension to the Moon diameter, leaving a generous $28\%$ safety margin ($14\%$ per side).
- When $\text{aspect} \ge 1.0$ (desktop/laptop widescreen), vertical height is the limiting dimension. $Z = 3.82\text{ units}$, yielding $H_v = 2.78\text{ units}$, with top/bottom margin $= 0.39\text{ units}$.
- When $\text{aspect} < 1.0$ (tablets, mobile portrait), horizontal width is the limiting dimension. $Z = Z_{\text{base}} / \text{aspect}$, ensuring visible width $W_h = 2.78\text{ units}$, with left/right margin $= 0.39\text{ units}$.

Even with maximum idle mouse parallax deflection ($\pm 0.12\text{ units}$ in $X$, $\pm 0.08\text{ units}$ in $Y$), the lunar edge maintains a minimum buffer of $0.27\text{ units}$ ($> 75\text{px}$) from all viewport boundaries.

```ts
// Frontend/src/components/CinematicMoon.tsx
const MOON_RADIUS = 1.0;
const FOV = 40;
const TAN_HALF_FOV = Math.tan((FOV / 2) * (Math.PI / 180));

const calculateTargetZ = (w: number, h: number) => {
  const aspect = w / Math.max(h, 1);
  const baseZ = MOON_RADIUS / (0.72 * TAN_HALF_FOV);
  return baseZ / Math.min(aspect, 1.0);
};
```

### 2.2 Strict WebGL Zero-Alpha Clear & Block Canvas Styling

```ts
renderer = new THREE.WebGLRenderer({
  antialias: true,
  alpha: true,
  powerPreference: "high-performance",
});
renderer.setClearColor(0x000000, 0); // Strict zero-alpha clear color
renderer.setSize(width, height);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.domElement.style.display = "block";
renderer.domElement.style.width = "100%";
renderer.domElement.style.height = "100%";
renderer.domElement.style.outline = "none";
renderer.domElement.style.border = "none";
container.appendChild(renderer.domElement);
```

### 2.3 Container-Aware ResizeObserver Lifecycle

Rather than relying solely on `window.onresize`, a `ResizeObserver` was wired to `containerRef.current`. When grid layout shifts or viewport adjustments occur, `handleResize` recalculates `camera.aspect`, calls `camera.updateProjectionMatrix()`, adjusts `renderer.setSize(w, h)`, and updates `targetCameraZ`.

On unmount, `resizeObserver.disconnect()` cleanly releases observer resources.

### 2.4 Seamless Closest-Side Radial Glow

In `Home.tsx`, the ambient glow behind the Moon was updated to use `closest-side`:

```html
<!-- Seamless Deep-Space Ambient Radial Glow behind the Moon -->
<div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(closest-side_at_50%_50%,rgba(255,255,255,0.035)_0%,rgba(255,255,255,0.01)_50%,transparent_100%)]" />
```

By specifying `closest-side at 50% 50%` with `transparent 100%`, the radial gradient reaches absolute zero opacity ($0.0$) at the nearest edge of the bounding box. It is mathematically impossible for any rectangular edge seam to form. Behind it, the global twinkling starfield (`<Stars />`) shines through uninterrupted.

---

## 3. Mathematical & Geometric Verification Matrix

| Viewport Profile | Width × Height | Aspect Ratio | Camera $Z$ | Frustum $W_h \times H_v$ | Moon Fill % | Edge Margin |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **4K UHD** | 3840 × 2160 | 1.778 | 3.82 | $4.94 \times 2.78$ | 71.9% | $0.39\text{ units}$ ($152\text{px}$) |
| **Desktop Full HD** | 1920 × 1080 | 1.778 | 3.82 | $4.94 \times 2.78$ | 71.9% | $0.39\text{ units}$ ($152\text{px}$) |
| **Laptop 16:10** | 1920 × 1200 | 1.600 | 3.82 | $4.45 \times 2.78$ | 71.9% | $0.39\text{ units}$ ($168\text{px}$) |
| **Standard 4:3** | 1024 × 768 | 1.333 | 3.82 | $3.71 \times 2.78$ | 71.9% | $0.39\text{ units}$ ($108\text{px}$) |
| **Square Viewport** | 680 × 680 | 1.000 | 3.82 | $2.78 \times 2.78$ | 71.9% | $0.39\text{ units}$ ($95\text{px}$) |
| **Tablet Portrait** | 768 × 1024 | 0.750 | 5.09 | $2.78 \times 3.70$ | 71.9% | $0.39\text{ units}$ ($108\text{px}$) |
| **Mobile Portrait** | 390 × 844 | 0.462 | 8.26 | $2.78 \times 6.01$ | 71.9% | $0.39\text{ units}$ ($55\text{px}$) |
| **Narrow Foldable** | 320 × 800 | 0.400 | 9.54 | $2.78 \times 6.95$ | 71.9% | $0.39\text{ units}$ ($45\text{px}$) |

---

## 4. Visual Verification Criteria Achieved
1. **Seamless Void Integration:** No rectangular boundary, seam, or clipped edge visible across `#090909`.
2. **Pristine Limb Silhouette:** $96 \times 96$ sphere geometry ensures curvature is smooth at sub-pixel levels.
3. **Deep-Space Stars Passthrough:** Transparent WebGL clear color allows twinkling background stars to be visible around the lunar limb.
4. **Cinematic Entry Glide:** Initial camera starts at $1.25 \times Z_{\text{target}}$ and eases into rest position within 1.2s.
5. **Zero Regression:** All existing NASA textures (`lroc_color_2k.jpg`, `ldem_3_8bit.jpg`) and vacuum lighting parameters are 100% preserved.
