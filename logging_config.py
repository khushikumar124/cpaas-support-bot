"""Central logging setup for CLI and future Slack handler."""

from __future__ import annotations

import logging
import sys

from config import LOG_LEVEL


def setup_logging() -> None:
    """Configure root logger with a consistent format."""
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
