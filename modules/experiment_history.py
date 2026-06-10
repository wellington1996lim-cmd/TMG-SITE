from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = APP_ROOT / "database" / "app.db"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_experiment_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ensaios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_ensaio TEXT,
                nome_area TEXT,
                fazenda TEXT,
                talhao TEXT,
                quadra TEXT,
                cultura TEXT,
                safra TEXT,
                data_plantio TEXT,
                data_criacao TEXT,
                area_m2 REAL,
                area_ha REAL,
                perimetro_m REAL,
                total_tiros INTEGER,
                total_disparos INTEGER,
                total_parcelas INTEGER,
                materiais_plantados TEXT,
                observacao TEXT,
                status TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS parcelas_ensaio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ensaio_id INTEGER,
                parcela TEXT,
                tiro INTEGER,
                disparo INTEGER,
                material TEXT,
                tratamento TEXT,
                repeticao TEXT,
                bloco TEXT,
                area_m2 REAL,
                latitude_centro REAL,
                longitude_centro REAL,
                coordenadas_geojson TEXT,
                observacao TEXT,
                FOREIGN KEY(ensaio_id) REFERENCES ensaios(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS geometrias_ensaio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ensaio_id INTEGER,
                tipo TEXT,
                geojson TEXT,
                kml TEXT,
                data_criacao TEXT,
                FOREIGN KEY(ensaio_id) REFERENCES ensaios(id) ON DELETE CASCADE
            )
            """
        )


def _materials_summary(parcels: list[dict[str, Any]]) -> str:
    materials = sorted({str(p.get("material") or "").strip() for p in parcels if str(p.get("material") or "").strip()})
    return ", ".join(materials)


def save_experiment(
    summary: dict[str, Any],
    parcels: list[dict[str, Any]],
    area_geojson: dict[str, Any] | None,
    parcels_geojson: dict[str, Any] | None,
    kml: str = "",
) -> int:
    init_experiment_db()
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO ensaios (
                nome_ensaio, nome_area, fazenda, talhao, quadra, cultura, safra, data_plantio,
                data_criacao, area_m2, area_ha, perimetro_m, total_tiros, total_disparos,
                total_parcelas, materiais_plantados, observacao, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary.get("nome_ensaio", ""),
                summary.get("nome_area", ""),
                summary.get("fazenda", ""),
                summary.get("talhao", ""),
                summary.get("quadra", ""),
                summary.get("cultura", ""),
                summary.get("safra", ""),
                summary.get("data_plantio", ""),
                summary.get("data_criacao", now) or now,
                float(summary.get("area_m2") or 0),
                float(summary.get("area_ha") or 0),
                float(summary.get("perimetro_m") or 0),
                int(summary.get("total_tiros") or 0),
                int(summary.get("total_disparos") or 0),
                int(summary.get("total_parcelas") or len(parcels)),
                _materials_summary(parcels),
                summary.get("observacao", ""),
                summary.get("status", "Planejado"),
            ),
        )
        ensaio_id = int(cur.lastrowid)
        for parcel in parcels:
            conn.execute(
                """
                INSERT INTO parcelas_ensaio (
                    ensaio_id, parcela, tiro, disparo, material, tratamento, repeticao, bloco,
                    area_m2, latitude_centro, longitude_centro, coordenadas_geojson, observacao
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ensaio_id,
                    parcel.get("parcela", ""),
                    int(parcel.get("tiro") or 0),
                    int(parcel.get("disparo") or 0),
                    parcel.get("material", ""),
                    parcel.get("tratamento", ""),
                    parcel.get("repeticao", ""),
                    parcel.get("bloco", ""),
                    float(parcel.get("area_m2") or 0),
                    float(parcel.get("latitude_centro") or 0),
                    float(parcel.get("longitude_centro") or 0),
                    json.dumps(parcel.get("geojson") or {}, ensure_ascii=False),
                    parcel.get("observacao", ""),
                ),
            )
        conn.execute(
            "INSERT INTO geometrias_ensaio(ensaio_id, tipo, geojson, kml, data_criacao) VALUES (?, ?, ?, ?, ?)",
            (ensaio_id, "area", json.dumps(area_geojson or {}, ensure_ascii=False), kml or "", now),
        )
        conn.execute(
            "INSERT INTO geometrias_ensaio(ensaio_id, tipo, geojson, kml, data_criacao) VALUES (?, ?, ?, ?, ?)",
            (ensaio_id, "parcelas", json.dumps(parcels_geojson or {}, ensure_ascii=False), "", now),
        )
    return ensaio_id


def list_experiments(filters: dict[str, Any] | None = None) -> pd.DataFrame:
    init_experiment_db()
    filters = filters or {}
    clauses = []
    values: list[Any] = []
    for field in ("cultura", "safra", "fazenda", "talhao", "quadra"):
        value = str(filters.get(field) or "").strip()
        if value:
            clauses.append(f"{field} LIKE ?")
            values.append(f"%{value}%")
    sql = "SELECT * FROM ensaios"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id DESC"
    with _connect() as conn:
        return pd.read_sql_query(sql, conn, params=values)


def load_experiment(ensaio_id: int) -> dict[str, Any]:
    init_experiment_db()
    with _connect() as conn:
        summary = conn.execute("SELECT * FROM ensaios WHERE id = ?", (int(ensaio_id),)).fetchone()
        if not summary:
            raise ValueError("Ensaio não encontrado.")
        parcel_rows = conn.execute("SELECT * FROM parcelas_ensaio WHERE ensaio_id = ? ORDER BY disparo, tiro", (int(ensaio_id),)).fetchall()
        geo_rows = conn.execute("SELECT * FROM geometrias_ensaio WHERE ensaio_id = ? ORDER BY id", (int(ensaio_id),)).fetchall()
    parcels = []
    for row in parcel_rows:
        item = dict(row)
        try:
            item["geojson"] = json.loads(item.pop("coordenadas_geojson") or "{}")
        except Exception:
            item["geojson"] = {}
        parcels.append(item)
    geometries = {}
    for row in geo_rows:
        data = dict(row)
        try:
            data["geojson_obj"] = json.loads(data.get("geojson") or "{}")
        except Exception:
            data["geojson_obj"] = {}
        geometries[data.get("tipo") or f"geom_{data.get('id')}"] = data
    return {"summary": dict(summary), "parcels": parcels, "geometries": geometries}


def delete_experiment(ensaio_id: int) -> None:
    init_experiment_db()
    with _connect() as conn:
        conn.execute("DELETE FROM parcelas_ensaio WHERE ensaio_id = ?", (int(ensaio_id),))
        conn.execute("DELETE FROM geometrias_ensaio WHERE ensaio_id = ?", (int(ensaio_id),))
        conn.execute("DELETE FROM ensaios WHERE id = ?", (int(ensaio_id),))


def duplicate_experiment(ensaio_id: int) -> int:
    data = load_experiment(ensaio_id)
    summary = data["summary"]
    summary["nome_ensaio"] = f"{summary.get('nome_ensaio') or 'Ensaio'} - Cópia"
    summary["data_criacao"] = _now()
    area_geojson = data["geometries"].get("area", {}).get("geojson_obj", {})
    parcels_geojson = data["geometries"].get("parcelas", {}).get("geojson_obj", {})
    kml = data["geometries"].get("area", {}).get("kml", "")
    return save_experiment(summary, data["parcels"], area_geojson, parcels_geojson, kml)
