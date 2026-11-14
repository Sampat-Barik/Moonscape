/**
 * Moonscape Frontend Application Logic
 * Integrates directly with FastAPI backend at http://localhost:8000/api
 * Implements interactive lunar South Pole GIS map, real-time coverage validation,
 * temporal Sun/Earth visibility time-series visualization, contiguous zone detection,
 * MCDA & ML surrogate scoring, grounded AI scientific assistant, and PDF reports.
 */

const API_BASE = "http://localhost:8000/api";

let candidateSites = [];
let mapConfig = null;
let currentAnalysis = null;
let currentSimulation = null;
let coverageDebounceTimer = null;

// DOM Elements
const healthBadge = document.getElementById("healthBadge");
const statusDot = document.getElementById("statusDot");
const healthText = document.getElementById("healthText");
const siteSelect = document.getElementById("siteSelect");
const latInput = document.getElementById("latInput");
const lonInput = document.getElementById("lonInput");
const radiusInput = document.getElementById("radiusInput");
const coverageBadge = document.getElementById("coverageBadge");
const coverageText = document.getElementById("coverageText");

const missionProfileSelect = document.getElementById("missionProfileSelect");
const epochInput = document.getElementById("epochInput");
const durationInput = document.getElementById("durationInput");
const stepSelect = document.getElementById("stepSelect");

const btnSamplePoint = document.getElementById("btnSamplePoint");
const btnRunAnalysis = document.getElementById("btnRunAnalysis");
const btnDetectSites = document.getElementById("btnDetectSites");
const btnSimulateVisibility = document.getElementById("btnSimulateVisibility");
const btnCompareSites = document.getElementById("btnCompareSites");
const compareResults = document.getElementById("compareResults");

const btnScenario1 = document.getElementById("btnScenario1");
const btnScenario2 = document.getElementById("btnScenario2");
const btnScenario3 = document.getElementById("btnScenario3");

const mapLayerSelect = document.getElementById("mapLayerSelect");
const lunarMapCanvas = document.getElementById("lunarMapCanvas");
const mapTooltip = document.getElementById("mapTooltip");

const welcomeCard = document.getElementById("welcomeCard");
const analysisCard = document.getElementById("analysisCard");
const hazardsCard = document.getElementById("hazardsCard");
const detectionCard = document.getElementById("detectionCard");
const simulationCard = document.getElementById("simulationCard");
const suitabilityCard = document.getElementById("suitabilityCard");
const aiCard = document.getElementById("aiCard");
const reportCard = document.getElementById("reportCard");

const btnRequestAi = document.getElementById("btnRequestAi");
const btnSubmitAiQuery = document.getElementById("btnSubmitAiQuery");
const aiCustomPrompt = document.getElementById("aiCustomPrompt");
const aiLoading = document.getElementById("aiLoading");
const aiContent = document.getElementById("aiContent");
const btnDownloadPdf = document.getElementById("btnDownloadPdf");
const btnViewJsonReport = document.getElementById("btnViewJsonReport");

// ---------------------------------------------------------------------------
// 1. Health & Initialization
// ---------------------------------------------------------------------------

async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    statusDot.className = "status-dot healthy";
    healthText.textContent = `Online (v${data.version} | ${data.sites_loaded} Sites)`;
  } catch (err) {
    statusDot.className = "status-dot error";
    healthText.textContent = "Backend Offline (Retrying...)";
    setTimeout(checkBackendHealth, 5000);
  }
}

async function loadCandidateSites() {
  try {
    const res = await fetch(`${API_BASE}/sites`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    candidateSites = await res.json();
    siteSelect.innerHTML = '<option value="">-- Choose Candidate Site --</option>';
    candidateSites.forEach((site) => {
      const opt = document.createElement("option");
      opt.value = site.site_id;
      opt.textContent = `${site.name} (Lat: ${site.latitude.toFixed(2)}°, Lon: ${site.longitude.toFixed(2)}°)`;
      siteSelect.appendChild(opt);
    });
    drawLunarMap();
  } catch (err) {
    console.error("Failed to load candidate sites:", err);
  }
}

async function loadMapConfig() {
  try {
    const res = await fetch(`${API_BASE}/map/config`);
    if (res.ok) {
      mapConfig = await res.json();
    }
  } catch (err) {
    console.warn("Map config load failed:", err);
  }
}

// ---------------------------------------------------------------------------
// 2. Interactive Lunar South Pole GIS Map (Polar Stereographic Projection)
// ---------------------------------------------------------------------------

const mapCtx = lunarMapCanvas ? lunarMapCanvas.getContext("2d") : null;
const MAP_CENTER = 220;
const MAP_RADIUS = 195; // Radius representing -80 deg latitude outer boundary

function latLonToCanvas(lat, lon) {
  // Polar Stereographic math: Center is -90.0, outer circle is -80.0
  const clampedLat = Math.min(-80.0, Math.max(-90.0, lat));
  const r = ((clampedLat - (-90.0)) / 10.0) * MAP_RADIUS;
  // Convert longitude (0-360) to radians. 0 deg is oriented toward Earth (Top, -Y)
  const rad = ((lon - 90.0) * Math.PI) / 180.0;
  return {
    x: MAP_CENTER + r * Math.cos(rad),
    y: MAP_CENTER + r * Math.sin(rad),
  };
}

function canvasToLatLon(x, y) {
  const dx = x - MAP_CENTER;
  const dy = y - MAP_CENTER;
  const r = Math.min(MAP_RADIUS, Math.sqrt(dx * dx + dy * dy));
  const lat = -90.0 + (r / MAP_RADIUS) * 10.0;
  let deg = (Math.atan2(dy, dx) * 180.0) / Math.PI + 90.0;
  if (deg < 0) deg += 360.0;
  if (deg >= 360.0) deg -= 360.0;
  return { lat, lon: deg };
}

function drawLunarMap() {
  if (!mapCtx) return;

  const width = lunarMapCanvas.width;
  const height = lunarMapCanvas.height;
  mapCtx.clearRect(0, 0, width, height);

  // 1. Draw Polar Background Disc with selected overlay tint
  const overlay = mapLayerSelect ? mapLayerSelect.value : "lola_elevation";
  const grad = mapCtx.createRadialGradient(MAP_CENTER, MAP_CENTER, 10, MAP_CENTER, MAP_CENTER, MAP_RADIUS);

  if (overlay === "lola_slope") {
    grad.addColorStop(0, "#2d004b");
    grad.addColorStop(0.5, "#7b1fa2");
    grad.addColorStop(0.8, "#d81b60");
    grad.addColorStop(1, "#f4511e");
  } else if (overlay === "solar_illumination") {
    grad.addColorStop(0, "#0a0a1a");
    grad.addColorStop(0.4, "#1e3a8a");
    grad.addColorStop(0.7, "#ca8a04");
    grad.addColorStop(1, "#fef08a");
  } else {
    // Elevation (Viridis-like)
    grad.addColorStop(0, "#440154");
    grad.addColorStop(0.3, "#3b528b");
    grad.addColorStop(0.6, "#21918c");
    grad.addColorStop(0.85, "#5ec962");
    grad.addColorStop(1, "#fde725");
  }

  mapCtx.fillStyle = grad;
  mapCtx.beginPath();
  mapCtx.arc(MAP_CENTER, MAP_CENTER, MAP_RADIUS, 0, Math.PI * 2);
  mapCtx.fill();

  // 2. Draw Concentric Latitude Rings (-88°, -86°, -84°, -82°, -80°)
  const ringLats = [-88, -86, -84, -82, -80];
  ringLats.forEach((ringLat) => {
    const r = ((ringLat - (-90.0)) / 10.0) * MAP_RADIUS;
    mapCtx.strokeStyle = ringLat === -80 ? "rgba(56, 189, 248, 0.6)" : "rgba(255, 255, 255, 0.15)";
    mapCtx.lineWidth = ringLat === -80 ? 2 : 1;
    mapCtx.beginPath();
    mapCtx.arc(MAP_CENTER, MAP_CENTER, r, 0, Math.PI * 2);
    mapCtx.stroke();

    // Label
    mapCtx.fillStyle = "rgba(255, 255, 255, 0.4)";
    mapCtx.font = "9px monospace";
    mapCtx.fillText(`${ringLat}°S`, MAP_CENTER + 4, MAP_CENTER - r + 11);
  });

  // 3. Draw Radial Azimuth Lines (every 45°)
  const radials = [
    { deg: 0, label: "0° (Earth / Nearside)" },
    { deg: 90, label: "90°E" },
    { deg: 180, label: "180° (Farside)" },
    { deg: 270, label: "270°W" },
  ];
  radials.forEach((rad) => {
    const angle = ((rad.deg - 90.0) * Math.PI) / 180.0;
    const x2 = MAP_CENTER + MAP_RADIUS * Math.cos(angle);
    const y2 = MAP_CENTER + MAP_RADIUS * Math.sin(angle);
    mapCtx.strokeStyle = "rgba(255, 255, 255, 0.18)";
    mapCtx.setLineDash([3, 3]);
    mapCtx.beginPath();
    mapCtx.moveTo(MAP_CENTER, MAP_CENTER);
    mapCtx.lineTo(x2, y2);
    mapCtx.stroke();
    mapCtx.setLineDash([]);
  });

  // 4. Draw Center South Pole Pin (-90°S)
  mapCtx.fillStyle = "#fff";
  mapCtx.beginPath();
  mapCtx.arc(MAP_CENTER, MAP_CENTER, 3, 0, Math.PI * 2);
  mapCtx.fill();
  mapCtx.fillStyle = "#38bdf8";
  mapCtx.font = "10px sans-serif";
  mapCtx.fillText("90°S", MAP_CENTER + 6, MAP_CENTER + 4);

  // 5. Draw Candidate Sites Markers
  candidateSites.forEach((site) => {
    const pt = latLonToCanvas(site.latitude, site.longitude);
    // Outer yellow halo
    mapCtx.strokeStyle = "rgba(245, 158, 11, 0.85)";
    mapCtx.lineWidth = 1.5;
    mapCtx.beginPath();
    mapCtx.arc(pt.x, pt.y, 5, 0, Math.PI * 2);
    mapCtx.stroke();
    // Inner dot
    mapCtx.fillStyle = "#f59e0b";
    mapCtx.beginPath();
    mapCtx.arc(pt.x, pt.y, 2.5, 0, Math.PI * 2);
    mapCtx.fill();
  });

  // 6. Draw Currently Active Coordinate Target
  const curLat = parseFloat(latInput.value);
  const curLon = parseFloat(lonInput.value);
  if (!isNaN(curLat) && !isNaN(curLon) && curLat <= -80.0 && curLat >= -90.0) {
    const activePt = latLonToCanvas(curLat, curLon);
    // Neon Cyan Crosshair
    mapCtx.strokeStyle = "#38bdf8";
    mapCtx.lineWidth = 2;
    mapCtx.beginPath();
    mapCtx.arc(activePt.x, activePt.y, 8, 0, Math.PI * 2);
    mapCtx.stroke();

    // Cross arms
    mapCtx.beginPath();
    mapCtx.moveTo(activePt.x - 12, activePt.y);
    mapCtx.lineTo(activePt.x + 12, activePt.y);
    mapCtx.moveTo(activePt.x, activePt.y - 12);
    mapCtx.lineTo(activePt.x, activePt.y + 12);
    mapCtx.stroke();
  }
}

// Map Click-to-Pick Coordinates
if (lunarMapCanvas) {
  lunarMapCanvas.addEventListener("click", (e) => {
    const rect = lunarMapCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const { lat, lon } = canvasToLatLon(x, y);

    latInput.value = lat.toFixed(4);
    lonInput.value = lon.toFixed(4);

    drawLunarMap();
    triggerCoverageCheck(lat, lon);
  });

  lunarMapCanvas.addEventListener("mousemove", (e) => {
    const rect = lunarMapCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Check if hovering near a candidate site
    let hoveredSite = null;
    for (const site of candidateSites) {
      const pt = latLonToCanvas(site.latitude, site.longitude);
      const dist = Math.sqrt((pt.x - x) ** 2 + (pt.y - y) ** 2);
      if (dist < 8) {
        hoveredSite = site;
        break;
      }
    }

    if (hoveredSite && mapTooltip) {
      mapTooltip.style.display = "block";
      mapTooltip.style.left = `${x + 10}px`;
      mapTooltip.style.top = `${y - 10}px`;
      mapTooltip.innerHTML = `<b>${hoveredSite.name}</b><br>Lat: ${hoveredSite.latitude.toFixed(2)}°, Lon: ${hoveredSite.longitude.toFixed(2)}°`;
    } else if (mapTooltip) {
      mapTooltip.style.display = "none";
    }
  });

  lunarMapCanvas.addEventListener("mouseleave", () => {
    if (mapTooltip) mapTooltip.style.display = "none";
  });
}

if (mapLayerSelect) {
  mapLayerSelect.addEventListener("change", drawLunarMap);
}

// ---------------------------------------------------------------------------
// 3. Real-Time Dataset Coverage & Coordinate Validation
// ---------------------------------------------------------------------------

function triggerCoverageCheck(lat, lon) {
  clearTimeout(coverageDebounceTimer);
  coverageDebounceTimer = setTimeout(() => checkSpatialCoverage(lat, lon), 250);
}

async function checkSpatialCoverage(lat, lon) {
  if (isNaN(lat) || isNaN(lon)) return;
  try {
    const res = await fetch(`${API_BASE}/coverage?lat=${lat}&lon=${lon}`);
    if (!res.ok) {
      coverageText.textContent = "Outside Polar Coverage Area (-90° to -80°)";
      coverageBadge.style.borderColor = "var(--accent-red)";
      return;
    }
    const data = await res.json();
    if (!data.in_south_pole_zone) {
      coverageText.textContent = "Coordinate outside lunar South Pole (-90° to -80°)";
      coverageBadge.style.borderColor = "var(--accent-red)";
      return;
    }

    const available = data.available_layers.filter((l) => l.is_installed);
    if (available.length > 0) {
      const names = available.map((l) => `${l.name} (${l.resolution_m}m)`).join(" + ");
      coverageText.textContent = names;
      coverageBadge.style.borderColor = "var(--accent-green)";
    } else {
      coverageText.textContent = "Synthetic / Nodata Area";
      coverageBadge.style.borderColor = "var(--accent-gold)";
    }
  } catch (err) {
    coverageText.textContent = "Coverage check offline";
  }
}

// ---------------------------------------------------------------------------
// 4. Pre-configured Demo Scenarios
// ---------------------------------------------------------------------------

function setupDemoScenarios() {
  if (btnScenario1) {
    btnScenario1.addEventListener("click", () => {
      latInput.value = "-89.44";
      lonInput.value = "222.50";
      radiusInput.value = "1000";
      missionProfileSelect.value = "artemis_hls";
      siteSelect.value = "shackleton_connecting_ridge";
      drawLunarMap();
      triggerCoverageCheck(-89.44, 222.50);
      btnRunAnalysis.click();
    });
  }

  if (btnScenario2) {
    btnScenario2.addEventListener("click", () => {
      // Steep Faustini / crater wall with slopes > 20°
      latInput.value = "-89.75";
      lonInput.value = "120.00";
      radiusInput.value = "1000";
      missionProfileSelect.value = "artemis_hls";
      siteSelect.value = "";
      drawLunarMap();
      triggerCoverageCheck(-89.75, 120.00);
      btnRunAnalysis.click();
    });
  }

  if (btnScenario3) {
    btnScenario3.addEventListener("click", () => {
      // Out of polar coverage (-78.50°)
      latInput.value = "-78.50";
      lonInput.value = "45.00";
      radiusInput.value = "1000";
      siteSelect.value = "";
      drawLunarMap();
      triggerCoverageCheck(-78.50, 45.00);
      btnRunAnalysis.click();
    });
  }
}

// ---------------------------------------------------------------------------
// 5. Site Selection & Coordinate Inputs
// ---------------------------------------------------------------------------

siteSelect.addEventListener("change", (e) => {
  const selectedId = e.target.value;
  const site = candidateSites.find((s) => s.site_id === selectedId);
  if (site) {
    latInput.value = site.latitude.toFixed(4);
    lonInput.value = site.longitude.toFixed(4);
    drawLunarMap();
    triggerCoverageCheck(site.latitude, site.longitude);
  }
});

latInput.addEventListener("input", () => {
  drawLunarMap();
  triggerCoverageCheck(parseFloat(latInput.value), parseFloat(lonInput.value));
});

lonInput.addEventListener("input", () => {
  drawLunarMap();
  triggerCoverageCheck(parseFloat(latInput.value), parseFloat(lonInput.value));
});

// ---------------------------------------------------------------------------
// 6. Point Terrain Sampling (GET /api/terrain)
// ---------------------------------------------------------------------------

btnSamplePoint.addEventListener("click", async () => {
  const lat = parseFloat(latInput.value);
  const lon = parseFloat(lonInput.value);

  btnSamplePoint.textContent = "Sampling...";
  try {
    const res = await fetch(`${API_BASE}/terrain?lat=${lat}&lon=${lon}`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Point query failed");
    }
    const data = await res.json();
    const elevStr = data.elevation_m !== null ? `${data.elevation_m.toFixed(1)} m` : "N/A (Nodata/Shadow)";
    const slopeStr = data.slope_deg !== null ? `${data.slope_deg.toFixed(2)}°` : "N/A";
    const roughStr = data.roughness_m !== null ? `${data.roughness_m.toFixed(2)} m` : "N/A";
    const feasibleStr = (data.landing_hazard_classification === "safe" || data.landing_hazard_classification === "nominal") ? "YES" : "NO (Marginal/Hazardous/Nodata)";
    alert(
      `Point Elevation: ${elevStr}\n` +
      `Local Slope: ${slopeStr}\n` +
      `RMS Roughness: ${roughStr}\n` +
      `Classification: ${data.landing_hazard_classification ? data.landing_hazard_classification.toUpperCase() : "NODATA"}\n` +
      `Safe Touchdown Feasible: ${feasibleStr}`
    );
  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    btnSamplePoint.textContent = "Sample Point";
  }
});

// ---------------------------------------------------------------------------
// 7. Full Landing Zone Spatial Analysis (POST /api/analysis/run)
// ---------------------------------------------------------------------------

btnRunAnalysis.addEventListener("click", async () => {
  const lat = parseFloat(latInput.value);
  const lon = parseFloat(lonInput.value);
  const radius = parseFloat(radiusInput.value);
  const profile = missionProfileSelect.value || "artemis_hls";

  btnRunAnalysis.innerHTML = '<span class="loading-spinner"></span> Processing...';
  btnRunAnalysis.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/analysis/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        center_lat: lat,
        center_lon: lon,
        radius_meters: radius,
        max_acceptable_slope_deg: 10.0,
        max_acceptable_roughness_m: 0.5,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Analysis failed");
    }

    currentAnalysis = await res.json();
    displayAnalysisResults(currentAnalysis);

    // Concurrently trigger hazard detection
    runHazardPrediction(lat, lon, radius);

  } catch (err) {
    alert(`Analysis Failed: ${err.message}`);
  } finally {
    btnRunAnalysis.innerHTML = "Run Full Analysis";
    btnRunAnalysis.disabled = false;
  }
});

function displayAnalysisResults(data) {
  welcomeCard.style.display = "none";
  analysisCard.style.display = "block";
  suitabilityCard.style.display = "block";
  aiCard.style.display = "block";
  reportCard.style.display = "block";

  document.getElementById("analysisIdBadge").textContent = data.analysis_id;
  document.getElementById("analysisTitle").textContent = `Landing Zone: ${data.center_lat.toFixed(2)}°, ${data.center_lon.toFixed(2)}°`;

  // Elevation
  const meanElev = data.elevation.mean_value !== null ? `${data.elevation.mean_value.toFixed(1)} m` : "N/A";
  const relief = data.elevation.variation !== null ? `Relief: ${data.elevation.variation.toFixed(1)} m (±${data.elevation.std_dev.toFixed(1)}m)` : "Relief: N/A";
  document.getElementById("valElevation").textContent = meanElev;
  document.getElementById("subElevationRelief").textContent = relief;

  // Slope
  const meanSlope = data.slope.mean_value !== null ? `${data.slope.mean_value.toFixed(2)}°` : "MISSING";
  const peakSlope = data.slope.max_value !== null ? `Peak: ${data.slope.max_value.toFixed(2)}°` : "Peak: N/A";
  document.getElementById("valSlope").textContent = meanSlope;
  document.getElementById("subSlopeMax").textContent = peakSlope;

  // Roughness
  const roughness = data.roughness_mean_m !== null && data.roughness_mean_m !== undefined ? `${data.roughness_mean_m.toFixed(2)} m` : "N/A";
  document.getElementById("valRoughness").textContent = roughness;
  const baseLabel = data.roughness_baseline_m ? `${data.roughness_baseline_m.toFixed(0)}m baseline` : "15m baseline";
  const subRoughEl = document.getElementById("subRoughnessBaseline");
  if (subRoughEl) subRoughEl.textContent = baseLabel;

  document.getElementById("valSafeFraction").textContent = `${data.safe_touchdown_fraction_pct.toFixed(1)}%`;
  document.getElementById("subFeasibility").textContent = `Feasibility: ${data.preliminary_feasibility.toUpperCase()}`;

  // Slope Distribution Bar
  const dist = data.slope_distribution;
  document.getElementById("barIdeal").style.width = `${dist.ideal_pct}%`;
  document.getElementById("barAccept").style.width = `${dist.acceptable_pct}%`;
  document.getElementById("barMarginal").style.width = `${dist.marginal_pct}%`;
  document.getElementById("barCritical").style.width = `${dist.critical_hazardous_pct}%`;

  document.getElementById("lblIdeal").textContent = `${dist.ideal_pct.toFixed(1)}%`;
  document.getElementById("lblAccept").textContent = `${dist.acceptable_pct.toFixed(1)}%`;
  document.getElementById("lblMarginal").textContent = `${dist.marginal_pct.toFixed(1)}%`;
  document.getElementById("lblCritical").textContent = `${dist.critical_hazardous_pct.toFixed(1)}%`;

  // Instrument Uncertainty & Attribution Box
  const vertUncEl = document.getElementById("valVertUncertainty");
  if (vertUncEl) vertUncEl.textContent = "±1.5 m (LOLA 1-Sigma)";
  const slopeUncEl = document.getElementById("valSlopeUncertainty");
  if (slopeUncEl) slopeUncEl.textContent = "±1.2° (Laser Track Divergence)";
  const metaEl = document.getElementById("valDatasetAttribution");
  if (metaEl && data.dataset_metadata) {
    metaEl.textContent = `${data.dataset_metadata.dataset_name || "NASA LOLA DEM"} (${data.dataset_metadata.spatial_resolution_m || "20"}m/px)`;
  }

  // Illumination
  if (data.illumination && data.illumination.status === "available") {
    document.getElementById("valCumIllum").textContent = `${data.illumination.cumulative_illumination_pct.toFixed(1)}%`;
    document.getElementById("valInstIllum").textContent = `${data.illumination.instantaneous_sunlit_fraction_pct.toFixed(1)}%`;
    document.getElementById("subPsr").textContent = `PSR: ${data.illumination.is_permanently_shadowed_region ? "YES (Cold Trap)" : "NO"}`;
    document.getElementById("valTemp").textContent = `${data.illumination.estimated_surface_temp_k.toFixed(1)} K`;
  }

  // Suitability
  if (data.suitability) {
    const suit = data.suitability;
    document.getElementById("valSuitabilityScore").textContent = suit.overall_suitability_score !== null ? `${suit.overall_suitability_score.toFixed(1)}/100` : "INSUFFICIENT";
    document.getElementById("valSuitabilityCategory").textContent = suit.suitability_category;
    document.getElementById("valScoreCoverage").textContent = `Coverage: ${suit.score_coverage_pct.toFixed(1)}% of criteria`;

    // ML Surrogate & Gating enrichments
    const valMlEl = document.getElementById("valMlScore");
    if (valMlEl) {
      valMlEl.textContent = suit.ml_model_score !== null && suit.ml_model_score !== undefined ? `${suit.ml_model_score.toFixed(1)}/100` : "N/A";
    }
    const valMlMetaEl = document.getElementById("valMlModelVersion");
    if (valMlMetaEl) {
      valMlMetaEl.textContent = suit.model_version || "RF Surrogate";
    }
    const valGateEl = document.getElementById("valHardConstraintStatus");
    if (valGateEl && suit.hard_constraint_status) {
      const isViolated = suit.hard_constraint_status === "violated";
      valGateEl.textContent = isViolated ? "VIOLATED" : "PASSED";
      valGateEl.style.color = isViolated ? "var(--accent-red, #ff5555)" : "var(--accent-green, #50fa7b)";
    }
    const valProfEl = document.getElementById("valMissionProfile");
    if (valProfEl) {
      valProfEl.textContent = (suit.mission_profile || "Artemis HLS").toUpperCase();
    }
    const valConfEl = document.getElementById("valConfidenceInterval");
    if (valConfEl && suit.confidence_interval_95 && suit.confidence_interval_95.length === 2) {
      valConfEl.textContent = `[${suit.confidence_interval_95[0].toFixed(1)}, ${suit.confidence_interval_95[1].toFixed(1)}]`;
    }
    const valUncEl = document.getElementById("valScoreUncertainty");
    if (valUncEl) {
      valUncEl.textContent = suit.uncertainty_score_std !== null && suit.uncertainty_score_std !== undefined ? `±${suit.uncertainty_score_std.toFixed(2)} pts` : "";
    }

    // Populate subscores table
    const tbody = document.getElementById("subscoreTableBody");
    tbody.innerHTML = "";
    suit.subscores.forEach((sub) => {
      const tr = document.createElement("tr");
      const rawStr = sub.raw_measurement !== null ? `${sub.raw_measurement.toFixed(2)} ${sub.unit}` : "N/A";
      const normStr = sub.normalized_subscore !== null ? `${sub.normalized_subscore.toFixed(1)}/100` : "N/A";
      const contStr = sub.weighted_contribution !== null ? sub.weighted_contribution.toFixed(2) : "N/A";
      tr.innerHTML = `
        <td><b>${sub.criterion}</b></td>
        <td>${rawStr}</td>
        <td>${normStr}</td>
        <td>${sub.weight.toFixed(2)}</td>
        <td>${contStr}</td>
        <td><span style="color: ${sub.status === 'available' ? 'var(--accent-green)' : 'var(--accent-gold)'};">${sub.status}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Reset AI card state
  aiContent.style.display = "none";
}

// ---------------------------------------------------------------------------
// 8. Touchdown Hazard Detection (POST /api/hazards/predict)
// ---------------------------------------------------------------------------

async function runHazardPrediction(lat, lon, radius) {
  try {
    const res = await fetch(`${API_BASE}/hazards/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        center_lat: lat,
        center_lon: lon,
        radius_meters: radius,
      }),
    });
    if (!res.ok) return;
    const data = await res.json();
    hazardsCard.style.display = "block";

    document.getElementById("valHazardStatus").textContent = data.status.toUpperCase();
    document.getElementById("valCraterCount").textContent = data.crater_count !== null ? data.crater_count : "--";
    document.getElementById("valRockCount").textContent = data.rock_count !== null ? data.rock_count : "--";
    document.getElementById("hazardNotice").textContent = data.limitations || "";
  } catch (err) {
    console.warn("Hazard query fallback:", err);
  }
}

// ---------------------------------------------------------------------------
// 9. Automated Contiguous Landing Zone Detection (POST /api/sites/detect)
// ---------------------------------------------------------------------------

if (btnDetectSites) {
  btnDetectSites.addEventListener("click", async () => {
    const lat = parseFloat(latInput.value);
    const lon = parseFloat(lonInput.value);
    const radius = parseFloat(radiusInput.value);
    const profile = missionProfileSelect.value || "artemis_hls";

    btnDetectSites.textContent = "Detecting...";
    btnDetectSites.disabled = true;

    try {
      const res = await fetch(`${API_BASE}/sites/detect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          center_lat: lat,
          center_lon: lon,
          search_radius_meters: radius,
          max_slope_deg: 8.0,
          max_roughness_m: 0.35,
          min_landing_diameter_meters: 40.0,
          mission_profile: profile,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Detection failed");
      }

      const data = await res.json();
      welcomeCard.style.display = "none";
      detectionCard.style.display = "block";
      document.getElementById("detectionSummary").textContent = data.summary;

      const detectionTableBody = document.getElementById("detectionTableBody");
      detectionTableBody.innerHTML = "";
      if (data.candidate_zones.length === 0) {
        detectionTableBody.innerHTML = '<tr><td colspan="11" style="text-align: center; color: var(--accent-gold);">No contiguous zones met footprint diameter and slope limits in this search area.</td></tr>';
      } else {
        data.candidate_zones.forEach((zone) => {
          const tr = document.createElement("tr");
          const isPassed = zone.hard_constraint_status === "passed";
          tr.innerHTML = `
            <td><b>#${zone.safety_rank}</b></td>
            <td><code>${zone.zone_id}</code></td>
            <td>${zone.centroid_lat.toFixed(4)}°, ${zone.centroid_lon.toFixed(4)}°</td>
            <td>${(zone.contiguous_area_m2 / 1000).toFixed(1)}k m²</td>
            <td>${zone.effective_diameter_m.toFixed(1)} m</td>
            <td>${zone.mean_slope_deg.toFixed(2)}°</td>
            <td>${zone.mean_roughness_m.toFixed(2)} m</td>
            <td><b>${zone.suitability_score.toFixed(1)}</b></td>
            <td>${zone.ml_model_score !== null && zone.ml_model_score !== undefined ? `${zone.ml_model_score.toFixed(1)}` : "N/A"}</td>
            <td><span style="color: ${isPassed ? 'var(--accent-green)' : 'var(--accent-red)'}; font-weight: 600;">${isPassed ? 'PASS' : 'VIOLATION'}</span></td>
            <td><span style="color: ${zone.feasibility_status === 'optimal' ? 'var(--accent-green)' : 'var(--accent-cyan)'};">${zone.feasibility_status.toUpperCase()}</span></td>
          `;
          detectionTableBody.appendChild(tr);
        });
      }
    } catch (err) {
      alert(`Detection error: ${err.message}`);
    } finally {
      btnDetectSites.textContent = "Detect Zones";
      btnDetectSites.disabled = false;
    }
  });
}

// ---------------------------------------------------------------------------
// 10. Temporal Sun & Earth Visibility Simulation & Time-Series Chart
// ---------------------------------------------------------------------------

if (btnSimulateVisibility) {
  btnSimulateVisibility.addEventListener("click", async () => {
    const lat = parseFloat(latInput.value);
    const lon = parseFloat(lonInput.value);
    const startEpoch = epochInput.value ? `${epochInput.value}:00Z` : "2026-07-01T00:00:00Z";
    const durationDays = parseFloat(durationInput.value) || 14.0;
    const stepHours = parseFloat(stepSelect.value) || 2.0;

    btnSimulateVisibility.textContent = "Simulating...";
    btnSimulateVisibility.disabled = true;

    try {
      const res = await fetch(`${API_BASE}/simulation/visibility`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lat: lat,
          lon: lon,
          start_epoch_iso: startEpoch,
          duration_days: durationDays,
          step_hours: stepHours,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Simulation failed");
      }

      currentSimulation = await res.json();
      welcomeCard.style.display = "none";
      simulationCard.style.display = "block";

      document.getElementById("valSimDaylight").textContent = `${currentSimulation.total_sunlight_hours.toFixed(1)} h`;
      document.getElementById("subSimDaylightPct").textContent = `${currentSimulation.sunlight_percentage.toFixed(1)}% of duration`;

      document.getElementById("valSimComm").textContent = `${currentSimulation.total_earth_comm_hours.toFixed(1)} h`;
      document.getElementById("subSimCommPct").textContent = `${currentSimulation.earth_comm_percentage.toFixed(1)}% of duration`;

      document.getElementById("valSimDark").textContent = `${currentSimulation.max_continuous_darkness_hours.toFixed(1)} h`;
      document.getElementById("valSimBlackout").textContent = `${currentSimulation.max_continuous_comm_blackout_hours.toFixed(1)} h`;

      document.getElementById("simCaveat").textContent = currentSimulation.scientific_methodology;

      // Render Time-Series Curves in SVG
      renderVisibilityTimeline(currentSimulation);

    } catch (err) {
      alert(`Simulation error: ${err.message}`);
    } finally {
      btnSimulateVisibility.textContent = "Simulate Orbit";
      btnSimulateVisibility.disabled = false;
    }
  });
}

function renderVisibilityTimeline(sim) {
  const svg = document.getElementById("visibilityTimelineSvg");
  if (!svg || !sim.time_series || sim.time_series.length === 0) return;

  const width = 800;
  const height = 160;
  const padLeft = 40;
  const padRight = 20;
  const padTop = 15;
  const padBottom = 25;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const steps = sim.time_series;
  const totalH = steps[steps.length - 1].elapsed_hours || (sim.duration_days * 24);

  // Elevation scale: -10 deg to +15 deg
  const minElev = -10.0;
  const maxElev = 15.0;

  function toY(deg) {
    const norm = (deg - minElev) / (maxElev - minElev);
    return padTop + chartH - (norm * chartH);
  }

  function toX(hours) {
    return padLeft + (hours / totalH) * chartW;
  }

  const yZero = toY(0.0);

  // Build SVG elements
  let svgContent = "";

  // 1. Background grid and zero line
  svgContent += `<rect x="${padLeft}" y="${padTop}" width="${chartW}" height="${chartH}" fill="#0f172a" />`;
  svgContent += `<line x1="${padLeft}" y1="${yZero}" x2="${padLeft + chartW}" y2="${yZero}" stroke="rgba(255,255,255,0.25)" stroke-dasharray="4,4" />`;
  svgContent += `<text x="${padLeft - 5}" y="${yZero + 3}" fill="#94a3b8" font-size="9" text-anchor="end">0° Horizon</text>`;
  svgContent += `<text x="${padLeft - 5}" y="${toY(10) + 3}" fill="#94a3b8" font-size="9" text-anchor="end">+10°</text>`;
  svgContent += `<text x="${padLeft - 5}" y="${toY(-5) + 3}" fill="#94a3b8" font-size="9" text-anchor="end">-5°</text>`;

  // 2. Combined Ops and Sunlit shading bars across bottom
  const stepW = chartW / steps.length;
  steps.forEach((st) => {
    const x = toX(st.elapsed_hours);
    if (st.is_sunlit && st.is_earth_visible) {
      // Combined ops green bar
      svgContent += `<rect x="${x}" y="${padTop + chartH - 6}" width="${stepW + 1}" height="6" fill="#10b981" />`;
    } else if (st.is_sunlit) {
      // Sunlit gold bar
      svgContent += `<rect x="${x}" y="${padTop + chartH - 4}" width="${stepW + 1}" height="4" fill="rgba(245, 158, 11, 0.4)" />`;
    } else if (!st.is_earth_visible) {
      // Blackout red bar
      svgContent += `<rect x="${x}" y="${padTop + chartH - 2}" width="${stepW + 1}" height="2" fill="rgba(239, 68, 68, 0.5)" />`;
    }
  });

  // 3. Solar Elevation Path (Gold Curve)
  let sunPath = "";
  steps.forEach((st, idx) => {
    const x = toX(st.elapsed_hours);
    const y = toY(st.solar_elevation_deg);
    sunPath += `${idx === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)} `;
  });
  svgContent += `<path d="${sunPath}" fill="none" stroke="#f59e0b" stroke-width="2" />`;

  // 4. Earth Elevation Path (Cyan Curve)
  let earthPath = "";
  steps.forEach((st, idx) => {
    const x = toX(st.elapsed_hours);
    const y = toY(st.earth_elevation_deg);
    earthPath += `${idx === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)} `;
  });
  svgContent += `<path d="${earthPath}" fill="none" stroke="#38bdf8" stroke-width="1.8" />`;

  // 5. Time axis labels
  const timeIntervalH = totalH > 168 ? 48 : 24;
  for (let h = 0; h <= totalH; h += timeIntervalH) {
    const x = toX(h);
    svgContent += `<line x1="${x}" y1="${padTop + chartH}" x2="${x}" y2="${padTop + chartH + 4}" stroke="#64748b" />`;
    svgContent += `<text x="${x}" y="${padTop + chartH + 16}" fill="#94a3b8" font-size="9" text-anchor="middle">${h}h</text>`;
  }

  svg.innerHTML = svgContent;
}

// ---------------------------------------------------------------------------
// 11. Multi-Candidate Site Comparison (POST /api/sites/compare)
// ---------------------------------------------------------------------------

btnCompareSites.addEventListener("click", async () => {
  btnCompareSites.textContent = "Comparing...";
  const profile = missionProfileSelect.value || "artemis_hls";

  try {
    const siteIds = candidateSites.slice(0, 4).map((s) => s.site_id);
    if (siteIds.length < 2) {
      alert("At least 2 candidate sites needed for comparison.");
      return;
    }
    const res = await fetch(`${API_BASE}/sites/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        site_ids: siteIds,
        mission_profile: profile,
      }),
    });
    if (!res.ok) throw new Error("Comparison failed");
    const data = await res.json();

    let html = `<p style="color: var(--accent-cyan); font-weight: 600; margin-bottom: 6px;">Top Recommended (${profile.toUpperCase()}): ${data.top_recommended_site_id.replace(/_/g, ' ').toUpperCase()}</p>`;
    html += '<ul style="padding-left: 16px; margin-bottom: 8px;">';
    data.compared_sites.forEach((site) => {
      const isPassed = site.hard_constraint_status === "passed";
      const mlStr = site.ml_model_score !== null && site.ml_model_score !== undefined ? ` | ML: <b>${site.ml_model_score.toFixed(1)}</b>` : "";
      const statusBadge = isPassed ? `<span style="color: var(--accent-green); font-size: 11px;">[PASS]</span>` : `<span style="color: var(--accent-red); font-size: 11px;">[VIOLATION]</span>`;
      html += `<li><b>Rank #${site.safety_rank}:</b> ${site.name} — Score: <b>${site.suitability_score.toFixed(1)}/100</b>${mlStr} ${statusBadge}</li>`;
    });
    html += `</ul><p style="font-size: 11px; color: var(--text-muted);">${data.tradeoff_summary}</p>`;
    compareResults.innerHTML = html;
  } catch (err) {
    compareResults.innerHTML = `<span style="color: var(--accent-red);">${err.message}</span>`;
  } finally {
    btnCompareSites.textContent = "Compare Top Artemis Sites";
  }
});

// ---------------------------------------------------------------------------
// 12. Interactive Grounded AI Scientific Assistant (POST /api/ai/explain)
// ---------------------------------------------------------------------------

async function requestAiExplanation(userQuery = "") {
  if (!currentAnalysis) return;

  btnRequestAi.disabled = true;
  if (btnSubmitAiQuery) btnSubmitAiQuery.disabled = true;
  aiLoading.style.display = "block";
  aiContent.style.display = "none";

  try {
    const res = await fetch(`${API_BASE}/ai/explain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysis_id: currentAnalysis.analysis_id,
        user_query: userQuery || undefined,
        focus_topics: ["topography", "solar_illumination", "slope", "roughness"],
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "AI explanation failed");
    }

    const data = await res.json();
    document.getElementById("aiExplanation").textContent = data.explanation;

    const posList = document.getElementById("aiPositiveFactors");
    posList.innerHTML = "";
    data.positive_factors.forEach((pf) => {
      const li = document.createElement("li");
      li.textContent = pf;
      posList.appendChild(li);
    });

    const riskList = document.getElementById("aiRiskFactors");
    riskList.innerHTML = "";
    data.risk_factors.forEach((rf) => {
      const li = document.createElement("li");
      li.textContent = rf;
      riskList.appendChild(li);
    });

    document.getElementById("aiConclusion").textContent = `"${data.conclusion}"`;
    aiContent.style.display = "block";

  } catch (err) {
    alert(`AI Explanation Failed: ${err.message}`);
  } finally {
    btnRequestAi.disabled = false;
    if (btnSubmitAiQuery) btnSubmitAiQuery.disabled = false;
    aiLoading.style.display = "none";
  }
}

if (btnRequestAi) {
  btnRequestAi.addEventListener("click", () => requestAiExplanation());
}

if (btnSubmitAiQuery && aiCustomPrompt) {
  btnSubmitAiQuery.addEventListener("click", () => {
    const query = aiCustomPrompt.value.trim();
    requestAiExplanation(query);
  });

  aiCustomPrompt.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      btnSubmitAiQuery.click();
    }
  });
}

// Preset question pills
const presetPills = document.querySelectorAll(".preset-pill");
presetPills.forEach((pill) => {
  pill.addEventListener("click", () => {
    const query = pill.getAttribute("data-query");
    if (aiCustomPrompt) aiCustomPrompt.value = query;
    requestAiExplanation(query);
  });
});

// ---------------------------------------------------------------------------
// 13. Scientific Report Generation (PDF & JSON)
// ---------------------------------------------------------------------------

btnDownloadPdf.addEventListener("click", async () => {
  if (!currentAnalysis) return;

  btnDownloadPdf.innerHTML = '<span class="loading-spinner"></span> Generating PDF...';
  btnDownloadPdf.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/reports/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/pdf",
      },
      body: JSON.stringify({
        analysis_id: currentAnalysis.analysis_id,
        format: "pdf",
      }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status} PDF generation failed`);

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `moonscape_report_${currentAnalysis.analysis_id}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();

  } catch (err) {
    alert(`PDF Download Error: ${err.message}`);
  } finally {
    btnDownloadPdf.innerHTML = "📄 Download Scientific PDF Report";
    btnDownloadPdf.disabled = false;
  }
});

btnViewJsonReport.addEventListener("click", async () => {
  if (!currentAnalysis) return;

  try {
    const res = await fetch(`${API_BASE}/reports/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysis_id: currentAnalysis.analysis_id,
        format: "json",
      }),
    });

    if (!res.ok) throw new Error("JSON report failed");
    const data = await res.json();

    const win = window.open("", "_blank");
    win.document.write(`<pre style="font-family: monospace; font-size: 13px; line-height: 1.5; padding: 20px; background: #0f172a; color: #f8fafc;">${JSON.stringify(data, null, 2)}</pre>`);
  } catch (err) {
    alert(`Report error: ${err.message}`);
  }
});

// ---------------------------------------------------------------------------
// 14. Application Initialization
// ---------------------------------------------------------------------------

checkBackendHealth();
loadCandidateSites();
loadMapConfig();
setupDemoScenarios();
checkSpatialCoverage(parseFloat(latInput.value), parseFloat(lonInput.value));
