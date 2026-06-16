"""Launch the SafeCheck synchronisation server (FastAPI + Uvicorn).

Run with:  python run_server.py

The field application syncs to http://127.0.0.1:8077 by default (see
``safecheck/config.py``: SYNC_SERVER_URL).
"""
from __future__ import annotations

import uvicorn

from safecheck.core.logging_config import configure_logging, get_logger


def run() -> None:
    configure_logging()
    get_logger("server").info("Starting SafeCheck sync server on http://127.0.0.1:8077")
    uvicorn.run("server.main:app", host="127.0.0.1", port=8077, reload=False)


if __name__ == "__main__":
    run()
