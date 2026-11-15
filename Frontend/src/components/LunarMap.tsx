/**
 * LunarMap — interactive 3D Moon rendered with three.js.
 *
 * Features:
 *  - textured sphere (real lunar map texture with CDN fallback chain and a
 *    procedural canvas fallback so the map always renders),
 *  - drag to rotate, wheel to zoom, click to pick lat/lon (raycast),
 *  - candidate-site markers, a selected-site marker with a pulsing ring,
 *  - graticule lines and a highlighted South Pole ring + label,
 *  - "fly to South Pole" animation (focusSouthPoleSignal),
 *  - "fly to any lat/lon" animation (focusSiteSignal),
 *  - optional auto-rotation.
 *
 * Coordinate convention (matches three.js SphereGeometry UVs, so the texture
 * aligns with the coordinates): lon 0° is at the centre of the texture.
 */
import { useEffect, useRef } from "react";
import * as THREE from "three";

export interface MapMarker {
  lat: number;
  lon: number;
  label?: string;
  color?: string;
}

export interface LunarMapProps {
  selected?: { lat: number; lon: number } | null;
  markers?: MapMarker[];
  onSelect?: (lat: number, lon: number) => void;
  /** false = display-only (no picking / rotating). Default true. */
  interactive?: boolean;
  autoRotate?: boolean;
  /** Increment this value to trigger the fly-to-South-Pole animation. */
  focusSouthPoleSignal?: number;
  /** Set this to animate camera to a specific lat/lon (nonce must change to trigger). */
  focusSiteSignal?: { lat: number; lon: number; nonce: number };
  /** Start with the camera over the South Pole. */
  initialSouthPole?: boolean;
  /** Solar azimuth/diurnal simulation angle in degrees (0–360). */
  sunAngle?: number;
  className?: string;
}

const D2R = Math.PI / 180;

/** lat/lon (degrees, lon in [-180, 180]) → point on a unit sphere. */
function latLonToVec3(lat: number, lon: number, r: number): THREE.Vector3 {
  const theta = (90 - lat) * D2R;
  const phi = (lon + 180) * D2R;
  return new THREE.Vector3(
    -Math.cos(phi) * Math.sin(theta),
    Math.cos(theta),
    Math.sin(phi) * Math.sin(theta)
  ).multiplyScalar(r);
}

/** Inverse of latLonToVec3. */
function vec3ToLatLon(v: THREE.Vector3): { lat: number; lon: number } {
  const len = v.length() || 1;
  const lat = 90 - Math.acos(THREE.MathUtils.clamp(v.y / len, -1, 1)) / D2R;
  let lon = Math.atan2(v.z, -v.x) / D2R - 180;
  lon = ((lon + 540) % 360) - 180;
  return { lat, lon };
}

/** Compute the quaternion that rotates the Moon so lat/lon faces the camera. */
function quatForLatLon(lat: number, lon: number): THREE.Quaternion {
  // The camera looks from +Z. We want the latLonToVec3 point to face +Z.
  const target = latLonToVec3(lat, lon, 1).normalize();
  return new THREE.Quaternion().setFromUnitVectors(target, new THREE.Vector3(0, 0, 1));
}

// Real lunar map textures (equirectangular). First reachable one is used;
// if all fail, a procedural canvas texture is generated as a last resort.
const TEXTURE_URLS = [
  "/assets/textures/lroc_color_2k.jpg",
  "/assets/textures/moon-2k.jpg",
  "https://raw.githubusercontent.com/Shriisoot/Planets-texture/master/2k_moon.jpg",
  "https://cdn.jsdelivr.net/gh/mrdoob/three.js@r160/examples/textures/planets/moon_1024.jpg",
];

const BUMP_TEXTURE_URL = "/assets/textures/ldem_3_8bit.jpg";

function makeDotTexture(color: string, size = 64): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d")!;
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, "#ffffff");
  g.addColorStop(0.28, color);
  g.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function makeRingTexture(color: string, size = 128): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d")!;
  ctx.strokeStyle = color;
  ctx.lineWidth = size * 0.055;
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size * 0.42, 0, Math.PI * 2);
  ctx.stroke();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function makeLabelTexture(text: string, color = "#58D9F2"): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 96;
  const ctx = c.getContext("2d")!;
  ctx.font = "600 46px 'Space Grotesk', sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.shadowColor = "rgba(88,217,242,0.9)";
  ctx.shadowBlur = 18;
  ctx.fillStyle = color;
  ctx.fillText(text, 256, 48);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** Last-resort texture if no CDN texture can be loaded (offline mode). */
function makeProceduralMoonTexture(): THREE.CanvasTexture {
  const w = 1024;
  const h = 512;
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const ctx = c.getContext("2d")!;
  ctx.fillStyle = "#8f9096";
  ctx.fillRect(0, 0, w, h);
  let seed = 1337;
  const rand = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  for (let i = 0; i < 46; i++) {
    ctx.fillStyle = `rgba(52,54,60,${0.1 + rand() * 0.22})`;
    ctx.beginPath();
    ctx.ellipse(
      rand() * w,
      h * 0.25 + rand() * h * 0.5,
      30 + rand() * 130,
      15 + rand() * 60,
      rand() * Math.PI,
      0,
      Math.PI * 2
    );
    ctx.fill();
  }
  for (let i = 0; i < 900; i++) {
    const x = rand() * w;
    const y = rand() * h;
    const r = 1 + rand() * 7;
    ctx.fillStyle = "rgba(30,30,34,0.35)";
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(220,222,228,0.35)";
    ctx.beginPath();
    ctx.arc(x - r * 0.3, y - r * 0.3, r * 0.55, 0, Math.PI * 2);
    ctx.fill();
  }
  for (let i = 0; i < 6000; i++) {
    ctx.fillStyle = rand() > 0.5 ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.08)";
    ctx.fillRect(rand() * w, rand() * h, 1.4, 1.4);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export default function LunarMap(props: LunarMapProps) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const propsRef = useRef(props);
  propsRef.current = props;
  const apiRef = useRef<{ focusSouthPole: () => void; focusSite: (lat: number, lon: number) => void; syncMarkers: () => void } | null>(null);

  const { markers, selected, focusSouthPoleSignal, focusSiteSignal } = props;

  // Re-sync markers when markers/selected change.
  useEffect(() => {
    apiRef.current?.syncMarkers();
  }, [markers, selected]);

  // Fly to the South Pole when the signal increments.
  useEffect(() => {
    if (focusSouthPoleSignal && focusSouthPoleSignal > 0) apiRef.current?.focusSouthPole();
  }, [focusSouthPoleSignal]);

  // Fly to a specific site when the nonce changes.
  useEffect(() => {
    if (focusSiteSignal && focusSiteSignal.nonce > 0) {
      apiRef.current?.focusSite(focusSiteSignal.lat, focusSiteSignal.lon);
    }
  }, [focusSiteSignal]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      42,
      mount.clientWidth / Math.max(mount.clientHeight, 1),
      0.1,
      100
    );
    camera.position.set(0, 0.35, 2.9);

    // Lighting: hemisphere for subtle sky fill + directional sun + subtle fill
    const hemi = new THREE.HemisphereLight(0x9fb8d4, 0x1a2a3a, 0.45);
    scene.add(hemi);
    const sun = new THREE.DirectionalLight(0xfff8f0, 2.6);
    sun.position.set(4, 1.5, 2.8);
    scene.add(sun);
    const fill = new THREE.DirectionalLight(0x2255aa, 0.28);
    fill.position.set(-3, -1, -2);
    scene.add(fill);

    const group = new THREE.Group();
    scene.add(group);

    const moonMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1, metalness: 0 });
    const moon = new THREE.Mesh(new THREE.SphereGeometry(1, 128, 128), moonMat);
    group.add(moon);

    // --- texture with fallback chain & LOLA elevation bump map ----------
    const loader = new THREE.TextureLoader();
    loader.setCrossOrigin("anonymous");
    const applyTexture = (tex: THREE.Texture) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
      moonMat.map = tex;
      moonMat.needsUpdate = true;
    };
    let urlIndex = 0;
    const tryNextTexture = () => {
      if (urlIndex < TEXTURE_URLS.length) {
        const url = TEXTURE_URLS[urlIndex++];
        loader.load(url, applyTexture, undefined, () => tryNextTexture());
      } else {
        applyTexture(makeProceduralMoonTexture());
      }
    };
    tryNextTexture();

    // Load NASA LOLA Digital Elevation Model bump map for realistic topographic relief
    loader.load(
      BUMP_TEXTURE_URL,
      (bumpTex) => {
        bumpTex.colorSpace = THREE.NoColorSpace;
        moonMat.bumpMap = bumpTex;
        moonMat.bumpScale = 0.035;
        moonMat.needsUpdate = true;
      },
      undefined,
      () => {
        /* bump map optional, graceful fallback */
      }
    );

    // --- graticule (lat/lon grid lines) -----------------------------------
    const gratPoints: number[] = [];
    for (let lat = -60; lat <= 60; lat += 30) {
      for (let lon = -180; lon < 180; lon += 5) {
        const v = latLonToVec3(lat, lon, 1.002);
        gratPoints.push(v.x, v.y, v.z);
      }
    }
    for (let lon = -180; lon < 180; lon += 30) {
      for (let lat = -88; lat < 90; lat += 5) {
        const v = latLonToVec3(lat, lon, 1.002);
        gratPoints.push(v.x, v.y, v.z);
      }
    }
    const gratGeo = new THREE.BufferGeometry();
    gratGeo.setAttribute("position", new THREE.Float32BufferAttribute(gratPoints, 3));
    group.add(
      new THREE.LineSegments(
        gratGeo,
        new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.09 })
      )
    );

    // --- South Pole highlight ring + label --------------------------------
    const ringPoints: number[] = [];
    for (let lon = -180; lon <= 180; lon += 4) {
      const v = latLonToVec3(-87.5, lon, 1.004);
      ringPoints.push(v.x, v.y, v.z);
    }
    const ringGeo = new THREE.BufferGeometry();
    ringGeo.setAttribute("position", new THREE.Float32BufferAttribute(ringPoints, 3));
    group.add(
      new THREE.Line(
        ringGeo,
        new THREE.LineBasicMaterial({ color: 0x58D9F2, transparent: true, opacity: 0.55 })
      )
    );
    const spLabel = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: makeLabelTexture("SOUTH POLE"), transparent: true, depthWrite: false })
    );
    spLabel.position.copy(latLonToVec3(-90, 0, 1.06));
    spLabel.scale.set(0.5, 0.094, 1);
    group.add(spLabel);

    // --- markers -----------------------------------------------------------
    const markerGroup = new THREE.Group();
    group.add(markerGroup);
    const syncMarkers = () => {
      markerGroup.clear();
      const { markers: ms = [], selected: sel } = propsRef.current;
      for (const m of ms) {
        const s = new THREE.Sprite(
          new THREE.SpriteMaterial({ map: makeDotTexture(m.color ?? "#fbbf24"), transparent: true, depthWrite: false })
        );
        s.position.copy(latLonToVec3(m.lat, m.lon, 1.012));
        s.scale.set(0.05, 0.05, 1);
        s.userData.latlon = { lat: m.lat, lon: m.lon };
        markerGroup.add(s);
      }
      if (sel) {
        const dot = new THREE.Sprite(
          new THREE.SpriteMaterial({ map: makeDotTexture("#159EEA"), transparent: true, depthWrite: false })
        );
        dot.position.copy(latLonToVec3(sel.lat, sel.lon, 1.016));
        dot.scale.set(0.075, 0.075, 1);
        const ring = new THREE.Sprite(
          new THREE.SpriteMaterial({ map: makeRingTexture("#58D9F2"), transparent: true, depthWrite: false })
        );
        ring.position.copy(latLonToVec3(sel.lat, sel.lon, 1.014));
        ring.scale.set(0.17, 0.17, 1);
        ring.userData.isPulseRing = true;
        markerGroup.add(dot, ring);
      }
    };
    syncMarkers();

    // --- interaction: drag rotate / wheel zoom / click pick ----------------
    const raycaster = new THREE.Raycaster();
    const ndc = new THREE.Vector2();
    let down = false;
    let moved = 0;
    let lastX = 0;
    let lastY = 0;
    let velX = 0;
    let velY = 0;
    let touchStartDist = 0;
    let initialCamDist = 0;
    let anim: {
      from: THREE.Quaternion;
      to: THREE.Quaternion;
      t: number;
      camFrom: number;
      camTo: number;
    } | null = null;

    const pick = (e: PointerEvent): { lat: number; lon: number } | null => {
      const rect = renderer.domElement.getBoundingClientRect();
      ndc.set(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );
      raycaster.setFromCamera(ndc, camera);
      group.updateMatrixWorld(true);

      // Check site markers first (if user clicked directly on a known site marker)
      const siteMarkers = markerGroup.children.filter((c) => Boolean(c.userData.latlon));
      if (siteMarkers.length) {
        const markerHits = raycaster.intersectObjects(siteMarkers, false);
        if (markerHits.length > 0) {
          const fromSprite = markerHits[0].object.userData.latlon as { lat: number; lon: number } | undefined;
          if (fromSprite) return fromSprite;
        }
      }

      // Intersect lunar sphere mesh directly (avoids sprite billboard offset distortion)
      const hits = raycaster.intersectObject(moon, false);
      if (!hits.length) return null;
      const p = group.worldToLocal(hits[0].point.clone());
      return vec3ToLatLon(p);
    };

    const onPointerDown = (e: PointerEvent) => {
      down = true;
      moved = 0;
      lastX = e.clientX;
      lastY = e.clientY;
      renderer.domElement.setPointerCapture(e.pointerId);
    };
    const onPointerMove = (e: PointerEvent) => {
      if (!down) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;
      moved += Math.abs(dx) + Math.abs(dy);
      if (propsRef.current.interactive !== false) {
        // Cancel any pending fly-to animation when user manually rotates
        if (anim && moved > 4) anim = null;
        velX = dx * 0.005;
        velY = dy * 0.005;
        const qy = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), velX);
        const qx = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), velY);
        group.quaternion.premultiply(qy).premultiply(qx);
      }
    };
    const onPointerUp = (e: PointerEvent) => {
      down = false;
      if (moved < 6 && propsRef.current.interactive !== false && propsRef.current.onSelect) {
        const ll = pick(e);
        if (ll) propsRef.current.onSelect(ll.lat, ll.lon);
      }
    };
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const d = camera.position.length();
      camera.position.setLength(THREE.MathUtils.clamp(d * (1 + e.deltaY * 0.0011), 1.25, 5));
    };

    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        touchStartDist = Math.hypot(dx, dy);
        initialCamDist = camera.position.length();
      }
    };
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2 && touchStartDist > 0) {
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        const dist = Math.hypot(dx, dy);
        const factor = touchStartDist / Math.max(dist, 1);
        camera.position.setLength(THREE.MathUtils.clamp(initialCamDist * factor, 1.25, 5));
      }
    };

    const el = renderer.domElement;
    el.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    el.addEventListener("wheel", onWheel, { passive: false });
    el.addEventListener("touchstart", onTouchStart, { passive: true });
    el.addEventListener("touchmove", onTouchMove, { passive: true });

    // --- South Pole focus ---------------------------------------------------
    const southPoleQuat = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(0, -1, 0),
      new THREE.Vector3(0, 0, 1)
    );
    const focusSouthPole = () => {
      anim = {
        from: group.quaternion.clone(),
        to: southPoleQuat.clone(),
        t: 0,
        camFrom: camera.position.length(),
        camTo: 2.05,
      };
    };
    const focusSite = (lat: number, lon: number) => {
      anim = {
        from: group.quaternion.clone(),
        to: quatForLatLon(lat, lon),
        t: 0,
        camFrom: camera.position.length(),
        camTo: 2.4,
      };
    };
    if (propsRef.current.initialSouthPole) {
      group.quaternion.copy(southPoleQuat);
      camera.position.setLength(2.05);
    }

    apiRef.current = { focusSouthPole, focusSite, syncMarkers };

    // --- resize -------------------------------------------------------------
    const ro = new ResizeObserver(() => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      if (!w || !h) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
    ro.observe(mount);

    // --- render loop ----------------------------------------------------------
    let raf = 0;
    let prev = performance.now();
    const loop = (now: number) => {
      const dt = Math.min((now - prev) / 1000, 0.05);
      prev = now;
      const t = now * 0.001;
      if (propsRef.current.autoRotate && !down) {
        const qAuto = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), dt * 0.06);
        group.quaternion.premultiply(qAuto);
      }

      // Update solar lighting azimuth for time-based diurnal cycle simulation
      if (typeof propsRef.current.sunAngle === "number") {
        const rad = propsRef.current.sunAngle * D2R;
        sun.position.set(4 * Math.cos(rad), 1.5, 4 * Math.sin(rad));
      }

      // Apply smooth damping when released
      if (!down && !anim && (Math.abs(velX) > 1e-5 || Math.abs(velY) > 1e-5)) {
        const qy = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), velX);
        const qx = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), velY);
        group.quaternion.premultiply(qy).premultiply(qx);
        velX *= 0.92;
        velY *= 0.92;
      }

      if (anim) {
        anim.t += dt / 1.4;
        const k = anim.t >= 1 ? 1 : 1 - Math.pow(1 - anim.t, 3);
        group.quaternion.slerpQuaternions(anim.from, anim.to, k);
        camera.position.setLength(THREE.MathUtils.lerp(anim.camFrom, anim.camTo, k));
        if (anim.t >= 1) anim = null;
      }
      // Pulse the selection ring
      markerGroup.children.forEach((child) => {
        if (child.userData.isPulseRing) {
          const pulse = 1 + 0.12 * Math.sin(t * 3.5);
          child.scale.setScalar(0.17 * pulse);
        }
      });
      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);

    // --- cleanup ---------------------------------------------------------------
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      el.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      el.removeEventListener("wheel", onWheel);
      el.removeEventListener("touchstart", onTouchStart);
      el.removeEventListener("touchmove", onTouchMove);
      scene.traverse((o) => {
        const obj = o as THREE.Mesh | THREE.Line | THREE.Sprite;
        if (obj.geometry) obj.geometry.dispose();
        const mat = (o as THREE.Mesh).material as THREE.Material | undefined;
        if (mat) {
          const spriteMat = mat as THREE.SpriteMaterial;
          if (spriteMat.map) spriteMat.map.dispose();
          mat.dispose();
        }
      });
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) mount.removeChild(renderer.domElement);
      apiRef.current = null;
    };
  }, []);

  return (
    <div
      ref={mountRef}
      className={props.className ?? "h-full w-full"}
      style={{ touchAction: "none" }}
      aria-label="Interactive 3D map of the Moon"
    />
  );
}
