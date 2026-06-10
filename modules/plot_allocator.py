from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from pyproj import CRS, Transformer
from shapely.geometry import Polygon, mapping, shape
from shapely.ops import transform as shapely_transform


@dataclass(frozen=True)
class MetricContext:
    polygon_ll: Polygon
    polygon_m: Polygon
    to_m: Transformer
    to_ll: Transformer
    crs_m: CRS


def utm_crs_for_lonlat(lon: float, lat: float) -> CRS:
    zone = int((float(lon) + 180.0) // 6.0) + 1
    zone = max(1, min(60, zone))
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return CRS.from_epsg(epsg)


def _as_polygon(area_geojson: dict[str, Any]) -> Polygon:
    if not area_geojson:
        raise ValueError("Desenhe uma área no mapa para calcular.")
    geom = area_geojson.get("geometry", area_geojson)
    polygon = shape(geom)
    if polygon.geom_type == "MultiPolygon":
        polygon = max(list(polygon.geoms), key=lambda g: g.area)
    if polygon.geom_type != "Polygon":
        raise ValueError("A geometria da área precisa ser um polígono.")
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    if polygon.is_empty:
        raise ValueError("O polígono desenhado é inválido.")
    return polygon


def build_metric_context(area_geojson: dict[str, Any]) -> MetricContext:
    polygon_ll = _as_polygon(area_geojson)
    centroid = polygon_ll.centroid
    crs_m = utm_crs_for_lonlat(centroid.x, centroid.y)
    to_m = Transformer.from_crs("EPSG:4326", crs_m, always_xy=True)
    to_ll = Transformer.from_crs(crs_m, "EPSG:4326", always_xy=True)
    polygon_m = shapely_transform(lambda x, y, z=None: to_m.transform(x, y), polygon_ll)
    if not polygon_m.is_valid:
        polygon_m = polygon_m.buffer(0)
    return MetricContext(polygon_ll=polygon_ll, polygon_m=polygon_m, to_m=to_m, to_ll=to_ll, crs_m=crs_m)


def calculate_area_metrics(area_geojson: dict[str, Any]) -> dict[str, Any]:
    ctx = build_metric_context(area_geojson)
    centroid_ll = ctx.polygon_ll.centroid
    return {
        "area_m2": float(ctx.polygon_m.area),
        "area_ha": float(ctx.polygon_m.area / 10000.0),
        "perimeter_m": float(ctx.polygon_m.length),
        "centroid_lat": float(centroid_ll.y),
        "centroid_lon": float(centroid_ll.x),
        "crs": ctx.crs_m.to_string(),
        "geojson": mapping(ctx.polygon_ll),
    }


def _linspace(start: float, stop: float, count: int) -> list[float]:
    if count <= 1 or abs(stop - start) < 1e-9:
        return [start]
    step = (stop - start) / (count - 1)
    return [start + i * step for i in range(count)]


def _local_axes(degrees: float) -> tuple[tuple[float, float], tuple[float, float]]:
    theta = math.radians(float(degrees or 0))
    ux = (math.cos(theta), math.sin(theta))
    uy = (-math.sin(theta), math.cos(theta))
    return ux, uy


def _parcel_polygon_from_local(
    anchor_x: float,
    anchor_y: float,
    col: int,
    row: int,
    width: float,
    length: float,
    gap: float,
    block_gap: float,
    ux: tuple[float, float],
    uy: tuple[float, float],
    origin_x: float,
    origin_y: float,
) -> Polygon:
    x0 = anchor_x + col * (width + gap)
    y0 = anchor_y + row * (length + gap + block_gap)
    local_points = ((x0, y0), (x0 + width, y0), (x0 + width, y0 + length), (x0, y0 + length))
    points = []
    for lx, ly in local_points:
        x = origin_x + ux[0] * lx + uy[0] * ly
        y = origin_y + ux[1] * lx + uy[1] * ly
        points.append((x, y))
    return Polygon(points)


def _to_local_bounds(polygon_m: Polygon, ux: tuple[float, float], uy: tuple[float, float], origin: tuple[float, float]) -> tuple[float, float, float, float]:
    values_x = []
    values_y = []
    ox, oy = origin
    for x, y in polygon_m.exterior.coords:
        dx = x - ox
        dy = y - oy
        values_x.append(dx * ux[0] + dy * ux[1])
        values_y.append(dx * uy[0] + dy * uy[1])
    return min(values_x), min(values_y), max(values_x), max(values_y)


def allocate_parcels(area_geojson: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    ctx = build_metric_context(area_geojson)
    length = max(0.1, float(params.get("comprimento_m") or 0))
    width = max(0.1, float(params.get("largura_m") or 0))
    gap = max(0.0, float(params.get("espacamento_m") or 0))
    block_gap = max(0.0, float(params.get("corredor_m") or 0))
    tiros = max(1, int(params.get("tiros") or 1))
    disparos = max(1, int(params.get("disparos") or 1))
    orientation = float(params.get("orientacao_graus") or 0)

    ux, uy = _local_axes(orientation)
    centroid = ctx.polygon_m.centroid
    origin = (centroid.x, centroid.y)
    min_lx, min_ly, max_lx, max_ly = _to_local_bounds(ctx.polygon_m, ux, uy, origin)
    total_w = tiros * width + max(0, tiros - 1) * gap
    total_h = disparos * length + max(0, disparos - 1) * (gap + block_gap)
    if total_w <= 0 or total_h <= 0:
        raise ValueError("Dimensões das parcelas inválidas.")

    start_x_min = min_lx
    start_x_max = max_lx - total_w
    start_y_min = min_ly
    start_y_max = max_ly - total_h
    if start_x_max < start_x_min:
        start_x_candidates = [(min_lx + max_lx - total_w) / 2]
    else:
        start_x_candidates = _linspace(start_x_min, start_x_max, min(17, max(3, tiros + 3)))
    if start_y_max < start_y_min:
        start_y_candidates = [(min_ly + max_ly - total_h) / 2]
    else:
        start_y_candidates = _linspace(start_y_min, start_y_max, min(17, max(3, disparos + 3)))

    area_check = ctx.polygon_m.buffer(0.03)
    best: dict[str, Any] | None = None
    planned = tiros * disparos
    for anchor_y in start_y_candidates:
        for anchor_x in start_x_candidates:
            kept = []
            for row in range(disparos):
                for col in range(tiros):
                    poly = _parcel_polygon_from_local(anchor_x, anchor_y, col, row, width, length, gap, block_gap, ux, uy, origin[0], origin[1])
                    if area_check.contains(poly):
                        kept.append((row, col, poly))
            if best is None or len(kept) > len(best["kept"]):
                best = {"anchor_x": anchor_x, "anchor_y": anchor_y, "kept": kept}
            if len(kept) == planned:
                break
        if best and len(best["kept"]) == planned:
            break

    kept = best["kept"] if best else []
    records = []
    for row, col, poly_m in kept:
        poly_ll = shapely_transform(lambda x, y, z=None: ctx.to_ll.transform(x, y), poly_m)
        center_ll = poly_ll.centroid
        tiro = col + 1
        disparo = row + 1
        records.append(
            {
                "parcela": f"T{tiro} D{disparo}",
                "tiro": tiro,
                "disparo": disparo,
                "material": "",
                "tratamento": "",
                "repeticao": "",
                "bloco": "",
                "observacao": "",
                "area_m2": float(poly_m.area),
                "latitude_centro": float(center_ll.y),
                "longitude_centro": float(center_ll.x),
                "geojson": mapping(poly_ll),
            }
        )

    occupied = sum(float(item["area_m2"]) for item in records)
    area_total = float(ctx.polygon_m.area)
    return {
        "parcels": records,
        "metrics": {
            "planned": planned,
            "allocated": len(records),
            "missing": max(0, planned - len(records)),
            "parcel_area_m2": length * width,
            "occupied_area_m2": occupied,
            "free_area_m2": max(0.0, area_total - occupied),
            "use_percent": (occupied / area_total * 100.0) if area_total > 0 else 0.0,
            "area_m2": area_total,
            "area_ha": area_total / 10000.0,
            "perimeter_m": float(ctx.polygon_m.length),
            "tiros": tiros,
            "disparos": disparos,
            "crs": ctx.crs_m.to_string(),
        },
    }
