"""Health check schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """System health and operational status response."""

    status: str = Field(..., description="Service health status ('healthy' or 'degraded')")
    version: str = Field(..., description="Moonscape backend version")
    dem_dataset_loaded: bool = Field(..., description="Whether the LOLA elevation raster is accessible")
    sites_loaded: int = Field(..., description="Number of candidate landing sites registered in catalog")
    crs: str = Field(..., description="Active lunar coordinate reference system")
    disclaimer: str = Field(..., description="Mandatory scientific disclaimer")
