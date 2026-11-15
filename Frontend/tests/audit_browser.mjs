import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9222;
const USER_DATA = "C:\\Users\\sampa\\AppData\\Local\\Temp\\chrome-explorer-audit-profile";

async function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getDebuggerUrl() {
  for (let i = 0; i < 20; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (res.ok) {
        const json = await res.json();
        return json.webSocketDebuggerUrl;
      }
    } catch (e) {
      // retry
    }
    await wait(300);
  }
  throw new Error("Could not connect to Chrome debugging port");
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.pending = new Map();
    this.consoleLogs = [];
    this.errors = [];

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.id && this.pending.has(data.id)) {
        const { resolve, reject } = this.pending.get(data.id);
        this.pending.delete(data.id);
        if (data.error) reject(data.error);
        else resolve(data.result);
      } else if (data.method) {
        if (data.method === "Runtime.consoleAPICalled") {
          const type = data.params.type;
          const text = data.params.args.map((a) => (a.value !== undefined ? a.value : JSON.stringify(a))).join(" ");
          this.consoleLogs.push({ type, text });
          if (type === "error") {
            this.errors.push(`[Console Error] ${text}`);
          }
        }
        if (data.method === "Runtime.exceptionThrown") {
          const desc = data.params.exceptionDetails.exception?.description || data.params.exceptionDetails.text;
          this.errors.push(`[Exception] ${desc}`);
        }
        if (data.method === "Log.entryAdded") {
          const entry = data.params.entry;
          if (entry.level === "error") {
            this.errors.push(`[Log Error] ${entry.text}`);
          }
        }
      }
    };
  }

  async ready() {
    if (this.ws.readyState === WebSocket.OPEN) return;
    return new Promise((resolve) => {
      this.ws.onopen = resolve;
    });
  }

  send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async eval(expression) {
    const res = await this.send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    return res.result?.value;
  }

  close() {
    this.ws.close();
  }
}

const VIEWPORTS = [
  { name: "1920px", width: 1920, height: 1080 },
  { name: "1440px", width: 1440, height: 900 },
  { name: "1280px", width: 1280, height: 800 },
  { name: "1024px", width: 1024, height: 768 },
  { name: "768px", width: 768, height: 1024, isMobile: true },
  { name: "390px", width: 390, height: 844, isMobile: true },
];

async function auditExplorer() {
  console.log("==================================================");
  console.log("MOONSCAPE LUNAR EXPLORER QA & RESPONSIVE AUDIT");
  console.log("==================================================");

  const outDir = path.resolve("docs/screenshots");
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  console.log("Spawning Chrome (headless)...");
  const chrome = spawn(CHROME_PATH, [
    "--headless=new",
    `--remote-debugging-port=${PORT}`,
    "--no-sandbox",
    "--disable-gpu",
    `--user-data-dir=${USER_DATA}`,
    "about:blank",
  ]);

  const auditReport = {
    viewports: [],
    modeSwitching: {},
    popovers: {},
    errors: [],
  };

  try {
    await getDebuggerUrl();
    const targetRes = await fetch(`http://127.0.0.1:${PORT}/json/new?http://localhost:5173/#/explorer`, { method: "PUT" });
    const targetJson = await targetRes.json();
    const client = new CDPClient(targetJson.webSocketDebuggerUrl);
    await client.ready();

    await client.send("Page.enable");
    await client.send("Runtime.enable");
    await client.send("Log.enable");

    // 1. Audit Explorer across all 6 requested viewports
    for (const vp of VIEWPORTS) {
      console.log(`\nTesting Viewport: ${vp.name} (${vp.width}x${vp.height})...`);
      await client.send("Emulation.setDeviceMetricsOverride", {
        width: vp.width,
        height: vp.height,
        deviceScaleFactor: 1,
        mobile: !!vp.isMobile,
      });

      await client.send("Page.navigate", { url: "http://localhost:5173/#/explorer" });
      await wait(3500);

      // Verify layout architecture dimensions
      const layoutMetrics = await client.eval(`
        (() => {
          const header = document.querySelector('header');
          const toolbar = document.querySelector('nav[aria-label="Lunar Explorer Controls"]');
          const sidebar = document.querySelector('aside');
          const canvas = document.querySelector('canvas');
          
          const headerRect = header ? header.getBoundingClientRect() : null;
          const toolbarRect = toolbar ? toolbar.getBoundingClientRect() : null;
          const sidebarRect = sidebar ? sidebar.getBoundingClientRect() : null;
          
          // Check for collision between header and toolbar (allow subpixel border boundary)
          const isOverlapping = headerRect && toolbarRect && (toolbarRect.top < headerRect.bottom - 1);
          
          return {
            headerHeight: headerRect ? headerRect.height : 0,
            toolbarTop: toolbarRect ? toolbarRect.top : 0,
            toolbarHeight: toolbarRect ? toolbarRect.height : 0,
            sidebarWidth: sidebarRect ? sidebarRect.width : 0,
            hasCanvas: !!canvas,
            isOverlapping: isOverlapping,
          };
        })()
      `);

      console.log(`  -> Header Height: ${layoutMetrics.headerHeight}px, Toolbar Top: ${layoutMetrics.toolbarTop}px`);
      console.log(`  -> Toolbar Height: ${layoutMetrics.toolbarHeight}px, Sidebar Width: ${layoutMetrics.sidebarWidth}px`);
      console.log(`  -> Controls Overlap Detected: ${layoutMetrics.isOverlapping}`);

      const shot = await client.send("Page.captureScreenshot", { format: "png" });
      const filename = `explorer_${vp.name}.png`;
      fs.writeFileSync(path.join(outDir, filename), Buffer.from(shot.data, "base64"));
      console.log(`  -> Screenshot saved: docs/screenshots/${filename}`);

      auditReport.viewports.push({
        name: vp.name,
        width: vp.width,
        height: vp.height,
        metrics: layoutMetrics,
        screenshot: filename,
      });
    }

    // Reset to Desktop 1920x1080 for interactive feature tests
    await client.send("Emulation.setDeviceMetricsOverride", {
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await client.send("Page.navigate", { url: "http://localhost:5173/#/explorer" });
    await wait(3500);

    // 2. Test Segmented View Mode Switching: Globe -> Terrain -> Cesium
    console.log("\nTesting Segmented View Mode Selector...");

    // Click 'Terrain'
    console.log("  -> Switching to 'Terrain' mode (Segmented button)...");
    await client.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button[role="radio"]'));
        const terrainBtn = btns.find(b => b.textContent.includes('Terrain'));
        if (terrainBtn) terrainBtn.click();
      })()
    `);
    await wait(3500);
    const shotTerrain = await client.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(path.join(outDir, "explorer_mode_terrain.png"), Buffer.from(shotTerrain.data, "base64"));
    console.log("  -> Saved: docs/screenshots/explorer_mode_terrain.png");

    // Click 'Cesium'
    console.log("  -> Switching to 'Cesium' mode (Segmented button)...");
    await client.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button[role="radio"]'));
        const cesiumBtn = btns.find(b => b.textContent.includes('Cesium'));
        if (cesiumBtn) cesiumBtn.click();
      })()
    `);
    await wait(4000);
    const shotCesium = await client.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(path.join(outDir, "explorer_mode_cesium.png"), Buffer.from(shotCesium.data, "base64"));
    console.log("  -> Saved: docs/screenshots/explorer_mode_cesium.png");

    // Click 'Globe' back
    console.log("  -> Switching back to 'Globe' mode...");
    await client.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button[role="radio"]'));
        const globeBtn = btns.find(b => b.textContent.includes('Globe'));
        if (globeBtn) globeBtn.click();
      })()
    `);
    await wait(3000);

    // 3. Test Basemap Popover Dropdown
    console.log("\nTesting Basemap Dropdown Popover...");
    await client.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const basemapBtn = btns.find(b => b.textContent.includes('Basemap'));
        if (basemapBtn) basemapBtn.click();
      })()
    `);
    await wait(1000);
    const shotBasemap = await client.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(path.join(outDir, "explorer_basemap_popover.png"), Buffer.from(shotBasemap.data, "base64"));
    console.log("  -> Saved: docs/screenshots/explorer_basemap_popover.png");

    // 4. Test Solar Simulation Popover
    console.log("\nTesting Solar Simulation Popover...");
    await client.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const sunBtn = btns.find(b => b.title && b.title.includes('solar diurnal'));
        if (sunBtn) sunBtn.click();
      })()
    `);
    await wait(1000);
    const shotSolar = await client.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(path.join(outDir, "explorer_solar_popover.png"), Buffer.from(shotSolar.data, "base64"));
    console.log("  -> Saved: docs/screenshots/explorer_solar_popover.png");

    // 5. Test Quick Candidate Site Click
    console.log("\nTesting Quick Preset Site Click...");
    await client.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const siteBtn = btns.find(b => b.textContent.includes('Connecting Ridge'));
        if (siteBtn) siteBtn.click();
      })()
    `);
    await wait(2000);

    // Record collected errors
    auditReport.errors = client.errors;

    console.log("\n==================================================");
    console.log(`LUNAR EXPLORER AUDIT COMPLETE: 6 viewports + 4 interaction states captured.`);
    console.log(`Console Errors: ${client.errors.length}`);
    if (client.errors.length > 0) {
      console.log("Errors logged:");
      client.errors.forEach((e) => console.log("  " + e));
    }
    console.log("==================================================");

    fs.writeFileSync(path.join(outDir, "explorer_audit_summary.json"), JSON.stringify(auditReport, null, 2));

    client.close();
  } finally {
    chrome.kill();
  }
}

auditExplorer().catch((err) => {
  console.error("Explorer QA script failed:", err);
  process.exit(1);
});
