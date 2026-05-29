from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "tmg_config"
DATA_DIR = PROJECT_ROOT / "tmg_data"
VIEWER_CONFIG_PATH = CONFIG_DIR / "viewer_config.json"
LOCAL_MODE_CONFIG_PATH = PROJECT_ROOT / "config" / "local_mode.json"


DEFAULT_VIEWER_CONFIG = {
    "viewer_mode": "streamlit",
    "enable_desktop_viewer_local": False,
    "force_streamlit_in_deploy": True,
    "desktop_viewer_max_dim": 12000,
    "desktop_viewer_cache_dir": "tmg_data/desktop_viewer",
}


def _read_viewer_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_MODE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not VIEWER_CONFIG_PATH.exists() and not LOCAL_MODE_CONFIG_PATH.exists():
        _write_viewer_config(DEFAULT_VIEWER_CONFIG)
        return dict(DEFAULT_VIEWER_CONFIG)
    try:
        merged = dict(DEFAULT_VIEWER_CONFIG)
        for path in (VIEWER_CONFIG_PATH, LOCAL_MODE_CONFIG_PATH):
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_VIEWER_CONFIG)


def _write_viewer_config(config: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        LOCAL_MODE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        VIEWER_CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        LOCAL_MODE_CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def save_viewer_mode(mode: str, enable_desktop: bool | None = None) -> dict:
    config = _read_viewer_config()
    normalized = str(mode or "auto").strip().lower()
    if normalized not in ("auto", "streamlit", "desktop"):
        normalized = "auto"
    config["viewer_mode"] = normalized
    if enable_desktop is not None:
        config["enable_desktop_viewer_local"] = bool(enable_desktop)
    _write_viewer_config(config)
    return config


def enable_desktop_viewer_mode() -> dict:
    return save_viewer_mode("desktop", enable_desktop=True)


def enable_streamlit_viewer_mode() -> dict:
    return save_viewer_mode("streamlit", enable_desktop=False)


def is_deploy_environment() -> bool:
    cloud_markers = (
        "STREAMLIT_CLOUD",
        "STREAMLIT_SHARING_MODE",
        "GITHUB_ACTIONS",
        "RENDER",
        "RAILWAY_ENVIRONMENT",
        "FLY_APP_NAME",
        "WEBSITE_SITE_NAME",
        "CODESPACES",
    )
    if any(os.getenv(name) for name in cloud_markers):
        return True
    if os.getenv("TMG_FORCE_STREAMLIT_VIEWER", "").strip().lower() in ("1", "true", "yes", "sim"):
        return True
    return False


def has_desktop_session() -> bool:
    if sys.platform.startswith("win"):
        return True
    return bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))


def get_viewer_runtime() -> dict:
    config = _read_viewer_config()
    env_mode = os.getenv("TMG_VIEWER_MODE", "").strip().lower()
    configured_mode = str(config.get("viewer_mode") or "auto").strip().lower()
    mode = env_mode or configured_mode
    if mode not in ("auto", "streamlit", "desktop"):
        mode = "auto"

    deploy = is_deploy_environment()
    try:
        from core.mode_manager import desktop_runtime_status
        desktop_status = desktop_runtime_status()
    except Exception:
        desktop_status = {"available": False, "engine": "streamlit", "message": "Motor desktop indisponível."}
    desktop_session_available = has_desktop_session()
    desktop_enabled = bool(config.get("enable_desktop_viewer_local", True))
    desktop_available = desktop_session_available and not deploy and bool(desktop_status.get("available"))
    desktop_possible = desktop_available and desktop_enabled
    if deploy and bool(config.get("force_streamlit_in_deploy", True)):
        active_mode = "streamlit"
    elif mode == "desktop" and desktop_possible:
        active_mode = "desktop"
    elif mode == "streamlit":
        active_mode = "streamlit"
    elif mode == "auto" and desktop_possible and not deploy:
        active_mode = "desktop"
    else:
        active_mode = "streamlit"

    return {
        "configured_mode": mode,
        "active_mode": active_mode,
        "is_deploy": deploy,
        "desktop_available": desktop_available,
        "desktop_enabled": desktop_enabled,
        "desktop_engine": str(desktop_status.get("engine", "streamlit")),
        "desktop_status": str(desktop_status.get("message", "")),
        "desktop_accelerated": bool(desktop_status.get("accelerated", False)),
        "streamlit_safe": True,
        "desktop_viewer_max_dim": int(config.get("desktop_viewer_max_dim") or 12000),
        "desktop_viewer_cache_dir": str((PROJECT_ROOT / str(config.get("desktop_viewer_cache_dir") or "tmg_data/desktop_viewer")).resolve()),
        "config_path": str(VIEWER_CONFIG_PATH),
    }
