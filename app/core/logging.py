from __future__ import annotations

import logging

from app.settings import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s",
    )
