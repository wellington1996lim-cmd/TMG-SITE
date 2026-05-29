from __future__ import annotations

from pathlib import Path


def tile_cache_dir(project_root: str | Path) -> Path:
    root = Path(project_root).resolve()
    target = root / "tmg_data" / "tile_viewer_cache"
    target.mkdir(parents=True, exist_ok=True)
    return target

