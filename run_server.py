"""Launch the SafeCheck synchronisation server (FastAPI + Uvicorn).

Run with:  python run_server.py

The field application syncs to http://127.0.0.1:8000 by default (see
``safecheck/config.py``: SYNC_SERVER_URL).
"""
from __future__ import annotations

import uvicorn


def run() -> None:
    uvicorn.run("server.main:app", host="127.0.0.1", port=8077, reload=False)


if __name__ == "__main__":
    run()
