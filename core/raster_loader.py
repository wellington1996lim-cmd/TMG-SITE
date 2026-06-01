from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any


class LruTileCache:
    def __init__(self, max_items: int = 64):
        self.max_items = max(4, int(max_items or 64))
        self._data: OrderedDict[Any, Any] = OrderedDict()

    def get(self, key):
        if key not in self._data:
            return None
        value = self._data.pop(key)
        self._data[key] = value
        return value

    def put(self, key, value) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self.max_items:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()


class RasterLoader:
    def __init__(self, path: str | Path, cache_size: int = 96):
        self.path = Path(path)
        self.cache = LruTileCache(cache_size)
        self.backend = "pillow"
        self.src = None
        self.image = None
        self.width = 0
        self.height = 0
        self.count = 0
        self.crs = None
        self.transform = None
        self._open()

    def _open(self) -> None:
        suffix = self.path.suffix.lower()
        if suffix in {".tif", ".tiff", ".geotiff", ".jp2"}:
            try:
                import rasterio

                self._rasterio_env = rasterio.Env(GDAL_CACHEMAX=512, NUM_THREADS="ALL_CPUS")
                self._rasterio_env.__enter__()
                self.src = rasterio.open(str(self.path), sharing=True)
                self.backend = "rasterio"
                self.width = int(self.src.width)
                self.height = int(self.src.height)
                self.count = int(self.src.count)
                self.crs = self.src.crs
                self.transform = self.src.transform
                return
            except Exception:
                self.src = None
        from PIL import Image, ImageFile

        Image.MAX_IMAGE_PIXELS = None
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        self.image = Image.open(self.path).convert("RGB")
        self.backend = "pillow"
        self.width, self.height = self.image.size
        self.count = 3

    def close(self) -> None:
        try:
            if self.src is not None:
                self.src.close()
        except Exception:
            pass
        try:
            env = getattr(self, "_rasterio_env", None)
            if env is not None:
                env.__exit__(None, None, None)
        except Exception:
            pass
        self.src = None
        self._rasterio_env = None
        self.image = None
        self.cache.clear()

    def _overview_factor(self, zoom: float) -> int:
        try:
            z = float(zoom)
        except Exception:
            z = 1.0
        if z >= 0.75:
            return 1
        if z >= 0.35:
            return 2
        if z >= 0.16:
            return 4
        return 8

    def get_viewport(self, x: float, y: float, zoom: float, width: int, height: int):
        import numpy as np

        x0 = max(0, int(float(x or 0)))
        y0 = max(0, int(float(y or 0)))
        view_w = max(1, int(width or 1))
        view_h = max(1, int(height or 1))
        factor = self._overview_factor(zoom)
        src_w = max(1, int(view_w / max(float(zoom or 1.0), 0.02)))
        src_h = max(1, int(view_h / max(float(zoom or 1.0), 0.02)))
        x1 = min(self.width, x0 + src_w)
        y1 = min(self.height, y0 + src_h)
        key = (x0, y0, x1, y1, factor, view_w, view_h)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        if self.backend == "rasterio" and self.src is not None:
            from rasterio.enums import Resampling
            from rasterio.windows import Window

            win = Window(x0, y0, max(1, x1 - x0), max(1, y1 - y0))
            out_w = max(1, int((x1 - x0) / factor))
            out_h = max(1, int((y1 - y0) / factor))
            indexes = [1, 2, 3] if self.count >= 3 else [1]
            data = self.src.read(
                indexes,
                window=win,
                out_shape=(len(indexes), out_h, out_w),
                resampling=getattr(Resampling, "bilinear", Resampling.nearest),
                masked=True,
            )
            arr = np.ma.asarray(data).filled(0)
            if arr.dtype != np.uint8:
                arr = self._stretch_uint8(arr)
            if arr.ndim == 3:
                if arr.shape[0] == 1:
                    rgb = np.repeat(arr[0:1, :, :], 3, axis=0)
                else:
                    rgb = arr[:3, :, :]
                result = np.transpose(rgb, (1, 2, 0)).astype(np.uint8, copy=False)
            else:
                result = np.repeat(arr[:, :, None], 3, axis=2).astype(np.uint8, copy=False)
        else:
            crop = self.image.crop((x0, y0, x1, y1))
            if factor > 1:
                crop = crop.resize((max(1, crop.width // factor), max(1, crop.height // factor)))
            result = np.asarray(crop.convert("RGB"))
        self.cache.put(key, result)
        return result

    @staticmethod
    def _stretch_uint8(arr):
        import numpy as np

        arr = np.asarray(arr, dtype=np.float32)
        out = []
        for band in arr:
            valid = band[np.isfinite(band)]
            if valid.size == 0:
                out.append(np.zeros(band.shape, dtype=np.uint8))
                continue
            mn = np.nanpercentile(valid, 1)
            mx = np.nanpercentile(valid, 99)
            if not np.isfinite(mn) or not np.isfinite(mx) or mx <= mn:
                mn = np.nanmin(valid)
                mx = np.nanmax(valid)
            if not np.isfinite(mn) or not np.isfinite(mx) or mx <= mn:
                out.append(np.zeros(band.shape, dtype=np.uint8))
            else:
                out.append(np.nan_to_num(np.clip((band - mn) / (mx - mn) * 255, 0, 255)).astype(np.uint8))
        return np.stack(out)
