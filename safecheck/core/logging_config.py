"""Centralised structured logging (rotating file + console).

Call :func:`configure_logging` once at process start (done by ``run_app.py`` and
``run_server.py``). Modules obtain a logger with :func:`get_logger`.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from safecheck.config import DATA_DIR

LOG_DIR = DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "safecheck.log"

_configured = False
_FORMAT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Set up the ``safecheck`` logger tree with a rotating file + console handler."""
    global _configured
    if _configured:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_FORMAT)
    root = logging.getLogger("safecheck")
    root.setLevel(level)
    root.handlers.clear()

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console)
    root.propagate = False
    _configured = True
    root.info("Logging configured -> %s", LOG_FILE)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``safecheck`` tree."""
    return logging.getLogger(f"safecheck.{name}")
