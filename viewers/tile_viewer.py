from __future__ import annotations

import os
import tempfile
from pathlib import Path


def tile_cache_dir(project_root: str | Path) -> Path:
    root = Path(project_root).resolve()
    if os.getenv("TMG_ENABLE_TILE_VIEWER_CACHE", "").strip().lower() in ("1", "true", "yes", "sim"):
        target = root / "tmg_data" / "tile_viewer_cache"
    else:
        target = Path(tempfile.gettempdir()) / "tmg_tile_viewer_cache"
    target.mkdir(parents=True, exist_ok=True)
    return target
