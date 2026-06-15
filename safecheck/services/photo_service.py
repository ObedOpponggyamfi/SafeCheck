"""Photograph handling — compress and store inspection photos with Pillow.

Photographs are optional in Phase One, but when supplied we compress them so the
offline database directory stays small and syncs quickly later.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image

from safecheck.config import PHOTO_JPEG_QUALITY, PHOTO_MAX_DIMENSION, PHOTOS_DIR


def save_compressed_photo(source_path: str, inspection_uuid: str) -> str:
    """Compress *source_path* and store it under the photos directory.

    Returns the path of the stored JPEG. The longest edge is capped at
    ``PHOTO_MAX_DIMENSION`` and the image is re-encoded as JPEG.
    """
    source = Path(source_path)
    target_dir = PHOTOS_DIR / inspection_uuid
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid.uuid4().hex}.jpg"

    with Image.open(source) as img:
        # Convert to RGB so formats like PNG/HEIC save cleanly as JPEG.
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail((PHOTO_MAX_DIMENSION, PHOTO_MAX_DIMENSION))
        img.save(target, format="JPEG", quality=PHOTO_JPEG_QUALITY, optimize=True)

    return str(target)
