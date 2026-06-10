from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


APP_NAME = "TMG Sistema de Analise"
DEFAULT_PORT = 8501
PORT_LIMIT = 8525


def _message(title: str, text: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, text)
        root.destroy()
    except Exception:
        print(f"{title}\n{text}")


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _python_command() -> list[str] | None:
    py_launcher = shutil.which("py")
    if py_launcher:
        return [py_launcher, "-3"]

    python = shutil.which("python")
    if python:
        return [python]

    python3 = shutil.which("python3")
    if python3:
        return [python3]

    return None


def _is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def _pick_port() -> int:
    for port in range(DEFAULT_PORT, PORT_LIMIT + 1):
        if _is_port_free(port):
            return port
    raise RuntimeError(f"Nenhuma porta livre entre {DEFAULT_PORT} e {PORT_LIMIT}.")


def main() -> int:
    root = _app_root()
    app_file = root / "tmg_app_final.py"
    if not app_file.exists():
        _message(
            APP_NAME,
            f"Nao encontrei o arquivo do sistema:\n\n{app_file}\n\n"
            "Deixe o executavel na mesma pasta do tmg_app_final.py.",
        )
        return 1

    python_cmd = _python_command()
    if python_cmd is None:
        _message(
            APP_NAME,
            "Python nao foi encontrado no computador.\n\n"
            "Instale o Python ou deixe o comando python disponivel no PATH.",
        )
        return 1

    try:
        port = _pick_port()
    except Exception as exc:
        _message(APP_NAME, str(exc))
        return 1

    data_dir = root / "tmg_data"
    for local_dir in (
        root / ".streamlit",
        root / "tmg_config",
        root / "Ultralytics",
        data_dir,
        data_dir / "tmp",
        data_dir / "matplotlib",
    ):
        local_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "abrir_tmgz.log"

    env = os.environ.copy()
    env.setdefault("TMG_APP_ROOT", str(root))
    env.setdefault("TMG_DATA_DIR", str(data_dir))
    env.setdefault("TMG_CONFIG_DIR", str(root / "tmg_config"))
    env.setdefault("STREAMLIT_CONFIG_DIR", str(root / ".streamlit"))
    env.setdefault("YOLO_CONFIG_DIR", str(root / "Ultralytics"))
    env.setdefault("MPLCONFIGDIR", str(data_dir / "matplotlib"))
    env.setdefault("TMP", str(data_dir / "tmp"))
    env.setdefault("TEMP", str(data_dir / "tmp"))
    env.setdefault("TMPDIR", str(data_dir / "tmp"))

    cmd = [
        *python_cmd,
        "-m",
        "streamlit",
        "run",
        str(app_file),
        "--server.headless=true",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
    ]

    try:
        log_file = log_path.open("a", encoding="utf-8")
        log_file.write(f"\n\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Abrindo sistema\n")
        log_file.flush()

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            cmd,
            cwd=str(root),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except Exception as exc:
        _message(APP_NAME, f"Nao consegui iniciar o Streamlit:\n\n{exc}")
        return 1

    url = f"http://localhost:{port}"
    if os.environ.get("TMG_LAUNCHER_NO_BROWSER") != "1":
        time.sleep(2)
        webbrowser.open(url)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
