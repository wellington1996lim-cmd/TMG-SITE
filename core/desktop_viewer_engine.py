from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.raster_loader import RasterLoader
from core.viewer_engine import BaseViewerEngine


def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


class DesktopViewerEngine(BaseViewerEngine):
    """Motor local com leitura por viewport/blocos e cache LRU."""

    name = "desktop"

    def __init__(self):
        super().__init__()
        self.loader: RasterLoader | None = None
        self.grid_data: Any = None
        self.layers: Any = None
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

    def open_image(self, path: str | Path):
        self.close_viewer()
        result = super().open_image(path)
        if not result.get("ok"):
            return {
                "ok": False,
                "engine": self.name,
                "path": str(path),
                "message": "Imagem nao encontrada para o visualizador desktop.",
            }
        self.loader = RasterLoader(path)
        return {
            "ok": True,
            "engine": self.name,
            "path": str(Path(path)),
            "width": int(self.loader.width),
            "height": int(self.loader.height),
            "backend": self.loader.backend,
            "crs": str(self.loader.crs) if self.loader.crs else "",
            "message": "Motor desktop local pronto com leitura por viewport.",
        }

    def get_viewport(self, x: float, y: float, zoom: float, width: int, height: int):
        if self.loader is None:
            if self.image_path is None:
                raise RuntimeError("Nenhuma imagem aberta no motor desktop.")
            self.loader = RasterLoader(self.image_path)
        self.pan_x = float(x or 0)
        self.pan_y = float(y or 0)
        self.zoom = max(0.02, float(zoom or 1.0))
        return self.loader.get_viewport(self.pan_x, self.pan_y, self.zoom, int(width), int(height))

    def render_grid(self, grid_data: Any):
        self.grid_data = grid_data
        return {"engine": self.name, "grid_data": grid_data}

    def render_overlays(self, layers: Any):
        self.layers = layers
        return {"engine": self.name, "layers": layers}

    def update_zoom(self, zoom: float):
        self.zoom = max(0.02, float(zoom or 1.0))
        return self.zoom

    def update_pan(self, x: float, y: float):
        self.pan_x = float(x or 0)
        self.pan_y = float(y or 0)
        return self.pan_x, self.pan_y

    def rotate_view(self, angle: float):
        return float(angle or 0)

    def select_parcel(self, parcel_id: str):
        return {"engine": self.name, "parcel_id": parcel_id}

    def export_current_view(self, output_path: str | Path):
        if self.loader is None:
            return {"ok": False, "path": str(output_path), "message": "Nenhuma imagem aberta."}
        return {
            "ok": False,
            "path": str(output_path),
            "message": "Exportacao oficial permanece nas funcoes Streamlit existentes.",
        }

    def close_viewer(self):
        if self.loader is not None:
            self.loader.close()
        self.loader = None
        return None


def launch_desktop_viewer(image_path: str | Path, app_root: str | Path | None = None) -> tuple[bool, str]:
    root = Path(app_root or Path(__file__).resolve().parents[1]).resolve()
    image = Path(image_path).resolve()
    if not image.exists():
        return False, f"Imagem nao encontrada: {image}"
    try:
        subprocess.Popen(
            [sys.executable, "-m", "core.desktop_viewer_engine", str(image)],
            cwd=str(root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True, "Visualizador Desktop Local aberto com motor otimizado."
    except Exception as exc:
        return False, f"Nao foi possivel abrir o visualizador desktop: {exc}"


def _array_to_qpixmap(arr):
    import numpy as np
    from PySide6 import QtGui

    rgb = np.ascontiguousarray(arr[:, :, :3])
    height, width, channels = rgb.shape
    qimg = QtGui.QImage(rgb.data, width, height, channels * width, QtGui.QImage.Format_RGB888).copy()
    return QtGui.QPixmap.fromImage(qimg)


def _run_pyside_tile_viewer(image_path: Path) -> int:
    from PySide6 import QtCore, QtGui, QtWidgets

    class TileWindow(QtWidgets.QMainWindow):
        def __init__(self, path: Path):
            super().__init__()
            self.path = path
            self.loader = RasterLoader(path)
            self.zoom = min(1.0, 1400 / max(1, max(self.loader.width, self.loader.height)))
            self.zoom = max(self.zoom, 0.02)
            self.center_x = self.loader.width / 2
            self.center_y = self.loader.height / 2
            self.drag_origin = None
            self.setWindowTitle(f"TMG Desktop Local - {path.name}")
            self.resize(1320, 860)
            self.setStyleSheet(
                """
                QMainWindow { background:#061525; color:#ffffff; }
                QLabel#imageLabel { background:#020e24; border:1px solid rgba(0,212,255,.35); }
                QLabel#statusLabel {
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #020e24, stop:1 #0d2b45);
                    color:#e8fbff; padding:8px; font-weight:700;
                    border-top:1px solid rgba(0,212,255,.30);
                }
                """
            )
            central = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(central)
            layout.setContentsMargins(8, 8, 8, 8)
            self.label = QtWidgets.QLabel(objectName="imageLabel")
            self.label.setAlignment(QtCore.Qt.AlignCenter)
            self.label.setMouseTracking(True)
            self.status = QtWidgets.QLabel(objectName="statusLabel")
            layout.addWidget(self.label, 1)
            layout.addWidget(self.status, 0)
            self.setCentralWidget(central)
            self.label.installEventFilter(self)
            QtCore.QTimer.singleShot(100, self.render)

        def eventFilter(self, obj, event):
            if obj is self.label:
                if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                    self.drag_origin = event.position()
                    return True
                if event.type() == QtCore.QEvent.MouseMove and self.drag_origin is not None:
                    pos = event.position()
                    delta = pos - self.drag_origin
                    self.drag_origin = pos
                    self.center_x -= delta.x() / max(self.zoom, 0.02)
                    self.center_y -= delta.y() / max(self.zoom, 0.02)
                    self._clamp_center()
                    self.render()
                    return True
                if event.type() == QtCore.QEvent.MouseButtonRelease:
                    self.drag_origin = None
                    return True
                if event.type() == QtCore.QEvent.Wheel:
                    factor = 1.18 if event.angleDelta().y() > 0 else 0.84
                    self.zoom = max(0.02, min(20.0, self.zoom * factor))
                    self._clamp_center()
                    self.render()
                    return True
            return super().eventFilter(obj, event)

        def resizeEvent(self, event):
            super().resizeEvent(event)
            QtCore.QTimer.singleShot(50, self.render)

        def keyPressEvent(self, event):
            if event.key() in (QtCore.Qt.Key_F, QtCore.Qt.Key_R):
                self.zoom = min(1.0, self.label.width() / max(1, self.loader.width), self.label.height() / max(1, self.loader.height))
                self.zoom = max(self.zoom, 0.02)
                self.center_x = self.loader.width / 2
                self.center_y = self.loader.height / 2
                self.render()
                return
            if event.key() == QtCore.Qt.Key_Escape:
                self.close()
                return
            super().keyPressEvent(event)

        def _clamp_center(self):
            self.center_x = min(max(self.center_x, 0), self.loader.width)
            self.center_y = min(max(self.center_y, 0), self.loader.height)

        def render(self):
            width = max(240, self.label.width())
            height = max(180, self.label.height())
            src_w = width / max(self.zoom, 0.02)
            src_h = height / max(self.zoom, 0.02)
            x = max(0, min(self.loader.width - 1, self.center_x - src_w / 2))
            y = max(0, min(self.loader.height - 1, self.center_y - src_h / 2))
            arr = self.loader.get_viewport(x, y, self.zoom, width, height)
            pix = _array_to_qpixmap(arr)
            pix = pix.scaled(width, height, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.label.setPixmap(pix)
            self.status.setText(
                f"{self.path.name} | {self.loader.width} x {self.loader.height}px | "
                f"{self.loader.backend} | Zoom {self.zoom * 100:.0f}% | arrastar para mover, roda para zoom, F ajustar"
            )

        def closeEvent(self, event):
            self.loader.close()
            super().closeEvent(event)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    app.setApplicationName("TMG Desktop Local")
    window = TileWindow(image_path)
    window.show()
    return int(app.exec())


def _run_tk_fallback(image_path: Path) -> int:
    from viewers.desktop_viewer import DesktopOrthoViewer

    viewer = DesktopOrthoViewer(image_path)
    viewer.run()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv)
    if len(args) < 2:
        print("Uso: python -m core.desktop_viewer_engine caminho_da_imagem")
        return 2
    image_path = Path(args[1]).resolve()
    if not image_path.exists():
        print(f"Imagem nao encontrada: {image_path}")
        return 1
    if _has_module("PySide6") and _has_module("numpy"):
        try:
            return _run_pyside_tile_viewer(image_path)
        except Exception:
            pass
    return _run_tk_fallback(image_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
