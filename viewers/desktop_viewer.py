from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk, ImageFile


Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True


class DesktopOrthoViewer:
    def __init__(self, image_path: Path, max_dim: int = 12000):
        self.image_path = Path(image_path)
        self.max_dim = int(max_dim or 12000)
        self.root = tk.Tk()
        self.root.title(f"TMG Visualizador Local - {self.image_path.name}")
        self.root.geometry("1280x820")
        self.root.configure(bg="#071526")

        self.canvas = tk.Canvas(self.root, bg="#071526", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.status = tk.Label(
            self.root,
            bg="#020e24",
            fg="#e8fbff",
            anchor="w",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
        )
        self.status.pack(fill=tk.X)

        self.image = self._load_image()
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.dragging = False
        self.last_x = 0
        self.last_y = 0
        self.photo = None

        self.root.bind("<Configure>", self._on_resize)
        self.canvas.bind("<ButtonPress-1>", self._start_pan)
        self.canvas.bind("<B1-Motion>", self._pan)
        self.canvas.bind("<ButtonRelease-1>", self._stop_pan)
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<Button-4>", lambda event: self._zoom_at(event.x, event.y, 1.18))
        self.canvas.bind("<Button-5>", lambda event: self._zoom_at(event.x, event.y, 0.84))
        self.root.bind("<plus>", lambda _event: self._zoom_center(1.18))
        self.root.bind("<minus>", lambda _event: self._zoom_center(0.84))
        self.root.bind("<f>", lambda _event: self.fit())
        self.root.bind("<r>", lambda _event: self.fit())
        self.root.bind("<Escape>", lambda _event: self.root.destroy())

        self.root.after(100, self.fit)

    def _load_image(self) -> Image.Image:
        raster_img = self._load_image_rasterio()
        if raster_img is not None:
            return raster_img
        img = Image.open(self.image_path)
        img = img.convert("RGB")
        if max(img.size) > self.max_dim:
            img.thumbnail((self.max_dim, self.max_dim), Image.Resampling.LANCZOS)
        return img

    def _load_image_rasterio(self) -> Image.Image | None:
        if self.image_path.suffix.lower() not in {".tif", ".tiff", ".geotiff", ".jp2"}:
            return None
        try:
            import numpy as np
            import rasterio
            from rasterio.enums import Resampling
        except Exception:
            return None

        def stretch_band(band):
            arr = np.ma.asarray(band).astype(np.float32).filled(np.nan)
            valid = arr[np.isfinite(arr)]
            if valid.size == 0:
                return np.zeros(arr.shape, dtype=np.uint8)
            mn = np.nanpercentile(valid, 1)
            mx = np.nanpercentile(valid, 99)
            if not np.isfinite(mn) or not np.isfinite(mx) or mx <= mn:
                mn = np.nanmin(valid)
                mx = np.nanmax(valid)
            if not np.isfinite(mn) or not np.isfinite(mx) or mx <= mn:
                return np.zeros(arr.shape, dtype=np.uint8)
            return np.nan_to_num(np.clip((arr - mn) / (mx - mn) * 255, 0, 255)).astype(np.uint8)

        try:
            with rasterio.open(str(self.image_path)) as src:
                ratio = min(1.0, self.max_dim / max(src.width, src.height))
                out_width = max(1, int(src.width * ratio))
                out_height = max(1, int(src.height * ratio))
                resampling = getattr(Resampling, "cubic", Resampling.bilinear)
                if src.count >= 3:
                    indexes = [1, 2, 3]
                    data = src.read(
                        indexes,
                        out_shape=(3, out_height, out_width),
                        resampling=resampling,
                        masked=True,
                    )
                    dtypes = [np.dtype(src.dtypes[index - 1]) for index in indexes]
                    if all(dtype == np.dtype("uint8") for dtype in dtypes):
                        bands = [np.ma.asarray(data[i]).filled(0).astype(np.uint8, copy=False) for i in range(3)]
                    else:
                        bands = [stretch_band(data[i]) for i in range(3)]
                    arr = np.transpose(np.stack(bands), (1, 2, 0))
                    return Image.fromarray(arr, "RGB")
                data = src.read(1, out_shape=(out_height, out_width), resampling=resampling, masked=True)
                if np.dtype(src.dtypes[0]) == np.dtype("uint8"):
                    gray = np.ma.asarray(data).filled(0).astype(np.uint8, copy=False)
                else:
                    gray = stretch_band(data)
                return Image.fromarray(gray, "L").convert("RGB")
        except Exception:
            return None

    def fit(self) -> None:
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        self.scale = min(cw / self.image.width, ch / self.image.height) * 0.98
        self.offset_x = (cw - self.image.width * self.scale) / 2
        self.offset_y = (ch - self.image.height * self.scale) / 2
        self.draw()

    def _on_resize(self, _event=None) -> None:
        self.draw()

    def _start_pan(self, event) -> None:
        self.dragging = True
        self.last_x = event.x
        self.last_y = event.y

    def _pan(self, event) -> None:
        if not self.dragging:
            return
        self.offset_x += event.x - self.last_x
        self.offset_y += event.y - self.last_y
        self.last_x = event.x
        self.last_y = event.y
        self.draw()

    def _stop_pan(self, _event=None) -> None:
        self.dragging = False

    def _wheel(self, event) -> None:
        factor = 1.18 if event.delta > 0 else 0.84
        self._zoom_at(event.x, event.y, factor)

    def _zoom_center(self, factor: float) -> None:
        self._zoom_at(self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2, factor)

    def _zoom_at(self, x: float, y: float, factor: float) -> None:
        old_scale = self.scale
        self.scale = max(0.02, min(80.0, self.scale * factor))
        ix = (x - self.offset_x) / old_scale
        iy = (y - self.offset_y) / old_scale
        self.offset_x = x - ix * self.scale
        self.offset_y = y - iy * self.scale
        self.draw()

    def draw(self) -> None:
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        self.canvas.delete("all")
        if self.scale <= 0:
            return

        img_x0 = max(0, int((-self.offset_x) / self.scale))
        img_y0 = max(0, int((-self.offset_y) / self.scale))
        img_x1 = min(self.image.width, int((cw - self.offset_x) / self.scale) + 2)
        img_y1 = min(self.image.height, int((ch - self.offset_y) / self.scale) + 2)
        if img_x1 <= img_x0 or img_y1 <= img_y0:
            self._update_status()
            return

        crop = self.image.crop((img_x0, img_y0, img_x1, img_y1))
        screen_w = max(1, int(crop.width * self.scale))
        screen_h = max(1, int(crop.height * self.scale))
        crop = crop.resize((screen_w, screen_h), Image.Resampling.BILINEAR)
        self.photo = ImageTk.PhotoImage(crop)
        screen_x = self.offset_x + img_x0 * self.scale
        screen_y = self.offset_y + img_y0 * self.scale
        self.canvas.create_image(screen_x, screen_y, image=self.photo, anchor="nw")
        self._update_status()

    def _update_status(self) -> None:
        self.status.config(
            text=(
                f"{self.image_path.name} | Preview {self.image.width} x {self.image.height}px | "
                f"Zoom {self.scale * 100:.0f}% | mouse: arrastar/pan, roda/zoom, F ajustar, ESC sair"
            )
        )

    def run(self) -> None:
        self.root.mainloop()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Uso: python desktop_viewer.py caminho_da_imagem")
        return 2
    image_path = Path(argv[1]).resolve()
    if not image_path.exists():
        print(f"Imagem nao encontrada: {image_path}")
        return 1
    viewer = DesktopOrthoViewer(image_path)
    viewer.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
