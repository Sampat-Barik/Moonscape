"""Data source adapters package for NASA lunar datasets."""

from app.services.data_sources.base import BaseDataSource
from app.services.data_sources.diviner import DivinerThermalSource, diviner_thermal
from app.services.data_sources.lroc_nac import LROCNACSource, lroc_nac
from app.services.data_sources.lroc_wac import LROCWACSource, lroc_wac
from app.services.data_sources.pgda_product104 import (
    PGDAProduct104Source,
    pgda_product104,
)
from app.services.data_sources.pgda_product78 import (
    PGDAProduct78Source,
    pgda_product78,
)
from app.services.data_sources.pgda_product90 import (
    PGDAProduct90Source,
    pgda_product90,
)

__all__ = [
    "BaseDataSource",
    "pgda_product90",
    "pgda_product78",
    "pgda_product104",
    "diviner_thermal",
    "lroc_wac",
    "lroc_nac",
    "PGDAProduct90Source",
    "PGDAProduct78Source",
    "PGDAProduct104Source",
    "DivinerThermalSource",
    "LROCWACSource",
    "LROCNACSource",
]
