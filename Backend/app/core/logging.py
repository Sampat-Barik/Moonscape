"""Application logging configuration."""

import logging
import sys


def setup_logging() -> None:
    """Configures structured, informative logging for scientific pipelines and API requests."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


logger = logging.getLogger("moonscape")
