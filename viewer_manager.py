from __future__ import annotations

import hashlib
import html
import os
import subprocess
import sys
from pathlib import Path

from config_app import PROJECT_ROOT, get_viewer_runtime


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".geotiff",
    ".jp2",
    ".bmp",
    ".webp",
}


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix in IMAGE_EXTENSIONS else ".png"


def _safe_stem(filename: str) -> str:
    stem = Path(filename or "ortofoto").stem
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in stem).strip("_")
    return cleaned or "ortofoto"


def is_desktop_viewer_enabled() -> bool:
    runtime = get_viewer_runtime()
    return runtime.get("active_mode") == "desktop" and bool(runtime.get("desktop_available"))


def prepare_desktop_viewer_cache(file_bytes: bytes, filename: str, app_root: str | Path | None = None) -> Path | None:
    if not is_desktop_viewer_enabled() or not file_bytes:
        return None
    return save_image_for_desktop_viewer(file_bytes, filename, app_root=app_root)


def save_image_for_desktop_viewer(file_bytes: bytes, filename: str, app_root: str | Path | None = None) -> Path:
    root = Path(app_root or PROJECT_ROOT).resolve()
    runtime = get_viewer_runtime()
    cache_dir = Path(runtime.get("desktop_viewer_cache_dir") or root / "tmg_data" / "desktop_viewer")
    if not cache_dir.is_absolute():
        cache_dir = root / cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha1()
    digest.update(str(filename or "").encode("utf-8", errors="ignore"))
    digest.update(str(len(file_bytes or b"")).encode("ascii"))
    digest.update((file_bytes or b"")[:1024 * 1024])
    if len(file_bytes or b"") > 1024 * 1024:
        digest.update((file_bytes or b"")[-1024 * 1024:])
    safe_name = f"{_safe_stem(filename)}_{digest.hexdigest()[:16]}{_safe_suffix(filename)}"
    target = cache_dir / safe_name
    if not target.exists() or target.stat().st_size != len(file_bytes or b""):
        target.write_bytes(file_bytes or b"")
    cleanup_desktop_viewer_cache(cache_dir, keep_path=target)
    return target


def cleanup_desktop_viewer_cache(cache_dir: str | Path, keep_path: str | Path | None = None, max_files: int = 4, max_bytes: int = 420 * 1024 * 1024) -> None:
    try:
        root = Path(cache_dir)
        root.mkdir(parents=True, exist_ok=True)
        keep = Path(keep_path).resolve() if keep_path else None
        files = sorted(
            [item for item in root.iterdir() if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        total = sum(item.stat().st_size for item in files)
        for index, item in enumerate(files):
            try:
                if keep and item.resolve() == keep:
                    continue
                if index >= max_files or total > max_bytes:
                    size = item.stat().st_size
                    item.unlink(missing_ok=True)
                    total -= size
            except Exception:
                pass
    except Exception:
        pass


def launch_desktop_viewer(image_path: str | Path, app_root: str | Path | None = None) -> tuple[bool, str]:
    if not is_desktop_viewer_enabled():
        return False, "Visualizador local indisponivel neste ambiente. Usando visualizador Streamlit."

    root = Path(app_root or PROJECT_ROOT).resolve()
    try:
        from core.desktop_viewer_engine import launch_desktop_viewer as _launch_desktop_engine

        ok, message = _launch_desktop_engine(image_path, app_root=root)
        if ok:
            return ok, message
    except Exception:
        pass

    script = root / "viewers" / "desktop_viewer.py"
    if not script.exists():
        return False, f"Arquivo do visualizador local nao encontrado: {script}"

    try:
        subprocess.Popen(
            [sys.executable, str(script), str(Path(image_path).resolve())],
            cwd=str(root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True, "Visualizador local aberto em uma janela externa."
    except Exception as exc:
        return False, f"Nao foi possivel abrir o visualizador local: {exc}"


def render_desktop_viewer_controls(file_bytes: bytes, filename: str, key: str, app_root: str | Path | None = None) -> None:
    if not is_desktop_viewer_enabled() or not file_bytes:
        return
    try:
        import streamlit as st
    except Exception:
        return

    runtime = get_viewer_runtime()
    image_path = save_image_for_desktop_viewer(file_bytes, filename, app_root=app_root)
    safe_name = html.escape(Path(filename or image_path.name).name)
    safe_path = html.escape(str(image_path))
    engine_label = html.escape(str(runtime.get("desktop_engine") or "desktop"))
    status_label = html.escape(str(runtime.get("desktop_status") or "Modo Desktop Local disponivel."))
    accelerated_label = "Acelerado" if bool(runtime.get("desktop_accelerated")) else "Fallback seguro"
    with st.expander("Modo Desktop Local (opcional)", expanded=False):
        st.markdown(
            f"""
            <div style="
                border:1px solid rgba(0,229,255,.38);
                border-radius:14px;
                padding:12px 14px;
                background:linear-gradient(145deg, rgba(2,14,36,.94), rgba(13,43,69,.82));
                color:#ffffff;
                box-shadow:0 12px 26px rgba(0,0,0,.30), 0 0 18px rgba(0,229,255,.16);
                font-weight:800;">
                Modo local detectado: voce pode abrir <b>{safe_name}</b> em uma janela externa mais fluida.
                <div style="margin-top:6px;color:#dffbff;font-size:.78rem;word-break:break-word;">{safe_path}</div>
                <div style="margin-top:4px;color:#9eefff;font-size:.75rem;">Motor: {engine_label} · {accelerated_label}</div>
                <div style="margin-top:4px;color:#c9f7ff;font-size:.75rem;">{status_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Abrir visualizador local", key=key, use_container_width=True):
            ok, message = launch_desktop_viewer(image_path, app_root=app_root)
            if ok:
                st.success(message)
            else:
                st.warning(message)
