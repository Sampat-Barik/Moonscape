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
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { TargetIcon } from "./icons";

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
  /** Active basemap layer: 'default' | 'trek_wac' */
  activeLayer?: string;
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

function makeLabelTexture(text: string, color = "#F1F1EF"): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 96;
  const ctx = c.getContext("2d")!;
  ctx.font = "600 44px 'Space Grotesk', sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.shadowColor = "rgba(0,0,0,0.9)";
  ctx.shadowBlur = 12;
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
  const apiRef = useRef<{
    focusSouthPole: () => void;
    focusSite: (lat: number, lon: number) => void;
    syncMarkers: () => void;
    switchLayer?: (layer: string) => void;
    zoomIn: () => void;
    zoomOut: () => void;
  } | null>(null);

  const handleZoomIn = () => apiRef.current?.zoomIn();
  const handleZoomOut = () => apiRef.current?.zoomOut();
  const handleResetView = () => apiRef.current?.focusSouthPole();

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

  // Switch basemap layer dynamically
  useEffect(() => {
    if (props.activeLayer && apiRef.current?.switchLayer) {
      apiRef.current.switchLayer(props.activeLayer);
    }
  }, [props.activeLayer]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight, false);
    renderer.setClearColor(0x000000, 0);
    renderer.domElement.style.display = "block";
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.outline = "none";
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      42,
      mount.clientWidth / Math.max(mount.clientHeight, 1),
      0.1,
      100
    );

    // Calculate dynamic Fit Globe distance ensuring the Moon occupies ~74% of the limiting viewport dimension
    const calculateFitDistance = (w: number, h: number, radius = 1.0) => {
      const aspect = w / Math.max(h, 1);
      const tanHalfFov = Math.tan((42 / 2) * (Math.PI / 180));
      const fillRatio = 0.74;
      const hDist = radius / (fillRatio * tanHalfFov);
      const wDist = radius / (fillRatio * tanHalfFov * aspect);
      return Math.max(hDist, wDist);
    };

    const initialFitDist = calculateFitDistance(
      mount.clientWidth || window.innerWidth,
      mount.clientHeight || window.innerHeight,
      1.0
    );

    // Position camera along +Z axis directly facing origin (0, 0, 0)
    camera.position.set(0, 0, initialFitDist);
    camera.lookAt(0, 0, 0);

    // Three.js OrbitControls: industry-standard orbiting anchored to globe origin (0, 0, 0)
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enablePan = false; // Strictly lock pan so target never drifts from (0, 0, 0)
    controls.minDistance = 1.35; // Surface clearance margin at R = 1.0
    controls.maxDistance = 6.0;
    controls.zoomToCursor = false; // Zoom strictly scales toward origin (0, 0, 0)
    controls.rotateSpeed = 0.65;
    controls.zoomSpeed = 0.85;

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
        new THREE.LineBasicMaterial({ color: 0x888888, transparent: true, opacity: 0.12 })
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
        new THREE.LineBasicMaterial({ color: 0xD4D4D0, transparent: true, opacity: 0.65 })
      )
    );
    const spLabel = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: makeLabelTexture("SOUTH POLE", "#F1F1EF"), transparent: true, depthWrite: false })
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
          new THREE.SpriteMaterial({ map: makeDotTexture(m.color ?? "#E5E5E2"), transparent: true, depthWrite: false })
        );
        s.position.copy(latLonToVec3(m.lat, m.lon, 1.012));
        s.scale.set(0.05, 0.05, 1);
        s.userData.latlon = { lat: m.lat, lon: m.lon };
        markerGroup.add(s);
      }
      if (sel) {
        const dot = new THREE.Sprite(
          new THREE.SpriteMaterial({ map: makeDotTexture("#FFFFFF"), transparent: true, depthWrite: false })
        );
        dot.position.copy(latLonToVec3(sel.lat, sel.lon, 1.016));
        dot.scale.set(0.075, 0.075, 1);
        const ring = new THREE.Sprite(
          new THREE.SpriteMaterial({ map: makeRingTexture("#FFFFFF"), transparent: true, depthWrite: false })
        );
        ring.position.copy(latLonToVec3(sel.lat, sel.lon, 1.014));
        ring.scale.set(0.17, 0.17, 1);
        ring.userData.isPulseRing = true;
        markerGroup.add(dot, ring);
      }
    };
    syncMarkers();

    // --- interaction: raycasting & OrbitControls ---------------------------
    const raycaster = new THREE.Raycaster();
    const ndc = new THREE.Vector2();
    let downPos = { x: 0, y: 0 };
    let downTime = 0;
    let anim: {
      fromQuat: THREE.Quaternion;
      toQuat: THREE.Quaternion;
      fromDist: number;
      toDist: number;
      t: number;
      duration: number;
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
      downTime = performance.now();
      downPos = { x: e.clientX, y: e.clientY };
      // Cancel ongoing fly-to animation when user interacts directly
      if (anim) anim = null;
    };

    const onPointerUp = (e: PointerEvent) => {
      const elapsed = performance.now() - downTime;
      const dist = Math.hypot(e.clientX - downPos.x, e.clientY - downPos.y);
      // Treat as selection click only if pointer did not drag (< 5px)
      if (dist < 5 && elapsed < 450 && propsRef.current.interactive !== false && propsRef.current.onSelect) {
        const ll = pick(e);
        if (ll) propsRef.current.onSelect(ll.lat, ll.lon);
      }
    };

    // Isolate wheel zoom from outer page / sidebar scrolling
    const el = renderer.domElement;
    const onCanvasWheel = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();
    };

    el.addEventListener("pointerdown", onPointerDown);
    el.addEventListener("pointerup", onPointerUp);
    el.addEventListener("wheel", onCanvasWheel, { passive: false });

    // --- South Pole & Site Focus System ------------------------------------
    const southPoleQuat = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(0, -1, 0),
      new THREE.Vector3(0, 0, 1)
    );

    const focusSouthPole = () => {
      const w = mount.clientWidth || window.innerWidth;
      const h = mount.clientHeight || window.innerHeight;
      const fitDist = calculateFitDistance(w, h, 1.0);
      anim = {
        fromQuat: group.quaternion.clone(),
        toQuat: southPoleQuat.clone(),
        fromDist: camera.position.length(),
        toDist: fitDist,
        t: 0,
        duration: 1.0,
      };
    };

    const focusSite = (lat: number, lon: number) => {
      const w = mount.clientWidth || window.innerWidth;
      const h = mount.clientHeight || window.innerHeight;
      const fitDist = calculateFitDistance(w, h, 1.0);
      const siteDist = Math.min(2.40, fitDist * 0.72);
      anim = {
        fromQuat: group.quaternion.clone(),
        toQuat: quatForLatLon(lat, lon),
        fromDist: camera.position.length(),
        toDist: siteDist,
        t: 0,
        duration: 1.0,
      };
    };

    if (propsRef.current.initialSouthPole) {
      group.quaternion.copy(southPoleQuat);
    }

    const switchLayer = (layerId: string) => {
      if (layerId === "trek_wac") {
        loader.load(
          "/api/external/moon-trek/tile/trek_wac_global_mosaic/0/0/0",
          applyTexture,
          undefined,
          () => {
            urlIndex = 0;
            tryNextTexture();
          }
        );
      } else {
        urlIndex = 0;
        tryNextTexture();
      }
    };

    const zoomIn = () => {
      anim = null;
      const currentDist = camera.position.length();
      const newDist = THREE.MathUtils.clamp(currentDist * 0.82, controls.minDistance, controls.maxDistance);
      camera.position.setLength(newDist);
      camera.lookAt(0, 0, 0);
      controls.target.set(0, 0, 0);
      controls.update();
    };

    const zoomOut = () => {
      anim = null;
      const currentDist = camera.position.length();
      const newDist = THREE.MathUtils.clamp(currentDist * 1.20, controls.minDistance, controls.maxDistance);
      camera.position.setLength(newDist);
      camera.lookAt(0, 0, 0);
      controls.target.set(0, 0, 0);
      controls.update();
    };

    apiRef.current = { focusSouthPole, focusSite, syncMarkers, switchLayer, zoomIn, zoomOut };

    // --- resize observer with layout isolation ------------------------------
    const ro = new ResizeObserver(() => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      if (!w || !h) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
      controls.update();
    });
    ro.observe(mount);

    // --- render loop with damping & target locking ---------------------------
    let raf = 0;
    let prev = performance.now();
    const loop = (now: number) => {
      const dt = Math.min((now - prev) / 1000, 0.05);
      prev = now;
      const t = now * 0.001;

      if (propsRef.current.autoRotate && !anim) {
        const qAuto = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), dt * 0.06);
        group.quaternion.premultiply(qAuto);
      }

      // Update solar lighting azimuth for diurnal simulation
      if (typeof propsRef.current.sunAngle === "number") {
        const rad = propsRef.current.sunAngle * D2R;
        sun.position.set(4 * Math.cos(rad), 1.5, 4 * Math.sin(rad));
      }

      if (anim) {
        anim.t += dt / anim.duration;
        const k = anim.t >= 1 ? 1 : 1 - Math.pow(1 - anim.t, 3);
        group.quaternion.slerpQuaternions(anim.fromQuat, anim.toQuat, k);
        const d = THREE.MathUtils.lerp(anim.fromDist, anim.toDist, k);
        camera.position.set(0, 0, d);
        camera.lookAt(0, 0, 0);
        controls.target.set(0, 0, 0);
        controls.update();
        if (anim.t >= 1) anim = null;
      } else {
        // Enforce lock to origin: camera target strictly anchored to Moon's world center
        if (controls.target.lengthSq() > 1e-6) controls.target.set(0, 0, 0);
        controls.update();
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
      el.removeEventListener("pointerup", onPointerUp);
      el.removeEventListener("wheel", onCanvasWheel);
      controls.dispose();
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
      className={`relative ${props.className ?? "h-full w-full"}`}
      style={{ touchAction: "none" }}
      aria-label="Interactive 3D map of the Moon"
    >
      {/* Viewport Zoom & Framing HUD Controls */}
      {props.interactive !== false && (
        <div className="absolute top-4 left-4 z-20 flex flex-col items-center gap-1 pointer-events-auto">
          <div className="flex flex-col rounded-sm border border-divider/70 bg-[#161616]/90 backdrop-blur-md shadow-md overflow-hidden">
            <button
              type="button"
              onClick={handleZoomIn}
              className="flex h-7 w-7 items-center justify-center font-mono text-sm font-semibold text-ink/80 hover:text-ink hover:bg-white/10 transition-colors cursor-pointer"
              title="Zoom in closer to lunar surface"
              aria-label="Zoom in"
            >
              +
            </button>
            <div className="h-px w-full bg-divider/40" />
            <button
              type="button"
              onClick={handleZoomOut}
              className="flex h-7 w-7 items-center justify-center font-mono text-sm font-semibold text-ink/80 hover:text-ink hover:bg-white/10 transition-colors cursor-pointer"
              title="Zoom out for macroscopic lunar disk"
              aria-label="Zoom out"
            >
              −
            </button>
            <div className="h-px w-full bg-divider/40" />
            <button
              type="button"
              onClick={handleResetView}
              className="flex h-7 w-7 items-center justify-center text-ink/80 hover:text-ink hover:bg-white/10 transition-colors cursor-pointer p-1.5"
              title="Reset orientation and center South Pole (89.44°S)"
              aria-label="Reset view to South Pole"
            >
              <TargetIcon className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
