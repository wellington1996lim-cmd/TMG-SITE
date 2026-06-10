from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable


LOCAL_FOLDERS = (
    "data/uploads",
    "data/ortofotos",
    "data/tiles",
    "data/resultados",
    "data/exports",
    "data/modelos",
    "data/status",
    "data/cache",
    "database",
    "logs",
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_root(app_root: Path | str) -> Path:
    return Path(app_root).resolve()


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=20)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def ensure_local_performance_layout(app_root: Path | str) -> dict:
    root = _safe_root(app_root)
    created = {}
    for relative in LOCAL_FOLDERS:
        path = root / relative
        path.mkdir(parents=True, exist_ok=True)
        created[relative] = str(path)

    db_path = root / "database" / "app.db"
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_status (
                id_tarefa TEXT PRIMARY KEY,
                tipo_analise TEXT,
                caminho_arquivo TEXT,
                status TEXT,
                progresso REAL DEFAULT 0,
                mensagem TEXT,
                resultado TEXT,
                data_inicio TEXT,
                data_fim TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ortho_cache (
                file_hash TEXT PRIMARY KEY,
                filename TEXT,
                path TEXT,
                preview_path TEXT,
                meta_path TEXT,
                size_bytes INTEGER DEFAULT 0,
                mtime REAL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                event TEXT,
                message TEXT,
                created_at TEXT
            )
            """
        )

    return {
        "root": str(root),
        "database": str(db_path),
        "folders": created,
    }


def fast_file_fingerprint(file_bytes: bytes, filename: str = "", extra: str = "") -> str:
    data = file_bytes or b""
    hasher = hashlib.sha1()
    hasher.update(str(filename or "").encode("utf-8", errors="ignore"))
    hasher.update(str(extra or "").encode("utf-8", errors="ignore"))
    hasher.update(str(len(data)).encode("ascii"))
    if not data:
        return hasher.hexdigest()

    sample = 4 * 1024 * 1024
    hasher.update(data[:sample])
    if len(data) > sample * 2:
        mid = max(0, (len(data) // 2) - (sample // 2))
        hasher.update(data[mid : mid + sample])
    if len(data) > sample:
        hasher.update(data[-sample:])
    return hasher.hexdigest()


def _env_int(name: str, default: int, min_value: int, max_value: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        value = int(raw) if raw else int(default)
    except Exception:
        value = int(default)
    return max(min_value, min(max_value, value))


def local_cache_limits() -> tuple[int, int]:
    max_files = _env_int("TMG_ORTHO_DISK_CACHE_FILES", 96, 12, 500)
    max_gb = _env_int("TMG_ORTHO_DISK_CACHE_GB", 5, 1, 50)
    return max_files, max_gb * 1024 * 1024 * 1024


def cleanup_file_cache(
    cache_dir: Path | str,
    pattern: str = "*.jpg",
    sidecar_suffixes: Iterable[str] = (".json",),
    max_files: int | None = None,
    max_bytes: int | None = None,
) -> None:
    directory = Path(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    if max_files is None or max_bytes is None:
        default_files, default_bytes = local_cache_limits()
        max_files = default_files if max_files is None else max_files
        max_bytes = default_bytes if max_bytes is None else max_bytes

    files = sorted(
        [p for p in directory.glob(pattern) if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    total = sum(p.stat().st_size for p in files)
    for index, path in enumerate(files):
        if index < max_files and total <= max_bytes:
            continue
        try:
            size = path.stat().st_size
            path.unlink(missing_ok=True)
            total -= size
            for suffix in sidecar_suffixes:
                path.with_suffix(suffix).unlink(missing_ok=True)
        except Exception:
            pass


def write_app_log(app_root: Path | str, event: str, message: str, level: str = "INFO") -> None:
    root = _safe_root(app_root)
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {
            "created_at": _now(),
            "level": level,
            "event": event,
            "message": message,
        },
        ensure_ascii=False,
    )
    try:
        with (logs_dir / "app.log").open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        return

    db_path = root / "database" / "app.db"
    if db_path.exists():
        try:
            with _connect(db_path) as conn:
                conn.execute(
                    "INSERT INTO app_events(level, event, message, created_at) VALUES (?, ?, ?, ?)",
                    (level, event, message, _now()),
                )
        except Exception:
            pass


def upsert_ortho_cache_record(
    app_root: Path | str,
    file_hash: str,
    filename: str,
    preview_path: Path | str,
    meta_path: Path | str,
    size_bytes: int,
) -> None:
    root = _safe_root(app_root)
    db_path = root / "database" / "app.db"
    if not db_path.exists():
        return
    now = _now()
    try:
        with _connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO ortho_cache(file_hash, filename, path, preview_path, meta_path, size_bytes, mtime, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_hash) DO UPDATE SET
                    filename = excluded.filename,
                    preview_path = excluded.preview_path,
                    meta_path = excluded.meta_path,
                    size_bytes = excluded.size_bytes,
                    mtime = excluded.mtime,
                    updated_at = excluded.updated_at
                """,
                (
                    file_hash,
                    filename,
                    "",
                    str(preview_path),
                    str(meta_path),
                    int(size_bytes or 0),
                    time.time(),
                    now,
                    now,
                ),
            )
    except Exception:
        pass
