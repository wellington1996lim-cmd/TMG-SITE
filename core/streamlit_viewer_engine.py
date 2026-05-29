from __future__ import annotations

from pathlib import Path
from typing import Any

from core.viewer_engine import BaseViewerEngine


class StreamlitViewerEngine(BaseViewerEngine):
    """Adapter seguro para manter o visualizador Streamlit existente intacto."""

    name = "streamlit"

    def open_image(self, path: str | Path):
        result = super().open_image(path)
        result.update(
            {
                "engine": self.name,
                "desktop": False,
                "message": "Visualizador Streamlit atual preservado.",
            }
        )
        return result

    def get_viewport(self, x: float, y: float, zoom: float, width: int, height: int):
        return {
            "engine": self.name,
            "x": x,
            "y": y,
            "zoom": zoom,
            "width": width,
            "height": height,
            "message": "Viewport gerenciado pelo visualizador Streamlit existente.",
        }

    def render_grid(self, grid_data: Any):
        return {"engine": self.name, "grid_data": grid_data}

    def render_overlays(self, layers: Any):
        return {"engine": self.name, "layers": layers}

    def export_current_view(self, output_path: str | Path):
        return {
            "ok": False,
            "engine": self.name,
            "path": str(output_path),
            "message": "Exportacao permanece no fluxo Streamlit existente.",
        }
