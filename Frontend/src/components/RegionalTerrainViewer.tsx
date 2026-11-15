import { useEffect, useRef, useState, useMemo } from "react";
import * as THREE from "three";
import type { TerrainMeshResponse, DetectedLandingZone, HazardItem } from "@/types";
import { fmtCoord, fmtNum } from "@/utils/format";
import LoadingState from "./LoadingState";
import {
  AlertIcon,
  CrosshairIcon,
  MountainIcon,
  RefreshIcon,
} from "./icons";

interface RegionalTerrainViewerProps {
  className?: string;
  meshData: TerrainMeshResponse | null;
  loading: boolean;
  error: string | null;
  onRefresh?: () => void;
  selectedCoord: { lat: number; lon: number; radius_m: number };
  onSelectCoord?: (lat: number, lon: number) => void;
  detectedZones?: DetectedLandingZone[];
  hazards?: { craters?: HazardItem[] | null; rocks?: HazardItem[] | null } | null;
  sunAngle?: number;
}

export type TerrainLayerMode = "monochrome" | "elevation" | "slope" | "wireframe";

const D2R = Math.PI / 180;
const MOON_RADIUS_M = 1_737_400.0;

/** Convert Polar Stereographic meters (ESRI:104903) to Lat/Lon */
export function polarStereoToLatLon(x: number, y: number): { lat: number; lon: number } {
  const rho = Math.hypot(x, y);
  if (rho < 1e-6) {
    return { lat: -90.0, lon: 0.0 };
  }
  const colat_rad = 2.0 * Math.atan(rho / (2.0 * MOON_RADIUS_M));
  const lat = (colat_rad - Math.PI / 2.0) / D2R;
  let lon = Math.atan2(x, y) / D2R;
  lon = ((lon % 360) + 360) % 360;
  return { lat, lon };
}

/** Convert Lat/Lon to Polar Stereographic meters (ESRI:104903) */
export function latLonToPolarStereo(latDeg: number, lonDeg: number): { x: number; y: number } {
  const lat_rad = latDeg * D2R;
  const lon_rad = lonDeg * D2R;
  const colat_rad = (Math.PI / 2.0) + lat_rad;
  const r = 2.0 * MOON_RADIUS_M * Math.tan(colat_rad / 2.0);
  const x = r * Math.sin(lon_rad);
  const y = r * Math.cos(lon_rad);
  return { x, y };
}

export default function RegionalTerrainViewer({
  className = "",
  meshData,
  loading,
  error,
  onRefresh,
  selectedCoord,
  onSelectCoord,
  detectedZones = [],
  hazards = null,
  sunAngle = 35,
}: RegionalTerrainViewerProps) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [activeLayer, setActiveLayer] = useState<TerrainLayerMode>("monochrome");
  const [reliefExaggeration, setReliefExaggeration] = useState<number>(1.5);
  const [showProfile, setShowProfile] = useState<boolean>(false);
  const [webglError, setWebglError] = useState<string | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<{
    elev: number;
    slope: number;
    lat: number;
    lon: number;
    distM: number;
  } | null>(null);

  // Compute profile transect (center row slice)
  const profileData = useMemo(() => {
    if (!meshData || !meshData.elevation_grid || meshData.elevation_grid.length === 0) {
      return null;
    }
    const grid = meshData.elevation_grid;
    const midRow = Math.floor(grid.length / 2);
    const row = grid[midRow];
    const n = row.length;
    const stepM = (meshData.radius_m * 2.0) / Math.max(1, n - 1);
    return row.map((elev, idx) => ({
      distM: (idx - (n - 1) / 2) * stepM,
      elev,
    }));
  }, [meshData]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || !meshData || !meshData.elevation_grid || meshData.elevation_grid.length === 0) {
      return;
    }

    const grid = meshData.elevation_grid;
    const slopeGrid = meshData.slope_grid || [];
    const rows = grid.length;
    const cols = grid[0].length;
    const radiusM = meshData.radius_m;
    const minElev = meshData.min_elevation_m;
    const maxElev = meshData.max_elevation_m;
    const meanElev = meshData.mean_elevation_m;
    const relief = Math.max(1.0, maxElev - minElev);

    // Three.js Scene Setup with safe WebGL initialization
    const width = Math.max(mount.clientWidth, 100);
    const height = Math.max(mount.clientHeight, 100);
    const aspect = width / height;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    } catch (err) {
      setWebglError(err instanceof Error ? err.message : "WebGL context initialization failed.");
      return;
    }

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    mount.appendChild(renderer.domElement);

    const onContextLost = (e: Event) => {
      e.preventDefault();
      setWebglError("WebGL context was lost. Click retry to re-initialize 3D terrain.");
    };
    renderer.domElement.addEventListener("webglcontextlost", onContextLost);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x090909);

    const camera = new THREE.PerspectiveCamera(40, aspect, 0.1, 1000);
    // Position camera in local units: world size is normalized to 10.0 units
    const WORLD_SIZE = 10.0;
    camera.position.set(0, WORLD_SIZE * 0.9, WORLD_SIZE * 1.25);
    camera.lookAt(0, 0, 0);

    // Guaranteed Ambient Illumination so terrain geometry is never in pitch-black shadow
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.45);
    scene.add(ambientLight);

    // Dynamic Vacuum Sun Lighting
    const sunLight = new THREE.DirectionalLight(0xfff8f0, 2.5);
    const sunRad = sunAngle * D2R;
    sunLight.position.set(
      WORLD_SIZE * 2 * Math.cos(sunRad),
      WORLD_SIZE * 1.2,
      WORLD_SIZE * 2 * Math.sin(sunRad)
    );
    sunLight.target.position.set(0, 0, 0);
    scene.add(sunLight);
    scene.add(sunLight.target);

    // Earthshine ambient fill
    const earthshine = new THREE.HemisphereLight(0x4a4a50, 0x1a1a20, 0.4);
    scene.add(earthshine);

    const terrainGroup = new THREE.Group();
    scene.add(terrainGroup);

    // Construct 3D Plane Geometry for Real Elevation Relief
    const planeGeo = new THREE.PlaneGeometry(WORLD_SIZE, WORLD_SIZE, cols - 1, rows - 1);
    planeGeo.rotateX(-Math.PI / 2); // Orient horizontal (XZ plane, Y up)

    const posAttr = planeGeo.attributes.position;
    const colorAttr = new Float32Array(posAttr.count * 3);

    const elevScale = (WORLD_SIZE / (radiusM * 2.0)) * reliefExaggeration;

    for (let i = 0; i < posAttr.count; i++) {
      const r = Math.floor(i / cols);
      const c = i % cols;
      const elev = grid[r] && grid[r][c] !== undefined ? grid[r][c] : meanElev;
      const slope = slopeGrid[r] && slopeGrid[r][c] !== undefined ? slopeGrid[r][c] : 0.0;

      // Displace vertex height in meters centered around mean elevation
      const normY = (elev - meanElev) * elevScale;
      posAttr.setY(i, normY);

      // Vertex color depending on active layer
      let color = new THREE.Color(0x999999);
      if (activeLayer === "elevation") {
        // Continuous greyscale elevation ramp
        const t = THREE.MathUtils.clamp((elev - minElev) / relief, 0, 1);
        color.setHSL(0.65 - t * 0.65, 0.8, 0.5); // Rich scientific elevation gradient
      } else if (activeLayer === "slope") {
        // Horn slope color scale: Green (0-5°), Yellow (5-15°), Red (>15°)
        if (slope <= 5.0) {
          color.setHex(0x4ade80); // Favorable safe
        } else if (slope <= 15.0) {
          color.setHex(0xfbbf24); // Marginal
        } else {
          color.setHex(0xf87171); // Hazardous critical
        }
      } else {
        // Monochromatic documentary regolith shading
        const t = THREE.MathUtils.clamp((elev - minElev) / relief, 0, 1);
        const grey = 0.25 + t * 0.55;
        color.setRGB(grey, grey, grey);
      }

      colorAttr[i * 3] = color.r;
      colorAttr[i * 3 + 1] = color.g;
      colorAttr[i * 3 + 2] = color.b;
    }

    planeGeo.setAttribute("color", new THREE.BufferAttribute(colorAttr, 3));
    planeGeo.computeVertexNormals();

    const terrainMat = new THREE.MeshStandardMaterial({
      vertexColors: activeLayer !== "wireframe",
      wireframe: activeLayer === "wireframe",
      color: activeLayer === "wireframe" ? 0xcccccc : 0xffffff,
      roughness: 0.92,
      metalness: 0.05,
      flatShading: false,
    });

    const terrainMeshObj = new THREE.Mesh(planeGeo, terrainMat);
    terrainGroup.add(terrainMeshObj);

    // Analysis Footprint Disc Outline (Radius M)
    const ringRadius = WORLD_SIZE * 0.48;
    const ringPts: THREE.Vector3[] = [];
    for (let a = 0; a <= 360; a += 5) {
      const rad = a * D2R;
      ringPts.push(new THREE.Vector3(ringRadius * Math.cos(rad), 0.02, ringRadius * Math.sin(rad)));
    }
    const ringGeo = new THREE.BufferGeometry().setFromPoints(ringPts);
    const ringMat = new THREE.LineBasicMaterial({ color: 0xf1f1ef, transparent: true, opacity: 0.75 });
    const ringLine = new THREE.Line(ringGeo, ringMat);
    terrainGroup.add(ringLine);

    // Center Touchdown Target Beacon
    const beaconGeo = new THREE.CylinderGeometry(0.04, 0.04, WORLD_SIZE * 0.12, 16);
    beaconGeo.translate(0, WORLD_SIZE * 0.06, 0);
    const beaconMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const beaconMesh = new THREE.Mesh(beaconGeo, beaconMat);
    terrainGroup.add(beaconMesh);

    // Candidate Safe Zones (Vector Overlays)
    if (detectedZones && detectedZones.length > 0) {
      detectedZones.slice(0, 5).forEach((z, idx) => {
        const zoneLat = typeof z.centroid_lat === "number" ? z.centroid_lat : (z.latitude as number | undefined);
        const zoneLon = typeof z.centroid_lon === "number" ? z.centroid_lon : (z.longitude as number | undefined);
        if (typeof zoneLat !== "number" || typeof zoneLon !== "number") return;
        const dLat = zoneLat - selectedCoord.lat;
        const dLon = zoneLon - selectedCoord.lon;
        // Project offset onto local grid
        const ox = (dLon * D2R * MOON_RADIUS_M * Math.cos(selectedCoord.lat * D2R) / (radiusM * 2)) * WORLD_SIZE;
        const oz = -(dLat * D2R * MOON_RADIUS_M / (radiusM * 2)) * WORLD_SIZE;

        if (Math.hypot(ox, oz) < WORLD_SIZE * 0.5) {
          const zoneDiscGeo = new THREE.RingGeometry(0.15, 0.22, 24);
          zoneDiscGeo.rotateX(-Math.PI / 2);
          const zoneDiscMat = new THREE.MeshBasicMaterial({
            color: idx === 0 ? 0x4ade80 : 0xd4d4d0,
            side: THREE.DoubleSide,
          });
          const zoneMesh = new THREE.Mesh(zoneDiscGeo, zoneDiscMat);
          zoneMesh.position.set(ox, 0.04, oz);
          terrainGroup.add(zoneMesh);
        }
      });
    }

    // Crater and Boulder Hazard Footprints
    if (hazards && hazards.craters && hazards.craters.length > 0) {
      hazards.craters.slice(0, 15).forEach((c) => {
        if (typeof c.latitude === "number" && typeof c.longitude === "number") {
          const dLat = c.latitude - selectedCoord.lat;
          const dLon = c.longitude - selectedCoord.lon;
          const ox = (dLon * D2R * MOON_RADIUS_M * Math.cos(selectedCoord.lat * D2R) / (radiusM * 2)) * WORLD_SIZE;
          const oz = -(dLat * D2R * MOON_RADIUS_M / (radiusM * 2)) * WORLD_SIZE;
          const diamM = (c.diameter_m || (c.radius_m ? c.radius_m * 2 : 20.0));
          const visualR = Math.max(0.08, (diamM / (radiusM * 2)) * WORLD_SIZE * 0.5);

          if (Math.hypot(ox, oz) < WORLD_SIZE * 0.55) {
            const crGeo = new THREE.RingGeometry(visualR * 0.85, visualR, 20);
            crGeo.rotateX(-Math.PI / 2);
            const crMat = new THREE.MeshBasicMaterial({ color: 0xf87171, side: THREE.DoubleSide });
            const crMesh = new THREE.Mesh(crGeo, crMat);
            crMesh.position.set(ox, 0.03, oz);
            terrainGroup.add(crMesh);
          }
        }
      });
    }

    // Camera and Interactive Raycasting
    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;
    let yaw = 0;
    let pitch = 0.55;
    let camDistance = WORLD_SIZE * 1.5;
    const raycaster = new THREE.Raycaster();
    const mouseNdc = new THREE.Vector2();

    const updateCamera = () => {
      pitch = THREE.MathUtils.clamp(pitch, 0.08, 1.45);
      camDistance = THREE.MathUtils.clamp(camDistance, WORLD_SIZE * 0.6, WORLD_SIZE * 3.5);
      camera.position.x = camDistance * Math.sin(yaw) * Math.cos(pitch);
      camera.position.y = camDistance * Math.sin(pitch);
      camera.position.z = camDistance * Math.cos(yaw) * Math.cos(pitch);
      camera.lookAt(0, 0, 0);
    };
    updateCamera();

    const onPointerDown = (e: PointerEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
      renderer.domElement.setPointerCapture(e.pointerId);
    };

    const onPointerMove = (e: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouseNdc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouseNdc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      if (isDragging) {
        const dx = e.clientX - prevMouseX;
        const dy = e.clientY - prevMouseY;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;
        yaw -= dx * 0.006;
        pitch += dy * 0.006;
        updateCamera();
      } else {
        // Inspect hovered elevation & coordinates
        raycaster.setFromCamera(mouseNdc, camera);
        const hits = raycaster.intersectObject(terrainMeshObj, false);
        if (hits.length > 0) {
          const pt = hits[0].point;
          // Invert local coords to polar stereographic
          const normX = pt.x / WORLD_SIZE;
          const normZ = -pt.z / WORLD_SIZE;
          const polarX = meshData.center_x_polar_m + normX * (radiusM * 2.0);
          const polarY = meshData.center_y_polar_m + normZ * (radiusM * 2.0);
          const ll = polarStereoToLatLon(polarX, polarY);

          // Bilinear interpolate elevation from grid
          const rFloat = THREE.MathUtils.clamp((0.5 - normZ) * rows, 0, rows - 1);
          const cFloat = THREE.MathUtils.clamp((normX + 0.5) * cols, 0, cols - 1);
          const r0 = Math.floor(rFloat);
          const c0 = Math.floor(cFloat);
          const curElev = grid[r0] ? grid[r0][c0] : meanElev;
          const curSlope = slopeGrid[r0] ? slopeGrid[r0][c0] : 0.0;
          const distM = Math.hypot(normX * radiusM * 2.0, normZ * radiusM * 2.0);

          setHoveredPoint({
            elev: curElev,
            slope: curSlope,
            lat: ll.lat,
            lon: ll.lon,
            distM,
          });
        } else {
          setHoveredPoint(null);
        }
      }
    };

    const onPointerUp = (e: PointerEvent) => {
      isDragging = false;
      const dx = Math.abs(e.clientX - prevMouseX);
      const dy = Math.abs(e.clientY - prevMouseY);
      if (dx < 5 && dy < 5 && onSelectCoord) {
        raycaster.setFromCamera(mouseNdc, camera);
        const hits = raycaster.intersectObject(terrainMeshObj, false);
        if (hits.length > 0) {
          const pt = hits[0].point;
          const normX = pt.x / WORLD_SIZE;
          const normZ = -pt.z / WORLD_SIZE;
          const polarX = meshData.center_x_polar_m + normX * (radiusM * 2.0);
          const polarY = meshData.center_y_polar_m + normZ * (radiusM * 2.0);
          const ll = polarStereoToLatLon(polarX, polarY);
          if (ll.lat <= -70.0 && ll.lat >= -90.0) {
            onSelectCoord(ll.lat, ll.lon);
          }
        }
      }
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();
      camDistance *= 1 + e.deltaY * 0.001;
      updateCamera();
    };

    const el = renderer.domElement;
    el.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    el.addEventListener("wheel", onWheel, { passive: false });

    // Render loop
    let raf = 0;
    const render = () => {
      renderer.render(scene, camera);
      raf = requestAnimationFrame(render);
    };
    render();

    // Resize observer
    const ro = new ResizeObserver(() => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      if (!w || !h || w <= 0 || h <= 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
    ro.observe(mount);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      renderer.domElement.removeEventListener("webglcontextlost", onContextLost);
      el.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      el.removeEventListener("wheel", onWheel);
      scene.traverse((o) => {
        const obj = o as THREE.Mesh;
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
          if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose());
          else obj.material.dispose();
        }
      });
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, [meshData, activeLayer, reliefExaggeration, sunAngle, selectedCoord, onSelectCoord, detectedZones, hazards]);

  return (
    <div className={`relative flex flex-col overflow-hidden bg-space ${className}`}>
      {/* 3D Canvas Mount */}
      <div ref={mountRef} className="relative flex-1 w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-space/85 backdrop-blur-sm z-30">
          <LoadingState label="Extracting LOLA/PGDA DEM Elevation & Slope Grid (POST /api/terrain/mesh)…" />
        </div>
      )}

      {/* WebGL Context / Renderer Failure */}
      {webglError && (
        <div className="absolute inset-0 flex items-center justify-center bg-space/90 p-6 z-30">
          <div className="panel max-w-md p-6 text-center border-bad/40">
            <AlertIcon className="h-8 w-8 text-bad mx-auto mb-3" />
            <h4 className="font-display text-sm font-semibold text-bad">
              WebGL Renderer Unavailable
            </h4>
            <p className="mt-2 text-xs text-muted leading-relaxed">
              {webglError}
            </p>
            {onRefresh && (
              <button
                className="btn-primary mt-4 !px-4 !py-2 !text-xs cursor-pointer"
                onClick={() => {
                  setWebglError(null);
                  onRefresh();
                }}
              >
                <RefreshIcon className="h-4 w-4" /> Re-initialize WebGL
              </button>
            )}
          </div>
        </div>
      )}

      {/* Error / No Data Banner */}
      {error && !webglError && (
        <div className="absolute inset-0 flex items-center justify-center bg-space/90 p-6 z-30">
          <div className="panel max-w-md p-6 text-center border-warn/40">
            <AlertIcon className="h-8 w-8 text-warn mx-auto mb-3" />
            <h4 className="font-display text-sm font-semibold text-warn">
              Terrain Relief Grid Offline
            </h4>
            <p className="mt-2 text-xs text-muted leading-relaxed">
              {error}
            </p>
            {onRefresh && (
              <button className="btn-primary mt-4 !px-4 !py-2 !text-xs cursor-pointer" onClick={onRefresh}>
                <RefreshIcon className="h-4 w-4" /> Retry Query
              </button>
            )}
          </div>
        </div>
      )}

      {/* Target Outside Polar Zone */}
      {meshData && meshData.status === "outside_polar_zone" && !loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-space/90 p-6 z-30">
          <div className="panel max-w-md p-6 text-center border-warn/40">
            <AlertIcon className="h-8 w-8 text-warn mx-auto mb-3" />
            <h4 className="font-display text-sm font-semibold text-warn">
              Target Outside Polar Zone
            </h4>
            <p className="mt-2 text-xs text-muted leading-relaxed">
              Coordinates {fmtCoord(meshData.latitude, meshData.longitude)} fall outside the supported lunar South Pole exploration boundary (-90° to -70°). 3D polar stereographic relief meshes are restricted to polar latitudes.
            </p>
          </div>
        </div>
      )}

      {/* Standby State: Ready to load DEM */}
      {!meshData && !loading && !error && !webglError && (
        <div className="absolute inset-0 flex items-center justify-center bg-space/90 p-6 z-30">
          <div className="panel max-w-md p-6 text-center border-divider">
            <MountainIcon className="h-8 w-8 text-muted mx-auto mb-3" />
            <h4 className="font-display text-sm font-semibold text-ink">
              3D Lunar Relief Mesh Ready
            </h4>
            <p className="mt-2 text-xs text-muted leading-relaxed">
              Select any candidate preset or click below to extract the 3D DEM elevation matrix for {fmtCoord(selectedCoord.lat, selectedCoord.lon)} (R = {selectedCoord.radius_m}m).
            </p>
            {onRefresh && (
              <button className="btn-primary mt-4 !px-4 !py-2 !text-xs cursor-pointer" onClick={onRefresh}>
                <RefreshIcon className="h-4 w-4" /> Load 3D Terrain Relief
              </button>
            )}
          </div>
        </div>
      )}

      {/* Top HUD Toolbar: Layer Modes & Relief Exaggeration */}
      <div className="absolute top-4 left-4 right-4 flex flex-wrap items-center justify-between gap-3 pointer-events-none z-20">
        <div className="flex flex-wrap items-center gap-2 pointer-events-auto">
          <div className="glass-soft rounded px-2.5 py-1 text-[11px] font-mono text-ink">
            3D TERRAIN RELIEF · R = {selectedCoord.radius_m}m
          </div>
          {(["monochrome", "elevation", "slope", "wireframe"] as TerrainLayerMode[]).map((mode) => (
            <button
              key={mode}
              className={`glass-soft rounded px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider transition-colors ${activeLayer === mode ? "text-ink border-white/40 bg-white/10" : "text-muted hover:text-ink"
                }`}
              onClick={() => setActiveLayer(mode)}
            >
              {mode}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 pointer-events-auto">
          <button
            className={`glass-soft rounded px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider transition-colors ${showProfile ? "text-ink border-white/40 bg-white/10" : "text-muted hover:text-ink"
              }`}
            onClick={() => setShowProfile((v) => !v)}
          >
            TRANSECT PROFILE
          </button>
          <div className="glass-soft rounded px-2.5 py-1 flex items-center gap-2 text-[11px] font-mono text-muted">
            <span>RELIEF:</span>
            {[1.0, 1.5, 2.5].map((scale) => (
              <button
                key={scale}
                className={`cursor-pointer transition-colors ${reliefExaggeration === scale ? "text-ink font-bold underline" : "hover:text-ink"
                  }`}
                onClick={() => setReliefExaggeration(scale)}
              >
                {scale}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom HUD: Live Hover / Surface Measurement Telemetry */}
      {hoveredPoint && (
        <div className="absolute bottom-5 left-5 pointer-events-none z-20">
          <div className="glass-soft rounded p-3 text-xs space-y-1">
            <div className="flex items-center gap-2 font-mono text-ink font-semibold">
              <CrosshairIcon className="h-3.5 w-3.5" />
              <span>{fmtCoord(hoveredPoint.lat, hoveredPoint.lon)}</span>
            </div>
            <div className="flex items-center gap-4 text-[11px] font-mono text-muted">
              <span>Elev: <strong className="text-ink">{fmtNum(hoveredPoint.elev, 1)} m</strong></span>
              <span>Slope: <strong className={hoveredPoint.slope > 15 ? "text-bad" : "text-ink"}>{fmtNum(hoveredPoint.slope, 1)}°</strong></span>
              <span>Offset: <strong className="text-ink">{fmtNum(hoveredPoint.distM, 0)} m</strong></span>
            </div>
          </div>
        </div>
      )}

      {/* Bottom Right: Dataset Provenance & Legend */}
      {meshData && (
        <div className="absolute bottom-5 right-5 pointer-events-none z-20 flex flex-col items-end gap-2">
          {activeLayer === "slope" && (
            <div className="glass-soft rounded p-2 text-[10px] font-mono space-y-1 pointer-events-auto">
              <div className="flex items-center gap-2">
                <span className="h-2 w-3 rounded-xs bg-[#4ade80]" />
                <span className="text-ink">0°–5° (Nominal Touchdown)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-2 w-3 rounded-xs bg-[#fbbf24]" />
                <span className="text-ink">5°–15° (Marginal Gradient)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-2 w-3 rounded-xs bg-[#f87171]" />
                <span className="text-ink">&gt;15° (Critical Hazard)</span>
              </div>
            </div>
          )}

          {activeLayer === "elevation" && (
            <div className="glass-soft rounded p-2 text-[10px] font-mono space-y-1 pointer-events-auto">
              <div className="text-muted">Elevation Relief: {fmtNum(meshData.relief_m, 1)}m</div>
              <div className="flex items-center gap-2">
                <span className="text-muted">{fmtNum(meshData.min_elevation_m, 0)}m</span>
                <span className="h-2 w-20 rounded-xs bg-gradient-to-r from-blue-500 via-yellow-400 to-red-500" />
                <span className="text-ink font-semibold">{fmtNum(meshData.max_elevation_m, 0)}m</span>
              </div>
            </div>
          )}

          <div className="glass-soft rounded px-3 py-1.5 text-right space-y-0.5">
            <div className="flex items-center justify-end gap-1.5">
              {meshData.has_high_res ? (
                <span className="inline-block px-1.5 py-0.5 text-[9px] font-mono text-good border border-good/40 rounded">
                  5m HIGH-RES DEM
                </span>
              ) : (
                <span className="inline-block px-1.5 py-0.5 text-[9px] font-mono text-muted border border-divider/40 rounded">
                  BROAD-AREA DEM
                </span>
              )}
            </div>
            <p className="font-mono text-[10px] text-ink font-semibold">{meshData.dataset_name}</p>
            <p className="font-mono text-[9px] text-muted">
              {meshData.source_tier ? `${meshData.source_tier} · ` : ""}Res: {meshData.resolution_m}m · CRS: {meshData.crs}
            </p>
          </div>
        </div>
      )}

      {/* Transect Profile Drawer */}
      {showProfile && profileData && (
        <div className="absolute bottom-18 left-5 right-5 glass-soft rounded-lg p-4 z-20 shadow-2xl">
          <div className="flex items-center justify-between text-xs mb-2">
            <span className="font-mono text-ink font-semibold uppercase">
              East-West Cross-Sectional Elevation Transect (LOLA DEM)
            </span>
            <button className="text-muted hover:text-ink text-xs font-mono" onClick={() => setShowProfile(false)}>
              [CLOSE]
            </button>
          </div>
          <div className="h-20 w-full overflow-hidden">
            <svg viewBox="0 0 800 80" preserveAspectRatio="none" className="w-full h-full">
              {(() => {
                const minE = meshData?.min_elevation_m ?? 0;
                const maxE = meshData?.max_elevation_m ?? 100;
                const range = Math.max(1, maxE - minE);
                const pts = profileData
                  .map((p, idx) => {
                    const x = (idx / (profileData.length - 1)) * 800;
                    const y = 70 - ((p.elev - minE) / range) * 60;
                    return `${x},${y}`;
                  })
                  .join(" ");
                return (
                  <>
                    <polyline fill="none" stroke="#F1F1EF" strokeWidth="2" points={pts} />
                    <line x1="0" y1="70" x2="800" y2="70" stroke="rgba(255,255,255,0.15)" strokeDasharray="3 3" />
                  </>
                );
              })()}
            </svg>
          </div>
          <div className="flex justify-between text-[10px] font-mono text-muted mt-1">
            <span>-{selectedCoord.radius_m}m (West)</span>
            <span>Center (0m): {fmtNum(meshData?.mean_elevation_m ?? 0, 1)}m</span>
            <span>+{selectedCoord.radius_m}m (East)</span>
          </div>
        </div>
      )}
    </div>
  );
}
