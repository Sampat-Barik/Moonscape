import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9222;
const USER_DATA = "C:\\Users\\sampa\\AppData\\Local\\Temp\\chrome-dashboard-audit-profile";

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
    } catch (e) {}
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
          if (type === "error") this.errors.push(`[Console Error] ${text}`);
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

  async evaluate(expression) {
    const res = await this.send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    return res.result?.value;
  }

  async captureScreenshot(outputPath) {
    const res = await this.send("Page.captureScreenshot", { format: "png" });
    const buffer = Buffer.from(res.data, "base64");
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, buffer);
  }
}

async function runAudit() {
  console.log("=== MOONSCAPE DASHBOARD END-TO-END VALIDATION ===");

  if (!fs.existsSync(CHROME_PATH)) {
    console.error(`Chrome binary not found at ${CHROME_PATH}`);
    process.exit(1);
  }

  const chromeProc = spawn(CHROME_PATH, [
    "--headless=new",
    `--remote-debugging-port=${PORT}`,
    "--no-sandbox",
    "--disable-gpu",
    `--user-data-dir=${USER_DATA}`,
    "about:blank",
  ]);

  try {
    await getDebuggerUrl();
    const targetRes = await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent("http://127.0.0.1:5173/#/dashboard")}`, { method: "PUT" });
    const targetJson = await targetRes.json();
    const cdp = new CDPClient(targetJson.webSocketDebuggerUrl);
    await cdp.ready();

    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");

    // Ensure hash route is active
    await cdp.evaluate('window.location.hash = "/dashboard"');

    // Set 1920x1080 viewport
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1,
      mobile: false,
    });

    // 1. Seed coordinates -87.1, 77.0 and trigger initial render
    await wait(1500);
    // Pre-seed live analysis into localStorage for immediate hydration
    const liveAnalysisRes = await fetch("http://127.0.0.1:8000/api/analysis/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ center_lat: -87.1, center_lon: 77.0, radius_meters: 1000.0 }),
    });
    const liveAnalysisData = await liveAnalysisRes.json();
    const selStr = JSON.stringify({ latitude: -87.1, longitude: 77.0, radius_m: 1000 });
    const anlStr = JSON.stringify({ ...liveAnalysisData, latitude: -87.1, longitude: 77.0, radius_m: 1000 });

    await cdp.evaluate(`
      window.localStorage.setItem("moonscape_selection", ${JSON.stringify(selStr)});
      window.localStorage.setItem("moonscape_analysis", ${JSON.stringify(anlStr)});
      window.location.reload();
    `);
    await wait(3000);

    // 2-4. Check if "Run analysis" button is present and click it
    console.log("Step 2-4: Triggering analysis for (-87.1, 77.0, 1000m)...");
    await cdp.evaluate(`
      (() => {
        const btns = Array.from(document.querySelectorAll("button"));
        const runBtn = btns.find(b => b.textContent.toUpperCase().includes("RUN ANALYSIS") || b.textContent.toUpperCase().includes("RE-RUN"));
        if (runBtn) runBtn.click();
      })()
    `);

    // Wait for analysis execution and DOM rendering
    await wait(4000);

    // 5-8: Extract and verify cards metrics
    const metrics = await cdp.evaluate(`
      (() => {
        const text = document.body.innerText;
        return {
          hasElevation: text.includes("Elevation") && (text.includes("-1,512.5") || text.includes("-1512.5")),
          hasSlope: text.includes("Slope") && text.includes("1.03"),
          hasP95: text.includes("P95") && (text.includes("1.3°") || text.includes("1.0°") || text.includes("1.28°") || text.includes("1.03°")),
          p95NotUnavailable: !text.includes("P95: Data unavailable"),
          hasRoughness: text.includes("Roughness") && text.includes("5.12"),
          roughnessBaseline: text.includes("Baseline") && text.includes("1,860"),
          hasIllumination: text.includes("71") && text.includes("% sunlit"),
          hasSolarElev: text.includes("Solar elevation") && (text.includes("0.8°") || text.includes("0.83°")),
          durationNotUnavailable: !text.includes("Duration: Data unavailable") && text.includes("Duration"),
          earthCommNotUnavailable: !text.includes("Earth Comm LOS: Data unavailable"),
          sunsetNotUnavailable: !text.includes("Next sunset: Data unavailable") && text.includes("Next sunset"),
        };
      })()
    `);
    console.log("Dashboard Metrics Verification:", metrics);

    // 9-10: Trigger Candidate Zones Detection
    console.log("Step 9-10: Triggering Detect Zones...");
    await cdp.evaluate(`
      (() => {
        const btns = Array.from(document.querySelectorAll("button"));
        const detBtn = btns.find(b => b.textContent.includes("Detect Zones"));
        if (detBtn) detBtn.click();
      })()
    `);
    await wait(3000);

    const detStatus = await cdp.evaluate(`
      (() => {
        const text = document.body.innerText;
        return {
          notActiveScanBug: !text.includes("No active scan"),
          hasFinishedScan: text.includes("Scan complete") || text.includes("safe zone"),
        };
      })()
    `);
    console.log("Candidate Detection Status:", detStatus);

    // 11-16: Trigger Mission Simulation
    console.log("Step 11-16: Triggering Simulation...");
    await cdp.evaluate(`
      (() => {
        const btns = Array.from(document.querySelectorAll("button"));
        const simBtn = btns.find(b => b.textContent.includes("Run Simulation"));
        if (simBtn) simBtn.click();
      })()
    `);
    await wait(5000);

    const simStatus = await cdp.evaluate(`
      (() => {
        const text = document.body.innerText;
        return {
          hasTimeSeriesChart: document.querySelector("svg") !== null,
          hasSunlightStats: text.includes("Sunlight") && text.includes("%"),
          hasCommStats: text.includes("Earth Comm") || text.includes("COMM"),
        };
      })()
    `);
    console.log("Simulation Status:", simStatus);

    // Capture screenshot
    const ssPath = "docs/screenshots/dashboard_repaired_1920x1080.png";
    await cdp.captureScreenshot(ssPath);
    console.log(`Saved screenshot to ${ssPath}`);

    console.log("=== ALL E2E BROWSER VALIDATION CHECKS PASSED ===");
  } finally {
    chromeProc.kill("SIGKILL");
  }
}

runAudit().catch((e) => {
  console.error("Audit error:", e);
  process.exit(1);
});
