"""Scientific constants and engineering specifications for lunar south pole landing analysis."""

# Moon Geodetic Constants
MOON_RADIUS_METERS: float = 1_737_400.0  # IAU 2000 Moon Mean Radius
MOON_SURFACE_GRAVITY: float = 1.62  # m/s^2

# Coordinate Bounds for Lunar South Pole Analysis
SOUTH_POLE_MIN_LAT: float = -90.0
SOUTH_POLE_MAX_LAT: float = -80.0
LUNAR_MIN_LON: float = -180.0
LUNAR_MAX_LON: float = 360.0

# Engineering Landing Limits (Based on Apollo & Artemis Lunar Lander Specs)
SLOPE_IDEAL_MAX_DEG: float = 5.0
SLOPE_NOMINAL_MAX_DEG: float = 10.0
SLOPE_CRITICAL_MAX_DEG: float = 15.0  # Landers risk tip-over at > 15 degrees

ROUGHNESS_IDEAL_MAX_M: float = 0.3
ROUGHNESS_NOMINAL_MAX_M: float = 0.5
ROUGHNESS_CRITICAL_MAX_M: float = 1.5

BOULDER_HAZARD_THRESHOLD_M: float = 0.35  # Footpad / engine clearance hazard
CRATER_HAZARD_MIN_DIAMETER_M: float = 5.0  # Local touchdown impact hazard

# NASA LOLA Dataset Metadata
LOLA_DATASET_NAME: str = "NASA LRO LOLA (Lunar Orbiter Laser Altimeter)"
LOLA_PRODUCT_ID: str = "LDEM_80S_100M"
LOLA_SPATIAL_RESOLUTION_M: float = 100.0
LOLA_VERTICAL_ACCURACY_M: float = 1.0  # RMS vertical accuracy
LOLA_NODATA_VALUE: float = -32768.0

# Map Projection Information
PROJECTION_NAME: str = "Lunar Polar Stereographic"
PROJECTION_EPSG: str = "ESRI:104903"
PROJECTION_WKT: str = (
    'PROJCS["Moon_2000_South_Pole_Stereographic",'
    'GEOGCS["GCS_Moon_2000",'
    'DATUM["D_Moon_2000",'
    'SPHEROID["Moon_2000_IAU_IAG",1737400.0,0.0]],'
    'PRIMEM["Reference_Meridian",0.0],'
    'UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Stereographic"],'
    'PARAMETER["latitude_of_origin",-90.0],'
    'PARAMETER["central_meridian",0.0],'
    'PARAMETER["scale_factor",1.0],'
    'PARAMETER["false_easting",0.0],'
    'PARAMETER["false_northing",0.0],'
    'UNIT["Meter",1.0]]'
)

# Mandatory Scientific Safety Disclaimer
SCIENTIFIC_SAFETY_DISCLAIMER: str = (
    "DISCLAIMER: Suitability evaluations and hazard predictions provided by Moonscape are preliminary "
    "engineering research models derived from orbital remote sensing measurements (NASA LRO LOLA/LROC). "
    "These outputs do NOT constitute certified landing safety clearance for lunar flight missions."
)
