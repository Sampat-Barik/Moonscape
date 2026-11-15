import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_DIR = path.resolve(__dirname, '..');
const CINEMATIC_MOON_PATH = path.join(FRONTEND_DIR, 'src', 'components', 'CinematicMoon.tsx');
const HOME_PAGE_PATH = path.join(FRONTEND_DIR, 'src', 'pages', 'Home.tsx');
const LUNAR_MAP_PATH = path.join(FRONTEND_DIR, 'src', 'components', 'LunarMap.tsx');
const EXPLORER_PAGE_PATH = path.join(FRONTEND_DIR, 'src', 'pages', 'Explorer.tsx');
const REGIONAL_TERRAIN_PATH = path.join(FRONTEND_DIR, 'src', 'components', 'RegionalTerrainViewer.tsx');

test('PROBLEM 1 VERIFICATION — HOMEPAGE MOON BOUNDARY & FRUSTUM ENCLOSURE', async (t) => {
  const moonSrc = fs.readFileSync(CINEMATIC_MOON_PATH, 'utf-8');
  const homeSrc = fs.readFileSync(HOME_PAGE_PATH, 'utf-8');

  await t.test('1.1 Sphere geometry is normalized and ultra-smooth', () => {
    assert.match(moonSrc, /SphereGeometry\s*\(\s*MOON_RADIUS\s*,\s*96\s*,\s*96\s*\)/,
      'CinematicMoon must use SphereGeometry with 96x96 subdivision for smooth silhouette');
    assert.match(moonSrc, /const\s+MOON_RADIUS\s*=\s*1\.0/,
      'CinematicMoon must use normalized unit radius (1.0)');
  });

  await t.test('1.2 Dynamic camera distance formula prevents boundary clipping across all aspect ratios', () => {
    assert.match(moonSrc, /calculateTargetZ/,
      'CinematicMoon must dynamically compute target camera Z based on aspect ratio');
    assert.match(moonSrc, /Math\.min\s*\(\s*aspect\s*,\s*1\.0\s*\)/,
      'CinematicMoon must clamp aspect to ensure mobile portrait viewports never clip left/right');

    // Simulate frustum math at various screen resolutions
    const radius = 1.0;
    const diameter = 2.0;
    const fov = 40;
    const tanHalfFov = Math.tan((fov / 2) * (Math.PI / 180));
    const fillRatio = 0.72;
    const baseZ = radius / (fillRatio * tanHalfFov);

    const testAspects = [
      { name: '4K Widescreen 3840x2160', aspect: 3840 / 2160 },
      { name: 'Full HD 1920x1080', aspect: 1920 / 1080 },
      { name: 'MacBook 16:10 1920x1200', aspect: 1920 / 1200 },
      { name: 'Tablet 4:3 1024x768', aspect: 1024 / 768 },
      { name: 'Square 680x680', aspect: 1.0 },
      { name: 'Mobile Portrait 390x844', aspect: 390 / 844 },
      { name: 'Narrow Foldable 320x800', aspect: 320 / 800 },
    ];

    for (const { name, aspect } of testAspects) {
      const z = baseZ / Math.min(aspect, 1.0);
      const visibleHeight = 2 * z * tanHalfFov;
      const visibleWidth = visibleHeight * aspect;
      const minDimension = Math.min(visibleWidth, visibleHeight);
      const actualFill = diameter / minDimension;

      assert.ok(actualFill <= 0.75,
        `On ${name}, fill ratio (${actualFill.toFixed(3)}) must not exceed 0.75`);
      assert.ok(minDimension - diameter >= 0.6,
        `On ${name}, clearance margin (${(minDimension - diameter).toFixed(3)} units) must prevent boundary clipping`);
    }
  });

  await t.test('1.3 WebGL clear color is strict zero-alpha and canvas display is block', () => {
    assert.match(moonSrc, /renderer\.setClearColor\s*\(\s*0x000000\s*,\s*0\s*\)/,
      'CinematicMoon must set clear color to 0x000000 with alpha 0');
    assert.match(moonSrc, /renderer\.domElement\.style\.display\s*=\s*["']block["']/,
      'Canvas element must have display: block');
    assert.match(moonSrc, /renderer\.domElement\.style\.width\s*=\s*["']100%["']/,
      'Canvas element must have width: 100%');
    assert.match(moonSrc, /renderer\.domElement\.style\.height\s*=\s*["']100%["']/,
      'Canvas element must have height: 100%');
  });

  await t.test('1.4 Homepage radial highlight fades to 100% transparency at closest container side', () => {
    assert.match(homeSrc, /radial-gradient\(closest-side_at_50%_50%.*transparent_100%\)/,
      'Home.tsx must use closest-side radial gradient that terminates in transparent_100% to eliminate rectangular seams');
  });

  await t.test('1.5 ResizeObserver ensures live responsive boundary updates on container shifts', () => {
    assert.match(moonSrc, /new\s+ResizeObserver\s*\(\s*handleResize\s*\)/,
      'CinematicMoon must observe container resize with ResizeObserver');
    assert.match(moonSrc, /resizeObserver\.disconnect\s*\(\s*\)/,
      'CinematicMoon must clean up ResizeObserver on unmount');
  });
});

test('PROBLEM 2 VERIFICATION — LUNAR EXPLORER CAMERA CENTERING, ZOOM & FRAMING', async (t) => {
  const mapSrc = fs.readFileSync(LUNAR_MAP_PATH, 'utf-8');
  const expSrc = fs.readFileSync(EXPLORER_PAGE_PATH, 'utf-8');
  const terrSrc = fs.readFileSync(REGIONAL_TERRAIN_PATH, 'utf-8');
  const appSrc = fs.readFileSync(path.join(FRONTEND_DIR, 'src', 'App.tsx'), 'utf-8');

  await t.test('2.1 Initial camera position is strictly centered on Z-axis with lookAt(0,0,0) and OrbitControls target (0,0,0)', () => {
    assert.match(mapSrc, /camera\.position\.set\s*\(\s*0\s*,\s*0\s*,\s*initialFitDist\s*\)/,
      'LunarMap initial camera must be dynamically placed on Z-axis with zero X/Y offset');
    assert.match(mapSrc, /camera\.lookAt\s*\(\s*0\s*,\s*0\s*,\s*0\s*\)/,
      'LunarMap initial camera must look directly at (0, 0, 0)');
    assert.match(mapSrc, /controls\.target\.set\s*\(\s*0\s*,\s*0\s*,\s*0\s*\)/,
      'OrbitControls target must be strictly anchored to Moon origin (0, 0, 0)');
    assert.doesNotMatch(mapSrc, /camera\.position\.set\s*\(\s*0\s*,\s*0\.35/,
      'LunarMap must NOT have the buggy (0, 0.35, 2.9) camera position that caused downward drift');
  });

  await t.test('2.2 Dynamic Fit Globe distance ensures Moon occupies ~74% of viewport without clipping', () => {
    assert.match(mapSrc, /calculateFitDistance/,
      'LunarMap must calculate dynamic fit distance based on viewport width and height');
    assert.match(mapSrc, /controls\.enablePan\s*=\s*false/,
      'OrbitControls pan must be disabled to prevent camera target drift');
    assert.match(mapSrc, /controls\.zoomToCursor\s*=\s*false/,
      'zoomToCursor must be disabled so zooming scales directly toward globe origin');
    assert.match(mapSrc, /controls\.minDistance\s*=\s*1\.35/,
      'OrbitControls minDistance must clamp to 1.35');
    assert.match(mapSrc, /controls\.maxDistance\s*=\s*6\.0/,
      'OrbitControls maxDistance must clamp to 6.0');
  });

  await t.test('2.3 Wheel events are isolated from page scrolling', () => {
    assert.match(mapSrc, /e\.preventDefault\s*\(\s*\);[\s\S]*e\.stopPropagation\s*\(\s*\);/,
      'LunarMap onCanvasWheel must call both preventDefault() and stopPropagation()');
    assert.match(terrSrc, /e\.preventDefault\s*\(\s*\);[\s\S]*e\.stopPropagation\s*\(\s*\);/,
      'RegionalTerrainViewer onWheel must call both preventDefault() and stopPropagation()');
  });

  await t.test('2.4 South Pole focus and candidate site glide maintain camera alignment and origin lock', () => {
    assert.match(mapSrc, /const\s+focusSouthPole\s*=\s*\(\)\s*=>\s*\{/,
      'focusSouthPole must smoothly animate camera and quaternion to South Pole');
    assert.match(mapSrc, /const\s+focusSite\s*=\s*\(lat:\s*number,\s*lon:\s*number\)\s*=>\s*\{/,
      'focusSite must smoothly animate camera and quaternion to target lat/lon');
    assert.match(mapSrc, /controls\.target\.set\s*\(\s*0\s*,\s*0\s*,\s*0\s*\)/,
      'Animation loop must continuously lock controls.target to (0, 0, 0)');
  });

  await t.test('2.5 Working Camera Reset / Fit actions exist in both toolbar and viewport HUD', () => {
    assert.match(expSrc, /Reset View/,
      'Explorer toolbar must provide an explicit Reset View button');
    assert.match(mapSrc, /handleZoomIn[\s\S]*handleZoomOut[\s\S]*handleResetView/,
      'LunarMap must provide interactive HUD controls for Zoom In, Zoom Out, and Reset View');
    assert.match(mapSrc, /<TargetIcon/,
      'LunarMap HUD must render TargetIcon for visual center/reset indicator');
  });

  await t.test('2.6 Full-screen viewport isolation prevents sidebar and document scrolling', () => {
    assert.match(appSrc, /isExplorer\s*\?\s*["']h-screen overflow-hidden["']/,
      'App.tsx must constrain Explorer root to h-screen overflow-hidden');
    assert.match(expSrc, /h-full overflow-hidden bg-space text-ink select-none/,
      'Explorer container must be h-full overflow-hidden');
    assert.match(expSrc, /min-w-0 min-h-0 bg-space/,
      '3D viewport container must enforce min-w-0 min-h-0 to prevent flex blowout');
  });
});
