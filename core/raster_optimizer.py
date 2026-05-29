from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPTIMIZED_DIR = PROJECT_ROOT / "cache" / "optimized_orthos"


def inspect_raster(path: str | Path) -> dict:
    raster_path = Path(path)
    info = {
        "ok": False,
        "path": str(raster_path),
        "width": 0,
        "height": 0,
        "count": 0,
        "crs": "",
        "is_tiled": False,
        "block_shapes": [],
        "overviews": [],
        "message": "",
    }
    try:
        import rasterio

        with rasterio.open(str(raster_path)) as src:
            block_shapes = list(getattr(src, "block_shapes", []) or [])
            overviews = src.overviews(1) if src.count else []
            info.update(
                {
                    "ok": True,
                    "width": int(src.width),
                    "height": int(src.height),
                    "count": int(src.count),
                    "crs": str(src.crs) if src.crs else "",
                    "is_tiled": any(bool(shape) for shape in block_shapes),
                    "block_shapes": [tuple(map(int, shape)) for shape in block_shapes],
                    "overviews": [int(value) for value in overviews],
                    "message": "Raster analisado.",
                }
            )
    except Exception as exc:
        info["message"] = f"Nao foi possivel analisar o raster: {exc}"
    return info


def has_internal_blocks(path: str | Path) -> bool:
    return bool(inspect_raster(path).get("is_tiled"))


def has_overviews(path: str | Path) -> bool:
    return bool(inspect_raster(path).get("overviews"))


def optimized_output_path(path: str | Path, cache_dir: str | Path | None = None) -> Path:
    raster_path = Path(path)
    root = Path(cache_dir or OPTIMIZED_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{raster_path.stem}_tmg_optimized.tif"


def _gdal_available() -> bool:
    return shutil.which("gdal_translate") is not None and shutil.which("gdaladdo") is not None


def create_optimized_copy(path: str | Path, output_path: str | Path | None = None, overwrite: bool = False) -> dict:
    raster_path = Path(path).resolve()
    if not raster_path.exists():
        return {"ok": False, "path": str(raster_path), "message": "Raster original nao encontrado."}
    target = Path(output_path).resolve() if output_path else optimized_output_path(raster_path).resolve()
    if target == raster_path and not overwrite:
        return {"ok": False, "path": str(target), "message": "O arquivo original nao sera sobrescrito sem confirmacao."}
    if target.exists() and not overwrite:
        return {"ok": True, "path": str(target), "message": "Copia otimizada ja existe."}
    if not _gdal_available():
        return {
            "ok": False,
            "path": str(target),
            "message": "GDAL nao encontrado. Instale requirements-desktop.txt para criar COG/overviews localmente.",
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    translate_cmd = [
        "gdal_translate",
        "-of",
        "GTiff",
        "-co",
        "TILED=YES",
        "-co",
        "BIGTIFF=IF_SAFER",
        "-co",
        "COMPRESS=DEFLATE",
        "-co",
        "PREDICTOR=2",
        str(raster_path),
        str(target),
    ]
    addo_cmd = ["gdaladdo", "-r", "average", str(target), "2", "4", "8", "16", "32"]
    try:
        subprocess.run(translate_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(addo_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True, "path": str(target), "message": "Copia otimizada criada com tiles e overviews."}
    except Exception as exc:
        return {"ok": False, "path": str(target), "message": f"Falha ao otimizar raster: {exc}"}
