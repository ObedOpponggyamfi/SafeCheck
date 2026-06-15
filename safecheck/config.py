"""Application-wide configuration and filesystem paths.

Keeping every path and tunable in one module makes it easy to relocate storage
when the app is later packaged for Android.
"""
from __future__ import annotations

from pathlib import Path

APP_NAME = "SafeCheck Offline"
APP_VERSION = "0.1.0"  # Phase One

# Project root = one level above the ``safecheck`` package directory.
BASE_DIR = Path(__file__).resolve().parent.parent

# Local data directory holds the offline SQLite database and captured photos.
DATA_DIR = BASE_DIR / "data"
PHOTOS_DIR = DATA_DIR / "photos"

# Create runtime directories on import so the rest of the app can assume them.
DATA_DIR.mkdir(parents=True, exist_ok=True)
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# SQLite database used by the field application (offline-first store).
DATABASE_PATH = DATA_DIR / "safecheck.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Photograph compression target (Pillow) — keeps offline storage small.
PHOTO_MAX_DIMENSION = 1280   # pixels, longest edge
PHOTO_JPEG_QUALITY = 70      # 0-95

# Synchronisation server (Phase Two). The field app stays fully functional even
# when this server is unreachable — inspections simply wait in the sync queue.
# Port 8077 is dedicated to SafeCheck to avoid clashing with other local servers.
SYNC_SERVER_URL = "http://127.0.0.1:8077"
SYNC_TIMEOUT_SECONDS = 5

# Default password applied to every seeded demo user.
DEMO_PASSWORD = "safecheck"
