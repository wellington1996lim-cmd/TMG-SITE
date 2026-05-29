from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_MODE_PATH = PROJECT_ROOT / "config" / "local_mode.json"
DEFAULT_MODE = {
    "viewer_mode": "streamlit",
    "enable_desktop_viewer_local": False,
    "force_streamlit_in_deploy": True,
    "desktop_viewer_max_dim": 12000,
    "desktop_viewer_cache_dir": "tmg_data/desktop_viewer",
}


def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def is_deploy_environment() -> bool:
    markers = (
        "STREAMLIT_CLOUD",
        "STREAMLIT_SHARING_MODE",
        "GITHUB_ACTIONS",
        "RENDER",
        "RAILWAY_ENVIRONMENT",
        "FLY_APP_NAME",
        "WEBSITE_SITE_NAME",
        "CODESPACES",
    )
    if any(os.getenv(name) for name in markers):
        return True
    return os.getenv("TMG_FORCE_STREAMLIT_VIEWER", "").strip().lower() in ("1", "true", "yes", "sim")


def has_desktop_session() -> bool:
    if sys.platform.startswith("win"):
        return True
    return bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))


def desktop_runtime_status() -> dict:
    if is_deploy_environment():
        return {
            "available": False,
            "accelerated": False,
            "engine": "streamlit",
            "message": "Deploy detectado. Usando Modo Streamlit Web.",
        }
    if not has_desktop_session():
        return {
            "available": False,
            "accelerated": False,
            "engine": "streamlit",
            "message": "Sessão gráfica local não encontrada. Usando Streamlit.",
        }

    has_pillow = _has_module("PIL")
    has_tkinter = _has_module("tkinter")
    has_rasterio = _has_module("rasterio")
    has_numpy = _has_module("numpy")
    has_pyside = _has_module("PySide6")
    has_pyqtgraph = _has_module("pyqtgraph")

    if has_pyside and has_pyqtgraph and has_rasterio and has_numpy:
        return {
            "available": True,
            "accelerated": True,
            "engine": "desktop_pyqtgraph",
            "message": "Modo Desktop Local acelerado disponível.",
        }
    if has_pillow and has_tkinter:
        engine = "desktop_tkinter_rasterio" if has_rasterio and has_numpy else "desktop_tkinter_pillow"
        return {
            "available": True,
            "accelerated": False,
            "engine": engine,
            "message": "Modo Desktop Local disponível com fallback seguro.",
        }
    return {
        "available": False,
        "accelerated": False,
        "engine": "streamlit",
        "message": "Bibliotecas desktop não instaladas. Usando Streamlit.",
    }


def read_local_mode() -> dict:
    LOCAL_MODE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOCAL_MODE_PATH.exists():
        write_local_mode(DEFAULT_MODE)
        return dict(DEFAULT_MODE)
    try:
        data = json.loads(LOCAL_MODE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            merged = dict(DEFAULT_MODE)
            merged.update(data)
            return merged
    except Exception:
        pass
    return dict(DEFAULT_MODE)


def write_local_mode(config: dict) -> None:
    LOCAL_MODE_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULT_MODE)
    if isinstance(config, dict):
        merged.update(config)
    LOCAL_MODE_PATH.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")


def set_desktop_mode(enabled: bool) -> dict:
    config = read_local_mode()
    config["viewer_mode"] = "desktop" if enabled else "streamlit"
    config["enable_desktop_viewer_local"] = bool(enabled)
    write_local_mode(config)
    return config

