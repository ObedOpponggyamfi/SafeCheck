"""Application-wide configuration and filesystem paths.

Values can be overridden with environment variables (optionally via a ``.env``
file in the project root). Sensible defaults keep the app working with zero
configuration. Keeping every path and tunable here makes it easy to relocate
storage when the app is later packaged for Android.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "SafeCheck Offline"
APP_VERSION = "0.2.0"  # Phase Two

# Project root = one level above the ``safecheck`` package directory.
BASE_DIR = Path(__file__).resolve().parent.parent

# Optional .env support (python-dotenv ships with the server dependencies).
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except Exception:  # noqa: BLE001 — .env is entirely optional
    pass


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


# Local data directory holds the offline SQLite database and captured photos.
DATA_DIR = Path(_env("SAFECHECK_DATA_DIR", str(BASE_DIR / "data")))
PHOTOS_DIR = DATA_DIR / "photos"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# SQLite database used by the field application (offline-first store).
DATABASE_PATH = DATA_DIR / "safecheck.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Generated PDF/Excel reports are written here.
REPORTS_DIR = Path(_env("SAFECHECK_REPORTS_DIR", str(BASE_DIR / "reports_output")))
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Photograph compression target (Pillow) — keeps offline storage small.
PHOTO_MAX_DIMENSION = int(_env("SAFECHECK_PHOTO_MAX_DIMENSION", "1280"))  # px, longest edge
PHOTO_JPEG_QUALITY = int(_env("SAFECHECK_PHOTO_JPEG_QUALITY", "70"))      # 0-95

# Server-side upload safety.
MAX_UPLOAD_BYTES = int(_env("SAFECHECK_MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))  # 8 MB
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# Synchronisation server. The field app stays fully functional even when this
# server is unreachable — inspections simply wait in the sync queue. Port 8077
# is dedicated to SafeCheck to avoid clashing with other local servers.
SYNC_SERVER_URL = _env("SAFECHECK_SYNC_SERVER_URL", "http://127.0.0.1:8077")
SYNC_TIMEOUT_SECONDS = int(_env("SAFECHECK_SYNC_TIMEOUT", "5"))

# Default password applied to every seeded demo user.
DEMO_PASSWORD = _env("SAFECHECK_DEMO_PASSWORD", "safecheck")

# Logging level (DEBUG / INFO / WARNING / ERROR).
LOG_LEVEL = _env("SAFECHECK_LOG_LEVEL", "INFO")
