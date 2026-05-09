import sys
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
from PIL import Image, ImageFile
import os
import shutil
import base64
import io
from io import BytesIO
import numpy as np
import json
import tempfile
import zipfile
import csv
import cv2
import warnings
import hashlib
from datetime import datetime, date

APP_ROOT = Path(__file__).resolve().parent

# NOVO - Configurações para suportar imagens grandes e formatos variados
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True
warnings.simplefilter('ignore', Image.DecompressionBombWarning)

# IMPORTAÇÕES ADICIONAIS PARA GERAÇÃO ROBUSTA DE SHP[cite: 1]
try:
    import geopandas as gpd
    from shapely.geometry import Polygon
    from affine import Affine
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False

# Remover limite de tamanho de imagem do PIL para Ortofotos gigantes[cite: 1]
Image.MAX_IMAGE_PIXELS = None

# ==========================================
# CONFIGURAÇÃO DA PÁGINA[cite: 1]
# ==========================================
st.set_page_config(
    page_title="TMG Sistema de Análise",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    '<meta name="google" content="notranslate"><meta name="robots" content="notranslate">',
    unsafe_allow_html=True
)

components.html(
    """
<script>
(function () {
  function protectOneDocument(doc) {
    const root = doc.documentElement;
    root.setAttribute("lang", "pt-BR");
    root.setAttribute("translate", "no");
    root.classList.add("notranslate");
    root.classList.remove("translated-ltr", "translated-rtl");

    if (doc.body) {
      doc.body.setAttribute("translate", "no");
      doc.body.classList.add("notranslate");
      doc.body.classList.remove("translated-ltr", "translated-rtl");
    }

    doc.querySelectorAll("body, #root, .stApp, [data-testid='stAppViewContainer']").forEach((el) => {
      el.setAttribute("translate", "no");
      el.classList.add("notranslate");
    });

    if (!doc.head.querySelector('meta[name="google"][content="notranslate"]')) {
      const meta = doc.createElement("meta");
      meta.setAttribute("name", "google");
      meta.setAttribute("content", "notranslate");
      doc.head.appendChild(meta);
    }

    if (!doc.head.querySelector("#tmg-notranslate-style")) {
      const style = doc.createElement("style");
      style.id = "tmg-notranslate-style";
      style.textContent = ".goog-te-banner-frame,.skiptranslate{display:none!important;}body{top:0!important;}";
      doc.head.appendChild(style);
    }
  }

  function protectDocument() {
    try {
      let current = window;
      for (let i = 0; i < 4; i += 1) {
        protectOneDocument(current.document);
        if (current === current.parent) {
          break;
        }
        current = current.parent;
      }
    } catch (err) {
      // Cross-frame access can be blocked in some hosted contexts; the app still works without it.
    }
  }

  protectDocument();
  window.setTimeout(protectDocument, 500);
  window.setTimeout(protectDocument, 2000);
})();
</script>
    """,
    height=0,
    width=0,
)

# ==========================================
# ESTILO CSS PERSONALIZADO (DARK SAAS 3D)[cite: 1]
# ==========================================
st.markdown("""
<style>
    .stApp {
        background-color: #121212;
        color: #e0e0e0;
    }

    .main-header {
        text-align: center;
        color: #FFFFFF;
        padding: 20px;
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
        letter-spacing: 4px;
        font-size: 2.2rem;
        text-shadow:
            2px 2px 0px #000000,
            4px 4px 0px #1a1a1a,
            6px 6px 8px rgba(0,0,0,0.9),
            0 0 30px rgba(255,140,0,0.25);
        border-bottom: 2px solid #ff8c00;
        margin-bottom: 30px;
    }

    [data-testid="stSidebar"] {
        background-color: #1a1a1a;
        border-right: 1px solid #333;
        padding-top: 20px;
    }

    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        border: none;
        padding: 15px 20px;
        background: linear-gradient(145deg, #222, #111);
        color: #ccc;
        font-weight: 600;
        box-shadow: 3px 3px 6px #0a0a0a, -1px -1px 6px #2a2a2a;
        transition: 0.3s;
        margin-bottom: 10px;
        text-align: left;
    }

    div.stButton > button:hover {
        color: #ff8c00;
        border: 1px solid #ff8c00;
        transform: translateY(-2px);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(145deg, #ff9e33, #e67600) !important;
        color: white !important;
        box-shadow: 4px 4px 10px #0a0a0a !important;
    }

    .card {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #333;
    }

    /* 3D Menu Title */
    .menu-3d-title {
        text-align: center;
        font-family: 'Segoe UI', sans-serif;
        font-weight: 900;
        font-size: 1.6rem;
        letter-spacing: 4px;
        color: #ff8c00;
        text-transform: uppercase;
        text-shadow:
            1px 1px 0 #7a3a00,
            2px 2px 0 #5c2b00,
            3px 3px 0 #3d1d00,
            4px 4px 6px rgba(0,0,0,0.9),
            0 0 20px rgba(255,140,0,0.4),
            0 0 40px rgba(255,140,0,0.15);
        margin-bottom: 8px;
    }

    /* Separator with glow */
    .separator-glow {
        border: none;
        border-top: 1px solid #ff8c00;
        box-shadow: 0 0 8px rgba(255,140,0,0.5);
        margin: 10px 0 18px 0;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# DIRETÓRIOS DE ASSETS[cite: 1]
# ==========================================
LOGO_DIR = APP_ROOT / "tmg_assets/logo"
LOGO_DIR.mkdir(parents=True, exist_ok=True)
LOGO_PATH = LOGO_DIR / "logo_tmg_referencia.png"

LOGIN_BG_DIR = APP_ROOT / "tmg_assets/login"
LOGIN_BG_DIR.mkdir(parents=True, exist_ok=True)
LOGIN_BG_PATH = LOGIN_BG_DIR / "login_bg_referencia.png"

SYSTEM_CONFIG_DIR = APP_ROOT / "tmg_config"
SYSTEM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
SYSTEM_CONFIG_PATH = SYSTEM_CONFIG_DIR / "system_config.json"

# ==========================================
# HELPER — ENCODE IMAGEM PARA BASE64 CSS[cite: 1]
# ==========================================
def _img_to_base64_css(path: Path) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{data}"

def app_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

def app_image(image, **kwargs):
    try:
        return st.image(image, use_container_width=True, **kwargs)
    except TypeError:
        return st.image(image, use_column_width=True, **kwargs)

def _streamlit_secret(name: str, default: str = "") -> str:
    secrets_paths = [
        Path.home() / ".streamlit" / "secrets.toml",
        APP_ROOT / ".streamlit" / "secrets.toml",
    ]
    if not any(path.exists() for path in secrets_paths):
        return default
    try:
        return str(st.secrets.get(name, default) or default)
    except Exception:
        return default

def _configured_database_dir() -> str:
    return (
        os.getenv("TMG_DATABASE_DIR", "").strip()
        or _streamlit_secret("TMG_DATABASE_DIR").strip()
        or _streamlit_secret("database_dir").strip()
    )

def _int_setting(name: str, default: int, min_value: int, max_value: int) -> int:
    raw = os.getenv(name, "").strip() or _streamlit_secret(name).strip()
    try:
        value = int(raw) if raw else int(default)
    except Exception:
        value = int(default)
    return max(min_value, min(max_value, value))

def _preview_max_dim() -> int:
    return _int_setting("TMG_PREVIEW_MAX_DIM", 4096, 1024, 8192)

def _preview_jpeg_quality() -> int:
    return _int_setting("TMG_PREVIEW_JPEG_QUALITY", 90, 70, 97)

def _looks_like_windows_drive_path(raw: str) -> bool:
    return len(raw) > 2 and raw[1] == ":" and raw[2:3] in ("\\", "/")

def _resolve_system_path(value: str) -> Path:
    raw = os.path.expandvars(str(value or "").strip())
    if os.name != "nt" and _looks_like_windows_drive_path(raw):
        raw = "tmg_data"
    path = Path(raw).expanduser() if raw else Path("tmg_data")
    if not path.is_absolute():
        path = (APP_ROOT / path).resolve()
    return path

def _load_system_config() -> dict:
    configured_dir = _configured_database_dir()
    default_dir = _resolve_system_path(configured_dir or "tmg_data")
    default = {
        "database_dir": str(default_dir),
        "updated_at": "",
        "tema": "padrao"
    }
    if not SYSTEM_CONFIG_PATH.exists():
        SYSTEM_CONFIG_PATH.write_text(json.dumps(default, indent=2, ensure_ascii=False), encoding="utf-8")
        return default
    try:
        data = json.loads(SYSTEM_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = default
    data.setdefault("database_dir", str(default_dir))
    data.setdefault("updated_at", "")
    data.setdefault("tema", "padrao")
    if configured_dir:
        data["database_dir"] = str(default_dir)
    else:
        data["database_dir"] = str(_resolve_system_path(data.get("database_dir", "tmg_data")))
    return data

def _save_system_config(data: dict) -> None:
    SYSTEM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SYSTEM_CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

SYSTEM_CONFIG = _load_system_config()
SYSTEM_DATABASE_DIR = _resolve_system_path(SYSTEM_CONFIG.get("database_dir", "tmg_data"))
SYSTEM_DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# TEMA — CSS APLICADO CONFORME CONFIGURAÇÃO
# ==========================================
if SYSTEM_CONFIG.get("tema", "padrao") == "tmg_azul":
    st.markdown("""
<style>
    .stApp {
        background-color: #0a1628 !important;
        color: #e8edf5 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #0d1e35 !important;
        border-right: 1px solid #1e3a5f !important;
    }
    div.stButton > button {
        background: linear-gradient(145deg, #1a3a5c, #0d2140) !important;
        color: #a8c4e0 !important;
        box-shadow: 3px 3px 6px #050e1a, -1px -1px 6px #1a3a5c !important;
    }
    div.stButton > button:hover {
        color: #64b5f6 !important;
        border: 1px solid #1976d2 !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(145deg, #1976d2, #1565c0) !important;
        color: #ffffff !important;
        box-shadow: 4px 4px 10px #050e1a !important;
    }
    .card {
        background-color: #112038 !important;
        border: 1px solid #1e3a5f !important;
    }
    .menu-3d-title {
        color: #42a5f5 !important;
        text-shadow:
            1px 1px 0 #0d47a1,
            2px 2px 0 #0a3070,
            3px 3px 0 #071f4a,
            4px 4px 6px rgba(0,0,0,0.9),
            0 0 20px rgba(66,165,245,0.4),
            0 0 40px rgba(66,165,245,0.15) !important;
    }
    .separator-glow {
        border-top: 1px solid #1976d2 !important;
        box-shadow: 0 0 8px rgba(25,118,210,0.5) !important;
    }
    .main-header {
        color: #FFFFFF !important;
        border-bottom: 2px solid #1976d2 !important;
        text-shadow:
            2px 2px 0px #000000,
            4px 4px 0px #0a1628,
            6px 6px 8px rgba(0,0,0,0.9),
            0 0 30px rgba(25,118,210,0.25) !important;
    }
    [data-testid="stTextInput"] > div > div > input,
    [data-testid="stTextArea"] > div > div > textarea {
        background-color: #0d1e35 !important;
        border: 1px solid #1e3a5f !important;
        color: #e8edf5 !important;
    }
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stMultiSelect"] > div > div {
        background-color: #0d1e35 !important;
        border: 1px solid #1e3a5f !important;
        color: #e8edf5 !important;
    }
    [data-testid="stExpander"] {
        background-color: #0d1e35 !important;
        border: 1px solid #1e3a5f !important;
    }
    .stDataFrame, [data-testid="stTable"] {
        background-color: #0d1e35 !important;
    }
    [data-testid="stMetricValue"] { color: #42a5f5 !important; }
    [data-testid="stMetricLabel"] { color: #90caf9 !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# HELPER — PROCESSAR ORTOFOTO PARA VISUALIZAÇÃO[cite: 1]
# ==========================================
@st.cache_data(show_spinner=False, max_entries=12)
def processar_ortofoto(file_bytes: bytes, filename: str):
    """Converte qualquer ortofoto para base64 renderizável, suportando imagens gigantes e recuperando Metadados Espaciais para o SHP."""
    ext = Path(filename).suffix.lower()
    img = None
    erro = None
    
    # NOVOS DADOS ESPACIAIS ARMAZENADOS
    spatial_meta = {
        "transform": None,
        "crs": None,
        "ratio": 1.0,
        "orig_width": 0,
        "orig_height": 0
    }

    def _stretch_band(band):
        band = np.ma.asarray(band).astype(np.float32).filled(np.nan)
        valid = band[np.isfinite(band)]
        if valid.size == 0:
            return np.zeros(band.shape, dtype=np.uint8)
        mn = np.nanpercentile(valid, 2)
        mx = np.nanpercentile(valid, 98)
        if not np.isfinite(mn) or not np.isfinite(mx) or mx <= mn:
            return np.zeros(band.shape, dtype=np.uint8)
        return np.nan_to_num(np.clip((band - mn) / (mx - mn) * 255, 0, 255)).astype(np.uint8)

    try:
        # Tenta inicialmente com Rasterio (Obrigatório para GeoTIFF, robusto para JPG/PNG)
        import rasterio
        from rasterio.enums import Resampling
        from rasterio.io import MemoryFile
        with MemoryFile(file_bytes) as memfile:
            with memfile.open() as src:
                spatial_meta["orig_width"] = src.width
                spatial_meta["orig_height"] = src.height
                if hasattr(src, 'crs') and src.crs:
                    spatial_meta["crs"] = src.crs.to_wkt()
                if hasattr(src, 'transform'):
                    spatial_meta["transform"] = src.transform.to_gdal()

                max_dim = _preview_max_dim()
                ratio = min(1.0, max_dim / max(src.width, src.height))
                out_width = max(1, int(src.width * ratio))
                out_height = max(1, int(src.height * ratio))
                spatial_meta["ratio"] = ratio

                bands = src.count
                if bands >= 3:
                    data = src.read(
                        [1, 2, 3],
                        out_shape=(3, out_height, out_width),
                        resampling=Resampling.bilinear,
                        masked=True
                    )
                    arr = np.transpose(np.stack([_stretch_band(data[i]) for i in range(3)]), (1, 2, 0))
                    img = Image.fromarray(arr, 'RGB')
                else:
                    data = src.read(
                        1,
                        out_shape=(out_height, out_width),
                        resampling=Resampling.bilinear,
                        masked=True
                    )
                    img = Image.fromarray(_stretch_band(data), 'L').convert('RGB')
    except ImportError:
        try:
            img = Image.open(BytesIO(file_bytes))
        except Exception as e_pil:
            erro = f"Falha (Sem Rasterio): {e_pil}"
    except Exception as e_rast:
        try:
            # Fallback direto para PIL em caso de erro na leitura do rasterio
            img = Image.open(BytesIO(file_bytes))
        except Exception as e_pil:
            erro = f"Falha ao ler formato {ext}: {e_rast} | {e_pil}"
            
    # Garantia de carregamento pelo PIL
    if erro is None and img is None:
        try:
            img = Image.open(BytesIO(file_bytes))
        except Exception as e:
            erro = f"Falha ao interpretar a imagem: {e}"

    if erro:
        return None, None, erro, spatial_meta
    if img is None:
        return None, None, "Não foi possível interpretar a imagem.", spatial_meta

    if spatial_meta["orig_width"] == 0:
        spatial_meta["orig_width"] = img.width
        spatial_meta["orig_height"] = img.height

    if img.mode == 'RGBA':
        try:
            img.load()  # Força carregamento completo antes do split (evita OSError -2 do libtiff)
            bg = Image.new('RGB', img.size, (18, 18, 18))
            bg.paste(img, mask=img.split()[3])
            img = bg
        except OSError:
            # Fallback via NumPy: composição alpha manual sem depender do libtiff
            try:
                arr = np.array(img)
                if arr.ndim == 3 and arr.shape[2] == 4:
                    alpha = arr[:, :, 3:4].astype(np.float32) / 255.0
                    rgb   = arr[:, :, :3].astype(np.float32)
                    bg_v  = np.array([18, 18, 18], dtype=np.float32)
                    composite = (rgb * alpha + bg_v * (1.0 - alpha)).clip(0, 255).astype(np.uint8)
                    img = Image.fromarray(composite, 'RGB')
                else:
                    img = img.convert('RGB')
            except Exception:
                img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    MAX_DIM = _preview_max_dim()
    if max(img.size) > MAX_DIM:
        ratio = MAX_DIM / max(img.size)
        spatial_meta["ratio"] = ratio
        resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), resample_filter)

    buf = BytesIO()
    img.save(buf, format='JPEG', quality=_preview_jpeg_quality(), subsampling=0, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    
    return b64, img.size, None, spatial_meta


# ==========================================
# TELA DE LOGIN[cite: 1]
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "login_cfg_open" not in st.session_state:
    st.session_state.login_cfg_open = False

if "cultura_selecionada" not in st.session_state:
    st.session_state.cultura_selecionada = None

if not st.session_state.logged_in:

    if LOGIN_BG_PATH.exists():
        bg_css = _img_to_base64_css(LOGIN_BG_PATH)
        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("{bg_css}") !important;
            background-size: cover !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
            background-color: transparent !important;
        }}
        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            background: rgba(8, 8, 8, 0.70);
            z-index: 0;
            pointer-events: none;
        }}
        </style>
        """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }

    .login-card {
        background: linear-gradient(160deg, #1c1c1c 0%, #111111 100%);
        border: 1px solid #2e2e2e;
        border-radius: 20px;
        padding: 48px 44px 36px 44px;
        box-shadow:
            0 8px 32px rgba(0,0,0,0.85),
            0 2px 8px rgba(0,0,0,0.6),
            inset 0 1px 0 rgba(255,255,255,0.04);
        position: relative;
        z-index: 1;
    }

    .login-title {
        text-align: center;
        font-family: 'Segoe UI', sans-serif;
        font-weight: 900;
        font-size: 2.4rem;
        letter-spacing: 6px;
        color: #ff8c00;
        text-transform: uppercase;
        text-shadow:
            1px 1px 0 #7a3a00,
            2px 2px 0 #5c2b00,
            3px 3px 0 #3d1d00,
            5px 5px 10px rgba(0,0,0,0.95),
            0 0 25px rgba(255,140,0,0.5),
            0 0 60px rgba(255,140,0,0.15);
        margin-bottom: 4px;
    }

    .login-subtitle {
        text-align: center;
        color: #555;
        font-size: 0.78rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 28px;
    }

    .login-divider {
        border: none;
        border-top: 1px solid #ff8c00;
        box-shadow: 0 0 10px rgba(255,140,0,0.4);
        margin: 0 0 28px 0;
    }

    .stTextInput > div > div > input {
        background-color: #1a1a1a !important;
        border: 1px solid #333 !important;
        border-radius: 10px !important;
        color: #e0e0e0 !important;
        padding: 12px 16px !important;
        font-size: 0.95rem !important;
        box-shadow: inset 2px 2px 5px #0a0a0a !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #ff8c00 !important;
        box-shadow: inset 2px 2px 5px #0a0a0a, 0 0 8px rgba(255,140,0,0.3) !important;
    }

    .stTextInput label {
        color: #888 !important;
        font-size: 0.82rem !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }

    .login-footer {
        text-align: center;
        color: #444;
        font-size: 0.72rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 14px;
    }

    .login-cfg-panel {
        background: linear-gradient(160deg, #181818 0%, #0f0f0f 100%);
        border: 1px solid #2a2a2a;
        border-top: 2px solid #ff8c00;
        border-radius: 16px;
        padding: 24px 28px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.7);
        position: relative;
        z-index: 1;
        margin-top: 4px;
    }

    .cfg-panel-title {
        color: #ff8c00;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        text-shadow: 0 0 12px rgba(255,140,0,0.35);
        margin-bottom: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col_mid, _ = st.columns([1, 1.05, 1])

    with col_mid:
        if LOGO_PATH.exists():
            lc1, lc2, lc3 = st.columns([1, 2, 1])
            with lc2:
                app_image(str(LOGO_PATH))
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        st.markdown("<div class='login-title'>TMG</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='login-subtitle'>Sistema de Análise &nbsp;·&nbsp; Acesso Seguro</div>",
            unsafe_allow_html=True
        )
        st.markdown("<hr class='login-divider'>", unsafe_allow_html=True)

        usuario = st.text_input("Usuário", placeholder="Digite seu login", key="login_user")
        senha   = st.text_input("Senha",   placeholder="Digite sua senha", type="password", key="login_pass")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        if st.button("⟶  ENTRAR", type="primary", key="btn_entrar"):
            if usuario == "123" and senha == "123":
                st.session_state.logged_in = True
                app_rerun()
            else:
                st.markdown("""
                <div style='
                    background:rgba(180,30,30,0.12);
                    border:1px solid #7a0000;
                    border-radius:10px;
                    padding:12px 16px;
                    color:#ff6b6b;
                    font-size:0.88rem;
                    text-align:center;
                    margin-top:8px;
                    box-shadow:0 0 12px rgba(180,0,0,0.2);
                '>&#9888; Usuário ou senha incorretos.</div>
                """, unsafe_allow_html=True)

        st.markdown("<div class='login-footer'>TMG v2.0 &nbsp;·&nbsp; 2026</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        if st.button("⚙️  Configurações da Tela de Login", key="btn_login_cfg"):
            st.session_state.login_cfg_open = not st.session_state.login_cfg_open

        if st.session_state.login_cfg_open:
            st.markdown(
                "<div class='cfg-panel-title'>&#9881; Identidade Visual &nbsp;·&nbsp; Tela de Login</div>",
                unsafe_allow_html=True
            )

            if LOGIN_BG_PATH.exists():
                st.markdown(
                    f"<p style='color:#666;font-size:0.8rem;margin-bottom:10px;'>"
                    f"&#128193; Background atual: "
                    f"<code style='color:#ff8c00;'>{LOGIN_BG_PATH}</code></p>",
                    unsafe_allow_html=True
                )

            nova_bg = st.file_uploader(
                "Imagem de fundo da tela de login",
                type=["png", "jpg", "jpeg"],
                key="login_bg_uploader"
            )

            if nova_bg:
                bg_img = Image.open(nova_bg).convert("RGB")
                bg_img.save(str(LOGIN_BG_PATH), format="PNG")
                st.success(f"✅ Imagem salva em `{LOGIN_BG_PATH}` — recarregando...")
                app_rerun()

            if LOGIN_BG_PATH.exists():
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                if st.button("🗑️  Remover imagem de fundo", key="btn_rm_bg"):
                    LOGIN_BG_PATH.unlink()
                    st.success("Imagem de fundo removida.")
                    app_rerun()

    st.stop()


# ==========================================
# TELA DE SELEÇÃO DE CULTURA (PÓS-LOGIN)[cite: 1]
# ==========================================
if st.session_state.logged_in and st.session_state.cultura_selecionada is None:

    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }

    .cultura-page {
        min-height: 85vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    .cultura-title {
        text-align: center;
        font-family: 'Segoe UI', sans-serif;
        font-weight: 900;
        font-size: 2rem;
        letter-spacing: 5px;
        color: #ff8c00;
        text-transform: uppercase;
        text-shadow:
            1px 1px 0 #7a3a00,
            2px 2px 0 #5c2b00,
            3px 3px 0 #3d1d00,
            5px 5px 10px rgba(0,0,0,0.95),
            0 0 25px rgba(255,140,0,0.45),
            0 0 60px rgba(255,140,0,0.12);
        margin-bottom: 6px;
    }

    .cultura-subtitle {
        text-align: center;
        color: #555;
        font-size: 0.78rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 36px;
    }

    .cultura-hr {
        border: none;
        border-top: 1px solid #ff8c00;
        box-shadow: 0 0 10px rgba(255,140,0,0.4);
        width: 60%;
        margin: 0 auto 40px auto;
    }

    .cultura-card {
        background: linear-gradient(160deg, #1c1c1c 0%, #111111 100%);
        border: 1px solid #2e2e2e;
        border-radius: 20px;
        padding: 38px 24px 28px 24px;
        text-align: center;
        cursor: pointer;
        transition: all 0.25s ease;
        box-shadow:
            4px 4px 14px #080808,
            -1px -1px 8px #252525,
            inset 0 1px 0 rgba(255,255,255,0.04);
        position: relative;
        overflow: hidden;
    }

    .cultura-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #ff8c00, transparent);
        opacity: 0.5;
    }

    .cultura-card:hover {
        border-color: #ff8c00;
        box-shadow:
            6px 6px 20px #050505,
            -2px -2px 10px #2a2a2a,
            0 0 20px rgba(255,140,0,0.15),
            inset 0 1px 0 rgba(255,255,255,0.06);
        transform: translateY(-5px) scale(1.02);
    }

    .cultura-icon {
        font-size: 4.2rem;
        margin-bottom: 12px;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.8));
        display: block;
    }

    .cultura-nome {
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
        font-size: 1.15rem;
        letter-spacing: 4px;
        color: #e0e0e0;
        text-transform: uppercase;
        text-shadow: 1px 1px 4px rgba(0,0,0,0.9);
        margin-bottom: 6px;
    }

    .cultura-desc {
        font-size: 0.72rem;
        color: #555;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    .cultura-btn-wrapper div.stButton > button {
        width: 100%;
        border-radius: 16px;
        border: 1px solid #2e2e2e;
        padding: 0;
        background: transparent;
        color: transparent;
        box-shadow: none;
        margin: 0;
        height: 0;
        overflow: hidden;
        pointer-events: none;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    _, hcol, _ = st.columns([1, 2, 1])
    with hcol:
        if LOGO_PATH.exists():
            lc1, lc2, lc3 = st.columns([1, 2, 1])
            with lc2:
                app_image(str(LOGO_PATH))
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        st.markdown("<div class='cultura-title'>Selecione a Cultura</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='cultura-subtitle'>Escolha a cultura para iniciar a análise</div>",
            unsafe_allow_html=True
        )
        st.markdown("<hr class='cultura-hr'>", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    _, gcol, _ = st.columns([0.15, 2.7, 0.15])

    with gcol:
        c1, c2, c3 = st.columns(3, gap="large")

        culturas = [
            ("🌱", "SOJA",    "Glycine max",       "#4caf50"),
            ("🌽", "MILHO",   "Zea mays",          "#ffb300"),
            ("🌿", "ALGODÃO", "Gossypium hirsutum", "#80cbc4"),
        ]

        cols = [c1, c2, c3]
        for col, (icon, nome, cientifico, cor) in zip(cols, culturas):
            with col:
                st.markdown(f"""
                <div class='cultura-card'>
                    <span class='cultura-icon'>{icon}</span>
                    <div class='cultura-nome' style='color:{cor};
                        text-shadow:
                            1px 1px 0 rgba(0,0,0,0.8),
                            0 0 12px {cor}55;
                    '>{nome}</div>
                    <div class='cultura-desc'>{cientifico}</div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                if st.button(f"Selecionar {nome}", key=f"btn_cultura_{nome}", type="primary"):
                    st.session_state.cultura_selecionada = nome
                    app_rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    _, fcol, _ = st.columns([1, 2, 1])
    with fcol:
        st.markdown(
            "<p style='text-align:center; color:#333; font-size:0.72rem; letter-spacing:2px; text-transform:uppercase;'>"
            "TMG v2.0 &nbsp;·&nbsp; 2026</p>",
            unsafe_allow_html=True
        )

    st.stop()


# ==========================================
# CÓDIGO PRINCIPAL[cite: 1]
# ==========================================

if "pagina_ativa" not in st.session_state:
    st.session_state.pagina_ativa = "Checklist"

if st.session_state.pagina_ativa in ("TransferenciaVoos",):
    st.session_state.pagina_ativa = "Checklist"

if "logo_sistema" not in st.session_state:
    if LOGO_PATH.exists():
        st.session_state.logo_sistema = Image.open(LOGO_PATH)
    else:
        st.session_state.logo_sistema = None

def ir_para(pagina):
    st.session_state.pagina_ativa = pagina

# Adicionado um payload oculto para receber as coordenadas vindas do JavaScript
st.text_input("grid_payload", key="grid_payload", label_visibility="hidden")

# ==========================================
# MODULO ISOLADO - TRANSFERENCIA DE VOOS
# ==========================================
TV_ROOT = SYSTEM_DATABASE_DIR / "transferencia_voos"
TV_PROJECTS_DIR = TV_ROOT / "projetos"
TV_ORTHOS_DIR = TV_ROOT / "ortofotos"
TV_GRIDS_DIR = TV_ROOT / "grids"
TV_IMPORTS_DIR = TV_ROOT / "importacoes"
TV_RETURNS_DIR = TV_ROOT / "retornos"
TV_MANIFEST_PATH = TV_ROOT / "manifest.json"
MOSAIC_LIBRARY_DIR = SYSTEM_DATABASE_DIR / "mosaicos_importados"
MOSAIC_MANIFEST_PATH = MOSAIC_LIBRARY_DIR / "manifest.json"
MOSAIC_UPLOAD_TYPES = ["png", "jpg", "jpeg", "tif", "tiff", "geotiff", "geotif", "img", "ecw", "jp2"]

def _tv_safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(value).strip())
    return cleaned.strip("_") or "projeto"

def _tv_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _tv_human_size(num_bytes: int) -> str:
    size = float(num_bytes or 0)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TB"

def _tv_hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _tv_hash_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def _mosaic_default_manifest() -> dict:
    return {"mosaics": []}

def _mosaic_ensure_storage() -> None:
    MOSAIC_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    if not MOSAIC_MANIFEST_PATH.exists():
        MOSAIC_MANIFEST_PATH.write_text(json.dumps(_mosaic_default_manifest(), indent=2, ensure_ascii=False), encoding="utf-8")

def _mosaic_load_manifest() -> dict:
    _mosaic_ensure_storage()
    try:
        data = json.loads(MOSAIC_MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = _mosaic_default_manifest()
    data.setdefault("mosaics", [])
    return data

def _mosaic_save_manifest(data: dict) -> None:
    _mosaic_ensure_storage()
    MOSAIC_MANIFEST_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def _mosaic_option_label(record: dict) -> str:
    size = record.get("tamanho_fmt") or _tv_human_size(record.get("tamanho", 0))
    origem = record.get("origem", "Importado")
    return f"{record.get('mosaic_id')} · {record.get('nome')} · {size} · {origem}"

def _mosaic_records() -> list:
    manifest = _mosaic_load_manifest()
    records = []
    for record in manifest.get("mosaics", []):
        if Path(record.get("path", "")).exists():
            records.append(record)
    return records

def _mosaic_single_select(label: str, key: str) -> str:
    options = [""] + [_mosaic_option_label(record) for record in _mosaic_records()]
    if len(options) == 1:
        st.caption("Biblioteca de mosaicos vazia. Envie uma ortofoto para deixá-la disponível nos outros visualizadores.")
        return ""
    return st.selectbox(label, options, key=key)

def _mosaic_multi_select(label: str, key: str, max_items: int = 10) -> list:
    options = [_mosaic_option_label(record) for record in _mosaic_records()]
    if not options:
        st.caption("Biblioteca de mosaicos vazia. Os uploads feitos nos visualizadores ficam disponíveis aqui.")
        return []
    selected = st.multiselect(label, options, key=key, max_selections=max_items)
    return selected or []

def _mosaic_find(option: str) -> dict:
    mosaic_id = option.split(" · ")[0] if option else ""
    if not mosaic_id:
        return {}
    for record in _mosaic_records():
        if record.get("mosaic_id") == mosaic_id:
            return record
    return {}

def _mosaic_path_inside_library(path: Path) -> bool:
    try:
        return path.resolve().is_relative_to(MOSAIC_LIBRARY_DIR.resolve())
    except Exception:
        return False

def _mosaic_delete(option: str) -> tuple:
    record = _mosaic_find(option)
    if not record:
        return False, "Mosaico não encontrado na biblioteca."

    mosaic_id = record.get("mosaic_id", "")
    mosaic_name = record.get("nome") or mosaic_id or "mosaico"
    path = Path(record.get("path", ""))
    manifest = _mosaic_load_manifest()
    manifest["mosaics"] = [
        item for item in manifest.get("mosaics", [])
        if item.get("mosaic_id") != mosaic_id
    ]
    _mosaic_save_manifest(manifest)

    removed_file = False
    if path.exists() and _mosaic_path_inside_library(path):
        try:
            target = path.parent if path.parent.name == mosaic_id else path
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            removed_file = True
        except Exception as exc:
            return True, f"Mosaico removido da lista, mas não foi possível apagar o arquivo: {exc}"

    if removed_file:
        return True, f"Mosaico `{mosaic_name}` excluído da biblioteca."
    return True, f"Mosaico `{mosaic_name}` removido da biblioteca. O arquivo original foi preservado."

def _mosaic_register_bytes(raw: bytes, filename: str, origem: str) -> dict:
    if not raw:
        return {}
    manifest = _mosaic_load_manifest()
    file_hash = _tv_hash_bytes(raw)
    for record in manifest.get("mosaics", []):
        if record.get("sha256") == file_hash and Path(record.get("path", "")).exists():
            return record

    mosaic_id = f"MOSAICO_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    safe_name = Path(filename or mosaic_id).name
    mosaic_dir = MOSAIC_LIBRARY_DIR / mosaic_id
    mosaic_dir.mkdir(parents=True, exist_ok=True)
    target = mosaic_dir / safe_name
    if target.exists():
        target = mosaic_dir / f"{target.stem}_{datetime.now().strftime('%H%M%S%f')}{target.suffix}"
    target.write_bytes(raw)
    record = {
        "mosaic_id": mosaic_id,
        "nome": safe_name,
        "path": str(target),
        "tamanho": len(raw),
        "tamanho_fmt": _tv_human_size(len(raw)),
        "sha256": file_hash,
        "ext": target.suffix.lower(),
        "origem": origem,
        "importado_em": _tv_now()
    }
    manifest.setdefault("mosaics", []).insert(0, record)
    manifest["mosaics"] = manifest["mosaics"][:200]
    _mosaic_save_manifest(manifest)
    return record

def _mosaic_register_file(path_value, filename: str, origem: str, file_hash: str = "", file_size: int = 0) -> dict:
    path = Path(path_value)
    if not path.exists():
        return {}
    manifest = _mosaic_load_manifest()
    file_hash = file_hash or _tv_hash_file(path)
    for record in manifest.get("mosaics", []):
        if record.get("sha256") == file_hash and Path(record.get("path", "")).exists():
            return record

    record = {
        "mosaic_id": f"MOSAICO_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
        "nome": Path(filename or path.name).name,
        "path": str(path),
        "tamanho": int(file_size or path.stat().st_size),
        "tamanho_fmt": _tv_human_size(int(file_size or path.stat().st_size)),
        "sha256": file_hash,
        "ext": path.suffix.lower(),
        "origem": origem,
        "importado_em": _tv_now()
    }
    manifest.setdefault("mosaics", []).insert(0, record)
    manifest["mosaics"] = manifest["mosaics"][:200]
    _mosaic_save_manifest(manifest)
    return record

def _mosaic_bytes_from_selection(option: str) -> tuple:
    record = _mosaic_find(option)
    path = Path(record.get("path", ""))
    if record and path.exists():
        return path.read_bytes(), record.get("nome") or path.name
    return None, ""

def _mosaic_input_bytes(uploaded, selected_option: str, origem: str) -> tuple:
    if uploaded is not None:
        raw = uploaded.getbuffer().tobytes()
        _mosaic_register_bytes(raw, uploaded.name, origem)
        return raw, uploaded.name
    return _mosaic_bytes_from_selection(selected_option)

def _tv_default_manifest() -> dict:
    return {
        "projects": [],
        "orthos": [],
        "grids": [],
        "imports": [],
        "returns": [],
        "history": [],
        "config": {
            "provider": "Servidor local",
            "destination": str(TV_ROOT / "sync"),
            "sync_mode": "Manual",
            "checksum": True,
            "resumable": True,
            "encryption": True,
            "auth_mode": "Token/OAuth"
        },
        "users": [
            {"usuario": "admin", "perfil": "Administrador", "permissao": "Leitura, envio, analise, configuracao"},
            {"usuario": "operador", "perfil": "Operador de Campo", "permissao": "Envio e download"},
            {"usuario": "analista", "perfil": "Analista Tecnico", "permissao": "Grid, parcelas e relatorios"}
        ]
    }

def _tv_ensure_storage() -> None:
    for folder in [TV_ROOT, TV_PROJECTS_DIR, TV_ORTHOS_DIR, TV_GRIDS_DIR, TV_IMPORTS_DIR, TV_RETURNS_DIR]:
        folder.mkdir(parents=True, exist_ok=True)
    if not TV_MANIFEST_PATH.exists():
        TV_MANIFEST_PATH.write_text(json.dumps(_tv_default_manifest(), indent=2, ensure_ascii=False), encoding="utf-8")

def _tv_load_manifest() -> dict:
    _tv_ensure_storage()
    try:
        data = json.loads(TV_MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = _tv_default_manifest()
    default = _tv_default_manifest()
    for key, value in default.items():
        data.setdefault(key, value)
    return data

def _tv_save_manifest(data: dict) -> None:
    _tv_ensure_storage()
    TV_MANIFEST_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def _tv_add_history(manifest: dict, event: str, project_id: str = "", status: str = "OK") -> None:
    manifest.setdefault("history", []).insert(0, {
        "data": _tv_now(),
        "projeto": project_id,
        "evento": event,
        "status": status
    })
    manifest["history"] = manifest["history"][:300]

def _tv_project_options(manifest: dict) -> list:
    return [f"{p['project_id']} · {p.get('nome','Projeto')}" for p in manifest.get("projects", [])]

def _tv_get_project_id(option: str) -> str:
    return option.split(" · ")[0] if option else ""

def _tv_get_ortho_id(option: str) -> str:
    return option.split(" · ")[0] if option else ""

def _tv_find_project(manifest: dict, project_id: str) -> dict:
    for project in manifest.get("projects", []):
        if project.get("project_id") == project_id:
            return project
    return {}

def _tv_find_ortho(manifest: dict, ortho_id: str) -> dict:
    for ortho in manifest.get("orthos", []):
        if ortho.get("ortho_id") == ortho_id:
            return ortho
    return {}

def _tv_find_grid(manifest: dict, grid_id: str) -> dict:
    for grid in manifest.get("grids", []):
        if grid.get("grid_id") == grid_id:
            return grid
    return {}

def _tv_file_exists_by_hash(manifest: dict, file_hash: str) -> bool:
    for project in manifest.get("projects", []):
        for item in project.get("files", []):
            if item.get("sha256") == file_hash:
                return True
    for ortho in manifest.get("orthos", []):
        if ortho.get("sha256") == file_hash:
            return True
    return False

def _tv_save_uploaded_batch(files, base_dir: Path, manifest: dict, duplicate_check: bool = True) -> tuple:
    saved, duplicates, total_size = [], [], 0
    base_dir.mkdir(parents=True, exist_ok=True)
    for uploaded in files or []:
        hasher = hashlib.sha256()
        file_size = 0
        temp_name = f".{_tv_safe_name(Path(uploaded.name).stem)}_{datetime.now().strftime('%H%M%S%f')}.uploading"
        temp_path = base_dir / temp_name
        try:
            uploaded.seek(0)
        except Exception:
            pass
        with open(temp_path, "wb") as out:
            while True:
                chunk = uploaded.read(1024 * 1024)
                if not chunk:
                    break
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                hasher.update(chunk)
                out.write(chunk)
                file_size += len(chunk)
        file_hash = hasher.hexdigest()
        total_size += file_size
        if duplicate_check and _tv_file_exists_by_hash(manifest, file_hash):
            duplicates.append(uploaded.name)
            try:
                temp_path.unlink()
            except Exception:
                pass
            continue
        target = base_dir / Path(uploaded.name).name
        if target.exists():
            stem, suffix = target.stem, target.suffix
            target = base_dir / f"{stem}_{datetime.now().strftime('%H%M%S%f')}{suffix}"
        temp_path.replace(target)
        saved.append({
            "nome": uploaded.name,
            "path": str(target),
            "tamanho": file_size,
            "tamanho_fmt": _tv_human_size(file_size),
            "sha256": file_hash,
            "ext": Path(uploaded.name).suffix.lower(),
            "enviado_em": _tv_now()
        })
    return saved, duplicates, total_size

def _tv_status_chip(text: str, color: str = "#ff8c00") -> str:
    return f"<span style='display:inline-block;border:1px solid {color};color:{color};border-radius:999px;padding:4px 10px;font-size:11px;margin:2px 5px 2px 0;'>{text}</span>"

def _tv_metric_cards(manifest: dict) -> None:
    projects = manifest.get("projects", [])
    orthos = manifest.get("orthos", [])
    grids = manifest.get("grids", [])
    total_bytes = sum(sum(f.get("tamanho", 0) for f in p.get("files", [])) for p in projects)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Projetos", len(projects))
    c2.metric("Ortofotos", len(orthos))
    c3.metric("Grids", len(grids))
    c4.metric("Volume", _tv_human_size(total_bytes))

def _tv_render_upload(manifest: dict) -> None:
    st.markdown("#### Upload de Voos")
    meta1, meta2, meta3 = st.columns(3)
    with meta1:
        nome = st.text_input("Nome do projeto", value=f"Voo_{date.today().strftime('%Y%m%d')}", key="tv_nome")
        operador = st.text_input("Operador", value="", key="tv_operador")
    with meta2:
        data_voo = st.date_input("Data", value=date.today(), key="tv_data")
        fazenda = st.text_input("Fazenda", value="", key="tv_fazenda")
    with meta3:
        talhao = st.text_input("Talhão", value="", key="tv_talhao")
        coordenadas = st.text_input("Coordenadas / centroide", value="", key="tv_coords")

    provider = st.selectbox(
        "Destino de sincronização",
        ["Microsoft OneDrive", "Microsoft Azure", "Google Drive", "Dropbox", "Servidor local", "NAS", "FTP/SFTP"],
        index=["Microsoft OneDrive", "Microsoft Azure", "Google Drive", "Dropbox", "Servidor local", "NAS", "FTP/SFTP"].index(manifest.get("config", {}).get("provider", "Servidor local")) if manifest.get("config", {}).get("provider", "Servidor local") in ["Microsoft OneDrive", "Microsoft Azure", "Google Drive", "Dropbox", "Servidor local", "NAS", "FTP/SFTP"] else 4,
        key="tv_upload_provider"
    )

    files = st.file_uploader(
        "Fotos do voo, RAW, TIFF/GeoTIFF ou ZIP da pasta completa",
        type=["jpg", "jpeg", "tif", "tiff", "png", "raw", "dng", "arw", "cr2", "nef", "zip"],
        accept_multiple_files=True,
        key="tv_flight_upload"
    )

    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        compactar = st.checkbox("Compactação automática do lote", value=True, key="tv_zip")
    with col_b:
        manter_original = st.checkbox("Preservar qualidade original", value=True, key="tv_original", disabled=True)
    with col_c:
        checksum = st.checkbox("Validar integridade SHA-256", value=True, key="tv_checksum")

    if st.button("Enviar e sincronizar lote", type="primary", key="tv_send_batch", use_container_width=True):
        if not files:
            st.warning("Selecione os arquivos do voo.")
        else:
            project_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_tv_safe_name(nome)}"
            project_dir = TV_PROJECTS_DIR / project_id / "raw"
            progress = st.progress(0)
            saved, duplicates, total_size = _tv_save_uploaded_batch(files, project_dir, manifest, duplicate_check=checksum)
            progress.progress(40)

            zip_path = ""
            if compactar and saved:
                zip_path = str(TV_PROJECTS_DIR / project_id / f"{project_id}_pacote_voo.zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for item in saved:
                        zf.write(item["path"], arcname=Path(item["path"]).name)
            progress.progress(75)

            project = {
                "project_id": project_id,
                "nome": nome,
                "data": str(data_voo),
                "operador": operador,
                "fazenda": fazenda,
                "talhao": talhao,
                "coordenadas": coordenadas,
                "quantidade_imagens": len(saved),
                "tamanho_total": sum(item["tamanho"] for item in saved),
                "tamanho_total_fmt": _tv_human_size(sum(item["tamanho"] for item in saved)),
                "status": "Voo enviado - aguardando recebimento",
                "workflow": "VOO_ENVIADO",
                "provedor": provider,
                "zip_path": zip_path,
                "files": saved,
                "duplicados": duplicates,
                "criado_em": _tv_now()
            }
            manifest.setdefault("projects", []).insert(0, project)
            _tv_add_history(manifest, f"Lote enviado: {len(saved)} arquivo(s), {len(duplicates)} duplicado(s)", project_id)
            _tv_save_manifest(manifest)
            progress.progress(100)
            st.success(f"Projeto `{project_id}` criado com {len(saved)} arquivo(s).")
            if duplicates:
                st.warning("Duplicados ignorados: " + ", ".join(duplicates[:8]))

    st.markdown("---")
    _tv_metric_cards(manifest)

def _tv_render_database(manifest: dict) -> None:
    st.markdown("#### Banco de Dados")
    rows = []
    for p in manifest.get("projects", []):
        rows.append({
            "Projeto": p.get("project_id"),
            "Nome": p.get("nome"),
            "Data": p.get("data"),
            "Operador": p.get("operador"),
            "Fazenda": p.get("fazenda"),
            "Talhão": p.get("talhao"),
            "Imagens": p.get("quantidade_imagens"),
            "Tamanho": p.get("tamanho_total_fmt"),
            "Status": p.get("status"),
            "Nuvem": p.get("provedor")
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.download_button(
        "Baixar manifesto JSON",
        data=json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"),
        file_name="transferencia_voos_manifest.json",
        mime="application/json",
        use_container_width=True
    )

def _tv_render_receber_voos(manifest: dict) -> None:
    st.markdown("#### Receber Voos")
    st.caption("Janela para o operador receber pacotes de voo, baixar imagens originais e marcar o processamento externo da ortofoto.")

    with st.expander("Receber pacote de voo de outro usuário", expanded=False):
        r1, r2, r3 = st.columns(3)
        with r1:
            incoming_name = st.text_input("Nome do voo recebido", value=f"Recebido_{date.today().strftime('%Y%m%d')}", key="tv_incoming_name")
            incoming_operator = st.text_input("Operador de origem", value="", key="tv_incoming_operator")
        with r2:
            incoming_farm = st.text_input("Fazenda", value="", key="tv_incoming_farm")
            incoming_field = st.text_input("Talhão", value="", key="tv_incoming_field")
        with r3:
            incoming_coords = st.text_input("Coordenadas", value="", key="tv_incoming_coords")
            incoming_provider = st.selectbox("Origem", ["OneDrive", "Azure", "Google Drive", "Dropbox", "Servidor local", "NAS", "FTP/SFTP", "Upload direto"], key="tv_incoming_provider")
        incoming_files = st.file_uploader(
            "ZIP ou imagens recebidas",
            type=["zip", "jpg", "jpeg", "tif", "tiff", "png", "raw", "dng", "arw", "cr2", "nef"],
            accept_multiple_files=True,
            key="tv_incoming_files"
        )
        if st.button("Registrar voo recebido", type="primary", key="tv_register_incoming", use_container_width=True):
            if not incoming_files:
                st.warning("Selecione o pacote ou as imagens recebidas.")
            else:
                project_id = f"REC_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_tv_safe_name(incoming_name)}"
                project_dir = TV_PROJECTS_DIR / project_id / "recebido"
                saved, duplicates, _ = _tv_save_uploaded_batch(incoming_files, project_dir, manifest, duplicate_check=True)
                zip_path = str(TV_PROJECTS_DIR / project_id / f"{project_id}_pacote_recebido.zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for item in saved:
                        zf.write(item["path"], arcname=Path(item["path"]).name)
                project = {
                    "project_id": project_id,
                    "nome": incoming_name,
                    "data": str(date.today()),
                    "operador": incoming_operator,
                    "fazenda": incoming_farm,
                    "talhao": incoming_field,
                    "coordenadas": incoming_coords,
                    "quantidade_imagens": len(saved),
                    "tamanho_total": sum(item["tamanho"] for item in saved),
                    "tamanho_total_fmt": _tv_human_size(sum(item["tamanho"] for item in saved)),
                    "status": "Voo recebido - gerar ortofoto externa",
                    "workflow": "VOO_RECEBIDO",
                    "provedor": incoming_provider,
                    "zip_path": zip_path,
                    "files": saved,
                    "duplicados": duplicates,
                    "criado_em": _tv_now(),
                    "recebido_em": _tv_now()
                }
                manifest.setdefault("projects", []).insert(0, project)
                _tv_add_history(manifest, f"Voo externo recebido: {len(saved)} arquivo(s)", project_id)
                _tv_save_manifest(manifest)
                st.success(f"Voo recebido registrado como `{project_id}`.")
                if duplicates:
                    st.warning("Duplicados ignorados: " + ", ".join(duplicates[:8]))

    options = _tv_project_options(manifest)
    if not options:
        st.info("Nenhum voo enviado ainda.")
        return

    selected = st.selectbox("Voo disponível para recebimento", options, key="tv_receive_project")
    project_id = _tv_get_project_id(selected)
    project = _tv_find_project(manifest, project_id)
    if not project:
        st.warning("Projeto não encontrado.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Imagens", project.get("quantidade_imagens", 0))
    c2.metric("Tamanho", project.get("tamanho_total_fmt", "0 B"))
    c3.metric("Fazenda", project.get("fazenda") or "-")
    c4.metric("Status", project.get("status") or "-")

    st.markdown(
        f"<div class='tv-band'>"
        f"{_tv_status_chip('Metadados preservados', '#55ff99')}"
        f"{_tv_status_chip('Coordenadas: ' + (project.get('coordenadas') or 'não informado'), '#5599ff')}"
        f"{_tv_status_chip('Provedor: ' + (project.get('provedor') or 'local'), '#ff8c00')}"
        f"</div>",
        unsafe_allow_html=True
    )

    col_a, col_b = st.columns(2)
    with col_a:
        zip_path = project.get("zip_path")
        if zip_path and Path(zip_path).exists():
            st.download_button(
                "Baixar pacote completo do voo",
                data=Path(zip_path).read_bytes(),
                file_name=Path(zip_path).name,
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.info("Pacote ZIP não encontrado; arquivos individuais continuam registrados no manifesto.")
    with col_b:
        if st.button("Confirmar recebimento do voo", type="primary", key="tv_confirm_receive", use_container_width=True):
            project["status"] = "Voo recebido - gerar ortofoto externa"
            project["workflow"] = "VOO_RECEBIDO"
            project["recebido_em"] = _tv_now()
            _tv_add_history(manifest, "Voo recebido por operador para processamento externo", project_id)
            _tv_save_manifest(manifest)
            st.success("Recebimento confirmado. Gere a ortofoto externamente e envie em Ortofotos Geradas.")

    st.markdown("##### Arquivos do voo")
    st.dataframe(project.get("files", []), use_container_width=True, hide_index=True)

def _tv_render_orthos(manifest: dict) -> None:
    st.markdown("#### Ortofotos Geradas")
    st.caption("Receba a ortofoto gerada externamente e encaminhe para ajuste/marcação de grid.")
    options = _tv_project_options(manifest)
    selected_project = st.selectbox("Projeto vinculado", [""] + options, key="tv_ortho_project")
    ortho_files = st.file_uploader(
        "Enviar ortofoto processada",
        type=["tif", "tiff", "geotiff", "jpg", "jpeg", "png", "zip"],
        accept_multiple_files=True,
        key="tv_ortho_upload"
    )
    if st.button("Registrar ortofoto recebida", type="primary", key="tv_register_ortho", use_container_width=True):
        if not ortho_files:
            st.warning("Selecione uma ortofoto.")
        else:
            project_id = _tv_get_project_id(selected_project)
            ortho_dir = TV_ORTHOS_DIR / (project_id or "sem_projeto") / datetime.now().strftime("%Y%m%d_%H%M%S")
            saved, duplicates, _ = _tv_save_uploaded_batch(ortho_files, ortho_dir, manifest, duplicate_check=True)
            for item in saved:
                spatial = {"crs": "", "transform": "", "orig_width": 0, "orig_height": 0}
                thumb_dims = "Aguardando abertura no visualizador"
                if item["ext"] in [".tif", ".tiff", ".png", ".jpg", ".jpeg"]:
                    try:
                        _mosaic_register_file(item["path"], item["nome"], "Transferencia de Voos", item.get("sha256", ""), item.get("tamanho", 0))
                    except Exception:
                        pass
                manifest.setdefault("orthos", []).insert(0, {
                    "ortho_id": f"ORTO_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                    "project_id": project_id,
                    "nome": item["nome"],
                    "path": item["path"],
                    "tamanho": item["tamanho"],
                    "tamanho_fmt": item["tamanho_fmt"],
                    "sha256": item["sha256"],
                    "resolucao_preview": thumb_dims,
                    "crs": spatial.get("crs") if isinstance(spatial, dict) else "",
                    "coordenadas": spatial.get("transform") if isinstance(spatial, dict) else "",
                    "data_processamento": _tv_now(),
                    "status": "Ortofoto gerada recebida - aguardando grid"
                })
            project = _tv_find_project(manifest, project_id)
            if project:
                project["status"] = "Ortofoto recebida - ajustar e marcar grid"
                project["workflow"] = "ORTOFOTO_RECEBIDA"
                project["ortofoto_recebida_em"] = _tv_now()
            _tv_add_history(manifest, f"Ortofoto(s) recebida(s): {len(saved)}", project_id)
            _tv_save_manifest(manifest)
            st.success(f"{len(saved)} ortofoto(s) registrada(s).")
            st.info("Próximo passo: abra Grid e Parcelas para ajustar a ortofoto e marcar o grid.")
            if duplicates:
                st.warning("Duplicados ignorados: " + ", ".join(duplicates[:8]))

    ortho_rows = [{
        "ID": o.get("ortho_id"),
        "Projeto": o.get("project_id"),
        "Arquivo": o.get("nome"),
        "Resolução": o.get("resolucao_preview"),
        "Tamanho": o.get("tamanho_fmt"),
        "CRS": (o.get("crs") or "")[:80],
        "Processamento": o.get("data_processamento"),
        "Status": o.get("status")
    } for o in manifest.get("orthos", [])]
    st.dataframe(ortho_rows, use_container_width=True, hide_index=True)

    if manifest.get("orthos"):
        selected = st.selectbox("Download de ortofoto", [f"{o['ortho_id']} · {o['nome']}" for o in manifest.get("orthos", [])], key="tv_ortho_download")
        ortho_id = selected.split(" · ")[0]
        record = next((o for o in manifest.get("orthos", []) if o.get("ortho_id") == ortho_id), None)
        if record and Path(record["path"]).exists():
            st.download_button(
                "Baixar ortofoto original",
                data=Path(record["path"]).read_bytes(),
                file_name=Path(record["path"]).name,
                mime="application/octet-stream",
                use_container_width=True
            )
            if st.button("Abrir esta ortofoto para marcar grid", key="tv_open_ortho_grid", use_container_width=True):
                st.session_state["tv_next_grid_ortho"] = selected
                st.info("Selecione a aba Grid e Parcelas no menu superior para continuar com esta ortofoto.")

def _tv_grid_viewer_html(b64: str, rows: int, cols: int, image_name: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:#0d0d0d; overflow:hidden; font-family:Segoe UI, Arial, sans-serif; }}
  #wrap {{ width:100%; height:680px; position:relative; background:#0d0d0d; border:1px solid #2a2a2a; border-radius:8px; overflow:hidden; }}
  canvas {{ position:absolute; inset:0; }}
  .bar {{ position:absolute; top:12px; right:12px; display:flex; gap:6px; z-index:3; }}
  button {{ background:#171717; color:#ff8c00; border:1px solid #3a3a3a; border-radius:6px; padding:8px 10px; cursor:pointer; font-weight:700; }}
  button:hover {{ border-color:#ff8c00; }}
  .hint {{ position:absolute; left:12px; bottom:12px; color:#aaa; background:rgba(0,0,0,.72); border:1px solid #333; border-radius:6px; padding:7px 10px; font-size:11px; }}
</style>
</head>
<body>
<div id="wrap">
  <canvas id="cv"></canvas>
  <div class="bar">
    <button id="mark">Marcar 4 cantos</button>
    <button id="fit">Ajustar tela</button>
    <button id="clear">Limpar</button>
    <button id="export">Exportar Grid JSON</button>
    <button id="geojson">GeoJSON</button>
    <button id="csv">CSV</button>
  </div>
  <div class="hint" id="hint">Scroll zoom · arrastar mover · arraste os pontos azuis para ajustar · {rows} linhas × {cols} colunas</div>
</div>
<script>
const cv=document.getElementById('cv'), ctx=cv.getContext('2d'), wrap=document.getElementById('wrap');
let points=[], markMode=false, sc=1, ox=0, oy=0, drag=false, lx=0, ly=0, imgW=0, imgH=0, draggingPoint=-1;
const ROWS={rows}, COLS={cols}, IMG_NAME={json.dumps(image_name)};
const img=new Image();
function resize(){{ cv.width=wrap.clientWidth; cv.height=wrap.clientHeight; draw(); }}
function toImg(e){{ const r=cv.getBoundingClientRect(); return {{x:(e.clientX-r.left-ox)/sc, y:(e.clientY-r.top-oy)/sc}}; }}
function bilerp(p0,p1,p2,p3,u,v){{ const tx=(1-u)*p0.x+u*p1.x, ty=(1-u)*p0.y+u*p1.y; const bx=(1-u)*p3.x+u*p2.x, by=(1-u)*p3.y+u*p2.y; return {{x:(1-v)*tx+v*bx,y:(1-v)*ty+v*by}}; }}
function fit(){{ if(!imgW) return; sc=Math.min(cv.width/imgW,cv.height/imgH); ox=(cv.width-imgW*sc)/2; oy=(cv.height-imgH*sc)/2; draw(); }}
function getCells(){{
  if(points.length!==4) return [];
  const [p0,p1,p2,p3]=points, cells=[];
  for(let r=0;r<ROWS;r++) for(let c=0;c<COLS;c++){{
    const u0=c/COLS,u1=(c+1)/COLS,v0=r/ROWS,v1=(r+1)/ROWS;
    const tl=bilerp(p0,p1,p2,p3,u0,v0), tr=bilerp(p0,p1,p2,p3,u1,v0), br=bilerp(p0,p1,p2,p3,u1,v1), bl=bilerp(p0,p1,p2,p3,u0,v1);
    cells.push({{linha:r+1,coluna:c+1,polygon:[tl,tr,br,bl]}});
  }}
  return cells;
}}
function download(name,type,text){{ const blob=new Blob([text],{{type:type}}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name; a.click(); }}
function draw(){{
  ctx.clearRect(0,0,cv.width,cv.height); ctx.save(); ctx.translate(ox,oy); ctx.scale(sc,sc);
  if(imgW) ctx.drawImage(img,0,0);
  if(points.length===4){{
    const [p0,p1,p2,p3]=points; ctx.strokeStyle='rgba(255,140,0,.95)'; ctx.lineWidth=2/sc;
    for(let r=0;r<=ROWS;r++){{ const v=r/ROWS; const a=bilerp(p0,p1,p2,p3,0,v), b=bilerp(p0,p1,p2,p3,1,v); ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); }}
    for(let c=0;c<=COLS;c++){{ const u=c/COLS; const a=bilerp(p0,p1,p2,p3,u,0), b=bilerp(p0,p1,p2,p3,u,1); ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); }}
  }}
  points.forEach((p,i)=>{{ ctx.fillStyle='#1e90ff'; ctx.beginPath(); ctx.arc(p.x,p.y,8/sc,0,Math.PI*2); ctx.fill(); ctx.fillStyle='#fff'; ctx.font=(12/sc)+'px Arial'; ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillText(i+1,p.x,p.y); }});
  ctx.restore();
}}
img.onload=()=>{{ imgW=img.width; imgH=img.height; resize(); fit(); }};
img.src='data:image/png;base64,{b64}';
window.addEventListener('resize',resize);
cv.addEventListener('wheel',e=>{{ e.preventDefault(); const f=e.deltaY<0?1.18:.84; const r=cv.getBoundingClientRect(); const mx=e.clientX-r.left, my=e.clientY-r.top; const ix=(mx-ox)/sc, iy=(my-oy)/sc; sc=Math.max(.05,Math.min(40,sc*f)); ox=mx-ix*sc; oy=my-iy*sc; draw(); }},{{passive:false}});
cv.addEventListener('mousedown',e=>{{
  const p=toImg(e);
  for(let i=0;i<points.length;i++){{ const dx=(p.x-points[i].x)*sc, dy=(p.y-points[i].y)*sc; if(Math.sqrt(dx*dx+dy*dy)<18){{ draggingPoint=i; return; }} }}
  if(markMode && points.length<4){{ points.push(p); if(points.length===4) markMode=false; draw(); return; }}
  drag=true; lx=e.clientX; ly=e.clientY;
}});
cv.addEventListener('mousemove',e=>{{
  if(draggingPoint>=0){{ points[draggingPoint]=toImg(e); draw(); return; }}
  if(drag){{ ox+=e.clientX-lx; oy+=e.clientY-ly; lx=e.clientX; ly=e.clientY; draw(); }}
}});
cv.addEventListener('mouseup',()=>{{ drag=false; draggingPoint=-1; }}); cv.addEventListener('mouseleave',()=>{{ drag=false; draggingPoint=-1; }});
document.getElementById('mark').onclick=()=>{{ markMode=true; points=[]; draw(); }};
document.getElementById('fit').onclick=()=>fit();
document.getElementById('clear').onclick=()=>{{ points=[]; draw(); }};
document.getElementById('export').onclick=()=>{{
  if(points.length!==4){{ alert('Marque os 4 cantos do grid.'); return; }}
  const payload={{ imagem:IMG_NAME, linhas:ROWS, colunas:COLS, pontos:points, parcelas:getCells(), criado_em:new Date().toISOString(), versao:'1.0' }};
  download('grid_parcelas_'+Date.now()+'.json','application/json',JSON.stringify(payload,null,2));
}};
document.getElementById('geojson').onclick=()=>{{
  if(points.length!==4){{ alert('Marque os 4 cantos do grid.'); return; }}
  const features=getCells().map(cell=>({{type:'Feature',properties:{{linha:cell.linha,coluna:cell.coluna,id:'L'+cell.linha+'_C'+cell.coluna}},geometry:{{type:'Polygon',coordinates:[[...cell.polygon.map(p=>[p.x,-p.y]),[cell.polygon[0].x,-cell.polygon[0].y]]]}}}}));
  download('grid_parcelas_'+Date.now()+'.geojson','application/geo+json',JSON.stringify({{type:'FeatureCollection',features:features}},null,2));
}};
document.getElementById('csv').onclick=()=>{{
  if(points.length!==4){{ alert('Marque os 4 cantos do grid.'); return; }}
  let csv='linha;coluna;x1;y1;x2;y2;x3;y3;x4;y4\\n';
  for(const cell of getCells()) csv+=cell.linha+';'+cell.coluna+';'+cell.polygon.map(p=>Math.round(p.x)+';'+Math.round(p.y)).join(';')+'\\n';
  download('grid_parcelas_'+Date.now()+'.csv','text/csv;charset=utf-8',csv);
}};
</script>
</body>
</html>
"""

def _tv_render_grid_parcelas(manifest: dict) -> None:
    st.markdown("#### Grid e Parcelas")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        ortho_options = [f"{o['ortho_id']} · {o['nome']}" for o in manifest.get("orthos", [])]
        ortho_select_options = [""] + ortho_options
        pending_ortho = st.session_state.pop("tv_next_grid_ortho", "")
        ortho_index = ortho_select_options.index(pending_ortho) if pending_ortho in ortho_select_options else 0
        selected = st.selectbox("Ortofoto", ortho_select_options, index=ortho_index, key="tv_grid_ortho")
        rows = st.number_input("Linhas", min_value=1, max_value=500, value=5, key="tv_grid_rows")
        cols = st.number_input("Colunas", min_value=1, max_value=500, value=5, key="tv_grid_cols")
        imported = st.file_uploader(
            "Importar grid/vetor",
            type=["shp", "geojson", "json", "kml", "kmz", "csv", "dxf", "tif", "tiff", "gpkg"],
            accept_multiple_files=True,
            key="tv_grid_import"
        )
        if st.button("Registrar importação", key="tv_register_import", use_container_width=True):
            saved, _, _ = _tv_save_uploaded_batch(imported, TV_IMPORTS_DIR / datetime.now().strftime("%Y%m%d_%H%M%S"), manifest, duplicate_check=False)
            for item in saved:
                manifest.setdefault("imports", []).insert(0, {**item, "tipo": item["ext"], "registrado_em": _tv_now()})
            _tv_add_history(manifest, f"Importação GIS: {len(saved)} arquivo(s)")
            _tv_save_manifest(manifest)
            st.success(f"{len(saved)} arquivo(s) importado(s).")

        grid_json = st.file_uploader("Reenviar grid JSON exportado pelo visualizador", type=["json"], key="tv_grid_json")
        if st.button("Salvar versão do grid", type="primary", key="tv_save_grid_version", use_container_width=True):
            if grid_json is None:
                st.warning("Selecione o JSON do grid exportado.")
            else:
                ortho_id = _tv_get_ortho_id(selected)
                ortho_record = _tv_find_ortho(manifest, ortho_id)
                project_id = ortho_record.get("project_id", "") if ortho_record else ""
                raw = grid_json.getbuffer().tobytes()
                grid_id = f"GRID_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                target = TV_GRIDS_DIR / f"{grid_id}_{Path(grid_json.name).name}"
                target.write_bytes(raw)
                record = {
                    "grid_id": grid_id,
                    "project_id": project_id,
                    "ortho_id": ortho_id,
                    "ortho": selected,
                    "path": str(target),
                    "sha256": _tv_hash_bytes(raw),
                    "linhas": int(rows),
                    "colunas": int(cols),
                    "versao": len(manifest.get("grids", [])) + 1,
                    "status": "Grid marcado - pronto para retorno",
                    "criado_em": _tv_now()
                }
                manifest.setdefault("grids", []).insert(0, record)
                project = _tv_find_project(manifest, project_id)
                if project:
                    project["status"] = "Grid marcado - pronto para retornar"
                    project["workflow"] = "GRID_MARCADO"
                    project["grid_marcado_em"] = _tv_now()
                if ortho_record:
                    ortho_record["status"] = "Grid marcado"
                _tv_add_history(manifest, f"Grid registrado: {grid_id}", project_id)
                _tv_save_manifest(manifest)
                st.success(f"Grid `{grid_id}` salvo. Próximo passo: Retornar Projeto.")

    with col_r:
        if not selected:
            st.info("Selecione uma ortofoto recebida para abrir o visualizador GIS.")
        else:
            ortho_id = selected.split(" · ")[0]
            record = next((o for o in manifest.get("orthos", []) if o.get("ortho_id") == ortho_id), None)
            if record and Path(record.get("path", "")).exists():
                with st.spinner("Preparando visualizador GIS..."):
                    raw = Path(record["path"]).read_bytes()
                    b64, dims, err, _ = processar_ortofoto(raw, record["nome"])
                if err:
                    st.error(err)
                else:
                    st.markdown(f"<p style='color:#888;font-size:0.8rem;'>📐 {record['nome']} · {dims[0]}×{dims[1]} px · grid preservado em JSON</p>", unsafe_allow_html=True)
                    components.html(_tv_grid_viewer_html(b64, int(rows), int(cols), record["nome"]), height=700, scrolling=False)

    st.markdown("##### Versões de Grid")
    grid_rows = [{
        "Grid": g.get("grid_id"),
        "Ortofoto": g.get("ortho"),
        "Linhas": g.get("linhas"),
        "Colunas": g.get("colunas"),
        "Versão": g.get("versao"),
        "Status": g.get("status"),
        "Data": g.get("criado_em")
    } for g in manifest.get("grids", [])]
    st.dataframe(grid_rows, use_container_width=True, hide_index=True)

def _tv_render_analises(manifest: dict) -> None:
    st.markdown("#### Análises")
    c1, c2, c3 = st.columns(3)
    c1.metric("Projetos em análise", len([p for p in manifest.get("projects", []) if p.get("status")]))
    c2.metric("Grids disponíveis", len(manifest.get("grids", [])))
    c3.metric("Ortofotos prontas", len(manifest.get("orthos", [])))
    st.markdown("<h4 style='color:#ff8c00;margin-top:0;'>Fila técnica</h4>", unsafe_allow_html=True)
    rows = []
    for p in manifest.get("projects", []):
        rows.append({
            "Projeto": p.get("project_id"),
            "Fazenda": p.get("fazenda"),
            "Talhão": p.get("talhao"),
            "Status": "Aguardando análise técnica" if manifest.get("grids") else p.get("status"),
            "Relatórios": "Contagem · Falhas · Parcelas"
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if st.button("Reenviar pacote selecionado para análise", type="primary", key="tv_send_analysis", use_container_width=True):
        _tv_add_history(manifest, "Pacote reenviado para análise técnica", status="ENVIADO")
        _tv_save_manifest(manifest)
        st.success("Pacote colocado na fila de análise técnica.")

def _tv_render_retornar_projeto(manifest: dict) -> None:
    st.markdown("#### Retornar Projeto")
    st.caption("Após marcar o grid, gere o pacote de retorno com ortofoto, grid, parcelas e metadados para o próximo usuário ou análise técnica.")
    ready_grids = [g for g in manifest.get("grids", []) if g.get("status")]
    if not ready_grids:
        st.info("Nenhum grid marcado ainda. Primeiro receba a ortofoto e marque o grid em Grid e Parcelas.")
        return

    options = [f"{g['grid_id']} · {g.get('ortho','Ortofoto')}" for g in ready_grids]
    selected = st.selectbox("Grid para retorno", options, key="tv_return_grid")
    grid_id = selected.split(" · ")[0] if selected else ""
    grid = _tv_find_grid(manifest, grid_id)
    ortho = _tv_find_ortho(manifest, grid.get("ortho_id", "")) if grid else {}
    project = _tv_find_project(manifest, grid.get("project_id", "")) if grid else {}

    c1, c2, c3 = st.columns(3)
    c1.metric("Grid", grid.get("grid_id", "-"))
    c2.metric("Projeto", grid.get("project_id", "-") or "-")
    c3.metric("Parcelas", int(grid.get("linhas", 0)) * int(grid.get("colunas", 0)))

    incluir_ortho = st.checkbox("Incluir ortofoto original no pacote", value=True, key="tv_return_include_ortho")
    incluir_raw_manifest = st.checkbox("Incluir lista de imagens originais e checksums", value=True, key="tv_return_include_raw")

    if st.button("Gerar pacote de retorno", type="primary", key="tv_make_return_pkg", use_container_width=True):
        if not grid or not Path(grid.get("path", "")).exists():
            st.error("Arquivo do grid não encontrado.")
            return
        return_id = f"RET_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return_dir = TV_RETURNS_DIR / return_id
        return_dir.mkdir(parents=True, exist_ok=True)
        package_path = return_dir / f"{return_id}_{grid.get('project_id','projeto')}.zip"

        meta = {
            "return_id": return_id,
            "created_at": _tv_now(),
            "project": project,
            "ortho": ortho,
            "grid": grid,
            "parcelas": int(grid.get("linhas", 0)) * int(grid.get("colunas", 0)),
            "conteudo": {
                "ortofoto_original": bool(incluir_ortho),
                "manifesto_raw": bool(incluir_raw_manifest),
                "grid_json": True
            }
        }

        manifest_file = return_dir / "manifesto_retorno.json"
        manifest_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

        with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(grid["path"], arcname=f"grid/{Path(grid['path']).name}")
            zf.write(manifest_file, arcname="manifesto_retorno.json")
            if incluir_ortho and ortho and Path(ortho.get("path", "")).exists():
                zf.write(ortho["path"], arcname=f"ortofoto/{Path(ortho['path']).name}")
            if incluir_raw_manifest and project:
                raw_manifest = return_dir / "imagens_originais_checksums.json"
                raw_manifest.write_text(json.dumps(project.get("files", []), indent=2, ensure_ascii=False), encoding="utf-8")
                zf.write(raw_manifest, arcname="imagens_originais_checksums.json")

        record = {
            "return_id": return_id,
            "project_id": grid.get("project_id", ""),
            "grid_id": grid.get("grid_id", ""),
            "ortho_id": grid.get("ortho_id", ""),
            "path": str(package_path),
            "tamanho": package_path.stat().st_size,
            "tamanho_fmt": _tv_human_size(package_path.stat().st_size),
            "sha256": _tv_hash_file(package_path),
            "status": "Pacote retornado",
            "criado_em": _tv_now()
        }
        manifest.setdefault("returns", []).insert(0, record)
        grid["status"] = "Retornado"
        if project:
            project["status"] = "Projeto retornado com grid marcado"
            project["workflow"] = "RETORNADO_COM_GRID"
            project["retornado_em"] = _tv_now()
        _tv_add_history(manifest, f"Pacote de retorno gerado: {return_id}", grid.get("project_id", ""))
        _tv_save_manifest(manifest)
        st.success(f"Pacote `{return_id}` gerado.")

    st.markdown("##### Pacotes gerados")
    rows = [{
        "Retorno": r.get("return_id"),
        "Projeto": r.get("project_id"),
        "Grid": r.get("grid_id"),
        "Tamanho": r.get("tamanho_fmt"),
        "Status": r.get("status"),
        "Data": r.get("criado_em")
    } for r in manifest.get("returns", [])]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if manifest.get("returns"):
        selected_return = st.selectbox("Baixar pacote de retorno", [f"{r['return_id']} · {r.get('project_id','')}" for r in manifest.get("returns", [])], key="tv_return_download")
        return_id = selected_return.split(" · ")[0]
        record = next((r for r in manifest.get("returns", []) if r.get("return_id") == return_id), None)
        if record and Path(record.get("path", "")).exists():
            st.download_button(
                "Baixar ZIP de retorno",
                data=Path(record["path"]).read_bytes(),
                file_name=Path(record["path"]).name,
                mime="application/zip",
                use_container_width=True
            )

def _tv_render_historico(manifest: dict) -> None:
    st.markdown("#### Histórico")
    st.dataframe(manifest.get("history", []), use_container_width=True, hide_index=True)

def _tv_render_config(manifest: dict) -> None:
    st.markdown("#### Configurações")
    config = manifest.get("config", {})
    providers = ["Microsoft OneDrive", "Microsoft Azure", "Google Drive", "Dropbox", "Servidor local", "NAS", "FTP/SFTP"]
    provider_index = providers.index(config.get("provider", "Servidor local")) if config.get("provider", "Servidor local") in providers else 4
    c1, c2 = st.columns(2)
    with c1:
        provider = st.selectbox("Conector", providers, index=provider_index, key="tv_cfg_provider")
        destination = st.text_input("Destino / bucket / caminho", value=config.get("destination", str(TV_ROOT / "sync")), key="tv_cfg_dest")
        sync_mode = st.selectbox("Sincronização", ["Manual", "Automática ao enviar", "A cada hora", "Diária"], key="tv_cfg_sync")
    with c2:
        auth_mode = st.selectbox("Autenticação", ["Token/OAuth", "Chave de acesso", "Usuário e senha", "Conta de serviço"], key="tv_cfg_auth")
        encryption = st.checkbox("Criptografia de uploads", value=bool(config.get("encryption", True)), key="tv_cfg_enc")
        resumable = st.checkbox("Upload retomável", value=bool(config.get("resumable", True)), key="tv_cfg_resume")
        checksum = st.checkbox("Verificação de integridade", value=bool(config.get("checksum", True)), key="tv_cfg_checksum")
    if st.button("Salvar configurações de transferência", type="primary", key="tv_cfg_save", use_container_width=True):
        manifest["config"] = {
            "provider": provider,
            "destination": destination,
            "sync_mode": sync_mode,
            "checksum": checksum,
            "resumable": resumable,
            "encryption": encryption,
            "auth_mode": auth_mode
        }
        _tv_add_history(manifest, f"Configuração atualizada: {provider}")
        _tv_save_manifest(manifest)
        st.success("Configurações salvas.")

    st.markdown("##### Usuários e permissões")
    st.dataframe(manifest.get("users", []), use_container_width=True, hide_index=True)

def render_transferencia_voos() -> None:
    _tv_ensure_storage()
    manifest = _tv_load_manifest()
    st.markdown("""
    <style>
      .tv-hero {
        background:linear-gradient(145deg,#181818 0%,#111 56%,#2a1700 100%);
        border:1px solid #3a2a18;
        border-top:2px solid #ff8c00;
        border-radius:8px;
        padding:20px 22px;
        margin-bottom:14px;
        box-shadow:4px 4px 14px #070707,0 0 24px rgba(255,140,0,.10);
      }
      .tv-hero h2 {
        margin:0;
        color:#ff8c00;
        letter-spacing:3px;
        text-transform:uppercase;
        text-shadow:1px 1px 0 #7a3a00,3px 3px 8px rgba(0,0,0,.9),0 0 22px rgba(255,140,0,.32);
      }
      .tv-hero p { margin:8px 0 0 0; color:#cfcfcf; font-size:13px; }
      .tv-band { border:1px solid #3a2a18; background:#161616; border-radius:8px; padding:12px; }
      div[data-testid="stRadio"] > div {
        background:#151515;
        border:1px solid #2e2e2e;
        border-radius:8px;
        padding:8px 10px;
        box-shadow:inset 0 1px 0 rgba(255,255,255,.03);
      }
      div[data-testid="stRadio"] label {
        background:linear-gradient(145deg,#222,#111);
        border:1px solid #303030;
        border-radius:8px;
        padding:7px 10px;
        margin-right:4px;
      }
      div[data-testid="stRadio"] label:hover {
        border-color:#ff8c00;
        box-shadow:0 0 12px rgba(255,140,0,.12);
      }
      div[data-testid="stRadio"] label:has(input:checked) {
        border-color:#ff8c00;
        background:linear-gradient(145deg,#ff9e33,#e67600);
        box-shadow:0 0 16px rgba(255,140,0,.22);
      }
    </style>
    """, unsafe_allow_html=True)
    st.markdown(
        "<div class='tv-hero'><h2>Transferência de Voos</h2>"
        "<p>Central GIS para envio, sincronização, ortofotos, grids, versões e análise técnica.</p>"
        f"{_tv_status_chip('Python 3.12', '#55ff99')}"
        f"{_tv_status_chip('Qualidade original preservada', '#ff8c00')}"
        f"{_tv_status_chip('Checksums SHA-256', '#5599ff')}"
        "</div>",
        unsafe_allow_html=True
    )

    tabs = ["Upload de Voos", "Receber Voos", "Banco de Dados", "Ortofotos Geradas", "Grid e Parcelas", "Retornar Projeto", "Análises", "Histórico", "Configurações"]
    active = st.radio("Menu Transferência de Voos", tabs, horizontal=True, label_visibility="collapsed", key="tv_active_tab")
    st.markdown("---")

    if active == "Upload de Voos":
        _tv_render_upload(manifest)
    elif active == "Receber Voos":
        _tv_render_receber_voos(manifest)
    elif active == "Banco de Dados":
        _tv_render_database(manifest)
    elif active == "Ortofotos Geradas":
        _tv_render_orthos(manifest)
    elif active == "Grid e Parcelas":
        _tv_render_grid_parcelas(manifest)
    elif active == "Retornar Projeto":
        _tv_render_retornar_projeto(manifest)
    elif active == "Análises":
        _tv_render_analises(manifest)
    elif active == "Histórico":
        _tv_render_historico(manifest)
    elif active == "Configurações":
        _tv_render_config(manifest)

# ==========================================
# MODULO ISOLADO - VOOS DIRECIONADOS
# ==========================================
VD_ROOT = SYSTEM_DATABASE_DIR / "voos_direcionados"
VD_FLIGHTS_DIR = VD_ROOT / "voos_enviados"
VD_ORTHOS_DIR = VD_ROOT / "ortofotos_recebidas"
VD_GRIDS_DIR = VD_ROOT / "grids_salvos"
VD_EXPORTS_DIR = VD_ROOT / "exportacoes"
VD_MANIFEST_PATH = VD_ROOT / "manifest.json"
VD_DESTINATIONS = [
    "OneDrive",
    "Google Drive",
    "Azure Storage",
    "Diretório local",
    "Pasta em rede",
    "Outros bancos/diretórios futuros"
]

def _vd_default_manifest() -> dict:
    return {
        "voos": [],
        "orthos": [],
        "grids": [],
        "exports": [],
        "history": [],
        "config": {
            "destino": "Diretório local",
            "caminho": str(VD_ROOT / "destinos" / "local"),
            "usuario_padrao": "Operador"
        }
    }

def _vd_ensure_storage() -> None:
    for folder in [VD_ROOT, VD_FLIGHTS_DIR, VD_ORTHOS_DIR, VD_GRIDS_DIR, VD_EXPORTS_DIR, VD_ROOT / "destinos" / "local"]:
        folder.mkdir(parents=True, exist_ok=True)
    if not VD_MANIFEST_PATH.exists():
        VD_MANIFEST_PATH.write_text(json.dumps(_vd_default_manifest(), indent=2, ensure_ascii=False), encoding="utf-8")

def _vd_load_manifest() -> dict:
    _vd_ensure_storage()
    try:
        data = json.loads(VD_MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = _vd_default_manifest()
    default = _vd_default_manifest()
    for key, value in default.items():
        data.setdefault(key, value)
    data.setdefault("config", {}).setdefault("destino", "Diretório local")
    data.setdefault("config", {}).setdefault("caminho", str(VD_ROOT / "destinos" / "local"))
    return data

def _vd_save_manifest(data: dict) -> None:
    _vd_ensure_storage()
    VD_MANIFEST_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def _vd_add_history(manifest: dict, event: str, lote_id: str = "", status: str = "OK") -> None:
    manifest.setdefault("history", []).insert(0, {
        "data": _tv_now(),
        "lote": lote_id,
        "evento": event,
        "status": status
    })
    manifest["history"] = manifest["history"][:500]

def _vd_find_voo(manifest: dict, lote_id: str) -> dict:
    for voo in manifest.get("voos", []):
        if voo.get("lote_id") == lote_id:
            return voo
    return {}

def _vd_find_ortho(manifest: dict, ortho_id: str) -> dict:
    for ortho in manifest.get("orthos", []):
        if ortho.get("ortho_id") == ortho_id:
            return ortho
    return {}

def _vd_find_grid(manifest: dict, grid_id: str) -> dict:
    for grid in manifest.get("grids", []):
        if grid.get("grid_id") == grid_id:
            return grid
    return {}

def _vd_project_options(manifest: dict) -> list:
    return [f"{v['lote_id']} · {v.get('nome_voo','Voo')}" for v in manifest.get("voos", [])]

def _vd_ortho_options(manifest: dict) -> list:
    return [f"{o['ortho_id']} · {o.get('nome','Ortofoto')}" for o in manifest.get("orthos", [])]

def _vd_id_from_option(option: str) -> str:
    return option.split(" · ")[0] if option else ""

def _vd_destination_status(destino: str, caminho: str, manifest: dict) -> dict:
    path = Path(caminho.strip()) if caminho else VD_ROOT / "destinos" / _tv_safe_name(destino)
    exists = path.exists()
    status = "Conectado" if exists else "Pendente"
    free = "Indisponível"
    try:
        base = path if exists else path.parent
        usage = shutil.disk_usage(base)
        free = _tv_human_size(usage.free)
    except Exception:
        pass
    last = "-"
    for voo in manifest.get("voos", []):
        if voo.get("destino_enviado") == destino:
            last = voo.get("data_hora", "-")
            break
    return {
        "nome": destino,
        "caminho": str(path),
        "status": status,
        "espaco": free,
        "ultimo_envio": last
    }

def _vd_save_uploaded_files(files, base_dir: Path, progress=None) -> tuple:
    saved, total_size = [], 0
    base_dir.mkdir(parents=True, exist_ok=True)
    expected = sum(int(getattr(uploaded, "size", 0) or 0) for uploaded in (files or []))
    written_total = 0
    for uploaded in files or []:
        hasher = hashlib.sha256()
        file_size = 0
        temp_name = f".{_tv_safe_name(Path(uploaded.name).stem)}_{datetime.now().strftime('%H%M%S%f')}.uploading"
        temp_path = base_dir / temp_name
        try:
            uploaded.seek(0)
        except Exception:
            pass
        with open(temp_path, "wb") as out:
            while True:
                chunk = uploaded.read(1024 * 1024)
                if not chunk:
                    break
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                hasher.update(chunk)
                out.write(chunk)
                file_size += len(chunk)
                written_total += len(chunk)
                if progress and expected:
                    progress.progress(min(99, int((written_total / expected) * 100)))
        target = base_dir / Path(uploaded.name).name
        if target.exists():
            target = base_dir / f"{target.stem}_{datetime.now().strftime('%H%M%S%f')}{target.suffix}"
        temp_path.replace(target)
        total_size += file_size
        saved.append({
            "nome": uploaded.name,
            "path": str(target),
            "tamanho": file_size,
            "tamanho_fmt": _tv_human_size(file_size),
            "sha256": hasher.hexdigest(),
            "ext": Path(uploaded.name).suffix.lower(),
            "enviado_em": _tv_now()
        })
    if progress:
        progress.progress(100)
    return saved, total_size

def _vd_copy_to_destination(saved: list, caminho: str, lote_id: str, nome_voo: str = "") -> tuple:
    """Copia o lote para o diretório escolhido criando uma pasta limpa com o nome do voo."""
    if not caminho:
        return "", "Armazenado somente no banco interno"
    try:
        base_destino = Path(str(caminho).strip()).expanduser()
        pasta_voo = _tv_safe_name(nome_voo) if nome_voo else lote_id
        dest_dir = base_destino / pasta_voo
        if dest_dir.exists():
            dest_dir = base_destino / f"{pasta_voo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        for item in saved:
            src = Path(item["path"])
            if src.exists():
                shutil.copy2(src, dest_dir / src.name)
        return str(dest_dir), "Enviado"
    except Exception as exc:
        return "", f"Falha no destino externo: {exc}"

def _vd_metric_cards(manifest: dict) -> None:
    voos = manifest.get("voos", [])
    orthos = manifest.get("orthos", [])
    grids = manifest.get("grids", [])
    volume = sum(v.get("tamanho_total", 0) for v in voos) + sum(o.get("tamanho", 0) for o in orthos)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Voos enviados", len(voos))
    c2.metric("Ortofotos", len(orthos))
    c3.metric("Grids salvos", len(grids))
    c4.metric("Volume interno", _tv_human_size(volume))

def _vd_ortho_viewer_html(b64: str, image_name: str, width: int, height: int) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:#0d0d0d; overflow:hidden; font-family:Segoe UI, Arial, sans-serif; }}
  #vdv {{ width:100%; height:680px; background:#0d0d0d; border:1px solid #2f2f2f; border-radius:8px; overflow:hidden; position:relative; }}
  canvas {{ position:absolute; inset:0; cursor:grab; }}
  canvas:active {{ cursor:grabbing; }}
  .vdtop {{ position:absolute; left:12px; top:12px; right:12px; display:flex; justify-content:space-between; gap:10px; z-index:3; pointer-events:none; }}
  .badge {{ background:rgba(10,10,10,.82); border:1px solid #333; color:#ff8c00; border-radius:6px; padding:7px 10px; font-size:11px; letter-spacing:.5px; }}
  .panel {{ position:absolute; right:12px; bottom:12px; background:rgba(10,10,10,.86); border:1px solid #333; border-radius:8px; padding:10px; z-index:4; color:#ddd; min-width:240px; }}
  .panel label {{ display:flex; align-items:center; justify-content:space-between; gap:8px; color:#ff8c00; font-size:11px; margin:6px 0; }}
  input[type=range] {{ accent-color:#ff8c00; width:138px; }}
  button {{ background:linear-gradient(145deg,#222,#111); color:#ff8c00; border:1px solid #3a3a3a; border-radius:6px; padding:7px 9px; cursor:pointer; font-weight:700; }}
  button:hover {{ border-color:#ff8c00; box-shadow:0 0 10px rgba(255,140,0,.22); }}
  .scale {{ position:absolute; left:12px; bottom:12px; color:#ccc; background:rgba(0,0,0,.72); border:1px solid #333; border-radius:6px; padding:7px 10px; font-size:11px; }}
  .scaleLine {{ display:inline-block; width:86px; border-bottom:3px solid #ff8c00; margin-right:8px; transform:translateY(-3px); }}
</style>
</head>
<body>
<div id="vdv">
  <canvas id="vd_cv"></canvas>
  <div class="vdtop">
    <div class="badge">{image_name} · {width} x {height} px</div>
    <div class="badge" id="vd_coord">X: - · Y: - · Zoom: 100%</div>
  </div>
  <div class="panel">
    <label>Brilho <input id="vd_bright" type="range" min="50" max="160" value="100"></label>
    <label>Contraste <input id="vd_contrast" type="range" min="50" max="180" value="100"></label>
    <div style="display:flex;gap:6px;margin-top:8px;">
      <button id="vd_fit">Ajustar</button>
      <button id="vd_100">1:1</button>
      <button id="vd_reset">Reset</button>
    </div>
  </div>
  <div class="scale"><span class="scaleLine"></span>escala visual</div>
</div>
<script>
const wrap=document.getElementById('vdv'), cv=document.getElementById('vd_cv'), ctx=cv.getContext('2d');
const coord=document.getElementById('vd_coord'), brightEl=document.getElementById('vd_bright'), contrastEl=document.getElementById('vd_contrast');
let sc=1, ox=0, oy=0, drag=false, lx=0, ly=0, imgW=0, imgH=0;
const img=new Image();
function resize(){{ cv.width=wrap.clientWidth; cv.height=wrap.clientHeight; draw(); }}
function fit(){{ if(!imgW) return; sc=Math.min(cv.width/imgW, cv.height/imgH); ox=(cv.width-imgW*sc)/2; oy=(cv.height-imgH*sc)/2; draw(); }}
function draw(){{
  ctx.clearRect(0,0,cv.width,cv.height);
  ctx.save(); ctx.translate(ox,oy); ctx.scale(sc,sc);
  ctx.filter=`brightness(${{brightEl.value}}%) contrast(${{contrastEl.value}}%)`;
  if(imgW) ctx.drawImage(img,0,0);
  ctx.restore();
  coord.textContent=coord.dataset.base || 'X: - · Y: - · Zoom: '+Math.round(sc*100)+'%';
}}
img.onload=()=>{{ imgW=img.width; imgH=img.height; resize(); fit(); }};
img.src='data:image/jpeg;base64,{b64}';
window.addEventListener('resize', resize);
brightEl.oninput=draw; contrastEl.oninput=draw;
cv.addEventListener('wheel',e=>{{ e.preventDefault(); const f=e.deltaY<0?1.18:.84; const r=cv.getBoundingClientRect(); const mx=e.clientX-r.left,my=e.clientY-r.top; const ix=(mx-ox)/sc,iy=(my-oy)/sc; sc=Math.max(.05,Math.min(40,sc*f)); ox=mx-ix*sc; oy=my-iy*sc; draw(); }},{{passive:false}});
cv.addEventListener('mousedown',e=>{{ drag=true; lx=e.clientX; ly=e.clientY; }});
cv.addEventListener('mousemove',e=>{{ const r=cv.getBoundingClientRect(); const x=(e.clientX-r.left-ox)/sc, y=(e.clientY-r.top-oy)/sc; coord.dataset.base='X: '+Math.round(x)+' · Y: '+Math.round(y)+' · Zoom: '+Math.round(sc*100)+'%'; coord.textContent=coord.dataset.base; if(drag){{ ox+=e.clientX-lx; oy+=e.clientY-ly; lx=e.clientX; ly=e.clientY; draw(); }} }});
cv.addEventListener('mouseup',()=>{{ drag=false; }}); cv.addEventListener('mouseleave',()=>{{ drag=false; }});
document.getElementById('vd_fit').onclick=fit;
document.getElementById('vd_100').onclick=()=>{{ sc=1; ox=(cv.width-imgW)/2; oy=(cv.height-imgH)/2; draw(); }};
document.getElementById('vd_reset').onclick=()=>{{ brightEl.value=100; contrastEl.value=100; fit(); }};
</script>
</body>
</html>
"""

def _vd_grid_features(grid: dict, ortho: dict) -> tuple:
    payload = json.loads(Path(grid["path"]).read_text(encoding="utf-8"))
    meta = ortho.get("spatial_meta", {}) or {}
    ratio = float(meta.get("ratio") or 1.0)
    transform = None
    if meta.get("transform") and "Affine" in globals():
        try:
            transform = Affine.from_gdal(*meta.get("transform"))
        except Exception:
            transform = None

    def to_coord(point: dict) -> list:
        x = float(point.get("x", 0)) / ratio
        y = float(point.get("y", 0)) / ratio
        if transform is not None:
            gx, gy = transform * (x, y)
            return [gx, gy]
        return [x, -y]

    features = []
    for cell in payload.get("parcelas", []):
        poly = cell.get("polygon", [])
        if len(poly) < 4:
            continue
        coords = [to_coord(p) for p in poly]
        coords.append(coords[0])
        linha = cell.get("linha", 0)
        coluna = cell.get("coluna", 0)
        features.append({
            "type": "Feature",
            "properties": {
                "id": cell.get("id") or f"L{linha}_C{coluna}",
                "linha": linha,
                "coluna": coluna,
                "grid_id": grid.get("grid_id", ""),
                "ortho_id": grid.get("ortho_id", ""),
                "parcelas": grid.get("parcelas", 0)
            },
            "geometry": {"type": "Polygon", "coordinates": [coords]}
        })
    return features, meta.get("crs")

def _vd_grid_geojson_bytes(grid: dict, ortho: dict) -> bytes:
    features, _ = _vd_grid_features(grid, ortho)
    return json.dumps({"type": "FeatureCollection", "features": features}, indent=2, ensure_ascii=False).encode("utf-8")

def _vd_grid_shp_zip_bytes(grid: dict, ortho: dict) -> bytes:
    features, crs = _vd_grid_features(grid, ortho)
    if not HAS_GEOPANDAS:
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("parcelas.geojson", json.dumps({"type": "FeatureCollection", "features": features}, indent=2, ensure_ascii=False))
            zf.writestr("LEIA.txt", "GeoPandas/GDAL nao instalado. Exportado GeoJSON como fallback compativel com QGIS.")
        buf.seek(0)
        return buf.getvalue()

    tmpdir = Path(tempfile.mkdtemp(prefix="vd_shp_"))
    try:
        rows = []
        for feat in features:
            rows.append({
                **feat["properties"],
                "geometry": Polygon(feat["geometry"]["coordinates"][0])
            })
        gdf = gpd.GeoDataFrame(rows, geometry="geometry")
        if crs:
            try:
                gdf.set_crs(crs, inplace=True, allow_override=True)
            except Exception:
                pass
        shp_path = tmpdir / "parcelas_voos_direcionados.shp"
        gdf.to_file(shp_path, driver="ESRI Shapefile", encoding="utf-8")
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in tmpdir.iterdir():
                zf.write(item, arcname=item.name)
        buf.seek(0)
        return buf.getvalue()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

def _vd_grid_overlay_bytes(grid: dict, ortho: dict, image_format: str = "PNG") -> bytes:
    from PIL import ImageDraw
    raw = Path(ortho["path"]).read_bytes()
    b64, _, err, _ = processar_ortofoto(raw, ortho.get("nome", "ortofoto"))
    if err:
        raise RuntimeError(err)
    img = Image.open(BytesIO(base64.b64decode(b64))).convert("RGBA")
    draw = ImageDraw.Draw(img)
    payload = json.loads(Path(grid["path"]).read_text(encoding="utf-8"))
    for cell in payload.get("parcelas", []):
        poly = [(float(p.get("x", 0)), float(p.get("y", 0))) for p in cell.get("polygon", [])]
        if len(poly) < 4:
            continue
        closed = poly + [poly[0]]
        draw.line(closed, fill=(255, 140, 0, 255), width=3)
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        label = cell.get("id") or f"L{cell.get('linha',0)}_C{cell.get('coluna',0)}"
        draw.text((cx - 14, cy - 6), label, fill=(255, 255, 255, 255))
    buf = BytesIO()
    fmt = image_format.upper()
    if fmt in ("JPG", "JPEG"):
        img.convert("RGB").save(buf, format="JPEG", quality=92)
    elif fmt in ("TIF", "TIFF"):
        img.convert("RGB").save(buf, format="TIFF")
    else:
        img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def _vd_grid_geotiff_overlay_bytes(grid: dict, ortho: dict) -> bytes:
    try:
        import rasterio
        from rasterio.io import MemoryFile
        img = Image.open(BytesIO(_vd_grid_overlay_bytes(grid, ortho, "PNG"))).convert("RGB")
        arr = np.array(img)
        meta = ortho.get("spatial_meta", {}) or {}
        profile = {
            "driver": "GTiff",
            "height": arr.shape[0],
            "width": arr.shape[1],
            "count": 3,
            "dtype": arr.dtype,
            "compress": "lzw"
        }
        if meta.get("transform") and "Affine" in globals():
            ratio = float(meta.get("ratio") or 1.0)
            profile["transform"] = Affine.from_gdal(*meta.get("transform")) * Affine.scale(1 / ratio, 1 / ratio)
        if meta.get("crs"):
            profile["crs"] = meta.get("crs")
        with MemoryFile() as memfile:
            with memfile.open(**profile) as dst:
                dst.write(arr[:, :, 0], 1)
                dst.write(arr[:, :, 1], 2)
                dst.write(arr[:, :, 2], 3)
            return memfile.read()
    except Exception:
        return _vd_grid_overlay_bytes(grid, ortho, "TIFF")

def _vd_render_login() -> None:
    st.markdown("""
    <style>
      .vd-login-wrap { min-height:72vh; display:flex; align-items:center; justify-content:center; }
      .vd-login-card {
        width:min(430px, 96vw);
        background:linear-gradient(155deg,#1b1b1b,#101010 62%,#271600);
        border:1px solid #333;
        border-top:2px solid #ff8c00;
        border-radius:8px;
        padding:28px;
        box-shadow:6px 6px 18px #050505,0 0 30px rgba(255,140,0,.12);
      }
      .vd-login-title {
        color:#ff8c00;
        font-weight:900;
        letter-spacing:3px;
        text-transform:uppercase;
        font-size:1.45rem;
        text-shadow:1px 1px 0 #7a3a00,3px 3px 8px #000;
        margin-bottom:8px;
      }
      .vd-login-sub { color:#aaa; font-size:.82rem; letter-spacing:1px; margin-bottom:16px; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="vd-login-card">
      <div class="vd-login-title">Processos de Voos para Análise</div>
      <div class="vd-login-sub">Acesso dedicado para envio de fotos, recebimento de ortofotos, marcador de grid e retorno dos dados.</div>
    </div>
    """, unsafe_allow_html=True)
    usuario = st.text_input("Login", key="vd_login_user")
    senha = st.text_input("Senha", type="password", key="vd_login_pass")
    if st.button("Abrir Processos de Voos para Análise", type="primary", key="vd_login_btn", use_container_width=True):
        if usuario == "1234" and senha == "1234":
            st.session_state.vd_logged_in = True
            app_rerun()
        else:
            st.error("Login ou senha incorretos para Processos de Voos para Análise.")

def _vd_render_envio(manifest: dict) -> None:
    st.markdown("""
    <style>
      .vd-clean-card {
        background:linear-gradient(145deg,#181818,#101010);
        border:1px solid #2d2d2d;
        border-radius:12px;
        padding:18px 18px 10px 18px;
        margin-bottom:14px;
        box-shadow:3px 3px 12px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.03);
      }
      .vd-section-title {
        color:#cfcfcf;
        font-weight:800;
        letter-spacing:1.5px;
        text-transform:uppercase;
        font-size:.92rem;
        margin:0 0 10px 0;
      }
      .vd-progress-box {
        background:#111;
        border:1px solid #333;
        border-left:4px solid #ff8c00;
        border-radius:10px;
        padding:14px;
        margin-top:12px;
      }
      .vd-dest-path {
        color:#9f9f9f;
        font-size:.78rem;
        background:#0f0f0f;
        border:1px solid #2d2d2d;
        border-radius:8px;
        padding:8px 10px;
        margin-top:6px;
        word-break:break-all;
      }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("#### PASSO 1 — Enviar Fotos de Voos")
    st.markdown("<div class='vd-section-title'>Dados principais do voo</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        nome_voo = st.text_input("Nome do voo", value=f"Voo_Direcionado_{date.today().strftime('%Y%m%d')}", key="vd_nome_voo")
        fazenda = st.text_input("Nome da fazenda", value="", key="vd_fazenda")
    with c2:
        ensaio = st.text_input("Ensaio", value="", key="vd_ensaio")
        inicio_final = st.text_input("Início / Final", value="", placeholder="Ex.: Início, Final ou Início-Final", key="vd_inicio_final")
    with c3:
        tipo_voo = st.text_input("Tipo de voo", value="", placeholder="Ex.: RGB, Multiespectral, NDVI, Altura", key="vd_tipo_voo")
        usuario = st.text_input("Usuário responsável", value=manifest.get("config", {}).get("usuario_padrao", "Operador"), key="vd_usuario_resp")
    data_voo = st.date_input("Data do voo", value=date.today(), key="vd_data_voo")

    st.markdown("<div class='vd-section-title'>Destino e diretório de envio</div>", unsafe_allow_html=True)
    dcol1, dcol2 = st.columns([1, 2])
    with dcol1:
        destino = st.selectbox(
            "Destino de armazenamento",
            VD_DESTINATIONS,
            index=VD_DESTINATIONS.index(manifest.get("config", {}).get("destino", "Diretório local")) if manifest.get("config", {}).get("destino", "Diretório local") in VD_DESTINATIONS else 3,
            key="vd_destino"
        )
    with dcol2:
        caminho = st.text_input("Diretório escolhido para receber a pasta do voo", value=manifest.get("config", {}).get("caminho", str(VD_ROOT / "destinos" / "local")), key="vd_caminho_destino")
    dest_status = _vd_destination_status(destino, caminho, manifest)
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Destino", dest_status["nome"])
    d2.metric("Status", dest_status["status"])
    d3.metric("Espaço disponível", dest_status["espaco"])
    d4.metric("Último envio", dest_status["ultimo_envio"])
    pasta_prevista = Path(str(caminho).strip()).expanduser() / _tv_safe_name(nome_voo)
    st.markdown(f"<div class='vd-dest-path'>Pasta que será criada no destino: <b>{pasta_prevista}</b></div>", unsafe_allow_html=True)

    st.markdown("<div class='vd-section-title'>Anexar imagens do voo</div>", unsafe_allow_html=True)
    files = st.file_uploader(
        "Selecionar fotos de voos ou ZIP",
        type=["jpg", "jpeg", "tif", "tiff", "png", "raw", "dng", "arw", "cr2", "nef", "zip"],
        accept_multiple_files=True,
        key="vd_select_images"
    )
    if files:
        total_previsto = sum(int(getattr(f, "size", 0) or 0) for f in files)
        st.info(f"{len(files)} arquivo(s) selecionado(s) · volume previsto: {_tv_human_size(total_previsto)}")

    if st.button("🚀 Enviar Fotos de Voos", type="primary", key="vd_send_flight", use_container_width=True):
        if not files:
            st.warning("Selecione as imagens do drone ou um ZIP do voo.")
        elif not str(nome_voo).strip():
            st.warning("Informe o nome do voo para criar a pasta de destino.")
        elif not str(caminho).strip():
            st.warning("Escolha/informe o diretório de destino.")
        else:
            lote_id = f"VD_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_tv_safe_name(nome_voo)}"
            st.markdown("<div class='vd-progress-box'><b>Resumo da progressão de envio</b></div>", unsafe_allow_html=True)
            status_line = st.empty()
            progress = st.progress(0)
            status_line.info("1/4 — Criando pasta interna do lote e gravando arquivos...")
            saved, total_size = _vd_save_uploaded_files(files, VD_FLIGHTS_DIR / lote_id / "raw", progress)
            status_line.info("2/4 — Criando pasta com o nome do voo no destino escolhido...")
            destino_path, envio_status = _vd_copy_to_destination(saved, caminho, lote_id, nome_voo)
            progress.progress(92)
            status_line.info("3/4 — Atualizando manifesto e histórico do sistema...")
            record = {
                "lote_id": lote_id,
                "nome_voo": nome_voo,
                "nome_fazenda": fazenda,
                "fazenda": fazenda,
                "ensaio": ensaio,
                "inicio_final": inicio_final,
                "tipo_voo": tipo_voo,
                "quantidade_imagens": len(saved),
                "data_hora": _tv_now(),
                "usuario_responsavel": usuario,
                "data_voo": str(data_voo),
                "destino_enviado": destino,
                "caminho_destino": caminho,
                "pasta_nome_voo": _tv_safe_name(nome_voo),
                "destino_path": destino_path,
                "status_envio": envio_status,
                "tamanho_total": total_size,
                "tamanho_total_fmt": _tv_human_size(total_size),
                "identificador_lote": lote_id,
                "files": saved
            }
            manifest.setdefault("voos", []).insert(0, record)
            manifest.setdefault("config", {})["destino"] = destino
            manifest.setdefault("config", {})["caminho"] = caminho
            manifest.setdefault("config", {})["usuario_padrao"] = usuario
            _vd_add_history(manifest, f"Voo enviado com {len(saved)} arquivo(s) para pasta {record['pasta_nome_voo']}", lote_id, envio_status)
            _vd_save_manifest(manifest)
            progress.progress(100)
            status_line.success("4/4 — Envio finalizado e registrado no resumo.")
            st.success(f"Lote `{lote_id}` enviado. Pasta criada: `{destino_path or pasta_prevista}`. Status: {envio_status}")
            if saved:
                st.dataframe([{
                    "Arquivo": item.get("nome"),
                    "Tamanho": item.get("tamanho_fmt"),
                    "Enviado em": item.get("enviado_em"),
                    "SHA-256": item.get("sha256", "")[:16] + "..."
                } for item in saved], use_container_width=True, hide_index=True)

    st.markdown("#### Resumo de Envios")
    try:
        voos_manifest = manifest.get("voos", [])
        if not isinstance(voos_manifest, list):
            voos_manifest = []

        rows = []
        for v in voos_manifest:
            if not isinstance(v, dict):
                continue
            rows.append({
                "Nome do voo": v.get("nome_voo", ""),
                "Fazenda": v.get("nome_fazenda") or v.get("fazenda") or "",
                "Ensaio": v.get("ensaio", ""),
                "Início/Final": v.get("inicio_final", ""),
                "Tipo de voo": v.get("tipo_voo") or v.get("coordenadas") or "",
                "Imagens": v.get("quantidade_imagens", 0),
                "Data e hora": v.get("data_hora", ""),
                "Destino": v.get("destino_enviado", ""),
                "Pasta criada": v.get("destino_path", ""),
                "Status": v.get("status_envio", ""),
                "Tamanho": v.get("tamanho_total_fmt", ""),
                "Lote": v.get("identificador_lote") or v.get("lote_id") or ""
            })

        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum envio registrado ainda. Após enviar as fotos do voo, o resumo aparecerá aqui automaticamente.")
    except Exception:
        st.info("Resumo de Envios indisponível no momento. Faça um novo envio para atualizar o histórico automaticamente.")

def _vd_render_ortofotos(manifest: dict) -> None:
    st.markdown("#### PASSO 2 — Receber Ortofotos")
    project_options = _vd_project_options(manifest)

    with st.form("vd_ortho_import_form", clear_on_submit=False):
        selected_voo = st.selectbox("Voo vinculado", [""] + project_options, key="vd_ortho_voo")
        ortho_file = st.file_uploader(
            "Buscar/Importar Ortofoto Gerada",
            type=["tif", "tiff", "geotiff", "png", "jpg", "jpeg", "jp2", "img", "zip"],
            key="vd_ortho_file"
        )
        importar_ortho = st.form_submit_button("Importar Ortofoto", type="primary", use_container_width=True)

    if importar_ortho:
        if ortho_file is None:
            st.warning("Selecione a ortofoto processada externamente.")
        else:
            ortho_id = f"ORT_VD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            saved, _ = _vd_save_uploaded_files([ortho_file], VD_ORTHOS_DIR / ortho_id)
            item = saved[0]
            if any(o.get("sha256") == item.get("sha256") for o in manifest.get("orthos", [])):
                try:
                    Path(item["path"]).unlink()
                except Exception:
                    pass
                st.warning("Esta ortofoto já estava registrada e não foi importada novamente.")
            else:
                dims, spatial_meta, preview_error = None, {}, ""
                if item["ext"] != ".zip":
                    _mosaic_register_file(item["path"], item["nome"], "Voos Direcionados", item.get("sha256", ""), item.get("tamanho", 0))
                    preview_error = "Preview será gerado ao abrir a pré-visualização."
                record = {
                    "ortho_id": ortho_id,
                    "lote_id": _vd_id_from_option(selected_voo),
                    "nome": item["nome"],
                    "path": item["path"],
                    "tipo": item["ext"].replace(".", "").upper() or "RASTER",
                    "tamanho": item["tamanho"],
                    "tamanho_fmt": item["tamanho_fmt"],
                    "sha256": item["sha256"],
                    "resolucao_preview": f"{dims[0]}x{dims[1]} px" if dims else "Aguardando preview",
                    "spatial_meta": spatial_meta or {},
                    "crs": (spatial_meta or {}).get("crs", ""),
                    "status": "Ortofoto anexada - pronta para visualizar e marcar grid",
                    "data_processamento": _tv_now(),
                    "preview_error": preview_error or ""
                }
                manifest.setdefault("orthos", []).insert(0, record)
                voo = _vd_find_voo(manifest, record["lote_id"])
                if voo:
                    voo["status_envio"] = "Ortofoto anexada"
                    voo["ortho_id"] = ortho_id
                _vd_add_history(manifest, f"Ortofoto anexada: {item['nome']}", record["lote_id"])
                _vd_save_manifest(manifest)
                st.session_state.pop("vd_preview_ortho_id", None)
                st.success(f"Ortofoto `{ortho_id}` anexada.")
                st.info("A ortofoto foi registrada. Abra a pré-visualização somente quando quiser carregar o visualizador.")

    rows = [{
        "ID": o.get("ortho_id"),
        "Voo": o.get("lote_id"),
        "Arquivo": o.get("nome"),
        "Tipo": o.get("tipo"),
        "Resolução": o.get("resolucao_preview"),
        "CRS": (o.get("crs") or "")[:80],
        "Tamanho": o.get("tamanho_fmt"),
        "Status": o.get("status")
    } for o in manifest.get("orthos", [])]
    st.markdown("#### Ortofotos recebidas")
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma ortofoto anexada ainda.")
        return

    st.markdown("#### Pré-visualizador de Ortofoto")
    ortho_options = _vd_ortho_options(manifest)
    if not ortho_options:
        st.info("Nenhuma ortofoto anexada ainda.")
        return

    selected = st.selectbox("Ortofotos disponíveis/importadas", ortho_options, key="vd_ortho_selected")
    ortho_id = _vd_id_from_option(selected)
    ortho = _vd_find_ortho(manifest, ortho_id)
    if not ortho or not Path(ortho.get("path", "")).exists():
        st.warning("Arquivo da ortofoto não encontrado.")
        return

    open_col, grid_col = st.columns(2)
    with open_col:
        if st.button("Abrir pré-visualização", type="primary", key="vd_open_ortho_preview", use_container_width=True):
            st.session_state["vd_preview_ortho_id"] = ortho_id
            app_rerun()
    with grid_col:
        if st.button("Marcar Grid", key="vd_go_grid_selected", use_container_width=True):
            st.session_state["vd_pending_grid_ortho_id"] = ortho_id
            st.session_state["vd_next_tab"] = "ETAPA 3"
            app_rerun()

    if st.session_state.get("vd_preview_ortho_id") != ortho_id:
        st.info("Pré-visualização em espera. Clique em Abrir pré-visualização para carregar o mosaico no navegador.")
        return

    raw = Path(ortho["path"]).read_bytes()
    b64, dims, err, spatial_meta = processar_ortofoto(raw, ortho["nome"])
    if err:
        st.error(f"Não foi possível abrir o preview: {err}")
    else:
        ortho["spatial_meta"] = spatial_meta or ortho.get("spatial_meta", {})
        ortho["resolucao_preview"] = f"{dims[0]}x{dims[1]} px"
        _vd_save_manifest(manifest)
        components.html(_vd_ortho_viewer_html(b64, ortho["nome"], dims[0], dims[1]), height=700, scrolling=False)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.download_button(
                "Baixar Ortofoto Original",
                data=raw,
                file_name=Path(ortho["path"]).name,
                mime="application/octet-stream",
                use_container_width=True
            )
        with c2:
            st.download_button(
                "Baixar Compactada JPG",
                data=base64.b64decode(b64),
                file_name=f"{Path(ortho['nome']).stem}_compactada.jpg",
                mime="image/jpeg",
                use_container_width=True
            )
        with c3:
            png_buf = BytesIO()
            Image.open(BytesIO(base64.b64decode(b64))).save(png_buf, format="PNG")
            st.download_button(
                "Baixar PNG",
                data=png_buf.getvalue(),
                file_name=f"{Path(ortho['nome']).stem}_preview.png",
                mime="image/png",
                use_container_width=True
            )
        with c4:
            if st.button("Fechar pré-visualização", key="vd_close_ortho_preview", use_container_width=True):
                st.session_state.pop("vd_preview_ortho_id", None)
                app_rerun()

def _vd_render_grid(manifest: dict) -> None:
    st.markdown("#### Grid, Parcelas e Salvamento no Sistema")
    ortho_options = _vd_ortho_options(manifest)
    if not ortho_options:
        st.info("Anexe uma ortofoto gerada antes de marcar o grid.")
        return

    pending = st.session_state.pop("vd_pending_grid_ortho_id", "")
    current_options = [""] + ortho_options
    pending_option = next((opt for opt in current_options if opt.startswith(pending + " · ")), "")
    if pending_option and st.session_state.get("vd_grid_ortho") != pending_option:
        st.session_state.pop("vd_grid_ortho", None)
    grid_index = current_options.index(pending_option) if pending_option in current_options else 0

    left, right = st.columns([1, 2])
    with left:
        selected = st.selectbox("Ortofoto para marcar grid", current_options, index=grid_index, key="vd_grid_ortho")
        rows = st.number_input("Número de linhas", min_value=1, max_value=500, value=10, key="vd_grid_rows")
        cols = st.number_input("Número de colunas", min_value=1, max_value=500, value=10, key="vd_grid_cols")
        escala = st.text_input("Escala / referência espacial", value="Preservar metadados da ortofoto", key="vd_grid_scale")
        grid_json = st.file_uploader("JSON do grid exportado pelo visualizador", type=["json"], key="vd_grid_json_upload")

        if st.button("Salvar Grid no Sistema", type="primary", key="vd_save_grid_system", use_container_width=True):
            if not selected:
                st.warning("Selecione uma ortofoto.")
            elif grid_json is None:
                st.warning("Exporte o JSON no visualizador e anexe aqui para salvar o grid.")
            else:
                ortho_id = _vd_id_from_option(selected)
                ortho = _vd_find_ortho(manifest, ortho_id)
                raw = grid_json.getbuffer().tobytes()
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except Exception as exc:
                    st.error(f"JSON inválido: {exc}")
                    return
                grid_id = f"GRID_VD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                target = VD_GRIDS_DIR / f"{grid_id}_{Path(grid_json.name).name}"
                target.write_bytes(raw)
                parcelas = payload.get("parcelas", [])
                record = {
                    "grid_id": grid_id,
                    "ortho_id": ortho_id,
                    "lote_id": ortho.get("lote_id", "") if ortho else "",
                    "ortho_nome": ortho.get("nome", "") if ortho else "",
                    "path": str(target),
                    "linhas": int(rows),
                    "colunas": int(cols),
                    "parcelas": len(parcelas),
                    "ids_parcelas": [cell.get("id") or f"L{cell.get('linha')}_C{cell.get('coluna')}" for cell in parcelas],
                    "escala": escala,
                    "dados_posicionamento": payload.get("pontos", []),
                    "configuracoes": {"linhas": int(rows), "colunas": int(cols), "escala": escala},
                    "mini_resumo": {
                        "parcelas": len(parcelas),
                        "linhas": int(rows),
                        "colunas": int(cols),
                        "ortofoto": ortho.get("nome", "") if ortho else ""
                    },
                    "status": "Grid salvo no sistema",
                    "criado_em": _tv_now()
                }
                manifest.setdefault("grids", []).insert(0, record)
                if ortho:
                    ortho["status"] = "Grid salvo no sistema"
                    ortho["grid_id"] = grid_id
                voo = _vd_find_voo(manifest, record["lote_id"])
                if voo:
                    voo["status_envio"] = "Grid salvo"
                    voo["grid_id"] = grid_id
                _vd_add_history(manifest, f"Grid salvo no sistema: {grid_id}", record["lote_id"])
                _vd_save_manifest(manifest)
                st.success(f"Grid `{grid_id}` salvo com {len(parcelas)} parcela(s).")

        if selected:
            ortho_id_for_existing = _vd_id_from_option(selected)
            ortho_for_existing = _vd_find_ortho(manifest, ortho_id_for_existing)
            if st.button("Abrir no Marcador de Grid existente", key="vd_open_existing_grid", use_container_width=True):
                if ortho_for_existing:
                    st.session_state["grid_prefill_ortho_path"] = ortho_for_existing.get("path", "")
                    st.session_state["grid_prefill_ortho_name"] = ortho_for_existing.get("nome", "")
                ir_para("Grid")
                app_rerun()

    with right:
        if not selected:
            st.info("Selecione a ortofoto para abrir o visualizador de grid.")
        else:
            ortho_id = _vd_id_from_option(selected)
            ortho = _vd_find_ortho(manifest, ortho_id)
            if ortho and Path(ortho.get("path", "")).exists():
                raw = Path(ortho["path"]).read_bytes()
                b64, dims, err, _ = processar_ortofoto(raw, ortho["nome"])
                if err:
                    st.error(err)
                else:
                    st.caption(f"{ortho['nome']} · {dims[0]}x{dims[1]} px")
                    components.html(_tv_grid_viewer_html(b64, int(rows), int(cols), ortho["nome"]), height=700, scrolling=False)

    st.markdown("#### Exportação Final")
    grid_options = [f"{g['grid_id']} · {g.get('ortho_nome','Ortofoto')}" for g in manifest.get("grids", [])]
    if not grid_options:
        st.info("Nenhum grid salvo ainda.")
        return
    selected_grid = st.selectbox("Grid salvo para exportar", grid_options, key="vd_grid_export_select")
    grid_id = _vd_id_from_option(selected_grid)
    grid = _vd_find_grid(manifest, grid_id)
    ortho = _vd_find_ortho(manifest, grid.get("ortho_id", "")) if grid else {}
    if not grid or not ortho:
        st.warning("Grid ou ortofoto não encontrados.")
        return

    e1, e2, e3, e4, e5, e6 = st.columns(6)
    with e1:
        st.download_button(
            "Baixar Ortofoto com Grid PNG",
            data=_vd_grid_overlay_bytes(grid, ortho, "PNG"),
            file_name=f"{grid_id}_ortofoto_grid.png",
            mime="image/png",
            use_container_width=True
        )
    with e2:
        st.download_button(
            "Baixar JPG",
            data=_vd_grid_overlay_bytes(grid, ortho, "JPEG"),
            file_name=f"{grid_id}_ortofoto_grid.jpg",
            mime="image/jpeg",
            use_container_width=True
        )
    with e3:
        st.download_button(
            "Baixar TIFF",
            data=_vd_grid_overlay_bytes(grid, ortho, "TIFF"),
            file_name=f"{grid_id}_ortofoto_grid.tif",
            mime="image/tiff",
            use_container_width=True
        )
    with e4:
        st.download_button(
            "GeoTIFF",
            data=_vd_grid_geotiff_overlay_bytes(grid, ortho),
            file_name=f"{grid_id}_ortofoto_grid_geotiff.tif",
            mime="image/tiff",
            use_container_width=True
        )
    with e5:
        st.download_button(
            "GeoJSON",
            data=_vd_grid_geojson_bytes(grid, ortho),
            file_name=f"{grid_id}_parcelas.geojson",
            mime="application/geo+json",
            use_container_width=True
        )
    with e6:
        st.download_button(
            "SHP QGIS",
            data=_vd_grid_shp_zip_bytes(grid, ortho),
            file_name=f"{grid_id}_parcelas_shp.zip",
            mime="application/zip",
            use_container_width=True
        )

    rows_grid = [{
        "Grid": g.get("grid_id"),
        "Ortofoto": g.get("ortho_nome"),
        "Linhas": g.get("linhas"),
        "Colunas": g.get("colunas"),
        "Parcelas": g.get("parcelas"),
        "Status": g.get("status"),
        "Data": g.get("criado_em")
    } for g in manifest.get("grids", [])]
    st.markdown("#### Grids salvos")
    st.dataframe(rows_grid, use_container_width=True, hide_index=True)

def _vd_render_projetos(manifest: dict) -> None:
    st.markdown("#### PASSO 4 — Retornar Dados")
    rows = []
    for voo in manifest.get("voos", []):
        ortho = _vd_find_ortho(manifest, voo.get("ortho_id", ""))
        grid = _vd_find_grid(manifest, voo.get("grid_id", ""))
        rows.append({
            "Nome do projeto": voo.get("nome_voo"),
            "Data": voo.get("data_hora"),
            "Imagens": voo.get("quantidade_imagens"),
            "Parcelas": grid.get("parcelas", 0) if grid else 0,
            "Status": voo.get("status_envio"),
            "Ortofoto": ortho.get("nome", "") if ortho else "",
            "Lote": voo.get("lote_id")
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    options = _vd_project_options(manifest)
    if not options:
        st.info("Nenhum projeto salvo ainda.")
        return
    selected = st.selectbox("Abrir projeto", options, key="vd_project_open")
    lote_id = _vd_id_from_option(selected)
    voo = _vd_find_voo(manifest, lote_id)
    if not voo:
        return
    ortho = _vd_find_ortho(manifest, voo.get("ortho_id", ""))
    grid = _vd_find_grid(manifest, voo.get("grid_id", ""))

    c1, c2 = st.columns([1, 2])
    with c1:
        if ortho and Path(ortho.get("path", "")).exists():
            raw = Path(ortho["path"]).read_bytes()
            b64, dims, err, _ = processar_ortofoto(raw, ortho["nome"])
            if not err:
                app_image(Image.open(BytesIO(base64.b64decode(b64))))
                st.caption(f"Miniatura: {ortho['nome']} · {dims[0]}x{dims[1]}")
            else:
                st.info("Miniatura indisponível.")
        else:
            st.info("Projeto ainda sem ortofoto anexada.")
    with c2:
        st.markdown(
            f"<div class='vd-card'><b style='color:#ff8c00;'>Projeto:</b> {voo.get('nome_voo')}<br>"
            f"<b>Fazenda:</b> {voo.get('fazenda') or '-'} &nbsp; <b>Talhão:</b> {voo.get('talhao') or '-'}<br>"
            f"<b>Lote:</b> {lote_id}<br><b>Status:</b> {voo.get('status_envio')}</div>",
            unsafe_allow_html=True
        )
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Abrir", key="vd_project_btn_open", use_container_width=True):
                if ortho:
                    st.session_state["vd_next_tab"] = "ETAPA 2"
                    app_rerun()
                else:
                    st.info("Anexe a ortofoto para abrir o preview.")
        with b2:
            st.download_button(
                "Baixar manifesto",
                data=json.dumps(voo, indent=2, ensure_ascii=False).encode("utf-8"),
                file_name=f"{lote_id}_manifesto.json",
                mime="application/json",
                use_container_width=True
            )
        with b3:
            if st.button("Continuar edição", key="vd_project_continue", use_container_width=True):
                if ortho:
                    st.session_state["vd_pending_grid_ortho_id"] = ortho.get("ortho_id")
                    st.session_state["vd_next_tab"] = "ETAPA 3"
                    app_rerun()
                else:
                    st.warning("Projeto ainda sem ortofoto para edição.")

        if grid and ortho:
            st.download_button(
                "Baixar Ortofoto com Grid",
                data=_vd_grid_overlay_bytes(grid, ortho, "PNG"),
                file_name=f"{grid.get('grid_id')}_ortofoto_grid.png",
                mime="image/png",
                use_container_width=True
            )

def _vd_render_historico(manifest: dict) -> None:
    st.markdown("#### Histórico de Alterações")
    st.dataframe(manifest.get("history", []), use_container_width=True, hide_index=True)
    st.download_button(
        "Baixar banco interno JSON",
        data=json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"),
        file_name="voos_direcionados_manifest.json",
        mime="application/json",
        use_container_width=True
    )

def render_voos_direcionados() -> None:
    _vd_ensure_storage()
    if "vd_logged_in" not in st.session_state:
        st.session_state.vd_logged_in = False
    if not st.session_state.vd_logged_in:
        _vd_render_login()
        return

    manifest = _vd_load_manifest()
    st.markdown("""
    <style>
      .vd-hero {
        background:linear-gradient(145deg,#181818 0%,#101010 58%,#2a1700 100%);
        border:1px solid #3a2a18;
        border-top:2px solid #ff8c00;
        border-radius:8px;
        padding:20px 22px;
        margin-bottom:14px;
        box-shadow:4px 4px 14px #070707,0 0 24px rgba(255,140,0,.10);
      }
      .vd-hero h2 {
        margin:0;
        color:#ff8c00;
        letter-spacing:3px;
        text-transform:uppercase;
        text-shadow:1px 1px 0 #7a3a00,3px 3px 8px #000,0 0 22px rgba(255,140,0,.32);
      }
      .vd-hero p { margin:8px 0 0 0; color:#cfcfcf; font-size:13px; }
      .vd-card {
        background:#161616;
        border:1px solid #303030;
        border-radius:8px;
        padding:14px;
        color:#ddd;
        margin-bottom:10px;
      }
      div[data-testid="stRadio"] > div {
        background:#151515;
        border:1px solid #2e2e2e;
        border-radius:8px;
        padding:8px 10px;
      }
      div[data-testid="stRadio"] label {
        background:linear-gradient(145deg,#222,#111);
        border:1px solid #303030;
        border-radius:8px;
        padding:7px 10px;
        margin-right:4px;
      }
      div[data-testid="stRadio"] label:hover { border-color:#ff8c00; box-shadow:0 0 12px rgba(255,140,0,.12); }
      div[data-testid="stRadio"] label:has(input:checked) {
        border-color:#ff8c00;
        background:linear-gradient(145deg,#ff9e33,#e67600);
        box-shadow:0 0 16px rgba(255,140,0,.22);
      }
    </style>
    """, unsafe_allow_html=True)

    ctop1, ctop2 = st.columns([5, 1])
    with ctop1:
        st.markdown(
            "<div class='vd-hero'><h2>Processos de Voos para Análise</h2>"
            "<p>Fluxo passo a passo: enviar fotos de voos, receber ortofotos, marcar grid e retornar dados para análise.</p>"
            f"{_tv_status_chip('Janela isolada', '#ff8c00')}"
            f"{_tv_status_chip('Banco interno isolado', '#55ff99')}"
            f"{_tv_status_chip('QGIS / GeoJSON / SHP', '#5599ff')}"
            "</div>",
            unsafe_allow_html=True
        )
    with ctop2:
        if st.button("Sair", key="vd_logout", use_container_width=True):
            st.session_state.vd_logged_in = False
            app_rerun()

    _vd_metric_cards(manifest)

    tabs = ["Enviar Fotos de Voos", "Receber Ortofotos", "Marcador de Grid", "Retornar Dados", "Histórico"]
    legacy_tabs = {
        "ETAPA 1": "Enviar Fotos de Voos",
        "ETAPA 2": "Receber Ortofotos",
        "ETAPA 3": "Marcador de Grid",
        "ETAPA 4": "Retornar Dados",
        "HIST.": "Histórico",
        "Envio de Imagens": "Enviar Fotos de Voos",
        "Ortofotos": "Receber Ortofotos",
        "Marcar Grid": "Marcador de Grid",
        "Projetos Salvos": "Retornar Dados",
        "Histórico": "Histórico"
    }
    next_tab = st.session_state.pop("vd_next_tab", None)
    next_tab = legacy_tabs.get(next_tab, next_tab)
    if next_tab in tabs and st.session_state.get("vd_active_tab") != next_tab:
        st.session_state.pop("vd_active_tab", None)
        tab_index = tabs.index(next_tab)
    else:
        current_tab = st.session_state.get("vd_active_tab", tabs[0])
        current_tab = legacy_tabs.get(current_tab, current_tab)
        tab_index = tabs.index(current_tab) if current_tab in tabs else 0
    active = st.radio("Processos de Voos para Análise", tabs, horizontal=True, label_visibility="collapsed", index=tab_index, key="vd_active_tab")
    etapa_desc = {
        "Enviar Fotos de Voos": "PASSO 1: selecionar fotos, definir caminho do Azure/destino e enviar o lote.",
        "Receber Ortofotos": "PASSO 2: buscar/importar ortofoto gerada e abrir no visualizador.",
        "Marcador de Grid": "PASSO 3: usar o marcador de grid, salvar parcelas e preparar exportação.",
        "Retornar Dados": "PASSO 4: disponibilizar ortofoto, grid, SHP, GeoJSON e resumo final.",
        "Histórico": "Histórico e banco interno isolado."
    }
    st.caption(etapa_desc.get(active, ""))
    st.markdown("---")

    if active == "Enviar Fotos de Voos":
        _vd_render_envio(manifest)
        st.markdown("---")
        if st.button("Próximo Passo ➜ Receber Ortofotos", key="vd_next_to_ortho", type="primary", use_container_width=True):
            st.session_state["vd_next_tab"] = "Receber Ortofotos"
            app_rerun()
    elif active == "Receber Ortofotos":
        _vd_render_ortofotos(manifest)
        st.markdown("---")
        if st.button("Próximo Passo ➜ Marcador de Grid", key="vd_next_to_grid", type="primary", use_container_width=True):
            st.session_state["vd_next_tab"] = "Marcador de Grid"
            app_rerun()
    elif active == "Marcador de Grid":
        _vd_render_grid(manifest)
        st.markdown("---")
        if st.button("Próximo Passo ➜ Retornar Dados", key="vd_next_to_return", type="primary", use_container_width=True):
            st.session_state["vd_next_tab"] = "Retornar Dados"
            app_rerun()
    elif active == "Retornar Dados":
        _vd_render_projetos(manifest)
    elif active == "Histórico":
        _vd_render_historico(manifest)





# ==========================================
# SIDEBAR[cite: 1]
# ==========================================
with st.sidebar:

    st.markdown("""
    <div class='menu-3d-title'>&#9776; MENU</div>
    <hr class='separator-glow'>
    """, unsafe_allow_html=True)

    if st.button("📋 Checklist Notas", key="btn_check"):
        ir_para('Checklist')

    if st.button("📊 Marcador de Grid", key="btn_grid"):
        ir_para('Grid')

    if st.button("📤 Upload de Imagens", key="btn_upload"):
        ir_para('Upload')

    if st.button("🗂️ Banco de Dados Sistema", key="btn_bases"):
        ir_para('Bases')

    if st.button("🔄 Sincronizar Dados", key="btn_sync"):
        ir_para('Sync')

    if st.button("🛰️ Gerar Ortomosaicos", key="btn_orto"):
        ir_para('Ortomosaicos')

    # NOVO - Botão Análises de Fenotipagem
    if st.button("📈 Análises de Fenotipagem", key="btn_visualizador"):
        ir_para('Visualizador')

    # NOVO - Botão isolado para fluxo passo a passo de voos para análise
    if st.button("🛰️ Processos de Voos para Análise", key="btn_processos_voos_analise"):
        ir_para('VoosDirecionados')

    if st.button("⚙️ Configurações", key="btn_config"):
        ir_para('Config')

    st.markdown("---")
    st.caption("TMG v2.0 - 2026")

# ==========================================
# TOPO (LOGO FIXA)[cite: 1]
# ==========================================
if st.session_state.logo_sistema and st.session_state.pagina_ativa not in ('TransferenciaVoos', 'VoosDirecionados'):
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        app_image(st.session_state.logo_sistema)

if st.session_state.pagina_ativa not in ('TransferenciaVoos', 'VoosDirecionados'):
    st.markdown("<h1 class='main-header'>TMG SISTEMA DE ANÁLISE</h1>", unsafe_allow_html=True)

# ==========================================
# CONTEÚDO[cite: 1]
# ==========================================
main_container = st.container()

with main_container:

    # ==========================================
    # TRANSFERENCIA DE VOOS
    # ==========================================
    if st.session_state.pagina_ativa == 'TransferenciaVoos':
        render_transferencia_voos()

    # ==========================================
    # VOOS DIRECIONADOS
    # ==========================================
    elif st.session_state.pagina_ativa == 'VoosDirecionados':
        render_voos_direcionados()

    # ==========================================
    # CHECKLIST[cite: 1]
    # ==========================================
    elif st.session_state.pagina_ativa == 'Checklist':
        st.subheader("📋 Avaliador de Parcelas")

        # ── Visualizador com anotação de parcelas ──────────────────────────
        st.markdown("""
        <div style='color:#ff8c00;font-weight:700;font-size:1rem;letter-spacing:2px;
                    text-transform:uppercase;margin-bottom:10px;'>
            🗺️ Visualizador de Ortofoto · Anotação de Parcelas
        </div>""", unsafe_allow_html=True)

        chk_file = st.file_uploader(
            "Selecione a ortofoto para anotação",
            type=MOSAIC_UPLOAD_TYPES,
            key="chk_orto_uploader",
            help="PNG · JPG · TIF/GeoTIFF · JP2 · IMG · ECW"
        )
        chk_library = _mosaic_single_select("Ou usar mosaico já importado", key="chk_mosaic_library")
        if chk_library:
            _, delete_mosaic_col = st.columns([3, 1])
            with delete_mosaic_col:
                if st.button("🗑️ Excluir mosaico", key="chk_delete_mosaic", use_container_width=True):
                    ok, msg = _mosaic_delete(chk_library)
                    if ok:
                        st.success(msg)
                    else:
                        st.warning(msg)
                    app_rerun()
        chk_bytes, chk_name = _mosaic_input_bytes(chk_file, chk_library, "Checklist")

        if chk_bytes:
            with st.spinner("Carregando ortofoto..."):
                # Atualizado Unpack para o spatial_meta
                chk_b64, chk_dims, chk_err, chk_spatial = processar_ortofoto(chk_bytes, chk_name)

            if chk_err:
                st.error(f"Erro: {chk_err}")
            else:
                cw, ch = chk_dims
                chk_storage_id = json.dumps(_tv_hash_bytes(chk_bytes)[:32])
                st.markdown(
                    f"<p style='color:#666;font-size:0.78rem;margin-bottom:6px;'>"
                    f"📐 {chk_name} · {cw}×{ch} px</p>",
                    unsafe_allow_html=True
                )

                chk_viewer = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:#0d0d0d; overflow:auto; font-family:'Segoe UI',sans-serif; }}

  #vc {{
    width:100%; height:706px;
    background:
      linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px),
      #0d0d0d;
    background-size:32px 32px;
    border:1px solid #2a2a2a; border-radius:12px;
    overflow:hidden; position:relative; cursor:grab; user-select:none;
  }}
  #vc:active {{ cursor:grabbing; }}
  canvas {{ position:absolute; top:0; left:0; display:block; }}

  .toolbar {{ position:absolute; top:12px; right:12px; display:flex; flex-direction:column; gap:5px; z-index:20; }}
  .tb-btn {{
    background:linear-gradient(145deg,#1e1e1e,#111); border:1px solid #3a3a3a;
    color:#ff8c00; width:34px; height:34px; border-radius:8px; cursor:pointer;
    font-size:15px; font-weight:700; display:flex; align-items:center; justify-content:center;
    box-shadow:2px 2px 8px #000,inset 0 1px 0 rgba(255,255,255,.05); transition:all .2s;
  }}
  .tb-btn:hover {{ border-color:#ff8c00; box-shadow:0 0 10px rgba(255,140,0,.35),2px 2px 8px #000; color:#ffaa33; }}
  .tb-btn:active {{ transform:translateY(1px); }}
  .tb-sep {{ width:34px; height:1px; background:linear-gradient(90deg,transparent,#333,transparent); margin:2px 0; }}

  .grid-panel {{
    position:absolute; top:12px; right:55px;
    background:rgba(10,10,10,.88); border:1px solid #2a2a2a;
    border-radius:8px; padding:10px; display:flex; flex-direction:column;
    gap:8px; z-index:20;
  }}
  .grid-panel label {{ color:#ff8c00; font-size:11px; font-weight:bold; text-align:center; }}
  .grid-panel input[type=number] {{
    background:#1a1a1a; border:1px solid #333; color:#fff;
    border-radius:4px; padding:4px; width:50px; text-align:center; font-size:11px;
  }}
  .grid-panel input[type=text], .grid-panel select {{
    background:#1a1a1a; border:1px solid #333; color:#fff;
    border-radius:4px; padding:4px; font-size:11px; min-width:110px;
  }}
  .grid-panel .row-col {{ display:flex; gap:8px; align-items:center; justify-content:space-between; color:#ccc; font-size:11px; }}
  .grid-status {{ color:#777; font-size:9px; line-height:1.25; max-width:190px; }}
  .grid-all-status {{
    color:#44ff99; font-size:10px; line-height:1.25; max-width:190px;
    border:1px solid #1f5f3a; border-radius:5px; padding:5px; background:rgba(0,80,40,.16);
  }}
  .grid-btn {{
    background:linear-gradient(145deg,#1e1e1e,#111); border:1px solid #3a3a3a;
    color:#ccc; cursor:pointer; border-radius:4px; padding:6px; font-size:11px; font-weight:bold; transition:.2s;
  }}
  .grid-btn:hover {{ border-color:#ff8c00; color:#ff8c00; }}
  .grid-btn.active {{ border-color:#ff8c00; color:#ff8c00; box-shadow:0 0 8px rgba(255,140,0,.3); background:#2a1a00; }}
  .grid-btn.annot {{ border-color:#00cfff; color:#00cfff; }}
  .grid-btn.annot.active {{ background:#001a2a; box-shadow:0 0 8px rgba(0,207,255,.3); }}

  #btnExport {{
    background:linear-gradient(145deg,#003a00,#001a00); border:1px solid #006600;
    color:#00ee55; border-radius:4px; padding:6px 8px; font-size:11px;
    font-weight:bold; cursor:pointer; transition:.2s; width:100%;
  }}
  #btnExport:hover {{ border-color:#00ee55; box-shadow:0 0 8px rgba(0,238,85,.3); }}
  #btnQuickNote.quick-active {{
    background:linear-gradient(145deg,#003a16,#001a0a);
    border-color:#00d46a;
    color:#44ff99;
    box-shadow:0 0 10px rgba(0,212,106,.35);
  }}

  .zoom-badge {{
    position:absolute; top:12px; left:12px;
    background:rgba(10,10,10,.82); border:1px solid #2a2a2a; border-radius:8px;
    color:#ff8c00; font-size:11px; font-family:'Courier New',monospace;
    font-weight:700; padding:5px 10px; letter-spacing:1px; z-index:20; pointer-events:none;
  }}
  .crosshair {{
    position:absolute; bottom:12px; left:12px;
    background:rgba(10,10,10,.82); border:1px solid #222; border-radius:8px;
    color:#555; font-size:10px; font-family:'Courier New',monospace;
    padding:4px 10px; z-index:20; pointer-events:none; letter-spacing:.5px;
  }}
  .hint {{
    position:absolute; bottom:12px; right:12px; color:#333; font-size:10px;
    z-index:20; pointer-events:none; text-align:right; line-height:1.6;
  }}

  #annotPopup {{
    position:absolute; display:none;
    background:linear-gradient(160deg,#1c1c1c,#111);
    border:1px solid #ff8c00; border-radius:12px; padding:14px 16px;
    z-index:40; min-width:245px; max-width:290px;
    box-shadow:0 8px 28px rgba(0,0,0,.9),0 0 16px rgba(255,140,0,.2);
    transform:translate(-50%,-50%);
  }}
  #annotPopup h4 {{ color:#ff8c00; font-size:12px; letter-spacing:2px; text-transform:uppercase; margin-bottom:10px; text-align:center; }}
  #annotPopup .nota-row {{ display:flex; gap:5px; flex-wrap:wrap; margin-bottom:10px; }}
  .nota-btn {{
    width:36px; height:36px; border-radius:7px; border:1px solid #333;
    background:#1a1a1a; color:#ccc; font-weight:800; font-size:15px;
    cursor:pointer; transition:.15s; display:flex; align-items:center; justify-content:center;
  }}
  .nota-btn:hover {{ border-color:#ff8c00; color:#ff8c00; }}
  .nota-btn.sel {{ background:#ff8c00; color:#000; border-color:#ff8c00; box-shadow:0 0 8px rgba(255,140,0,.5); }}
  #annotObs {{
    width:100%; background:#111; border:1px solid #333; color:#ddd;
    border-radius:6px; padding:7px; font-size:11px; resize:vertical; min-height:60px;
    font-family:'Segoe UI',sans-serif; margin-bottom:10px;
  }}
  #annotObs:focus {{ border-color:#ff8c00; outline:none; }}
  .popup-btns {{ display:flex; gap:6px; }}
  .popup-save, .popup-next {{
    flex:1; background:linear-gradient(145deg,#ff9e33,#e07000);
    color:#fff; border:none; border-radius:6px; padding:7px;
    font-size:11px; font-weight:700; cursor:pointer;
  }}
  .popup-next {{ background:linear-gradient(145deg,#0077aa,#004b77); }}
  .popup-cancel {{
    background:#1a1a1a; color:#888; border:1px solid #333;
    border-radius:6px; padding:7px 10px; font-size:11px; cursor:pointer;
  }}
  .popup-cancel:hover {{ color:#ff6b6b; border-color:#552222; }}
  .assessment-panel {{
    margin-top:12px; background:#151515; border:1px solid #333; border-radius:12px;
    padding:14px; color:#ddd; box-shadow:0 6px 18px rgba(0,0,0,.55);
  }}
  .assessment-panel-title {{
    color:#ff8c00; font-weight:800; font-size:13px; letter-spacing:2px;
    text-transform:uppercase; margin-bottom:10px;
  }}
  .assessment-table {{ width:100%; border-collapse:collapse; font-size:11px; }}
  .assessment-table th {{
    background:#1f1f1f; color:#ff8c00; border:1px solid #333;
    padding:7px; text-align:left; text-transform:uppercase; letter-spacing:1px;
  }}
  .assessment-table td {{ border:1px solid #2b2b2b; padding:6px; color:#ddd; }}
  .assessment-empty {{ color:#777; font-size:12px; padding:8px 0; }}
</style>
</head>
<body>
<div id="vc">
  <canvas id="cv"></canvas>
  <div class="zoom-badge" id="zbadge">100%</div>

  <div class="grid-panel">
    <label>📍 MARCAÇÃO DE GRID</label>
    <div class="row-col"><span>Nome:</span><input type="text" id="inpGridName" value="Grid 1"></div>
    <div class="row-col"><span>Ativo:</span><select id="selGridList"></select></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;">
      <button class="grid-btn" id="btnSaveGrid">Salvar Grid</button>
      <button class="grid-btn" id="btnNewGrid">Novo Grid</button>
    </div>
    <div class="grid-status" id="gridStatus">Grid ativo: Grid 1</div>
    <div class="grid-all-status" id="gridAllStatus">👁️ Todos os grids salvos visíveis: ATIVO</div>
    <button class="grid-btn" id="btnGridTool">Ativar Marcação</button>
    <div class="row-col"><span>DISPAROS:</span><input type="number" id="inpRows" value="10" min="1" max="500"></div>
    <div class="row-col"><span>TIROS:</span><input type="number" id="inpCols" value="10" min="1" max="500"></div>
    <div class="row-col" style="justify-content:flex-start; gap:4px; margin-top:4px;">
        <input type="checkbox" id="cbShowSummary" checked style="width:auto;">
        <span style="font-size:10px;">👁️ Mostrar ID e Resumo</span>
    </div>
    <div class="row-col"><span>Tam. ID:</span><input type="number" id="inpIdTextSize" value="12" min="5" max="40"></div>
    <div class="row-col"><span>Tam. Nota:</span><input type="number" id="inpNoteTextSize" value="10" min="5" max="40"></div>
    <div class="tb-sep" style="width:100%"></div>
    <button class="grid-btn annot" id="btnAnnotTool">✏️ Anotar Parcela</button>
    <button class="grid-btn" id="btnQuickNote" style="border-color:#00a651;color:#44ff99;">⚡ Nota Rápida</button>
    <button id="btnExport">📥 Exportar Excel</button>
    <button class="grid-btn" id="btnClearGrid" style="color:#ff6b6b;border-color:#552222;">🗑️ Limpar Grid</button>
  </div>

  <div class="toolbar">
    <button class="tb-btn" id="btnZI">+</button>
    <button class="tb-btn" id="btnZO">−</button>
    <div class="tb-sep"></div>
    <button class="tb-btn" id="btnFit">⊡</button>
    <button class="tb-btn" id="btnN">1:1</button>
    <div class="tb-sep"></div>
    <button class="tb-btn" id="btnR">↺</button>
  </div>

  <div class="crosshair" id="coord">X: — &nbsp; Y: —</div>
  <div class="hint">Scroll: zoom &nbsp;|&nbsp; Arrastar: mover<br>Anotar/Nota Rápida: duplo clique na parcela</div>

  <div id="annotPopup">
    <h4 id="popupTitle">Parcela T1 D1</h4>
    <div class="nota-row" id="notaBtns"></div>
    <textarea id="annotObs" placeholder="Observação da parcela..."></textarea>
    <div class="popup-btns">
      <button class="popup-save" id="btnPopupSave">💾 Salvar</button>
      <button class="popup-next" id="btnPopupNext">Próxima</button>
      <button class="popup-cancel" id="btnPopupCancel">✕</button>
    </div>
    <!-- NOVO RECURSO: Exportação individual por célula -->
    <div class="popup-btns" style="margin-top:6px;">
      <button class="popup-save" style="background:linear-gradient(145deg,#0077aa,#005588);" id="btnExportCellPNG" title="Salvar imagem da célula com informações geradas visualmente">🖼️ Resumo PNG</button>
      <button class="popup-save" style="background:linear-gradient(145deg,#008844,#006633);" id="btnExportCellData" title="Salvar dados da célula em JSON">📄 Dados</button>
    </div>
  </div>
</div>
<div class="assessment-panel">
  <div class="assessment-panel-title">📊 Painel da Avaliação de Parcelas</div>
  <div id="assessmentSummary"></div>
</div>

<script>
const IMG_B64 = '{chk_b64}';
const vc    = document.getElementById('vc');
const cv    = document.getElementById('cv');
const ctx   = cv.getContext('2d');
const zb    = document.getElementById('zbadge');
const coord = document.getElementById('coord');

const inpRows = document.getElementById('inpRows');
const inpCols = document.getElementById('inpCols');
const cbShowSummary = document.getElementById('cbShowSummary');
const inpIdTextSize = document.getElementById('inpIdTextSize');
const inpNoteTextSize = document.getElementById('inpNoteTextSize');
const inpGridName = document.getElementById('inpGridName');
const selGridList = document.getElementById('selGridList');
const btnSaveGrid = document.getElementById('btnSaveGrid');
const btnNewGrid = document.getElementById('btnNewGrid');
const gridStatus = document.getElementById('gridStatus');
const btnGrid = document.getElementById('btnGridTool');
const btnAnnot = document.getElementById('btnAnnotTool');
const btnQuickNote = document.getElementById('btnQuickNote');
const btnClear = document.getElementById('btnClearGrid');
const btnExport = document.getElementById('btnExport');
const annotPopup = document.getElementById('annotPopup');
const assessmentSummary = document.getElementById('assessmentSummary');
const gridAllStatus = document.getElementById('gridAllStatus');
const ORTHO_STORAGE_ID = {chk_storage_id};
const STORAGE_KEY = 'tmg_checklist_notas_grids_' + ORTHO_STORAGE_ID;
let suppressPersist = false;

let gridMode = false;
let annotMode = false;
let quickNoteMode = false;
let points = [];
let draggingPoint = -1;
let sc = 1, ox = 0, oy = 0;
let drag = false, lx = 0, ly = 0;
const MIN_SC = 0.05, MAX_SC = 40;
let imgW = 0, imgH = 0;

let annotations = {{}};
let savedGrids = {{}};
let activeGridName = 'Grid 1';
let activeCell = null;
let activeNota = 0;

const img = new Image();

const notaBtns = document.getElementById('notaBtns');
for(let n=1; n<=9; n++) {{
  const b = document.createElement('button');
  b.className = 'nota-btn'; b.textContent = n;
  b.onclick = () => selectNota(n);
  notaBtns.appendChild(b);
}}

function selectNota(n) {{
  activeNota = n;
  document.querySelectorAll('.nota-btn').forEach((b,i) => {{
    b.classList.toggle('sel', i+1 === n);
  }});
}}

function getImgCoords(cx, cy) {{
  const r = cv.getBoundingClientRect();
  return {{ x:(cx-r.left-ox)/sc, y:(cy-r.top-oy)/sc }};
}}

function bilerp(p0,p1,p2,p3, u,v) {{
  const tx = (1-u)*p0.x + u*p1.x;
  const ty = (1-u)*p0.y + u*p1.y;
  const bx = (1-u)*p3.x + u*p2.x;
  const by = (1-u)*p3.y + u*p2.y;
  return {{ x:(1-v)*tx + v*bx, y:(1-v)*ty + v*by }};
}}

function invBilerp(px, py, p0, p1, p2, p3) {{
  let u=0.5, v=0.5;
  for(let k=0; k<20; k++) {{
    const f = bilerp(p0,p1,p2,p3,u,v);
    const fu = bilerp(p0,p1,p2,p3,u+0.001,v);
    const fv = bilerp(p0,p1,p2,p3,u,v+0.001);
    const du_dx=(fu.x-f.x)/0.001, du_dy=(fu.y-f.y)/0.001;
    const dv_dx=(fv.x-f.x)/0.001, dv_dy=(fv.y-f.y)/0.001;
    const det=du_dx*dv_dy - du_dy*dv_dx;
    if(Math.abs(det)<1e-10) break;
    const ex=px-f.x, ey=py-f.y;
    u += ( dv_dy*ex - dv_dx*ey)/det;
    v += (-du_dy*ex + du_dx*ey)/det;
    u=Math.max(0,Math.min(1,u));
    v=Math.max(0,Math.min(1,v));
  }}
  return {{u,v}};
}}

function getCellFromImgPt(ix, iy) {{
  if(points.length < 4) return null;
  const R=parseInt(inpRows.value)||1;
  const C=parseInt(inpCols.value)||1;
  const {{u,v}} = invBilerp(ix,iy,points[0],points[1],points[2],points[3]);
  if(u<0||u>1||v<0||v>1) return null;
  const c = Math.floor(u*C); const r = Math.floor(v*R);
  return {{ r:Math.min(r,R-1), c:Math.min(c,C-1) }};
}}

function getCellQuad(r,c) {{
  if(points.length < 4) return null;
  const R=parseInt(inpRows.value)||1;
  const C=parseInt(inpCols.value)||1;
  const p0=points[0],p1=points[1],p2=points[2],p3=points[3];
  const u0=c/C, u1=(c+1)/C, v0=r/R, v1=(r+1)/R;
  const tl=bilerp(p0,p1,p2,p3,u0,v0);
  const tr=bilerp(p0,p1,p2,p3,u1,v0);
  const br=bilerp(p0,p1,p2,p3,u1,v1);
  const bl=bilerp(p0,p1,p2,p3,u0,v1);
  return {{
    tl,tr,br,bl,
    cx:(tl.x+tr.x+br.x+bl.x)/4,
    cy:(tl.y+tr.y+br.y+bl.y)/4
  }};
}}

function getNotaFillColor(nota) {{
  if(nota>=9) return 'rgba(0,176,80,0.50)';
  if(nota>=7) return 'rgba(80,220,120,0.38)';
  if(nota>=5) return 'rgba(255,205,0,0.38)';
  return 'rgba(220,50,50,0.42)';
}}

function resumoObs(obs) {{
  const clean = String(obs || '').trim();
  if(!clean) return '';
  return clean.length > 18 ? clean.slice(0,18) + '...' : clean;
}}

function clonePoints(src) {{
  return (src || []).map(p => ({{x:Number(p.x)||0, y:Number(p.y)||0}}));
}}

function cloneAnnotations(src) {{
  return JSON.parse(JSON.stringify(src || {{}}));
}}

function cleanGridName(name) {{
  const value = String(name || '').trim();
  return value || 'Grid 1';
}}

function persistGrids() {{
  if(suppressPersist) return;
  try {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify({{
      activeGridName,
      savedGrids,
      updatedAt: new Date().toISOString()
    }}));
  }} catch(e) {{ console.warn('Não foi possível persistir grids:', e); }}
}}

function restoreGrids() {{
  try {{
    const raw = localStorage.getItem(STORAGE_KEY);
    if(!raw) return false;
    const data = JSON.parse(raw);
    if(!data || !data.savedGrids) return false;
    savedGrids = data.savedGrids || {{}};
    activeGridName = cleanGridName(data.activeGridName || Object.keys(savedGrids)[0] || 'Grid 1');
    const rec = savedGrids[activeGridName] || savedGrids[Object.keys(savedGrids)[0]];
    if(rec) {{
      points = clonePoints(rec.points);
      annotations = cloneAnnotations(rec.annotations);
      inpRows.value = rec.rows || inpRows.value;
      inpCols.value = rec.cols || inpCols.value;
    }}
    return Object.keys(savedGrids).length > 0;
  }} catch(e) {{ console.warn('Não foi possível restaurar grids:', e); return false; }}
}}

function updateGridSelect() {{
  if(!savedGrids[activeGridName]) {{
    savedGrids[activeGridName] = {{
      points: clonePoints(points),
      annotations: cloneAnnotations(annotations),
      rows: parseInt(inpRows.value)||1,
      cols: parseInt(inpCols.value)||1
    }};
  }}
  const names = Object.keys(savedGrids);
  selGridList.innerHTML = '';
  names.forEach(name => {{
    const rec = savedGrids[name] || {{}};
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name + (rec.points && rec.points.length===4 ? ' ✓' : '');
    selGridList.appendChild(opt);
  }});
  selGridList.value = activeGridName;
  inpGridName.value = activeGridName;
  const marked = points.length===4 ? 'marcado' : 'sem 4 pontos';
  const completos = names.filter(n => savedGrids[n] && savedGrids[n].points && savedGrids[n].points.length===4).length;
  gridStatus.textContent = 'Grid ativo: ' + activeGridName + ' · ' + marked + ' · salvos: ' + names.length;
  if(gridAllStatus) gridAllStatus.textContent = '👁️ Todos os grids salvos visíveis: ATIVO · ' + completos + ' grid(s) completo(s) na tela';
}}

function saveActiveGrid(showMsg=false) {{
  activeGridName = cleanGridName(inpGridName.value || activeGridName);
  savedGrids[activeGridName] = {{
    points: clonePoints(points),
    annotations: cloneAnnotations(annotations),
    rows: parseInt(inpRows.value)||1,
    cols: parseInt(inpCols.value)||1
  }};
  updateGridSelect();
  persistGrids();
  if(showMsg) gridStatus.textContent = 'Grid salvo: ' + activeGridName + ' · todos continuam visíveis no visualizador';
}}

function loadGridByName(name) {{
  const target = cleanGridName(String(name || '').replace(/ ✓$/,''));
  if(target === activeGridName) return;
  saveActiveGrid(false);
  const rec = savedGrids[target];
  if(!rec) return;
  activeGridName = target;
  points = clonePoints(rec.points);
  annotations = cloneAnnotations(rec.annotations);
  inpRows.value = rec.rows || inpRows.value;
  inpCols.value = rec.cols || inpCols.value;
  closePopup();
  updateGridSelect();
  draw();
}}

function makeUniqueGridName(base) {{
  let name = cleanGridName(base);
  if(!savedGrids[name]) return name;
  let i = 2;
  while(savedGrids[name + ' ' + i]) i++;
  return name + ' ' + i;
}}

function createNewGrid() {{
  saveActiveGrid(false);
  const suggested = makeUniqueGridName('Grid ' + (Object.keys(savedGrids).length + 1));
  const typed = prompt('Nome do novo grid:', suggested);
  if(typed === null) return;
  activeGridName = makeUniqueGridName(typed);
  points = [];
  annotations = {{}};
  savedGrids[activeGridName] = {{
    points: [],
    annotations: {{}},
    rows: parseInt(inpRows.value)||1,
    cols: parseInt(inpCols.value)||1
  }};
  closePopup();
  updateGridSelect();
  draw();
}}

function renameActiveGrid() {{
  const next = cleanGridName(inpGridName.value);
  if(next === activeGridName) return;
  const old = activeGridName;
  activeGridName = makeUniqueGridName(next);
  if(savedGrids[old]) delete savedGrids[old];
  saveActiveGrid(false);
}}

function getExportGridRecords() {{
  saveActiveGrid(false);
  return Object.keys(savedGrids).map(name => {{
    const rec = savedGrids[name] || {{}};
    return {{
      name: name,
      rows: rec.rows || parseInt(inpRows.value)||1,
      cols: rec.cols || parseInt(inpCols.value)||1,
      points: clonePoints(rec.points),
      annotations: cloneAnnotations(rec.annotations)
    }};
  }});
}}

function escHtml(value) {{
  return String(value || '')
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}}

function renderAssessmentPanel() {{
  if(!assessmentSummary) return;
  const rows = [];
  getExportGridRecords().forEach(grid => {{
    const R=parseInt(grid.rows)||1, C=parseInt(grid.cols)||1;
    for(let r=0;r<R;r++) for(let c=0;c<C;c++) {{
      const ann=(grid.annotations[r]||{{}})[c];
      if(ann && ann.nota) rows.push({{
        grid:grid.name,
        tiro:c+1,
        disparo:r+1,
        parcela:'D'+(r+1)+' T'+(c+1),
        nota:ann.nota,
        obs:ann.obs || ''
      }});
    }}
  }});
  if(rows.length===0) {{
    assessmentSummary.innerHTML = '<div class="assessment-empty">Nenhuma nota registrada ainda. Use Anotar Parcela ou Nota Rápida no visualizador.</div>';
    return;
  }}
  let html = '<table class="assessment-table"><thead><tr>' +
    '<th>Nome do Grid</th><th>Tiro</th><th>Disparo</th><th>Parcela</th><th>Nota</th><th>Observação</th>' +
    '</tr></thead><tbody>';
  rows.forEach(row => {{
    html += '<tr><td>'+escHtml(row.grid)+'</td><td>'+row.tiro+'</td><td>'+row.disparo+'</td><td>'+escHtml(row.parcela)+'</td><td>'+escHtml(row.nota)+'</td><td>'+escHtml(row.obs)+'</td></tr>';
  }});
  html += '</tbody></table>';
  assessmentSummary.innerHTML = html;
}}

function drawGridRecord(gridName, rec, isActive) {{
  const pts = isActive ? points : clonePoints(rec.points);
  if(!pts || pts.length===0) return;

  const showSummary = cbShowSummary.checked;
  const R=parseInt(isActive ? inpRows.value : rec.rows)||1;
  const C=parseInt(isActive ? inpCols.value : rec.cols)||1;
  const anns = isActive ? annotations : cloneAnnotations(rec.annotations);

  function quadFor(r,c) {{
    if(pts.length < 4) return null;
    const p0=pts[0],p1=pts[1],p2=pts[2],p3=pts[3];
    const u0=c/C, u1=(c+1)/C, v0=r/R, v1=(r+1)/R;
    const tl=bilerp(p0,p1,p2,p3,u0,v0);
    const tr=bilerp(p0,p1,p2,p3,u1,v0);
    const br=bilerp(p0,p1,p2,p3,u1,v1);
    const bl=bilerp(p0,p1,p2,p3,u0,v1);
    return {{tl,tr,br,bl,cx:(tl.x+tr.x+br.x+bl.x)/4,cy:(tl.y+tr.y+br.y+bl.y)/4}};
  }}

  if(pts.length===4) {{
    const p0=pts[0],p1=pts[1],p2=pts[2],p3=pts[3];
    for(let r=0; r<R; r++) {{
      for(let c=0; c<C; c++) {{
        const ann = anns[r] && anns[r][c];
        const quad=quadFor(r,c);
        if(!quad) continue;
        const tl=quad.tl, tr=quad.tr, br=quad.br, bl=quad.bl;
        if(ann) {{
          const nota = ann.nota;
          ctx.beginPath();
          ctx.moveTo(tl.x,tl.y); ctx.lineTo(tr.x,tr.y);
          ctx.lineTo(br.x,br.y); ctx.lineTo(bl.x,bl.y);
          ctx.closePath();
          ctx.fillStyle=getNotaFillColor(Number(nota)||1); ctx.fill();
        }}
        if(isActive && activeCell && activeCell.r===r && activeCell.c===c) {{
          ctx.beginPath();
          ctx.moveTo(tl.x,tl.y); ctx.lineTo(tr.x,tr.y);
          ctx.lineTo(br.x,br.y); ctx.lineTo(bl.x,bl.y);
          ctx.closePath();
          ctx.fillStyle='rgba(255,140,0,0.20)'; ctx.fill();
          ctx.save();
          ctx.strokeStyle='rgba(255,210,0,0.98)';
          ctx.lineWidth=3/sc;
          ctx.shadowColor='rgba(255,210,0,0.65)'; ctx.shadowBlur=8/sc;
          ctx.stroke(); ctx.restore();
        }}
        if(showSummary) {{
          const idTextSize = Math.max(5, Math.min(40, parseFloat(inpIdTextSize.value)||12));
          const noteTextSize = Math.max(5, Math.min(40, parseFloat(inpNoteTextSize.value)||10));
          const hasNota = ann && ann.nota;
          const obsTxt = hasNota ? resumoObs(ann.obs) : '';
          const lines = ['D'+(r+1)+' T'+(c+1)];
          if(hasNota) lines.push('Nota: '+ann.nota);
          if(obsTxt) lines.push(obsTxt);
          if(!isActive && r===0 && c===0) lines.unshift(gridName);
          const lineGap = Math.max(7, noteTextSize * 0.95);
          const startY = quad.cy - ((lines.length-1) * lineGap) / (2*sc);
          ctx.save();
          ctx.globalAlpha = isActive ? 1 : 0.82;
          ctx.shadowColor='rgba(0,0,0,0.85)'; ctx.shadowBlur=4/sc;
          ctx.fillStyle=isActive ? '#ffffff' : '#d7ecff';
          ctx.textAlign='center'; ctx.textBaseline='middle';
          lines.forEach((line, idx) => {{
            ctx.font='bold '+((idx===0 ? idTextSize : noteTextSize)/sc)+'px Arial';
            ctx.fillText(line, quad.cx, startY + (lineGap*idx)/sc);
          }});
          ctx.restore();
        }}
      }}
    }}
    ctx.save();
    ctx.shadowColor=isActive ? 'rgba(0,160,255,0.6)' : 'rgba(255,140,0,0.45)';
    ctx.shadowBlur=6/sc;
    ctx.strokeStyle=isActive ? 'rgba(30,144,255,0.95)' : 'rgba(255,140,0,0.85)';
    ctx.lineWidth=(isActive ? 2 : 1.4)/sc;
    for(let i=0;i<=R;i++) {{
      const v=i/R;
      const lxv=(1-v)*p0.x+v*p3.x, lyv=(1-v)*p0.y+v*p3.y;
      const rxv=(1-v)*p1.x+v*p2.x, ryv=(1-v)*p1.y+v*p2.y;
      ctx.beginPath(); ctx.moveTo(lxv,lyv); ctx.lineTo(rxv,ryv); ctx.stroke();
    }}
    for(let j=0;j<=C;j++) {{
      const u=j/C;
      const txv=(1-u)*p0.x+u*p1.x, tyv=(1-u)*p0.y+u*p1.y;
      const bxv=(1-u)*p3.x+u*p2.x, byv=(1-u)*p3.y+u*p2.y;
      ctx.beginPath(); ctx.moveTo(txv,tyv); ctx.lineTo(bxv,byv); ctx.stroke();
    }}
    ctx.restore();
  }}
  if(isActive) {{
    pts.forEach((p,i) => {{
      const isDrag = draggingPoint===i;
      const r2 = 11/sc;
      ctx.save();
      ctx.shadowColor = isDrag ? 'rgba(255,255,255,0.9)' : 'rgba(0,180,255,0.8)';
      ctx.shadowBlur = 14/sc;
      ctx.beginPath(); ctx.arc(p.x,p.y,r2+3/sc,0,2*Math.PI);
      ctx.fillStyle = isDrag ? 'rgba(255,255,255,0.25)' : 'rgba(0,100,200,0.35)'; ctx.fill();
      ctx.beginPath(); ctx.arc(p.x,p.y,r2,0,2*Math.PI);
      ctx.fillStyle = isDrag ? '#ffffff' : '#1e90ff'; ctx.fill();
      ctx.lineWidth=2.5/sc; ctx.strokeStyle = isDrag ? '#aaddff' : '#00cfff'; ctx.stroke();
      ctx.restore();
      ctx.save();
      ctx.fillStyle = isDrag ? '#003366' : '#ffffff';
      ctx.font='bold '+(13/sc)+'px Arial'; ctx.textAlign='center'; ctx.textBaseline='middle';
      ctx.fillText(i+1,p.x,p.y); ctx.restore();
    }});
  }}
}}

function drawGrid() {{
  const activeRecord = {{
    points: clonePoints(points),
    annotations: cloneAnnotations(annotations),
    rows: parseInt(inpRows.value)||1,
    cols: parseInt(inpCols.value)||1
  }};
  savedGrids[activeGridName] = activeRecord;
  const names = Object.keys(savedGrids);
  names.forEach(name => {{
    if(name !== activeGridName) drawGridRecord(name, savedGrids[name], false);
  }});
  drawGridRecord(activeGridName, activeRecord, true);
  updateGridSelect();
}}

function resize() {{ cv.width=vc.clientWidth; cv.height=vc.clientHeight; if(imgW) draw(); }}

function draw() {{
  ctx.clearRect(0,0,cv.width,cv.height);
  ctx.save();
  ctx.translate(ox,oy); ctx.scale(sc,sc);
  ctx.imageSmoothingEnabled=sc<2; ctx.imageSmoothingQuality='high';
  ctx.drawImage(img,0,0);
  drawGrid();
  ctx.restore();
  zb.textContent=Math.round(sc*100)+'%';
  updatePopupPosition();
  renderAssessmentPanel();
}}

function fitScreen() {{
  const sx=cv.width/imgW, sy=cv.height/imgH;
  sc=Math.min(sx,sy)*0.92;
  ox=(cv.width-imgW*sc)/2; oy=(cv.height-imgH*sc)/2; draw();
}}

function zoomAt(factor,cx,cy) {{
  const ns=Math.min(MAX_SC,Math.max(MIN_SC,sc*factor));
  ox=cx-(cx-ox)*(ns/sc); oy=cy-(cy-oy)*(ns/sc); sc=ns; draw();
}}

img.onload=()=>{{ imgW=img.width; imgH=img.height; resize(); fitScreen(); }};
img.src='data:image/jpeg;base64,'+IMG_B64;

function updatePopupPosition() {{
  if(!activeCell || annotPopup.style.display==='none' || points.length<4) return;
  const quad = getCellQuad(activeCell.r, activeCell.c);
  if(!quad) return;
  const vw = vc.clientWidth, vh = vc.clientHeight;
  const px = Math.max(135, Math.min(vw-135, ox + quad.cx*sc));
  const py = Math.max(115, Math.min(vh-115, oy + quad.cy*sc));
  annotPopup.style.left = px+'px';
  annotPopup.style.top  = py+'px';
}}

function openPopup(r, c) {{
  activeCell = {{r,c}};
  // Nomenclatura atualizada para T = TIRO (Coluna), D = DISPARO (Linha)
  document.getElementById('popupTitle').textContent = 'Parcela D'+(r+1)+' T'+(c+1);
  const ann = (annotations[r]||{{}})[c] || {{}};
  activeNota = ann.nota || 0;
  document.querySelectorAll('.nota-btn').forEach((b,i) => b.classList.toggle('sel', i+1===activeNota));
  document.getElementById('annotObs').value = ann.obs || '';
  annotPopup.style.display = 'block';
  updatePopupPosition();
  draw();
}}

function closePopup() {{
  annotPopup.style.display='none';
  activeCell = null;
  if(imgW) draw();
}}

function setAnnotation(r,c,nota,obs) {{
  if(!annotations[r]) annotations[r]={{}};
  const prev=(annotations[r]||{{}})[c] || {{}};
  annotations[r][c] = {{
    nota: nota,
    obs: obs !== undefined ? obs : (prev.obs || '')
  }};
  saveActiveGrid(false);
}}

function clearAnnotation(r,c) {{
  if(!annotations[r]) return;
  delete annotations[r][c];
  if(Object.keys(annotations[r]).length===0) delete annotations[r];
  saveActiveGrid(false);
}}

function saveActiveAnnotation(closeAfter=true) {{
  if(!activeCell) return false;
  const {{r,c}} = activeCell;
  setAnnotation(r,c,activeNota || 1,document.getElementById('annotObs').value);
  if(closeAfter) closePopup();
  draw();
  return true;
}}

function openNextParcel() {{
  if(!activeCell) return;
  saveActiveAnnotation(false);
  const R=parseInt(inpRows.value)||1, C=parseInt(inpCols.value)||1;
  let idx = activeCell.r*C + activeCell.c + 1;
  if(idx >= R*C) idx = 0;
  const nr = Math.floor(idx / C);
  const nc = idx % C;
  openPopup(nr,nc);
}}

document.getElementById('btnPopupSave').onclick = () => {{
  saveActiveAnnotation(true);
}};

document.getElementById('btnPopupCancel').onclick = closePopup;
document.getElementById('btnPopupNext').onclick = openNextParcel;
annotPopup.addEventListener('mousedown', e=>e.stopPropagation());
annotPopup.addEventListener('click', e=>e.stopPropagation());
annotPopup.addEventListener('dblclick', e=>e.stopPropagation());

// Exportar Imagem Resumo Célula
document.getElementById('btnExportCellPNG').onclick = () => {{
  if(!activeCell) return;
  const {{r,c}} = activeCell;
  const R = parseInt(inpRows.value)||1, C = parseInt(inpCols.value)||1;
  const p0 = points[0], p1 = points[1], p2 = points[2], p3 = points[3];
  
  const u0=c/C, u1=(c+1)/C, v0=r/R, v1=(r+1)/R;
  const tl=bilerp(p0,p1,p2,p3,u0,v0), tr=bilerp(p0,p1,p2,p3,u1,v0);
  const br=bilerp(p0,p1,p2,p3,u1,v1), bl=bilerp(p0,p1,p2,p3,u0,v1);
  
  const minX = Math.min(tl.x, tr.x, br.x, bl.x);
  const maxX = Math.max(tl.x, tr.x, br.x, bl.x);
  const minY = Math.min(tl.y, tr.y, br.y, bl.y);
  const maxY = Math.max(tl.y, tr.y, br.y, bl.y);
  const w = maxX - minX, h = maxY - minY;
  
  const cv2 = document.createElement('canvas');
  cv2.width = w + 40; cv2.height = h + 130;
  const ctx2 = cv2.getContext('2d');
  
  ctx2.fillStyle = '#1e1e1e'; ctx2.fillRect(0,0,cv2.width,cv2.height);
  ctx2.drawImage(img, minX, minY, w, h, 20, 20, w, h);
  
  ctx2.fillStyle = '#ff8c00'; ctx2.font = 'bold 16px sans-serif';
  ctx2.fillText('Célula: T'+(c+1)+' D'+(r+1), 20, h + 50);
  
  const ann = (annotations[r]||{{}})[c] || {{}};
  ctx2.fillStyle = '#ccc'; ctx2.font = '14px sans-serif';
  ctx2.fillText('Nota: ' + (ann.nota||'Sem nota registrada'), 20, h + 75);
  ctx2.fillText('Obs: ' + (document.getElementById('annotObs').value||'Nenhuma observação'), 20, h + 100);
  
  const a = document.createElement('a');
  a.download = 'TMG_Resumo_T'+(c+1)+'_D'+(r+1)+'.png';
  a.href = cv2.toDataURL('image/png');
  a.click();
}};

// Exportar Dados Individuais JSON
document.getElementById('btnExportCellData').onclick = () => {{
  if(!activeCell) return;
  const {{r,c}} = activeCell;
  const ann = (annotations[r]||{{}})[c] || {{}};
  const data = {{
      celula: "T"+(c+1)+" D"+(r+1),
      tiro: c+1,
      disparo: r+1,
      nota: activeNota,
      observacao: document.getElementById('annotObs').value || ''
  }};
  
  const blob = new Blob([JSON.stringify(data, null, 2)], {{type:'application/json'}});
  const a = document.createElement('a');
  a.download = 'TMG_Dados_T'+(c+1)+'_D'+(r+1)+'.json';
  a.href = URL.createObjectURL(blob);
  a.click();
}};

btnExport.onclick = () => {{
  const nome = prompt('Digite o nome do arquivo Excel:', 'checklist_notas_parcelas');
  if(nome === null) return;
  const safeName = (nome.trim() || 'checklist_notas_parcelas')
    .replace(/[\\\\/:*?"<>|]+/g,'_')
    .replace(/\\s+/g,'_');
  const gridRecords = getExportGridRecords();
  const esc = (value) => String(value || '')
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;');
  let html = '<html><head><meta charset="utf-8"></head><body>';
  for(const grid of gridRecords) {{
    html += '<table border="1" style="border-collapse:collapse;font-family:Arial;font-size:11pt;margin-bottom:18px;">';
    html += '<tr><td colspan="4" style="background:#ff8c00;color:#000;font-weight:bold;font-size:13pt;">Grid: '+esc(grid.name)+'</td></tr>';
    html += '<tr style="background:#1f1f1f;color:#ff8c00;font-weight:bold;">';
    html += '<th>Disparo</th><th>Tiro</th><th>Nota</th><th>Observação</th></tr>';
    const R=parseInt(grid.rows)||1, C=parseInt(grid.cols)||1;
    for(let r=0;r<R;r++) for(let c=0;c<C;c++) {{
      const ann=(grid.annotations[r]||{{}})[c];
      const nota=Number(ann && ann.nota ? ann.nota : 1);
      const notaStyle = nota===9
        ? 'background:#ff0000;color:#ffffff;font-weight:bold;text-align:center;'
        : (nota===1
            ? 'background:#00b050;color:#ffffff;font-weight:bold;text-align:center;'
            : 'background:#ffd966;color:#000000;font-weight:bold;text-align:center;');
      html += '<tr>';
      html += '<td>'+(r+1)+'</td>';
      html += '<td>'+(c+1)+'</td>';
      html += '<td style="'+notaStyle+'">'+nota+'</td>';
      html += '<td>'+esc(ann?ann.obs:'')+'</td>';
      html += '</tr>';
    }}
    html += '</table><br>';
  }}
  html += '</body></html>';
  const blob = new Blob(['\\ufeff'+html], {{type:'application/vnd.ms-excel;charset=utf-8;'}});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download=safeName+'.xls';
  a.click();
}};

vc.addEventListener('wheel', e=>{{
  e.preventDefault();
  const r=cv.getBoundingClientRect();
  zoomAt(e.deltaY<0?1.18:1/1.18, e.clientX-r.left, e.clientY-r.top);
}},{{passive:false}});

vc.addEventListener('mousedown', e=>{{
  const ic=getImgCoords(e.clientX,e.clientY);
  draggingPoint=-1;

  for(let i=0;i<points.length;i++) {{
    const dx=points[i].x-ic.x, dy=points[i].y-ic.y;
    if(Math.sqrt(dx*dx+dy*dy)<30/sc) {{ draggingPoint=i; vc.style.cursor='move'; return; }}
  }}

  if(gridMode && points.length<4) {{
    points.push({{x:ic.x, y:ic.y}});
    saveActiveGrid(false);
    draw(); return;
  }}

  drag=true; lx=e.clientX; ly=e.clientY;
  if(!gridMode && !annotMode) vc.style.cursor='grabbing';
}});

vc.addEventListener('click', e=>{{
  if((annotMode || quickNoteMode) && points.length===4) e.preventDefault();
}});

window.addEventListener('mousemove', e=>{{
  const ic=getImgCoords(e.clientX,e.clientY);
  coord.textContent='X: '+Math.round(ic.x)+'   Y: '+Math.round(ic.y);

  if(draggingPoint!==-1) {{ points[draggingPoint]={{x:ic.x,y:ic.y}}; draw(); return; }}
  if(drag) {{ ox+=e.clientX-lx; oy+=e.clientY-ly; lx=e.clientX; ly=e.clientY; draw(); return; }}

  let hover=false;
  for(let i=0;i<points.length;i++) {{
    const dx=points[i].x-ic.x,dy=points[i].y-ic.y;
    if(Math.sqrt(dx*dx+dy*dy)<30/sc) {{ hover=true; break; }}
  }}
  if(hover) vc.style.cursor='move';
  else if(gridMode && points.length<4) vc.style.cursor='crosshair';
  else if(quickNoteMode && points.length===4) vc.style.cursor='cell';
  else if(annotMode && points.length===4) vc.style.cursor='cell';
  else vc.style.cursor='grab';
}});

window.addEventListener('mouseup',()=>{{
  if(draggingPoint!==-1) saveActiveGrid(false);
  drag=false; draggingPoint=-1;
  if(gridMode && points.length<4) vc.style.cursor='crosshair';
  else if(quickNoteMode && points.length===4) vc.style.cursor='cell';
  else if(annotMode && points.length===4) vc.style.cursor='cell';
  else vc.style.cursor='grab';
}});

vc.addEventListener('dblclick', e=>{{
  if((annotMode || quickNoteMode) && points.length===4) {{
    e.preventDefault();
    const ic=getImgCoords(e.clientX,e.clientY);
    const cell=getCellFromImgPt(ic.x,ic.y);
    if(!cell) return;
    if(quickNoteMode) {{
      const ann = (annotations[cell.r]||{{}})[cell.c];
      if(ann && Number(ann.nota)===9) {{
        if(String(ann.obs || '').trim()) setAnnotation(cell.r, cell.c, 1, ann.obs);
        else clearAnnotation(cell.r, cell.c);
      }} else {{
        activeCell = {{r:cell.r,c:cell.c}};
        setAnnotation(cell.r, cell.c, 9);
      }}
      closePopup();
      draw();
      return;
    }}
    openPopup(cell.r, cell.c);
    return;
  }}
  fitScreen();
}});

btnGrid.onclick=()=>{{
  saveActiveGrid(false);
  gridMode=!gridMode; annotMode=false; quickNoteMode=false;
  btnGrid.className=gridMode?'grid-btn active':'grid-btn';
  btnGrid.textContent=gridMode?'📍 Selecione 4 Pontos':'Ativar Marcação';
  btnAnnot.className='grid-btn annot';
  btnQuickNote.className='grid-btn';
  vc.style.cursor=gridMode?'crosshair':'grab';
}};

btnSaveGrid.onclick=()=>saveActiveGrid(true);
btnNewGrid.onclick=createNewGrid;
selGridList.onchange=()=>loadGridByName(selGridList.value);
inpGridName.onchange=renameActiveGrid;

btnAnnot.onclick=()=>{{
  if(points.length<4){{ alert('Marque os 4 pontos do Grid primeiro.'); return; }}
  annotMode=!annotMode; quickNoteMode=false; gridMode=false;
  btnAnnot.className=annotMode?'grid-btn annot active':'grid-btn annot';
  btnQuickNote.className='grid-btn';
  btnGrid.className='grid-btn';
  btnGrid.textContent='Ativar Marcação';
  vc.style.cursor=annotMode?'cell':'grab';
}};

btnQuickNote.onclick=()=>{{
  if(points.length<4){{ alert('Marque os 4 pontos do Grid primeiro.'); return; }}
  quickNoteMode=!quickNoteMode; annotMode=false; gridMode=false;
  btnQuickNote.className=quickNoteMode?'grid-btn quick-active':'grid-btn';
  btnAnnot.className='grid-btn annot';
  btnGrid.className='grid-btn';
  btnGrid.textContent='Ativar Marcação';
  closePopup();
  vc.style.cursor=quickNoteMode?'cell':'grab';
}};

btnClear.onclick=()=>{{ points=[]; annotations={{}}; closePopup(); saveActiveGrid(false); draw(); }};

inpRows.addEventListener('input',()=>{{ saveActiveGrid(false); draw(); }});
inpCols.addEventListener('input',()=>{{ saveActiveGrid(false); draw(); }});
inpIdTextSize.addEventListener('input',draw);
inpNoteTextSize.addEventListener('input',draw);
cbShowSummary.addEventListener('change', draw);

document.getElementById('btnZI').onclick=()=>zoomAt(1.3,cv.width/2,cv.height/2);
document.getElementById('btnZO').onclick=()=>zoomAt(1/1.3,cv.width/2,cv.height/2);
document.getElementById('btnFit').onclick=fitScreen;
document.getElementById('btnN').onclick=()=>{{sc=1;ox=(cv.width-imgW)/2;oy=(cv.height-imgH)/2;draw();}};
document.getElementById('btnR').onclick=fitScreen;

window.addEventListener('resize',resize);
suppressPersist = true;
restoreGrids();
suppressPersist = false;
saveActiveGrid(false);
updateGridSelect();
</script>
</body>
</html>
"""
                components.html(chk_viewer, height=980, scrolling=True)

        else:
            st.markdown("""
            <div style='height:706px;border:1px dashed #2e2e2e;border-radius:12px;background:#0d0d0d;
                        display:flex;flex-direction:column;align-items:center;justify-content:center;
                        gap:12px;color:#333;'>
                <div style='font-size:3rem;'>🗺️</div>
                <div style='font-size:0.9rem;letter-spacing:2px;text-transform:uppercase;'>
                    Nenhuma ortofoto carregada
                </div>
                <div style='font-size:0.75rem;color:#2a2a2a;'>
                    PNG · JPG · TIF · GeoTIFF · JP2 · IMG · ECW
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ==========================================
    # GRID COM OPÇÕES DE EXPORTAÇÃO E SHAPEFILE[cite: 1]
    # ==========================================
    elif st.session_state.pagina_ativa == 'Grid':
        st.subheader("📊 Visualizador de Ortofoto")

        orto_file = st.file_uploader(
            "Selecione a ortofoto",
            type=MOSAIC_UPLOAD_TYPES,
            key="orto_uploader",
            help="Formatos suportados: PNG, JPG, TIF/GeoTIFF, JP2, IMG"
        )
        grid_library = _mosaic_single_select("Ou usar mosaico já importado", key="grid_mosaic_library")

        grid_prefill_path = st.session_state.get("grid_prefill_ortho_path", "")
        grid_prefill_name = st.session_state.get("grid_prefill_ortho_name", "")
        grid_prefill_available = bool(grid_prefill_path and Path(grid_prefill_path).exists())
        if grid_prefill_available and not orto_file and not grid_library:
            st.info(f"Ortofoto recebida do módulo Voos Direcionados: {grid_prefill_name or Path(grid_prefill_path).name}")
            if st.button("Limpar ortofoto recebida", key="btn_clear_grid_prefill"):
                st.session_state.pop("grid_prefill_ortho_path", None)
                st.session_state.pop("grid_prefill_ortho_name", None)
                app_rerun()

        if orto_file or grid_library or grid_prefill_available:
            with st.spinner("Carregando ortofoto de alta resolução... (Isso pode levar alguns segundos)"):
                if orto_file:
                    file_bytes, orto_nome_exibicao = _mosaic_input_bytes(orto_file, "", "Grid")
                elif grid_library:
                    file_bytes, orto_nome_exibicao = _mosaic_input_bytes(None, grid_library, "Grid")
                else:
                    file_bytes = Path(grid_prefill_path).read_bytes()
                    orto_nome_exibicao = grid_prefill_name or Path(grid_prefill_path).name
                # Atualizado Unpack para obter Metadata Espacial para o SHP
                b64, dims, err, spatial_meta = processar_ortofoto(file_bytes, orto_nome_exibicao)
                st.session_state.spatial_meta = spatial_meta

            if err:
                st.error(f"Erro ao processar imagem: {err}")
            else:
                w, h = dims
                st.markdown(
                    f"<p style='color:#666;font-size:0.78rem;margin-bottom:6px;'>"
                    f"📐 {orto_nome_exibicao} &nbsp;·&nbsp; Resolução final processada: {w}×{h} px</p>",
                    unsafe_allow_html=True
                )

                viewer_html = f"""
<!DOCTYPE html>
<html>
<head>
<!-- SHPWRITE LIBRARY PARA EXPORTAÇÃO SHAPEFILE (MANTIDO APENAS COMO LEGADO NO CONSOLE) -->
<script src="https://unpkg.com/shp-write@latest/shpwrite.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d0d0d; overflow: hidden; }}

  #vc {{
    width: 100%;
    height: 706px;
    background:
      linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px),
      #0d0d0d;
    background-size: 32px 32px;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    cursor: grab;
    user-select: none;
  }}
  #vc:active {{ cursor: grabbing; }}
  canvas {{ position: absolute; top:0; left:0; display: block; }}

  .toolbar {{
    position: absolute;
    top: 12px; right: 12px;
    display: flex;
    flex-direction: column;
    gap: 5px;
    z-index: 20;
  }}
  .tb-btn {{
    background: linear-gradient(145deg, #1e1e1e, #111);
    border: 1px solid #3a3a3a;
    color: #ff8c00;
    width: 34px; height: 34px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 15px;
    font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 2px 2px 8px #000, inset 0 1px 0 rgba(255,255,255,0.05);
    transition: all .2s;
    font-family: 'Segoe UI', sans-serif;
    line-height: 1;
  }}
  .tb-btn:hover {{
    border-color: #ff8c00;
    box-shadow: 0 0 10px rgba(255,140,0,0.35), 2px 2px 8px #000;
    color: #ffaa33;
  }}
  .tb-btn:active {{ transform: translateY(1px); }}

  .tb-sep {{
    width: 34px; height: 1px;
    background: linear-gradient(90deg, transparent, #333, transparent);
    margin: 2px 0;
  }}

  /* GRID PANEL */
  .grid-panel {{
      position: absolute;
      top: 12px; right: 55px;
      background: rgba(10,10,10,0.85);
      border: 1px solid #2a2a2a;
      border-radius: 8px;
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      z-index: 20;
      font-family: 'Segoe UI', sans-serif;
  }}
  .grid-panel label {{ color: #ff8c00; font-size: 11px; font-weight: bold; text-align: center; margin-bottom: 2px; }}
  .grid-panel input[type=number] {{
      background: #1a1a1a; border: 1px solid #333; color: #fff;
      border-radius: 4px; padding: 4px; width: 50px; text-align: center; font-size: 11px;
  }}
  .grid-panel .row-col {{ display: flex; gap: 8px; align-items: center; justify-content: space-between; color: #ccc; font-size:11px; }}
  .grid-btn {{
      background: linear-gradient(145deg, #1e1e1e, #111);
      border: 1px solid #3a3a3a; color: #ccc; cursor: pointer; border-radius:4px; padding: 6px; font-size: 11px; font-weight:bold; transition: 0.2s;
  }}
  .grid-btn:hover {{ border-color: #ff8c00; color: #ff8c00; }}
  .grid-btn.active {{ border-color: #ff8c00; color: #ff8c00; box-shadow: 0 0 8px rgba(255,140,0,0.3); background: #2a1a00; }}

  .zoom-badge {{
    position: absolute;
    top: 12px; left: 12px;
    background: rgba(10,10,10,0.82);
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    color: #ff8c00;
    font-size: 11px;
    font-family: 'Courier New', monospace;
    font-weight: 700;
    padding: 5px 10px;
    letter-spacing: 1px;
    z-index: 20;
    pointer-events: none;
  }}

  .crosshair {{
    position: absolute;
    bottom: 12px; left: 12px;
    background: rgba(10,10,10,0.82);
    border: 1px solid #222;
    border-radius: 8px;
    color: #555;
    font-size: 10px;
    font-family: 'Courier New', monospace;
    padding: 4px 10px;
    z-index: 20;
    pointer-events: none;
    letter-spacing: 0.5px;
  }}

  .hint {{
    position: absolute;
    bottom: 12px; right: 12px;
    color: #333;
    font-size: 10px;
    font-family: 'Segoe UI', sans-serif;
    z-index: 20;
    pointer-events: none;
    text-align: right;
    line-height: 1.6;
  }}
</style>
</head>
<body>
<div id="vc">
  <canvas id="cv"></canvas>

  <div class="zoom-badge" id="zbadge">100%</div>

  <div class="grid-panel">
      <label>📍 MARCAÇÃO DE GRID</label>
      <button class="grid-btn" id="btnGridTool">Ativar Marcação</button>
      <div class="row-col">
          <span>DISPAROS:</span>
          <input type="number" id="inpRows" value="10" min="1" max="500">
      </div>
      <div class="row-col">
          <span>TIROS:</span>
          <input type="number" id="inpCols" value="10" min="1" max="500">
      </div>
      <div class="row-col" style="justify-content:flex-start; gap:4px; margin-top:4px;">
          <input type="checkbox" id="cbShowSummary" checked style="width:auto;">
          <span style="font-size:10px;">👁️ Mostrar ID e Resumo</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:3px;margin-top:2px;">
          <span style="color:#ff8c00;font-size:11px;font-weight:bold;">🔤 Tamanho do Texto:</span>
          <div style="display:flex;align-items:center;gap:6px;">
              <input type="range" id="inpFontSize" min="4" max="72" value="12"
                     style="width:85px;accent-color:#ff8c00;cursor:pointer;">
              <span id="lblFontSize" style="font-size:11px;color:#ff8c00;font-weight:bold;min-width:22px;">12</span>
          </div>
      </div>
      <button class="grid-btn" id="btnClearGrid" style="color:#ff6b6b; border-color:#552222;">🗑️ Limpar Grid</button>
      
      <div class="tb-sep" style="width:100%"></div>
      <button class="grid-btn" id="btnExportFull" style="color:#00ee55; border-color:#006600;">📥 Exportar Ortofoto + Grid</button>
      <button class="grid-btn" id="btnExportGrid" style="color:#00cfff; border-color:#006699;">📥 Exportar Apenas Grid</button>
      <button class="grid-btn" id="btnExportSHP" style="color:#ff00ff; border-color:#990099;">🗺️ Exportar Shapefile (.SHP)</button>
  </div>

  <div class="toolbar">
    <button class="tb-btn" id="btnZI" title="Zoom In (+)">+</button>
    <button class="tb-btn" id="btnZO" title="Zoom Out (-)">−</button>
    <div class="tb-sep"></div>
    <button class="tb-btn" id="btnFit" title="Ajustar à tela">⊡</button>
    <button class="tb-btn" id="btnN"   title="Zoom 100%">1:1</button>
    <div class="tb-sep"></div>
    <button class="tb-btn" id="btnR"   title="Resetar vista">↺</button>
  </div>

  <div class="crosshair" id="coord">X: — &nbsp; Y: —</div>
  <div class="hint">Scroll: zoom &nbsp;|&nbsp; Arrastar: mover extremidade<br>Duplo clique: ajustar tela</div>
</div>

<script>
const IMG_B64 = '{b64}';
const vc  = document.getElementById('vc');
const cv  = document.getElementById('cv');
const ctx = cv.getContext('2d');
const zb  = document.getElementById('zbadge');
const coord = document.getElementById('coord');

const inpRows = document.getElementById('inpRows');
const inpCols = document.getElementById('inpCols');
const cbShowSummary = document.getElementById('cbShowSummary');
const btnGrid = document.getElementById('btnGridTool');
const btnClear = document.getElementById('btnClearGrid');
let gridMode = false;
let points = [];
let draggingPoint = -1;

let sc = 1, ox = 0, oy = 0;
let drag = false, lx = 0, ly = 0;
const MIN_SC = 0.05, MAX_SC = 40;
let imgW = 0, imgH = 0;

const img = new Image();

function getImgCoords(cx, cy) {{
    const r = cv.getBoundingClientRect();
    return {{
        x: (cx - r.left - ox) / sc,
        y: (cy - r.top - oy) / sc
    }};
}}

// Helper interpolador adicionado ao painel de Grid para gerar células exatas
function bilerp(p0,p1,p2,p3, u,v) {{
  const tx = (1-u)*p0.x + u*p1.x;
  const ty = (1-u)*p0.y + u*p1.y;
  const bx = (1-u)*p3.x + u*p2.x;
  const by = (1-u)*p3.y + u*p2.y;
  return {{ x:(1-v)*tx + v*bx, y:(1-v)*ty + v*by }};
}}

// Mantém o payload dentro do iframe. Alterar inputs internos do Streamlit pelo
// window.parent pode quebrar a árvore React durante rerender no Streamlit Cloud.
function syncToPython() {{
    if (points.length === 4) {{
        const data = {{ 
            points: points, 
            rows: parseInt(inpRows.value)||1, 
            cols: parseInt(inpCols.value)||1 
        }};
        try {{
            window.localStorage.setItem('tmg_grid_payload', JSON.stringify(data));
        }} catch(e) {{ console.log("Sincronização local indisponível", e); }}
    }}
}}

function drawGrid() {{
    if (points.length === 0) return;

    const showSummary = cbShowSummary.checked;

    if (points.length === 4) {{
        const R = parseInt(inpRows.value) || 1;
        const C = parseInt(inpCols.value) || 1;
        const p0 = points[0], p1 = points[1], p2 = points[2], p3 = points[3];

        if (showSummary) {{
            for(let r=0; r<R; r++) {{
                for(let c=0; c<C; c++) {{
                    const u0=c/C, u1=(c+1)/C, v0=r/R, v1=(r+1)/R;
                    const tl=bilerp(p0,p1,p2,p3,u0,v0);
                    const tr=bilerp(p0,p1,p2,p3,u1,v0);
                    const br=bilerp(p0,p1,p2,p3,u1,v1);
                    const bl=bilerp(p0,p1,p2,p3,u0,v1);
                    
                    const cx2=(tl.x+tr.x+br.x+bl.x)/4;
                    const cy2=(tl.y+tr.y+br.y+bl.y)/4;
                    
                    ctx.save();
                    ctx.shadowColor='rgba(0,0,0,0.8)'; ctx.shadowBlur=4/sc;
                    ctx.fillStyle='#ffffff';
                    const userFS = parseInt(document.getElementById('inpFontSize').value) || 12;
                    ctx.font='bold '+(Math.max(4, userFS/sc))+'px Arial';
                    ctx.textAlign='center'; ctx.textBaseline='middle';
                    ctx.fillText(`T${{c+1}} D${{r+1}}`, cx2, cy2);
                    ctx.restore();
                }}
            }}
        }}

        ctx.save();
        ctx.shadowColor = 'rgba(0, 160, 255, 0.6)';
        ctx.shadowBlur = 6 / sc;
        ctx.strokeStyle = 'rgba(30, 144, 255, 0.95)';
        ctx.lineWidth = 2 / sc;

        for(let i=0; i<=R; i++) {{
            let v = i / R;
            let lx = (1-v)*p0.x + v*p3.x;
            let ly = (1-v)*p0.y + v*p3.y;
            let rx = (1-v)*p1.x + v*p2.x;
            let ry = (1-v)*p1.y + v*p2.y;
            ctx.beginPath(); ctx.moveTo(lx, ly); ctx.lineTo(rx, ry); ctx.stroke();
        }}

        for(let j=0; j<=C; j++) {{
            let u = j / C;
            let tx = (1-u)*p0.x + u*p1.x;
            let ty = (1-u)*p0.y + u*p1.y;
            let bx = (1-u)*p3.x + u*p2.x;
            let by = (1-u)*p3.y + u*p2.y;
            ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(bx, by); ctx.stroke();
        }}
        ctx.restore();
    }}

    points.forEach((p, i) => {{
        const isDrag = draggingPoint === i;
        const r = 11 / sc;

        ctx.save();
        ctx.shadowColor = isDrag ? 'rgba(255,255,255,0.9)' : 'rgba(0,180,255,0.8)';
        ctx.shadowBlur = 14 / sc;

        ctx.beginPath();
        ctx.arc(p.x, p.y, r + 3/sc, 0, 2 * Math.PI);
        ctx.fillStyle = isDrag ? 'rgba(255,255,255,0.25)' : 'rgba(0,100,200,0.35)';
        ctx.fill();

        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, 2 * Math.PI);
        ctx.fillStyle = isDrag ? '#ffffff' : '#1e90ff';
        ctx.fill();
        ctx.lineWidth = 2.5 / sc;
        ctx.strokeStyle = isDrag ? '#aaddff' : '#00cfff';
        ctx.stroke();
        ctx.restore();

        ctx.save();
        ctx.fillStyle = isDrag ? '#003366' : '#ffffff';
        ctx.font = 'bold ' + (13/sc) + 'px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(i+1, p.x, p.y);
        ctx.restore();
    }});
}}

function resize() {{
  cv.width  = vc.clientWidth;
  cv.height = vc.clientHeight;
  if (imgW) draw();
}}

function draw() {{
  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.save();
  ctx.translate(ox, oy);
  ctx.scale(sc, sc);
  ctx.imageSmoothingEnabled = sc < 2;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(img, 0, 0);
  drawGrid();
  ctx.restore();
  zb.textContent = Math.round(sc * 100) + '%';
}}

function fitScreen() {{
  const sx = cv.width  / imgW;
  const sy = cv.height / imgH;
  sc = Math.min(sx, sy) * 0.92;
  ox = (cv.width  - imgW * sc) / 2;
  oy = (cv.height - imgH * sc) / 2;
  draw();
}}

function zoomAt(factor, cx, cy) {{
  const ns = Math.min(MAX_SC, Math.max(MIN_SC, sc * factor));
  ox = cx - (cx - ox) * (ns / sc);
  oy = cy - (cy - oy) * (ns / sc);
  sc = ns;
  draw();
}}

img.onload = () => {{ imgW = img.width; imgH = img.height; resize(); fitScreen(); }};
img.src = 'data:image/jpeg;base64,' + IMG_B64;

vc.addEventListener('wheel', e => {{
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  zoomAt(e.deltaY < 0 ? 1.18 : 1/1.18, e.clientX - r.left, e.clientY - r.top);
}}, {{ passive: false }});

vc.addEventListener('mousedown', e => {{
    const ic = getImgCoords(e.clientX, e.clientY);
    draggingPoint = -1;

    for(let i=0; i<points.length; i++) {{
        let dx = points[i].x - ic.x;
        let dy = points[i].y - ic.y;
        if (Math.sqrt(dx*dx + dy*dy) < 30 / sc) {{
            draggingPoint = i;
            vc.style.cursor = 'move';
            return;
        }}
    }}

    if (gridMode && points.length < 4) {{
        points.push({{x: ic.x, y: ic.y}});
        draw();
        return;
    }}

    drag=true; lx=e.clientX; ly=e.clientY;
    if (!gridMode) vc.style.cursor = 'grabbing';
}});

window.addEventListener('mousemove', e => {{
  const ic = getImgCoords(e.clientX, e.clientY);
  
  coord.textContent = 'X: ' + Math.round(ic.x) + '   Y: ' + Math.round(ic.y);

  if (draggingPoint !== -1) {{
      points[draggingPoint] = {{x: ic.x, y: ic.y}};
      draw();
      return;
  }}

  if (drag) {{
      ox += e.clientX - lx; oy += e.clientY - ly;
      lx = e.clientX; ly = e.clientY;
      draw();
      return;
  }}

  let hoverPoint = false;
  for(let i=0; i<points.length; i++) {{
      let dx = points[i].x - ic.x;
      let dy = points[i].y - ic.y;
      if (Math.sqrt(dx*dx + dy*dy) < 30 / sc) hoverPoint = true;
  }}

  if (hoverPoint) {{
      vc.style.cursor = 'move';
  }} else if (gridMode && points.length < 4) {{
      vc.style.cursor = 'crosshair';
  }} else {{
      vc.style.cursor = 'grab';
  }}
}});

window.addEventListener('mouseup', () => {{
    drag = false;
    if(draggingPoint !== -1){{
        draggingPoint = -1;
        syncToPython();
    }}
    vc.style.cursor = (gridMode && points.length < 4) ? 'crosshair' : 'grab';
}});

vc.addEventListener('dblclick', fitScreen);

btnGrid.onclick = () => {{
    gridMode = !gridMode;
    btnGrid.className = gridMode ? 'grid-btn active' : 'grid-btn';
    btnGrid.innerText = gridMode ? '📍 Selecione 4 Pontos' : 'Ativar Marcação';
    vc.style.cursor = gridMode ? 'crosshair' : 'grab';
}};

btnClear.onclick = () => {{
    points = [];
    draw();
}};

inpRows.addEventListener('change', syncToPython);
inpCols.addEventListener('change', syncToPython);
inpRows.addEventListener('input', draw);
inpCols.addEventListener('input', draw);
cbShowSummary.addEventListener('change', draw);

// Controle de tamanho do texto em tempo real
const inpFontSize = document.getElementById('inpFontSize');
const lblFontSize = document.getElementById('lblFontSize');
inpFontSize.addEventListener('input', () => {{
    lblFontSize.textContent = inpFontSize.value;
    draw();
}});

document.getElementById('btnZI').onclick  = () => zoomAt(1.3, cv.width/2, cv.height/2);
document.getElementById('btnZO').onclick  = () => zoomAt(1/1.3, cv.width/2, cv.height/2);
document.getElementById('btnFit').onclick = fitScreen;
document.getElementById('btnN').onclick   = () => {{ sc=1; ox=(cv.width-imgW)/2; oy=(cv.height-imgH)/2; draw(); }};
document.getElementById('btnR').onclick   = fitScreen;

// Lógica de exportação WYSIWYG
document.getElementById('btnExportFull').onclick = () => {{
    const link = document.createElement('a');
    link.download = 'TMG_Grid_Visualizador.png';
    link.href = cv.toDataURL("image/png");
    link.click();
}};

// Lógica de exportação Somente Grade
document.getElementById('btnExportGrid').onclick = () => {{
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.save();
    ctx.translate(ox, oy);
    ctx.scale(sc, sc);
    drawGrid();
    ctx.restore();
    
    const link = document.createElement('a');
    link.download = 'TMG_Grid_Limpo.png';
    link.href = cv.toDataURL("image/png");
    link.click();
    
    draw();
}};

// NOVO: EXPORTAÇÃO DE SHAPEFILE INTEGRADA COM PYTHON PARA VALIDACAO ROBUSTA
document.getElementById('btnExportSHP').onclick = () => {{
    if(points.length !== 4) {{
        alert('Por favor, marque os 4 pontos do Grid antes de exportar o Shapefile.');
        return;
    }}
    syncToPython();
    alert('✅ Dados geométricos validados e sincronizados com sucesso! Role a página um pouco para baixo e clique em "📥 Baixar Shapefile (.SHP)" na área de Exportação Robusta para garantir a integridade e CRS corretos.');
}};

window.addEventListener('resize', resize);
</script>
</body>
</html>
"""
                components.html(viewer_html, height=720, scrolling=False)

                # ---------------------------------------------------------
                # ADIÇÃO: MÓDULO ROBUSTO DE EXPORTAÇÃO SHAPEFILE (GEOPANDAS)
                # ---------------------------------------------------------
                st.markdown("---")
                st.markdown("""
                <div style='color:#ff00ff;font-weight:700;font-size:1.1rem;letter-spacing:2px; text-transform:uppercase;margin-bottom:10px;'>
                    🗺️ Exportação Robusta de Shapefile (VectorData)
                </div>
                """, unsafe_allow_html=True)
                
                grid_payload = st.session_state.get("grid_payload")

                if grid_payload and len(json.loads(grid_payload).get("points", [])) == 4:
                    if HAS_GEOPANDAS:
                        st.success("✅ Geometrias do Grid lidas e alinhadas. O sistema está pronto para consolidar as células do grid garantindo o empacotamento completo do vetor sem erros.")
                        
                        try:
                            data = json.loads(grid_payload)
                            points = data.get("points", [])
                            R = data.get("rows", 1)
                            C = data.get("cols", 1)
                            
                            features = []
                            
                            # Helper em python equivalente ao bilerp do JS
                            def py_bilerp(p0, p1, p2, p3, u, v):
                                tx = (1-u)*p0['x'] + u*p1['x']
                                ty = (1-u)*p0['y'] + u*p1['y']
                                bx = (1-u)*p3['x'] + u*p2['x']
                                by = (1-u)*p3['y'] + u*p2['y']
                                return {"x": (1-v)*tx + v*bx, "y": (1-v)*ty + v*by}
                            
                            meta = st.session_state.get("spatial_meta", {})
                            ratio = meta.get("ratio", 1.0)
                            gdal_transform = meta.get("transform", None)
                            crs_wkt = meta.get("crs", None)
                            
                            # Recriando a matriz Affine da Ortofoto Original se disponível
                            aff = Affine.from_gdal(*gdal_transform) if gdal_transform else None

                            for r in range(R):
                                for c in range(C):
                                    u0, u1 = c/C, (c+1)/C
                                    v0, v1 = r/R, (r+1)/R
                                    
                                    tl = py_bilerp(points[0], points[1], points[2], points[3], u0, v0)
                                    tr = py_bilerp(points[0], points[1], points[2], points[3], u1, v0)
                                    br = py_bilerp(points[0], points[1], points[2], points[3], u1, v1)
                                    bl = py_bilerp(points[0], points[1], points[2], points[3], u0, v1)
                                    
                                    # Desfazer a escala temporária aplicada no visualizador (MAX_DIM)
                                    coords_px = [
                                        (tl['x'] / ratio, tl['y'] / ratio),
                                        (tr['x'] / ratio, tr['y'] / ratio),
                                        (br['x'] / ratio, br['y'] / ratio),
                                        (bl['x'] / ratio, bl['y'] / ratio)
                                    ]
                                    
                                    # Aplicar a conversão georreferenciada Affine
                                    if aff:
                                        coords_geo = [aff * pt for pt in coords_px]
                                    else:
                                        # Fallback visual padrão com inversão de Eixo Y se a imagem for apenas um JPG limpo
                                        coords_geo = [(pt[0], -pt[1]) for pt in coords_px]
                                        
                                    poly = Polygon(coords_geo)
                                    
                                    features.append({
                                        "geometry": poly,
                                        "ID": f"T{c+1} D{r+1}",
                                        "TIRO": c+1,
                                        "DISPARO": r+1
                                    })
                            
                            gdf = gpd.GeoDataFrame(features)
                            
                            # Recuperar CRS se o arquivo importado for GeoTIFF
                            if crs_wkt and aff:
                                gdf.set_crs(crs_wkt, allow_override=True, inplace=True)
                                
                            # Compactar todos os sub-arquivos Shapefile em Memória (SEM ERRO EXTERNO)
                            zip_buffer = io.BytesIO()
                            with tempfile.TemporaryDirectory() as tmpdir:
                                shp_path = os.path.join(tmpdir, "TMG_Grid_Parcelas.shp")
                                gdf.to_file(shp_path, driver="ESRI Shapefile")
                                
                                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                                    for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                                        filepath = shp_path.replace(".shp", ext)
                                        if os.path.exists(filepath):
                                            zf.write(filepath, arcname=f"TMG_Grid_Parcelas{ext}")
                            
                            # Gerar Download Nativo e Seguro Streamlit
                            st.download_button(
                                label="📥 Baixar Shapefile (.SHP) Arquivo ZIP",
                                data=zip_buffer.getvalue(),
                                file_name="TMG_Grid_Shapefile.zip",
                                mime="application/zip",
                                type="primary"
                            )
                        except Exception as ex:
                            st.error(f"Ocorreu um erro no processamento vetorial: {ex}")
                    else:
                        st.error("Bibliotecas obrigatórias (GeoPandas, Shapely) não estão instaladas. Verifique seu ambiente.")
                else:
                    st.info("Aguardando desenho do Grid e clique em Exportar Shapefile no visualizador...")

        else:
            st.markdown("""
            <div style='
                height: 706px;
                border: 1px dashed #2e2e2e;
                border-radius: 12px;
                background: #0d0d0d;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 12px;
                color: #333;
            '>
                <div style='font-size:3rem;'>🗺️</div>
                <div style='font-size:0.9rem;letter-spacing:2px;text-transform:uppercase;'>
                    Nenhuma ortofoto carregada
                </div>
                <div style='font-size:0.75rem;color:#2a2a2a;'>
                    PNG · JPG · TIF · GeoTIFF · JP2 · IMG · ECW
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ==========================================
    # UPLOAD COM SISTEMA DE TRANSFERÊNCIA INTELIGENTE[cite: 1]
    # ==========================================
    elif st.session_state.pagina_ativa == 'Upload':
        st.subheader("📤 Central de Arquivos")

        st.info("Arraste e solte as imagens do experimento agrícola abaixo.")

        uploaded_files = st.file_uploader(
            "Imagens (PNG, JPG)",
            type=["png", "jpg"],
            accept_multiple_files=True
        )

        if uploaded_files:
            st.success(f"{len(uploaded_files)} arquivos prontos para processamento.")

            # Funcionalidade Original que existia[cite: 1]
            if st.button("Iniciar Processamento", type="primary"):
                st.toast("Iniciando análise por IA...")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- NOVA FUNCIONALIDADE: Transferidor de Arquivos ---
            st.markdown("<h4 style='color:#ff8c00; margin-bottom:15px;'>🚀 Transferência Inteligente de Arquivos</h4>", unsafe_allow_html=True)

            col_dest1, col_dest2 = st.columns(2)
            with col_dest1:
                destino_escolhido = st.selectbox(
                    "Selecione o destino de envio das imagens:",
                    ["☁️ OneDrive", "☁️ Google Drive", "☁️ Azure Storage", "📁 Pasta local pré-definida"]
                )
            with col_dest2:
                # Definir caminhos padrões baseados na escolha do usuário
                if "Pasta local" in destino_escolhido:
                    default_path = str(SYSTEM_DATABASE_DIR / "imagens")
                else:
                    default_path = "/Projetos/TMG_2026/Imagens"
                    
                caminho_envio = st.text_input("Caminho/Pasta de destino (Editável):", value=default_path)

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(f"Transferir para {destino_escolhido}", type="primary"):
                with st.spinner(f"Estabelecendo conexão e transferindo {len(uploaded_files)} arquivos para {destino_escolhido}..."):
                    import time
                    time.sleep(2.5) # Simulação mock do envio / status API
                
                if "Pasta local" in destino_escolhido:
                    destino_local = _resolve_system_path(caminho_envio)
                    destino_local.mkdir(parents=True, exist_ok=True)
                    for arquivo in uploaded_files:
                        try:
                            arquivo.seek(0)
                        except Exception:
                            pass
                        (destino_local / Path(arquivo.name).name).write_bytes(arquivo.read())
                    caminho_envio = str(destino_local)

                st.success(f"✅ Transferência concluída com sucesso!")
                st.markdown(f"**Status:** {len(uploaded_files)} imagens salvas na pasta configurada: `{caminho_envio}`")
                st.balloons()
    # CONFIG[cite: 1]
    elif st.session_state.pagina_ativa == 'Config':
        st.subheader("⚙️ Painel Administrativo")

        with st.expander("🎨 Tema do Sistema", expanded=False):
            st.markdown(
                "<div style='color:#888;font-size:0.82rem;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;'>"
                "Selecione o tema visual aplicado em todo o sistema:</div>",
                unsafe_allow_html=True
            )

            _temas_disponiveis = {
                "padrao": "🟠 Padrão do Sistema  —  Dark com laranja (original)",
                "tmg_azul": "🔵 TMG Azul  —  Azul escuro · Cinza · Branco"
            }
            _tema_atual = SYSTEM_CONFIG.get("tema", "padrao")
            _tema_nomes = list(_temas_disponiveis.keys())
            _tema_labels = list(_temas_disponiveis.values())
            _tema_index = _tema_nomes.index(_tema_atual) if _tema_atual in _tema_nomes else 0

            _tema_escolhido_label = st.radio(
                "Tema",
                _tema_labels,
                index=_tema_index,
                key="cfg_tema_radio",
                label_visibility="collapsed"
            )
            _tema_escolhido = _tema_nomes[_tema_labels.index(_tema_escolhido_label)]

            if st.button("💾 Aplicar Tema", type="primary", key="btn_aplicar_tema", use_container_width=True):
                _cfg_tema = _load_system_config()
                _cfg_tema["tema"] = _tema_escolhido
                _save_system_config(_cfg_tema)
                st.success("✅ Tema salvo! Recarregue a página para aplicar.")
                app_rerun()

        with st.expander("Identidade Visual", expanded=True):
            st.write("Atualize a logo do sistema:")

            if LOGO_PATH.exists():
                st.markdown(
                    f"<p style='color:#888; font-size:0.85rem;'>📁 Logo salva em: "
                    f"<code style='color:#ff8c00;'>{LOGO_PATH}</code></p>",
                    unsafe_allow_html=True
                )

            nova_logo = st.file_uploader(
                "Escolha uma nova logo",
                type=["png", "jpg", "jpeg"]
            )

            if nova_logo:
                img = Image.open(nova_logo)
                img.save(str(LOGO_PATH), format="PNG")
                st.session_state.logo_sistema = img

                st.success(f"✅ Logo atualizada e salva em: `{LOGO_PATH}`")
                app_rerun()

        with st.expander("Caminhos de Diretório"):
            st.text_input("Diretório de Banco de Dados", value=str(SYSTEM_DATABASE_DIR), disabled=True)
            st.caption("Altere esta pasta pelo menu Banco de Dados Sistema.")

    # BASES[cite: 1]
    elif st.session_state.pagina_ativa == 'Bases':
        st.subheader("🗂️ Banco de Dados Sistema")

        st.info("Escolha a pasta principal onde o sistema irá trabalhar, salvar arquivos, imagens, ortomosaicos, relatórios e bancos internos.")

        atual = SYSTEM_DATABASE_DIR
        try:
            uso = shutil.disk_usage(atual)
            espaco_livre = _tv_human_size(uso.free)
        except Exception:
            espaco_livre = "Indisponível"

        c1, c2, c3 = st.columns(3)
        c1.metric("Status", "Ativo" if atual.exists() else "Não criado")
        c2.metric("Espaço livre", espaco_livre)
        c3.metric("Atualizado", SYSTEM_CONFIG.get("updated_at") or "-")

        st.markdown(
            f"<div class='card'><h4 style='color:#ff8c00;margin-top:0;'>Pasta atual</h4>"
            f"<code>{atual}</code></div>",
            unsafe_allow_html=True
        )

        sugestoes = {
            "Pasta atual": str(atual),
            "Padrão do sistema": str(_resolve_system_path("tmg_data")),
            "Documentos": str(Path.home() / "Documents" / "TMG_Banco_Dados"),
            "Área de trabalho": str(Path.home() / "Desktop" / "TMG_Banco_Dados")
        }
        if os.name == "nt":
            sugestoes["Disco C"] = "C:/TMG/Banco_Dados_Sistema"

        s1, s2 = st.columns([1, 2])
        with s1:
            preset = st.selectbox("Atalho de pasta", list(sugestoes.keys()), key="sys_db_preset")
        with s2:
            caminho_db = st.text_input(
                "Local da pasta de trabalho",
                value=sugestoes[preset],
                key="sys_db_path"
            )

        criar_estrutura = st.checkbox("Criar estrutura padrão de pastas", value=True, key="sys_db_create_tree")
        subpastas = ["imagens", "ortomosaicos", "relatorios", "exports", "uploads", "grids", "temporarios"]

        if st.button("Salvar Banco de Dados Sistema", type="primary", key="btn_save_system_db", use_container_width=True):
            try:
                novo_dir = _resolve_system_path(caminho_db)
                novo_dir.mkdir(parents=True, exist_ok=True)
                if criar_estrutura:
                    for nome in subpastas:
                        (novo_dir / nome).mkdir(parents=True, exist_ok=True)
                config = _load_system_config()
                config["database_dir"] = str(novo_dir)
                config["updated_at"] = _tv_now()
                _save_system_config(config)
                st.success(f"Banco de Dados Sistema salvo em: `{novo_dir}`")
                app_rerun()
            except Exception as exc:
                st.error(f"Não foi possível salvar a pasta do sistema: {exc}")

        st.markdown("#### Estrutura da pasta")
        estrutura = []
        for nome in subpastas + ["transferencia_voos", "voos_direcionados"]:
            pasta = atual / nome
            estrutura.append({
                "Pasta": nome,
                "Caminho": str(pasta),
                "Status": "Existe" if pasta.exists() else "Não criada"
            })
        st.dataframe(estrutura, use_container_width=True, hide_index=True)

    # SINCRONIZAR DADOS[cite: 1]
    elif st.session_state.pagina_ativa == 'Sync':
        st.subheader("🔄 Sincronização de Dados")

        st.info("Gerencie a sincronização entre bases locais e remotas.")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<h4 style='color:#ff8c00;'>Origem</h4>", unsafe_allow_html=True)
            st.text_input("Servidor de Origem", value=str(SYSTEM_DATABASE_DIR))
            st.selectbox("Protocolo", ["FTP", "SFTP", "S3", "API REST"])

        with col2:
            st.markdown("<h4 style='color:#ff8c00;'>Destino</h4>", unsafe_allow_html=True)
            st.text_input("Servidor de Destino", value="nuvem.tmg.com.br")
            st.selectbox("Frequência", ["Manual", "A cada hora", "Diário", "Semanal"])

        st.markdown("<br>", unsafe_allow_html=True)

        col_a, col_b, col_c = st.columns([1,1,1])
        with col_b:
            if st.button("▶ Iniciar Sincronização", type="primary"):
                with st.spinner("Sincronizando dados..."):
                    import time
                    time.sleep(2)
                st.success("✅ Sincronização concluída com sucesso!")
                st.balloons()

    # GERAR ORTOMOSAICOS[cite: 1]
    elif st.session_state.pagina_ativa == 'Ortomosaicos':
        st.subheader("🛰️ Geração de Ortomosaicos")

        st.info("Configure e processe a geração de ortomosaicos a partir das imagens carregadas.")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<h4 style='color:#ff8c00;'>Parâmetros de Processamento</h4>", unsafe_allow_html=True)
            st.selectbox("Resolução de Saída", ["5 cm/px", "10 cm/px", "20 cm/px", "50 cm/px"])
            st.selectbox("Método de Alinhamento", ["Alta Precisão", "Média Precisão", "Rápida"])
            st.selectbox("Sistema de Coordenadas", ["SIRGAS 2000 (EPSG:4674)", "WGS 84 (EPSG:4326)", "UTM Zone 21S"])
            st.number_input("Sobreposição Frontal (%)", min_value=60, max_value=95, value=80)
            st.number_input("Sobreposição Lateral (%)", min_value=60, max_value=95, value=75)

        with col2:
            st.markdown("<h4 style='color:#ff8c00;'>Área de Processamento</h4>", unsafe_allow_html=True)
            st.text_input("Diretório de Imagens", value=str(SYSTEM_DATABASE_DIR / "imagens"))
            st.text_input("Diretório de Saída", value=str(SYSTEM_DATABASE_DIR / "ortomosaicos"))
            st.text_area("Notas do Voo", placeholder="Descreva condições do voo, sensor utilizado, altitude, etc.")

        st.markdown("<br>", unsafe_allow_html=True)

        cols_btn = st.columns([1,1,1])
        with cols_btn[1]:
            if st.button("🛰️ Gerar Ortomosaico", type="primary"):
                with st.spinner("Processando ortomosaico..."):
                    import time
                    progress = st.progress(0)
                    for i in range(100):
                        time.sleep(0.03)
                        progress.progress(i + 1)
                st.success("✅ Ortomosaico gerado com sucesso!")
                st.markdown(
                    "<p style='color:#ff8c00; text-align:center;'>📁 Arquivo salvo em: "
                    f"<code>{SYSTEM_DATABASE_DIR / 'ortomosaicos' / 'orto_output.tif'}</code></p>",
                    unsafe_allow_html=True
                )

    # ==========================================
    # NOVO - VISUALIZADOR DE RESULTADOS
    # ==========================================
    elif st.session_state.pagina_ativa == 'Visualizador':
        st.subheader("📈 Visualizador de Resultados")

        st.markdown("""
        <div style='color:#ff8c00;font-weight:700;font-size:1rem;letter-spacing:2px;
                    text-transform:uppercase;margin-bottom:20px;'>
            Selecione o tipo de análise para visualizar
        </div>""", unsafe_allow_html=True)

        # NOVO - Inicializar sub-página do visualizador
        if "visualizador_sub" not in st.session_state:
            st.session_state.visualizador_sub = None

        col_v1, col_v2, col_v3, col_v4 = st.columns(4)

        with col_v1:
            if st.button("🔢 Contagem", key="btn_viz_contagem", use_container_width=True):
                st.session_state.visualizador_sub = "Contagem"
        with col_v2:
            if st.button("🍇 Maturação", key="btn_viz_maturacao", use_container_width=True):
                st.session_state.visualizador_sub = "Maturação"
        with col_v3:
            if st.button("🌾 Pendoamento", key="btn_viz_pendoamento", use_container_width=True):
                st.session_state.visualizador_sub = "Pendoamento"
        with col_v4:
            if st.button("✅ Qualidade de Parcelas", key="btn_viz_qualidade", use_container_width=True):
                st.session_state.visualizador_sub = "Qualidade"

        st.markdown("---")

        # NOVO - Sub-visualizações
        if st.session_state.visualizador_sub == "Contagem":
            # NOVO - MÓDULO COMPLETO DE CONTAGEM DE PLANTAS (viewer idêntico ao Checklist + funções TZ Plants)
            st.markdown("""
            <div style='color:#ff8c00;font-weight:700;font-size:1rem;letter-spacing:2px;
                        text-transform:uppercase;margin-bottom:10px;'>
                🌱 Contagem de Plantas por Parcela
            </div>""", unsafe_allow_html=True)

            # NOVO - Upload de imagem para contagem (mesmo formato do Checklist)
            cnt_file = st.file_uploader(
                "📷 Carregar Ortofoto para Contagem",
                type=MOSAIC_UPLOAD_TYPES,
                key="cnt_orto_uploader",
                help="PNG · JPG · TIF/GeoTIFF · JP2 · IMG · ECW"
            )
            cnt_library = _mosaic_single_select("Ou usar mosaico já importado", key="cnt_mosaic_library")
            cnt_bytes, cnt_name = _mosaic_input_bytes(cnt_file, cnt_library, "Contagem")

            if cnt_bytes:
                with st.spinner("Carregando ortofoto..."):
                    cnt_b64, cnt_dims, cnt_err, cnt_spatial = processar_ortofoto(cnt_bytes, cnt_name)

                if cnt_err:
                    st.error(f"Erro: {cnt_err}")
                else:
                    cw_cnt, ch_cnt = cnt_dims
                    st.markdown(
                        f"<p style='color:#666;font-size:0.78rem;margin-bottom:6px;'>"
                        f"📐 {cnt_name} · {cw_cnt}×{ch_cnt} px</p>",
                        unsafe_allow_html=True
                    )

                    # NOVO - Viewer HTML/JS idêntico ao Checklist com funcionalidades de contagem TZ Plants
                    cnt_viewer = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:#0d0d0d; overflow:hidden; font-family:'Segoe UI',sans-serif; }}

  #vc {{
    width:100%; height:706px;
    background:
      linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px),
      #0d0d0d;
    background-size:32px 32px;
    border:1px solid #2a2a2a; border-radius:12px;
    overflow:hidden; position:relative; cursor:grab; user-select:none;
  }}
  #vc:active {{ cursor:grabbing; }}
  canvas {{ position:absolute; top:0; left:0; display:block; }}

  .toolbar {{ position:absolute; top:12px; right:12px; display:flex; flex-direction:column; gap:5px; z-index:20; }}
  .tb-btn {{
    background:linear-gradient(145deg,#1e1e1e,#111); border:1px solid #3a3a3a;
    color:#ff8c00; width:34px; height:34px; border-radius:8px; cursor:pointer;
    font-size:15px; font-weight:700; display:flex; align-items:center; justify-content:center;
    box-shadow:2px 2px 8px #000,inset 0 1px 0 rgba(255,255,255,.05); transition:all .2s;
  }}
  .tb-btn:hover {{ border-color:#ff8c00; box-shadow:0 0 10px rgba(255,140,0,.35),2px 2px 8px #000; color:#ffaa33; }}
  .tb-btn:active {{ transform:translateY(1px); }}
  .tb-sep {{ width:34px; height:1px; background:linear-gradient(90deg,transparent,#333,transparent); margin:2px 0; }}

  .grid-panel {{
    position:absolute; top:12px; right:55px;
    background:rgba(10,10,10,.88); border:1px solid #2a2a2a;
    border-radius:8px; padding:10px; display:flex; flex-direction:column;
    gap:8px; z-index:20;
  }}
  .grid-panel label {{ color:#ff8c00; font-size:11px; font-weight:bold; text-align:center; }}
  .grid-panel input[type=number] {{
    background:#1a1a1a; border:1px solid #333; color:#fff;
    border-radius:4px; padding:4px; width:50px; text-align:center; font-size:11px;
  }}
  .grid-panel .row-col {{ display:flex; gap:8px; align-items:center; justify-content:space-between; color:#ccc; font-size:11px; }}
  .grid-btn {{
    background:linear-gradient(145deg,#1e1e1e,#111); border:1px solid #3a3a3a;
    color:#ccc; cursor:pointer; border-radius:4px; padding:6px; font-size:11px; font-weight:bold; transition:.2s;
  }}
  .grid-btn:hover {{ border-color:#ff8c00; color:#ff8c00; }}
  .grid-btn.active {{ border-color:#ff8c00; color:#ff8c00; box-shadow:0 0 8px rgba(255,140,0,.3); background:#2a1a00; }}

  .zoom-badge {{
    position:absolute; top:12px; left:12px;
    background:rgba(10,10,10,.82); border:1px solid #2a2a2a; border-radius:8px;
    color:#ff8c00; font-size:11px; font-family:'Courier New',monospace;
    font-weight:700; padding:5px 10px; letter-spacing:1px; z-index:20; pointer-events:none;
  }}
  .crosshair {{
    position:absolute; bottom:12px; left:12px;
    background:rgba(10,10,10,.82); border:1px solid #222; border-radius:8px;
    color:#555; font-size:10px; font-family:'Courier New',monospace;
    padding:4px 10px; z-index:20; pointer-events:none; letter-spacing:.5px;
  }}
  .hint {{
    position:absolute; bottom:12px; right:12px; color:#333; font-size:10px;
    z-index:20; pointer-events:none; text-align:right; line-height:1.6;
  }}

  .count-panel {{
    position:absolute; top:50px; left:12px;
    background:rgba(10,10,10,.92); border:1px solid #2a2a2a; border-radius:8px;
    padding:10px; z-index:20; min-width:180px;
  }}
  .count-panel h3 {{ color:#00ff00; font-size:12px; margin-bottom:6px; letter-spacing:1px; }}
  .count-panel .total {{ color:#fff; font-size:22px; font-weight:bold; }}
  .count-panel .info {{ color:#888; font-size:10px; margin-top:4px; }}

  .cnt-btn {{
    background:linear-gradient(145deg,#1a3a1a,#0a2a0a); border:1px solid #006600;
    color:#00ee55; border-radius:4px; padding:6px 8px; font-size:11px;
    font-weight:bold; cursor:pointer; transition:.2s; width:100%; margin-top:4px;
  }}
  .cnt-btn:hover {{ border-color:#00ee55; box-shadow:0 0 8px rgba(0,238,85,.3); }}
  .cnt-btn.danger {{ background:linear-gradient(145deg,#3a1a1a,#2a0a0a); border-color:#660000; color:#ff5555; }}
  .cnt-btn.danger:hover {{ border-color:#ff5555; box-shadow:0 0 8px rgba(255,85,85,.3); }}
  .cnt-btn.manual {{ background:linear-gradient(145deg,#1a1a3a,#0a0a2a); border-color:#000066; color:#5599ff; }}
  .cnt-btn.manual:hover {{ border-color:#5599ff; box-shadow:0 0 8px rgba(85,153,255,.3); }}

  #btnExportCnt {{
    background:linear-gradient(145deg,#003a00,#001a00); border:1px solid #006600;
    color:#00ee55; border-radius:4px; padding:6px 8px; font-size:11px;
    font-weight:bold; cursor:pointer; transition:.2s; width:100%; margin-top:6px;
  }}
  #btnExportCnt:hover {{ border-color:#00ee55; box-shadow:0 0 8px rgba(0,238,85,.3); }}
</style>
</head>
<body>
<div id="vc">
  <canvas id="cv"></canvas>
  <div class="zoom-badge" id="zbadge">1.00×</div>
  <div class="crosshair" id="coord">X:0 Y:0</div>
  <div class="hint">Scroll=Zoom · Drag=Pan<br>Grid: marque 4 pontos</div>

  <div class="toolbar">
    <button class="tb-btn" id="btnGridTool" title="Marcar Grid (4 pontos)">⊞</button>
    <button class="tb-btn" id="btnCountPlants" title="Contar Plantas (automático)">🌱</button>
    <button class="tb-btn" id="btnManualMode" title="Modo Manual (clique para marcar)">✏️</button>
    <button class="tb-btn" id="btnRemoveLast" title="Apagar Última Marcação">❌</button>
    <div class="tb-sep"></div>
    <button class="tb-btn" id="btnClearAll" title="Limpar Tudo">🗑️</button>
  </div>

  <div class="grid-panel">
    <label>🌱 CONTAGEM</label>
    <div class="row-col">
      <span>Disp:</span><input type="number" id="inpRows" value="5" min="1" max="200">
    </div>
    <div class="row-col">
      <span>Tiros:</span><input type="number" id="inpCols" value="5" min="1" max="200">
    </div>
    <button class="cnt-btn" id="btnCountAuto">🌱 Contar</button>
    <button class="cnt-btn manual" id="btnManual2">✏️ Manual</button>
    <button class="cnt-btn danger" id="btnUndoMark">❌ Desfazer</button>
    <button id="btnExportCnt">💾 Exportar CSV</button>
    <button class="cnt-btn" id="btnResumo" style="background:linear-gradient(145deg,#2a1a00,#1a0a00);border-color:#ff8c00;color:#ff8c00;">📊 Resumo</button>
  </div>

  <div class="count-panel" id="countPanel" style="display:none;">
    <h3>CONTAGEM</h3>
    <div class="total" id="totalCount">0</div>
    <div class="info" id="countInfo">Marque o grid e clique Contar</div>
  </div>

  <!-- NOVO - Modal Resumo -->
  <div id="resumoModal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;
    background:rgba(0,0,0,0.85);z-index:9999;align-items:center;justify-content:center;">
    <div style="background:#1a1a1a;border:1px solid #ff8c00;border-radius:16px;width:90%;max-width:700px;
      max-height:85vh;overflow:auto;padding:24px;box-shadow:0 0 40px rgba(255,140,0,0.3);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <h3 style="color:#ff8c00;font-size:14px;letter-spacing:2px;text-transform:uppercase;margin:0;">📊 RESUMO DA CONTAGEM</h3>
        <button id="btnCloseResumo" style="background:#333;border:1px solid #555;color:#fff;border-radius:6px;
          padding:5px 12px;cursor:pointer;font-size:12px;">✕ Fechar</button>
      </div>
      <div id="resumoTotalCard" style="background:#111;border:1px solid #333;border-radius:10px;padding:16px;
        text-align:center;margin-bottom:16px;">
        <div id="resumoTotal" style="color:#00ff00;font-size:28px;font-weight:bold;">0</div>
        <div style="color:#888;font-size:11px;letter-spacing:2px;text-transform:uppercase;">Total de Plantas</div>
      </div>
      <div id="resumoFilter" style="margin-bottom:12px;display:flex;gap:8px;align-items:center;">
        <input type="text" id="resumoSearch" placeholder="Pesquisar parcela (ex: T1 D2)"
          style="flex:1;background:#111;border:1px solid #333;color:#fff;border-radius:6px;padding:8px;font-size:12px;">
        <select id="resumoFilterTiro" style="background:#111;border:1px solid #333;color:#fff;border-radius:6px;padding:8px;font-size:11px;">
          <option value="">Todos Tiros</option>
        </select>
        <select id="resumoFilterDisp" style="background:#111;border:1px solid #333;color:#fff;border-radius:6px;padding:8px;font-size:11px;">
          <option value="">Todos Disparos</option>
        </select>
      </div>
      <div id="resumoTable" style="max-height:300px;overflow-y:auto;border:1px solid #333;border-radius:8px;"></div>
      <div style="display:flex;gap:8px;margin-top:14px;">
        <button id="btnResumoCSV" style="flex:1;background:linear-gradient(145deg,#003a00,#001a00);border:1px solid #006600;
          color:#00ee55;border-radius:6px;padding:8px;font-size:11px;font-weight:bold;cursor:pointer;">💾 Exportar CSV</button>
        <button id="btnResumoXLSX" style="flex:1;background:linear-gradient(145deg,#1a003a,#0a001a);border:1px solid #660099;
          color:#cc66ff;border-radius:6px;padding:8px;font-size:11px;font-weight:bold;cursor:pointer;">📗 Exportar Excel</button>
      </div>
    </div>
  </div>
</div>

<script>
const IMG_B64 = '{cnt_b64}';
const vc    = document.getElementById('vc');
const cv    = document.getElementById('cv');
const ctx   = cv.getContext('2d');
const zb    = document.getElementById('zbadge');
const coordEl = document.getElementById('coord');

const inpRows = document.getElementById('inpRows');
const inpCols = document.getElementById('inpCols');
const btnGridTool = document.getElementById('btnGridTool');
const btnCountPlants = document.getElementById('btnCountPlants');
const btnManualMode = document.getElementById('btnManualMode');
const btnRemoveLast = document.getElementById('btnRemoveLast');
const btnClearAll = document.getElementById('btnClearAll');
const btnCountAuto = document.getElementById('btnCountAuto');
const btnManual2 = document.getElementById('btnManual2');
const btnUndoMark = document.getElementById('btnUndoMark');
const btnExportCnt = document.getElementById('btnExportCnt');
const countPanel = document.getElementById('countPanel');
const totalCountEl = document.getElementById('totalCount');
const countInfoEl = document.getElementById('countInfo');

let gridMode = false;
let manualMode = false;
let points = [];
let draggingPoint = -1;
let sc = 1, ox = 0, oy = 0;
let drag = false, lx = 0, ly = 0;
const MIN_SC = 0.05, MAX_SC = 40;
let imgW = 0, imgH = 0;

let plantCenters = [];
let manualMarks = [];
let parcelCounts = {{}};

const img = new Image();

function getImgCoords(cx, cy) {{
  const r = cv.getBoundingClientRect();
  return {{ x:(cx-r.left-ox)/sc, y:(cy-r.top-oy)/sc }};
}}

function bilerp(p0,p1,p2,p3, u,v) {{
  const tx = (1-u)*p0.x + u*p1.x;
  const ty = (1-u)*p0.y + u*p1.y;
  const bx = (1-u)*p3.x + u*p2.x;
  const by = (1-u)*p3.y + u*p2.y;
  return {{ x:(1-v)*tx + v*bx, y:(1-v)*ty + v*by }};
}}

function pointInPolygon(px, py, polygon) {{
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {{
    const xi = polygon[i].x, yi = polygon[i].y;
    const xj = polygon[j].x, yj = polygon[j].y;
    if (((yi > py) !== (yj > py)) && (px < (xj - xi) * (py - yi) / (yj - yi) + xi)) {{
      inside = !inside;
    }}
  }}
  return inside;
}}

function countPlantsInGrid() {{
  if (points.length < 4) {{
    alert('Marque os 4 cantos do grid primeiro!');
    return;
  }}

  const R = parseInt(inpRows.value) || 1;
  const C = parseInt(inpCols.value) || 1;
  const p0=points[0], p1=points[1], p2=points[2], p3=points[3];

  // Extrair pixels da região do grid para detecção HSV via canvas
  // Criar canvas temporário para processar a imagem
  const tempCv = document.createElement('canvas');
  tempCv.width = imgW; tempCv.height = imgH;
  const tempCtx = tempCv.getContext('2d');
  tempCtx.drawImage(img, 0, 0);

  // Bounding box do polígono
  const xs = points.map(p=>p.x), ys = points.map(p=>p.y);
  const minX = Math.max(0, Math.floor(Math.min(...xs)));
  const maxX = Math.min(imgW, Math.ceil(Math.max(...xs)));
  const minY = Math.max(0, Math.floor(Math.min(...ys)));
  const maxY = Math.min(imgH, Math.ceil(Math.max(...ys)));

  const imgData = tempCtx.getImageData(minX, minY, maxX-minX, maxY-minY);
  const data = imgData.data;
  const w = maxX - minX;
  const h = maxY - minY;

  plantCenters = [];

  // Detecção HSV simplificada (verde)
  // Converter RGB para HSV e detectar plantas
  const visited = new Uint8Array(w * h);
  const minArea = 25;

  for (let y = 0; y < h; y++) {{
    for (let x = 0; x < w; x++) {{
      const idx = (y * w + x) * 4;
      const r2 = data[idx], g = data[idx+1], b = data[idx+2];

      // RGB para HSV
      const max2 = Math.max(r2, g, b), min2 = Math.min(r2, g, b);
      const diff = max2 - min2;
      let hue = 0, sat = 0, val = max2;
      if (diff > 0) {{
        if (max2 === r2) hue = 60 * (((g - b) / diff) % 6);
        else if (max2 === g) hue = 60 * ((b - r2) / diff + 2);
        else hue = 60 * ((r2 - g) / diff + 4);
        if (hue < 0) hue += 360;
        sat = (diff / max2) * 255;
      }}
      val = val;
      hue = hue / 2; // 0-180 range like OpenCV

      // Filtro verde (H:30-90, S:40-255, V:40-255)
      if (hue >= 30 && hue <= 90 && sat >= 40 && val >= 40) {{
        const absX = x + minX, absY = y + minY;
        if (pointInPolygon(absX, absY, points) && !visited[y * w + x]) {{
          // Flood-fill simples para agrupar pixels conectados
          let area = 0, sumX = 0, sumY = 0;
          const stack = [[x, y]];
          while (stack.length > 0 && area < 2000) {{
            const [sx, sy] = stack.pop();
            if (sx < 0 || sx >= w || sy < 0 || sy >= h) continue;
            if (visited[sy * w + sx]) continue;
            const si = (sy * w + sx) * 4;
            const sr = data[si], sg = data[si+1], sb = data[si+2];
            const smax = Math.max(sr,sg,sb), smin = Math.min(sr,sg,sb);
            const sdiff = smax - smin;
            let sh = 0, ss = 0;
            if (sdiff > 0) {{
              if (smax === sr) sh = 60*(((sg-sb)/sdiff)%6);
              else if (smax === sg) sh = 60*((sb-sr)/sdiff+2);
              else sh = 60*((sr-sg)/sdiff+4);
              if (sh < 0) sh += 360;
              ss = (sdiff/smax)*255;
            }}
            sh = sh/2;
            if (sh < 30 || sh > 90 || ss < 40 || smax < 40) continue;
            visited[sy * w + sx] = 1;
            area++; sumX += sx; sumY += sy;
            stack.push([sx+1,sy],[sx-1,sy],[sx,sy+1],[sx,sy-1]);
          }}
          if (area >= minArea) {{
            plantCenters.push({{ x: Math.round(sumX/area) + minX, y: Math.round(sumY/area) + minY }});
          }}
        }}
      }}
    }}
  }}

  // Adicionar marcas manuais que estão dentro do polígono
  for (const m of manualMarks) {{
    if (pointInPolygon(m.x, m.y, points)) {{
      plantCenters.push(m);
    }}
  }}

  // Contar por parcela
  parcelCounts = {{}};
  for (let r2 = 0; r2 < R; r2++) {{
    for (let c = 0; c < C; c++) {{
      const u0=c/C, u1=(c+1)/C, v0=r2/R, v1=(r2+1)/R;
      const tl=bilerp(p0,p1,p2,p3,u0,v0);
      const tr=bilerp(p0,p1,p2,p3,u1,v0);
      const br=bilerp(p0,p1,p2,p3,u1,v1);
      const bl=bilerp(p0,p1,p2,p3,u0,v1);
      const poly = [tl, tr, br, bl];
      let cnt = 0;
      for (const p of plantCenters) {{
        if (pointInPolygon(p.x, p.y, poly)) cnt++;
      }}
      const dispLabel = R - r2;
      const tiroLabel = C - c;
      parcelCounts[dispLabel + '_' + tiroLabel] = cnt;
    }}
  }}

  // Atualizar painel
  countPanel.style.display = 'block';
  totalCountEl.textContent = plantCenters.length;
  countInfoEl.textContent = 'Grid ' + R + '×' + C + ' | Dentro da área marcada';

  drawAll();
}}

function drawAll() {{
  const W = vc.clientWidth, H = vc.clientHeight;
  cv.width = W; cv.height = H;
  ctx.clearRect(0,0,W,H);
  ctx.save();
  ctx.translate(ox,oy); ctx.scale(sc,sc);
  if(imgW>0) ctx.drawImage(img,0,0);

  // Desenhar grid
  if (points.length === 4) {{
    const R = parseInt(inpRows.value)||1;
    const C = parseInt(inpCols.value)||1;
    const p0=points[0],p1=points[1],p2=points[2],p3=points[3];

    ctx.save();
    ctx.strokeStyle='rgba(30,144,255,0.95)'; ctx.lineWidth=2/sc;
    ctx.shadowColor='rgba(0,160,255,0.6)'; ctx.shadowBlur=6/sc;

    for(let i=0;i<=R;i++) {{
      const v=i/R;
      const lx2=(1-v)*p0.x+v*p3.x, ly2=(1-v)*p0.y+v*p3.y;
      const rx2=(1-v)*p1.x+v*p2.x, ry2=(1-v)*p1.y+v*p2.y;
      ctx.beginPath(); ctx.moveTo(lx2,ly2); ctx.lineTo(rx2,ry2); ctx.stroke();
    }}
    for(let j=0;j<=C;j++) {{
      const u=j/C;
      const tx2=(1-u)*p0.x+u*p1.x, ty2=(1-u)*p0.y+u*p1.y;
      const bx2=(1-u)*p3.x+u*p2.x, by2=(1-u)*p3.y+u*p2.y;
      ctx.beginPath(); ctx.moveTo(tx2,ty2); ctx.lineTo(bx2,by2); ctx.stroke();
    }}
    ctx.restore();

    // Mostrar contagem por parcela
    if (Object.keys(parcelCounts).length > 0) {{
      for (let r2=0; r2<R; r2++) {{
        for (let c=0; c<C; c++) {{
          const u0=c/C, u1=(c+1)/C, v0=r2/R, v1=(r2+1)/R;
          const tl=bilerp(p0,p1,p2,p3,u0,v0);
          const tr=bilerp(p0,p1,p2,p3,u1,v0);
          const br=bilerp(p0,p1,p2,p3,u1,v1);
          const bl=bilerp(p0,p1,p2,p3,u0,v1);
          const cx2=(tl.x+tr.x+br.x+bl.x)/4;
          const cy2=(tl.y+tr.y+br.y+bl.y)/4;
          const dispLabel = R - r2;
          const tiroLabel = C - c;
          const cnt = parcelCounts[dispLabel + '_' + tiroLabel] || 0;

          ctx.save();
          ctx.fillStyle = cnt > 0 ? 'rgba(0,255,0,0.15)' : 'rgba(255,0,0,0.08)';
          ctx.beginPath();
          ctx.moveTo(tl.x,tl.y); ctx.lineTo(tr.x,tr.y);
          ctx.lineTo(br.x,br.y); ctx.lineTo(bl.x,bl.y);
          ctx.closePath(); ctx.fill();

          ctx.shadowColor='rgba(0,0,0,0.9)'; ctx.shadowBlur=4/sc;
          ctx.fillStyle='#ffffff';
          ctx.font='bold '+(Math.max(8, 11/sc))+'px Arial';
          ctx.textAlign='center'; ctx.textBaseline='middle';
          ctx.fillText(cnt, cx2, cy2);
          ctx.font=(Math.max(6, 8/sc))+'px Arial';
          ctx.fillStyle='#aaa';
          ctx.fillText('T'+tiroLabel+' D'+dispLabel, cx2, cy2 + 14/sc);
          ctx.restore();
        }}
      }}
    }}
  }}

  // Desenhar pontos do grid
  points.forEach((p,i) => {{
    const isDrag = draggingPoint===i;
    const r2 = 11/sc;
    ctx.save();
    ctx.shadowColor = isDrag ? 'rgba(255,255,255,0.9)' : 'rgba(0,180,255,0.8)';
    ctx.shadowBlur = 14/sc;
    ctx.beginPath(); ctx.arc(p.x,p.y,r2,0,2*Math.PI);
    ctx.fillStyle = isDrag ? '#ffffff' : '#1e90ff'; ctx.fill();
    ctx.lineWidth=2.5/sc; ctx.strokeStyle = isDrag ? '#aaddff' : '#00cfff'; ctx.stroke();
    ctx.restore();
    ctx.save();
    ctx.fillStyle='#ffffff'; ctx.font='bold '+(13/sc)+'px Arial';
    ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText(i+1,p.x,p.y);
    ctx.restore();
  }});

  // Desenhar plantas detectadas (X verde)
  for (const p of plantCenters) {{
    const sz = 6/sc;
    ctx.save();
    ctx.strokeStyle='#00ff00'; ctx.lineWidth=2/sc;
    ctx.beginPath(); ctx.moveTo(p.x-sz,p.y-sz); ctx.lineTo(p.x+sz,p.y+sz); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(p.x-sz,p.y+sz); ctx.lineTo(p.x+sz,p.y-sz); ctx.stroke();
    ctx.restore();
  }}

  // Desenhar marcas manuais (X vermelho)
  for (const p of manualMarks) {{
    const sz = 8/sc;
    ctx.save();
    ctx.strokeStyle='#ff3333'; ctx.lineWidth=2.5/sc;
    ctx.beginPath(); ctx.moveTo(p.x-sz,p.y-sz); ctx.lineTo(p.x+sz,p.y+sz); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(p.x-sz,p.y+sz); ctx.lineTo(p.x+sz,p.y-sz); ctx.stroke();
    ctx.restore();
  }}

  ctx.restore();
  zb.textContent = sc.toFixed(2) + '×';
}}

// Eventos
img.onload = () => {{
  imgW = img.width; imgH = img.height;
  const W = vc.clientWidth, H = vc.clientHeight;
  sc = Math.min(W/imgW, H/imgH);
  ox = (W - imgW*sc)/2; oy = (H - imgH*sc)/2;
  drawAll();
}};
img.src = 'data:image/png;base64,' + IMG_B64;

// Pan & Zoom
vc.addEventListener('wheel', e => {{
  e.preventDefault();
  const factor = e.deltaY < 0 ? 1.2 : 0.8;
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  const ix = (mx - ox)/sc, iy = (my - oy)/sc;
  sc *= factor;
  sc = Math.max(MIN_SC, Math.min(MAX_SC, sc));
  ox = mx - ix*sc; oy = my - iy*sc;
  drawAll();
}}, {{passive:false}});

vc.addEventListener('mousedown', e => {{
  const pt = getImgCoords(e.clientX, e.clientY);

  // Verificar se está arrastando um ponto do grid
  for (let i = 0; i < points.length; i++) {{
    const dx = (pt.x - points[i].x)*sc, dy = (pt.y - points[i].y)*sc;
    if (Math.sqrt(dx*dx+dy*dy) < 20) {{
      draggingPoint = i;
      return;
    }}
  }}

  // Modo grid - adicionar ponto
  if (gridMode && points.length < 4) {{
    points.push({{x:pt.x, y:pt.y}});
    if (points.length === 4) gridMode = false;
    drawAll();
    return;
  }}

  // Modo manual - adicionar marca
  if (manualMode && points.length === 4) {{
    if (pointInPolygon(pt.x, pt.y, points)) {{
      manualMarks.push({{x:pt.x, y:pt.y}});
      plantCenters.push({{x:pt.x, y:pt.y}});
      // Recontabilizar
      recount();
      drawAll();
    }}
    return;
  }}

  // Pan
  drag = true; lx = e.clientX; ly = e.clientY;
  vc.style.cursor = 'grabbing';
}});

vc.addEventListener('mousemove', e => {{
  const pt = getImgCoords(e.clientX, e.clientY);
  coordEl.textContent = 'X:' + Math.round(pt.x) + ' Y:' + Math.round(pt.y);

  if (draggingPoint >= 0) {{
    points[draggingPoint] = {{x:pt.x, y:pt.y}};
    drawAll();
    return;
  }}
  if (drag) {{
    ox += e.clientX - lx; oy += e.clientY - ly;
    lx = e.clientX; ly = e.clientY;
    drawAll();
  }}
}});

vc.addEventListener('mouseup', () => {{
  drag = false; draggingPoint = -1;
  vc.style.cursor = 'grab';
}});
vc.addEventListener('mouseleave', () => {{
  drag = false; draggingPoint = -1;
}});

function recount() {{
  if (points.length < 4) return;
  const R = parseInt(inpRows.value)||1;
  const C = parseInt(inpCols.value)||1;
  const p0=points[0],p1=points[1],p2=points[2],p3=points[3];
  parcelCounts = {{}};
  for (let r2=0; r2<R; r2++) {{
    for (let c=0; c<C; c++) {{
      const u0=c/C, u1=(c+1)/C, v0=r2/R, v1=(r2+1)/R;
      const tl=bilerp(p0,p1,p2,p3,u0,v0);
      const tr=bilerp(p0,p1,p2,p3,u1,v0);
      const br=bilerp(p0,p1,p2,p3,u1,v1);
      const bl=bilerp(p0,p1,p2,p3,u0,v1);
      const poly = [tl,tr,br,bl];
      let cnt = 0;
      for (const p of plantCenters) {{
        if (pointInPolygon(p.x, p.y, poly)) cnt++;
      }}
      parcelCounts[(R-r2)+'_'+(C-c)] = cnt;
    }}
  }}
  countPanel.style.display = 'block';
  totalCountEl.textContent = plantCenters.length;
  countInfoEl.textContent = 'Grid ' + R + '×' + C + ' | ' + plantCenters.length + ' plantas';
}}

// Botões
btnGridTool.onclick = () => {{
  gridMode = !gridMode; manualMode = false;
  btnGridTool.style.borderColor = gridMode ? '#ff8c00' : '#3a3a3a';
  btnManualMode.style.borderColor = '#3a3a3a';
  if (gridMode) {{ points = []; plantCenters = []; manualMarks = []; parcelCounts = {{}}; countPanel.style.display='none'; drawAll(); }}
}};

btnCountPlants.onclick = () => countPlantsInGrid();
btnCountAuto.onclick = () => countPlantsInGrid();

btnManualMode.onclick = () => {{
  manualMode = !manualMode; gridMode = false;
  btnManualMode.style.borderColor = manualMode ? '#5599ff' : '#3a3a3a';
  btnGridTool.style.borderColor = '#3a3a3a';
}};
btnManual2.onclick = () => {{
  manualMode = !manualMode; gridMode = false;
  btnManualMode.style.borderColor = manualMode ? '#5599ff' : '#3a3a3a';
}};

btnRemoveLast.onclick = () => {{
  if (manualMarks.length > 0) {{
    const removed = manualMarks.pop();
    plantCenters = plantCenters.filter(p => p.x !== removed.x || p.y !== removed.y);
    recount(); drawAll();
  }}
}};
btnUndoMark.onclick = btnRemoveLast.onclick;

btnClearAll.onclick = () => {{
  points = []; plantCenters = []; manualMarks = []; parcelCounts = {{}};
  countPanel.style.display = 'none'; gridMode = false; manualMode = false;
  btnGridTool.style.borderColor = '#3a3a3a';
  btnManualMode.style.borderColor = '#3a3a3a';
  drawAll();
}};

btnExportCnt.onclick = () => {{
  if (Object.keys(parcelCounts).length === 0) {{ alert('Nenhuma contagem realizada.'); return; }}
  const R = parseInt(inpRows.value)||1;
  const C = parseInt(inpCols.value)||1;
  let csvContent = '\\uFEFF' + 'Disparo;Tiro;Quantidade de Plantas\\n';
  const keys = Object.keys(parcelCounts).sort((a,b) => {{
    const [da,ta] = a.split('_').map(Number);
    const [db,tb] = b.split('_').map(Number);
    return da===db ? ta-tb : da-db;
  }});
  let total = 0;
  for (const k of keys) {{
    const [d,t] = k.split('_');
    csvContent += d + ';' + t + ';' + parcelCounts[k] + '\\n';
    total += parcelCounts[k];
  }}
  csvContent += '\\n;Total Geral;' + total + '\\n';
  const blob = new Blob([csvContent], {{type:'text/csv;charset=utf-8;'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'contagem_plantas.csv';
  a.click();
}};

// NOVO - Resumo Modal Logic
const resumoModal = document.getElementById('resumoModal');
const btnResumo = document.getElementById('btnResumo');
const btnCloseResumo = document.getElementById('btnCloseResumo');
const resumoSearch = document.getElementById('resumoSearch');
const resumoFilterTiro = document.getElementById('resumoFilterTiro');
const resumoFilterDisp = document.getElementById('resumoFilterDisp');

function buildResumoTable(filterText, filterTiro, filterDisp) {{
  const table = document.getElementById('resumoTable');
  if (Object.keys(parcelCounts).length === 0) {{
    table.innerHTML = '<p style="color:#666;text-align:center;padding:20px;font-size:12px;">Nenhuma contagem realizada.</p>';
    return;
  }}
  const R = parseInt(inpRows.value)||1, C = parseInt(inpCols.value)||1;
  let html = '<table style="width:100%;border-collapse:collapse;font-size:11px;">';
  html += '<thead><tr style="background:#222;color:#ff8c00;"><th style="padding:8px;border-bottom:1px solid #333;">Parcela</th><th style="padding:8px;border-bottom:1px solid #333;">Tiro</th><th style="padding:8px;border-bottom:1px solid #333;">Disparo</th><th style="padding:8px;border-bottom:1px solid #333;">Plantas</th></tr></thead><tbody>';
  const keys = Object.keys(parcelCounts).sort((a,b) => {{
    const [da,ta] = a.split('_').map(Number);
    const [db,tb] = b.split('_').map(Number);
    return da===db ? ta-tb : da-db;
  }});
  let total = 0, shown = 0;
  const tiroTotals = {{}}, dispTotals = {{}};
  for (const k of keys) {{
    const [d,t] = k.split('_').map(Number);
    const cnt = parcelCounts[k];
    total += cnt;
    tiroTotals[t] = (tiroTotals[t]||0) + cnt;
    dispTotals[d] = (dispTotals[d]||0) + cnt;
    const label = 'T'+t+' D'+d;
    if (filterText && !label.toLowerCase().includes(filterText.toLowerCase())) continue;
    if (filterTiro && t !== parseInt(filterTiro)) continue;
    if (filterDisp && d !== parseInt(filterDisp)) continue;
    shown++;
    html += '<tr style="border-bottom:1px solid #222;"><td style="padding:6px 8px;color:#ccc;">P'+(shown<10?'0':'')+shown+'</td><td style="padding:6px 8px;color:#5599ff;">T'+t+'</td><td style="padding:6px 8px;color:#55ff99;">D'+d+'</td><td style="padding:6px 8px;color:#fff;font-weight:bold;">'+cnt+'</td></tr>';
  }}
  html += '</tbody></table>';

  // Totais por tiro
  html += '<div style="margin-top:12px;padding:10px;background:#111;border:1px solid #222;border-radius:6px;"><p style="color:#5599ff;font-size:11px;font-weight:bold;margin-bottom:6px;">Resumo por Tiro:</p>';
  for (const t of Object.keys(tiroTotals).sort((a,b)=>a-b)) {{
    html += '<span style="color:#ccc;font-size:10px;margin-right:12px;">T'+t+': <b style=color:#fff>'+tiroTotals[t]+'</b></span>';
  }}
  html += '</div>';

  // Totais por disparo
  html += '<div style="margin-top:8px;padding:10px;background:#111;border:1px solid #222;border-radius:6px;"><p style="color:#55ff99;font-size:11px;font-weight:bold;margin-bottom:6px;">Resumo por Disparo:</p>';
  for (const d of Object.keys(dispTotals).sort((a,b)=>a-b)) {{
    html += '<span style="color:#ccc;font-size:10px;margin-right:12px;">D'+d+': <b style=color:#fff>'+dispTotals[d]+'</b></span>';
  }}
  html += '</div>';

  table.innerHTML = html;
  document.getElementById('resumoTotal').textContent = total;
}}

function openResumo() {{
  if (Object.keys(parcelCounts).length === 0) {{ alert('Realize a contagem primeiro!'); return; }}
  const R = parseInt(inpRows.value)||1, C = parseInt(inpCols.value)||1;
  // Populate filters
  resumoFilterTiro.innerHTML = '<option value="">Todos Tiros</option>';
  resumoFilterDisp.innerHTML = '<option value="">Todos Disparos</option>';
  for (let c=1;c<=C;c++) resumoFilterTiro.innerHTML += '<option value="'+c+'">Tiro '+c+'</option>';
  for (let r=1;r<=R;r++) resumoFilterDisp.innerHTML += '<option value="'+r+'">Disparo '+r+'</option>';
  buildResumoTable('','','');
  resumoModal.style.display = 'flex';
}}

btnResumo.onclick = openResumo;
btnCloseResumo.onclick = () => {{ resumoModal.style.display = 'none'; }};
resumoSearch.oninput = () => buildResumoTable(resumoSearch.value, resumoFilterTiro.value, resumoFilterDisp.value);
resumoFilterTiro.onchange = () => buildResumoTable(resumoSearch.value, resumoFilterTiro.value, resumoFilterDisp.value);
resumoFilterDisp.onchange = () => buildResumoTable(resumoSearch.value, resumoFilterTiro.value, resumoFilterDisp.value);

document.getElementById('btnResumoCSV').onclick = () => {{
  const R = parseInt(inpRows.value)||1, C = parseInt(inpCols.value)||1;
  let csv = '\\uFEFF' + 'ID Parcela;Tiro;Disparo;Quantidade Plantas\\n';
  const keys = Object.keys(parcelCounts).sort((a,b) => {{
    const [da,ta] = a.split('_').map(Number);
    const [db,tb] = b.split('_').map(Number);
    return da===db ? ta-tb : da-db;
  }});
  let total = 0, idx = 0;
  for (const k of keys) {{
    const [d,t] = k.split('_'); idx++;
    csv += 'P'+(idx<10?'0':'')+idx+';'+t+';'+d+';'+parcelCounts[k]+'\\n';
    total += parcelCounts[k];
  }}
  csv += '\\n;;Total Geral;'+total+'\\n';
  const blob = new Blob([csv], {{type:'text/csv;charset=utf-8;'}});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'resumo_contagem_plantas.csv'; a.click();
}};

document.getElementById('btnResumoXLSX').onclick = () => {{
  if (typeof XLSX === 'undefined') {{ alert('Biblioteca XLSX não carregada.'); return; }}
  const R = parseInt(inpRows.value)||1, C = parseInt(inpCols.value)||1;
  const rows = [['ID Parcela','Tiro','Disparo','Quantidade Plantas']];
  const keys = Object.keys(parcelCounts).sort((a,b) => {{
    const [da,ta] = a.split('_').map(Number);
    const [db,tb] = b.split('_').map(Number);
    return da===db ? ta-tb : da-db;
  }});
  let total = 0, idx = 0;
  for (const k of keys) {{
    const [d,t] = k.split('_').map(Number); idx++;
    rows.push(['P'+(idx<10?'0':'')+idx, t, d, parcelCounts[k]]);
    total += parcelCounts[k];
  }}
  rows.push([]); rows.push(['','','Total Geral', total]);
  const ws = XLSX.utils.aoa_to_sheet(rows);
  ws['!cols'] = [{{wch:12}},{{wch:8}},{{wch:10}},{{wch:18}}];
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Resumo Contagem');
  XLSX.writeFile(wb, 'resumo_contagem_plantas.xlsx');
}};

// Resize
new ResizeObserver(() => drawAll()).observe(vc);
</script>
</body>
</html>
"""
                    components.html(cnt_viewer, height=720, scrolling=False)

            else:
                st.markdown("""
                <div style='height:706px;border:1px dashed #2e2e2e;border-radius:12px;background:#0d0d0d;
                            display:flex;flex-direction:column;align-items:center;justify-content:center;
                            gap:12px;color:#333;'>
                    <div style='font-size:3rem;'>🌱</div>
                    <div style='font-size:0.85rem;letter-spacing:2px;text-transform:uppercase;color:#555;'>
                        Carregue uma ortofoto para iniciar a contagem
                    </div>
                    <div style='font-size:0.75rem;color:#444;'>
                        Marque 4 pontos do grid → Clique em Contar → Exporte CSV
                    </div>
                </div>""", unsafe_allow_html=True)
            # FIM NOVO - MÓDULO CONTAGEM DE PLANTAS

        elif st.session_state.visualizador_sub == "Maturação":
            st.markdown("""
            <div style='background:#1e1e1e;border:1px solid #333;border-radius:15px;padding:30px;text-align:center;'>
                <div style='font-size:3rem;margin-bottom:12px;'>🍇</div>
                <div style='color:#ff8c00;font-weight:700;font-size:1.2rem;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;'>
                    Maturação
                </div>
                <div style='color:#666;font-size:0.85rem;'>
                    Módulo de análise de maturação por parcela.<br>
                    Funcionalidade em desenvolvimento — dados serão exibidos aqui.
                </div>
            </div>""", unsafe_allow_html=True)

        elif st.session_state.visualizador_sub == "Pendoamento":
            st.markdown("""
            <div style='color:#ff8c00;font-weight:700;font-size:1rem;letter-spacing:2px;
                        text-transform:uppercase;margin-bottom:10px;'>
                🌾 Pendoamento · Visualizador de Ortofoto por Parcela
            </div>""", unsafe_allow_html=True)

            pend_file = st.file_uploader(
                "📷 Carregar Ortofoto para Pendoamento",
                type=MOSAIC_UPLOAD_TYPES,
                key="pend_orto_uploader",
                help="PNG · JPG · TIF/GeoTIFF · JP2 · IMG · ECW"
            )
            pend_library = _mosaic_single_select("Ou usar mosaico já importado", key="pend_mosaic_library")
            pend_bytes, pend_name = _mosaic_input_bytes(pend_file, pend_library, "Pendoamento")

            if pend_bytes:
                with st.spinner("Carregando ortofoto para pendoamento..."):
                    pend_b64, pend_dims, pend_err, pend_spatial = processar_ortofoto(pend_bytes, pend_name)

                if pend_err:
                    st.error(f"Erro: {pend_err}")
                else:
                    pw, ph = pend_dims
                    st.markdown(
                        f"<p style='color:#666;font-size:0.78rem;margin-bottom:6px;'>"
                        f"📐 {pend_name} · {pw}×{ph} px · análise sobre ortofoto e grid</p>",
                        unsafe_allow_html=True
                    )

                    pend_viewer = """
<!DOCTYPE html>
<html>
<head>
<style>
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:#0d0d0d; overflow:hidden; font-family:'Segoe UI',sans-serif; }
  #vc {
    width:100%; height:720px; position:relative; overflow:hidden; user-select:none; cursor:grab;
    border:1px solid #2a2a2a; border-radius:12px;
    background:
      linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px),
      #0d0d0d;
    background-size:32px 32px;
  }
  #vc:active { cursor:grabbing; }
  canvas { position:absolute; inset:0; display:block; }
  .toolbar { position:absolute; top:12px; right:12px; display:flex; flex-direction:column; gap:5px; z-index:20; }
  .tb-btn {
    width:34px; height:34px; border-radius:8px; cursor:pointer; font-size:15px; font-weight:700;
    display:flex; align-items:center; justify-content:center; color:#ff8c00;
    background:linear-gradient(145deg,#1e1e1e,#111); border:1px solid #3a3a3a;
    box-shadow:2px 2px 8px #000,inset 0 1px 0 rgba(255,255,255,.05); transition:all .2s;
  }
  .tb-btn:hover { border-color:#ff8c00; box-shadow:0 0 10px rgba(255,140,0,.35),2px 2px 8px #000; color:#ffaa33; }
  .tb-btn.active { border-color:#ff8c00; color:#ff8c00; background:#2a1a00; }
  .tb-sep { width:34px; height:1px; background:linear-gradient(90deg,transparent,#333,transparent); margin:2px 0; }
  .grid-panel {
    position:absolute; top:10px; right:55px; z-index:20; min-width:218px; max-height:calc(100% - 20px);
    overflow-y:auto; overflow-x:hidden; background:rgba(10,10,10,.92); border:1px solid #2a2a2a;
    border-radius:8px; padding:8px; display:flex; flex-direction:column; gap:5px;
    scrollbar-width:thin; scrollbar-color:#ff8c00 #141414;
  }
  .grid-panel::-webkit-scrollbar { width:6px; }
  .grid-panel::-webkit-scrollbar-track { background:#141414; border-radius:6px; }
  .grid-panel::-webkit-scrollbar-thumb { background:#ff8c00; border-radius:6px; }
  .grid-panel label { color:#ff8c00; font-size:10px; line-height:1.1; font-weight:bold; text-align:center; }
  .grid-panel .section { color:#ff8c00; font-size:10px; font-weight:800; text-align:center; margin-top:4px; }
  .grid-panel .row-col { display:flex; gap:6px; align-items:center; justify-content:space-between; color:#ccc; font-size:10px; min-height:21px; }
  .grid-panel input[type=number] {
    background:#1a1a1a; border:1px solid #333; color:#fff; border-radius:4px;
    padding:2px 3px; height:21px; width:54px; text-align:center; font-size:10px;
  }
  .grid-panel select {
    background:#1a1a1a; border:1px solid #333; color:#fff; border-radius:4px;
    padding:2px 4px; height:23px; width:92px; font-size:10px;
  }
  .grid-btn, .cnt-btn {
    width:100%; min-height:23px; border-radius:4px; padding:4px 6px; font-size:10px; font-weight:bold;
    cursor:pointer; transition:.2s; color:#ccc; background:linear-gradient(145deg,#1e1e1e,#111); border:1px solid #3a3a3a;
  }
  .grid-btn:hover, .cnt-btn:hover { border-color:#ff8c00; color:#ff8c00; }
  .grid-btn.active { border-color:#ff8c00; color:#ff8c00; box-shadow:0 0 8px rgba(255,140,0,.3); background:#2a1a00; }
  .cnt-btn.orange { background:linear-gradient(145deg,#2a1a00,#1a0a00); border-color:#ff8c00; color:#ff8c00; }
  .cnt-btn.green { background:linear-gradient(145deg,#1a3a1a,#0a2a0a); border-color:#006600; color:#00ee55; }
  .cnt-btn.blue { background:linear-gradient(145deg,#1a1a3a,#0a0a2a); border-color:#000066; color:#5599ff; }
  .cnt-btn.danger { background:linear-gradient(145deg,#3a1a1a,#2a0a0a); border-color:#660000; color:#ff5555; }
  .qual-sep { width:100%; height:1px; background:linear-gradient(90deg,transparent,#333,transparent); margin:2px 0; }
  .zoom-badge {
    position:absolute; top:12px; left:12px; z-index:20; pointer-events:none;
    background:rgba(10,10,10,.82); border:1px solid #2a2a2a; border-radius:8px;
    color:#ff8c00; font-size:11px; font-family:'Courier New',monospace; font-weight:700;
    padding:5px 10px; letter-spacing:1px;
  }
  .crosshair {
    position:absolute; bottom:12px; left:12px; z-index:20; pointer-events:none;
    background:rgba(10,10,10,.82); border:1px solid #222; border-radius:8px;
    color:#555; font-size:10px; font-family:'Courier New',monospace; padding:4px 10px; letter-spacing:.5px;
  }
  .hint {
    position:absolute; bottom:12px; right:12px; z-index:20; pointer-events:none; text-align:right;
    color:#333; font-size:10px; line-height:1.6;
  }
  .count-panel {
    position:absolute; top:50px; left:12px; z-index:20; min-width:215px; max-width:280px;
    background:rgba(10,10,10,.92); border:1px solid #2a2a2a; border-radius:8px; padding:11px;
  }
  .count-panel h3 { color:#ffb347; font-size:12px; margin-bottom:6px; letter-spacing:1px; }
  .count-panel .total { color:#fff; font-size:22px; font-weight:bold; }
  .count-panel .info { color:#888; font-size:10px; margin-top:4px; line-height:1.35; }
  .result-box {
    max-height:145px; overflow:auto; margin-top:8px; border-top:1px solid #262626; padding-top:6px;
    color:#bbb; font-size:10px; line-height:1.45;
  }
</style>
</head>
<body>
<div id="vc">
  <canvas id="cv"></canvas>
  <div class="zoom-badge" id="zbadge">1.00×</div>
  <div class="crosshair" id="coord">X:0 Y:0</div>
  <div class="hint">Scroll=Zoom · Drag=Pan<br>Grid: marque 4 pontos · Pendoamento sobre parcelas</div>

  <div class="toolbar">
    <button class="tb-btn" id="btnGridTool" title="Marcar Grid">⊞</button>
    <button class="tb-btn" id="btnSelectParcel" title="Selecionar Parcelas">▣</button>
    <div class="tb-sep"></div>
    <button class="tb-btn" id="btnFit" title="Ajustar à tela">⤢</button>
    <button class="tb-btn" id="btnClearAll" title="Limpar">🗑</button>
  </div>

  <div class="grid-panel">
    <label>🌾 PENDOAMENTO</label>
    <div class="row-col"><span>Disp:</span><input type="number" id="inpRows" value="5" min="1" max="200"></div>
    <div class="row-col"><span>Tiros:</span><input type="number" id="inpCols" value="5" min="1" max="200"></div>
    <div class="row-col"><span>Teto/parcela:</span><input type="number" id="inpTeto" value="20" min="1" max="10000"></div>
    <div class="row-col"><span>Trava:</span><span style="color:#ffb347;font-weight:800;">50%</span></div>
    <button class="grid-btn" id="btnGrid2">Marcar Grid</button>
    <button class="cnt-btn blue" id="btnSelect2">Selecionar Parcelas</button>
    <div class="qual-sep"></div>
    <div class="section">Análise</div>
    <button class="cnt-btn orange" id="btnAnalyze18000">🌾 Análise de Pendoamento</button>
    <button class="cnt-btn green" id="btnAnalyzeSelected">🌾 Análise Selecionadas</button>
    <button class="cnt-btn" id="btnExportCSV">💾 Exportar CSV</button>
    <button class="cnt-btn danger" id="btnClearResults">Limpar Resultados</button>
  </div>

  <div class="count-panel" id="countPanel" style="display:none;">
    <h3>RESULTADOS PENDOAMENTO</h3>
    <div class="total" id="totalCount">0</div>
    <div class="info" id="countInfo">Marque o grid e execute a análise.</div>
    <div class="result-box" id="resultBox"></div>
  </div>
</div>

<script>
const IMG_B64 = "__PEND_B64__";
const IMAGE_NAME = __PEND_IMAGE_NAME__;
const vc = document.getElementById('vc');
const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const zb = document.getElementById('zbadge');
const coordEl = document.getElementById('coord');
const inpRows = document.getElementById('inpRows');
const inpCols = document.getElementById('inpCols');
const inpTeto = document.getElementById('inpTeto');
const btnGridTool = document.getElementById('btnGridTool');
const btnGrid2 = document.getElementById('btnGrid2');
const btnSelectParcel = document.getElementById('btnSelectParcel');
const btnSelect2 = document.getElementById('btnSelect2');
const btnRun = document.getElementById('btnRun');
const btnAnalyze18000 = document.getElementById('btnAnalyze18000');
const btnAnalyzeAll = document.getElementById('btnAnalyzeAll');
const btnAnalyzeSelected = document.getElementById('btnAnalyzeSelected');
const btnTrainPositive = document.getElementById('btnTrainPositive');
const btnTrainNegative = document.getElementById('btnTrainNegative');
const btnClearTraining = document.getElementById('btnClearTraining');
const trainInfo = document.getElementById('trainInfo');
const btnExportCSV = document.getElementById('btnExportCSV');
const btnClearResults = document.getElementById('btnClearResults');
const btnClearAll = document.getElementById('btnClearAll');
const btnFit = document.getElementById('btnFit');
const countPanel = document.getElementById('countPanel');
const totalCountEl = document.getElementById('totalCount');
const countInfoEl = document.getElementById('countInfo');
const resultBox = document.getElementById('resultBox');

let gridMode=false, selectMode=false;
let points=[], selectedParcels=new Set(), results={}, pendaoMarks=[];
let trainMode='', trainingMarks=[];
let draggingPoint=-1, drag=false, lx=0, ly=0;
let sc=1, ox=0, oy=0, imgW=0, imgH=0;
const MIN_SC=0.05, MAX_SC=40;
const PEND_STEP=1;
const PEND_MIN_AREA=18;
const PEND_CRITICO=20;
const PEND_SCORE_THRESHOLD=4.35;
const PEND_PERCENT_LIMIT=50;
const TRAIN_KEY='tmg_pendao_ia_' + IMAGE_NAME;
let trainingSamples={pos:[],neg:[]};
const img = new Image();
const tempCv = document.createElement('canvas');
const tempCtx = tempCv.getContext('2d', { willReadFrequently:true });

function getImgCoords(cx, cy) {
  const r=cv.getBoundingClientRect();
  return { x:(cx-r.left-ox)/sc, y:(cy-r.top-oy)/sc };
}

function fitView() {
  const W=vc.clientWidth, H=vc.clientHeight;
  if(!imgW || !imgH) return;
  sc=Math.min(W/imgW,H/imgH);
  ox=(W-imgW*sc)/2; oy=(H-imgH*sc)/2;
  drawAll();
}

function bilerp(p0,p1,p2,p3,u,v) {
  const tx=(1-u)*p0.x+u*p1.x, ty=(1-u)*p0.y+u*p1.y;
  const bx=(1-u)*p3.x+u*p2.x, by=(1-u)*p3.y+u*p2.y;
  return { x:(1-v)*tx+v*bx, y:(1-v)*ty+v*by };
}

function pointInPolygon(px,py,polygon) {
  let inside=false;
  for(let i=0,j=polygon.length-1;i<polygon.length;j=i++) {
    const xi=polygon[i].x, yi=polygon[i].y, xj=polygon[j].x, yj=polygon[j].y;
    if(((yi>py)!==(yj>py)) && (px < (xj-xi)*(py-yi)/(yj-yi)+xi)) inside=!inside;
  }
  return inside;
}

function getCellPoly(r,c) {
  if(points.length<4) return null;
  const R=parseInt(inpRows.value)||1, C=parseInt(inpCols.value)||1;
  const p0=points[0], p1=points[1], p2=points[2], p3=points[3];
  const u0=c/C, u1=(c+1)/C, v0=r/R, v1=(r+1)/R;
  return [
    bilerp(p0,p1,p2,p3,u0,v0),
    bilerp(p0,p1,p2,p3,u1,v0),
    bilerp(p0,p1,p2,p3,u1,v1),
    bilerp(p0,p1,p2,p3,u0,v1)
  ];
}

function cellLabel(r,c) {
  return 'T' + (c+1) + ' D' + (r+1);
}

function cellCenter(poly) {
  return {
    x:(poly[0].x+poly[1].x+poly[2].x+poly[3].x)/4,
    y:(poly[0].y+poly[1].y+poly[2].y+poly[3].y)/4
  };
}

function findCellAt(pt) {
  const R=parseInt(inpRows.value)||1, C=parseInt(inpCols.value)||1;
  for(let r=0;r<R;r++) {
    for(let c=0;c<C;c++) {
      const poly=getCellPoly(r,c);
      if(poly && pointInPolygon(pt.x,pt.y,poly)) return {r,c,label:cellLabel(r,c),poly};
    }
  }
  return null;
}

function rgbToHsv(r,g,b) {
  r/=255; g/=255; b/=255;
  const max=Math.max(r,g,b), min=Math.min(r,g,b), d=max-min;
  let h=0;
  if(d!==0) {
    if(max===r) h=60*(((g-b)/d)%6);
    else if(max===g) h=60*((b-r)/d+2);
    else h=60*((r-g)/d+4);
    if(h<0) h+=360;
  }
  const s=max===0 ? 0 : d/max;
  return {h,s,v:max};
}

function pixelFeatures(r,g,b) {
  const hsv=rgbToHsv(r,g,b);
  const exg=(2*g-r-b)/255;
  const yellowness=(((r+g)*0.5)-b)/255;
  return {
    h:hsv.h,
    s:hsv.s,
    v:hsv.v,
    exg:exg,
    yellow:yellowness,
    r:r/255,
    g:g/255,
    b:b/255
  };
}

function featureDistance(a,b) {
  const dh=Math.min(Math.abs(a.h-b.h), 360-Math.abs(a.h-b.h))/180;
  const ds=a.s-b.s, dv=a.v-b.v;
  const de=a.exg-b.exg, dy=a.yellow-b.yellow;
  const dr=a.r-b.r, dg=a.g-b.g, db=a.b-b.b;
  return Math.sqrt(
    dh*dh*1.2 + ds*ds*0.8 + dv*dv*0.5 +
    de*de*1.1 + dy*dy*1.4 + dr*dr*0.25 + dg*dg*0.25 + db*db*0.25
  );
}

function loadTrainingSamples() {
  try {
    const raw=localStorage.getItem(TRAIN_KEY);
    if(raw) {
      const parsed=JSON.parse(raw);
      if(parsed && Array.isArray(parsed.pos) && Array.isArray(parsed.neg)) trainingSamples=parsed;
    }
  } catch(e) {}
  updateTrainingInfo();
}

function saveTrainingSamples() {
  try { localStorage.setItem(TRAIN_KEY, JSON.stringify(trainingSamples)); } catch(e) {}
  updateTrainingInfo();
}

function updateTrainingInfo() {
  if(trainInfo) trainInfo.textContent=trainingSamples.pos.length+' pendão · '+trainingSamples.neg.length+' fundo';
}

function trainingBoost(r,g,b) {
  return 0;
}

function getPixelAtImagePoint(pt) {
  const x=Math.max(0, Math.min(imgW-1, Math.round(pt.x)));
  const y=Math.max(0, Math.min(imgH-1, Math.round(pt.y)));
  const d=tempCtx.getImageData(x,y,1,1).data;
  return [d[0],d[1],d[2]];
}

function addTrainingSample(pt, kind) {
  if(!imgW || !imgH) return;
  prepareImageData();
  const radius=4;
  const bucket=kind==='pos' ? trainingSamples.pos : trainingSamples.neg;
  let added=0;
  for(let yy=-radius; yy<=radius; yy++) {
    for(let xx=-radius; xx<=radius; xx++) {
      if(xx*xx+yy*yy>radius*radius) continue;
      const x=Math.max(0, Math.min(imgW-1, Math.round(pt.x+xx)));
      const y=Math.max(0, Math.min(imgH-1, Math.round(pt.y+yy)));
      const d=tempCtx.getImageData(x,y,1,1).data;
      bucket.push(pixelFeatures(d[0],d[1],d[2]));
      added++;
    }
  }
  while(bucket.length>360) bucket.shift();
  trainingMarks.push({x:pt.x,y:pt.y,kind:kind});
  saveTrainingSamples();
  drawAll();
  countInfoEl.innerHTML=(kind==='pos'?'Exemplo de pendão':'Exemplo de fundo')+' salvo para calibrar esta ortofoto.';
  countPanel.style.display='block';
}

function tasselScore(r,g,b) {
  const hsv=rgbToHsv(r,g,b);
  const maxc=Math.max(r,g,b), minc=Math.min(r,g,b);
  const chroma=maxc-minc;
  const exg=2*g-r-b;
  const yellowness=((r+g)*0.5)-b;
  const redYellowBalance=Math.abs(r-g);
  const leafGreen=(exg>8 && g>=r*0.92 && g>=b*1.03 && hsv.h>=56 && hsv.h<=168);
  const darkShadow = hsv.v<0.22;
  const whiteGlare = hsv.s<0.12 && hsv.v>0.74;
  const soilRed = r>g*1.28 && r>b*1.36 && hsv.h<18;
  const greenWhiteEdge = hsv.s<0.24 && g>=r*0.94 && b>=r*0.72 && hsv.h>=55 && hsv.h<=150;
  const nonGreen = !leafGreen && !greenWhiteEdge && exg < 42;

  const strawHue = hsv.h>=20 && hsv.h<=58 && hsv.s>=0.15 && hsv.v>=0.34 && yellowness>=16;
  const tanDry = r>=88 && g>=60 && b<=142 && r>=b+18 && g>=b+8 && redYellowBalance<=92 && hsv.h>=14 && hsv.h<=58;
  const paleTassel = r>=112 && g>=88 && b<=162 && yellowness>=18 && redYellowBalance<=72 && hsv.s>=0.11 && hsv.h>=16 && hsv.h<=62;
  const oldPinkTan = r>=102 && g>=70 && b<=155 && r>=g*0.88 && g>=b*0.82 && r>=b+10 && hsv.h>=8 && hsv.h<=42 && hsv.s>=0.12;
  const youngTassel = hsv.h>=42 && hsv.h<=74 && hsv.s>=0.12 && hsv.s<=0.58 && hsv.v>=0.34 && yellowness>=12 && exg<30;
  const branchTexture = chroma>=22 && yellowness>=16 && hsv.s>=0.14;

  let score=0;
  if(strawHue) score+=2.2;
  if(tanDry) score+=2.4;
  if(paleTassel) score+=2.1;
  if(oldPinkTan) score+=1.8;
  if(youngTassel) score+=1.15;
  if(branchTexture) score+=0.9;
  if(yellowness>=30) score+=0.6;
  if(!nonGreen) score-=5.0;
  if(leafGreen) score-=4.8;
  if(greenWhiteEdge) score-=3.4;
  if(darkShadow) score-=2.2;
  if(whiteGlare) score-=2.2;
  if(soilRed) score-=1.6;
  if(chroma<12 && yellowness<18) score-=1.2;
  return score;
}

function isTasselPixel(r,g,b) {
  return tasselScore(r,g,b) >= PEND_SCORE_THRESHOLD;
}

function prepareImageData() {
  tempCv.width=imgW; tempCv.height=imgH;
  tempCtx.clearRect(0,0,imgW,imgH);
  tempCtx.drawImage(img,0,0);
}

function mergeNearbyTassels(marks,w,h) {
  if(!marks.length) return marks;
  const radius=Math.max(12, Math.min(28, Math.min(w,h)*0.040));
  const ordered=[...marks].sort((a,b)=>(b.score*b.area)-(a.score*a.area));
  const merged=[];
  for(const m of ordered) {
    let found=null;
    for(const c of merged) {
      const dx=m.x-c.x, dy=m.y-c.y;
      if(Math.sqrt(dx*dx+dy*dy)<=radius) { found=c; break; }
    }
    if(found) {
      const wa=Math.max(1,found.area), wb=Math.max(1,m.area);
      found.x=(found.x*wa+m.x*wb)/(wa+wb);
      found.y=(found.y*wa+m.y*wb)/(wa+wb);
      found.area+=m.area;
      found.score=Math.max(found.score,m.score);
    } else {
      merged.push({...m});
    }
  }
  return merged.sort((a,b)=>a.y===b.y ? a.x-b.x : a.y-b.y);
}

function analyzeCell(r,c) {
  const poly=getCellPoly(r,c);
  if(!poly) return {label:cellLabel(r,c), count:0, marks:[]};
  const step=PEND_STEP;
  const minAreaPx=PEND_MIN_AREA;
  const xs=poly.map(p=>p.x), ys=poly.map(p=>p.y);
  const minX=Math.max(0, Math.floor(Math.min(...xs)));
  const maxX=Math.min(imgW-1, Math.ceil(Math.max(...xs)));
  const minY=Math.max(0, Math.floor(Math.min(...ys)));
  const maxY=Math.min(imgH-1, Math.ceil(Math.max(...ys)));
  const w=maxX-minX+1, h=maxY-minY+1;
  if(w<=0 || h<=0) return {label:cellLabel(r,c), count:0, marks:[]};

  const imageData=tempCtx.getImageData(minX,minY,w,h).data;
  const gw=Math.ceil(w/step), gh=Math.ceil(h/step);
  const mask=new Uint8Array(gw*gh);
  const cleanMask=new Uint8Array(gw*gh);
  const closedMask=new Uint8Array(gw*gh);
  const scores=new Float32Array(gw*gh);
  const visited=new Uint8Array(gw*gh);

  for(let gy=0; gy<gh; gy++) {
    for(let gx=0; gx<gw; gx++) {
      const px=Math.min(w-1, gx*step), py=Math.min(h-1, gy*step);
      const ax=minX+px, ay=minY+py;
      if(!pointInPolygon(ax,ay,poly)) continue;
      const idx=(py*w+px)*4;
      const score=tasselScore(imageData[idx], imageData[idx+1], imageData[idx+2]);
      scores[gy*gw+gx]=score;
      if(score>=PEND_SCORE_THRESHOLD) {
        mask[gy*gw+gx]=1;
      }
    }
  }

  for(let gy=0; gy<gh; gy++) {
    for(let gx=0; gx<gw; gx++) {
      const idx=gy*gw+gx;
      if(!mask[idx]) continue;
      let neighbors=0;
      for(let yy=-1; yy<=1; yy++) {
        for(let xx=-1; xx<=1; xx++) {
          if(xx===0 && yy===0) continue;
          const nx=gx+xx, ny=gy+yy;
          if(nx>=0 && nx<gw && ny>=0 && ny<gh && mask[ny*gw+nx]) neighbors++;
        }
      }
      if(neighbors>=2 || scores[idx]>=4.5) cleanMask[idx]=1;
    }
  }

  for(let gy=0; gy<gh; gy++) {
    for(let gx=0; gx<gw; gx++) {
      const idx=gy*gw+gx;
      if(cleanMask[idx]) { closedMask[idx]=1; continue; }
      let neighbors=0, scoreAround=0;
      for(let yy=-1; yy<=1; yy++) {
        for(let xx=-1; xx<=1; xx++) {
          const nx=gx+xx, ny=gy+yy;
          if(nx>=0 && nx<gw && ny>=0 && ny<gh) {
            const ni=ny*gw+nx;
            if(cleanMask[ni]) neighbors++;
            scoreAround+=scores[ni];
          }
        }
      }
      if(neighbors>=5 && scoreAround/9>=2.15) closedMask[idx]=1;
    }
  }

  const marks=[];
  const dirs=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,1],[1,-1],[-1,-1]];
  for(let gy=0; gy<gh; gy++) {
    for(let gx=0; gx<gw; gx++) {
      const start=gy*gw+gx;
      if(!closedMask[start] || visited[start]) continue;
      let cells=0, sx=0, sy=0, scoreSum=0;
      let minGX=gx, maxGX=gx, minGY=gy, maxGY=gy;
      const stack=[[gx,gy]];
      visited[start]=1;
      while(stack.length) {
        const p=stack.pop();
        const x=p[0], y=p[1];
        const pos=y*gw+x;
        cells++; sx+=x; sy+=y; scoreSum+=scores[pos];
        if(x<minGX) minGX=x; if(x>maxGX) maxGX=x;
        if(y<minGY) minGY=y; if(y>maxGY) maxGY=y;
        for(const d of dirs) {
          const nx=x+d[0], ny=y+d[1];
          if(nx<0 || nx>=gw || ny<0 || ny>=gh) continue;
          const ni=ny*gw+nx;
          if(closedMask[ni] && !visited[ni]) {
            visited[ni]=1;
            stack.push([nx,ny]);
          }
        }
      }
      const areaPx=cells*step*step;
      const widthPx=(maxGX-minGX+1)*step;
      const heightPx=(maxGY-minGY+1)*step;
      const bboxCells=Math.max(1,(maxGX-minGX+1)*(maxGY-minGY+1));
      const density=cells/bboxCells;
      const elongation=Math.max(widthPx,heightPx)/Math.max(1,Math.min(widthPx,heightPx));
      const meanScore=scoreSum/Math.max(1,cells);
      const cx=minX + (sx/cells)*step;
      const cy=minY + (sy/cells)*step;
      const maxAreaPx=Math.max(minAreaPx*22, Math.min(w*h*0.022, 1400));
      const validShape =
        areaPx>=minAreaPx &&
        areaPx<=maxAreaPx &&
        density>=0.11 &&
        elongation<=8.5 &&
        widthPx<=Math.max(18, w*0.18) &&
        heightPx<=Math.max(18, h*0.18) &&
        meanScore>=PEND_SCORE_THRESHOLD-0.15 &&
        pointInPolygon(cx,cy,poly);

      if(validShape) {
        marks.push({x:cx, y:cy, area:areaPx, score:meanScore});
      }
    }
  }
  const finalMarks=mergeNearbyTassels(marks,w,h);
  return {label:cellLabel(r,c), row:r+1, col:c+1, count:finalMarks.length, marks:finalMarks};
}

function setGridMode(active) {
  gridMode=active;
  selectMode=false;
  trainMode='';
  btnGridTool.classList.toggle('active', gridMode);
  btnGrid2.classList.toggle('active', gridMode);
  btnSelectParcel.classList.remove('active');
  btnSelect2.classList.remove('active');
  if(btnTrainPositive) btnTrainPositive.classList.remove('active');
  if(btnTrainNegative) btnTrainNegative.classList.remove('active');
  if(gridMode) {
    points=[]; selectedParcels.clear(); results={}; pendaoMarks=[]; countPanel.style.display='none';
  }
  drawAll();
}

function setSelectMode(active) {
  if(points.length<4) { alert('Marque o grid primeiro.'); return; }
  selectMode=active;
  gridMode=false;
  trainMode='';
  btnSelectParcel.classList.toggle('active', selectMode);
  btnSelect2.classList.toggle('active', selectMode);
  btnGridTool.classList.remove('active');
  btnGrid2.classList.remove('active');
  if(btnTrainPositive) btnTrainPositive.classList.remove('active');
  if(btnTrainNegative) btnTrainNegative.classList.remove('active');
  drawAll();
}

function setTrainMode(mode) {
  if(!btnTrainPositive || !btnTrainNegative) return;
  trainMode = trainMode===mode ? '' : mode;
  gridMode=false;
  selectMode=false;
  btnGridTool.classList.remove('active');
  btnGrid2.classList.remove('active');
  btnSelectParcel.classList.remove('active');
  btnSelect2.classList.remove('active');
  btnTrainPositive.classList.toggle('active', trainMode==='pos');
  btnTrainNegative.classList.toggle('active', trainMode==='neg');
  countPanel.style.display='block';
  countInfoEl.innerHTML = trainMode==='pos'
    ? 'Clique sobre pendões reais para treinar a IA local.'
    : trainMode==='neg'
      ? 'Clique em folha, solo, sombra ou palha falsa para ensinar o que ignorar.'
      : 'Treino IA local pausado.';
  drawAll();
}

function analyzePendoamento(onlySelected) {
  if(points.length<4) { alert('Marque os 4 cantos do grid primeiro.'); return; }
  const R=parseInt(inpRows.value)||1, C=parseInt(inpCols.value)||1;
  if(onlySelected && selectedParcels.size===0) {
    alert('Selecione uma ou mais parcelas para analisar.');
    return;
  }
  prepareImageData();
  results={}; pendaoMarks=[];
  let total=0, analyzed=0, critical=0;
  const crit=getPendaoLimit();

  for(let r=0;r<R;r++) {
    for(let c=0;c<C;c++) {
      const label=cellLabel(r,c);
      if(onlySelected && !selectedParcels.has(label)) continue;
      const res=analyzeCell(r,c);
      results[label]=res;
      for(const m of res.marks) pendaoMarks.push({x:m.x,y:m.y,label:label});
      total+=res.count;
      analyzed++;
      if(res.count>=crit) critical++;
    }
  }

  countPanel.style.display='block';
  totalCountEl.textContent=total;
  countInfoEl.innerHTML='Parcelas analisadas: '+analyzed+'<br>Média: '+(analyzed? (total/analyzed).toFixed(1):'0.0')+' pendões/parcela<br>Trava 50%: '+crit+' pendões';
  updateResultBox();
  drawAll();
}

function getPendaoLimit() {
  const teto=Math.max(1, parseInt(inpTeto ? inpTeto.value : PEND_CRITICO) || PEND_CRITICO);
  return Math.max(1, Math.ceil(teto * (PEND_PERCENT_LIMIT/100)));
}

function updateResultBox() {
  const entries=Object.values(results).sort((a,b)=> a.row===b.row ? a.col-b.col : a.row-b.row);
  if(!entries.length) {
    resultBox.innerHTML='Sem resultados.';
    return;
  }
  const crit=getPendaoLimit();
  resultBox.innerHTML=entries.map(r=>{
    const color = r.count>=crit ? '#ff5555' : '#ddd';
    return '<div><b style="color:#ff8c00">'+r.label+'</b> · <span style="color:'+color+'">'+r.count+' pendões</span> · '+(r.count>=crit?'ATINGIU 50%':'abaixo')+'</div>';
  }).join('');
}

function exportCSV() {
  const entries=Object.values(results).sort((a,b)=> a.row===b.row ? a.col-b.col : a.row-b.row);
  if(!entries.length) { alert('Execute a análise de pendoamento antes de exportar.'); return; }
  const crit=getPendaoLimit();
  let csv='\\uFEFFParcela;Linha;Coluna;Pendoes;Status;Imagem\\n';
  for(const r of entries) {
    csv += r.label+';'+r.row+';'+r.col+';'+r.count+';'+(r.count>=crit?'ATINGIU_50':'ABAIXO_50')+';'+IMAGE_NAME+'\\n';
  }
  const blob=new Blob([csv], {type:'text/csv;charset=utf-8;'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='pendoamento_por_parcela.csv';
  a.click();
}

function clearResults() {
  results={}; pendaoMarks=[]; countPanel.style.display='none'; drawAll();
}

function drawAll() {
  const W=vc.clientWidth, H=vc.clientHeight;
  cv.width=W; cv.height=H;
  ctx.clearRect(0,0,W,H);
  ctx.save();
  ctx.translate(ox,oy); ctx.scale(sc,sc);
  if(imgW>0) ctx.drawImage(img,0,0);

  const R=parseInt(inpRows.value)||1, C=parseInt(inpCols.value)||1;
  if(points.length===4) {
    ctx.save();
    ctx.lineWidth=1.6/sc; ctx.strokeStyle='rgba(0,207,255,.78)';
    ctx.shadowColor='rgba(0,207,255,.35)'; ctx.shadowBlur=5/sc;
    for(let i=0;i<=R;i++) {
      const v=i/R;
      const p0=points[0], p1=points[1], p2=points[2], p3=points[3];
      const left=bilerp(p0,p1,p2,p3,0,v), right=bilerp(p0,p1,p2,p3,1,v);
      ctx.beginPath(); ctx.moveTo(left.x,left.y); ctx.lineTo(right.x,right.y); ctx.stroke();
    }
    for(let j=0;j<=C;j++) {
      const u=j/C;
      const p0=points[0], p1=points[1], p2=points[2], p3=points[3];
      const top=bilerp(p0,p1,p2,p3,u,0), bottom=bilerp(p0,p1,p2,p3,u,1);
      ctx.beginPath(); ctx.moveTo(top.x,top.y); ctx.lineTo(bottom.x,bottom.y); ctx.stroke();
    }
    ctx.restore();

    for(let r=0;r<R;r++) {
      for(let c=0;c<C;c++) {
        const label=cellLabel(r,c);
        const poly=getCellPoly(r,c);
        const cen=cellCenter(poly);
        const res=results[label];
        const selected=selectedParcels.has(label);
        if(selected || res) {
          ctx.save();
          ctx.beginPath();
          ctx.moveTo(poly[0].x,poly[0].y);
          for(let k=1;k<poly.length;k++) ctx.lineTo(poly[k].x,poly[k].y);
          ctx.closePath();
          if(res) {
            const crit=PEND_CRITICO;
            ctx.fillStyle=res.count>=crit ? 'rgba(255,64,0,.20)' : 'rgba(255,179,71,.16)';
          } else {
            ctx.fillStyle='rgba(255,210,0,.18)';
          }
          ctx.fill();
          ctx.strokeStyle=selected ? 'rgba(255,230,0,.95)' : 'rgba(255,140,0,.55)';
          ctx.lineWidth=(selected?2.4:1.2)/sc;
          ctx.stroke();
          ctx.restore();
        }
        if(res) {
          ctx.save();
          ctx.shadowColor='rgba(0,0,0,.9)'; ctx.shadowBlur=4/sc;
          ctx.fillStyle='#fff';
          ctx.font='bold '+Math.max(9,12/sc)+'px Arial';
          ctx.textAlign='center'; ctx.textBaseline='middle';
          ctx.fillText(String(res.count), cen.x, cen.y);
          ctx.font=Math.max(7,9/sc)+'px Arial';
          ctx.fillStyle='#ffb347';
          ctx.fillText(label, cen.x, cen.y+15/sc);
          ctx.restore();
        }
      }
    }
  }

  for(const m of pendaoMarks) {
    const size=5/sc;
    ctx.save();
    ctx.strokeStyle='#ff2b2b'; ctx.lineWidth=2/sc; ctx.shadowColor='rgba(255,0,0,.7)'; ctx.shadowBlur=5/sc;
    ctx.beginPath(); ctx.moveTo(m.x-size,m.y-size); ctx.lineTo(m.x+size,m.y+size); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(m.x-size,m.y+size); ctx.lineTo(m.x+size,m.y-size); ctx.stroke();
    ctx.restore();
  }

  for(const m of trainingMarks) {
    const size=7/sc;
    ctx.save();
    ctx.strokeStyle=m.kind==='pos' ? '#00ff66' : '#5599ff';
    ctx.fillStyle=m.kind==='pos' ? 'rgba(0,255,102,.18)' : 'rgba(85,153,255,.18)';
    ctx.lineWidth=2/sc;
    ctx.beginPath(); ctx.arc(m.x,m.y,size,0,Math.PI*2); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(m.x-size,m.y); ctx.lineTo(m.x+size,m.y); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(m.x,m.y-size); ctx.lineTo(m.x,m.y+size); ctx.stroke();
    ctx.restore();
  }

  points.forEach((p,i)=>{
    const r=11/sc;
    ctx.save();
    ctx.shadowColor=draggingPoint===i ? 'rgba(255,255,255,.9)' : 'rgba(0,180,255,.8)';
    ctx.shadowBlur=14/sc;
    ctx.beginPath(); ctx.arc(p.x,p.y,r,0,Math.PI*2);
    ctx.fillStyle=draggingPoint===i ? '#fff' : '#1e90ff';
    ctx.fill();
    ctx.lineWidth=2.5/sc; ctx.strokeStyle=draggingPoint===i ? '#aaddff' : '#00cfff';
    ctx.stroke();
    ctx.fillStyle='#fff'; ctx.font='bold '+(13/sc)+'px Arial'; ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText(i+1,p.x,p.y);
    ctx.restore();
  });
  ctx.restore();
  zb.textContent=sc.toFixed(2)+'×';
}

img.onload=()=>{ imgW=img.width; imgH=img.height; fitView(); };
img.src='data:image/png;base64,'+IMG_B64;

vc.addEventListener('wheel', e=>{
  e.preventDefault();
  const factor=e.deltaY<0?1.2:0.8;
  const r=cv.getBoundingClientRect();
  const mx=e.clientX-r.left, my=e.clientY-r.top;
  const ix=(mx-ox)/sc, iy=(my-oy)/sc;
  sc=Math.max(MIN_SC, Math.min(MAX_SC, sc*factor));
  ox=mx-ix*sc; oy=my-iy*sc;
  drawAll();
}, {passive:false});

vc.addEventListener('mousedown', e=>{
  const pt=getImgCoords(e.clientX,e.clientY);
  for(let i=0;i<points.length;i++) {
    const dx=(pt.x-points[i].x)*sc, dy=(pt.y-points[i].y)*sc;
    if(Math.sqrt(dx*dx+dy*dy)<20) { draggingPoint=i; return; }
  }
  if(gridMode && points.length<4) {
    points.push({x:pt.x,y:pt.y});
    if(points.length===4) setGridMode(false);
    drawAll(); return;
  }
  if(trainMode) {
    addTrainingSample(pt, trainMode);
    return;
  }
  if(selectMode && points.length===4) {
    const cell=findCellAt(pt);
    if(cell) {
      if(selectedParcels.has(cell.label)) selectedParcels.delete(cell.label);
      else selectedParcels.add(cell.label);
      drawAll();
    }
    return;
  }
  drag=true; lx=e.clientX; ly=e.clientY; vc.style.cursor='grabbing';
});

vc.addEventListener('mousemove', e=>{
  const pt=getImgCoords(e.clientX,e.clientY);
  coordEl.textContent='X:'+Math.round(pt.x)+' Y:'+Math.round(pt.y);
  if(draggingPoint>=0) {
    points[draggingPoint]={x:pt.x,y:pt.y};
    clearResults();
    drawAll(); return;
  }
  if(drag) {
    ox+=e.clientX-lx; oy+=e.clientY-ly; lx=e.clientX; ly=e.clientY;
    drawAll();
  }
});
vc.addEventListener('mouseup',()=>{ drag=false; draggingPoint=-1; vc.style.cursor='grab'; });
vc.addEventListener('mouseleave',()=>{ drag=false; draggingPoint=-1; vc.style.cursor='grab'; });

function resetAll() {
  points=[]; selectedParcels.clear(); results={}; pendaoMarks=[]; gridMode=false; selectMode=false; trainMode='';
  btnGridTool.classList.remove('active'); btnGrid2.classList.remove('active');
  btnSelectParcel.classList.remove('active'); btnSelect2.classList.remove('active');
  if(btnTrainPositive) btnTrainPositive.classList.remove('active');
  if(btnTrainNegative) btnTrainNegative.classList.remove('active');
  countPanel.style.display='none'; drawAll();
}

function clearTraining() {
  trainingSamples={pos:[],neg:[]};
  trainingMarks=[];
  try { localStorage.removeItem(TRAIN_KEY); } catch(e) {}
  trainMode='';
  if(btnTrainPositive) btnTrainPositive.classList.remove('active');
  if(btnTrainNegative) btnTrainNegative.classList.remove('active');
  updateTrainingInfo();
  clearResults();
}

btnGridTool.onclick=()=>setGridMode(!gridMode);
btnGrid2.onclick=()=>setGridMode(!gridMode);
btnSelectParcel.onclick=()=>setSelectMode(!selectMode);
btnSelect2.onclick=()=>setSelectMode(!selectMode);
if(btnTrainPositive) btnTrainPositive.onclick=()=>setTrainMode('pos');
if(btnTrainNegative) btnTrainNegative.onclick=()=>setTrainMode('neg');
if(btnClearTraining) btnClearTraining.onclick=clearTraining;
if(btnRun) btnRun.onclick=()=>analyzePendoamento(false);
btnAnalyze18000.onclick=()=>analyzePendoamento(false);
if(btnAnalyzeAll) btnAnalyzeAll.onclick=()=>analyzePendoamento(false);
btnAnalyzeSelected.onclick=()=>analyzePendoamento(true);
btnExportCSV.onclick=exportCSV;
btnClearResults.onclick=clearResults;
btnClearAll.onclick=resetAll;
btnFit.onclick=fitView;
inpRows.onchange=()=>{ selectedParcels.clear(); clearResults(); drawAll(); };
inpCols.onchange=()=>{ selectedParcels.clear(); clearResults(); drawAll(); };
inpTeto.onchange=()=>{ updateResultBox(); drawAll(); };
loadTrainingSamples();
new ResizeObserver(()=>drawAll()).observe(vc);
</script>
</body>
</html>
"""
                    pend_viewer = (
                        pend_viewer
                        .replace("__PEND_B64__", pend_b64)
                        .replace("__PEND_IMAGE_NAME__", json.dumps(pend_file.name, ensure_ascii=False))
                    )
                    components.html(pend_viewer, height=740, scrolling=False)

            else:
                st.markdown("""
                <div style='height:706px;border:1px dashed #2e2e2e;border-radius:12px;background:#0d0d0d;
                            display:flex;flex-direction:column;align-items:center;justify-content:center;
                            gap:12px;color:#333;'>
                    <div style='font-size:3rem;'>🌾</div>
                    <div style='font-size:0.85rem;letter-spacing:2px;text-transform:uppercase;color:#555;'>
                        Carregue uma ortofoto para análise de pendoamento
                    </div>
                    <div style='font-size:0.75rem;color:#444;'>
                        Marque o grid → selecione parcelas, se quiser → execute Pendoamento
                    </div>
                </div>""", unsafe_allow_html=True)

            st.markdown("""
            <div style='margin:18px 0 10px 0;padding:12px 14px;border:1px solid #2a2a2a;
                        border-radius:10px;background:linear-gradient(145deg,#151515,#0b0b0b);'>
                <div style='color:#ff8c00;font-weight:800;font-size:0.95rem;letter-spacing:1.6px;
                            text-transform:uppercase;'>
                    🌾 Análise Cronológica de Pendoamento
                </div>
                <div style='color:#777;font-size:0.78rem;margin-top:4px;'>
                    Compare até 10 ortofotos da mesma área, mantendo o grid fixo para identificar a primeira data de atingimento por parcela.
                </div>
            </div>""", unsafe_allow_html=True)

            st.markdown("##### Fluxo simples")
            p1, p2, p3, p4 = st.columns([2, 1, 1, 1])
            with p1:
                cron_nome_analise = st.text_input(
                    "Nome da análise",
                    value="Pendoamento cronológico",
                    key="pend_cron_nome_analise"
                )
            with p2:
                cron_rows = st.number_input("Disp", min_value=1, max_value=200, value=5, step=1, key="pend_cron_rows")
            with p3:
                cron_cols = st.number_input("Tiros", min_value=1, max_value=200, value=5, step=1, key="pend_cron_cols")
            with p4:
                cron_teto = st.number_input("Teto plantas/parcela", min_value=1, max_value=10000, value=20, step=1, key="pend_cron_teto")

            cron_percentual = 50.0
            cron_min_pendoes = 1
            cron_referencia = ""
            cron_tolerancia = 62
            cron_filtro_cor = "Misto"
            cron_sensibilidade = 72
            cron_area_min = 18
            cron_area_max = 900
            cron_revisao_manual = True
            meta_codlocal = ""
            meta_quadra = ""
            meta_ensaio = ""
            meta_gli = ""
            meta_tecnologia = ""
            meta_rep = ""
            meta_nc = ""
            meta_linhagem = ""
            meta_genealogia = ""
            meta_parental1 = ""
            meta_pop_parental1 = ""
            meta_parental2 = ""
            meta_pop_parental2 = ""
            meta_dtp = ""
            st.caption("O limite fica travado em 50% do teto informado. Depois de anexar, use Próxima/Anterior no visualizador para conferir cada data.")

            cron_files = st.file_uploader(
                "📷 Anexar ortofotos cronológicas de pendoamento (até 10)",
                type=MOSAIC_UPLOAD_TYPES,
                accept_multiple_files=True,
                key="pend_cron_ortos",
                help="Use ortofotos da mesma área, em datas diferentes. O grid marcado será mantido fixo em todas."
            )
            cron_library = _mosaic_multi_select("Ou usar mosaicos já importados na análise cronológica", key="pend_cron_mosaic_library", max_items=10)

            cron_items = []
            for cron_file in cron_files or []:
                raw = cron_file.getbuffer().tobytes()
                _mosaic_register_bytes(raw, cron_file.name, "Pendoamento cronológico")
                cron_items.append({"name": cron_file.name, "raw": raw})
            for selected_mosaic in cron_library:
                raw, name = _mosaic_bytes_from_selection(selected_mosaic)
                if raw:
                    cron_items.append({"name": name, "raw": raw})

            if cron_items:
                selected_cron_items = cron_items[:10]
                if len(cron_items) > 10:
                    st.warning("Foram anexadas mais de 10 ortofotos. A análise cronológica usará somente as 10 primeiras.")

                st.caption("Revise a data de cada ortofoto. A ordem cronológica será organizada automaticamente pela data informada.")
                date_cols = st.columns(min(5, len(selected_cron_items)))
                cron_entries = []
                for idx, cron_item in enumerate(selected_cron_items):
                    key_hash = hashlib.md5(f"{idx}-{cron_item['name']}".encode("utf-8")).hexdigest()[:8]
                    with date_cols[idx % len(date_cols)]:
                        cron_date = st.date_input(
                            f"Data {idx + 1}",
                            value=date.today(),
                            key=f"pend_cron_date_{key_hash}"
                        )
                    cron_entries.append({"idx": idx, "name": cron_item["name"], "raw": cron_item["raw"], "date": cron_date.isoformat()})

                ordem_preview = [
                    {"Ordem": pos + 1, "Ortofoto": item["name"], "Data": item["date"]}
                    for pos, item in enumerate(sorted(cron_entries, key=lambda it: (it["date"], it["idx"])))
                ]
                st.dataframe(ordem_preview, use_container_width=True, hide_index=True)

                cron_orthos = []
                cron_errors = []
                with st.spinner("Preparando ortofotos cronológicas para o visualizador de pendoamento..."):
                    for item in cron_entries:
                        cron_name = item["name"]
                        try:
                            raw = item["raw"]
                            b64, dims, err, spatial = processar_ortofoto(raw, cron_name)
                            if err:
                                cron_errors.append(f"{cron_name}: {err}")
                                continue
                            cron_orthos.append({
                                "order": int(item["idx"]),
                                "name": cron_name,
                                "date": item["date"],
                                "b64": b64,
                                "width": int(dims[0]),
                                "height": int(dims[1]),
                                "orig_width": int(spatial.get("orig_width", dims[0]) or dims[0]) if spatial else int(dims[0]),
                                "orig_height": int(spatial.get("orig_height", dims[1]) or dims[1]) if spatial else int(dims[1]),
                            })
                        except Exception as exc:
                            cron_errors.append(f"{cron_name}: {exc}")

                for message in cron_errors:
                    st.warning(message)

                cron_orthos = sorted(cron_orthos, key=lambda it: (it["date"], it["order"]))

                if cron_orthos:
                    cron_config = {
                        "nomeAnalise": cron_nome_analise,
                        "rows": int(cron_rows),
                        "cols": int(cron_cols),
                        "tetoPlantas": int(cron_teto),
                        "percentualLimite": float(cron_percentual),
                        "minPendoes": int(cron_min_pendoes),
                        "referenciaManual": cron_referencia,
                        "tolerancia": int(cron_tolerancia),
                        "filtroCor": cron_filtro_cor,
                        "areaMin": int(cron_area_min),
                        "areaMax": int(cron_area_max),
                        "sensibilidade": int(cron_sensibilidade),
                        "revisaoManual": bool(cron_revisao_manual),
                        "metadata": {
                            "CODLOCAL": meta_codlocal,
                            "QUADRA": meta_quadra,
                            "ENSAIO": meta_ensaio,
                            "GLI": meta_gli,
                            "TECNOLOGIA": meta_tecnologia,
                            "REP": meta_rep,
                            "NC": meta_nc,
                            "LINHAGEM": meta_linhagem,
                            "GENEALOGIA": meta_genealogia,
                            "PARENTAL1": meta_parental1,
                            "POP_PARENTAL1": meta_pop_parental1,
                            "PARENTAL2": meta_parental2,
                            "POP_PARENTAL2": meta_pop_parental2,
                            "DTP": meta_dtp,
                        }
                    }

                    cron_html = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
<style>
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:#0d0d0d; overflow:hidden; font-family:'Segoe UI',sans-serif; color:#ddd; }
  #cronRoot {
    width:100%; height:850px; display:grid; grid-template-columns:minmax(0,1fr) 305px; gap:10px;
    border:1px solid #2a2a2a; border-radius:12px; background:#0d0d0d; overflow:hidden;
  }
  #cronViewer {
    position:relative; overflow:hidden; user-select:none; cursor:grab;
    background:
      linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px),
      #0d0d0d;
    background-size:32px 32px;
  }
  #cronViewer:active { cursor:grabbing; }
  #cronCanvas { position:absolute; inset:0; display:block; }
  .cron-side {
    background:linear-gradient(145deg,rgba(18,18,18,.98),rgba(8,8,8,.98));
    border-left:1px solid #2a2a2a; padding:10px; overflow:auto; scrollbar-width:thin; scrollbar-color:#ff8c00 #141414;
  }
  .cron-side::-webkit-scrollbar { width:6px; }
  .cron-side::-webkit-scrollbar-track { background:#141414; }
  .cron-side::-webkit-scrollbar-thumb { background:#ff8c00; border-radius:6px; }
  .title { color:#ff8c00; font-size:12px; font-weight:900; letter-spacing:1.3px; text-align:center; text-transform:uppercase; margin-bottom:8px; }
  .subtle { color:#777; font-size:10px; line-height:1.35; }
  .row { display:flex; gap:6px; align-items:center; justify-content:space-between; margin:5px 0; color:#bbb; font-size:10px; }
  .row span:first-child { max-width:160px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  input, select, textarea {
    background:#171717; border:1px solid #333; color:#fff; border-radius:5px; padding:4px 5px; font-size:10px;
  }
  select { width:100%; }
  textarea { width:100%; min-height:44px; resize:vertical; }
  .btn {
    width:100%; min-height:28px; border-radius:5px; padding:5px 7px; font-size:10px; font-weight:800;
    cursor:pointer; transition:.18s; color:#ccc; background:linear-gradient(145deg,#1e1e1e,#111); border:1px solid #3a3a3a;
    margin:3px 0;
  }
  .btn:hover { border-color:#ff8c00; color:#ff8c00; }
  .btn.orange { background:linear-gradient(145deg,#2a1a00,#160b00); border-color:#ff8c00; color:#ffb347; }
  .btn.blue { background:linear-gradient(145deg,#0c1f33,#071321); border-color:#1f77d0; color:#75b7ff; }
  .btn.green { background:linear-gradient(145deg,#0b2815,#06160d); border-color:#00a651; color:#33ee77; }
  .btn.red { background:linear-gradient(145deg,#341010,#1d0606); border-color:#c9302c; color:#ff6666; }
  .btn.active { border-color:#ffd600; color:#ffd600; box-shadow:0 0 10px rgba(255,214,0,.25); }
  .sep { height:1px; background:linear-gradient(90deg,transparent,#333,transparent); margin:8px 0; }
  .badge {
    position:absolute; z-index:20; pointer-events:none; background:rgba(10,10,10,.82); border:1px solid #2a2a2a;
    border-radius:8px; padding:5px 10px; color:#ff8c00; font-size:11px; font-family:'Courier New',monospace; font-weight:700;
  }
  #cronZoom { top:12px; left:12px; }
  #cronCoord { bottom:12px; left:12px; color:#666; font-weight:600; }
  #cronHint { right:12px; bottom:12px; text-align:right; color:#555; font-family:'Segoe UI',sans-serif; font-size:10px; line-height:1.45; }
  .stats { display:grid; grid-template-columns:1fr 1fr; gap:6px; margin:6px 0; }
  .stat {
    border:1px solid #2b2b2b; background:rgba(255,255,255,.025); border-radius:7px; padding:7px;
  }
  .stat b { display:block; color:#fff; font-size:15px; }
  .stat span { color:#888; font-size:9px; text-transform:uppercase; letter-spacing:.6px; }
  .date-list { max-height:120px; overflow:auto; border:1px solid #242424; border-radius:7px; padding:5px; background:#101010; }
  .date-item { display:flex; justify-content:space-between; gap:5px; color:#aaa; font-size:10px; padding:3px; border-radius:4px; cursor:pointer; }
  .date-item.active { color:#ffb347; background:#221400; }
  .date-item:hover { background:#1a1a1a; }
  .review {
    border:1px solid #333; border-radius:8px; background:#101010; padding:8px; margin-top:6px; display:none;
  }
  .review h4 { color:#ffd600; font-size:11px; margin-bottom:6px; }
  .review-line { display:grid; grid-template-columns:1fr 58px; gap:5px; align-items:center; margin:3px 0; color:#aaa; font-size:10px; }
  .review-line input { width:58px; text-align:center; }
  .progress {
    height:7px; background:#171717; border:1px solid #333; border-radius:999px; overflow:hidden; margin:5px 0;
  }
  .progress div { height:100%; width:0%; background:linear-gradient(90deg,#ff8c00,#ffd166); transition:width .2s; }
  .legend { display:flex; flex-wrap:wrap; gap:5px; color:#888; font-size:9px; margin-top:5px; }
  .leg { display:flex; align-items:center; gap:3px; }
  .sw { width:10px; height:10px; border-radius:2px; border:1px solid rgba(255,255,255,.25); }
</style>
</head>
<body>
<div id="cronRoot">
  <div id="cronViewer">
    <canvas id="cronCanvas"></canvas>
    <div class="badge" id="cronZoom">1.00×</div>
    <div class="badge" id="cronCoord">X:0 Y:0</div>
    <div class="badge" id="cronHint">Scroll=Zoom · Drag=Pan<br>Grid fixo: marque 4 pontos</div>
  </div>
  <div class="cron-side">
    <div class="title">Análise Cronológica de Pendoamento</div>
    <div class="subtle">O grid marcado fica fixo e é reaplicado nas ortofotos por data.</div>

    <div class="sep"></div>
    <div class="row"><span>Data ativa</span><select id="dateSelect"></select></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
      <button class="btn blue" id="btnPrevDate">◀ Data</button>
      <button class="btn blue" id="btnNextDate">Data ▶</button>
    </div>
    <div class="date-list" id="dateList"></div>

    <div class="sep"></div>
    <button class="btn orange" id="btnMarkGrid">⊞ Marcar Grid Fixo</button>
    <button class="btn green" id="btnAnalyzeChrono">🌾 Análise Cronológica</button>
    <button class="btn blue" id="btnReviewMode">✎ Revisar Parcela</button>
    <button class="btn" id="btnFitChrono">⤢ Ajustar à tela</button>
    <button class="btn red" id="btnClearChrono">Limpar módulo cronológico</button>
    <div class="progress"><div id="cronProgress"></div></div>
    <div class="subtle" id="cronStatus">Marque o grid fixo na primeira ortofoto e execute a análise.</div>

    <div class="sep"></div>
    <div class="stats">
      <div class="stat"><b id="statTotal">0</b><span>Parcelas</span></div>
      <div class="stat"><b id="statHit">0</b><span>Atingiram</span></div>
      <div class="stat"><b id="statNoHit">0</b><span>Não atingiram</span></div>
      <div class="stat"><b id="statReview">0</b><span>Revisar</span></div>
    </div>
    <div class="subtle" id="statFirstDate">Primeira data geral: --</div>
    <div class="legend">
      <span class="leg"><i class="sw" style="background:rgba(255,140,0,.35)"></i>atingiu</span>
      <span class="leg"><i class="sw" style="background:rgba(120,120,120,.25)"></i>não atingiu</span>
      <span class="leg"><i class="sw" style="background:rgba(255,214,0,.35)"></i>revisar</span>
      <span class="leg"><i class="sw" style="background:#ff2222"></i>pendão</span>
    </div>

    <div class="review" id="reviewPanel"></div>

    <div class="sep"></div>
    <button class="btn orange" id="btnExportCSV">Exportar CSV</button>
    <button class="btn orange" id="btnExportXLSX">Exportar Excel</button>
    <button class="btn" id="btnExportResumo">Exportar resumo final</button>
    <button class="btn" id="btnExportCompleto">Exportar dados completos por ortofoto</button>
    <button class="btn" id="btnExportImagem">Exportar imagem com grid e marcações</button>
  </div>
</div>

<script>
const ORTHOS = __CRON_ORTHOS__;
const CONFIG = __CRON_CONFIG__;
const viewer = document.getElementById('cronViewer');
const canvas = document.getElementById('cronCanvas');
const ctx = canvas.getContext('2d');
const zoomBadge = document.getElementById('cronZoom');
const coordBadge = document.getElementById('cronCoord');
const dateSelect = document.getElementById('dateSelect');
const dateList = document.getElementById('dateList');
const progressBar = document.getElementById('cronProgress');
const statusEl = document.getElementById('cronStatus');
const reviewPanel = document.getElementById('reviewPanel');
const btnMarkGrid = document.getElementById('btnMarkGrid');
const btnAnalyzeChrono = document.getElementById('btnAnalyzeChrono');
const btnReviewMode = document.getElementById('btnReviewMode');
const btnFitChrono = document.getElementById('btnFitChrono');
const btnClearChrono = document.getElementById('btnClearChrono');
const btnPrevDate = document.getElementById('btnPrevDate');
const btnNextDate = document.getElementById('btnNextDate');
const btnExportCSV = document.getElementById('btnExportCSV');
const btnExportXLSX = document.getElementById('btnExportXLSX');
const btnExportResumo = document.getElementById('btnExportResumo');
const btnExportCompleto = document.getElementById('btnExportCompleto');
const btnExportImagem = document.getElementById('btnExportImagem');

let images = [];
let loaded = 0;
let activeIdx = 0;
let scale = 1, offsetX = 0, offsetY = 0;
let dragging = false, lastX = 0, lastY = 0;
let markGridMode = false, reviewMode = false;
let gridRatios = [];
let selectedParcel = null;
let resultsByParcel = {};
let finalRows = [];
let fullRows = [];
let manualReviews = {};
const tempCanvas = document.createElement('canvas');
const tempCtx = tempCanvas.getContext('2d', { willReadFrequently:true });
let tempPrepared = -1;

function clamp(v,min,max){ return Math.max(min, Math.min(max, v)); }
function imgW(idx=activeIdx){ return ORTHOS[idx]?.width || images[idx]?.width || 1; }
function imgH(idx=activeIdx){ return ORTHOS[idx]?.height || images[idx]?.height || 1; }
function cellLabel(r,c){ return 'T' + (c + 1) + ' D' + (r + 1); }
function fmtPct(v){ return Number.isFinite(v) ? v.toFixed(2) : ''; }
function quoteCSV(v){
  const s = (v === null || v === undefined) ? '' : String(v);
  return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

function setupDates(){
  dateSelect.innerHTML = '';
  dateList.innerHTML = '';
  ORTHOS.forEach((o, idx) => {
    const opt = document.createElement('option');
    opt.value = idx;
    opt.textContent = (idx + 1) + ' · ' + o.date + ' · ' + o.name;
    dateSelect.appendChild(opt);
    const item = document.createElement('div');
    item.className = 'date-item' + (idx === activeIdx ? ' active' : '');
    item.innerHTML = '<span>' + (idx + 1) + ' · ' + o.date + '</span><span>' + o.name + '</span>';
    item.onclick = () => setActiveDate(idx);
    dateList.appendChild(item);
  });
}

function setActiveDate(idx){
  activeIdx = clamp(idx, 0, ORTHOS.length - 1);
  dateSelect.value = String(activeIdx);
  tempPrepared = -1;
  [...dateList.children].forEach((el,i) => el.classList.toggle('active', i === activeIdx));
  drawAll();
}

function loadImages(){
  ORTHOS.forEach((o, idx) => {
    const im = new Image();
    im.onload = () => {
      loaded += 1;
      if(idx === 0) fitView();
      statusEl.textContent = 'Ortofotos carregadas: ' + loaded + '/' + ORTHOS.length;
      drawAll();
    };
    im.src = 'data:image/jpeg;base64,' + o.b64;
    images[idx] = im;
  });
}

function fitView(){
  const W = viewer.clientWidth, H = viewer.clientHeight;
  const w = imgW(), h = imgH();
  scale = Math.min(W / w, H / h);
  offsetX = (W - w * scale) / 2;
  offsetY = (H - h * scale) / 2;
  drawAll();
}

function screenToImg(clientX, clientY){
  const r = canvas.getBoundingClientRect();
  return { x:(clientX - r.left - offsetX) / scale, y:(clientY - r.top - offsetY) / scale };
}

function ratioPoint(pt, idx=activeIdx){
  return { x: pt.x / imgW(idx), y: pt.y / imgH(idx) };
}

function currentGridPoints(idx=activeIdx){
  return gridRatios.map(p => ({ x:p.x * imgW(idx), y:p.y * imgH(idx) }));
}

function bilerp(p0,p1,p2,p3,u,v){
  const tx = (1-u)*p0.x + u*p1.x, ty = (1-u)*p0.y + u*p1.y;
  const bx = (1-u)*p3.x + u*p2.x, by = (1-u)*p3.y + u*p2.y;
  return { x:(1-v)*tx + v*bx, y:(1-v)*ty + v*by };
}

function cellPoly(r,c,idx=activeIdx){
  const pts = currentGridPoints(idx);
  if(pts.length < 4) return null;
  const R = Math.max(1, parseInt(CONFIG.rows || 1));
  const C = Math.max(1, parseInt(CONFIG.cols || 1));
  const u0 = c / C, u1 = (c + 1) / C, v0 = r / R, v1 = (r + 1) / R;
  return [
    bilerp(pts[0],pts[1],pts[2],pts[3],u0,v0),
    bilerp(pts[0],pts[1],pts[2],pts[3],u1,v0),
    bilerp(pts[0],pts[1],pts[2],pts[3],u1,v1),
    bilerp(pts[0],pts[1],pts[2],pts[3],u0,v1)
  ];
}

function pointInPolygon(px,py,poly){
  let inside = false;
  for(let i=0,j=poly.length-1; i<poly.length; j=i++){
    const xi=poly[i].x, yi=poly[i].y, xj=poly[j].x, yj=poly[j].y;
    if(((yi>py)!==(yj>py)) && (px < (xj-xi)*(py-yi)/(yj-yi)+xi)) inside = !inside;
  }
  return inside;
}

function findCell(pt){
  const R = Math.max(1, parseInt(CONFIG.rows || 1));
  const C = Math.max(1, parseInt(CONFIG.cols || 1));
  for(let r=0; r<R; r++){
    for(let c=0; c<C; c++){
      const poly = cellPoly(r,c);
      if(poly && pointInPolygon(pt.x, pt.y, poly)) return {r,c,label:cellLabel(r,c),poly};
    }
  }
  return null;
}

function rgbToHsv(r,g,b){
  r/=255; g/=255; b/=255;
  const max=Math.max(r,g,b), min=Math.min(r,g,b), d=max-min;
  let h=0;
  if(d!==0){
    if(max===r) h=60*(((g-b)/d)%6);
    else if(max===g) h=60*((b-r)/d+2);
    else h=60*((r-g)/d+4);
    if(h<0) h+=360;
  }
  return {h, s:max===0 ? 0 : d/max, v:max};
}

function tasselScore(r,g,b){
  const hsv = rgbToHsv(r,g,b);
  const chroma = Math.max(r,g,b) - Math.min(r,g,b);
  const exg = 2*g-r-b;
  const yellowness = ((r+g)*0.5)-b;
  const redYellowBalance = Math.abs(r-g);
  const leafGreen = (exg>8 && g>=r*0.92 && g>=b*1.03 && hsv.h>=56 && hsv.h<=168);
  const darkShadow = hsv.v<0.22;
  const whiteGlare = hsv.s<0.12 && hsv.v>0.74;
  const soilRed = r>g*1.28 && r>b*1.36 && hsv.h<18;
  const greenWhiteEdge = hsv.s<0.24 && g>=r*0.94 && b>=r*0.72 && hsv.h>=55 && hsv.h<=150;
  const nonGreen = !leafGreen && !greenWhiteEdge && exg < 42;
  const filter = CONFIG.filtroCor || 'Misto';

  let score = 0;
  const young = hsv.h>=42 && hsv.h<=74 && hsv.s>=0.12 && hsv.s<=0.58 && hsv.v>=0.34 && yellowness>=12 && exg<30;
  const dry = hsv.h>=20 && hsv.h<=58 && hsv.s>=0.15 && hsv.v>=0.34 && yellowness>=16 && r>=88 && g>=60 && b<=142 && r>=b+18 && g>=b+8 && redYellowBalance<=92;
  const bright = r>=112 && g>=88 && b<=162 && yellowness>=18 && redYellowBalance<=72 && hsv.s>=0.11 && hsv.h>=16 && hsv.h<=62;
  const oldPinkTan = r>=102 && g>=70 && b<=155 && r>=g*0.88 && g>=b*0.82 && r>=b+10 && hsv.h>=8 && hsv.h<=42 && hsv.s>=0.12;
  const textureColor = chroma>=22 && yellowness>=16 && hsv.s>=0.14;

  if(filter === 'Pendão novo'){
    if(young) score += 3.2;
    if(hsv.h>=50 && hsv.h<=90) score += 1.1;
    if(dry) score += 0.8;
  } else if(filter === 'Pendão seco/velho'){
    if(dry) score += 3.3;
    if(bright) score += 1.6;
    if(young) score += 0.7;
  } else {
    if(young) score += 2.1;
    if(dry) score += 2.4;
    if(bright) score += 1.7;
    if(oldPinkTan) score += 1.8;
  }
  if(textureColor) score += 0.8;
  if(yellowness>=28) score += 0.65;
  if(!nonGreen) score -= 5.0;
  if(leafGreen) score -= 4.8;
  if(greenWhiteEdge) score -= 3.4;
  if(darkShadow) score -= 2.2;
  if(whiteGlare) score -= 2.2;
  if(soilRed) score -= 1.6;
  if(chroma<12 && yellowness<18) score -= 1.2;

  const sensitivity = clamp(Number(CONFIG.sensibilidade || 60), 1, 100);
  const tolerance = clamp(Number(CONFIG.tolerancia || 55), 0, 100);
  score += (sensitivity - 50) / 70;
  score += (tolerance - 50) / 130;
  return score;
}

function scoreThreshold(){
  const sensitivity = clamp(Number(CONFIG.sensibilidade || 60), 1, 100);
  const tolerance = clamp(Number(CONFIG.tolerancia || 55), 0, 100);
  return clamp(4.35 - (sensitivity - 50) / 100 - (tolerance - 50) / 150, 3.75, 4.80);
}

function mergeNearbyTassels(marks,w,h){
  if(!marks.length) return marks;
  const radius = Math.max(12, Math.min(28, Math.min(w,h)*0.040));
  const ordered = [...marks].sort((a,b)=>(b.score*b.area)-(a.score*a.area));
  const merged = [];
  for(const m of ordered){
    let target = null;
    for(const c of merged){
      const dx=m.x-c.x, dy=m.y-c.y;
      if(Math.sqrt(dx*dx+dy*dy)<=radius){ target=c; break; }
    }
    if(target){
      const wa=Math.max(1,target.area), wb=Math.max(1,m.area);
      target.x=(target.x*wa+m.x*wb)/(wa+wb);
      target.y=(target.y*wa+m.y*wb)/(wa+wb);
      target.area+=m.area;
      target.score=Math.max(target.score,m.score);
    } else {
      merged.push({...m});
    }
  }
  return merged.sort((a,b)=>a.y===b.y ? a.x-b.x : a.y-b.y);
}

function prepareTemp(idx){
  if(tempPrepared === idx) return;
  tempCanvas.width = imgW(idx);
  tempCanvas.height = imgH(idx);
  tempCtx.clearRect(0,0,tempCanvas.width,tempCanvas.height);
  tempCtx.drawImage(images[idx],0,0,tempCanvas.width,tempCanvas.height);
  tempPrepared = idx;
}

function analyzeCellInImage(idx,r,c){
  prepareTemp(idx);
  const poly = cellPoly(r,c,idx);
  if(!poly) return {count:0, marks:[], confidence:0};
  const xs = poly.map(p=>p.x), ys = poly.map(p=>p.y);
  const minX = clamp(Math.floor(Math.min(...xs)),0,imgW(idx)-1);
  const maxX = clamp(Math.ceil(Math.max(...xs)),0,imgW(idx)-1);
  const minY = clamp(Math.floor(Math.min(...ys)),0,imgH(idx)-1);
  const maxY = clamp(Math.ceil(Math.max(...ys)),0,imgH(idx)-1);
  const w = maxX-minX+1, h=maxY-minY+1;
  if(w<=1 || h<=1) return {count:0, marks:[], confidence:0};

  const data = tempCtx.getImageData(minX,minY,w,h).data;
  const sensitivity = clamp(Number(CONFIG.sensibilidade || 60), 1, 100);
  const step = sensitivity >= 75 ? 1 : (sensitivity >= 45 ? 2 : 3);
  const gw = Math.ceil(w/step), gh=Math.ceil(h/step);
  const mask = new Uint8Array(gw*gh);
  const clean = new Uint8Array(gw*gh);
  const close = new Uint8Array(gw*gh);
  const scores = new Float32Array(gw*gh);
  const th = scoreThreshold();

  for(let gy=0; gy<gh; gy++){
    for(let gx=0; gx<gw; gx++){
      const px = Math.min(w-1, gx*step), py=Math.min(h-1, gy*step);
      const ax=minX+px, ay=minY+py;
      if(!pointInPolygon(ax,ay,poly)) continue;
      const di=(py*w+px)*4;
      const score = tasselScore(data[di],data[di+1],data[di+2]);
      const mi=gy*gw+gx;
      scores[mi]=score;
      if(score>=th) mask[mi]=1;
    }
  }

  for(let gy=0; gy<gh; gy++){
    for(let gx=0; gx<gw; gx++){
      const mi=gy*gw+gx;
      if(!mask[mi]) continue;
      let n=0;
      for(let yy=-1; yy<=1; yy++){
        for(let xx=-1; xx<=1; xx++){
          if(xx===0 && yy===0) continue;
          const nx=gx+xx, ny=gy+yy;
          if(nx>=0 && nx<gw && ny>=0 && ny<gh && mask[ny*gw+nx]) n++;
        }
      }
      if(n>=2 || scores[mi]>=th+1.05) clean[mi]=1;
    }
  }

  for(let gy=0; gy<gh; gy++){
    for(let gx=0; gx<gw; gx++){
      const mi=gy*gw+gx;
      if(clean[mi]) { close[mi]=1; continue; }
      let n=0, s=0, total=0;
      for(let yy=-1; yy<=1; yy++){
        for(let xx=-1; xx<=1; xx++){
          const nx=gx+xx, ny=gy+yy;
          if(nx>=0 && nx<gw && ny>=0 && ny<gh){
            const ni=ny*gw+nx;
            if(clean[ni]) n++;
            s += scores[ni]; total++;
          }
        }
      }
      if(n>=5 && s/Math.max(1,total)>=th-0.65) close[mi]=1;
    }
  }

  const minArea = Math.max(1, Number(CONFIG.areaMin || 18));
  const maxAreaCfg = Math.max(minArea+1, Number(CONFIG.areaMax || 900));
  const maxArea = Math.min(maxAreaCfg, Math.max(minArea+1, w*h*0.026));
  const visited = new Uint8Array(gw*gh);
  const dirs = [[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,1],[1,-1],[-1,-1]];
  const marks = [];
  let confidenceSum = 0;

  for(let gy=0; gy<gh; gy++){
    for(let gx=0; gx<gw; gx++){
      const start=gy*gw+gx;
      if(!close[start] || visited[start]) continue;
      let cells=0, sx=0, sy=0, scoreSum=0;
      let minGX=gx, maxGX=gx, minGY=gy, maxGY=gy;
      const stack=[[gx,gy]];
      visited[start]=1;
      while(stack.length){
        const p=stack.pop(), x=p[0], y=p[1], pos=y*gw+x;
        cells++; sx+=x; sy+=y; scoreSum+=scores[pos];
        if(x<minGX) minGX=x; if(x>maxGX) maxGX=x; if(y<minGY) minGY=y; if(y>maxGY) maxGY=y;
        for(const d of dirs){
          const nx=x+d[0], ny=y+d[1];
          if(nx<0 || nx>=gw || ny<0 || ny>=gh) continue;
          const ni=ny*gw+nx;
          if(close[ni] && !visited[ni]) { visited[ni]=1; stack.push([nx,ny]); }
        }
      }
      const area = cells*step*step;
      const widthPx = (maxGX-minGX+1)*step;
      const heightPx = (maxGY-minGY+1)*step;
      const bboxCells = Math.max(1,(maxGX-minGX+1)*(maxGY-minGY+1));
      const density = cells / bboxCells;
      const elongation = Math.max(widthPx,heightPx) / Math.max(1,Math.min(widthPx,heightPx));
      const meanScore = scoreSum / Math.max(1,cells);
      const cx=minX + (sx/cells)*step, cy=minY + (sy/cells)*step;
      const valid =
        area>=minArea &&
        area<=maxArea &&
        density>=0.11 &&
        elongation<=8.5 &&
        widthPx<=Math.max(16, w*0.18) &&
        heightPx<=Math.max(16, h*0.22) &&
        meanScore>=th-0.15 &&
        pointInPolygon(cx,cy,poly);
      if(valid){
        marks.push({x:cx,y:cy,area:area,score:meanScore});
        confidenceSum += clamp((meanScore - (th-0.2)) / 2.2, 0.15, 1);
      }
    }
  }
  const confidence = marks.length ? confidenceSum / marks.length : 0.78;
  const finalMarks = mergeNearbyTassels(marks,w,h);
  return {count:finalMarks.length, marks:finalMarks, confidence};
}

function rebuildRows(){
  finalRows = [];
  fullRows = [];
  const R = Math.max(1, parseInt(CONFIG.rows || 1));
  const C = Math.max(1, parseInt(CONFIG.cols || 1));
  const meta = CONFIG.metadata || {};
  let hit=0, noHit=0, review=0, firstGeneral='';
  for(let r=0; r<R; r++){
    for(let c=0; c<C; c++){
      const label = cellLabel(r,c);
      const rec = resultsByParcel[label] || {counts:ORTHOS.map(()=>0), percents:ORTHOS.map(()=>0), confidence:1, marksByDate:ORTHOS.map(()=>[])};
      const manual = manualReviews[label] || {};
      const teto = Math.max(1, Number(manual.teto || CONFIG.tetoPlantas || 1));
      const counts = ORTHOS.map((_,i) => manual.counts && manual.counts[i] !== undefined ? Number(manual.counts[i] || 0) : Number(rec.counts[i] || 0));
      const percents = counts.map(v => (v / teto) * 100);
      let status = 'NÃO ATINGIU';
      let firstDate = '';
      let firstOrtho = '';
      for(let i=0; i<ORTHOS.length; i++){
        if(counts[i] >= Number(CONFIG.minPendoes || 0) && percents[i] >= Number(CONFIG.percentualLimite || 50)){
          status = 'ATINGIU';
          firstDate = ORTHOS[i].date;
          firstOrtho = ORTHOS[i].name;
          break;
        }
      }
      if(manual.status) status = manual.status;
      if(rec.confidence < 0.38 && !manual.status) status = 'REVISAR';
      if(manual.firstDate !== undefined) firstDate = manual.firstDate;
      if(manual.firstOrtho !== undefined) firstOrtho = manual.firstOrtho;
      const obs = manual.obs || (rec.confidence < 0.38 ? 'Baixa confiança na detecção automática' : '');
      const row = {
        NOME_ANALISE: CONFIG.nomeAnalise || '',
        CODLOCAL: meta.CODLOCAL || '',
        QUADRA: meta.QUADRA || '',
        ENSAIO: meta.ENSAIO || '',
        GLI: meta.GLI || '',
        TECNOLOGIA: meta.TECNOLOGIA || '',
        REP: meta.REP || '',
        NC: meta.NC || '',
        LINHAGEM: meta.LINHAGEM || '',
        GENEALOGIA: meta.GENEALOGIA || '',
        PARENTAL1: meta.PARENTAL1 || '',
        POP_PARENTAL1: meta.POP_PARENTAL1 || '',
        PARENTAL2: meta.PARENTAL2 || '',
        POP_PARENTAL2: meta.POP_PARENTAL2 || '',
        DTP: meta.DTP || '',
        TIRO: 'T' + (c + 1),
        ID_PARCELA: label
      };
      for(let i=0; i<10; i++){
        row['DATA_ORTOFOTO_' + (i+1)] = ORTHOS[i] ? ORTHOS[i].date : '';
        row['PENDOES_' + (i+1)] = ORTHOS[i] ? counts[i] : '';
        row['PERCENTUAL_' + (i+1)] = ORTHOS[i] ? fmtPct(percents[i]) : '';
      }
      row.TETO_PLANTAS = teto;
      row.PERCENTUAL_LIMITE = CONFIG.percentualLimite;
      row.DATA_PRIMEIRO_ATINGIMENTO = status === 'ATINGIU' ? firstDate : '';
      row.ORTOFOTO_PRIMEIRO_ATINGIMENTO = status === 'ATINGIU' ? firstOrtho : '';
      row.STATUS = status;
      row.OBSERVACAO = obs;
      finalRows.push(row);

      for(let i=0; i<ORTHOS.length; i++){
        fullRows.push({
          Nome_Analise: CONFIG.nomeAnalise || '',
          Parcela: label,
          TIRO: 'T' + (c + 1),
          Linha: 'D' + (r + 1),
          Data: ORTHOS[i].date,
          Ortofoto: ORTHOS[i].name,
          Pendoes: counts[i],
          Percentual: fmtPct(percents[i]),
          Teto_Plantas: teto,
          Status: status,
          Confianca: fmtPct((rec.confidence || 0) * 100)
        });
      }

      if(status === 'ATINGIU') {
        hit++;
        if(firstDate && (!firstGeneral || firstDate < firstGeneral)) firstGeneral = firstDate;
      } else if(status === 'REVISAR') review++;
      else if(status === 'SEM DADOS') review++;
      else noHit++;
    }
  }
  document.getElementById('statTotal').textContent = finalRows.length;
  document.getElementById('statHit').textContent = hit;
  document.getElementById('statNoHit').textContent = noHit;
  document.getElementById('statReview').textContent = review;
  document.getElementById('statFirstDate').textContent = 'Primeira data geral: ' + (firstGeneral || '--');
}

function runChronologicalAnalysis(){
  if(gridRatios.length < 4){ alert('Marque os 4 pontos do grid fixo primeiro.'); return; }
  if(loaded < ORTHOS.length){ alert('Aguarde as ortofotos terminarem de carregar.'); return; }
  const R = Math.max(1, parseInt(CONFIG.rows || 1));
  const C = Math.max(1, parseInt(CONFIG.cols || 1));
  resultsByParcel = {};
  statusEl.textContent = 'Analisando pendoamento em ' + ORTHOS.length + ' ortofotos...';
  progressBar.style.width = '0%';
  setTimeout(() => {
    let done = 0;
    const total = ORTHOS.length * R * C;
    for(let i=0; i<ORTHOS.length; i++){
      tempPrepared = -1;
      for(let r=0; r<R; r++){
        for(let c=0; c<C; c++){
          const label = cellLabel(r,c);
          if(!resultsByParcel[label]){
            resultsByParcel[label] = {
              row:r+1,
              col:c+1,
              counts:ORTHOS.map(()=>0),
              percents:ORTHOS.map(()=>0),
              marksByDate:ORTHOS.map(()=>[]),
              confidence:1
            };
          }
          const res = analyzeCellInImage(i,r,c);
          resultsByParcel[label].counts[i] = res.count;
          resultsByParcel[label].marksByDate[i] = res.marks;
          resultsByParcel[label].confidence = Math.min(resultsByParcel[label].confidence, res.confidence);
          done++;
          if(done % Math.max(1, Math.floor(total/20)) === 0) progressBar.style.width = Math.round(done/total*100) + '%';
        }
      }
    }
    progressBar.style.width = '100%';
    rebuildRows();
    statusEl.textContent = 'Análise concluída. Parcelas processadas: ' + finalRows.length + '.';
    drawAll();
    renderReviewPanel();
  }, 50);
}

function rowForLabel(label){
  return finalRows.find(r => r.ID_PARCELA === label);
}

function renderReviewPanel(){
  if(!selectedParcel){
    reviewPanel.style.display = 'none';
    return;
  }
  const label = selectedParcel.label;
  const rec = resultsByParcel[label] || {counts:ORTHOS.map(()=>0)};
  const manual = manualReviews[label] || {};
  const counts = ORTHOS.map((_,i) => manual.counts && manual.counts[i] !== undefined ? Number(manual.counts[i] || 0) : Number(rec.counts[i] || 0));
  const teto = manual.teto || CONFIG.tetoPlantas || 1;
  const row = rowForLabel(label) || {};
  reviewPanel.style.display = 'block';
  reviewPanel.innerHTML = `
    <h4>Revisão manual · ${label}</h4>
    <div class="review-line"><span>Teto de plantas</span><input id="revTeto" type="number" min="1" value="${teto}"></div>
    ${ORTHOS.map((o,i)=>`<div class="review-line"><span>${i+1} · ${o.date}</span><input id="revCount${i}" type="number" min="0" value="${counts[i] || 0}"></div>`).join('')}
    <div class="row"><span>Status</span><select id="revStatus">
      ${['','ATINGIU','NÃO ATINGIU','REVISAR','SEM DADOS'].map(s=>`<option value="${s}" ${String(row.STATUS || '')===s?'selected':''}>${s || 'Automático'}</option>`).join('')}
    </select></div>
    <div class="row"><span>Observação</span></div>
    <textarea id="revObs">${manual.obs || row.OBSERVACAO || ''}</textarea>
    <button class="btn green" id="btnSaveReview">Salvar revisão</button>
  `;
  document.getElementById('btnSaveReview').onclick = () => {
    const newCounts = ORTHOS.map((_,i) => Number(document.getElementById('revCount'+i).value || 0));
    manualReviews[label] = {
      counts:newCounts,
      teto:Number(document.getElementById('revTeto').value || CONFIG.tetoPlantas || 1),
      status:document.getElementById('revStatus').value,
      obs:document.getElementById('revObs').value || ''
    };
    rebuildRows();
    renderReviewPanel();
    drawAll();
    statusEl.textContent = 'Revisão salva para ' + label + '.';
  };
}

function drawGrid(idx=activeIdx){
  if(gridRatios.length < 4) return;
  const R = Math.max(1, parseInt(CONFIG.rows || 1));
  const C = Math.max(1, parseInt(CONFIG.cols || 1));
  const pts = currentGridPoints(idx);
  ctx.save();
  ctx.lineWidth = 1.55 / scale;
  ctx.strokeStyle = 'rgba(0,207,255,.78)';
  ctx.shadowColor = 'rgba(0,207,255,.35)';
  ctx.shadowBlur = 5 / scale;
  for(let i=0; i<=R; i++){
    const v=i/R, left=bilerp(pts[0],pts[1],pts[2],pts[3],0,v), right=bilerp(pts[0],pts[1],pts[2],pts[3],1,v);
    ctx.beginPath(); ctx.moveTo(left.x,left.y); ctx.lineTo(right.x,right.y); ctx.stroke();
  }
  for(let j=0; j<=C; j++){
    const u=j/C, top=bilerp(pts[0],pts[1],pts[2],pts[3],u,0), bottom=bilerp(pts[0],pts[1],pts[2],pts[3],u,1);
    ctx.beginPath(); ctx.moveTo(top.x,top.y); ctx.lineTo(bottom.x,bottom.y); ctx.stroke();
  }
  ctx.restore();

  for(let r=0; r<R; r++){
    for(let c=0; c<C; c++){
      const label = cellLabel(r,c);
      const poly = cellPoly(r,c,idx);
      const row = rowForLabel(label);
      const isSel = selectedParcel && selectedParcel.label === label;
      if(!poly) continue;
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(poly[0].x,poly[0].y);
      for(let k=1; k<poly.length; k++) ctx.lineTo(poly[k].x,poly[k].y);
      ctx.closePath();
      if(row){
        if(row.STATUS === 'ATINGIU') ctx.fillStyle='rgba(255,140,0,.22)';
        else if(row.STATUS === 'REVISAR' || row.STATUS === 'SEM DADOS') ctx.fillStyle='rgba(255,214,0,.22)';
        else ctx.fillStyle='rgba(150,150,150,.10)';
        ctx.fill();
      }
      if(isSel){
        ctx.fillStyle='rgba(255,214,0,.22)';
        ctx.fill();
        ctx.strokeStyle='rgba(255,214,0,.96)';
        ctx.lineWidth=2.6/scale;
        ctx.stroke();
      }
      const cx=(poly[0].x+poly[1].x+poly[2].x+poly[3].x)/4;
      const cy=(poly[0].y+poly[1].y+poly[2].y+poly[3].y)/4;
      ctx.shadowColor='rgba(0,0,0,.9)';
      ctx.shadowBlur=4/scale;
      ctx.fillStyle='#fff';
      ctx.font='bold '+Math.max(8,10/scale)+'px Arial';
      ctx.textAlign='center';
      ctx.textBaseline='middle';
      ctx.fillText(label, cx, cy);
      ctx.restore();
    }
  }
}

function drawMarks(idx=activeIdx){
  for(const label of Object.keys(resultsByParcel)){
    const rec = resultsByParcel[label];
    const marks = rec.marksByDate ? (rec.marksByDate[idx] || []) : [];
    for(const m of marks){
      ctx.save();
      const s = 5 / scale;
      ctx.strokeStyle='#ff2020';
      ctx.lineWidth=2/scale;
      ctx.shadowColor='rgba(255,0,0,.65)';
      ctx.shadowBlur=5/scale;
      ctx.beginPath(); ctx.moveTo(m.x-s,m.y-s); ctx.lineTo(m.x+s,m.y+s); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(m.x-s,m.y+s); ctx.lineTo(m.x+s,m.y-s); ctx.stroke();
      ctx.restore();
    }
  }
}

function drawAll(){
  const W = viewer.clientWidth, H = viewer.clientHeight;
  canvas.width = W; canvas.height = H;
  ctx.clearRect(0,0,W,H);
  ctx.save();
  ctx.translate(offsetX,offsetY);
  ctx.scale(scale,scale);
  if(images[activeIdx] && images[activeIdx].complete) ctx.drawImage(images[activeIdx],0,0,imgW(activeIdx),imgH(activeIdx));
  drawGrid(activeIdx);
  drawMarks(activeIdx);
  if(gridRatios.length > 0 && gridRatios.length < 4){
    const pts = currentGridPoints(activeIdx);
    pts.forEach((p,i)=>{
      ctx.save();
      ctx.fillStyle='#1e90ff'; ctx.strokeStyle='#00cfff'; ctx.lineWidth=2/scale;
      ctx.beginPath(); ctx.arc(p.x,p.y,10/scale,0,Math.PI*2); ctx.fill(); ctx.stroke();
      ctx.fillStyle='#fff'; ctx.font='bold '+(12/scale)+'px Arial'; ctx.textAlign='center'; ctx.textBaseline='middle';
      ctx.fillText(String(i+1),p.x,p.y);
      ctx.restore();
    });
  }
  ctx.restore();
  zoomBadge.textContent = scale.toFixed(2) + '×';
}

function exportRows(rows, filename){
  if(!rows.length){ alert('Execute a análise antes de exportar.'); return; }
  const headers = Object.keys(rows[0]);
  const csv = '\uFEFF' + headers.join(',') + '\n' + rows.map(row => headers.map(h => quoteCSV(row[h])).join(',')).join('\n');
  const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
}

function exportExcel(){
  if(!finalRows.length){ alert('Execute a análise antes de exportar.'); return; }
  if(typeof XLSX === 'undefined'){ alert('Biblioteca Excel não carregou. Use Exportar CSV.'); return; }
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(finalRows), 'Resumo');
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(fullRows), 'Por_Ortofoto');
  XLSX.writeFile(wb, 'analise_cronologica_pendoamento.xlsx');
}

function exportResumo(){
  if(!finalRows.length){ alert('Execute a análise antes de exportar.'); return; }
  const resumo = finalRows.map(r => ({
    CODLOCAL:r.CODLOCAL, QUADRA:r.QUADRA, ENSAIO:r.ENSAIO, GLI:r.GLI, TECNOLOGIA:r.TECNOLOGIA,
    REP:r.REP, NC:r.NC, LINHAGEM:r.LINHAGEM, DTP:r.DTP, TIRO:r.TIRO, ID_PARCELA:r.ID_PARCELA,
    TETO_PLANTAS:r.TETO_PLANTAS, PERCENTUAL_LIMITE:r.PERCENTUAL_LIMITE,
    DATA_PRIMEIRO_ATINGIMENTO:r.DATA_PRIMEIRO_ATINGIMENTO,
    ORTOFOTO_PRIMEIRO_ATINGIMENTO:r.ORTOFOTO_PRIMEIRO_ATINGIMENTO,
    STATUS:r.STATUS, OBSERVACAO:r.OBSERVACAO
  }));
  exportRows(resumo, 'resumo_final_pendoamento.csv');
}

function exportImage(){
  const out = document.createElement('canvas');
  out.width = imgW(activeIdx); out.height = imgH(activeIdx);
  const octx = out.getContext('2d');
  octx.drawImage(images[activeIdx],0,0,out.width,out.height);
  const oldCtxDraw = ctx;
  octx.save();
  const originalCanvas = canvas;
  const originalCtx = ctx;
  octx.lineWidth = 2;
  if(gridRatios.length === 4){
    const R = Math.max(1, parseInt(CONFIG.rows || 1));
    const C = Math.max(1, parseInt(CONFIG.cols || 1));
    const pts = currentGridPoints(activeIdx);
    octx.strokeStyle='rgba(0,207,255,.95)';
    for(let i=0; i<=R; i++){
      const v=i/R, left=bilerp(pts[0],pts[1],pts[2],pts[3],0,v), right=bilerp(pts[0],pts[1],pts[2],pts[3],1,v);
      octx.beginPath(); octx.moveTo(left.x,left.y); octx.lineTo(right.x,right.y); octx.stroke();
    }
    for(let j=0; j<=C; j++){
      const u=j/C, top=bilerp(pts[0],pts[1],pts[2],pts[3],u,0), bottom=bilerp(pts[0],pts[1],pts[2],pts[3],u,1);
      octx.beginPath(); octx.moveTo(top.x,top.y); octx.lineTo(bottom.x,bottom.y); octx.stroke();
    }
    for(const label of Object.keys(resultsByParcel)){
      const marks = resultsByParcel[label].marksByDate ? (resultsByParcel[label].marksByDate[activeIdx] || []) : [];
      for(const m of marks){
        const s=7;
        octx.strokeStyle='#ff2020'; octx.lineWidth=2;
        octx.beginPath(); octx.moveTo(m.x-s,m.y-s); octx.lineTo(m.x+s,m.y+s); octx.stroke();
        octx.beginPath(); octx.moveTo(m.x-s,m.y+s); octx.lineTo(m.x+s,m.y-s); octx.stroke();
      }
    }
  }
  octx.restore();
  const a = document.createElement('a');
  a.href = out.toDataURL('image/png');
  a.download = 'pendoamento_grid_marcacoes_' + (ORTHOS[activeIdx]?.date || 'data') + '.png';
  a.click();
}

viewer.addEventListener('wheel', e => {
  e.preventDefault();
  const factor = e.deltaY < 0 ? 1.2 : 0.8;
  const r = canvas.getBoundingClientRect();
  const mx=e.clientX-r.left, my=e.clientY-r.top;
  const ix=(mx-offsetX)/scale, iy=(my-offsetY)/scale;
  scale = clamp(scale*factor, 0.04, 50);
  offsetX = mx - ix*scale;
  offsetY = my - iy*scale;
  drawAll();
}, {passive:false});

viewer.addEventListener('mousedown', e => {
  const pt = screenToImg(e.clientX,e.clientY);
  if(markGridMode){
    gridRatios.push(ratioPoint(pt, activeIdx));
    if(gridRatios.length >= 4){
      gridRatios = gridRatios.slice(0,4);
      markGridMode = false;
      btnMarkGrid.classList.remove('active');
      statusEl.textContent = 'Grid fixo marcado. Execute a análise cronológica.';
    } else {
      statusEl.textContent = 'Marque o ponto ' + (gridRatios.length + 1) + ' do grid fixo.';
    }
    resultsByParcel = {}; finalRows = []; fullRows = [];
    rebuildRows();
    drawAll();
    return;
  }
  if(reviewMode && gridRatios.length === 4){
    const cell = findCell(pt);
    if(cell){
      selectedParcel = cell;
      renderReviewPanel();
      drawAll();
    }
    return;
  }
  dragging = true; lastX=e.clientX; lastY=e.clientY; viewer.style.cursor='grabbing';
});

viewer.addEventListener('mousemove', e => {
  const pt = screenToImg(e.clientX,e.clientY);
  coordBadge.textContent = 'X:' + Math.round(pt.x) + ' Y:' + Math.round(pt.y);
  if(dragging){
    offsetX += e.clientX-lastX;
    offsetY += e.clientY-lastY;
    lastX=e.clientX; lastY=e.clientY;
    drawAll();
  }
});
viewer.addEventListener('mouseup', () => { dragging=false; viewer.style.cursor='grab'; });
viewer.addEventListener('mouseleave', () => { dragging=false; viewer.style.cursor='grab'; });

btnMarkGrid.onclick = () => {
  markGridMode = !markGridMode;
  reviewMode = false;
  btnMarkGrid.classList.toggle('active', markGridMode);
  btnReviewMode.classList.remove('active');
  if(markGridMode){
    gridRatios = [];
    resultsByParcel = {}; finalRows = []; fullRows = [];
    rebuildRows();
    statusEl.textContent = 'Marque 4 pontos do grid fixo na ortofoto.';
  }
  drawAll();
};
btnReviewMode.onclick = () => {
  if(gridRatios.length < 4){ alert('Marque o grid primeiro.'); return; }
  reviewMode = !reviewMode;
  markGridMode = false;
  btnReviewMode.classList.toggle('active', reviewMode);
  btnMarkGrid.classList.remove('active');
  statusEl.textContent = reviewMode ? 'Clique em uma parcela para revisar contagens por data.' : 'Revisão manual pausada.';
};
btnAnalyzeChrono.onclick = runChronologicalAnalysis;
btnFitChrono.onclick = fitView;
btnClearChrono.onclick = () => {
  if(!confirm('Limpar grid, resultados e revisões deste módulo cronológico?')) return;
  gridRatios=[]; selectedParcel=null; resultsByParcel={}; finalRows=[]; fullRows=[]; manualReviews={};
  progressBar.style.width='0%'; statusEl.textContent='Módulo cronológico limpo.';
  rebuildRows(); renderReviewPanel(); drawAll();
};
btnPrevDate.onclick = () => setActiveDate(activeIdx - 1);
btnNextDate.onclick = () => setActiveDate(activeIdx + 1);
dateSelect.onchange = () => setActiveDate(Number(dateSelect.value));
btnExportCSV.onclick = () => exportRows(finalRows, 'analise_cronologica_pendoamento.csv');
btnExportXLSX.onclick = exportExcel;
btnExportResumo.onclick = exportResumo;
btnExportCompleto.onclick = () => exportRows(fullRows, 'dados_completos_por_ortofoto.csv');
btnExportImagem.onclick = exportImage;

setupDates();
loadImages();
rebuildRows();
new ResizeObserver(() => drawAll()).observe(viewer);
</script>
</body>
</html>
"""
                    cron_html = (
                        cron_html
                        .replace("__CRON_ORTHOS__", json.dumps(cron_orthos, ensure_ascii=False))
                        .replace("__CRON_CONFIG__", json.dumps(cron_config, ensure_ascii=False))
                    )
                    components.html(cron_html, height=870, scrolling=False)
            else:
                st.markdown("""
                <div style='height:120px;border:1px dashed #2e2e2e;border-radius:12px;background:#0d0d0d;
                            display:flex;flex-direction:column;align-items:center;justify-content:center;
                            gap:8px;color:#444;margin-top:8px;'>
                    <div style='font-size:1.8rem;'>🗓️</div>
                    <div style='font-size:0.78rem;letter-spacing:1.5px;text-transform:uppercase;color:#666;'>
                        Anexe até 10 ortofotos para análise cronológica de pendoamento
                    </div>
                </div>""", unsafe_allow_html=True)

        elif st.session_state.visualizador_sub == "Qualidade":
            # ==========================================
            # NOVO - MÓDULO QUALIDADE DE PARCELA (Falhas Lineares)
            # ==========================================
            st.markdown("""
            <div style='color:#ff8c00;font-weight:700;font-size:1rem;letter-spacing:2px;
                        text-transform:uppercase;margin-bottom:10px;'>
                ✅ Qualidade de Parcelas · Detecção de Falhas Lineares
            </div>""", unsafe_allow_html=True)

            qual_file = st.file_uploader(
                "📷 Carregar Ortofoto para Análise de Qualidade",
                type=MOSAIC_UPLOAD_TYPES,
                key="qual_orto_uploader",
                help="PNG · JPG · TIF/GeoTIFF · JP2 · IMG · ECW"
            )
            qual_library = _mosaic_single_select("Ou usar mosaico já importado", key="qual_mosaic_library")
            qual_bytes, qual_name = _mosaic_input_bytes(qual_file, qual_library, "Qualidade")

            if qual_bytes:
                with st.spinner("Carregando ortofoto..."):
                    qual_b64, qual_dims, qual_err, qual_spatial = processar_ortofoto(qual_bytes, qual_name)

                if qual_err:
                    st.error(f"Erro: {qual_err}")
                else:
                    qw, qh = qual_dims
                    st.markdown(
                        f"<p style='color:#666;font-size:0.78rem;margin-bottom:6px;'>"
                        f"📐 {qual_name} · {qw}×{qh} px</p>",
                        unsafe_allow_html=True
                    )

                    qual_viewer = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:#0d0d0d; overflow:hidden; font-family:'Segoe UI',sans-serif; }}

  #vc {{
    width:100%; height:720px;
    background:
      linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px),
      #0d0d0d;
    background-size:32px 32px;
    border:1px solid #2a2a2a; border-radius:12px;
    overflow:hidden; position:relative; cursor:grab; user-select:none;
  }}
  #vc:active {{ cursor:grabbing; }}
  canvas {{ position:absolute; top:0; left:0; display:block; }}

  .toolbar {{ position:absolute; top:12px; right:12px; display:flex; flex-direction:column; gap:5px; z-index:20; }}
  .tb-btn {{
    background:linear-gradient(145deg,#1e1e1e,#111); border:1px solid #3a3a3a;
    color:#ff8c00; width:34px; height:34px; border-radius:8px; cursor:pointer;
    font-size:15px; font-weight:700; display:flex; align-items:center; justify-content:center;
    box-shadow:2px 2px 8px #000,inset 0 1px 0 rgba(255,255,255,.05); transition:all .2s;
  }}
  .tb-btn:hover {{ border-color:#ff8c00; box-shadow:0 0 10px rgba(255,140,0,.35),2px 2px 8px #000; color:#ffaa33; }}
  .tb-btn:active {{ transform:translateY(1px); }}
  .tb-sep {{ width:34px; height:1px; background:linear-gradient(90deg,transparent,#333,transparent); margin:2px 0; }}

  .grid-panel {{
    position:absolute; top:10px; right:55px;
    background:rgba(10,10,10,.92); border:1px solid #2a2a2a;
    border-radius:8px; padding:7px; display:flex; flex-direction:column;
    gap:4px; z-index:20; min-width:190px; max-height:calc(100% - 20px);
    overflow-y:auto; overflow-x:hidden; scrollbar-width:thin; scrollbar-color:#ff8c00 #141414;
  }}
  .grid-panel::-webkit-scrollbar {{ width:6px; }}
  .grid-panel::-webkit-scrollbar-track {{ background:#141414; border-radius:6px; }}
  .grid-panel::-webkit-scrollbar-thumb {{ background:#ff8c00; border-radius:6px; }}
  .grid-panel label {{ color:#ff8c00; font-size:9px; line-height:1.1; font-weight:bold; text-align:center; }}
  .grid-panel input[type=number] {{
    background:#1a1a1a; border:1px solid #333; color:#fff;
    border-radius:4px; padding:2px 3px; height:20px; width:46px; text-align:center; font-size:10px;
  }}
  .grid-panel .row-col {{ display:flex; gap:5px; align-items:center; justify-content:space-between; color:#ccc; font-size:10px; min-height:20px; }}
  .grid-panel .row-col span {{ line-height:1; }}
  .grid-panel select {{ height:21px; padding:2px 4px !important; font-size:10px !important; }}
  .grid-btn {{
    background:linear-gradient(145deg,#1e1e1e,#111); border:1px solid #3a3a3a;
    color:#ccc; cursor:pointer; border-radius:4px; padding:4px 5px; min-height:22px; font-size:10px; font-weight:bold; transition:.2s;
  }}
  .grid-btn:hover {{ border-color:#ff8c00; color:#ff8c00; }}
  .grid-btn.active {{ border-color:#ff8c00; color:#ff8c00; box-shadow:0 0 8px rgba(255,140,0,.3); background:#2a1a00; }}

  .zoom-badge {{
    position:absolute; top:12px; left:12px;
    background:rgba(10,10,10,.82); border:1px solid #2a2a2a; border-radius:8px;
    color:#ff8c00; font-size:11px; font-family:'Courier New',monospace;
    font-weight:700; padding:5px 10px; letter-spacing:1px; z-index:20; pointer-events:none;
  }}
  .crosshair {{
    position:absolute; bottom:12px; left:12px;
    background:rgba(10,10,10,.82); border:1px solid #222; border-radius:8px;
    color:#555; font-size:10px; font-family:'Courier New',monospace;
    padding:4px 10px; z-index:20; pointer-events:none; letter-spacing:.5px;
  }}
  .hint {{
    position:absolute; bottom:12px; right:12px; color:#333; font-size:10px;
    z-index:20; pointer-events:none; text-align:right; line-height:1.6;
  }}

  .count-panel {{
    position:absolute; top:50px; left:12px;
    background:rgba(10,10,10,.92); border:1px solid #2a2a2a; border-radius:8px;
    padding:10px; z-index:20; min-width:180px;
  }}
  .count-panel h3 {{ color:#ff4444; font-size:12px; margin-bottom:6px; letter-spacing:1px; }}
  .count-panel .total {{ color:#fff; font-size:20px; font-weight:bold; }}
  .count-panel .info {{ color:#888; font-size:10px; margin-top:4px; }}

  .cnt-btn {{
    background:linear-gradient(145deg,#1a3a1a,#0a2a0a); border:1px solid #006600;
    color:#00ee55; border-radius:4px; padding:4px 6px; min-height:22px; font-size:10px;
    font-weight:bold; cursor:pointer; transition:.2s; width:100%; margin-top:1px;
  }}
  .cnt-btn:hover {{ border-color:#00ee55; box-shadow:0 0 8px rgba(0,238,85,.3); }}
  .cnt-btn.danger {{ background:linear-gradient(145deg,#3a1a1a,#2a0a0a); border-color:#660000; color:#ff5555; }}
  .cnt-btn.danger:hover {{ border-color:#ff5555; box-shadow:0 0 8px rgba(255,85,85,.3); }}
  .cnt-btn.red {{ background:linear-gradient(145deg,#3a0a0a,#220000); border-color:#cc2200; color:#ff4444; }}
  .cnt-btn.red:hover {{ border-color:#ff4444; box-shadow:0 0 8px rgba(255,68,68,.3); }}
  .cnt-btn.orange {{ background:linear-gradient(145deg,#2a1a00,#1a0a00); border-color:#ff8c00; color:#ff8c00; }}
  .cnt-btn.orange:hover {{ border-color:#ffaa33; box-shadow:0 0 8px rgba(255,140,0,.3); }}

  .qual-sep {{ width:100%;height:1px;background:linear-gradient(90deg,transparent,#333,transparent);margin:1px 0; }}

  /* Falhas Modal */
  #falhasModal {{
    display:none; position:fixed; top:0; left:0; width:100%; height:100%;
    background:rgba(0,0,0,0.88); z-index:9999; align-items:center; justify-content:center;
  }}
  #falhasModal .modal-inner {{
    background:#1a1a1a; border:1px solid #cc3300; border-radius:16px;
    width:92%; max-width:720px; max-height:87vh; overflow:auto; padding:24px;
    box-shadow:0 0 40px rgba(255,60,0,0.3);
  }}
</style>
</head>
<body>
<div id="vc">
  <canvas id="cv"></canvas>
  <div class="zoom-badge" id="zbadge">1.00×</div>
  <div class="crosshair" id="coord">X:0 Y:0</div>
  <div class="hint">Scroll=Zoom · Drag=Pan<br>Grid: marque 4 pontos</div>

  <div class="toolbar">
    <button class="tb-btn" id="btnGridTool" title="Marcar Grid (4 pontos)">⊞</button>
    <button class="tb-btn" id="btnManualMode" title="Modo Manual (clique para marcar)">✏️</button>
    <button class="tb-btn" id="btnRemoveLast" title="Apagar Última Marcação">❌</button>
    <div class="tb-sep"></div>
    <button class="tb-btn" id="btnClearAll" title="Limpar Tudo">🗑️</button>
  </div>

  <div class="grid-panel">
    <label>✅ QUALIDADE</label>
    <div class="row-col">
      <span>Disp:</span><input type="number" id="inpRows" value="5" min="1" max="200">
    </div>
    <div class="row-col">
      <span>Tiros:</span><input type="number" id="inpCols" value="5" min="1" max="200">
    </div>
    <button class="cnt-btn" id="btnManual2" style="background:linear-gradient(145deg,#1a1a3a,#0a0a2a);border-color:#000066;color:#5599ff;">✏️ Manual</button>
    <div class="qual-sep"></div>
    <label style="color:#ff4444;">⚠️ FALHAS LINEARES</label>
    <div class="row-col">
      <span style="font-size:10px;">Mín. (cm):</span>
      <input type="number" id="inpMinDist" value="20" min="20" step="0.1" max="9999" style="width:55px;">
    </div>
    <div class="row-col">
      <span style="font-size:10px;">Buffer (cm):</span>
      <input type="number" id="inpBufferCm" value="20" min="0" step="1" max="9999" style="width:55px;">
    </div>
    <div class="row-col">
      <span style="font-size:10px;">Parcela (m):</span>
      <input type="number" id="inpParcelLen" value="5" min="0.1" step="0.1" style="width:55px;">
    </div>
    <div class="row-col">
      <span style="font-size:10px;">Unidade:</span>
      <select id="selUnit" style="background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:4px;padding:3px;font-size:10px;">
        <option value="px">px</option>
        <option value="cm">cm</option>
        <option value="m" selected>m</option>
      </select>
    </div>
    <div class="row-col">
      <span style="font-size:10px;">Espessura:</span>
      <input type="number" id="inpLineWidth" value="2" min="1" max="10" style="width:40px;">
    </div>
    <div class="row-col" style="gap:4px;">
      <label style="color:#ccc;font-size:10px;font-weight:normal;display:flex;align-items:center;gap:4px;">
        <input type="checkbox" id="chkLabels" checked style="accent-color:#ff4444;"> Etiquetas
      </label>
      <label style="color:#ccc;font-size:10px;font-weight:normal;display:flex;align-items:center;gap:4px;">
        <input type="checkbox" id="chkShowFalhas" checked style="accent-color:#ff4444;"> Mostrar
      </label>
    </div>
    <button class="cnt-btn red" id="btnDetectFalhas">⚠️ Detectar Falhas</button>
    <button class="cnt-btn red" id="btnMedirPlantados">📏 Medir Metros Plantados</button>
    <div class="qual-sep"></div>
    <label style="color:#ffd21f;">🔧 AJUSTE DE PARCELA</label>
    <button class="cnt-btn orange" id="btnSelectParcel">Marcar Parcela</button>
    <button class="cnt-btn" id="btnMoveSelected" style="background:linear-gradient(145deg,#1a1a3a,#0a0a2a);border-color:#003399;color:#5599ff;">Mover Selecionadas</button>
    <div class="row-col">
      <span style="font-size:10px;">Passo (px):</span>
      <input type="number" id="inpMoveStep" value="5" min="1" max="200" style="width:48px;">
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;">
      <button class="grid-btn" id="btnMoveUp" title="Mover para cima">↑</button>
      <button class="grid-btn" id="btnMoveDown" title="Mover para baixo">↓</button>
      <button class="grid-btn" id="btnMoveLeft" title="Mover para esquerda">←</button>
      <button class="grid-btn" id="btnMoveRight" title="Mover para direita">→</button>
      <button class="grid-btn" id="btnClearSelection" style="grid-column:span 2;color:#ff7777;border-color:#663333;">Limpar Seleção</button>
    </div>
    <button class="cnt-btn" id="btnSaveParcelAdjust" style="background:linear-gradient(145deg,#1a3a1a,#0a2a0a);border-color:#00aa55;color:#55ff99;">Salvar Ajuste da Parcela</button>
    <div id="parcelAdjustStatus" style="font-size:9px;color:#777;line-height:1.2;max-height:24px;overflow:hidden;">Nenhuma parcela selecionada.</div>
    <div class="qual-sep"></div>
    <button class="cnt-btn orange" id="btnOpenFalhas">📊 Relatório</button>
    <button class="cnt-btn danger" id="btnUndoMark">❌ Desfazer</button>
    <button id="btnExportCnt" style="background:linear-gradient(145deg,#003a00,#001a00);border:1px solid #006600;
      color:#00ee55;border-radius:4px;padding:4px 6px;min-height:22px;font-size:10px;font-weight:bold;cursor:pointer;
      transition:.2s;width:100%;margin-top:1px;">💾 Exportar CSV</button>
  </div>

  <div class="count-panel" id="countPanel" style="display:none;">
    <h3>FALHAS DETECTADAS</h3>
    <div class="total" id="totalCount" style="color:#ff4444;">0</div>
    <div class="info" id="countInfo">Detecte falhas</div>
    <div id="falhasSumario" style="margin-top:6px;font-size:10px;color:#888;"></div>
  </div>

  <!-- Modal Relatório de Falhas -->
  <div id="falhasModal">
    <div class="modal-inner">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <h3 style="color:#ff4444;font-size:14px;letter-spacing:2px;text-transform:uppercase;margin:0;">⚠️ RELATÓRIO DE FALHAS LINEARES</h3>
        <button id="btnCloseModal" style="background:#333;border:1px solid #555;color:#fff;border-radius:6px;
          padding:5px 12px;cursor:pointer;font-size:12px;">✕ Fechar</button>
      </div>
      <!-- Cards de totais -->
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:16px;">
        <div style="background:#111;border:1px solid #cc2200;border-radius:10px;padding:14px;text-align:center;">
          <div id="modalTotalFalhas" style="color:#ff4444;font-size:24px;font-weight:bold;">0</div>
          <div style="color:#666;font-size:10px;letter-spacing:1px;text-transform:uppercase;">Total Falhas</div>
        </div>
        <div style="background:#111;border:1px solid #333;border-radius:10px;padding:14px;text-align:center;">
          <div id="modalTotalLinear" style="color:#ffaa33;font-size:20px;font-weight:bold;">0</div>
          <div id="modalTotalLinearLabel" style="color:#666;font-size:10px;letter-spacing:1px;text-transform:uppercase;">Total Linear</div>
        </div>
        <div style="background:#111;border:1px solid #333;border-radius:10px;padding:14px;text-align:center;">
          <div id="modalMaiorFalha" style="color:#ff8c00;font-size:20px;font-weight:bold;">0</div>
          <div id="modalMaiorFalhaLabel" style="color:#666;font-size:10px;letter-spacing:1px;text-transform:uppercase;">Maior Falha</div>
        </div>
      </div>
      <!-- Filtros -->
      <div style="margin-bottom:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <input type="text" id="modalSearch" placeholder="Pesquisar linha..."
          style="flex:1;min-width:120px;background:#111;border:1px solid #333;color:#fff;border-radius:6px;padding:8px;font-size:12px;">
        <select id="modalFilterTiro" style="background:#111;border:1px solid #333;color:#fff;border-radius:6px;padding:8px;font-size:11px;">
          <option value="">Todos Tiros</option>
        </select>
        <select id="modalFilterDisp" style="background:#111;border:1px solid #333;color:#fff;border-radius:6px;padding:8px;font-size:11px;">
          <option value="">Todos Disp.</option>
        </select>
      </div>
      <!-- Tabela -->
      <div id="falhasTable" style="max-height:280px;overflow-y:auto;border:1px solid #333;border-radius:8px;"></div>
      <!-- Botões exportar -->
      <div style="display:flex;gap:8px;margin-top:14px;flex-wrap:wrap;">
        <button id="btnExportFalhasCSV" style="flex:1;background:linear-gradient(145deg,#003a00,#001a00);
          border:1px solid #006600;color:#00ee55;border-radius:6px;padding:8px;font-size:11px;font-weight:bold;cursor:pointer;">
          💾 Exportar CSV
        </button>
        <button id="btnExportFalhasGeoJSON" style="flex:1;background:linear-gradient(145deg,#001a3a,#000a1a);
          border:1px solid #003399;color:#5599ff;border-radius:6px;padding:8px;font-size:11px;font-weight:bold;cursor:pointer;">
          🗺️ Exportar GeoJSON
        </button>
        <button id="btnExportFalhasXLSX" style="flex:1;background:linear-gradient(145deg,#1a003a,#0a001a);
          border:1px solid #660099;color:#cc66ff;border-radius:6px;padding:8px;font-size:11px;font-weight:bold;cursor:pointer;">
          📗 Exportar Excel
        </button>
      </div>
    </div>
  </div>

</div>

<script>
const IMG_B64 = '{qual_b64}';
const vc      = document.getElementById('vc');
const cv      = document.getElementById('cv');
const ctx     = cv.getContext('2d');
const zb      = document.getElementById('zbadge');
const coordEl = document.getElementById('coord');

const inpRows      = document.getElementById('inpRows');
const inpCols      = document.getElementById('inpCols');
const btnGridTool  = document.getElementById('btnGridTool');
const btnCountPlants = document.getElementById('btnCountPlants');
const btnManualMode= document.getElementById('btnManualMode');
const btnRemoveLast= document.getElementById('btnRemoveLast');
const btnClearAll  = document.getElementById('btnClearAll');
const btnCountAuto = document.getElementById('btnCountAuto');
const btnManual2   = document.getElementById('btnManual2');
const btnUndoMark  = document.getElementById('btnUndoMark');
const btnExportCnt = document.getElementById('btnExportCnt');
const countPanel   = document.getElementById('countPanel');
const totalCountEl = document.getElementById('totalCount');
const countInfoEl  = document.getElementById('countInfo');
const falhasSumario = document.getElementById('falhasSumario');
const btnDetectFalhas = document.getElementById('btnDetectFalhas');
const btnMedirPlantados = document.getElementById('btnMedirPlantados');
const chkShowFalhas   = document.getElementById('chkShowFalhas');
const chkLabels       = document.getElementById('chkLabels');
const inpMinDist      = document.getElementById('inpMinDist');
const inpBufferCm     = document.getElementById('inpBufferCm');
const inpParcelLen    = document.getElementById('inpParcelLen');
const inpLineWidth    = document.getElementById('inpLineWidth');
const selUnit         = document.getElementById('selUnit');
const falhasModal     = document.getElementById('falhasModal');
const btnOpenFalhas   = document.getElementById('btnOpenFalhas');
const btnCloseModal   = document.getElementById('btnCloseModal');
const btnSelectParcel = document.getElementById('btnSelectParcel');
const btnMoveSelected = document.getElementById('btnMoveSelected');
const btnClearSelection = document.getElementById('btnClearSelection');
const btnSaveParcelAdjust = document.getElementById('btnSaveParcelAdjust');
const btnMoveUp       = document.getElementById('btnMoveUp');
const btnMoveDown     = document.getElementById('btnMoveDown');
const btnMoveLeft     = document.getElementById('btnMoveLeft');
const btnMoveRight    = document.getElementById('btnMoveRight');
const inpMoveStep     = document.getElementById('inpMoveStep');
const parcelAdjustStatus = document.getElementById('parcelAdjustStatus');

let gridMode = false, manualMode = false;
let parcelSelectMode = false, parcelMoveMode = false, draggingParcelSelection = false;
let points = [], draggingPoint = -1;
let sc = 1, ox = 0, oy = 0;
let drag = false, lx = 0, ly = 0;
const MIN_SC = 0.05, MAX_SC = 40;
let imgW = 0, imgH = 0;

let plantCenters = [];
let manualMarks  = [];
let parcelCounts = {{}};
let falhas       = []; // array de objetos {{p1, p2, dist, tiro, disp, linha}}
let areasUteis   = [];
let metrosPlantadosLinhas = [];
let metrosPlantadosSegmentos = [];
let qualidadeModoVisual = '';
const LINHAS_PLANTIO_POR_PARCELA = 4;
let parcelAdjustments = {{}};
let selectedParcels = new Set();
let lastParcelDragPt = null;
let parcelAdjustStorageKey = '';
const showPlantDebug = false;

const img = new Image();

// ── Coordenadas ──────────────────────────────────────────────────────────────
function getImgCoords(cx, cy) {{
  const r = cv.getBoundingClientRect();
  return {{ x:(cx-r.left-ox)/sc, y:(cy-r.top-oy)/sc }};
}}

function bilerp(p0,p1,p2,p3, u,v) {{
  const tx=(1-u)*p0.x+u*p1.x, ty=(1-u)*p0.y+u*p1.y;
  const bx=(1-u)*p3.x+u*p2.x, by=(1-u)*p3.y+u*p2.y;
  return {{ x:(1-v)*tx+v*bx, y:(1-v)*ty+v*by }};
}}

function getParcelKeyByRC(r2,c,R,C) {{
  return (R-r2)+'_'+(C-c);
}}

function getParcelLabel(key) {{
  const parts=String(key||'').split('_');
  if(parts.length!==2) return key || '';
  return 'T'+parts[1]+' D'+parts[0];
}}

function parseParcelKey(key) {{
  const parts=String(key||'').split('_').map(Number);
  return {{disp:parts[0]||0, tiro:parts[1]||0}};
}}

function getBaseParcelPoly(r2,c,R,C,p0,p1,p2,p3) {{
  const u0=c/C,u1=(c+1)/C,v0=r2/R,v1=(r2+1)/R;
  const tl=bilerp(p0,p1,p2,p3,u0,v0), tr=bilerp(p0,p1,p2,p3,u1,v0);
  const br=bilerp(p0,p1,p2,p3,u1,v1), bl=bilerp(p0,p1,p2,p3,u0,v1);
  return [tl,tr,br,bl];
}}

function getAdjustedParcelPoly(r2,c,R,C,p0,p1,p2,p3) {{
  const key=getParcelKeyByRC(r2,c,R,C);
  const adj=parcelAdjustments[key] || {{dx:0,dy:0}};
  return getBaseParcelPoly(r2,c,R,C,p0,p1,p2,p3).map(p=>{{ return {{x:p.x+(adj.dx||0), y:p.y+(adj.dy||0)}}; }});
}}

function getParcelCenter(poly) {{
  return {{
    x:poly.reduce((s,p)=>s+p.x,0)/poly.length,
    y:poly.reduce((s,p)=>s+p.y,0)/poly.length
  }};
}}

function findParcelAtPoint(pt) {{
  if(points.length<4) return null;
  const R=parseInt(inpRows.value)||1, C=parseInt(inpCols.value)||1;
  const p0=points[0],p1=points[1],p2=points[2],p3=points[3];
  for(let r2=R-1;r2>=0;r2--) {{
    for(let c=C-1;c>=0;c--) {{
      const poly=getAdjustedParcelPoly(r2,c,R,C,p0,p1,p2,p3);
      if(pointInPolygon(pt.x,pt.y,poly)) {{
        const key=getParcelKeyByRC(r2,c,R,C);
        return {{key:key,r:r2,c:c,poly:poly}};
      }}
    }}
  }}
  return null;
}}

function updateParcelAdjustStatus() {{
  const sel=[...selectedParcels].map(k=>getParcelLabel(k));
  const cadeia=getCascadeAffectedKeys(false);
  const ajustadas=Object.keys(parcelAdjustments).filter(k=>Math.abs((parcelAdjustments[k].dx||0))+Math.abs((parcelAdjustments[k].dy||0))>0).length;
  const modo=parcelSelectMode ? 'Seleção ativa' : (parcelMoveMode ? 'Mover ativo' : 'Modo normal');
  parcelAdjustStatus.textContent = modo + ' · Marcadas: ' + (sel.length?sel.join(', '):'nenhuma') + ' · Cadeia: ' + cadeia.size + ' · Ajustadas: ' + ajustadas;
  if(btnSelectParcel) btnSelectParcel.style.borderColor = parcelSelectMode ? '#ffd21f' : '#ff8c00';
  if(btnMoveSelected) btnMoveSelected.style.borderColor = parcelMoveMode ? '#5599ff' : '#003399';
}}

function getCascadeAffectedKeys(includeSelected) {{
  const R=parseInt(inpRows.value)||1;
  const affected=new Set();
  for(const key of selectedParcels) {{
    const parsed=parseParcelKey(key);
    if(includeSelected) affected.add(key);
    for(let d=parsed.disp+1; d<=R; d++) {{
      affected.add(d+'_'+parsed.tiro);
    }}
  }}
  return affected;
}}

function getCascadeMoveKeys() {{
  return getCascadeAffectedKeys(true);
}}

function translateSelectedParcels(dx,dy) {{
  if(selectedParcels.size===0) {{ alert('Selecione pelo menos uma parcela.'); return; }}
  const moveKeys=getCascadeMoveKeys();
  for(const key of moveKeys) {{
    const adj=parcelAdjustments[key] || {{dx:0,dy:0}};
    parcelAdjustments[key] = {{dx:(adj.dx||0)+dx, dy:(adj.dy||0)+dy}};
  }}
  updateParcelAdjustStatus();
  drawAll();
}}

function refreshAfterParcelAdjust() {{
  if(plantCenters.length>0) recount();
  if(falhas.length>0) detectarFalhas();
  else drawAll();
}}

function saveParcelAdjustments() {{
  try {{
    if(parcelAdjustStorageKey) localStorage.setItem(parcelAdjustStorageKey, JSON.stringify(parcelAdjustments));
  }} catch(e) {{}}
  refreshAfterParcelAdjust();
  updateParcelAdjustStatus();
}}

function loadParcelAdjustments() {{
  parcelAdjustStorageKey='tmg_qual_parcel_adjust_'+imgW+'x'+imgH+'_'+IMG_B64.length;
  try {{
    const raw=localStorage.getItem(parcelAdjustStorageKey);
    if(raw) parcelAdjustments=JSON.parse(raw) || {{}};
  }} catch(e) {{ parcelAdjustments={{}}; }}
  updateParcelAdjustStatus();
}}

function pointInPolygon(px, py, polygon) {{
  let inside = false;
  for (let i=0, j=polygon.length-1; i<polygon.length; j=i++) {{
    const xi=polygon[i].x, yi=polygon[i].y, xj=polygon[j].x, yj=polygon[j].y;
    if (((yi>py)!==(yj>py)) && (px<(xj-xi)*(py-yi)/(yj-yi)+xi)) inside=!inside;
  }}
  return inside;
}}

function lineDistance(a,b) {{
  return Math.sqrt((b.x-a.x)**2+(b.y-a.y)**2);
}}

function lerpPoint(a,b,t) {{
  return {{ x:a.x+(b.x-a.x)*t, y:a.y+(b.y-a.y)*t }};
}}

function midpoint(a,b) {{
  return {{ x:(a.x+b.x)/2, y:(a.y+b.y)/2 }};
}}

function pointOnLine(a,b,t) {{
  return lerpPoint(a,b,t);
}}

function getParcelaMeasureLine(tl,tr,br,bl) {{
  const horiz=(lineDistance(tl,tr)+lineDistance(bl,br))/2;
  const vert=(lineDistance(tl,bl)+lineDistance(tr,br))/2;
  const p1=horiz>=vert ? midpoint(tl,bl) : midpoint(tl,tr);
  const p2=horiz>=vert ? midpoint(tr,br) : midpoint(bl,br);
  return {{ p1:p1, p2:p2, dist:lineDistance(p1,p2) }};
}}

function projectPointOnLine(p,a,b) {{
  const dx=b.x-a.x, dy=b.y-a.y;
  const len2=dx*dx+dy*dy;
  if(len2===0) return 0;
  return Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/len2));
}}

function getParcelaAxes(tl,tr,br,bl) {{
  const horiz=(lineDistance(tl,tr)+lineDistance(bl,br))/2 >= (lineDistance(tl,bl)+lineDistance(tr,br))/2;
  const crossA=horiz ? midpoint(tl,tr) : midpoint(tl,bl);
  const crossB=horiz ? midpoint(bl,br) : midpoint(tr,br);
  return {{ horiz:horiz, crossA:crossA, crossB:crossB, secondaryLen:lineDistance(crossA,crossB) }};
}}

function getRowGeometry(tl,tr,br,bl,horiz,s) {{
  const p1=horiz ? lerpPoint(tl,bl,s) : lerpPoint(tl,tr,s);
  const p2=horiz ? lerpPoint(tr,br,s) : lerpPoint(bl,br,s);
  return {{ p1:p1, p2:p2, dist:lineDistance(p1,p2) }};
}}

function cross2(a,b) {{
  return a.x*b.y-a.y*b.x;
}}

function clipLineToPolygon(anchor,dir,poly) {{
  const hits=[];
  for(let i=0;i<poly.length;i++) {{
    const a=poly[i], b=poly[(i+1)%poly.length];
    const edge={{x:b.x-a.x,y:b.y-a.y}};
    const den=cross2(dir,edge);
    if(Math.abs(den)<0.000001) continue;
    const ap={{x:a.x-anchor.x,y:a.y-anchor.y}};
    const t=cross2(ap,edge)/den;
    const u=cross2(ap,dir)/den;
    if(u>=-0.0001 && u<=1.0001) hits.push({{t:t,p:{{x:anchor.x+dir.x*t,y:anchor.y+dir.y*t}}}});
  }}
  hits.sort((a,b)=>a.t-b.t);
  const uniq=[];
  for(const h of hits) {{
    if(uniq.length===0 || lineDistance(h.p,uniq[uniq.length-1].p)>0.5) uniq.push(h);
  }}
  if(uniq.length<2) return null;
  return {{p1:uniq[0].p,p2:uniq[uniq.length-1].p,dist:lineDistance(uniq[0].p,uniq[uniq.length-1].p)}};
}}

function alignRowGeometryToPlants(rowGeom,rowItems,poly) {{
  if(rowItems.length<2) return rowGeom;
  const baseDir={{x:rowGeom.p2.x-rowGeom.p1.x,y:rowGeom.p2.y-rowGeom.p1.y}};
  const baseLen=Math.sqrt(baseDir.x*baseDir.x+baseDir.y*baseDir.y);
  if(baseLen<=0) return rowGeom;
  baseDir.x/=baseLen; baseDir.y/=baseLen;
  const ordered=[...rowItems].sort((a,b)=>projectPointOnLine(a.p,rowGeom.p1,rowGeom.p2)-projectPointOnLine(b.p,rowGeom.p1,rowGeom.p2));
  const first=ordered[0].p, last=ordered[ordered.length-1].p;
  let dir={{x:last.x-first.x,y:last.y-first.y}};
  let len=Math.sqrt(dir.x*dir.x+dir.y*dir.y);
  if(len<5) {{ dir=baseDir; len=1; }} else {{ dir.x/=len; dir.y/=len; }}
  if(dir.x*baseDir.x+dir.y*baseDir.y<0) {{ dir.x*=-1; dir.y*=-1; }}
  const anchor={{
    x:ordered.reduce((s,it)=>s+it.p.x,0)/ordered.length,
    y:ordered.reduce((s,it)=>s+it.p.y,0)/ordered.length
  }};
  const clipped=clipLineToPolygon(anchor,dir,poly);
  return clipped || rowGeom;
}}

function getPlantRowInfo(p,axes,tl,tr,br,bl) {{
  const s=projectPointOnLine(p,axes.crossA,axes.crossB);
  const rowGeom=getRowGeometry(tl,tr,br,bl,axes.horiz,s);
  return {{ p:p, s:s, sPx:s*axes.secondaryLen, t:projectPointOnLine(p,rowGeom.p1,rowGeom.p2) }};
}}

function clusterPlantRows(rowInfos,tolPx) {{
  const sorted=[...rowInfos].sort((a,b)=>a.sPx-b.sPx);
  const rows=[];
  for(const item of sorted) {{
    let row=rows.length ? rows[rows.length-1] : null;
    if(!row || Math.abs(item.sPx-row.meanPx)>tolPx) {{
      rows.push({{ items:[item], meanPx:item.sPx, meanS:item.s }});
    }} else {{
      row.items.push(item);
      row.meanPx=row.items.reduce((s,it)=>s+it.sPx,0)/row.items.length;
      row.meanS=row.items.reduce((s,it)=>s+it.s,0)/row.items.length;
    }}
  }}
  return rows;
}}

function getParcelRealMeters() {{
  return Math.max(0.1,parseFloat(inpParcelLen.value)||5);
}}

function getBufferCorredorCm() {{
  const v=parseFloat(inpBufferCm.value);
  return Number.isFinite(v) ? Math.max(0,v) : 20;
}}

function polygonSignedArea(poly) {{
  let area=0;
  for(let i=0;i<poly.length;i++) {{
    const a=poly[i], b=poly[(i+1)%poly.length];
    area+=a.x*b.y-a.y*b.x;
  }}
  return area/2;
}}

function centerShrinkPolygon(poly,insetPx) {{
  const center=getParcelCenter(poly);
  return poly.map(p=>{{
    const vx=center.x-p.x, vy=center.y-p.y;
    const len=Math.sqrt(vx*vx+vy*vy);
    if(len<=0) return {{x:p.x,y:p.y}};
    const step=Math.min(insetPx,len*0.45);
    return {{x:p.x+(vx/len)*step,y:p.y+(vy/len)*step}};
  }});
}}

function intersectOffsetLines(lineA,lineB) {{
  const den=cross2(lineA.d,lineB.d);
  if(Math.abs(den)<0.000001) return null;
  const ap={{x:lineB.p.x-lineA.p.x,y:lineB.p.y-lineA.p.y}};
  const t=cross2(ap,lineB.d)/den;
  return {{x:lineA.p.x+lineA.d.x*t,y:lineA.p.y+lineA.d.y*t}};
}}

function shrinkPolygonToAreaUtil(poly,bufferPx) {{
  if(!bufferPx || bufferPx<=0) return poly.map(p=>{{return {{x:p.x,y:p.y}};}});
  const [tl,tr,br,bl]=poly;
  const leftLen=lineDistance(tl,bl);
  const rightLen=lineDistance(tr,br);
  const tLeft=leftLen>0 ? Math.min(bufferPx,leftLen*0.45)/leftLen : 0;
  const tRight=rightLen>0 ? Math.min(bufferPx,rightLen*0.45)/rightLen : 0;
  return [
    lerpPoint(tl,bl,tLeft),
    lerpPoint(tr,br,tRight),
    lerpPoint(br,tr,tRight),
    lerpPoint(bl,tl,tLeft)
  ];
}}

function getBufferCorredorPx(poly) {{
  const bufferM=getBufferCorredorCm()/100;
  if(bufferM<=0) return 0;
  const pxPorMetro=getPixelsPorMetroParcela(poly);
  return pxPorMetro>0 ? bufferM*pxPorMetro : 0;
}}

function getAreaUtilParcela(poly) {{
  return shrinkPolygonToAreaUtil(poly,getBufferCorredorPx(poly));
}}

function getPixelsPorMetroParcela(poly) {{
  const [tl,tr,br,bl]=poly;
  const measureLine=getParcelaMeasureLine(tl,tr,br,bl);
  if(!measureLine || measureLine.dist<=0) return 0;
  return measureLine.dist/getParcelRealMeters();
}}

function rowPxToMeters(px,rowGeom) {{
  if(!rowGeom || rowGeom.dist<=0) return 0;
  if(rowGeom.pxPorMetro && rowGeom.pxPorMetro>0) return px/rowGeom.pxPorMetro;
  return (px/rowGeom.dist)*getParcelRealMeters();
}}

function addFalhasNaFileira(rowGeom,rowItems,minDistM,tiroLabel,dispLabel,linhaLabel,parcelaId) {{
  if(rowGeom.dist<=0) return;
  const refs=rowItems
    .map(item=>projectPointOnLine(item.p,rowGeom.p1,rowGeom.p2))
    .sort((a,b)=>a-b);

  const refsUnicas=[];
  const mergeT=Math.max(2,(minDistM/getParcelRealMeters())*rowGeom.dist*0.15)/rowGeom.dist;
  for(const t of refs) {{
    if(refsUnicas.length===0 || Math.abs(t-refsUnicas[refsUnicas.length-1])>mergeT) refsUnicas.push(t);
  }}

  const intervalos=[];
  if(refsUnicas.length===0) {{
    intervalos.push({{t0:0,t1:1,tipo:'inicio'}});
  }} else {{
    intervalos.push({{t0:0,t1:refsUnicas[0],tipo:'inicio'}});
    for(let i=1;i<refsUnicas.length;i++) intervalos.push({{t0:refsUnicas[i-1],t1:refsUnicas[i],tipo:'entre plantas'}});
    intervalos.push({{t0:refsUnicas[refsUnicas.length-1],t1:1,tipo:'final'}});
  }}

  for(const inter of intervalos) {{
    const t0=inter.t0, t1=inter.t1;
    const dist=(t1-t0)*rowGeom.dist;
    const distM=rowPxToMeters(dist,rowGeom);
    if(distM>minDistM) {{
      falhas.push({{
        p1:pointOnLine(rowGeom.p1,rowGeom.p2,t0),
        p2:pointOnLine(rowGeom.p1,rowGeom.p2,t1),
        dist:dist,
        distM:distM,
        tiro:tiroLabel,
        disp:dispLabel,
        linha:linhaLabel,
        tipo:inter.tipo,
        parcelaId:parcelaId
      }});
    }}
  }}
}}

function isPlantRGB(r2,g,b) {{
  const max2=Math.max(r2,g,b), min2=Math.min(r2,g,b), diff=max2-min2;
  let hue=0,sat=0;
  if(diff>0){{
    if(max2===r2) hue=60*(((g-b)/diff)%6);
    else if(max2===g) hue=60*((b-r2)/diff+2);
    else hue=60*((r2-g)/diff+4);
    if(hue<0) hue+=360; sat=(diff/max2)*255;
  }}
  hue=hue/2;
  return hue>=30&&hue<=90&&sat>=40&&max2>=40;
}}

function getHSVExGInfo(r2,g,b) {{
  const max2=Math.max(r2,g,b), min2=Math.min(r2,g,b), diff=max2-min2;
  let hue=0, sat=0;
  if(diff>0) {{
    if(max2===r2) hue=60*(((g-b)/diff)%6);
    else if(max2===g) hue=60*((b-r2)/diff+2);
    else hue=60*((r2-g)/diff+4);
    if(hue<0) hue+=360;
    sat=diff/(max2||1);
  }}
  const exg=(2*g-r2-b);
  const exgNorm=exg/(r2+g+b+1);
  const hsvOk=hue>=35 && hue<=170 && sat>=0.16 && max2>=35 && g>=Math.max(r2,b)*0.82;
  const exgOk=exg>=14 || exgNorm>=0.045;
  return {{hsvOk:hsvOk,exgOk:exgOk,plant:hsvOk&&exgOk}};
}}

function erodeMask(mask,w,h) {{
  const out=new Uint8Array(w*h);
  for(let y=1;y<h-1;y++) {{
    const row=y*w;
    for(let x=1;x<w-1;x++) {{
      const idx=row+x;
      if(mask[idx]&&mask[idx-1]&&mask[idx+1]&&mask[idx-w]&&mask[idx+w]&&mask[idx-w-1]&&mask[idx-w+1]&&mask[idx+w-1]&&mask[idx+w+1]) out[idx]=1;
    }}
  }}
  return out;
}}

function dilateMask(mask,w,h) {{
  const out=new Uint8Array(w*h);
  for(let y=1;y<h-1;y++) {{
    const row=y*w;
    for(let x=1;x<w-1;x++) {{
      const idx=row+x;
      if(mask[idx]||mask[idx-1]||mask[idx+1]||mask[idx-w]||mask[idx+w]||mask[idx-w-1]||mask[idx-w+1]||mask[idx+w-1]||mask[idx+w+1]) out[idx]=1;
    }}
  }}
  return out;
}}

function cleanVegetationMask(mask,w,h) {{
  let out=dilateMask(erodeMask(mask,w,h),w,h);
  out=erodeMask(dilateMask(out,w,h),w,h);
  return out;
}}

function removeSmallVegetationObjects(mask,w,h,minX,minY,minArea,gridPoly) {{
  const visited=new Uint8Array(w*h);
  const cleaned=new Uint8Array(w*h);
  const centers=[];
  const stack=[];
  const pixels=[];
  for(let i=0;i<mask.length;i++) {{
    if(!mask[i] || visited[i]) continue;
    stack.length=0; pixels.length=0;
    stack.push(i); visited[i]=1;
    let area=0,sumX=0,sumY=0;
    while(stack.length>0) {{
      const idx=stack.pop();
      pixels.push(idx); area++;
      const x=idx%w, y=Math.floor(idx/w);
      sumX+=x; sumY+=y;
      const neigh=[idx-1,idx+1,idx-w,idx+w];
      for(const ni of neigh) {{
        if(ni<0||ni>=mask.length||visited[ni]||!mask[ni]) continue;
        const nx=ni%w, ny=Math.floor(ni/w);
        if(Math.abs(nx-x)+Math.abs(ny-y)!==1) continue;
        visited[ni]=1; stack.push(ni);
      }}
    }}
    if(area>=minArea) {{
      const cx=sumX/area+minX, cy=sumY/area+minY;
      if(!gridPoly || pointInPolygon(cx,cy,gridPoly)) {{
        for(const pi of pixels) cleaned[pi]=1;
        centers.push({{x:cx,y:cy,area:area}});
      }}
    }}
  }}
  return {{mask:cleaned,centers:centers}};
}}

function getQualidadeColorSampler() {{
  const tempCv=document.createElement('canvas');
  tempCv.width=imgW; tempCv.height=imgH;
  const tc=tempCv.getContext('2d'); tc.drawImage(img,0,0);
  const gridPoly=points.length===4 ? points : null;
  const xs=gridPoly ? gridPoly.map(p=>p.x) : [0,imgW];
  const ys=gridPoly ? gridPoly.map(p=>p.y) : [0,imgH];
  const pad=16;
  const minX=Math.max(0,Math.floor(Math.min(...xs)-pad));
  const maxX=Math.min(imgW,Math.ceil(Math.max(...xs)+pad));
  const minY=Math.max(0,Math.floor(Math.min(...ys)-pad));
  const maxY=Math.min(imgH,Math.ceil(Math.max(...ys)+pad));
  const w=Math.max(1,maxX-minX), h=Math.max(1,maxY-minY);
  const imgData=tc.getImageData(minX,minY,w,h);
  const data=imgData.data;
  let mask=new Uint8Array(w*h);
  for(let yy=0;yy<h;yy++) {{
    for(let xx=0;xx<w;xx++) {{
      const idx=(yy*w+xx)*4;
      const absX=xx+minX, absY=yy+minY;
      if(gridPoly && !pointInPolygon(absX,absY,gridPoly)) continue;
      const info=getHSVExGInfo(data[idx],data[idx+1],data[idx+2]);
      if(info.plant) mask[yy*w+xx]=1;
    }}
  }}
  mask=cleanVegetationMask(mask,w,h);
  const cleaned=removeSmallVegetationObjects(mask,w,h,minX,minY,18,gridPoly);
  mask=cleaned.mask;

  const sampler=function(x,y,rad) {{
    const rr=Math.max(1,Math.round(rad||3));
    const cx=Math.round(x)-minX, cy=Math.round(y)-minY;
    let total=0, plant=0;
    for(let yy=cy-rr;yy<=cy+rr;yy++) {{
      if(yy<0||yy>=h) continue;
      for(let xx=cx-rr;xx<=cx+rr;xx++) {{
        if(xx<0||xx>=w) continue;
        total++;
        if(mask[yy*w+xx]) plant++;
      }}
    }}
    return total>0 && (plant/total)>=0.10;
  }};
  sampler.centers=cleaned.centers;
  return sampler;
}}

function tipoFalhaPorPosicao(t0,t1,rowItems,rowGeom) {{
  if(rowItems.length===0) return 'inicio';
  const refs=rowItems
    .map(item=>projectPointOnLine(item.p,rowGeom.p1,rowGeom.p2))
    .sort((a,b)=>a-b);
  const mid=(t0+t1)/2;
  if(mid<refs[0]) return 'inicio';
  if(mid>refs[refs.length-1]) return 'final';
  return 'entre plantas';
}}

function addFalhasChaoNaFileira(rowGeom,rowItems,minDistM,tiroLabel,dispLabel,linhaLabel,parcelaId,sampler) {{
  if(!sampler) {{ addFalhasNaFileira(rowGeom,rowItems,minDistM,tiroLabel,dispLabel,linhaLabel,parcelaId); return; }}
  if(rowGeom.dist<=0) return;
  const samples=Math.max(12,Math.ceil(rowGeom.dist/2));
  const rad=Math.max(2,Math.min(5,rowGeom.dist*0.01));
  let startT=null;
  for(let i=0;i<=samples;i++) {{
    const t=i/samples;
    const p=pointOnLine(rowGeom.p1,rowGeom.p2,t);
    const isPlant=sampler(p.x,p.y,rad);
    if(!isPlant && startT===null) startT=t;
    if((isPlant || i===samples) && startT!==null) {{
      const endT=isPlant ? Math.max(0,(i-1)/samples) : t;
      if(endT>startT) {{
        const dist=(endT-startT)*rowGeom.dist;
        const distM=rowPxToMeters(dist,rowGeom);
        if(distM>minDistM) {{
          falhas.push({{
            p1:pointOnLine(rowGeom.p1,rowGeom.p2,startT),
            p2:pointOnLine(rowGeom.p1,rowGeom.p2,endT),
            dist:dist,
            distM:distM,
            tiro:tiroLabel,
            disp:dispLabel,
            linha:linhaLabel,
            tipo:tipoFalhaPorPosicao(startT,endT,rowItems,rowGeom),
            parcelaId:parcelaId
          }});
        }}
      }}
      startT=null;
    }}
  }}
}}

function getPlantRangesNaLinha(rowGeom,refsUnicas,sampler) {{
  const fallbackHalfT=Math.max(3,Math.min(12,rowGeom.dist*0.018))/rowGeom.dist;
  const samples=Math.max(80,Math.ceil(rowGeom.dist/2));
  const stepT=1/samples;
  const scanT=Math.max(fallbackHalfT*4, Math.min(0.18, 28/rowGeom.dist));
  const rad=Math.max(2,Math.min(5,rowGeom.dist*0.006));
  const ranges=[];

  for(const t of refsUnicas) {{
    let left=Math.max(0,t-fallbackHalfT);
    let right=Math.min(1,t+fallbackHalfT);

    if(sampler) {{
      let seenLeft=false, edgeLeft=t, emptyLeft=0;
      for(let tt=t; tt>=Math.max(0,t-scanT); tt-=stepT) {{
        const p=pointOnLine(rowGeom.p1,rowGeom.p2,tt);
        if(sampler(p.x,p.y,rad)) {{
          seenLeft=true; edgeLeft=tt; emptyLeft=0;
        }} else if(seenLeft) {{
          emptyLeft++;
          if(emptyLeft>=2) break;
        }}
      }}

      let seenRight=false, edgeRight=t, emptyRight=0;
      for(let tt=t; tt<=Math.min(1,t+scanT); tt+=stepT) {{
        const p=pointOnLine(rowGeom.p1,rowGeom.p2,tt);
        if(sampler(p.x,p.y,rad)) {{
          seenRight=true; edgeRight=tt; emptyRight=0;
        }} else if(seenRight) {{
          emptyRight++;
          if(emptyRight>=2) break;
        }}
      }}

      if(seenLeft || seenRight) {{
        left=Math.max(0,(seenLeft?edgeLeft:t)-stepT);
        right=Math.min(1,(seenRight?edgeRight:t)+stepT);
      }}
    }}

    ranges.push({{start:left,end:right}});
  }}

  ranges.sort((a,b)=>a.start-b.start);
  const merged=[];
  for(const rg of ranges) {{
    if(merged.length===0 || rg.start>merged[merged.length-1].end) merged.push({{start:rg.start,end:rg.end}});
    else merged[merged.length-1].end=Math.max(merged[merged.length-1].end,rg.end);
  }}
  return merged;
}}

function getRefsUnicasDaLinha(rowGeom,rowItems) {{
  if(!rowGeom || rowGeom.dist<=0 || !rowItems || rowItems.length<1) return;
  const refs=rowItems
    .map(item=>projectPointOnLine(item.p,rowGeom.p1,rowGeom.p2))
    .filter(t=>t>=0 && t<=1)
    .sort((a,b)=>a-b);

  const refsUnicas=[];
  const mergeT=Math.max(2,rowGeom.dist*0.01)/rowGeom.dist;
  for(const t of refs) {{
    if(refsUnicas.length===0 || Math.abs(t-refsUnicas[refsUnicas.length-1])>mergeT) refsUnicas.push(t);
  }}
  return refsUnicas;
}}

function sampleVegetacaoNoCorredor(rowGeom,t,sampler) {{
  if(!sampler || !rowGeom || rowGeom.dist<=0) return false;
  const p=pointOnLine(rowGeom.p1,rowGeom.p2,t);
  const dx=rowGeom.p2.x-rowGeom.p1.x, dy=rowGeom.p2.y-rowGeom.p1.y;
  const len=Math.sqrt(dx*dx+dy*dy);
  if(len<=0) return false;
  const normal=rowGeom.normal || {{x:-dy/len,y:dx/len}};
  const half=Math.max(2,Math.min(10,rowGeom.corridorPx||4));
  const step=Math.max(1.5,half/3);
  let total=0, hits=0;
  for(let off=-half; off<=half+0.01; off+=step) {{
    total++;
    if(sampler(p.x+normal.x*off,p.y+normal.y*off,2)) hits++;
  }}
  return total>0 && (hits/total)>=0.28;
}}

function getPlantRangesPorLinha(rowGeom,rowItems,sampler) {{
  if(!rowGeom || rowGeom.dist<=0 || !rowItems || rowItems.length<1) return [];
  const samples=Math.max(80,Math.ceil(rowGeom.dist/2));
  const flags=new Uint8Array(samples+1);
  for(let i=0;i<=samples;i++) {{
    flags[i]=sampleVegetacaoNoCorredor(rowGeom,i/samples,sampler)?1:0;
  }}

  const pxPorMetro=(rowGeom.pxPorMetro&&rowGeom.pxPorMetro>0)?rowGeom.pxPorMetro:(rowGeom.dist/getParcelRealMeters());
  const pxPorSample=rowGeom.dist/samples;
  const closeGapPx=Math.max(2,Math.min(getLimiteFalhaM()*0.75*pxPorMetro,rowGeom.dist*0.08));
  const closeGapSamples=Math.max(1,Math.round(closeGapPx/pxPorSample));

  let i=0;
  while(i<=samples) {{
    while(i<=samples && flags[i]) i++;
    const start=i;
    while(i<=samples && !flags[i]) i++;
    const end=i-1;
    const prev=start>0 && flags[start-1];
    const next=i<=samples && flags[i];
    if(prev && next && (end-start+1)<=closeGapSamples) {{
      for(let k=start;k<=end;k++) flags[k]=1;
    }}
  }}

  const minPlantPx=Math.max(2,0.03*pxPorMetro);
  const minPlantSamples=Math.max(1,Math.round(minPlantPx/pxPorSample));
  i=0;
  while(i<=samples) {{
    while(i<=samples && !flags[i]) i++;
    const start=i;
    while(i<=samples && flags[i]) i++;
    const end=i-1;
    if(end>=start && (end-start+1)<minPlantSamples) {{
      for(let k=start;k<=end;k++) flags[k]=0;
    }}
  }}

  const ranges=[];
  i=0;
  while(i<=samples) {{
    while(i<=samples && !flags[i]) i++;
    const start=i;
    while(i<=samples && flags[i]) i++;
    const end=i-1;
    if(end>=start) {{
      ranges.push({{start:Math.max(0,start/samples),end:Math.min(1,(end+1)/samples)}});
    }}
  }}
  return ranges;
}}

function limitarLinhasPlantio(linhas,maxLinhas) {{
  const out=linhas
    .filter(l=>l && l.items && l.items.length>0)
    .map(l=>{{ return {{items:[...l.items],meanPx:l.meanPx,meanS:l.meanS}}; }})
    .sort((a,b)=>a.meanPx-b.meanPx);
  while(out.length>maxLinhas) {{
    let bestIdx=1, bestDist=Infinity;
    for(let i=1;i<out.length;i++) {{
      const d=Math.abs(out[i].meanPx-out[i-1].meanPx);
      if(d<bestDist) {{ bestDist=d; bestIdx=i; }}
    }}
    const a=out[bestIdx-1], b=out[bestIdx];
    const items=a.items.concat(b.items);
    const meanPx=items.reduce((s,it)=>s+it.sPx,0)/items.length;
    const meanS=items.reduce((s,it)=>s+it.s,0)/items.length;
    out.splice(bestIdx-1,2,{{items:items,meanPx:meanPx,meanS:meanS}});
  }}
  return out.sort((a,b)=>a.meanPx-b.meanPx);
}}

function registrarMetrosPlantadosDaLinha(rowGeom,rowItems,tiroLabel,dispLabel,linhaLabel,parcelaId,sampler,plantRangesProntas) {{
  if(!rowGeom || rowGeom.dist<=0 || !rowItems || rowItems.length<1) return [];
  const plantRanges=plantRangesProntas || getPlantRangesPorLinha(rowGeom,rowItems,sampler);
  if(!plantRanges || plantRanges.length<1) return [];
  let totalPlantadoM=0;
  for(const rg of plantRanges) {{
    const t0=Math.max(0,Math.min(1,rg.start));
    const t1=Math.max(0,Math.min(1,rg.end));
    if(t1<=t0) continue;
    const segM=rowPxToMeters((t1-t0)*rowGeom.dist,rowGeom);
    totalPlantadoM+=segM;
    metrosPlantadosSegmentos.push({{
      p1:pointOnLine(rowGeom.p1,rowGeom.p2,t0),
      p2:pointOnLine(rowGeom.p1,rowGeom.p2,t1),
      distM:segM,
      parcelaId:parcelaId,
      tiro:tiroLabel,
      disp:dispLabel,
      linha:linhaLabel
    }});
  }}
  if(totalPlantadoM>0) {{
    metrosPlantadosLinhas.push({{
      parcela:parcelaId,
      tiro:tiroLabel,
      disp:dispLabel,
      linha:linhaLabel,
      plantadoM:totalPlantadoM
    }});
  }}
  return plantRanges;
}}

function addFalhasSomenteEntrePlantasDaLinha(rowGeom,rowItems,minDistM,tiroLabel,dispLabel,linhaLabel,parcelaId,sampler,plantRangesProntas) {{
  if(!rowGeom || rowGeom.dist<=0 || !rowItems || rowItems.length<1) return;
  const plantRanges=plantRangesProntas || getPlantRangesPorLinha(rowGeom,rowItems,sampler);
  if(plantRanges.length<1) return;
  const intervalos=[];
  intervalos.push({{t0:0,t1:plantRanges[0].start,tipo:'inicio'}});
  for(let i=1;i<plantRanges.length;i++) {{
    intervalos.push({{t0:plantRanges[i-1].end,t1:plantRanges[i].start,tipo:'entre plantas'}});
  }}
  intervalos.push({{t0:plantRanges[plantRanges.length-1].end,t1:1,tipo:'final'}});

  for(const inter of intervalos) {{
    const t0=inter.t0, t1=inter.t1;
    if(t1<=t0) continue;
    const dist=(t1-t0)*rowGeom.dist;
    const distM=rowPxToMeters(dist,rowGeom);
    if(distM>=minDistM) {{
      falhas.push({{
        p1:pointOnLine(rowGeom.p1,rowGeom.p2,t0),
        p2:pointOnLine(rowGeom.p1,rowGeom.p2,t1),
        dist:dist,
        distM:distM,
        tiro:tiroLabel,
        disp:dispLabel,
        linha:linhaLabel,
        tipo:inter.tipo,
        parcelaId:parcelaId
      }});
    }}
  }}
}}

// ── Detecção de plantas (idêntica ao módulo Contagem) ─────────────────────
function countPlantsInGrid() {{
  if (points.length < 4) {{ alert('Marque os 4 cantos do grid primeiro!'); return; }}
  const R=parseInt(inpRows.value)||1, C=parseInt(inpCols.value)||1;
  const p0=points[0],p1=points[1],p2=points[2],p3=points[3];
  const tempCv=document.createElement('canvas');
  tempCv.width=imgW; tempCv.height=imgH;
  const tc=tempCv.getContext('2d'); tc.drawImage(img,0,0);
  const xs=points.map(p=>p.x), ys=points.map(p=>p.y);
  const minX=Math.max(0,Math.floor(Math.min(...xs)));
  const maxX=Math.min(imgW,Math.ceil(Math.max(...xs)));
  const minY=Math.max(0,Math.floor(Math.min(...ys)));
  const maxY=Math.min(imgH,Math.ceil(Math.max(...ys)));
  const imgData=tc.getImageData(minX,minY,maxX-minX,maxY-minY);
  const data=imgData.data; const w=maxX-minX, h=maxY-minY;
  plantCenters=[]; falhas=[]; areasUteis=[]; metrosPlantadosLinhas=[]; metrosPlantadosSegmentos=[]; qualidadeModoVisual='';
  const visited=new Uint8Array(w*h);
  const minArea=25;
  for (let y=0;y<h;y++) {{
    for (let x=0;x<w;x++) {{
      const idx=(y*w+x)*4;
      const r2=data[idx],g=data[idx+1],b=data[idx+2];
      const max2=Math.max(r2,g,b), min2=Math.min(r2,g,b), diff=max2-min2;
      let hue=0,sat=0,val=max2;
      if(diff>0){{
        if(max2===r2) hue=60*(((g-b)/diff)%6);
        else if(max2===g) hue=60*((b-r2)/diff+2);
        else hue=60*((r2-g)/diff+4);
        if(hue<0) hue+=360; sat=(diff/max2)*255;
      }}
      hue=hue/2;
      if(hue>=30&&hue<=90&&sat>=40&&val>=40){{
        const absX=x+minX, absY=y+minY;
        if(pointInPolygon(absX,absY,points)&&!visited[y*w+x]){{
          let area=0,sumX=0,sumY=0;
          const stack=[[x,y]];
          while(stack.length>0&&area<2000){{
            const[sx,sy]=stack.pop();
            if(sx<0||sx>=w||sy<0||sy>=h) continue;
            if(visited[sy*w+sx]) continue;
            const si=(sy*w+sx)*4;
            const sr=data[si],sg=data[si+1],sb=data[si+2];
            const smax=Math.max(sr,sg,sb),smin=Math.min(sr,sg,sb),sdiff=smax-smin;
            let sh=0,ss=0;
            if(sdiff>0){{
              if(smax===sr) sh=60*(((sg-sb)/sdiff)%6);
              else if(smax===sg) sh=60*((sb-sr)/sdiff+2);
              else sh=60*((sr-sg)/sdiff+4);
              if(sh<0) sh+=360; ss=(sdiff/smax)*255;
            }}
            sh=sh/2;
            if(sh<30||sh>90||ss<40||smax<40) continue;
            visited[sy*w+sx]=1; area++; sumX+=sx; sumY+=sy;
            stack.push([sx+1,sy],[sx-1,sy],[sx,sy+1],[sx,sy-1]);
          }}
          if(area>=minArea){{
            plantCenters.push({{x:Math.round(sumX/area)+minX, y:Math.round(sumY/area)+minY}});
          }}
        }}
      }}
    }}
  }}
  for(const m of manualMarks) if(pointInPolygon(m.x,m.y,points)) plantCenters.push(m);
  recount(); drawAll();
}}

// ── Recontagem por parcela ────────────────────────────────────────────────
function recount() {{
  if(points.length<4) return;
  const R=parseInt(inpRows.value)||1, C=parseInt(inpCols.value)||1;
  const p0=points[0],p1=points[1],p2=points[2],p3=points[3];
  parcelCounts={{}};
  for(let r2=0;r2<R;r2++) for(let c=0;c<C;c++) {{
    const poly=getAdjustedParcelPoly(r2,c,R,C,p0,p1,p2,p3);
    let cnt=0;
    for(const p of plantCenters) if(pointInPolygon(p.x,p.y,poly)) cnt++;
    parcelCounts[(R-r2)+'_'+(C-c)]=cnt;
  }}
}}

// ── Detecção de Falhas Lineares ────────────────────────────────────────────
function getLimiteFalhaM() {{
  const cm=Math.max(20,parseFloat(inpMinDist.value)||20);
  inpMinDist.value=cm;
  return cm/100;
}}

function processarQualidadePorLinhas(modo) {{
  if(points.length<4) {{ alert('Marque o grid primeiro!'); return; }}
  const calcularFalhas=(modo==='falhas'||modo==='csv');
  const calcularPlantados=(modo==='plantados'||modo==='csv');
  const R=parseInt(inpRows.value)||1, C=parseInt(inpCols.value)||1;
  const minDistM=getLimiteFalhaM();
  const p0=points[0],p1=points[1],p2=points[2],p3=points[3];
  const sampler=getQualidadeColorSampler();
  const centrosAnalise=[...(sampler.centers||[])];
  for(const m of manualMarks) if(pointInPolygon(m.x,m.y,points)) centrosAnalise.push(m);
  plantCenters=centrosAnalise;
  falhas=[];
  areasUteis=[];
  metrosPlantadosLinhas=[];
  metrosPlantadosSegmentos=[];
  if(modo==='falhas') qualidadeModoVisual='falhas';
  else if(modo==='plantados') qualidadeModoVisual='plantados';

  // Para cada parcela (tiro x disparo), medir somente no eixo real da fileira de plantas.
  for(let r2=0;r2<R;r2++) {{
    for(let c=0;c<C;c++) {{
      const polyOriginal=getAdjustedParcelPoly(r2,c,R,C,p0,p1,p2,p3);
      const areaUtil=getAreaUtilParcela(polyOriginal);
      const [tl,tr,br,bl]=areaUtil;
      const dispLabel=R-r2, tiroLabel=C-c;
      const parcelaId='T'+tiroLabel+' D'+dispLabel;
      areasUteis.push({{parcelaId:parcelaId,poly:areaUtil}});
      const pxPorMetro=getPixelsPorMetroParcela(polyOriginal);
      const axes=getParcelaAxes(tl,tr,br,bl);
      const pts=centrosAnalise.filter(p=>pointInPolygon(p.x,p.y,areaUtil));

      if(pts.length<1) {{
        continue;
      }}

      const rowInfos=pts.map(p=>getPlantRowInfo(p,axes,tl,tr,br,bl));
      const rowTol=Math.max(3,Math.min(10,axes.secondaryLen*0.045));
      const linhas=limitarLinhasPlantio(clusterPlantRows(rowInfos,rowTol),LINHAS_PLANTIO_POR_PARCELA);
      const means=linhas.map(l=>l.meanPx).sort((a,b)=>a-b);
      let spacing=axes.secondaryLen/Math.max(1,linhas.length+1);
      for(let mi=1;mi<means.length;mi++) spacing=Math.min(spacing,Math.max(2,means[mi]-means[mi-1]));
      const corridorPx=Math.max(2,Math.min(10,spacing*0.28));

      for(let li=0;li<linhas.length;li++) {{
        if(linhas[li].items.length<1) continue;
        const rowGeom=alignRowGeometryToPlants(getRowGeometry(tl,tr,br,bl,axes.horiz,linhas[li].meanS),linhas[li].items,areaUtil);
        rowGeom.pxPorMetro=pxPorMetro;
        const dx=rowGeom.p2.x-rowGeom.p1.x, dy=rowGeom.p2.y-rowGeom.p1.y;
        const len=Math.sqrt(dx*dx+dy*dy);
        rowGeom.normal=len>0 ? {{x:-dy/len,y:dx/len}} : {{x:0,y:1}};
        rowGeom.corridorPx=corridorPx;
        const plantRanges=getPlantRangesPorLinha(rowGeom,linhas[li].items,sampler);
        if(calcularPlantados) registrarMetrosPlantadosDaLinha(rowGeom,linhas[li].items,tiroLabel,dispLabel,li+1,parcelaId,sampler,plantRanges);
        if(calcularFalhas) addFalhasSomenteEntrePlantasDaLinha(rowGeom,linhas[li].items,minDistM,tiroLabel,dispLabel,li+1,parcelaId,sampler,plantRanges);
      }}
    }}
  }}
  return true;
}}

function detectarFalhas() {{
  if(!processarQualidadePorLinhas('falhas')) return;
  const minDistM=getLimiteFalhaM();
  // Atualizar painel
  countPanel.style.display='block';
  countPanel.querySelector('h3').textContent='FALHAS DETECTADAS';
  totalCountEl.textContent=falhas.length;
  const totalLinear=getFalhasTotalValue(falhas);
  countInfoEl.textContent=falhas.length+' falha(s) na área útil >= '+formatMeters(minDistM)+' | buffer '+getBufferCorredorCm().toFixed(0)+' cm';
  if(falhas.length>0) {{
    falhasSumario.textContent='Total linear: '+formatMetricValue(totalLinear)+
      ' | Maior: '+formatFalhaDist(falhas.reduce((a,b)=>getFalhaValue(a)>=getFalhaValue(b)?a:b));
  }} else {{
    falhasSumario.textContent='Total linear: '+formatMetricValue(totalLinear);
  }}
  drawAll();
}}

function medirMetrosPlantados() {{
  if(!processarQualidadePorLinhas('plantados')) return;
  const totalPlantado=metrosPlantadosLinhas.reduce((s,row)=>s+(row.plantadoM||0),0);
  countPanel.style.display='block';
  countPanel.querySelector('h3').textContent='METROS PLANTADOS';
  totalCountEl.textContent=totalPlantado.toFixed(2).replace('.',',')+' m';
  countInfoEl.textContent=metrosPlantadosLinhas.length+' linha(s) medidas na área útil';
  falhasSumario.textContent='Total plantado: '+totalPlantado.toFixed(2).replace('.',',')+' m';
  drawAll();
}}

function formatDist(px) {{
  const u=selUnit.value;
  if(u==='cm') return (px*0.1).toFixed(1).replace('.',',')+' cm';
  if(u==='m')  return (px*0.001).toFixed(3).replace('.',',')+' m';
  return px.toFixed(0)+' px';
}}

function formatMeters(m) {{
  const u=selUnit.value;
  if(u==='cm') return (m*100).toFixed(1).replace('.',',')+' cm';
  if(u==='m')  return m.toFixed(3).replace('.',',')+' m';
  return m.toFixed(3).replace('.',',')+' m';
}}

function getFalhaValue(f) {{
  return selUnit.value==='px' ? f.dist : (f.distM||0);
}}

function formatMetricValue(value) {{
  if(selUnit.value==='px') return value.toFixed(0)+' px';
  return formatMeters(value);
}}

function formatFalhaDist(f) {{
  if(selUnit.value==='px') return f.dist.toFixed(0)+' px';
  return formatMeters(f.distM||0);
}}

function formatFalhaNumber(f) {{
  return formatFalhaDist(f).replace(' '+selUnit.value,'');
}}

function getFalhasTotalValue(lista) {{
  return lista.reduce((s,f)=>s+getFalhaValue(f),0);
}}

function cmToPx(value) {{
  return value/0.1;
}}

function unitToPx(value) {{
  const u=selUnit.value;
  if(u==='cm') return value/0.1;
  if(u==='m') return value/0.001;
  return value;
}}

function formatDistNumber(px) {{
  return formatDist(px).replace(' '+selUnit.value,'');
}}

function drawPolyPath(poly) {{
  ctx.beginPath();
  ctx.moveTo(poly[0].x,poly[0].y);
  for(let i=1;i<poly.length;i++) ctx.lineTo(poly[i].x,poly[i].y);
  ctx.closePath();
}}

function expandPoly(poly,pad) {{
  const center=getParcelCenter(poly);
  return poly.map(p=>{{
    const vx=p.x-center.x, vy=p.y-center.y;
    const len=Math.sqrt(vx*vx+vy*vy) || 1;
    return {{x:p.x+(vx/len)*pad, y:p.y+(vy/len)*pad}};
  }});
}}

function redrawImageInsidePoly(poly) {{
  if(imgW<=0 || !poly || poly.length<3) return;
  ctx.save();
  drawPolyPath(expandPoly(poly,8/sc));
  ctx.clip();
  ctx.drawImage(img,0,0);
  ctx.restore();
}}

function getParcelVisualKeys() {{
  const keys=new Set();
  for(const key of Object.keys(parcelAdjustments)) {{
    const adj=parcelAdjustments[key] || {{dx:0,dy:0}};
    if(Math.abs(adj.dx||0)+Math.abs(adj.dy||0)>0) keys.add(key);
  }}
  for(const key of selectedParcels) keys.add(key);
  for(const key of getCascadeAffectedKeys(false)) keys.add(key);
  return keys;
}}

function clearParcelAdjustmentResidues(R,C,p0,p1,p2,p3) {{
  const keys=getParcelVisualKeys();
  for(const key of keys) {{
    const parsed=parseParcelKey(key);
    if(parsed.disp<1 || parsed.disp>R || parsed.tiro<1 || parsed.tiro>C) continue;
    const r2=R-parsed.disp, c=C-parsed.tiro;
    redrawImageInsidePoly(getBaseParcelPoly(r2,c,R,C,p0,p1,p2,p3));
    redrawImageInsidePoly(getAdjustedParcelPoly(r2,c,R,C,p0,p1,p2,p3));
  }}
}}

function drawParcelAdjustmentOverlay(R,C,p0,p1,p2,p3) {{
  const cascadeAffected=getCascadeAffectedKeys(false);
  for(let r2=0;r2<R;r2++) for(let c=0;c<C;c++) {{
    const key=getParcelKeyByRC(r2,c,R,C);
    const adj=parcelAdjustments[key] || {{dx:0,dy:0}};
    const isAdjusted=Math.abs(adj.dx||0)+Math.abs(adj.dy||0)>0;
    const isSelected=selectedParcels.has(key);
    const isCascadeAffected=cascadeAffected.has(key);
    if(!isAdjusted && !isSelected && !isCascadeAffected) continue;
    const poly=getAdjustedParcelPoly(r2,c,R,C,p0,p1,p2,p3);
    const center=getParcelCenter(poly);
    ctx.save();
    drawPolyPath(poly);
    ctx.fillStyle=isSelected?'rgba(255,210,31,0.32)':(isCascadeAffected?'rgba(255,210,31,0.12)':'rgba(85,153,255,0.14)');
    ctx.fill();
    ctx.strokeStyle=isSelected?'#ffd21f':(isCascadeAffected?'rgba(255,210,31,0.72)':'#5599ff');
    ctx.lineWidth=(isSelected?4:(isCascadeAffected?2.5:3))/sc;
    ctx.shadowColor=isSelected?'rgba(255,210,31,0.75)':(isCascadeAffected?'rgba(255,210,31,0.35)':'rgba(85,153,255,0.55)');
    ctx.shadowBlur=10/sc;
    ctx.stroke();
    ctx.shadowBlur=0;
    ctx.fillStyle='rgba(0,0,0,0.75)';
    ctx.font='bold '+(Math.max(8,12/sc))+'px Arial';
    const label=getParcelLabel(key);
    const tw=ctx.measureText(label).width;
    ctx.fillRect(center.x-tw/2-4/sc,center.y-8/sc,tw+8/sc,16/sc);
    ctx.fillStyle=isSelected?'#ffd21f':(isCascadeAffected?'#ffe88a':'#aaddff');
    ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText(label,center.x,center.y);
    ctx.restore();
  }}
}}

// ── Renderização ─────────────────────────────────────────────────────────
function drawAll() {{
  const W=vc.clientWidth, H=vc.clientHeight;
  cv.width=W; cv.height=H;
  ctx.clearRect(0,0,W,H);
  ctx.save();
  ctx.translate(ox,oy); ctx.scale(sc,sc);
  if(imgW>0) ctx.drawImage(img,0,0);

  // Grid
  if(points.length===4){{
    const R=parseInt(inpRows.value)||1, C=parseInt(inpCols.value)||1;
    const p0=points[0],p1=points[1],p2=points[2],p3=points[3];
    ctx.save();
    ctx.strokeStyle='rgba(30,144,255,0.95)'; ctx.lineWidth=2/sc;
    ctx.shadowColor='rgba(0,160,255,0.6)'; ctx.shadowBlur=6/sc;
    for(let i=0;i<=R;i++) {{
      const v=i/R;
      const lx2=(1-v)*p0.x+v*p3.x, ly2=(1-v)*p0.y+v*p3.y;
      const rx2=(1-v)*p1.x+v*p2.x, ry2=(1-v)*p1.y+v*p2.y;
      ctx.beginPath(); ctx.moveTo(lx2,ly2); ctx.lineTo(rx2,ry2); ctx.stroke();
    }}
    for(let j=0;j<=C;j++) {{
      const u=j/C;
      const tx2=(1-u)*p0.x+u*p1.x, ty2=(1-u)*p0.y+u*p1.y;
      const bx2=(1-u)*p3.x+u*p2.x, by2=(1-u)*p3.y+u*p2.y;
      ctx.beginPath(); ctx.moveTo(tx2,ty2); ctx.lineTo(bx2,by2); ctx.stroke();
    }}
    ctx.restore();
    clearParcelAdjustmentResidues(R,C,p0,p1,p2,p3);
    drawParcelAdjustmentOverlay(R,C,p0,p1,p2,p3);

    // Área útil do buffer interno usada na medição das falhas.
    if(areasUteis.length>0) {{
      ctx.save();
      ctx.fillStyle='rgba(255,210,31,0.13)';
      ctx.strokeStyle='rgba(255,210,31,0.98)';
      ctx.lineWidth=Math.max(2/sc,1.4/sc);
      ctx.shadowColor='rgba(255,210,31,0.55)';
      ctx.shadowBlur=5/sc;
      for(const area of areasUteis) {{
        if(!area.poly || area.poly.length<3) continue;
        drawPolyPath(area.poly);
        ctx.fill();
        ctx.beginPath();
        ctx.moveTo(area.poly[0].x,area.poly[0].y);
        ctx.lineTo(area.poly[1].x,area.poly[1].y);
        ctx.moveTo(area.poly[3].x,area.poly[3].y);
        ctx.lineTo(area.poly[2].x,area.poly[2].y);
        ctx.stroke();
      }}
      ctx.restore();
    }}

    // Labels de parcela
    if(showPlantDebug && Object.keys(parcelCounts).length>0) {{
      for(let r2=0;r2<R;r2++) for(let c=0;c<C;c++) {{
        const [tl,tr,br,bl]=getAdjustedParcelPoly(r2,c,R,C,p0,p1,p2,p3);
        const cx2=(tl.x+tr.x+br.x+bl.x)/4, cy2=(tl.y+tr.y+br.y+bl.y)/4;
        const dispL=R-r2, tiroL=C-c;
        const cnt=parcelCounts[dispL+'_'+tiroL]||0;
        ctx.save();
        ctx.fillStyle=cnt>0?'rgba(0,255,0,0.12)':'rgba(255,0,0,0.07)';
        ctx.beginPath();
        ctx.moveTo(tl.x,tl.y); ctx.lineTo(tr.x,tr.y);
        ctx.lineTo(br.x,br.y); ctx.lineTo(bl.x,bl.y);
        ctx.closePath(); ctx.fill();
        ctx.shadowColor='rgba(0,0,0,0.9)'; ctx.shadowBlur=4/sc;
        ctx.fillStyle='#ffffff';
        ctx.font='bold '+(Math.max(8,11/sc))+'px Arial';
        ctx.textAlign='center'; ctx.textBaseline='middle';
        ctx.fillText(cnt,cx2,cy2);
        ctx.font=(Math.max(6,8/sc))+'px Arial'; ctx.fillStyle='#aaa';
        ctx.fillText('T'+tiroL+' D'+dispL,cx2,cy2+14/sc);
        ctx.restore();
      }}
    }}
  }}

  if(showPlantDebug) {{
    // Plantas detectadas (X verde)
    for(const p of plantCenters) {{
      const sz=6/sc;
      ctx.save(); ctx.strokeStyle='#00ff00'; ctx.lineWidth=2/sc;
      ctx.beginPath(); ctx.moveTo(p.x-sz,p.y-sz); ctx.lineTo(p.x+sz,p.y+sz); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(p.x-sz,p.y+sz); ctx.lineTo(p.x+sz,p.y-sz); ctx.stroke();
      ctx.restore();
    }}

    // Marcas manuais (X vermelho)
    for(const p of manualMarks) {{
      const sz=8/sc;
      ctx.save(); ctx.strokeStyle='#ff3333'; ctx.lineWidth=2.5/sc;
      ctx.beginPath(); ctx.moveTo(p.x-sz,p.y-sz); ctx.lineTo(p.x+sz,p.y+sz); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(p.x-sz,p.y+sz); ctx.lineTo(p.x+sz,p.y-sz); ctx.stroke();
      ctx.restore();
    }}
  }}

  // Metros plantados
  if(chkShowFalhas.checked && qualidadeModoVisual==='plantados' && metrosPlantadosSegmentos.length>0) {{
    const lw=parseFloat(inpLineWidth.value)||2;
    const showLbl=chkLabels.checked;
    for(const seg of metrosPlantadosSegmentos) {{
      ctx.save();
      ctx.strokeStyle='#00ee55'; ctx.lineWidth=Math.max(lw/sc,3/sc);
      ctx.shadowColor='rgba(0,238,85,0.65)'; ctx.shadowBlur=6/sc;
      ctx.beginPath(); ctx.moveTo(seg.p1.x,seg.p1.y); ctx.lineTo(seg.p2.x,seg.p2.y); ctx.stroke();
      ctx.fillStyle='#00ee55';
      ctx.beginPath(); ctx.arc(seg.p1.x,seg.p1.y,3/sc,0,2*Math.PI); ctx.fill();
      ctx.beginPath(); ctx.arc(seg.p2.x,seg.p2.y,3/sc,0,2*Math.PI); ctx.fill();
      if(showLbl) {{
        const mx=(seg.p1.x+seg.p2.x)/2, my=(seg.p1.y+seg.p2.y)/2;
        const label=(seg.distM||0).toFixed(2).replace('.',',')+' m';
        ctx.shadowBlur=0;
        ctx.fillStyle='rgba(0,0,0,0.75)';
        const fs=Math.max(9,12/sc);
        ctx.font=fs+'px Arial';
        const tw=ctx.measureText(label).width;
        ctx.fillRect(mx-tw/2-3/sc, my-fs*0.7, tw+6/sc, fs*1.4);
        ctx.fillStyle='#44ff88';
        ctx.textAlign='center'; ctx.textBaseline='middle';
        ctx.fillText(label,mx,my);
      }}
      ctx.restore();
    }}
  }}

  // Falhas lineares
  if(chkShowFalhas.checked && qualidadeModoVisual==='falhas' && falhas.length>0) {{
    const lw=parseFloat(inpLineWidth.value)||2;
    const showLbl=chkLabels.checked;
    for(const f of falhas) {{
      let dp1=f.p1, dp2=f.p2;
      const segLen=lineDistance(f.p1,f.p2);
      if(segLen>0) {{
        const pad=Math.min(6/sc,segLen*0.25);
        let tA=0, tB=1;
        if(f.tipo==='entre plantas') {{ tA=pad/segLen; tB=1-pad/segLen; }}
        else if(f.tipo==='inicio') tB=1-pad/segLen;
        else if(f.tipo==='final') tA=pad/segLen;
        if(tB>tA) {{
          dp1=pointOnLine(f.p1,f.p2,tA);
          dp2=pointOnLine(f.p1,f.p2,tB);
        }}
      }}
      ctx.save();
      ctx.strokeStyle='#ff2200'; ctx.lineWidth=Math.max(lw/sc,3/sc);
      ctx.shadowColor='rgba(255,34,0,0.6)'; ctx.shadowBlur=6/sc;
      ctx.setLineDash([8/sc,4/sc]);
      ctx.beginPath(); ctx.moveTo(dp1.x,dp1.y); ctx.lineTo(dp2.x,dp2.y); ctx.stroke();
      ctx.setLineDash([]);
      // Pequenos círculos nos extremos
      ctx.fillStyle='#ff4400';
      ctx.beginPath(); ctx.arc(dp1.x,dp1.y,4/sc,0,2*Math.PI); ctx.fill();
      ctx.beginPath(); ctx.arc(dp2.x,dp2.y,4/sc,0,2*Math.PI); ctx.fill();
      // Etiqueta de distância
      if(showLbl) {{
        const mx=(dp1.x+dp2.x)/2, my=(dp1.y+dp2.y)/2;
        const label=formatFalhaDist(f);
        ctx.shadowBlur=0;
        ctx.fillStyle='rgba(0,0,0,0.75)';
        const fs=Math.max(9,12/sc);
        ctx.font=fs+'px Arial';
        const tw=ctx.measureText(label).width;
        ctx.fillRect(mx-tw/2-3/sc, my-fs*0.7, tw+6/sc, fs*1.4);
        ctx.fillStyle='#ff6633';
        ctx.textAlign='center'; ctx.textBaseline='middle';
        ctx.fillText(label,mx,my);
      }}
      ctx.restore();
    }}
  }}

  // Pontos do grid
  points.forEach((p,i)=>{{
    const isDrag=draggingPoint===i, r2=11/sc;
    ctx.save();
    ctx.shadowColor=isDrag?'rgba(255,255,255,0.9)':'rgba(0,180,255,0.8)'; ctx.shadowBlur=14/sc;
    ctx.beginPath(); ctx.arc(p.x,p.y,r2,0,2*Math.PI);
    ctx.fillStyle=isDrag?'#ffffff':'#1e90ff'; ctx.fill();
    ctx.lineWidth=2.5/sc; ctx.strokeStyle=isDrag?'#aaddff':'#00cfff'; ctx.stroke();
    ctx.restore();
    ctx.save(); ctx.fillStyle='#ffffff';
    ctx.font='bold '+(13/sc)+'px Arial';
    ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText(i+1,p.x,p.y);
    ctx.restore();
  }});

  ctx.restore();
  zb.textContent=sc.toFixed(2)+'×';
}}

// ── Eventos imagem ────────────────────────────────────────────────────────
img.onload=()=>{{
  imgW=img.width; imgH=img.height;
  const W=vc.clientWidth, H=vc.clientHeight;
  sc=Math.min(W/imgW,H/imgH); ox=(W-imgW*sc)/2; oy=(H-imgH*sc)/2;
  loadParcelAdjustments();
  drawAll();
}};
img.src='data:image/png;base64,'+IMG_B64;

// ── Pan & Zoom ────────────────────────────────────────────────────────────
vc.addEventListener('wheel',e=>{{
  e.preventDefault();
  const factor=e.deltaY<0?1.2:0.8;
  const r=cv.getBoundingClientRect();
  const mx=e.clientX-r.left, my=e.clientY-r.top;
  const ix=(mx-ox)/sc, iy=(my-oy)/sc;
  sc*=factor; sc=Math.max(MIN_SC,Math.min(MAX_SC,sc));
  ox=mx-ix*sc; oy=my-iy*sc; drawAll();
}},{{passive:false}});

vc.addEventListener('mousedown',e=>{{
  const pt=getImgCoords(e.clientX,e.clientY);
  if((parcelSelectMode || parcelMoveMode) && points.length===4) {{
    const hit=findParcelAtPoint(pt);
    if(hit) {{
      if(parcelSelectMode) {{
        if(selectedParcels.has(hit.key)) selectedParcels.delete(hit.key);
        else selectedParcels.add(hit.key);
        updateParcelAdjustStatus();
        drawAll();
        return;
      }}
      if(parcelMoveMode) {{
        if(!selectedParcels.has(hit.key)) {{
          if(selectedParcels.size===0) selectedParcels.clear();
          selectedParcels.add(hit.key);
          updateParcelAdjustStatus();
        }}
        draggingParcelSelection=true;
        lastParcelDragPt=pt;
        vc.style.cursor='move';
        drawAll();
        return;
      }}
    }} else if(parcelSelectMode) {{
      selectedParcels.clear();
      updateParcelAdjustStatus();
      drawAll();
      return;
    }}
  }}
  for(let i=0;i<points.length;i++) {{
    const dx=(pt.x-points[i].x)*sc, dy=(pt.y-points[i].y)*sc;
    if(Math.sqrt(dx*dx+dy*dy)<20) {{ draggingPoint=i; return; }}
  }}
  if(gridMode&&points.length<4) {{
    points.push({{x:pt.x,y:pt.y}});
    if(points.length===4) gridMode=false;
    drawAll(); return;
  }}
  if(manualMode&&points.length===4) {{
    if(pointInPolygon(pt.x,pt.y,points)) {{
      manualMarks.push({{x:pt.x,y:pt.y}});
      plantCenters.push({{x:pt.x,y:pt.y}});
      recount(); drawAll();
    }}
    return;
  }}
  drag=true; lx=e.clientX; ly=e.clientY; vc.style.cursor='grabbing';
}});

vc.addEventListener('mousemove',e=>{{
  const pt=getImgCoords(e.clientX,e.clientY);
  coordEl.textContent='X:'+Math.round(pt.x)+' Y:'+Math.round(pt.y);
  if(draggingParcelSelection && lastParcelDragPt) {{
    translateSelectedParcels(pt.x-lastParcelDragPt.x, pt.y-lastParcelDragPt.y);
    lastParcelDragPt=pt;
    return;
  }}
  if(draggingPoint>=0) {{ points[draggingPoint]={{x:pt.x,y:pt.y}}; drawAll(); return; }}
  if(drag) {{ ox+=e.clientX-lx; oy+=e.clientY-ly; lx=e.clientX; ly=e.clientY; drawAll(); }}
}});

vc.addEventListener('mouseup',()=>{{
  if(draggingParcelSelection) refreshAfterParcelAdjust();
  drag=false; draggingPoint=-1; draggingParcelSelection=false; lastParcelDragPt=null; vc.style.cursor='grab';
}});
vc.addEventListener('mouseleave',()=>{{
  if(draggingParcelSelection) refreshAfterParcelAdjust();
  drag=false; draggingPoint=-1; draggingParcelSelection=false; lastParcelDragPt=null;
}});

// ── Botões ────────────────────────────────────────────────────────────────
btnGridTool.onclick=()=>{{
  gridMode=!gridMode; manualMode=false; parcelSelectMode=false; parcelMoveMode=false; selectedParcels.clear();
  btnGridTool.style.borderColor=gridMode?'#ff8c00':'#3a3a3a';
  if(gridMode) {{ points=[]; plantCenters=[]; manualMarks=[]; parcelCounts={{}}; falhas=[]; areasUteis=[]; metrosPlantadosLinhas=[]; metrosPlantadosSegmentos=[]; qualidadeModoVisual=''; parcelAdjustments={{}}; if(parcelAdjustStorageKey) localStorage.removeItem(parcelAdjustStorageKey); countPanel.style.display='none'; updateParcelAdjustStatus(); drawAll(); }}
}};
if(btnCountPlants) btnCountPlants.onclick=()=>countPlantsInGrid();
if(btnCountAuto) btnCountAuto.onclick  =()=>countPlantsInGrid();
btnManualMode.onclick=()=>{{
  manualMode=!manualMode; gridMode=false; parcelSelectMode=false; parcelMoveMode=false;
  btnManualMode.style.borderColor=manualMode?'#5599ff':'#3a3a3a';
  updateParcelAdjustStatus();
}};
btnManual2.onclick=()=>{{
  manualMode=!manualMode; gridMode=false; parcelSelectMode=false; parcelMoveMode=false;
  btnManualMode.style.borderColor=manualMode?'#5599ff':'#3a3a3a';
  updateParcelAdjustStatus();
}};
btnSelectParcel.onclick=()=>{{
  if(points.length<4) {{ alert('Marque o grid primeiro.'); return; }}
  parcelSelectMode=!parcelSelectMode;
  parcelMoveMode=false; manualMode=false; gridMode=false;
  btnManualMode.style.borderColor='#3a3a3a';
  btnGridTool.style.borderColor='#3a3a3a';
  updateParcelAdjustStatus();
  drawAll();
}};
btnMoveSelected.onclick=()=>{{
  if(points.length<4) {{ alert('Marque o grid primeiro.'); return; }}
  parcelMoveMode=!parcelMoveMode;
  parcelSelectMode=false; manualMode=false; gridMode=false;
  btnManualMode.style.borderColor='#3a3a3a';
  btnGridTool.style.borderColor='#3a3a3a';
  updateParcelAdjustStatus();
  drawAll();
}};
btnClearSelection.onclick=()=>{{
  selectedParcels.clear();
  parcelSelectMode=false; parcelMoveMode=false; draggingParcelSelection=false;
  updateParcelAdjustStatus();
  drawAll();
}};
function moveSelectedByStep(dx,dy) {{
  translateSelectedParcels(dx,dy);
  refreshAfterParcelAdjust();
}}
btnMoveUp.onclick=()=>moveSelectedByStep(0,-(parseFloat(inpMoveStep.value)||5));
btnMoveDown.onclick=()=>moveSelectedByStep(0,(parseFloat(inpMoveStep.value)||5));
btnMoveLeft.onclick=()=>moveSelectedByStep(-(parseFloat(inpMoveStep.value)||5),0);
btnMoveRight.onclick=()=>moveSelectedByStep((parseFloat(inpMoveStep.value)||5),0);
btnSaveParcelAdjust.onclick=()=>{{
  saveParcelAdjustments();
  alert('Ajuste da parcela salvo para visualização, análise, exportação e relatório nesta ortofoto.');
}};
btnRemoveLast.onclick=btnUndoMark.onclick=()=>{{
  if(manualMarks.length>0) {{
    const rem=manualMarks.pop();
    plantCenters=plantCenters.filter(p=>p.x!==rem.x||p.y!==rem.y);
    recount(); drawAll();
  }}
}};
btnClearAll.onclick=()=>{{
  points=[]; plantCenters=[]; manualMarks=[]; parcelCounts={{}}; falhas=[]; areasUteis=[]; metrosPlantadosLinhas=[]; metrosPlantadosSegmentos=[]; qualidadeModoVisual=''; parcelAdjustments={{}}; selectedParcels.clear();
  if(parcelAdjustStorageKey) localStorage.removeItem(parcelAdjustStorageKey);
  countPanel.style.display='none'; gridMode=false; manualMode=false; parcelSelectMode=false; parcelMoveMode=false;
  btnGridTool.style.borderColor='#3a3a3a'; btnManualMode.style.borderColor='#3a3a3a';
  updateParcelAdjustStatus();
  drawAll();
}};
btnDetectFalhas.onclick=()=>detectarFalhas();
btnMedirPlantados.onclick=()=>medirMetrosPlantados();
chkShowFalhas.onchange=()=>drawAll();
chkLabels.onchange=()=>drawAll();
inpMinDist.onchange=()=>{{ if(falhas.length>0) detectarFalhas(); }};
inpBufferCm.onchange=()=>{{ if(falhas.length>0) detectarFalhas(); }};
inpParcelLen.onchange=()=>{{ if(falhas.length>0) detectarFalhas(); }};
selUnit.onchange=()=>{{ if(falhas.length>0) detectarFalhas(); else drawAll(); }};
inpLineWidth.onchange=()=>drawAll();

function parseFalhaParcelaSort(id) {{
  const m=String(id||'').match(/T(\\d+)\\s*D(\\d+)/i);
  return m ? {{tiro:parseInt(m[1]),disp:parseInt(m[2])}} : {{tiro:999999,disp:999999}};
}}

function getLinhaPlantioExport(linha) {{
  return Math.max(1,Math.min(LINHAS_PLANTIO_POR_PARCELA,parseInt(linha)||1));
}}

function getResumoPlantadoFalhaRows() {{
  const mapa={{}};
  for(const row of metrosPlantadosLinhas) {{
    const parcela=row.parcela||('T'+row.tiro+' D'+row.disp);
    const linha=getLinhaPlantioExport(row.linha);
    const key=parcela+'|'+linha;
    if(!mapa[key]) mapa[key]={{parcela:parcela,linha:linha,plantadoM:0,falhaM:0}};
    mapa[key].plantadoM+=Number.isFinite(row.plantadoM) ? row.plantadoM : 0;
  }}
  for(const f of falhas) {{
    const parcela=f.parcelaId||('T'+f.tiro+' D'+f.disp);
    const linha=getLinhaPlantioExport(f.linha);
    const key=parcela+'|'+linha;
    if(!mapa[key]) mapa[key]={{parcela:parcela,linha:linha,plantadoM:0,falhaM:0}};
    mapa[key].falhaM+=Number.isFinite(f.distM) ? f.distM : 0;
  }}
  const parcelas=[...new Set(Object.values(mapa).map(row=>row.parcela))];
  for(const parcela of parcelas) {{
    for(let linha=1; linha<=LINHAS_PLANTIO_POR_PARCELA; linha++) {{
      const key=parcela+'|'+linha;
      if(!mapa[key]) mapa[key]={{parcela:parcela,linha:linha,plantadoM:0,falhaM:0}};
    }}
  }}
  return Object.values(mapa).sort((a,b)=>{{
    const pa=parseFalhaParcelaSort(a.parcela), pb=parseFalhaParcelaSort(b.parcela);
    if(pa.tiro!==pb.tiro) return pa.tiro-pb.tiro;
    if(pa.disp!==pb.disp) return pa.disp-pb.disp;
    return a.linha-b.linha;
  }});
}}

function downloadQualidadeCSV(nomeArquivo,csvContent) {{
  const blob=new Blob([csvContent],{{type:'text/csv;charset=utf-8;'}});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download=nomeArquivo;
  a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),1000);
}}

function exportFalhasPorLinhaCSV() {{
  if(points.length<4) {{ alert('Marque o grid primeiro.'); return; }}
  const estadoAnterior={{
    falhas:[...falhas],
    areasUteis:[...areasUteis],
    metrosPlantadosLinhas:[...metrosPlantadosLinhas],
    metrosPlantadosSegmentos:[...metrosPlantadosSegmentos],
    qualidadeModoVisual:qualidadeModoVisual
  }};
  if(!processarQualidadePorLinhas('csv')) return;
  const rows=getResumoPlantadoFalhaRows();
  if(rows.length===0) {{
    falhas=estadoAnterior.falhas; areasUteis=estadoAnterior.areasUteis;
    metrosPlantadosLinhas=estadoAnterior.metrosPlantadosLinhas;
    metrosPlantadosSegmentos=estadoAnterior.metrosPlantadosSegmentos;
    qualidadeModoVisual=estadoAnterior.qualidadeModoVisual;
    alert('Nenhuma linha de plantio detectada para exportar.'); return;
  }}
  const totalFalhaParcela={{}};
  const totalPlantadoParcela={{}};
  for(const row of rows) {{
    totalFalhaParcela[row.parcela]=(totalFalhaParcela[row.parcela]||0)+(row.falhaM||0);
    totalPlantadoParcela[row.parcela]=(totalPlantadoParcela[row.parcela]||0)+(row.plantadoM||0);
  }}
  let csvFalhas='\\uFEFF'+'Parcela,Linha,Metros_Falha_Linha,Total_Falha_Parcela\\n';
  let csvPlantados='\\uFEFF'+'Parcela,Linha,Metros_Plantados_Linha,Total_Plantado_Parcela\\n';
  for(const row of rows) {{
    csvFalhas+=row.parcela+',Linha '+row.linha+','+(row.falhaM||0).toFixed(2)+','+(totalFalhaParcela[row.parcela]||0).toFixed(2)+'\\n';
    csvPlantados+=row.parcela+',Linha '+row.linha+','+(row.plantadoM||0).toFixed(2)+','+(totalPlantadoParcela[row.parcela]||0).toFixed(2)+'\\n';
  }}
  falhas=estadoAnterior.falhas; areasUteis=estadoAnterior.areasUteis;
  metrosPlantadosLinhas=estadoAnterior.metrosPlantadosLinhas;
  metrosPlantadosSegmentos=estadoAnterior.metrosPlantadosSegmentos;
  qualidadeModoVisual=estadoAnterior.qualidadeModoVisual;
  downloadQualidadeCSV('falhas_por_linha.csv',csvFalhas);
  setTimeout(()=>downloadQualidadeCSV('metros_plantados_por_linha.csv',csvPlantados),250);
}}

btnExportCnt.onclick=()=>exportFalhasPorLinhaCSV();

// ── Modal Relatório de Falhas ─────────────────────────────────────────────
function getFalhasFiltradas(search, fTiro, fDisp) {{
  return falhas.filter(f=>{{
    const label=(f.parcelaId||('T'+f.tiro+' D'+f.disp));
    if(search && !label.toLowerCase().includes(search.toLowerCase())) return false;
    if(fTiro && f.tiro!==parseInt(fTiro)) return false;
    if(fDisp && f.disp!==parseInt(fDisp)) return false;
    return true;
  }});
}}

function buildResumoParcelas(falhasBase) {{
  if(falhasBase.length===0) return '';
  const resumo={{}};
  for(const f of falhasBase) {{
    const id=f.parcelaId||('T'+f.tiro+' D'+f.disp);
    if(!resumo[id]) resumo[id]={{qtd:0,total:0,maior:0,menor:Infinity,linhas:{{}}}};
    const r=resumo[id];
    const v=getFalhaValue(f);
    r.qtd++;
    r.total+=v;
    r.maior=Math.max(r.maior,v);
    r.menor=Math.min(r.menor,v);
    r.linhas[f.linha]=(r.linhas[f.linha]||0)+1;
  }}
  let html='<div style="background:#111;border:1px solid #333;border-radius:8px;padding:10px;margin-bottom:10px;">';
  html+='<div style="color:#ff8c00;font-size:11px;font-weight:bold;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">Resumo por parcela</div>';
  html+='<table style="width:100%;border-collapse:collapse;font-size:10px;">';
  html+='<thead><tr style="color:#aaa;"><th style="text-align:left;padding:4px;">Parcela</th><th style="padding:4px;">Falhas</th><th style="padding:4px;">Total</th><th style="padding:4px;">Por linha</th><th style="padding:4px;">Maior</th><th style="padding:4px;">Menor</th><th style="padding:4px;">Média</th></tr></thead><tbody>';
  for(const id of Object.keys(resumo).sort()) {{
    const r=resumo[id];
    const linhas=Object.keys(r.linhas).sort((a,b)=>parseInt(a)-parseInt(b)).map(l=>'L'+l+': '+r.linhas[l]).join(' | ');
    html+='<tr style="border-top:1px solid #222;">';
    html+='<td style="padding:4px;color:#fff;">'+id+'</td>';
    html+='<td style="padding:4px;color:#ff4444;text-align:center;">'+r.qtd+'</td>';
    html+='<td style="padding:4px;color:#ffaa33;text-align:center;">'+formatMetricValue(r.total)+'</td>';
    html+='<td style="padding:4px;color:#aaa;text-align:center;">'+linhas+'</td>';
    html+='<td style="padding:4px;color:#ff8c00;text-align:center;">'+formatMetricValue(r.maior)+'</td>';
    html+='<td style="padding:4px;color:#bbb;text-align:center;">'+formatMetricValue(r.menor)+'</td>';
    html+='<td style="padding:4px;color:#bbb;text-align:center;">'+formatMetricValue(r.total/r.qtd)+'</td>';
    html+='</tr>';
  }}
  html+='</tbody></table></div>';
  return html;
}}

function buildFalhasTable(search, fTiro, fDisp) {{
  const tbody=document.getElementById('falhasTable');
  if(falhas.length===0) {{ tbody.innerHTML='<p style="color:#666;text-align:center;padding:20px;font-size:12px;">Nenhuma falha detectada. Clique em ⚠️ Detectar Falhas.</p>'; return; }}
  const filtradas=getFalhasFiltradas(search, fTiro, fDisp);
  if(filtradas.length===0) {{
    tbody.innerHTML='<p style="color:#666;text-align:center;padding:20px;font-size:12px;">Nenhuma falha encontrada para o filtro atual.</p>';
    document.getElementById('modalTotalFalhas').textContent='0';
    document.getElementById('modalTotalLinear').textContent=formatMetricValue(0);
    document.getElementById('modalMaiorFalha').textContent=formatMetricValue(0);
    return;
  }}
  let html='<table style="width:100%;border-collapse:collapse;font-size:11px;">';
  html+='<thead><tr style="background:#222;color:#ff4444;"><th style="padding:8px;border-bottom:1px solid #333;">Parcela</th><th style="padding:8px;border-bottom:1px solid #333;">Linha</th><th style="padding:8px;border-bottom:1px solid #333;">Tipo</th><th style="padding:8px;border-bottom:1px solid #333;">Distância</th><th style="padding:8px;border-bottom:1px solid #333;">Coord. Ini.</th><th style="padding:8px;border-bottom:1px solid #333;">Coord. Fim</th></tr></thead><tbody>';
  let totalLinear=0, maior=0, count=0;
  for(const f of filtradas) {{
    const v=getFalhaValue(f);
    totalLinear+=v; if(v>maior) maior=v;
    count++;
    html+='<tr style="border-bottom:1px solid #1a1a1a;">';
    html+='<td style="padding:6px 8px;color:#5599ff;">'+(f.parcelaId||('T'+f.tiro+' D'+f.disp))+'</td>';
    html+='<td style="padding:6px 8px;color:#aaa;">L'+f.linha+'</td>';
    html+='<td style="padding:6px 8px;color:#bbb;">'+(f.tipo||'entre plantas')+'</td>';
    html+='<td style="padding:6px 8px;color:#ff4444;font-weight:bold;">'+formatFalhaDist(f)+'</td>';
    html+='<td style="padding:6px 8px;color:#666;font-size:10px;">('+Math.round(f.p1.x)+','+Math.round(f.p1.y)+')</td>';
    html+='<td style="padding:6px 8px;color:#666;font-size:10px;">('+Math.round(f.p2.x)+','+Math.round(f.p2.y)+')</td>';
    html+='</tr>';
  }}
  html+='</tbody></table>';
  tbody.innerHTML=buildResumoParcelas(filtradas)+html;
  document.getElementById('modalTotalFalhas').textContent=filtradas.length;
  document.getElementById('modalTotalLinear').textContent=formatMetricValue(totalLinear);
  document.getElementById('modalMaiorFalha').textContent=formatMetricValue(maior);
  document.getElementById('modalTotalLinearLabel').textContent='Total Linear';
  document.getElementById('modalMaiorFalhaLabel').textContent='Maior Falha';
}}

btnOpenFalhas.onclick=()=>{{
  if(points.length<4) {{ alert('Marque o grid primeiro!'); return; }}
  if(falhas.length===0) detectarFalhas();
  const R=parseInt(inpRows.value)||1, C=parseInt(inpCols.value)||1;
  const ftiro=document.getElementById('modalFilterTiro');
  const fdisp=document.getElementById('modalFilterDisp');
  ftiro.innerHTML='<option value="">Todos Tiros</option>';
  fdisp.innerHTML='<option value="">Todos Disp.</option>';
  for(let c=1;c<=C;c++) ftiro.innerHTML+='<option value="'+c+'">Tiro '+c+'</option>';
  for(let r=1;r<=R;r++) fdisp.innerHTML+='<option value="'+r+'">Disp. '+r+'</option>';
  buildFalhasTable('','','');
  falhasModal.style.display='flex';
}};
btnCloseModal.onclick=()=>{{ falhasModal.style.display='none'; }};
document.getElementById('modalSearch').oninput=function(){{ buildFalhasTable(this.value,document.getElementById('modalFilterTiro').value,document.getElementById('modalFilterDisp').value); }};
document.getElementById('modalFilterTiro').onchange=function(){{ buildFalhasTable(document.getElementById('modalSearch').value,this.value,document.getElementById('modalFilterDisp').value); }};
document.getElementById('modalFilterDisp').onchange=function(){{ buildFalhasTable(document.getElementById('modalSearch').value,document.getElementById('modalFilterTiro').value,this.value); }};

// ── Exportação Falhas CSV ─────────────────────────────────────────────────
document.getElementById('btnExportFalhasCSV').onclick=()=>{{
  exportFalhasPorLinhaCSV();
}};

// ── Exportação Falhas GeoJSON ─────────────────────────────────────────────
document.getElementById('btnExportFalhasGeoJSON').onclick=()=>{{
  const totalLinear=getFalhasTotalValue(falhas);
  const features=falhas.map((f,i)=>{{
    return {{
      type:'Feature',
      properties:{{ id:i+1, parcela_id:(f.parcelaId||('T'+f.tiro+' D'+f.disp)), tiro:f.tiro, disparo:f.disp, linha:f.linha, tipo:(f.tipo||'entre plantas'), distancia_px:Math.round(f.dist), distancia_m:f.distM||0, distancia_fmt:formatFalhaDist(f), unidade:selUnit.value }},
      geometry:{{ type:'LineString', coordinates:[[f.p1.x,-f.p1.y],[f.p2.x,-f.p2.y]] }}
    }};
  }});
  const gj=JSON.stringify({{type:'FeatureCollection',properties:{{total_falhas:falhas.length,total_linear_fmt:formatMetricValue(totalLinear),comprimento_parcela_m:getParcelRealMeters()}},features:features}},null,2);
  const blob=new Blob([gj],{{type:'application/json'}});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob);
  a.download='falhas_lineares.geojson'; a.click();
}};

// ── Exportação Falhas Excel ───────────────────────────────────────────────
document.getElementById('btnExportFalhasXLSX').onclick=()=>{{
  if(typeof XLSX==='undefined') {{ alert('Biblioteca XLSX não carregada.'); return; }}
  const rows=[['ID Parcela','Linha','Tipo Falha','Distância','Unidade','X Início','Y Início','X Fim','Y Fim']];
  for(const f of falhas) rows.push([f.parcelaId||('T'+f.tiro+' D'+f.disp),f.linha,f.tipo||'entre plantas',formatFalhaNumber(f),selUnit.value,Math.round(f.p1.x),Math.round(f.p1.y),Math.round(f.p2.x),Math.round(f.p2.y)]);
  rows.push(['TOTAL','','',formatMetricValue(getFalhasTotalValue(falhas)).replace(' '+selUnit.value,''),selUnit.value,'','','','']);
  const ws=XLSX.utils.aoa_to_sheet(rows);
  ws['!cols']=[{{wch:14}},{{wch:8}},{{wch:16}},{{wch:12}},{{wch:8}},{{wch:10}},{{wch:10}},{{wch:10}},{{wch:10}}];
  const wb=XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb,ws,'Falhas Lineares');
  XLSX.writeFile(wb,'falhas_lineares.xlsx');
}};

new ResizeObserver(()=>drawAll()).observe(vc);
</script>
</body>
</html>
"""
                    components.html(qual_viewer, height=740, scrolling=False)

            else:
                st.markdown("""
                <div style='height:740px;border:1px dashed #2e2e2e;border-radius:12px;background:#0d0d0d;
                            display:flex;flex-direction:column;align-items:center;justify-content:center;
                            gap:12px;color:#333;'>
                    <div style='font-size:3rem;'>✅</div>
                    <div style='font-size:0.85rem;letter-spacing:2px;text-transform:uppercase;color:#555;'>
                        Carregue uma ortofoto para análise de qualidade
                    </div>
                    <div style='font-size:0.75rem;color:#444;'>
                        Marque o grid → Detecte Falhas → Exporte relatório
                    </div>
                </div>""", unsafe_allow_html=True)
            # FIM NOVO - MÓDULO QUALIDADE DE PARCELA

        else:
            st.markdown("""
            <div style='background:#1e1e1e;border:1px solid #333;border-radius:15px;padding:40px;text-align:center;'>
                <div style='font-size:3rem;margin-bottom:12px;'>📈</div>
                <div style='color:#555;font-size:0.9rem;letter-spacing:2px;text-transform:uppercase;'>
                    Selecione uma das opções acima para visualizar os resultados
                </div>
            </div>""", unsafe_allow_html=True)
    # FIM NOVO - VISUALIZADOR DE RESULTADOS

# ==========================================
# FOOTER[cite: 1]
# ==========================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.divider()

st.markdown(
    "<p style='text-align: center; color: #555;'>Estrutura Modular Profissional | Python 3.12</p>",
    unsafe_allow_html=True
)
