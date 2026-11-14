"""FastAPI application entry point for the Moonscape Lunar Landing-Site Analysis Platform."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.constants import SCIENTIFIC_SAFETY_DISCLAIMER
from app.core.logging import logger, setup_logging
from app.routes import (
    ai,
    analysis,
    data_catalog,
    data_downloads,
    hazards,
    health,
    map,
    reports,
    scoring,
    sites,
    terrain,
)
from app.services.dem_service import dem_service
from app.services.hazard_detection import hazard_detection_service
from app.services.site_service import site_service
from Backend.app.services.data_management.dataset_registry import dataset_registry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown procedures."""
    setup_logging()
    logger.info("Initializing %s v%s", settings.PROJECT_NAME, settings.VERSION)

    # Verify candidate sites catalog
    site_count = site_service.count_sites()
    logger.info("Loaded %d candidate landing sites into memory catalog", site_count)

    # Verify DEM dataset availability
    if dem_service.is_available():
        logger.info("NASA LOLA DEM dataset verified at: %s", settings.DEM_DATA_PATH)
    else:
        logger.warning(
            "DEM dataset not found at %s. Some terrain endpoints may return degraded responses.",
            settings.DEM_DATA_PATH,
        )

    # Verify NASA lunar dataset registry
    installed_datasets = dataset_registry.get_installed_datasets()
    logger.info("NASA Lunar Registry initialized: %d verified datasets available locally", len(installed_datasets))

    # Initialize Lunar Hazard Detection ML model (Phase 4)
    if hazard_detection_service.load_model():
        logger.info("Lunar Hazard Detection ML model loaded successfully: %s", hazard_detection_service.get_metadata().get("model_name"))
    else:
        logger.info("Lunar Hazard Detection ML model not configured in Backend/data/models/. Optical ML inference will report 'not_available'.")

    yield

    logger.info("Shutting down %s", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Moonscape is a scientific lunar South Pole landing-site analysis platform. "
        "It provides terrain slopes, surface roughness, hazard detection, multi-criteria "
        "suitability scoring, and AI-driven scientific explanations."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# Cross-Origin Resource Sharing (CORS) Configuration
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API Route Registration
# ---------------------------------------------------------------------------
api_prefix = settings.API_V1_STR  # "/api"

app.include_router(health.router, prefix=api_prefix)
app.include_router(sites.router, prefix=api_prefix)
app.include_router(map.router, prefix=api_prefix)
app.include_router(terrain.router, prefix=api_prefix)
app.include_router(analysis.router, prefix=api_prefix)
app.include_router(hazards.router, prefix=api_prefix)
app.include_router(scoring.router, prefix=api_prefix)
app.include_router(ai.router, prefix=api_prefix)
app.include_router(reports.router, prefix=api_prefix)
app.include_router(data_catalog.router, prefix=api_prefix)
app.include_router(data_downloads.router, prefix=api_prefix)


# ---------------------------------------------------------------------------
# Root and Fallback Endpoints
# ---------------------------------------------------------------------------
@app.get("/", summary="Root landing endpoint")
def root_endpoint() -> dict:
    """Returns basic system identity, API documentation links, and active disclaimer."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "api_documentation": "/docs",
        "api_base": settings.API_V1_STR,
        "disclaimer": SCIENTIFIC_SAFETY_DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches unhandled errors and returns structured JSON responses without crashing."""
    logger.exception("Unhandled server exception during request %s: %s", request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred processing lunar scientific calculations.",
            "detail": str(exc) if settings.DEBUG else None,
            "path": request.url.path,
        },
    )
