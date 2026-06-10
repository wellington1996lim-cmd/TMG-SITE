from __future__ import annotations

import argparse
import json
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
DB_PATH = APP_ROOT / "database" / "app.db"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=20)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def ensure_db() -> None:
    with _connect() as conn:
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


def update_task(
    task_id: str,
    status: str,
    progress: float,
    message: str,
    result: dict | None = None,
    task_type: str = "analise",
    file_path: str = "",
) -> None:
    ensure_db()
    now = _now()
    result_text = json.dumps(result or {}, ensure_ascii=False)
    finish = now if status in {"concluido", "erro", "cancelado"} else ""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO task_status(id_tarefa, tipo_analise, caminho_arquivo, status, progresso, mensagem, resultado, data_inicio, data_fim)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id_tarefa) DO UPDATE SET
                tipo_analise = excluded.tipo_analise,
                caminho_arquivo = excluded.caminho_arquivo,
                status = excluded.status,
                progresso = excluded.progresso,
                mensagem = excluded.mensagem,
                resultado = excluded.resultado,
                data_fim = excluded.data_fim
            """,
            (task_id, task_type, file_path, status, float(progress), message, result_text, now, finish),
        )


def run_placeholder(task_id: str, task_type: str, file_path: str) -> None:
    update_task(task_id, "processando", 5, "Tarefa local iniciada.", task_type=task_type, file_path=file_path)
    for progress in (20, 40, 60, 80):
        time.sleep(0.15)
        update_task(task_id, "processando", progress, "Preparando processamento local.", task_type=task_type, file_path=file_path)
    update_task(
        task_id,
        "concluido",
        100,
        "Base de worker pronta para receber analises pesadas.",
        {"arquivo": file_path},
        task_type=task_type,
        file_path=file_path,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Worker local de analises TMG.")
    parser.add_argument("--task-id", default=str(uuid.uuid4()))
    parser.add_argument("--tipo", default="analise")
    parser.add_argument("--arquivo", default="")
    parser.add_argument("--placeholder", action="store_true")
    args = parser.parse_args()

    ensure_db()
    if args.placeholder:
        run_placeholder(args.task_id, args.tipo, args.arquivo)
    else:
        update_task(args.task_id, "pendente", 0, "Tarefa registrada para processamento local.", task_type=args.tipo, file_path=args.arquivo)
    print(args.task_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
