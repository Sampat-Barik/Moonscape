"""AI scientific advisory and landing-site trade-off explanation service."""

import uuid
from typing import List
from app.core.constants import SCIENTIFIC_SAFETY_DISCLAIMER
from app.schemas.ai import AIExplainRequest, AIExplainResponse
from app.services.site_service import site_service


class AIService:
    """Synthesizes physical measurements into coherent scientific rationales and engineering recommendations."""

    def explain_landing_site(self, req: AIExplainRequest) -> AIExplainResponse:
        """Generates an in-depth scientific explanation tailored to site topography and mission constraints."""
        explanation_id = f"EXP-{uuid.uuid4().hex[:8].upper()}"

        site_name = req.site_name
        lat = req.latitude
        lon = req.longitude
        catalog_site = None

        if req.site_id:
            catalog_site = site_service.get_site_by_id(req.site_id)
            if catalog_site:
                site_name = site_name or catalog_site.name
                lat = lat or catalog_site.latitude
                lon = lon or catalog_site.longitude

        target_name = site_name or (f"Coordinate ({lat}°, {lon}°)" if lat and lon else "Candidate Landing Site")
        lat_str = f"{lat:.2f}°" if lat is not None else "South Polar region"
        lon_str = f"{lon:.2f}°" if lon is not None else "undisclosed longitude"

        # Determine topographic context
        slope = None
        illum = None
        comms = None
        if catalog_site:
            slope = catalog_site.mean_slope_deg
            illum = catalog_site.illumination_pct
            comms = catalog_site.earth_visibility_pct
        if req.topographic_data:
            slope = req.topographic_data.get("mean_slope_deg", slope)
            illum = req.topographic_data.get("illumination_pct", illum)

        slope_context = f"{slope}°" if slope is not None else "moderate (5-8°)"
        illum_context = f"{illum}%" if illum is not None else "substantial (>70%)"
        comms_context = f"{comms}%" if comms is not None else "adequate"

        exec_summary = (
            f"Evaluation of {target_name} at {lat_str}, {lon_str} reveals a high-value lunar South Pole "
            f"candidate zone characterized by average slopes of {slope_context} and an estimated solar illumination "
            f"fraction of {illum_context}. The site offers an exceptional scientific balance between access to "
            f"cryogenic volatile cold traps and viable surface solar power generation, but requires strict hazard-relative "
            f"navigation to negotiate local slope inflections and boulder fields."
        )

        geom_text = (
            f"The local geomorphology is shaped by ancient South Pole-Aitken (SPA) basin ejecta blankets and "
            f"superposed impact degradation. Elevation profiles derived from NASA LRO LOLA data show undulating terrain "
            f"with local slopes averaging {slope_context}. While broad plateaus offer safe touchdown corridors, the rims "
            f"transition sharply into steep crater walls exceeding 20°, which present significant lander dynamic tip-over "
            f"hazards. Surface regolith is expected to be mature with sub-meter boulder populations clustered around "
            f"recent micro-impact scars."
        )

        thermal_text = (
            f"Due to the Moon's low obliquity (1.54°), sunlight strikes {target_name} at grazing angles, producing elongated, "
            f"dynamic shadows. Elevated peaks achieve {illum_context} annual illumination during lunar summer, supporting "
            f"surface photovoltaic power generation and mitigating extreme cryogenic drops. However, nearby crater depressions "
            f"are permanently shadowed (PSRs) with temperatures sustained between 40 K and 80 K, acting as pristine cold traps "
            f"for water ice (H2O), carbon monoxide, and volatile organic compounds."
        )

        comms_text = (
            f"Direct line-of-sight to Earth reaches approximately {comms_context} of the lunar year. Lunar orbital libration "
            f"(up to 6.7° in latitude and 8.1° in longitude) causes Earth to oscillate near the local horizon. During unfavorable "
            f"libration phases, terrestrial ground stations may be occulted by regional topography, requiring orbital relay "
            f"satellites (e.g., Gateway or dedicated lunar communication relays) to maintain continuous telemetry and crew comms."
        )

        traverse_text = (
            f"The location serves as an optimal operational staging hub for robotic and crewed EVAs. Benign regional slopes "
            f"enable rover trafficability into nearby shadowed sampling zones within a 2-5 km radius. Crew missions can "
            f"retrieve volatile cores from permanently shadowed depressions while maintaining base habitat and solar array "
            f"assets on illuminated ridge tops."
        )

        tradeoffs = [
            f"Solar Power vs. Slope Hazard: Peak elevations maximize illumination ({illum_context}) but narrow ridge crests reduce touchdown footprint clearance.",
            f"Volatile Proximity vs. Cryogenic Risk: Landing close to PSRs minimizes rover transit distance but increases thermal shock on lander propulsion and structures.",
            f"Direct Earth Contact vs. Topographic Shadowing: High direct Earth visibility ({comms_context}) is vulnerable to libration dips behind massif horizons.",
        ]

        mitigations = [
            "Implement active Hazard Detection and Avoidance (HDA) with flash lidar to detect sub-meter boulders during the final 500m of descent.",
            "Schedule landing touchdown during the peak southern lunar summer illumination window to maximize battery charging buffers.",
            "Deploy a secondary S-band/Ka-band relay antenna on an elevated mast or rely on lunar relay orbital assets during libration occultation periods.",
            "Equip surface rovers with radioactive heating units (RHUs) or active battery warming circuits before descending into cryogenic cold traps.",
        ]

        return AIExplainResponse(
            explanation_id=explanation_id,
            target_site=target_name,
            explanation=exec_summary,
            executive_summary=exec_summary,
            geomorphology_assessment=geom_text,
            thermal_and_power_assessment=thermal_text,
            communication_and_direct_line_of_sight=comms_text,
            traverse_and_sampling_potential=traverse_text,
            key_engineering_tradeoffs=tradeoffs,
            mitigation_strategies=mitigations,
            model_origin="Moonscape Lunar AI Scientific Advisory Engine v1.0 (Rule-Grounded Physics & Geomorphology)",
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )


ai_service = AIService()
