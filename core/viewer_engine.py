from __future__ import annotations

from pathlib import Path
from typing import Any


class BaseViewerEngine:
    name = "base"

    def __init__(self):
        self.image_path: Path | None = None

    def open_image(self, path: str | Path):
        self.image_path = Path(path)
        return {"ok": self.image_path.exists(), "path": str(self.image_path)}

    def get_viewport(self, x: float, y: float, zoom: float, width: int, height: int):
        raise NotImplementedError

    def render_grid(self, grid_data: Any):
        return grid_data

    def render_overlays(self, layers: Any):
        return layers

    def update_zoom(self, zoom: float):
        return zoom

    def update_pan(self, x: float, y: float):
        return x, y

    def rotate_view(self, angle: float):
        return angle

    def select_parcel(self, parcel_id: str):
        return parcel_id

    def export_current_view(self, output_path: str | Path):
        return {"ok": False, "path": str(output_path), "message": "Exportação delegada ao visualizador atual."}

    def close_viewer(self):
        return None


def select_engine(mode: str = "streamlit"):
    normalized = str(mode or "streamlit").lower()
    if normalized == "desktop":
        try:
            from core.desktop_viewer_engine import DesktopViewerEngine

            return DesktopViewerEngine()
        except Exception:
            pass
    from core.streamlit_viewer_engine import StreamlitViewerEngine

    return StreamlitViewerEngine()


def open_image(path: str | Path, mode: str = "streamlit"):
    return select_engine(mode).open_image(path)


def get_viewport(path: str | Path, x: float, y: float, zoom: float, width: int, height: int, mode: str = "streamlit"):
    engine = select_engine(mode)
    engine.open_image(path)
    return engine.get_viewport(x, y, zoom, width, height)


def render_grid(grid_data: Any, mode: str = "streamlit"):
    return select_engine(mode).render_grid(grid_data)


def render_overlays(layers: Any, mode: str = "streamlit"):
    return select_engine(mode).render_overlays(layers)


def update_zoom(zoom: float, mode: str = "streamlit"):
    return select_engine(mode).update_zoom(zoom)


def update_pan(x: float, y: float, mode: str = "streamlit"):
    return select_engine(mode).update_pan(x, y)


def rotate_view(angle: float, mode: str = "streamlit"):
    return select_engine(mode).rotate_view(angle)


def select_parcel(parcel_id: str, mode: str = "streamlit"):
    return select_engine(mode).select_parcel(parcel_id)


def export_current_view(output_path: str | Path, mode: str = "streamlit"):
    return select_engine(mode).export_current_view(output_path)


def close_viewer(mode: str = "streamlit"):
    return select_engine(mode).close_viewer()

