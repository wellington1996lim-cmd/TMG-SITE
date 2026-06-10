from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path
from typing import Any

import folium
import pandas as pd
import streamlit as st
from folium.plugins import Draw

try:
    from streamlit_folium import st_folium
except Exception:  # pragma: no cover
    st_folium = None

from modules.experiment_history import (
    delete_experiment,
    duplicate_experiment,
    init_experiment_db,
    list_experiments,
    load_experiment,
    save_experiment,
)
from modules.planting_exporter import excel_bytes, geojson_bytes, kml_bytes, map_png_bytes, parcels_csv_bytes
from modules.plot_allocator import allocate_parcels, calculate_area_metrics


ESRI_WORLD_IMAGERY = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
ESRI_LABELS = "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
ESRI_TRANSPORT = "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}"


def _fmt(value: float, decimals: int = 2) -> str:
    return f"{float(value or 0):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _safe_name(value: str, default: str = "Ensaio_TMG") -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("_", "-", ".") else "_" for ch in str(value or default).strip())
    return cleaned.strip("_") or default


def _default_form() -> dict[str, Any]:
    return {
        "nome_ensaio": f"Ensaio_TMG_{date.today().strftime('%Y%m%d')}",
        "nome_area": "QM-1A",
        "fazenda": "Fazenda Experimental",
        "talhao": "Talhão 01",
        "quadra": "QM-1A",
        "cultura": "Soja",
        "safra": str(date.today().year),
        "data_plantio": date.today(),
        "observacao": "",
        "status": "Planejado",
    }


def _init_state() -> None:
    st.session_state.setdefault("mc_area_geojson", None)
    st.session_state.setdefault("mc_area_metrics", {})
    st.session_state.setdefault("mc_parcels", [])
    st.session_state.setdefault("mc_alloc_metrics", {})
    st.session_state.setdefault("mc_form", _default_form())
    st.session_state.setdefault("mc_selected_parcel", "")
    st.session_state.setdefault("mc_show_code", True)
    st.session_state.setdefault("mc_show_material", True)
    st.session_state.setdefault("mc_show_history", False)
    st.session_state.setdefault("mc_show_exports", False)
    st.session_state.setdefault("mc_last_saved_id", None)
    if st.session_state.get("mc_pending_load"):
        data = st.session_state.pop("mc_pending_load")
        summary = data.get("summary", {})
        st.session_state.mc_form = {
            "nome_ensaio": summary.get("nome_ensaio") or _default_form()["nome_ensaio"],
            "nome_area": summary.get("nome_area") or "",
            "fazenda": summary.get("fazenda") or "",
            "talhao": summary.get("talhao") or "",
            "quadra": summary.get("quadra") or "",
            "cultura": summary.get("cultura") or "",
            "safra": summary.get("safra") or "",
            "data_plantio": pd.to_datetime(summary.get("data_plantio") or date.today()).date(),
            "observacao": summary.get("observacao") or "",
            "status": summary.get("status") or "Planejado",
        }
        area_geojson = data.get("geometries", {}).get("area", {}).get("geojson_obj") or None
        st.session_state.mc_area_geojson = {"type": "Feature", "properties": {}, "geometry": area_geojson} if area_geojson and area_geojson.get("type") else None
        st.session_state.mc_parcels = data.get("parcels", [])
        try:
            st.session_state.mc_area_metrics = calculate_area_metrics(st.session_state.mc_area_geojson)
        except Exception:
            st.session_state.mc_area_metrics = {}


def _style(theme_rgb: str) -> None:
    st.markdown(
        f"""
        <style>
        .mc-shell {{
          border:1px solid rgba({theme_rgb},.48);
          border-radius:14px;
          padding:14px 16px;
          margin-bottom:14px;
          background:linear-gradient(145deg,rgba(2,14,36,.96),rgba(14,52,84,.82),rgba({theme_rgb},.10));
          box-shadow:0 18px 34px rgba(0,0,0,.36),0 0 24px rgba({theme_rgb},.16),inset 0 1px 0 rgba(255,255,255,.13);
        }}
        .mc-shell h2 {{
          margin:0; color:#fff; font-size:1.15rem; letter-spacing:1.5px; text-transform:uppercase;
          text-shadow:0 1px 0 #020e24,0 0 16px rgba({theme_rgb},.42);
        }}
        .mc-shell p {{ margin:.45rem 0 0 0; color:#dffbff; font-size:.86rem; }}
        .mc-panel {{
          border:1px solid rgba({theme_rgb},.35);
          border-radius:12px;
          padding:12px;
          background:linear-gradient(180deg,rgba(6,31,54,.94),rgba(2,14,36,.96));
          box-shadow:inset 0 1px 0 rgba(255,255,255,.10),0 12px 22px rgba(0,0,0,.22);
        }}
        .mc-panel-title {{
          color:#fff; font-weight:950; letter-spacing:.8px; text-transform:uppercase; font-size:.78rem;
          border-bottom:1px solid rgba({theme_rgb},.34); padding-bottom:7px; margin-bottom:10px;
        }}
        div[data-testid="stMetric"] {{
          border:1px solid rgba({theme_rgb},.25); border-radius:10px; padding:8px;
          background:rgba(2,14,36,.48);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _extract_drawn_polygon(map_data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not map_data:
        return None
    drawings = map_data.get("all_drawings") or []
    polygons = []
    for item in drawings:
        geom = item.get("geometry") if isinstance(item, dict) else None
        if geom and geom.get("type") in ("Polygon", "MultiPolygon"):
            polygons.append(item)
    return polygons[-1] if polygons else None


def _map_center(area_geojson: dict[str, Any] | None, metrics: dict[str, Any]) -> tuple[float, float, int]:
    if metrics.get("centroid_lat") and metrics.get("centroid_lon"):
        return float(metrics["centroid_lat"]), float(metrics["centroid_lon"]), 18
    return -12.546, -55.722, 16


def _add_tile_layers(m: folium.Map, active_layer: str) -> None:
    folium.TileLayer(
        tiles=ESRI_WORLD_IMAGERY,
        name="Esri World Imagery",
        attr="Tiles © Esri",
        overlay=False,
        control=True,
        max_zoom=22,
        max_native_zoom=19,
    ).add_to(m)
    folium.TileLayer(
        tiles=ESRI_WORLD_IMAGERY,
        name="Satélite",
        attr="Tiles © Esri",
        overlay=False,
        control=True,
        max_zoom=22,
        max_native_zoom=19,
    ).add_to(m)
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="OpenStreetMap",
        overlay=False,
        control=True,
        max_zoom=22,
        max_native_zoom=19,
    ).add_to(m)
    folium.TileLayer(
        tiles=ESRI_LABELS,
        name="Híbrido - rótulos",
        attr="Labels © Esri",
        overlay=True,
        control=True,
        max_zoom=22,
        max_native_zoom=19,
    ).add_to(m)
    folium.TileLayer(
        tiles=ESRI_TRANSPORT,
        name="Híbrido - estradas",
        attr="Transportation © Esri",
        overlay=True,
        control=True,
        max_zoom=22,
        max_native_zoom=19,
    ).add_to(m)


def _add_area_and_parcels(m: folium.Map, area_geojson: dict[str, Any] | None, parcels: list[dict[str, Any]], selected: str, show_code: bool, show_material: bool) -> None:
    if area_geojson:
        folium.GeoJson(
            area_geojson,
            name="Área marcada",
            style_function=lambda _: {"color": "#00e5ff", "weight": 3, "fillColor": "#00e5ff", "fillOpacity": 0.18},
            tooltip="Área experimental",
        ).add_to(m)
    if parcels:
        group = folium.FeatureGroup(name="Parcelas alocadas", show=True)
        for parcel in parcels:
            color = "#ffffff" if parcel.get("parcela") == selected else "#ff9f1c"
            weight = 4 if parcel.get("parcela") == selected else 2
            label_parts = []
            if show_code:
                label_parts.append(parcel.get("parcela", ""))
            if show_material and parcel.get("material"):
                label_parts.append(parcel.get("material", ""))
            tooltip = " · ".join(part for part in label_parts if part) or parcel.get("parcela", "")
            folium.GeoJson(
                parcel.get("geojson", {}),
                name=parcel.get("parcela", "Parcela"),
                style_function=lambda _, color=color, weight=weight: {
                    "color": color,
                    "weight": weight,
                    "fillColor": "#ff9f1c",
                    "fillOpacity": 0.16,
                },
                tooltip=tooltip,
                popup=folium.Popup(
                    f"<b>{parcel.get('parcela','')}</b><br>Material: {parcel.get('material','')}<br>Tratamento: {parcel.get('tratamento','')}",
                    max_width=260,
                ),
            ).add_to(group)
            if tooltip and (show_code or show_material):
                folium.Marker(
                    [parcel.get("latitude_centro", 0), parcel.get("longitude_centro", 0)],
                    icon=folium.DivIcon(
                        html=f"<div style='font-size:10px;font-weight:800;color:white;text-shadow:0 1px 3px #000;white-space:nowrap;'>{tooltip}</div>"
                    ),
                ).add_to(group)
        group.add_to(m)


def _render_map(area_geojson: dict[str, Any] | None, parcels: list[dict[str, Any]], metrics: dict[str, Any], selected: str, show_code: bool, show_material: bool) -> dict[str, Any] | None:
    if st_folium is None:
        st.error("A biblioteca streamlit-folium não está instalada. Instale com: pip install streamlit-folium")
        return None
    lat, lon, zoom = _map_center(area_geojson, metrics)
    m = folium.Map(location=[lat, lon], zoom_start=zoom, tiles=None, control_scale=True, prefer_canvas=True, max_zoom=22)
    _add_tile_layers(m, "Esri World Imagery")
    _add_area_and_parcels(m, area_geojson, parcels, selected, show_code, show_material)
    Draw(
        export=False,
        draw_options={
            "polyline": False,
            "rectangle": False,
            "circle": False,
            "circlemarker": False,
            "marker": False,
            "polygon": {
                "allowIntersection": False,
                "showArea": True,
                "shapeOptions": {"color": "#00e5ff", "weight": 3, "fillOpacity": 0.18},
            },
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return st_folium(
        m,
        height=760,
        use_container_width=True,
        returned_objects=["all_drawings", "last_active_drawing", "last_object_clicked_popup"],
        key="mc_folium_map",
    )


def _summary_from_form(form: dict[str, Any], metrics: dict[str, Any], parcels: list[dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
    return {
        **form,
        "data_plantio": str(form.get("data_plantio") or ""),
        "data_criacao": date.today().isoformat(),
        "area_m2": float(metrics.get("area_m2") or 0),
        "area_ha": float(metrics.get("area_ha") or 0),
        "perimetro_m": float(metrics.get("perimeter_m") or metrics.get("perimetro_m") or 0),
        "total_tiros": int(params.get("tiros") or 0),
        "total_disparos": int(params.get("disparos") or 0),
        "total_parcelas": len(parcels),
    }


def _parcels_to_editor_df(parcels: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for item in parcels:
        rows.append(
            {
                "Parcela": item.get("parcela", ""),
                "Tiro": item.get("tiro", 0),
                "Disparo": item.get("disparo", 0),
                "Material": item.get("material", ""),
                "Tratamento": item.get("tratamento", ""),
                "Repetição": item.get("repeticao", ""),
                "Bloco": item.get("bloco", ""),
                "Observação": item.get("observacao", ""),
            }
        )
    return pd.DataFrame(rows)


def _apply_editor_df(df: pd.DataFrame) -> None:
    if df is None or df.empty:
        return
    by_code = {p.get("parcela"): p for p in st.session_state.mc_parcels}
    for _, row in df.iterrows():
        code = str(row.get("Parcela") or "")
        parcel = by_code.get(code)
        if not parcel:
            continue
        parcel["material"] = str(row.get("Material") or "")
        parcel["tratamento"] = str(row.get("Tratamento") or "")
        parcel["repeticao"] = str(row.get("Repetição") or "")
        parcel["bloco"] = str(row.get("Bloco") or "")
        parcel["observacao"] = str(row.get("Observação") or "")


def _read_material_file(uploaded) -> pd.DataFrame:
    if uploaded is None:
        return pd.DataFrame()
    suffix = Path(uploaded.name).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(uploaded)
    return pd.read_excel(uploaded)


def _distribute_materials(materials: pd.DataFrame, mode: str, repeat: bool) -> None:
    if materials.empty or not st.session_state.mc_parcels:
        return
    rows = materials.to_dict("records")
    parcels = list(st.session_state.mc_parcels)
    if mode == "column":
        parcels.sort(key=lambda p: (int(p.get("tiro") or 0), int(p.get("disparo") or 0)))
    elif mode == "random":
        random.shuffle(parcels)
    else:
        parcels.sort(key=lambda p: (int(p.get("disparo") or 0), int(p.get("tiro") or 0)))
    for idx, parcel in enumerate(parcels):
        if idx >= len(rows) and not repeat:
            break
        row = rows[idx % len(rows)]
        parcel["material"] = str(row.get("Material") or row.get("material") or "")
        parcel["tratamento"] = str(row.get("Tratamento") or row.get("tratamento") or "")
        parcel["repeticao"] = str(row.get("Repetição") or row.get("Repeticao") or row.get("repeticao") or "")
        parcel["bloco"] = str(row.get("Bloco") or row.get("bloco") or "")
        parcel["observacao"] = str(row.get("Observação") or row.get("Observacao") or row.get("observacao") or "")


def _render_history_panel() -> None:
    st.markdown("<div class='mc-panel-title'>Histórico de Ensaios</div>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    filters = {
        "cultura": f1.text_input("Cultura", key="mc_filter_cultura"),
        "safra": f2.text_input("Safra", key="mc_filter_safra"),
        "fazenda": f3.text_input("Fazenda", key="mc_filter_fazenda"),
    }
    history = list_experiments(filters)
    st.dataframe(history, use_container_width=True, height=220, hide_index=True)
    if history.empty:
        return
    ids = history["id"].tolist()
    selected_id = st.selectbox("Selecionar ensaio", ids, format_func=lambda x: f"#{x} · {history.loc[history['id']==x, 'nome_ensaio'].iloc[0]}", key="mc_history_select")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Abrir", use_container_width=True, key="mc_open_history"):
        st.session_state.mc_pending_load = load_experiment(int(selected_id))
        st.rerun()
    if c2.button("Duplicar", use_container_width=True, key="mc_dup_history"):
        new_id = duplicate_experiment(int(selected_id))
        st.success(f"Ensaio duplicado: #{new_id}")
    if c3.button("Excluir", use_container_width=True, key="mc_del_history"):
        delete_experiment(int(selected_id))
        st.warning("Ensaio excluído.")
        st.rerun()
    if c4.button("Exportar", use_container_width=True, key="mc_export_history"):
        data = load_experiment(int(selected_id))
        summary = data["summary"]
        area = data["geometries"].get("area", {}).get("geojson_obj", {})
        parcels = data["parcels"]
        st.download_button(
            "Baixar Excel do histórico",
            data=excel_bytes(summary, parcels, history),
            file_name=f"{_safe_name(summary.get('nome_ensaio'))}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="mc_history_excel_download",
        )


def render_map_creator(
    theme_primary: str = "#00e5ff",
    theme_soft: str = "#5ff2ff",
    theme_rgb: str = "0,229,255",
    logo_src: str = "",
    system_name: str = "TMG Sistema de Análise",
) -> None:
    init_experiment_db()
    _init_state()
    _style(theme_rgb)

    st.markdown(
        """
        <div class="mc-shell">
          <h2>Criador de Mapa</h2>
          <p>Planejamento de área experimental, alocação de parcelas, materiais plantados, histórico de ensaios e exportação.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top = st.columns([1.05, 1.05, 1.05, 1.05, 1.05, 1.05])
    if top[0].button("Nova Área", use_container_width=True):
        st.session_state.mc_area_geojson = None
        st.session_state.mc_area_metrics = {}
        st.session_state.mc_parcels = []
        st.session_state.mc_alloc_metrics = {}
        st.rerun()
    if top[1].button("Desenhar Polígono", use_container_width=True):
        st.info("Use o ícone de polígono no mapa para marcar a área experimental.")
    if top[2].button("Editar Polígono", use_container_width=True):
        st.info("Use a ferramenta de edição do mapa para mover vértices ou apagar o polígono.")
    if top[3].button("Medir Área", use_container_width=True):
        if st.session_state.mc_area_geojson:
            st.session_state.mc_area_metrics = calculate_area_metrics(st.session_state.mc_area_geojson)
            st.success("Área calculada com projeção UTM automática.")
        else:
            st.warning("Desenhe uma área no mapa para calcular.")
    if top[4].button("Ver Histórico", use_container_width=True):
        st.session_state.mc_show_history = not st.session_state.get("mc_show_history", False)
    if top[5].button("Exportar", use_container_width=True):
        st.session_state.mc_show_exports = not st.session_state.get("mc_show_exports", False)

    left, right = st.columns([1.9, 1.0], gap="large")

    with right:
        st.markdown("<div class='mc-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='mc-panel-title'>Dados da Área</div>", unsafe_allow_html=True)
        form = st.session_state.mc_form
        form["nome_ensaio"] = st.text_input("Nome do ensaio", value=form.get("nome_ensaio", ""), key="mc_nome_ensaio")
        c1, c2 = st.columns(2)
        form["nome_area"] = c1.text_input("Nome da área", value=form.get("nome_area", ""), key="mc_nome_area")
        form["quadra"] = c2.text_input("Quadra", value=form.get("quadra", ""), key="mc_quadra")
        form["fazenda"] = st.text_input("Fazenda", value=form.get("fazenda", ""), key="mc_fazenda")
        form["talhao"] = st.text_input("Talhão", value=form.get("talhao", ""), key="mc_talhao")
        c3, c4, c5 = st.columns(3)
        form["cultura"] = c3.text_input("Cultura", value=form.get("cultura", ""), key="mc_cultura")
        form["safra"] = c4.text_input("Safra", value=form.get("safra", ""), key="mc_safra")
        form["data_plantio"] = c5.date_input("Plantio", value=form.get("data_plantio") or date.today(), key="mc_data_plantio")
        form["observacao"] = st.text_area("Observação", value=form.get("observacao", ""), key="mc_observacao")

        metrics = st.session_state.mc_area_metrics or {}
        m1, m2, m3 = st.columns(3)
        m1.metric("Área m²", _fmt(metrics.get("area_m2", 0), 2))
        m2.metric("Área ha", _fmt(metrics.get("area_ha", 0), 4))
        m3.metric("Perímetro", f"{_fmt(metrics.get('perimeter_m', 0), 2)} m")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='mc-panel' style='margin-top:12px;'>", unsafe_allow_html=True)
        st.markdown("<div class='mc-panel-title'>Dividir em Parcelas</div>", unsafe_allow_html=True)
        p1, p2 = st.columns(2)
        comprimento = p1.number_input("Comprimento (m)", min_value=0.1, value=5.0, step=0.1, key="mc_comp")
        largura = p2.number_input("Largura (m)", min_value=0.1, value=2.0, step=0.1, key="mc_larg")
        p3, p4 = st.columns(2)
        esp = p3.number_input("Espaço parcelas (m)", min_value=0.0, value=0.5, step=0.1, key="mc_esp")
        corredor = p4.number_input("Espaço blocos/corredores (m)", min_value=0.0, value=0.0, step=0.1, key="mc_cor")
        p5, p6, p7 = st.columns(3)
        tiros = p5.number_input("Tiros", min_value=1, value=14, step=1, key="mc_tiros")
        disparos = p6.number_input("Disparos", min_value=1, value=30, step=1, key="mc_disparos")
        orient = p7.number_input("Orientação °", value=0.0, step=1.0, key="mc_orient")
        params = {
            "comprimento_m": comprimento,
            "largura_m": largura,
            "espacamento_m": esp,
            "corredor_m": corredor,
            "tiros": tiros,
            "disparos": disparos,
            "orientacao_graus": orient,
        }
        if st.button("Dividir em Parcelas", type="primary", use_container_width=True):
            if not st.session_state.mc_area_geojson:
                st.warning("Desenhe uma área no mapa antes de dividir em parcelas.")
            else:
                try:
                    result = allocate_parcels(st.session_state.mc_area_geojson, params)
                    st.session_state.mc_parcels = result["parcels"]
                    st.session_state.mc_alloc_metrics = result["metrics"]
                    if result["metrics"]["missing"]:
                        st.warning("A dimensão informada não permite alocar todas as parcelas dentro da área.")
                    else:
                        st.success("Parcelas alocadas com sucesso.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível alocar parcelas: {exc}")
        alloc = st.session_state.mc_alloc_metrics or {}
        a1, a2, a3 = st.columns(3)
        a1.metric("Planejadas", int(alloc.get("planned", 0)))
        a2.metric("Alocadas", int(alloc.get("allocated", len(st.session_state.mc_parcels))))
        a3.metric("Não couberam", int(alloc.get("missing", 0)))
        b1, b2 = st.columns(2)
        b1.metric("Área ocupada", f"{_fmt(alloc.get('occupied_area_m2', 0), 2)} m²")
        b2.metric("Aproveitamento", f"{_fmt(alloc.get('use_percent', 0), 2)}%")
        st.markdown("</div>", unsafe_allow_html=True)

    with left:
        st.markdown("<div class='mc-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='mc-panel-title'>Camada de Mapa e Marcação de Área</div>", unsafe_allow_html=True)
        map_data = _render_map(
            st.session_state.mc_area_geojson,
            st.session_state.mc_parcels,
            st.session_state.mc_area_metrics,
            st.session_state.mc_selected_parcel,
            st.session_state.mc_show_code,
            st.session_state.mc_show_material,
        )
        drawn = _extract_drawn_polygon(map_data)
        if drawn:
            geom_text = json.dumps(drawn.get("geometry", {}), sort_keys=True)
            current_text = json.dumps((st.session_state.mc_area_geojson or {}).get("geometry", {}), sort_keys=True)
            if geom_text != current_text:
                st.session_state.mc_area_geojson = {"type": "Feature", "properties": {}, "geometry": drawn["geometry"]}
                st.session_state.mc_area_metrics = calculate_area_metrics(st.session_state.mc_area_geojson)
                st.session_state.mc_parcels = []
                st.session_state.mc_alloc_metrics = {}
                st.success("Área marcada e medida com sucesso.")
                st.rerun()
        st.caption("Camadas: Esri World Imagery, Satélite, Híbrido com rótulos e OpenStreetMap. Zoom até 22 com ampliação do tile nativo quando necessário.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='mc-panel' style='margin-top:14px;'>", unsafe_allow_html=True)
    st.markdown("<div class='mc-panel-title'>Editar Materiais das Parcelas</div>", unsafe_allow_html=True)
    ec1, ec2, ec3, ec4 = st.columns([1, 1, 1, 1])
    st.session_state.mc_show_code = ec1.checkbox("Mostrar código no mapa", value=st.session_state.mc_show_code)
    st.session_state.mc_show_material = ec2.checkbox("Mostrar material no mapa", value=st.session_state.mc_show_material)
    dist_mode = ec3.selectbox("Distribuição", ["Sequencial por linha", "Sequencial por coluna", "Randomizado", "Manual"], key="mc_dist_mode")
    repeat_material = ec4.checkbox("Repetir lista", value=False, key="mc_repeat_material")
    uploaded_materials = st.file_uploader("Importar Materiais", type=["xlsx", "xls", "csv"], key="mc_materials_upload")
    if uploaded_materials is not None:
        try:
            material_df = _read_material_file(uploaded_materials)
            st.dataframe(material_df, use_container_width=True, height=120)
            if st.button("Distribuir Materiais", use_container_width=True):
                mode_key = {"Sequencial por linha": "row", "Sequencial por coluna": "column", "Randomizado": "random", "Manual": "manual"}[dist_mode]
                if mode_key != "manual":
                    _distribute_materials(material_df, mode_key, repeat_material)
                    st.success("Materiais distribuídos nas parcelas.")
                    st.rerun()
        except Exception as exc:
            st.error(f"Não foi possível importar materiais: {exc}")
    if st.session_state.mc_parcels:
        codes = [p.get("parcela", "") for p in st.session_state.mc_parcels]
        selected = st.selectbox("Selecionar parcela para destacar no mapa", [""] + codes, key="mc_selected_parcel_box")
        st.session_state.mc_selected_parcel = selected
        editor_df = st.data_editor(
            _parcels_to_editor_df(st.session_state.mc_parcels),
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key="mc_parcel_editor",
        )
        _apply_editor_df(editor_df)
    else:
        st.info("Aloque parcelas para editar materiais.")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Salvar Ensaio", type="primary", use_container_width=True):
        if not st.session_state.mc_area_geojson:
            st.error("Não foi possível salvar sem polígono de área.")
        else:
            summary = _summary_from_form(st.session_state.mc_form, st.session_state.mc_area_metrics, st.session_state.mc_parcels, params)
            area_geo = st.session_state.mc_area_geojson.get("geometry", st.session_state.mc_area_geojson)
            kml = kml_bytes(summary, area_geo, st.session_state.mc_parcels).decode("utf-8", errors="ignore")
            exp_id = save_experiment(summary, st.session_state.mc_parcels, area_geo, json.loads(geojson_bytes(None, st.session_state.mc_parcels).decode("utf-8")), kml)
            st.session_state.mc_last_saved_id = exp_id
            st.success(f"Ensaio salvo no histórico com ID #{exp_id}.")

    if st.session_state.get("mc_show_history", False):
        with st.container():
            st.markdown("<div class='mc-panel' style='margin-top:14px;'>", unsafe_allow_html=True)
            _render_history_panel()
            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get("mc_show_exports", False):
        st.markdown("<div class='mc-panel' style='margin-top:14px;'>", unsafe_allow_html=True)
        st.markdown("<div class='mc-panel-title'>Exportar Resultado</div>", unsafe_allow_html=True)
        summary = _summary_from_form(st.session_state.mc_form, st.session_state.mc_area_metrics, st.session_state.mc_parcels, params)
        area_geo = (st.session_state.mc_area_geojson or {}).get("geometry", st.session_state.mc_area_geojson)
        hist = list_experiments({})
        file_base = _safe_name(summary.get("nome_ensaio") or "Ensaio_TMG")
        ex1, ex2, ex3, ex4, ex5 = st.columns(5)
        ex1.download_button("Excel", excel_bytes(summary, st.session_state.mc_parcels, hist), f"{file_base}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        ex2.download_button("CSV", parcels_csv_bytes(st.session_state.mc_parcels), f"{file_base}_parcelas.csv", "text/csv", use_container_width=True)
        ex3.download_button("GeoJSON", geojson_bytes(area_geo, st.session_state.mc_parcels), f"{file_base}.geojson", "application/geo+json", use_container_width=True)
        ex4.download_button("KML", kml_bytes(summary, area_geo, st.session_state.mc_parcels), f"{file_base}.kml", "application/vnd.google-earth.kml+xml", use_container_width=True)
        try:
            png = map_png_bytes(summary, area_geo, st.session_state.mc_parcels)
            ex5.download_button("PNG", png, f"{file_base}_mapa.png", "image/png", use_container_width=True)
        except Exception as exc:
            ex5.warning(f"PNG indisponível: {exc}")
        st.caption("O PNG usa Esri World Imagery quando disponível; se os tiles falharem, gera um mapa técnico de fallback com as geometrias.")
        st.markdown("</div>", unsafe_allow_html=True)


def render_map_creator_module(
    theme_primary: str = "#00e5ff",
    theme_soft: str = "#5ff2ff",
    theme_rgb: str = "0,229,255",
    logo_src: str = "",
    system_name: str = "TMG Sistema de Análise",
) -> None:
    render_map_creator(theme_primary, theme_soft, theme_rgb, logo_src, system_name)
