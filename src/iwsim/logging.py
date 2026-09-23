from __future__ import annotations

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure package-wide logging once for CLI/tests."""
    logger = logging.getLogger(__name__)
    logger.info("configure_logging level=%s", level)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
