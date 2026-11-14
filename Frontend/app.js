/**
 * Moonscape Frontend Application Logic
 * Integrates directly with FastAPI backend at http://localhost:8000/api
 */

const API_BASE = "http://localhost:8000/api";

let candidateSites = [];
let currentAnalysis = null;

// DOM Elements
const healthBadge = document.getElementById("healthBadge");
const statusDot = document.getElementById("statusDot");
const healthText = document.getElementById("healthText");
const siteSelect = document.getElementById("siteSelect");
const latInput = document.getElementById("latInput");
const lonInput = document.getElementById("lonInput");
const radiusInput = document.getElementById("radiusInput");
const btnSamplePoint = document.getElementById("btnSamplePoint");
const btnRunAnalysis = document.getElementById("btnRunAnalysis");
const btnCompareSites = document.getElementById("btnCompareSites");
const compareResults = document.getElementById("compareResults");

const welcomeCard = document.getElementById("welcomeCard");
const analysisCard = document.getElementById("analysisCard");
const hazardsCard = document.getElementById("hazardsCard");
const suitabilityCard = document.getElementById("suitabilityCard");
const aiCard = document.getElementById("aiCard");
const reportCard = document.getElementById("reportCard");

const btnRequestAi = document.getElementById("btnRequestAi");
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
  } catch (err) {
    console.error("Failed to load candidate sites:", err);
  }
}

// ---------------------------------------------------------------------------
// 2. Site Selection Event
// ---------------------------------------------------------------------------

siteSelect.addEventListener("change", (e) => {
  const selectedId = e.target.value;
  const site = candidateSites.find((s) => s.site_id === selectedId);
  if (site) {
    latInput.value = site.latitude.toFixed(4);
    lonInput.value = site.longitude.toFixed(4);
  }
});

// ---------------------------------------------------------------------------
// 3. Point Terrain Sampling (GET /api/terrain)
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
    alert(
      `Point Elevation: ${data.elevation_m.toFixed(1)} m\n` +
      `Local Slope: ${data.mean_slope_deg.toFixed(2)}°\n` +
      `RMS Roughness: ${data.roughness_m.toFixed(2)} m\n` +
      `Safe Touchdown Feasible: ${data.safe_touchdown_feasible ? "YES" : "NO"}`
    );
  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    btnSamplePoint.textContent = "Sample Point";
  }
});

// ---------------------------------------------------------------------------
// 4. Full Landing Zone Spatial Analysis (POST /api/analysis/run)
// ---------------------------------------------------------------------------

btnRunAnalysis.addEventListener("click", async () => {
  const lat = parseFloat(latInput.value);
  const lon = parseFloat(lonInput.value);
  const radius = parseFloat(radiusInput.value);

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
  document.getElementById("valElevation").textContent = `${data.elevation.mean_value.toFixed(1)} m`;
  document.getElementById("subElevationRelief").textContent = `Relief: ${data.elevation.variation.toFixed(1)} m (±${data.elevation.std_dev.toFixed(1)}m)`;

  // Slope
  document.getElementById("valSlope").textContent = `${data.slope.mean_value.toFixed(2)}°`;
  document.getElementById("subSlopeMax").textContent = `Peak: ${data.slope.max_value.toFixed(2)}°`;

  // Roughness
  document.getElementById("valRoughness").textContent = `${(data.roughness_mean_m || 0).toFixed(2)} m`;
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
// 5. Hazard Detection (POST /api/hazards/predict)
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
// 6. Candidate Site Comparison (POST /api/sites/compare)
// ---------------------------------------------------------------------------

btnCompareSites.addEventListener("click", async () => {
  btnCompareSites.textContent = "Comparing...";
  try {
    const siteIds = candidateSites.slice(0, 4).map((s) => s.site_id);
    if (siteIds.length < 2) {
      alert("At least 2 candidate sites needed for comparison.");
      return;
    }
    const res = await fetch(`${API_BASE}/sites/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ site_ids: siteIds }),
    });
    if (!res.ok) throw new Error("Comparison failed");
    const data = await res.json();

    let html = `<p style="color: var(--accent-cyan); font-weight: 600; margin-bottom: 6px;">Top Recommended: ${data.top_recommended_site_id.replace(/_/g, ' ').toUpperCase()}</p>`;
    html += '<ul style="padding-left: 16px; margin-bottom: 8px;">';
    data.compared_sites.forEach((site) => {
      html += `<li><b>Rank #${site.safety_rank}:</b> ${site.name} — Score: <b>${site.suitability_score.toFixed(1)}/100</b></li>`;
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
// 7. AI Scientific Explainer (POST /api/ai/explain)
// ---------------------------------------------------------------------------

btnRequestAi.addEventListener("click", async () => {
  if (!currentAnalysis) return;

  btnRequestAi.disabled = true;
  aiLoading.style.display = "block";
  aiContent.style.display = "none";

  try {
    const res = await fetch(`${API_BASE}/ai/explain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysis_id: currentAnalysis.analysis_id,
        focus_topics: ["topography", "solar_illumination", "slope"],
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
    aiLoading.style.display = "none";
  }
});

// ---------------------------------------------------------------------------
// 8. Scientific Report Generation (POST /api/reports/generate)
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

    // Open formatted JSON in new browser tab
    const win = window.open("", "_blank");
    win.document.write(`<pre style="font-family: monospace; font-size: 13px; line-height: 1.5; padding: 20px; background: #0f172a; color: #f8fafc;">${JSON.stringify(data, null, 2)}</pre>`);
  } catch (err) {
    alert(`Report error: ${err.message}`);
  }
});

// Run initialization
checkBackendHealth();
loadCandidateSites();
