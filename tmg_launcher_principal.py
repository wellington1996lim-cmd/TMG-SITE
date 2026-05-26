from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


APP_FILENAME = "tmg_app_final.py"
APP_PORT = 8501


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _log(message: str) -> None:
    try:
        log_path = _app_dir() / "tmg_launcher.log"
        with log_path.open("a", encoding="utf-8", errors="ignore") as handle:
            handle.write(message.rstrip() + "\n")
    except Exception:
        pass


def _show_error(message: str) -> None:
    _log("ERRO: " + message)
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("TMG Sistema", message)
        root.destroy()
    except Exception:
        pass


def _port_is_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return True
    except OSError:
        return False


def _python_command() -> list[str] | None:
    configured = os.environ.get("TMG_PYTHON", "").strip()
    if configured:
        return [configured]
    py_launcher = shutil.which("py")
    if py_launcher:
        return [py_launcher, "-3.12"]
    python_exe = shutil.which("python")
    if python_exe:
        return [python_exe]
    python3_exe = shutil.which("python3")
    if python3_exe:
        return [python3_exe]
    return None


def _prepare_environment(app_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    local_dirs = {
        "STREAMLIT_CONFIG_DIR": app_dir / ".streamlit",
        "TMG_APP_ROOT": app_dir,
        "TMG_DATA_DIR": app_dir / "tmg_data",
        "TMG_CONFIG_DIR": app_dir / "tmg_config",
        "YOLO_CONFIG_DIR": app_dir / "Ultralytics",
        "MPLCONFIGDIR": app_dir / "tmg_data" / "matplotlib",
        "TMP": app_dir / "tmg_data" / "tmp",
        "TEMP": app_dir / "tmg_data" / "tmp",
        "TMPDIR": app_dir / "tmg_data" / "tmp",
    }
    for key, path in local_dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_SERVER_PORT"] = str(APP_PORT)
    env["STREAMLIT_BROWSER_SERVER_ADDRESS"] = "localhost"
    env["PYTHONUTF8"] = "1"
    return env


def main() -> int:
    app_dir = _app_dir()
    app_path = app_dir / APP_FILENAME
    if not app_path.exists():
        _show_error(f"Arquivo principal não encontrado:\n{app_path}")
        return 1

    url = f"http://localhost:{APP_PORT}/"
    _log("\n=== Iniciando TMG Sistema ===")
    _log(f"App principal: {app_path}")

    if _port_is_open(APP_PORT):
        _log(f"Porta {APP_PORT} já está ativa. Abrindo navegador em {url}")
        webbrowser.open(url)
        return 0

    py_cmd = _python_command()
    if not py_cmd:
        _show_error("Python 3.12 não foi encontrado. Instale Python 3.12 para abrir o TMG Sistema.")
        return 1

    command = [
        *py_cmd,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(APP_PORT),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    _log("Comando: " + " ".join(command))

    log_file = (app_dir / "tmg_launcher.log").open("a", encoding="utf-8", errors="ignore")
    try:
        subprocess.Popen(
            command,
            cwd=str(app_dir),
            env=_prepare_environment(app_dir),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        log_file.close()
        _show_error(f"Não foi possível iniciar o Streamlit:\n{exc}")
        return 1

    for _ in range(30):
        if _port_is_open(APP_PORT):
            webbrowser.open(url)
            _log(f"Sistema aberto em {url}")
            return 0
        time.sleep(0.5)

    webbrowser.open(url)
    _log(f"Servidor ainda iniciando. Navegador enviado para {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
