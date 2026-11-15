import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def fetch_raw(url, method="GET", data=None):
    req = urllib.request.Request(url, method=method)
    if data is not None:
        req.data = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "application/json" in content_type:
                return resp.status, json.loads(raw.decode("utf-8")), None
            return resp.status, raw, None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except:
            parsed = body
        return e.code, parsed, None
    except Exception as exc:
        return 0, None, str(exc)

def main():
    print("=== STAGE 4: COMPLETE OPENAPI AUDIT & ENDPOINT TESTING ===")
    
    # 1. Fetch OpenAPI spec
    code, spec, err = fetch_raw(f"{BASE_URL}/openapi.json")
    if code != 200:
        print(f"FAILED to fetch OpenAPI spec: {code} {err}")
        sys.exit(1)
        
    print(f"OpenAPI version: {spec.get('openapi')}")
    print(f"Application Title: {spec.get('info', {}).get('title')}")
    print(f"Application Version: {spec.get('info', {}).get('version')}")
    paths = spec.get("paths", {})
    print(f"Total Registered Endpoints: {len(paths)}\n")

    # First, run an analysis to obtain a live dynamic analysis_id for AI Explain test
    print("Running preliminary analysis to generate dynamic analysis_id...")
    anl_code, anl_resp, _ = fetch_raw(
        f"{BASE_URL}/api/analysis/run",
        method="POST",
        data={"center_lat": -89.44, "center_lon": 222.50, "radius_meters": 1500.0}
    )
    analysis_id = anl_resp.get("analysis_id", "ANL-SAMPLE") if anl_code == 200 else "ANL-SAMPLE"
    print(f"Dynamic Analysis ID: {analysis_id}\n")
    
    # Test matrix
    tests = [
        # (name, method, path, body, expected_status)
        ("Health Check", "GET", "/api/health", None, 200),
        ("Sites Catalog", "GET", "/api/sites", None, 200),
        ("Single Site (Shackleton)", "GET", "/api/sites/shackleton_connecting_ridge", None, 200),
        ("Single Site (Missing 404)", "GET", "/api/sites/nonexistent_999", None, 404),
        ("Map Config", "GET", "/api/map/config", None, 200),
        ("Point Terrain Valid", "GET", "/api/terrain?lat=-89.44&lon=222.50&radius_m=1000", None, 200),
        ("Data Catalog", "GET", "/api/data/catalog", None, 200),
        ("Data Status", "GET", "/api/data/status", None, 200),
        ("Data Coverage Check", "GET", "/api/coverage?lat=-89.44&lon=222.50", None, 200),
        ("Hazard Detection Status", "GET", "/api/hazards/status", None, 200),
        ("Download Tasks List", "GET", "/api/data/downloads", None, 200),
        ("External Sources Status", "GET", "/api/external/sources", None, 200),
        ("Moon Trek Layers", "GET", "/api/external/moon-trek/layers", None, 200),
        ("LROC Coverage Check", "GET", "/api/external/lroc/coverage?lat=-89.44&lon=222.50", None, 200),
        ("LROC Footprints Discovery", "GET", "/api/data/lroc/footprints?lat=-89.44&lon=222.50", None, 200),
        ("SPICE Ephemeris Metadata", "GET", "/api/ephemeris/spice/metadata", None, 200),
        ("Moon Trek Tile Proxy (Binary JPEG)", "GET", "/api/external/moon-trek/tile/trek_wac_global_mosaic/0/0/0", None, 200),
        ("Moon Trek Tile Missing 404", "GET", "/api/external/moon-trek/tile/nonexistent/0/0/0", None, 404),
        (
            "Spatial Analysis Run", "POST", "/api/analysis/run",
            {"center_lat": -89.44, "center_lon": 222.50, "radius_meters": 1500.0}, 200
        ),
        (
            "Spatial Analysis Out-of-bounds 422", "POST", "/api/analysis/run",
            {"center_lat": -50.0, "center_lon": 0.0, "radius_meters": 1500.0}, 422
        ),
        (
            "Hazard Prediction", "POST", "/api/hazards/predict",
            {"center_lat": -89.44, "center_lon": 222.50, "radius_meters": 1000.0}, 200
        ),
        (
            "Sites Compare", "POST", "/api/sites/compare",
            {"site_ids": ["shackleton_connecting_ridge", "malapert_mountain"]}, 200
        ),
        (
            "Sites Compare Duplicate 422", "POST", "/api/sites/compare",
            {"site_ids": ["shackleton_connecting_ridge", "shackleton_connecting_ridge"]}, 422
        ),
        (
            "Sites Compare Unknown ID 404", "POST", "/api/sites/compare",
            {"site_ids": ["shackleton_connecting_ridge", "nonexistent_fake_site"]}, 404
        ),
        (
            "Landing Site Detection", "POST", "/api/sites/detect",
            {"center_lat": -89.44, "center_lon": 222.50, "search_radius_meters": 1500.0}, 200
        ),
        (
            "Suitability Score (Site ID)", "POST", "/api/score",
            {"site_id": "shackleton_connecting_ridge", "mission_profile": "artemis_hls"}, 200
        ),
        (
            "Suitability Score (Custom Measurements)", "POST", "/api/score",
            {"slope_deg": 4.5, "roughness_m": 0.25, "illumination_pct": 82.0, "earth_visibility_pct": 65.0}, 200
        ),
        (
            "Horizon Elevation Radial", "POST", "/api/horizon/elevation",
            {"lat": -89.44, "lon": 222.50, "azimuth_deg": 45.0}, 200
        ),
        (
            "Sunset / Sunrise Prediction", "POST", "/api/sunset-sunrise",
            {"lat": -89.44, "lon": 222.50, "start_epoch_iso": "2026-11-15T00:00:00Z"}, 200
        ),
        (
            "Visibility Simulation (Horizons DE441)", "POST", "/api/simulation/visibility",
            {"lat": -89.44, "lon": 222.50, "duration_days": 1.0, "step_hours": 2.0, "ephemeris_source": "horizons"}, 200
        ),
        (
            "Visibility Simulation (Analytical Fallback)", "POST", "/api/simulation/visibility",
            {"lat": -89.44, "lon": 222.50, "duration_days": 1.0, "step_hours": 2.0, "ephemeris_source": "analytical"}, 200
        ),
        (
            "Horizons Direct Ephemeris Query", "POST", "/api/ephemeris/query",
            {"latitude": -89.44, "longitude": 222.50, "target": "Sun", "start_epoch_iso": "2026-11-15T00:00:00Z", "duration_days": 1.0, "step_hours": 2.0}, 200
        ),
        (
            "AI Assistant Explain", "POST", "/api/ai/explain",
            {"analysis_id": analysis_id}, 200
        ),
        (
            "Report Generation JSON", "POST", "/api/reports/generate",
            {"site_id": "shackleton_connecting_ridge", "format": "json"}, 200
        ),
        (
            "Report Generation PDF", "POST", "/api/reports/generate",
            {"site_id": "shackleton_connecting_ridge", "format": "pdf"}, 200
        ),
    ]

    print("--- EXECUTING API TEST MATRIX ---")
    passed = 0
    failed = 0
    
    for name, method, path, body, expected in tests:
        url = f"{BASE_URL}{path}"
        code, resp, err = fetch_raw(url, method=method, data=body)
        
        status_ok = (code == expected)
        if status_ok:
            passed += 1
            print(f"  [PASS] {name:44} -> HTTP {code} (expected {expected})")
        else:
            failed += 1
            print(f"  [FAIL] {name:44} -> HTTP {code} (expected {expected}, err={err}, resp={str(resp)[:120]})")
            
    print(f"\nAPI Contract Results: {passed} PASSED, {failed} FAILED out of {len(tests)} endpoints tested.")
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
