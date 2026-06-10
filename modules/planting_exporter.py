from __future__ import annotations

import csv
import io
import json
import math
from datetime import date
from typing import Any

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ESRI_WORLD_IMAGERY_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"


def build_feature_collection(area_geojson: dict[str, Any] | None, parcels: list[dict[str, Any]]) -> dict[str, Any]:
    features = []
    if area_geojson:
        features.append(
            {
                "type": "Feature",
                "properties": {"tipo": "area"},
                "geometry": area_geojson.get("geometry", area_geojson),
            }
        )
    for parcel in parcels:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "tipo": "parcela",
                    "parcela": parcel.get("parcela", ""),
                    "tiro": parcel.get("tiro", ""),
                    "disparo": parcel.get("disparo", ""),
                    "material": parcel.get("material", ""),
                    "tratamento": parcel.get("tratamento", ""),
                    "repeticao": parcel.get("repeticao", ""),
                    "bloco": parcel.get("bloco", ""),
                    "observacao": parcel.get("observacao", ""),
                    "area_m2": parcel.get("area_m2", 0),
                },
                "geometry": parcel.get("geojson", {}),
            }
        )
    return {"type": "FeatureCollection", "features": features}


def geojson_bytes(area_geojson: dict[str, Any] | None, parcels: list[dict[str, Any]]) -> bytes:
    return json.dumps(build_feature_collection(area_geojson, parcels), ensure_ascii=False, indent=2).encode("utf-8")


def _coords_from_geometry(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    geom = geometry.get("geometry", geometry) if geometry else {}
    coords = geom.get("coordinates") or []
    if geom.get("type") == "Polygon" and coords:
        return [(float(lon), float(lat)) for lon, lat, *_ in coords[0]]
    return []


def _kml_polygon(name: str, geometry: dict[str, Any], style_url: str, description: str = "") -> str:
    coords = _coords_from_geometry(geometry)
    if not coords:
        return ""
    coord_text = " ".join(f"{lon:.9f},{lat:.9f},0" for lon, lat in coords)
    return f"""
    <Placemark>
      <name>{_xml(name)}</name>
      <description>{_xml(description)}</description>
      <styleUrl>#{style_url}</styleUrl>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>{coord_text}</coordinates></LinearRing></outerBoundaryIs></Polygon>
    </Placemark>"""


def _xml(value: Any) -> str:
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")


def kml_bytes(summary: dict[str, Any], area_geojson: dict[str, Any] | None, parcels: list[dict[str, Any]]) -> bytes:
    description = (
        f"Área m²: {summary.get('area_m2', 0):.2f}\n"
        f"Área ha: {summary.get('area_ha', 0):.4f}\n"
        f"Perímetro m: {summary.get('perimetro_m', 0):.2f}\n"
        f"Cultura: {summary.get('cultura', '')}\n"
        f"Safra: {summary.get('safra', '')}"
    )
    placemarks = [_kml_polygon(summary.get("nome_area") or "Area TMG", area_geojson or {}, "areaStyle", description)]
    for parcel in parcels:
        desc = "\n".join(
            [
                f"Material: {parcel.get('material', '')}",
                f"Tratamento: {parcel.get('tratamento', '')}",
                f"Repetição: {parcel.get('repeticao', '')}",
                f"Bloco: {parcel.get('bloco', '')}",
            ]
        )
        placemarks.append(_kml_polygon(parcel.get("parcela", "Parcela"), parcel.get("geojson", {}), "parcelStyle", desc))
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{_xml(summary.get('nome_ensaio') or 'Ensaio TMG')}</name>
    <Style id="areaStyle">
      <LineStyle><color>ff00e5ff</color><width>3</width></LineStyle>
      <PolyStyle><color>3300e5ff</color></PolyStyle>
    </Style>
    <Style id="parcelStyle">
      <LineStyle><color>ff1c9fff</color><width>2</width></LineStyle>
      <PolyStyle><color>221c9fff</color></PolyStyle>
    </Style>
    {''.join(placemarks)}
  </Document>
</kml>"""
    return content.encode("utf-8")


def parcels_csv_bytes(parcels: list[dict[str, Any]]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Parcela", "Tiro", "Disparo", "Material", "Tratamento", "Repetição", "Bloco", "Área m²", "Latitude centro", "Longitude centro", "Observação"])
    for item in parcels:
        writer.writerow(
            [
                item.get("parcela", ""),
                item.get("tiro", ""),
                item.get("disparo", ""),
                item.get("material", ""),
                item.get("tratamento", ""),
                item.get("repeticao", ""),
                item.get("bloco", ""),
                item.get("area_m2", 0),
                item.get("latitude_centro", ""),
                item.get("longitude_centro", ""),
                item.get("observacao", ""),
            ]
        )
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def excel_bytes(summary: dict[str, Any], parcels: list[dict[str, Any]], history_df: pd.DataFrame | None = None) -> bytes:
    buffer = io.BytesIO()
    df_parcels = pd.DataFrame(parcels)
    if df_parcels.empty:
        df_parcels = pd.DataFrame(columns=["parcela", "tiro", "disparo", "material", "tratamento", "repeticao", "bloco", "area_m2", "latitude_centro", "longitude_centro", "observacao"])
    resumo = pd.DataFrame(
        [
            {
                "Nome do ensaio": summary.get("nome_ensaio", ""),
                "Nome da área": summary.get("nome_area", ""),
                "Fazenda": summary.get("fazenda", ""),
                "Talhão": summary.get("talhao", ""),
                "Quadra": summary.get("quadra", ""),
                "Cultura": summary.get("cultura", ""),
                "Safra": summary.get("safra", ""),
                "Data do plantio": summary.get("data_plantio", ""),
                "Área m²": summary.get("area_m2", 0),
                "Área ha": summary.get("area_ha", 0),
                "Perímetro": summary.get("perimetro_m", 0),
                "Total de tiros": summary.get("total_tiros", 0),
                "Total de disparos": summary.get("total_disparos", 0),
                "Total de parcelas": summary.get("total_parcelas", 0),
                "Observação": summary.get("observacao", ""),
            }
        ]
    )
    mapa_rows = []
    if not df_parcels.empty and {"disparo", "tiro"}.issubset(df_parcels.columns):
        for disparo in sorted(df_parcels["disparo"].dropna().unique()):
            row = {"Disparo": disparo}
            subset = df_parcels[df_parcels["disparo"] == disparo]
            for _, item in subset.sort_values("tiro").iterrows():
                row[f"T{int(item['tiro'])}"] = "\n".join(
                    str(v or "")
                    for v in (item.get("parcela", ""), item.get("material", ""), item.get("tratamento", ""), item.get("repeticao", ""))
                    if str(v or "").strip()
                )
            mapa_rows.append(row)
    mapa = pd.DataFrame(mapa_rows)
    materiais = (
        df_parcels.groupby(["material", "tratamento", "repeticao", "bloco"], dropna=False)
        .size()
        .reset_index(name="Quantidade de parcelas")
        .rename(columns={"material": "Material", "tratamento": "Tratamento", "repeticao": "Repetição", "bloco": "Bloco"})
    )
    dados = df_parcels.rename(
        columns={
            "parcela": "Parcela",
            "tiro": "Tiro",
            "disparo": "Disparo",
            "material": "Material",
            "tratamento": "Tratamento",
            "repeticao": "Repetição",
            "bloco": "Bloco",
            "area_m2": "Área m²",
            "latitude_centro": "Latitude centro",
            "longitude_centro": "Longitude centro",
            "geojson": "Coordenadas",
            "observacao": "Observação",
        }
    )
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        resumo.to_excel(writer, sheet_name="RESUMO", index=False)
        mapa.to_excel(writer, sheet_name="MAPA_PLANTIO", index=False)
        dados.to_excel(writer, sheet_name="DADOS_PARCELAS", index=False)
        materiais.to_excel(writer, sheet_name="MATERIAIS", index=False)
        (history_df if history_df is not None else pd.DataFrame()).to_excel(writer, sheet_name="HISTÓRICO", index=False)
    return buffer.getvalue()


def _lonlat_to_pixel(lon: float, lat: float, zoom: int) -> tuple[float, float]:
    lat = max(min(lat, 85.05112878), -85.05112878)
    sin_lat = math.sin(math.radians(lat))
    scale = 256 * (2**zoom)
    x = (lon + 180.0) / 360.0 * scale
    y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * scale
    return x, y


def _fetch_tile(url: str, z: int, x: int, y: int) -> Image.Image:
    import requests

    response = requests.get(url.format(z=z, x=x, y=y), timeout=8)
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGB")


def _all_lonlat(area_geojson: dict[str, Any] | None, parcels: list[dict[str, Any]]) -> list[tuple[float, float]]:
    coords = _coords_from_geometry(area_geojson or {})
    for parcel in parcels:
        coords.extend(_coords_from_geometry(parcel.get("geojson", {})))
    return coords


def map_png_bytes(
    summary: dict[str, Any],
    area_geojson: dict[str, Any] | None,
    parcels: list[dict[str, Any]],
    tile_url: str = ESRI_WORLD_IMAGERY_URL,
) -> bytes:
    width, height = 2400, 1600
    header_h, footer_h, legend_w = 130, 78, 390
    margin = 34
    map_box = (margin, header_h + margin, width - legend_w - margin * 2, height - footer_h - margin)
    map_w = map_box[2] - map_box[0]
    map_h = map_box[3] - map_box[1]
    image = Image.new("RGB", (width, height), "#020e24")
    draw = ImageDraw.Draw(image, "RGBA")
    font_big = ImageFont.truetype("arial.ttf", 42) if _has_arial() else ImageFont.load_default()
    font_med = ImageFont.truetype("arial.ttf", 24) if _has_arial() else ImageFont.load_default()
    font_small = ImageFont.truetype("arial.ttf", 18) if _has_arial() else ImageFont.load_default()

    draw.rectangle((0, 0, width, header_h), fill=(3, 24, 48, 255))
    draw.text((44, 28), str(summary.get("nome_ensaio") or "Mapa de Plantio TMG"), fill=(255, 255, 255, 255), font=font_big)
    draw.text((44, 86), f"{summary.get('fazenda','')} · {summary.get('cultura','')} · Safra {summary.get('safra','')}", fill=(190, 245, 255, 255), font=font_med)

    coords = _all_lonlat(area_geojson, parcels)
    if coords:
        min_lon = min(c[0] for c in coords)
        max_lon = max(c[0] for c in coords)
        min_lat = min(c[1] for c in coords)
        max_lat = max(c[1] for c in coords)
    else:
        min_lon, max_lon, min_lat, max_lat = -55.73, -55.71, -12.56, -12.54

    zoom = 19
    base = None
    crop_origin = (0.0, 0.0)
    scale_x = scale_y = 1.0
    for z in range(19, 14, -1):
        px_min, py_max = _lonlat_to_pixel(min_lon, min_lat, z)
        px_max, py_min = _lonlat_to_pixel(max_lon, max_lat, z)
        pad = 180
        x0, y0 = int(min(px_min, px_max) - pad), int(min(py_min, py_max) - pad)
        x1, y1 = int(max(px_min, px_max) + pad), int(max(py_min, py_max) + pad)
        tx0, ty0 = x0 // 256, y0 // 256
        tx1, ty1 = x1 // 256, y1 // 256
        if (tx1 - tx0 + 1) * (ty1 - ty0 + 1) > 96:
            continue
        try:
            mosaic = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256), "#102030")
            for tx in range(tx0, tx1 + 1):
                for ty in range(ty0, ty1 + 1):
                    tile = _fetch_tile(tile_url, z, tx, ty)
                    mosaic.paste(tile, ((tx - tx0) * 256, (ty - ty0) * 256))
            crop = mosaic.crop((x0 - tx0 * 256, y0 - ty0 * 256, x1 - tx0 * 256, y1 - ty0 * 256))
            base = crop.resize((map_w, map_h), Image.Resampling.LANCZOS)
            crop_origin = (x0, y0)
            scale_x = map_w / max(1, x1 - x0)
            scale_y = map_h / max(1, y1 - y0)
            zoom = z
            break
        except Exception:
            base = None

    if base is None:
        base = Image.new("RGB", (map_w, map_h), "#15344a")
    image.paste(base, (map_box[0], map_box[1]))
    overlay = ImageDraw.Draw(image, "RGBA")

    def project(lon: float, lat: float) -> tuple[int, int]:
        px, py = _lonlat_to_pixel(lon, lat, zoom)
        return int(map_box[0] + (px - crop_origin[0]) * scale_x), int(map_box[1] + (py - crop_origin[1]) * scale_y)

    area_points = [project(lon, lat) for lon, lat in _coords_from_geometry(area_geojson or {})]
    if len(area_points) >= 3:
        overlay.polygon(area_points, fill=(0, 229, 255, 42), outline=(0, 229, 255, 255))
        overlay.line(area_points, fill=(0, 229, 255, 255), width=5, joint="curve")
    for parcel in parcels:
        pts = [project(lon, lat) for lon, lat in _coords_from_geometry(parcel.get("geojson", {}))]
        if len(pts) >= 3:
            overlay.polygon(pts, fill=(255, 159, 28, 36), outline=(255, 159, 28, 230))
            if parcel.get("parcela"):
                cx = sum(p[0] for p in pts[:-1] or pts) / max(1, len(pts[:-1] or pts))
                cy = sum(p[1] for p in pts[:-1] or pts) / max(1, len(pts[:-1] or pts))
                overlay.text((cx - 22, cy - 8), str(parcel.get("parcela")), fill=(255, 255, 255, 255), font=font_small)

    draw.rectangle(map_box, outline=(0, 229, 255, 255), width=4)
    lx = width - legend_w - 10
    draw.text((lx, header_h + 44), "LEGENDA", fill=(255, 255, 255, 255), font=font_med)
    draw.rectangle((lx, header_h + 90, lx + 46, header_h + 118), fill=(0, 229, 255, 70), outline=(0, 229, 255, 255), width=3)
    draw.text((lx + 60, header_h + 90), "Área experimental", fill=(230, 250, 255, 255), font=font_small)
    draw.rectangle((lx, header_h + 135, lx + 46, header_h + 163), fill=(255, 159, 28, 70), outline=(255, 159, 28, 255), width=3)
    draw.text((lx + 60, header_h + 135), "Parcelas alocadas", fill=(230, 250, 255, 255), font=font_small)
    draw.text((lx, header_h + 205), f"Área: {summary.get('area_ha', 0):.4f} ha", fill=(230, 250, 255, 255), font=font_small)
    draw.text((lx, header_h + 236), f"Parcelas: {summary.get('total_parcelas', len(parcels))}", fill=(230, 250, 255, 255), font=font_small)
    draw.text((lx, header_h + 267), f"Zoom base: {zoom}", fill=(230, 250, 255, 255), font=font_small)
    draw.text((width - 126, header_h + 42), "N", fill=(255, 255, 255, 255), font=font_med)
    draw.polygon([(width - 92, header_h + 82), (width - 114, header_h + 142), (width - 70, header_h + 142)], fill=(0, 229, 255, 255))
    draw.rectangle((0, height - footer_h, width, height), fill=(3, 24, 48, 255))
    draw.text((44, height - 50), f"{summary.get('nome_area','')} · {date.today().strftime('%d/%m/%Y')} · TMG Sistema de Análise", fill=(210, 245, 255, 255), font=font_small)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _has_arial() -> bool:
    try:
        ImageFont.truetype("arial.ttf", 12)
        return True
    except Exception:
        return False
