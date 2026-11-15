/**
 * CinematicMoon — Photorealistic, physically plausible interactive 3D Moon
 * powered by Three.js for the Moonscape homepage.
 *
 * Features:
 * - Authentic NASA LROC grayscale albedo texture with LOLA elevation bump relief.
 * - Physically plausible vacuum lighting: single stark directional Sun with subtle earthshine fill.
 * - Smooth camera entry glide on mount.
 * - Gentle inertia-based mouse parallax and drag-to-rotate interaction.
 * - Progressive texture loading with instant fallback.
 * - Full WebGL resource disposal on unmount to prevent GPU leaks.
 */

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

interface CinematicMoonProps {
  className?: string;
  onExplore?: () => void;
}

export default function CinematicMoon({ className = "" }: CinematicMoonProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [webGLSupported, setWebGLSupported] = useState(true);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Detect WebGL support
    try {
      const testCanvas = document.createElement("canvas");
      const gl = testCanvas.getContext("webgl") || testCanvas.getContext("experimental-webgl");
      if (!gl) {
        setWebGLSupported(false);
        return;
      }
    } catch {
      setWebGLSupported(false);
      return;
    }

    // 2. Scene setup
    const scene = new THREE.Scene();

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    const MOON_RADIUS = 1.0;
    const FOV = 40;
    const TAN_HALF_FOV = Math.tan((FOV / 2) * (Math.PI / 180));
    // Moon occupies ~72% of the limiting viewport dimension, leaving comfortable margin
    const calculateTargetZ = (w: number, h: number) => {
      const aspect = w / Math.max(h, 1);
      const baseZ = MOON_RADIUS / (0.72 * TAN_HALF_FOV);
      return baseZ / Math.min(aspect, 1.0);
    };

    let targetCameraZ = calculateTargetZ(width, height);

    const camera = new THREE.PerspectiveCamera(FOV, width / Math.max(height, 1), 0.1, 100);
    // Camera starts slightly pulled back for smooth cinematic entry glide
    camera.position.set(0, 0, targetCameraZ * 1.25);

    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      });
      renderer.setClearColor(0x000000, 0); // Strict zero-alpha clear color to blend into deep space
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
    } catch (e) {
      console.warn("Failed to create WebGLRenderer:", e);
      setWebGLSupported(false);
      return;
    }

    // 3. Moon Sphere Geometry & Material
    // Segment density 96x96 delivers a pristine, perfectly smooth circular silhouette
    const geometry = new THREE.SphereGeometry(MOON_RADIUS, 96, 96);

    // Initial placeholder grayscale canvas texture for progressive loading
    const placeholderCanvas = document.createElement("canvas");
    placeholderCanvas.width = placeholderCanvas.height = 128;
    const pCtx = placeholderCanvas.getContext("2d")!;
    pCtx.fillStyle = "#1e1e1e";
    pCtx.fillRect(0, 0, 128, 128);
    const placeholderTexture = new THREE.CanvasTexture(placeholderCanvas);

    const material = new THREE.MeshStandardMaterial({
      map: placeholderTexture,
      roughness: 0.90,
      metalness: 0.04,
      bumpScale: 0.035,
    });

    const moonMesh = new THREE.Mesh(geometry, material);
    // Initial slight polar tilt matching Moon's 1.54 deg obliquity to ecliptic
    moonMesh.rotation.x = 0.08;
    moonMesh.rotation.y = -0.45;
    scene.add(moonMesh);

    // 4. Photorealistic Vacuum Lighting
    // The distant Sun: stark directional light with zero atmospheric scattering
    const sunLight = new THREE.DirectionalLight(0xffffff, 2.6);
    sunLight.position.set(5.0, 1.8, 3.8);
    scene.add(sunLight);

    // Subtle Earthshine fill light (very faint cool bounce off Earth onto lunar dark side)
    const earthshineLight = new THREE.DirectionalLight(0x3a4048, 0.14);
    earthshineLight.position.set(-4.0, -1.0, -2.0);
    scene.add(earthshineLight);

    // Faint ambient rim light to define lunar horizon silhouette against deep void
    const rimLight = new THREE.DirectionalLight(0x88929e, 0.12);
    rimLight.position.set(-2.0, 3.0, -4.0);
    scene.add(rimLight);

    // 5. Progressive Texture Loading
    const textureLoader = new THREE.TextureLoader();
    const primaryAlbedoUrl = "/assets/textures/lroc_color_2k.jpg";
    const bumpMapUrl = "/assets/textures/ldem_3_8bit.jpg";

    textureLoader.load(
      primaryAlbedoUrl,
      (albedoTex) => {
        albedoTex.colorSpace = THREE.SRGBColorSpace;
        albedoTex.generateMipmaps = true;
        albedoTex.minFilter = THREE.LinearMipmapLinearFilter;
        material.map = albedoTex;
        material.needsUpdate = true;
        setIsLoaded(true);

        // Load LOLA bump map for topographical depth
        textureLoader.load(
          bumpMapUrl,
          (bumpTex) => {
            bumpTex.generateMipmaps = true;
            bumpTex.minFilter = THREE.LinearMipmapLinearFilter;
            material.bumpMap = bumpTex;
            material.needsUpdate = true;
          },
          undefined,
          () => {
            /* bump map optional */
          }
        );
      },
      undefined,
      () => {
        // Fallback to secondary texture
        textureLoader.load("/assets/textures/moon-2k.jpg", (altTex) => {
          altTex.colorSpace = THREE.SRGBColorSpace;
          material.map = altTex;
          material.needsUpdate = true;
          setIsLoaded(true);
        });
      }
    );

    // 6. Interaction & Parallax State
    let targetRotX = 0.08;
    let targetRotY = -0.45;
    let isDragging = false;
    let previousPointerPosition = { x: 0, y: 0 };
    let dragVelocity = { x: 0, y: 0 };

    const handlePointerDown = (e: PointerEvent) => {
      isDragging = true;
      previousPointerPosition = { x: e.clientX, y: e.clientY };
      dragVelocity = { x: 0, y: 0 };
    };

    const handlePointerMove = (e: PointerEvent) => {
      if (isDragging) {
        const deltaX = e.clientX - previousPointerPosition.x;
        const deltaY = e.clientY - previousPointerPosition.y;
        dragVelocity = { x: deltaX * 0.005, y: deltaY * 0.005 };
        targetRotY += dragVelocity.x;
        targetRotX += dragVelocity.y;
        previousPointerPosition = { x: e.clientX, y: e.clientY };
      } else {
        // Gentle mouse parallax when idle (clamped to never push Moon towards boundary)
        const normX = (e.clientX / window.innerWidth - 0.5) * 2;
        const normY = (e.clientY / window.innerHeight - 0.5) * 2;
        camera.position.x = THREE.MathUtils.lerp(camera.position.x, normX * 0.12, 0.04);
        camera.position.y = THREE.MathUtils.lerp(camera.position.y, -normY * 0.08, 0.04);
      }
    };

    const handlePointerUp = () => {
      isDragging = false;
    };

    const domElement = renderer.domElement;
    domElement.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);

    // Responsive camera framing and resize observer
    const handleResize = () => {
      if (!container || !renderer) return;
      const w = container.clientWidth || window.innerWidth;
      const h = container.clientHeight || window.innerHeight;
      camera.aspect = w / Math.max(h, 1);
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
      targetCameraZ = calculateTargetZ(w, h);
    };

    window.addEventListener("resize", handleResize);
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // 7. Animation Loop with Camera Glide
    let animationFrameId: number;
    let lastTime = performance.now();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const now = performance.now();
      const delta = Math.min((now - lastTime) / 1000, 0.1);
      lastTime = now;

      // Smooth camera glide entry
      if (Math.abs(camera.position.z - targetCameraZ) > 0.005) {
        camera.position.z = THREE.MathUtils.lerp(camera.position.z, targetCameraZ, 0.035);
      }

      // Very subtle celestial idle rotation when not dragging
      if (!isDragging) {
        targetRotY += 0.035 * delta;
      }

      // Inertia interpolation for smooth rotation
      moonMesh.rotation.y = THREE.MathUtils.lerp(moonMesh.rotation.y, targetRotY, 0.08);
      moonMesh.rotation.x = THREE.MathUtils.lerp(moonMesh.rotation.x, targetRotX, 0.08);

      // Clamp vertical tilt to prevent awkward pole flipping
      targetRotX = THREE.MathUtils.clamp(targetRotX, -0.6, 0.6);

      if (renderer) {
        renderer.render(scene, camera);
      }
    };

    animate();

    // 8. Clean Disposal on Unmount
    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      window.removeEventListener("resize", handleResize);
      domElement.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);

      geometry.dispose();
      material.dispose();
      placeholderTexture.dispose();
      if (material.map && material.map !== placeholderTexture) {
        material.map.dispose();
      }
      if (material.bumpMap) {
        material.bumpMap.dispose();
      }

      if (renderer) {
        renderer.dispose();
        if (domElement.parentElement) {
          domElement.parentElement.removeChild(domElement);
        }
      }
    };
  }, []);

  if (!webGLSupported) {
    return (
      <div className={`relative flex items-center justify-center overflow-hidden ${className}`}>
        <img
          src="/assets/textures/moon-2k.jpg"
          alt="Photorealistic lunar surface fallback"
          className="max-h-[85vh] w-auto object-contain opacity-90 drop-shadow-[0_20px_50px_rgba(0,0,0,0.9)]"
        />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`relative h-full w-full cursor-grab active:cursor-grabbing select-none ${className}`}
    >
      {/* Loading state indicator */}
      {!isLoaded && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted/60 animate-pulse">
            CALIBRATING LUNAR GEOMETRY…
          </span>
        </div>
      )}
    </div>
  );
}
