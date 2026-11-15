import { useEffect, useRef, useState } from "react";
import LoadingState from "./LoadingState";
import { fmtCoord } from "@/utils/format";

interface CesiumLunarViewerProps {
  className?: string;
  selected?: { lat: number; lon: number };
  onSelect?: (lat: number, lon: number) => void;
  markers?: Array<{ lat: number; lon: number; label: string; color?: string }>;
}

/**
 * CesiumLunarViewer — Geospatial 3D lunar surface visualizer powered by CesiumJS.
 * Utilizes the IAU Moon reference ellipsoid (mean radius 1,737,400 m) with polar camera framing.
 */
export default function CesiumLunarViewer({
  className = "",
  selected,
  onSelect,
  markers = [],
}: CesiumLunarViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let viewer: any = null;
    let destroyed = false;

    async function initCesium() {
      try {
        setLoading(true);
        setError(null);

        // Dynamically import Cesium to preserve fast initial page loads
        const Cesium = await import("cesium");

        if (destroyed || !containerRef.current) return;

        // Lunar Ellipsoid: R = 1,737,400 meters
        const moonEllipsoid = new Cesium.Ellipsoid(1737400.0, 1737400.0, 1737400.0);

        // Prevent Cesium Ion network calls for Earth assets
        if (Cesium.Ion) {
          Cesium.Ion.defaultAccessToken = "";
        }

        // Initialize Cesium Viewer with Moon Globe (no default Earth imagery/terrain)
        viewer = new Cesium.Viewer(containerRef.current, {
          globe: new Cesium.Globe(moonEllipsoid),
          baseLayer: false, // Prevents Cesium Ion Earth imagery network fetch
          terrainProvider: new Cesium.EllipsoidTerrainProvider({ ellipsoid: moonEllipsoid }),
          skyBox: false,
          skyAtmosphere: false,
          animation: false,
          timeline: false,
          baseLayerPicker: false,
          geocoder: false,
          homeButton: false,
          infoBox: false,
          sceneModePicker: false,
          selectionIndicator: false,
          navigationHelpButton: false,
          fullscreenButton: false,
        });

        // Load local NASA LROC mosaic on lunar ellipsoid
        try {
          const imageryProvider = await Cesium.SingleTileImageryProvider.fromUrl(
            "/assets/textures/lroc_color_2k.jpg",
            { ellipsoid: moonEllipsoid }
          );
          if (viewer && !viewer.isDestroyed()) {
            viewer.imageryLayers.addImageryProvider(imageryProvider);
          }
        } catch (imageryErr) {
          console.warn("Cesium local lunar texture loading fallback:", imageryErr);
        }

        // Hide default credits container for clean HUD
        if (viewer.bottomContainer) {
          viewer.bottomContainer.style.display = "none";
        }

        // Configure atmospheric & lighting realism
        viewer.scene.globe.enableLighting = true;
        viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#171717");
        viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#090909");

        // Focus South Pole: 90°S, 0°E, altitude ~1,200 km
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(
            0.0,
            -85.0,
            1200000.0,
            moonEllipsoid
          ),
          orientation: {
            heading: Cesium.Math.toRadians(0.0),
            pitch: Cesium.Math.toRadians(-90.0),
            roll: 0.0,
          },
          duration: 1.5,
        });

        // Add candidate site pins
        markers.forEach((m) => {
          viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(m.lon, m.lat, 2000, moonEllipsoid),
            point: {
              pixelSize: 8,
              color: Cesium.Color.fromCssColorString(m.color || "#F1F1EF"),
              outlineColor: Cesium.Color.BLACK,
              outlineWidth: 2,
            },
            label: {
              text: m.label,
              font: "10px 'IBM Plex Mono', monospace",
              fillColor: Cesium.Color.fromCssColorString("#F1F1EF"),
              showBackground: true,
              backgroundColor: Cesium.Color.fromCssColorString("rgba(23, 23, 23, 0.85)"),
              pixelOffset: new Cesium.Cartesian2(0, -14),
            },
          });
        });

        // Handle click selection on the lunar ellipsoid
        const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
        handler.setInputAction((click: any) => {
          const ray = viewer.camera.getPickRay(click.position);
          if (!ray) return;
          const cartesian = viewer.scene.globe.pick(ray, viewer.scene);
          if (cartesian) {
            const cartographic = moonEllipsoid.cartesianToCartographic(cartesian);
            const lat = Cesium.Math.toDegrees(cartographic.latitude);
            const lon = Cesium.Math.toDegrees(cartographic.longitude);
            if (onSelect) {
              onSelect(lat, lon);
            }
          }
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

        setLoading(false);
      } catch (err) {
        console.warn("Cesium lunar globe initialization error:", err);
        setError(
          err instanceof Error
            ? err.message
            : "Cesium WebGL rendering could not be initialized."
        );
        setLoading(false);
      }
    }

    void initCesium();

    return () => {
      destroyed = true;
      if (viewer && !viewer.isDestroyed()) {
        viewer.destroy();
      }
    };
  }, []);

  return (
    <div className={`relative overflow-hidden bg-space ${className}`}>
      <div ref={containerRef} className="h-full w-full" />

      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-space/80 backdrop-blur-sm z-30">
          <LoadingState label="Initializing CesiumJS IAU Lunar Ellipsoid (1,737.4 km radius)…" />
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-space/90 p-6 z-30">
          <div className="panel max-w-md p-6 text-center border-divider">
            <h4 className="font-display text-sm font-semibold text-ink">
              CesiumJS Lunar Globe Offline
            </h4>
            <p className="mt-2 text-xs text-muted leading-relaxed">
              {error}
            </p>
            <p className="mt-3 text-[11px] text-muted font-mono">
              The Three.js polar graticule mode remains active and fully functional.
            </p>
          </div>
        </div>
      )}

      {/* Selected Coordinate readout overlay */}
      {selected && (
        <div className="pointer-events-none absolute bottom-5 left-5 z-20">
          <div className="glass-soft rounded px-3 py-1.5">
            <span className="font-mono text-xs text-ink">
              CESIUM GEO: {fmtCoord(selected.lat, selected.lon)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
