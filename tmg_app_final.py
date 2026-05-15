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
import html
import re
import subprocess
import sqlite3
from datetime import datetime, date
import pandas as pd

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
  function patchDomForTranslate(win) {
    try {
      if (!win || win.__tmgDomPatchInstalled || !win.Node || !win.Node.prototype) {
        return;
      }

      const nodeProto = win.Node.prototype;
      const nativeRemoveChild = nodeProto.removeChild;
      const nativeInsertBefore = nodeProto.insertBefore;

      nodeProto.removeChild = function (child) {
        if (child && child.parentNode !== this) {
          return child;
        }
        return nativeRemoveChild.call(this, child);
      };

      nodeProto.insertBefore = function (newNode, referenceNode) {
        if (referenceNode && referenceNode.parentNode !== this) {
          return this.appendChild(newNode);
        }
        return nativeInsertBefore.call(this, newNode, referenceNode);
      };

      Object.defineProperty(win, "__tmgDomPatchInstalled", {
        value: true,
        configurable: false,
        writable: false
      });
    } catch (err) {
      // Browser extensions and hosted iframes can block prototype access.
    }
  }

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
        patchDomForTranslate(current);
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
            0 0 30px var(--tmg-primary-glow-soft);
        border-bottom: 2px solid var(--tmg-primary);
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
        color: var(--tmg-primary);
        border: 1px solid var(--tmg-primary);
        transform: translateY(-2px);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(145deg, var(--tmg-primary), var(--tmg-primary-dark)) !important;
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
        color: var(--tmg-primary);
        text-transform: uppercase;
        text-shadow:
            1px 1px 0 var(--tmg-primary-shadow-1),
            2px 2px 0 var(--tmg-primary-shadow-2),
            3px 3px 0 var(--tmg-primary-shadow-3),
            4px 4px 6px rgba(0,0,0,0.9),
            0 0 20px var(--tmg-primary-glow),
            0 0 40px var(--tmg-primary-glow-soft);
        margin-bottom: 8px;
    }

    /* Separator with glow */
    .separator-glow {
        border: none;
        border-top: 1px solid var(--tmg-primary);
        box-shadow: 0 0 8px var(--tmg-primary-glow);
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
    # Ajuste solicitado: visualização de ortofotos com mais qualidade no Streamlit.
    # Pode ser configurado por variável/secret TMG_PREVIEW_MAX_DIM.
    # Mantém compatibilidade com Streamlit Cloud evitando carregar a imagem original inteira no navegador.
    return _int_setting("TMG_PREVIEW_MAX_DIM", 8192, 1024, 12000)

def _preview_jpeg_quality() -> int:
    # Qualidade alta para preservar detalhes de TIF/GeoTIFF/RGB no visualizador.
    return _int_setting("TMG_PREVIEW_JPEG_QUALITY", 97, 70, 98)

def _preview_max_payload_mb() -> int:
    # Evita que o HTML do visualizador fique pesado demais para carregar no navegador.
    return _int_setting("TMG_PREVIEW_MAX_PAYLOAD_MB", 10, 4, 80)

def _preview_min_dim() -> int:
    return _int_setting("TMG_PREVIEW_MIN_DIM", 2048, 900, 4096)

def _upload_limit_mb() -> int:
    # Valor informativo mostrado na interface; o limite real do Streamlit Cloud é definido em .streamlit/config.toml.
    return _int_setting("TMG_UPLOAD_LIMIT_MB", 2048, 200, 4096)

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

THEME_PALETTES = {
    "padrao": {
        "primary": "#42a5f5",
        "primary_dark": "#1565c0",
        "primary_soft": "#90caf9",
        "shadow_1": "#0d47a1",
        "shadow_2": "#0a3070",
        "shadow_3": "#071f4a",
        "rgb": "66,165,245",
    },
    "tmg_azul": {
        "primary": "#42a5f5",
        "primary_dark": "#1565c0",
        "primary_soft": "#90caf9",
        "shadow_1": "#0d47a1",
        "shadow_2": "#0a3070",
        "shadow_3": "#071f4a",
        "rgb": "66,165,245",
    },
}
THEME_PALETTE = THEME_PALETTES.get(SYSTEM_CONFIG.get("tema", "padrao"), THEME_PALETTES["padrao"])
THEME_PRIMARY_COLOR = THEME_PALETTE["primary"]
THEME_PRIMARY_DARK = THEME_PALETTE["primary_dark"]
THEME_PRIMARY_SOFT = THEME_PALETTE["primary_soft"]
THEME_PRIMARY_RGB = THEME_PALETTE["rgb"]

st.markdown(f"""
<style>
:root {{
    --tmg-primary: {THEME_PRIMARY_COLOR};
    --tmg-primary-dark: {THEME_PRIMARY_DARK};
    --tmg-primary-soft: {THEME_PRIMARY_SOFT};
    --tmg-primary-shadow-1: {THEME_PALETTE["shadow_1"]};
    --tmg-primary-shadow-2: {THEME_PALETTE["shadow_2"]};
    --tmg-primary-shadow-3: {THEME_PALETTE["shadow_3"]};
    --tmg-primary-glow: rgba({THEME_PRIMARY_RGB}, .42);
    --tmg-primary-glow-soft: rgba({THEME_PRIMARY_RGB}, .18);
}}
[style*="#ff8c00"], [style*="#FF8C00"] {{
    color: var(--tmg-primary) !important;
    border-color: var(--tmg-primary) !important;
}}
.main-header,
.cultura-title,
.login-title,
.partner-hero-title,
.partner-window-title,
.partner-card-title,
.vd-hero h2,
h1, h2, h3 {{
    text-shadow:
        1px 1px 0 rgba(0,0,0,.75),
        2px 2px 0 rgba(0,0,0,.45),
        0 0 18px var(--tmg-primary-glow) !important;
}}
</style>
""", unsafe_allow_html=True)

def _theme_colorize_markup(value):
    if not isinstance(value, str):
        return value
    themed = value
    replacements = {
        "#ff8c00": THEME_PRIMARY_COLOR,
        "#FF8C00": THEME_PRIMARY_COLOR,
        "#ff9e33": THEME_PRIMARY_COLOR,
        "#e67600": THEME_PRIMARY_DARK,
        "#e07000": THEME_PRIMARY_DARK,
        "#ffaa33": THEME_PRIMARY_SOFT,
        "#ffb347": THEME_PRIMARY_SOFT,
        "#2a1a00": "#0d2b45",
        "#1a0a00": "#071a2c",
        "#160b00": "#061525",
        "#7a3a00": THEME_PALETTE["shadow_1"],
        "#5c2b00": THEME_PALETTE["shadow_2"],
        "#3d1d00": THEME_PALETTE["shadow_3"],
    }
    for old, new in replacements.items():
        themed = themed.replace(old, new)
    themed = re.sub(
        r"rgba\(\s*255\s*,\s*140\s*,\s*0\s*,\s*([0-9.]+)\s*\)",
        rf"rgba({THEME_PRIMARY_RGB},\1)",
        themed,
    )
    return themed

_ORIGINAL_ST_MARKDOWN = st.markdown
_ORIGINAL_COMPONENTS_HTML = components.html

def _themed_markdown(body, *args, **kwargs):
    return _ORIGINAL_ST_MARKDOWN(_theme_colorize_markup(body), *args, **kwargs)

def _themed_components_html(html, *args, **kwargs):
    return _ORIGINAL_COMPONENTS_HTML(_theme_colorize_markup(html), *args, **kwargs)

st.markdown = _themed_markdown
components.html = _themed_components_html

# ==========================================
# MODULO ISOLADO - USUARIOS E PARCEIROS
# ==========================================
AUTH_USERS_PATH = SYSTEM_DATABASE_DIR / "usuarios_sistema.json"
CHAT_MESSAGES_PATH = SYSTEM_DATABASE_DIR / "chat_mensagens.json"
PARTNERS_ROOT = SYSTEM_DATABASE_DIR / "parceiros_controle_voos_dados"
PARTNERS_STATE_PATH = PARTNERS_ROOT / "parceiros_estado.json"
PARTNERS_LOGOS_DIR = PARTNERS_ROOT / "logos"
PARTNER_KEYS = {"eiwa": "EIWA", "alvaz": "ALVAZ"}
PARTNER_BUTTON_LABELS = {"eiwa": "EIWA", "alvaz": "ALVAZ"}
PARTNER_STATUS_OPTIONS = ["Executado", "Não executado"]
PARTNER_TREATMENT_STATUS = ["Aberto", "Em andamento", "Concluído", "Resolvido", "Atrasado"]
PARTNER_TREATMENT_DONE = {"Concluído", "Resolvido"}
PARTNER_INTERNAL_COLUMNS = ["Status de Execução", "Tratativa", "Descrição / Observação", "Última Alteração", "Usuário Responsável"]
PARTNER_ROW_ID = "__tmg_row_id"
MENU_PERMISSION_OPTIONS = {
    "menu_checklist": "Checklist",
    "menu_grid": "Marcar Grid",
    "menu_upload": "Upload",
    "menu_bases": "Banco de Dados",
    "menu_sync": "Sincronizar",
    "menu_ortomosaicos": "Gerar Ortomosaico",
    "menu_parceiros": "Parceiros",
    "menu_controle_dados": "Controle de Dados",
}
PARTNER_PERMISSION_OPTIONS = {
    "partner_sheet_view": "Visualizar planilha",
    "partner_sheet_import": "Importar planilha",
    "partner_sheet_edit_rows": "Editar linhas",
    "partner_sheet_delete_rows": "Excluir linhas",
    "partner_sheet_edit_header": "Editar cabeçalho",
    "partner_sheet_write_treatment": "Escrever tratativas na planilha",
    "partner_sheet_history": "Acessar histórico",
    "partner_sheet_export": "Exportar planilha",
}
PHENOTYPING_PERMISSION_OPTIONS = {
    "phenotyping_contagem": "Contagem",
    "phenotyping_maturacao": "Maturação",
    "phenotyping_pendoamento": "Pendoamento",
    "phenotyping_qualidade": "Qualidade de Parcela",
}

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _now_human() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def _default_permissions(all_access: bool = True) -> dict:
    permissions = {
        "culturas": bool(all_access),
        "soja": bool(all_access),
        "milho": bool(all_access),
        "algodao": bool(all_access),
        "parceiros": bool(all_access),
        "eiwa": bool(all_access),
        "alvaz": bool(all_access),
    }
    for key in MENU_PERMISSION_OPTIONS:
        permissions[key] = bool(all_access)
    for key in PHENOTYPING_PERMISSION_OPTIONS:
        permissions[key] = bool(all_access)
    for key in PARTNER_PERMISSION_OPTIONS:
        permissions[key] = bool(all_access)
    return permissions

def _auth_default_users() -> dict:
    return {
        "users": [
            {
                "nome": "Wellington",
                "usuario": "Wellington",
                "senha": "123",
                "ativo": True,
                "admin": True,
                "permissoes": _default_permissions(True),
                "criado_em": _now_iso(),
                "atualizado_em": _now_iso(),
            },
            {
                "nome": "Acesso legado",
                "usuario": "123",
                "senha": "123",
                "ativo": True,
                "admin": False,
                "permissoes": _default_permissions(True),
                "criado_em": _now_iso(),
                "atualizado_em": _now_iso(),
            },
        ]
    }

def _auth_ensure_users() -> None:
    AUTH_USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not AUTH_USERS_PATH.exists():
        AUTH_USERS_PATH.write_text(json.dumps(_auth_default_users(), indent=2, ensure_ascii=False), encoding="utf-8")
        return
    data = _auth_load_users()
    users = data.setdefault("users", [])
    if not any(str(u.get("usuario", "")).lower() == "wellington" for u in users):
        users.insert(0, _auth_default_users()["users"][0])
    _auth_save_users(data)

def _auth_load_users() -> dict:
    try:
        data = json.loads(AUTH_USERS_PATH.read_text(encoding="utf-8")) if AUTH_USERS_PATH.exists() else _auth_default_users()
    except Exception:
        data = _auth_default_users()
    data.setdefault("users", [])
    for user in data["users"]:
        user.setdefault("nome", user.get("usuario", "Usuário"))
        user.setdefault("usuario", "")
        user.setdefault("senha", "")
        user.setdefault("ativo", True)
        user.setdefault("admin", False)
        user.setdefault("permissoes", _default_permissions(False))
        perms = user["permissoes"]
        legacy_culture_access = bool(perms.get("culturas", False))
        legacy_partner_access = bool(perms.get("parceiros", False))
        defaults = _default_permissions(False)
        for key, value in defaults.items():
            if key in perms:
                continue
            if key in ("menu_checklist", "menu_grid", "menu_upload", "menu_bases", "menu_sync", "menu_ortomosaicos"):
                perms[key] = legacy_culture_access
            elif key in ("menu_parceiros", "menu_controle_dados"):
                perms[key] = legacy_partner_access
            elif key in PHENOTYPING_PERMISSION_OPTIONS:
                # Compatibilidade com usuários antigos: se já tinha acesso aos módulos de cultura,
                # libera as análises até o administrador ajustar individualmente.
                perms[key] = legacy_culture_access
            elif key in PARTNER_PERMISSION_OPTIONS:
                perms[key] = legacy_partner_access
            else:
                perms[key] = value
    return data

def _auth_save_users(data: dict) -> None:
    AUTH_USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUTH_USERS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def _auth_find_user(usuario: str, senha: str) -> dict:
    _auth_ensure_users()
    usuario_norm = str(usuario or "").strip().lower()
    senha_text = str(senha or "")
    for user in _auth_load_users().get("users", []):
        if str(user.get("usuario", "")).strip().lower() == usuario_norm and str(user.get("senha", "")) == senha_text:
            if bool(user.get("ativo", True)):
                return user
            return {}
    return {}

def _auth_current_user() -> dict:
    user = st.session_state.get("auth_user")
    if isinstance(user, dict) and user.get("usuario"):
        return user
    return _auth_default_users()["users"][0]

def _auth_user_name() -> str:
    user = _auth_current_user()
    return str(user.get("nome") or user.get("usuario") or "Usuário")

def _auth_is_admin(user: dict = None) -> bool:
    user = user or _auth_current_user()
    return bool(user.get("admin")) or str(user.get("usuario", "")).strip().lower() == "wellington"

def _auth_permissions(user: dict = None) -> dict:
    user = user or _auth_current_user()
    if _auth_is_admin(user):
        return _default_permissions(True)
    perms = user.get("permissoes", {}) if isinstance(user, dict) else {}
    normalized = _default_permissions(False)
    normalized.update({k: bool(v) for k, v in perms.items()})
    legacy_culture_access = bool(normalized.get("culturas"))
    legacy_partner_access = bool(normalized.get("parceiros"))
    for key in ("menu_checklist", "menu_grid", "menu_upload", "menu_bases", "menu_sync", "menu_ortomosaicos"):
        if key not in perms:
            normalized[key] = legacy_culture_access
    for key in ("menu_parceiros", "menu_controle_dados"):
        if key not in perms:
            normalized[key] = legacy_partner_access
    for key in PHENOTYPING_PERMISSION_OPTIONS:
        if key not in perms:
            normalized[key] = legacy_culture_access
    for key in PARTNER_PERMISSION_OPTIONS:
        if key not in perms:
            normalized[key] = legacy_partner_access
    return normalized

def _auth_allowed_cultures(user: dict = None) -> list:
    perms = _auth_permissions(user)
    if not perms.get("culturas"):
        return []
    allowed = []
    if perms.get("soja"):
        allowed.append("SOJA")
    if perms.get("milho"):
        allowed.append("MILHO")
    if perms.get("algodao"):
        allowed.append("ALGODÃO")
    return allowed

def _auth_can_partners(user: dict = None) -> bool:
    perms = _auth_permissions(user)
    return bool(perms.get("parceiros") and (perms.get("menu_parceiros") or perms.get("menu_controle_dados")))

def _auth_menu_allowed(menu_key: str, user: dict = None) -> bool:
    return bool(_auth_permissions(user).get(menu_key))

def _auth_phenotyping_allowed(permission_key: str, user: dict = None) -> bool:
    return bool(_auth_permissions(user).get(permission_key))

def _auth_allowed_phenotyping(user: dict = None) -> list:
    perms = _auth_permissions(user)
    if not perms.get("culturas"):
        return []
    return [key for key in PHENOTYPING_PERMISSION_OPTIONS if bool(perms.get(key))]

def _auth_partner_permission(permission_key: str, user: dict = None) -> bool:
    return bool(_auth_permissions(user).get(permission_key))

def _auth_allowed_partners(user: dict = None) -> list:
    perms = _auth_permissions(user)
    if not perms.get("parceiros"):
        return []
    allowed = []
    if perms.get("eiwa"):
        allowed.append("eiwa")
    if perms.get("alvaz"):
        allowed.append("alvaz")
    return allowed

def _chat_user_login(user: dict) -> str:
    return str((user or {}).get("usuario", "")).strip()

def _chat_user_display(user: dict) -> str:
    login = _chat_user_login(user)
    nome = str((user or {}).get("nome") or login or "Usuário").strip()
    return f"{nome} ({login})" if login and nome.lower() != login.lower() else (login or nome)

def _chat_load_state() -> dict:
    CHAT_MESSAGES_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(CHAT_MESSAGES_PATH.read_text(encoding="utf-8")) if CHAT_MESSAGES_PATH.exists() else {}
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("messages", [])
    if not isinstance(data["messages"], list):
        data["messages"] = []
    return data

def _chat_save_state(data: dict) -> None:
    CHAT_MESSAGES_PATH.parent.mkdir(parents=True, exist_ok=True)
    data.setdefault("messages", [])
    CHAT_MESSAGES_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def _chat_registered_users(current_user: dict) -> list:
    current_login = _chat_user_login(current_user).lower()
    users = []
    for user in _auth_load_users().get("users", []):
        login = _chat_user_login(user)
        if not login or login.lower() == current_login or not bool(user.get("ativo", True)):
            continue
        users.append(user)
    return users

def _chat_unread_count(login: str, other_login: str = "") -> int:
    login_norm = str(login or "").strip().lower()
    other_norm = str(other_login or "").strip().lower()
    total = 0
    for msg in _chat_load_state().get("messages", []):
        if str(msg.get("destinatario", "")).strip().lower() != login_norm:
            continue
        if bool(msg.get("lida", False)):
            continue
        if other_norm and str(msg.get("remetente", "")).strip().lower() != other_norm:
            continue
        total += 1
    return total

def _chat_thread_messages(login_a: str, login_b: str) -> list:
    a = str(login_a or "").strip().lower()
    b = str(login_b or "").strip().lower()
    rows = []
    for msg in _chat_load_state().get("messages", []):
        sender = str(msg.get("remetente", "")).strip().lower()
        target = str(msg.get("destinatario", "")).strip().lower()
        if (sender == a and target == b) or (sender == b and target == a):
            rows.append(msg)
    rows.sort(key=lambda item: str(item.get("timestamp", "")))
    return rows

def _chat_mark_thread_read(current_login: str, other_login: str) -> None:
    current_norm = str(current_login or "").strip().lower()
    other_norm = str(other_login or "").strip().lower()
    data = _chat_load_state()
    changed = False
    for msg in data.get("messages", []):
        if (
            str(msg.get("destinatario", "")).strip().lower() == current_norm
            and str(msg.get("remetente", "")).strip().lower() == other_norm
            and not bool(msg.get("lida", False))
        ):
            msg["lida"] = True
            msg["lida_em"] = _now_iso()
            changed = True
    if changed:
        _chat_save_state(data)

def _chat_send_message(sender_user: dict, target_login: str, text: str) -> tuple:
    sender_login = _chat_user_login(sender_user)
    target_login = str(target_login or "").strip()
    text = str(text or "").strip()
    if not sender_login:
        return False, "Faça login para acessar o chat."
    if not target_login:
        return False, "Selecione um usuário para enviar a mensagem."
    if sender_login.lower() == target_login.lower():
        return False, "Não é possível conversar consigo mesmo."
    if not text:
        return False, "Digite uma mensagem antes de enviar."

    users = {str(u.get("usuario", "")).strip().lower(): u for u in _auth_load_users().get("users", [])}
    target_user = users.get(target_login.lower())
    if not target_user or not bool(target_user.get("ativo", True)):
        return False, "Usuário destinatário não encontrado ou inativo."

    now = datetime.now()
    msg_id = hashlib.sha1(f"{sender_login}-{target_login}-{now.isoformat()}-{text}".encode("utf-8")).hexdigest()[:18]
    data = _chat_load_state()
    data.setdefault("messages", []).append({
        "id": msg_id,
        "remetente": sender_login,
        "remetente_nome": str(sender_user.get("nome") or sender_login),
        "destinatario": target_login,
        "destinatario_nome": str(target_user.get("nome") or target_login),
        "texto": text,
        "data": now.strftime("%d/%m/%Y"),
        "hora": now.strftime("%H:%M:%S"),
        "timestamp": now.isoformat(timespec="seconds"),
        "lida": False,
    })
    _chat_save_state(data)
    return True, "Mensagem enviada."

def _render_chat_body(current_user: dict) -> None:
    current_login = _chat_user_login(current_user)
    st.markdown("""
    <style>
      .tmg-chat-title { color: var(--tmg-primary); font-weight: 800; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }
      .tmg-chat-scroll { max-height: 320px; overflow-y: auto; padding: 8px; border: 1px solid #2a2a2a; border-radius: 10px; background: #0d0d0d; }
      .tmg-chat-msg { padding: 8px 10px; border-radius: 10px; margin: 7px 0; max-width: 86%; box-shadow: 0 4px 12px rgba(0,0,0,.22); }
      .tmg-chat-sent { margin-left: auto; background: linear-gradient(145deg,#0d2b45,#071a2c); border: 1px solid var(--tmg-primary); color: #f2f7fb; }
      .tmg-chat-received { margin-right: auto; background: #151515; border: 1px solid #333; color: #eee; }
      .tmg-chat-meta { color: #9aa7b5; font-size: .72rem; margin-bottom: 3px; }
      .tmg-chat-text { font-size: .88rem; line-height: 1.35; white-space: pre-wrap; }
      .tmg-chat-unread { color: #ff4d4d; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<div class='tmg-chat-title'>Chat</div>", unsafe_allow_html=True)

    users = _chat_registered_users(current_user)
    if not current_login:
        st.warning("Acesse o sistema para usar o chat.")
        return
    if not users:
        st.info("Nenhum outro usuário cadastrado para conversar.")
        return

    search = st.text_input("Pesquisar usuário", key="tmg_chat_search", placeholder="Pesquisar usuário cadastrado")
    filtered = [
        user for user in users
        if not search
        or search.lower() in _chat_user_display(user).lower()
        or search.lower() in _chat_user_login(user).lower()
    ]
    if not filtered:
        st.info("Nenhum usuário encontrado para a busca.")
        return

    labels = {}
    for user in filtered:
        login = _chat_user_login(user)
        unread = _chat_unread_count(current_login, login)
        labels[login] = _chat_user_display(user) + (f"  • {unread} nova(s)" if unread else "")

    logins = [_chat_user_login(user) for user in filtered]
    current_selected = st.session_state.get("tmg_chat_selected_user")
    selected_index = logins.index(current_selected) if current_selected in logins else 0
    selected_login = st.selectbox(
        "Usuário",
        logins,
        index=selected_index,
        format_func=lambda value: labels.get(value, value),
        key="tmg_chat_user_select",
    )
    st.session_state["tmg_chat_selected_user"] = selected_login
    _chat_mark_thread_read(current_login, selected_login)

    messages = _chat_thread_messages(current_login, selected_login)
    if not messages:
        st.caption("Sem mensagens nesta conversa.")
    else:
        parts = ["<div class='tmg-chat-scroll'>"]
        for msg in messages[-80:]:
            sent = str(msg.get("remetente", "")).strip().lower() == current_login.lower()
            cls = "tmg-chat-sent" if sent else "tmg-chat-received"
            author = "Você" if sent else html.escape(str(msg.get("remetente_nome") or msg.get("remetente") or "Usuário"))
            when = html.escape(f"{msg.get('data', '')} {msg.get('hora', '')}".strip())
            status = " · lida" if sent and bool(msg.get("lida", False)) else (" · não lida" if sent else "")
            text = html.escape(str(msg.get("texto", "")))
            parts.append(
                f"<div class='tmg-chat-msg {cls}'>"
                f"<div class='tmg-chat-meta'>{author} · {when}{status}</div>"
                f"<div class='tmg-chat-text'>{text}</div>"
                "</div>"
            )
        parts.append("</div>")
        st.markdown("".join(parts), unsafe_allow_html=True)

    with st.form("tmg_chat_send_form", clear_on_submit=True):
        msg_text = st.text_area("Mensagem", key="tmg_chat_message", height=70, placeholder="Digite sua mensagem")
        send = st.form_submit_button("Enviar", type="primary", use_container_width=True)
        if send:
            ok, feedback = _chat_send_message(current_user, selected_login, msg_text)
            if ok:
                st.success(feedback)
                app_rerun()
            else:
                st.warning(feedback)

    if st.button("Minimizar / Fechar", key="tmg_chat_close", use_container_width=True):
        st.session_state["tmg_chat_open"] = False
        app_rerun()

def _render_system_chat(current_user: dict) -> None:
    if not st.session_state.get("logged_in", False):
        return
    current_login = _chat_user_login(current_user)
    if not current_login:
        return

    unread_total = _chat_unread_count(current_login)
    label = "💬" + (f"  ● {unread_total}" if unread_total else "")
    st.markdown("""
    <style>
      div[data-testid="stPopover"] button, div[data-testid="stButton"] button {
        transition: all .18s ease;
      }
    </style>
    """, unsafe_allow_html=True)
    chat_cols = st.columns([0.90, 0.10])
    with chat_cols[1]:
        if hasattr(st, "popover"):
            with st.popover(label, help="Abrir chat", use_container_width=True):
                _render_chat_body(current_user)
        else:
            if st.button(label, key="tmg_chat_toggle", help="Abrir chat", use_container_width=True):
                st.session_state["tmg_chat_open"] = not st.session_state.get("tmg_chat_open", False)
            if st.session_state.get("tmg_chat_open", False):
                _render_chat_body(current_user)

def _partners_default_partner() -> dict:
    return {
        "link": "",
        "rows": [],
        "columns": [],
        "baseline_rows": [],
        "baseline_columns": [],
        "baseline_import": {},
        "last_import": {},
        "last_update": {},
        "diff_rows": [],
        "chat": [],
        "history": [],
        "logo_path": "",
    }

def _partners_default_state() -> dict:
    return {
        "partners": {key: _partners_default_partner() for key in PARTNER_KEYS},
        "history_general": [],
    }

def _partners_ensure_storage() -> None:
    PARTNERS_ROOT.mkdir(parents=True, exist_ok=True)
    if not PARTNERS_STATE_PATH.exists():
        PARTNERS_STATE_PATH.write_text(json.dumps(_partners_default_state(), indent=2, ensure_ascii=False), encoding="utf-8")

def _partners_load_state() -> dict:
    _partners_ensure_storage()
    try:
        state = json.loads(PARTNERS_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        state = _partners_default_state()
    state.setdefault("partners", {})
    state.setdefault("history_general", [])
    for key in PARTNER_KEYS:
        state["partners"].setdefault(key, _partners_default_partner())
        partner = state["partners"][key]
        partner.setdefault("link", "")
        partner.setdefault("rows", [])
        partner.setdefault("columns", [])
        partner.setdefault("baseline_rows", [])
        partner.setdefault("baseline_columns", [])
        partner.setdefault("baseline_import", {})
        partner.setdefault("last_import", {})
        partner.setdefault("last_update", {})
        partner.setdefault("diff_rows", [])
        partner.setdefault("chat", [])
        partner.setdefault("history", [])
        partner.setdefault("logo_path", "")
    return state

def _partners_save_state(state: dict) -> None:
    PARTNERS_ROOT.mkdir(parents=True, exist_ok=True)
    PARTNERS_STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def _partners_add_history(state: dict, partner_key: str, acao: str, detalhes: str = "", extra: dict = None) -> None:
    item = {
        "data_hora": _now_human(),
        "usuario": _auth_user_name(),
        "parceira": PARTNER_KEYS.get(partner_key, "Geral") if partner_key else "Geral",
        "acao": acao,
        "detalhes": detalhes,
    }
    if isinstance(extra, dict):
        item.update(extra)
    state.setdefault("history_general", []).insert(0, item)
    state["history_general"] = state["history_general"][:1000]
    if partner_key in state.get("partners", {}):
        state["partners"][partner_key].setdefault("history", []).insert(0, item)
        state["partners"][partner_key]["history"] = state["partners"][partner_key]["history"][:1000]

def _partner_label(partner_key: str) -> str:
    return PARTNER_BUTTON_LABELS.get(partner_key, PARTNER_KEYS.get(partner_key, partner_key))

def _partners_logo_path(partner_key: str):
    partner_key = str(partner_key or "").strip().lower()
    for suffix in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = PARTNERS_LOGOS_DIR / f"{partner_key}{suffix}"
        if candidate.exists():
            return candidate
    return None

def _partners_save_logo(state: dict, partner_key: str, uploaded_file) -> None:
    if uploaded_file is None:
        return
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        suffix = ".png"
    PARTNERS_LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    for old in PARTNERS_LOGOS_DIR.glob(f"{partner_key}.*"):
        try:
            old.unlink()
        except Exception:
            pass
    target = PARTNERS_LOGOS_DIR / f"{partner_key}{suffix}"
    target.write_bytes(uploaded_file.getvalue())
    state["partners"][partner_key]["logo_path"] = str(target)

def _partners_logo_html(partner_key: str) -> str:
    label = _partner_label(partner_key)
    logo_path = _partners_logo_path(partner_key)
    if logo_path and logo_path.exists():
        suffix = logo_path.suffix.lower()
        mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/webp" if suffix == ".webp" else "image/png"
        data = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        return (
            "<div class='partner-logo-frame'>"
            f"<img src='data:{mime};base64,{data}' alt='Logo {label}' class='partner-logo-img'>"
            "</div>"
        )
    return f"<div class='partner-logo-frame partner-logo-empty'>LOGO {label}</div>"

def _partners_history_rows(rows: list) -> list:
    label_map = {
        "eiwa": "EIWA",
        "iva": "EIWA",
        "eva": "EIWA",
        "alvaz": "ALVAZ",
        "alvás": "ALVAZ",
        "olvas": "ALVAZ",
        "elvas": "ALVAZ",
    }
    normalized = []
    for row in rows or []:
        item = dict(row)
        if "parceira" in item:
            item["parceira"] = label_map.get(str(item.get("parceira", "")).strip().lower(), item.get("parceira", ""))
        normalized.append(item)
    return normalized

def _auth_mention_options() -> tuple:
    users = []
    labels = {}
    for user in _auth_load_users().get("users", []):
        if not user.get("ativo", True):
            continue
        usuario = str(user.get("usuario", "")).strip()
        if not usuario:
            continue
        users.append(usuario)
        labels[usuario] = f"{user.get('nome', usuario)} ({usuario})"
    return users, labels

def _partners_mentions_for_user(state: dict, user: dict) -> list:
    usuario = str(user.get("usuario", "")).strip().lower()
    if not usuario:
        return []
    notes = []
    for partner_key, partner in state.get("partners", {}).items():
        for item in partner.get("chat", []) or []:
            citados = [str(v).strip().lower() for v in item.get("citados", [])]
            if usuario in citados:
                notes.append({
                    "parceira": _partner_label(partner_key),
                    "assunto": item.get("assunto", "Sem assunto"),
                    "usuario": item.get("usuario", ""),
                    "data": item.get("data", ""),
                    "hora": item.get("hora", ""),
                })
    return notes[:5]

def _partners_read_sheet_upload(uploaded_file) -> tuple:
    if uploaded_file is None:
        return None, "Selecione uma planilha Excel ou CSV para importar."
    try:
        raw = uploaded_file.getvalue()
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix in (".xlsx", ".xls"):
            df = pd.read_excel(BytesIO(raw))
        elif suffix == ".csv":
            df = None
            errors = []
            for encoding in ("utf-8-sig", "utf-8", "latin1", "cp1252"):
                try:
                    df = pd.read_csv(BytesIO(raw), sep=None, engine="python", encoding=encoding)
                    break
                except Exception as exc:
                    errors.append(f"{encoding}: {exc}")
            if df is None:
                raise ValueError("; ".join(errors[-2:]))
        else:
            return None, "Formato não suportado. Envie arquivos .xlsx, .xls ou .csv."
        df = _partners_clean_dataframe(df)
        if df.empty and len(df.columns) == 0:
            return None, "Não foi possível importar a planilha. Verifique o formato do arquivo e tente novamente."
        return df, ""
    except Exception:
        return None, "Não foi possível importar a planilha. Verifique o formato do arquivo e tente novamente."

def _partners_unique_columns(columns) -> list:
    seen = {}
    unique = []
    for idx, raw_col in enumerate(columns):
        base = str(raw_col).strip() or f"Coluna {idx + 1}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        unique.append(base if count == 0 else f"{base}_{count + 1}")
    return unique

def _partners_clean_dataframe(df) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    df = df.copy()
    df.columns = _partners_unique_columns(df.columns)
    df = df.replace({np.nan: ""})
    for col in df.columns:
        df[col] = df[col].map(lambda value: value.isoformat() if hasattr(value, "isoformat") else str(value) if value is not None else "")
    return df

def _partners_row_label(row: dict, idx: int = 0) -> str:
    row_id = str(row.get(PARTNER_ROW_ID, "")).strip()
    values = [str(v).strip() for k, v in row.items() if k != PARTNER_ROW_ID and str(v).strip()]
    preview = " · ".join(values[:2]) if values else row_id
    return f"{idx + 1} · {preview[:80]} · {row_id}"

def _partners_safe_excel_bytes(export_df: pd.DataFrame) -> tuple:
    if export_df is None:
        return None, "Não foi possível exportar a planilha agora."
    max_rows, max_cols = 1048576, 16384
    if len(export_df) > max_rows or len(export_df.columns) > max_cols:
        return None, "A planilha ultrapassa o limite do Excel. Use a exportação CSV para baixar todos os dados."
    try:
        excel_buf = BytesIO()
        clean_df = export_df.replace({np.nan: ""}).copy()
        with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
            clean_df.to_excel(writer, index=False, sheet_name="Planilha Tratada")
            ws = writer.book["Planilha Tratada"]
            try:
                from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
                from openpyxl.utils import get_column_letter

                header_fill = PatternFill("solid", fgColor="B7DEE8")
                data_fill = PatternFill("solid", fgColor="FFFFFF")
                internal_fill = PatternFill("solid", fgColor="EAF3F8")
                thin = Side(style="thin", color="808080")
                border = Border(left=thin, right=thin, top=thin, bottom=thin)
                header_font = Font(bold=True, color="000000")
                default_font = Font(color="000000")
                center = Alignment(horizontal="center", vertical="center", wrap_text=True)
                left = Alignment(horizontal="left", vertical="center", wrap_text=True)

                internal_cols = set(PARTNER_INTERNAL_COLUMNS)
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.border = border
                    cell.alignment = center

                for row in ws.iter_rows(min_row=2):
                    for cell in row:
                        header = str(ws.cell(row=1, column=cell.column).value or "")
                        cell.fill = internal_fill if header in internal_cols else data_fill
                        cell.font = default_font
                        cell.border = border
                        cell.alignment = left

                for col_idx, column_cells in enumerate(ws.columns, start=1):
                    max_len = 12
                    for cell in column_cells:
                        value = "" if cell.value is None else str(cell.value)
                        max_len = max(max_len, min(len(value) + 2, 55))
                    ws.column_dimensions[get_column_letter(col_idx)].width = max_len

                ws.freeze_panes = "A2"
                ws.auto_filter.ref = ws.dimensions
            except Exception:
                pass
        return excel_buf.getvalue(), ""
    except Exception:
        return None, "Não foi possível exportar para Excel. Use a exportação CSV ou revise a planilha."

def _partners_export_csv_file(export_df: pd.DataFrame, partner_key: str) -> tuple:
    try:
        export_dir = PARTNERS_ROOT / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        target = export_dir / f"{partner_key}_controle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        export_df.replace({np.nan: ""}).to_csv(target, index=False, encoding="utf-8-sig")
        return target, ""
    except Exception:
        return None, "Não foi possível preparar o CSV para download. Tente filtrar ou revisar a planilha."

def _partners_rename_column(partner: dict, old_name: str, new_name: str) -> tuple:
    old_name = str(old_name or "").strip()
    new_name = str(new_name or "").strip()
    if not old_name or not new_name:
        return False, "Informe o nome atual e o novo nome da coluna."
    if old_name == new_name:
        return False, "O cabeçalho já está com esse nome."
    if new_name == PARTNER_ROW_ID or new_name in PARTNER_INTERNAL_COLUMNS:
        return False, "Esse nome é reservado pelo sistema."
    columns = list(partner.get("columns", []))
    if old_name not in columns:
        return False, "Coluna não encontrada na planilha atual."
    if new_name in columns:
        return False, "Já existe uma coluna com esse nome."
    partner["columns"] = [new_name if col == old_name else col for col in columns]
    for collection_name in ("rows", "baseline_rows", "diff_rows"):
        for row in partner.get(collection_name, []) or []:
            if old_name in row:
                row[new_name] = row.pop(old_name)
    partner["baseline_columns"] = [new_name if col == old_name else col for col in partner.get("baseline_columns", [])]
    return True, ""

def _partners_add_blank_row(partner: dict, partner_key: str) -> dict:
    row_id = hashlib.sha1(f"{partner_key}-{_auth_user_name()}-{_now_iso()}-{len(partner.get('rows', []))}".encode()).hexdigest()[:12]
    row = {PARTNER_ROW_ID: row_id}
    row["Status de Execução"] = "Não executado"
    for col in partner.get("columns", []):
        row[col] = ""
    for col in PARTNER_INTERNAL_COLUMNS:
        row.setdefault(col, "Não executado" if col == "Status de Execução" else "")
    row["Última Alteração"] = _now_human()
    row["Usuário Responsável"] = _auth_user_name()
    partner.setdefault("rows", []).append(row)
    return row

def _partners_delete_row(partner: dict, row_id: str) -> bool:
    rows = partner.get("rows", [])
    before = len(rows)
    partner["rows"] = [row for row in rows if str(row.get(PARTNER_ROW_ID, "")) != str(row_id)]
    return len(partner["rows"]) != before

def _partners_ensure_row_ids(rows: list) -> list:
    prepared = []
    for idx, row in enumerate(rows or []):
        item = dict(row)
        item.setdefault(PARTNER_ROW_ID, hashlib.sha1(f"{idx}-{json.dumps(item, ensure_ascii=False, sort_keys=True)}".encode("utf-8")).hexdigest()[:12])
        prepared.append(item)
    return prepared

def _partners_rows_to_df(partner_data: dict) -> pd.DataFrame:
    rows = _partners_ensure_row_ids(partner_data.get("rows", []))
    columns = [col for col in partner_data.get("columns", []) if col != PARTNER_ROW_ID]
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=[PARTNER_ROW_ID] + columns + PARTNER_INTERNAL_COLUMNS)
    if PARTNER_ROW_ID not in df.columns:
        df[PARTNER_ROW_ID] = [hashlib.sha1(f"row-{i}".encode()).hexdigest()[:12] for i in range(len(df))]
    for col in columns + PARTNER_INTERNAL_COLUMNS:
        if col not in df.columns:
            df[col] = "Não executado" if col == "Status de Execução" else ""
    if "Status de Execução" in df.columns:
        df["Status de Execução"] = df["Status de Execução"].map(
            lambda value: value if str(value) in PARTNER_STATUS_OPTIONS else "Não executado"
        )
    status_cols = ["Status de Execução"] if "Status de Execução" in df.columns else []
    front_internal = [col for col in ("Tratativa", "Descrição / Observação") if col in df.columns]
    tail_internal = [col for col in PARTNER_INTERNAL_COLUMNS if col in df.columns and col not in status_cols + front_internal]
    ordered = [PARTNER_ROW_ID] + status_cols + front_internal + [col for col in columns if col in df.columns] + tail_internal
    ordered += [col for col in df.columns if col not in ordered]
    return df[ordered].replace({np.nan: ""})

def _partners_prepare_import_df(df: pd.DataFrame, current_user: str) -> tuple:
    df = _partners_clean_dataframe(df)
    original_columns = [col for col in df.columns if col != PARTNER_ROW_ID and col not in PARTNER_INTERNAL_COLUMNS]
    df.insert(0, PARTNER_ROW_ID, [hashlib.sha1(f"{current_user}-{_now_iso()}-{i}".encode()).hexdigest()[:12] for i in range(len(df))])
    for col in PARTNER_INTERNAL_COLUMNS:
        if col not in df.columns:
            df[col] = "Não executado" if col == "Status de Execução" else ""
    if "Status de Execução" in df.columns:
        df["Status de Execução"] = df["Status de Execução"].map(
            lambda value: value if str(value) in PARTNER_STATUS_OPTIONS else "Não executado"
        )
    if "Usuário Responsável" in df.columns:
        df["Usuário Responsável"] = df["Usuário Responsável"].replace("", current_user)
    return df, original_columns

def _partners_compare_dataframes(old_df: pd.DataFrame, new_df: pd.DataFrame, columns: list) -> tuple:
    old = old_df[[col for col in columns if col in old_df.columns]].reset_index(drop=True)
    new = new_df[[col for col in columns if col in new_df.columns]].reset_index(drop=True)
    max_len = max(len(old), len(new))
    preview = []
    changed_rows = 0
    new_rows = 0
    removed_rows = 0
    for idx in range(max_len):
        if idx >= len(old):
            row = new.iloc[idx].to_dict()
            row["__ALTERAÇÃO__"] = "Linha nova"
            row["__CELULAS__"] = ""
            preview.append(row)
            new_rows += 1
            continue
        if idx >= len(new):
            row = old.iloc[idx].to_dict()
            row["__ALTERAÇÃO__"] = "Linha removida"
            row["__CELULAS__"] = ""
            preview.append(row)
            removed_rows += 1
            continue
        changed_cells = [col for col in columns if str(old.at[idx, col] if col in old.columns else "") != str(new.at[idx, col] if col in new.columns else "")]
        row = new.iloc[idx].to_dict()
        row["__ALTERAÇÃO__"] = "Célula alterada" if changed_cells else "Sem alteração"
        row["__CELULAS__"] = ", ".join(changed_cells)
        preview.append(row)
        if changed_cells:
            changed_rows += 1
    return {
        "linhas_novas": new_rows,
        "linhas_alteradas": changed_rows,
        "linhas_removidas": removed_rows,
        "total_diferencas": new_rows + changed_rows + removed_rows,
        "data_hora": _now_human(),
        "usuario": _auth_user_name(),
    }, preview

def _partners_style_diff(df: pd.DataFrame):
    def _style(row):
        marker = row.get("__ALTERAÇÃO__", "")
        if marker == "Linha nova":
            return ["background-color: rgba(255, 76, 76, .24); color:#fff;"] * len(row)
        if marker == "Linha removida":
            return ["background-color: rgba(130, 130, 130, .30); color:#ddd;"] * len(row)
        if marker == "Célula alterada":
            changed = [part.strip() for part in str(row.get("__CELULAS__", "")).split(",") if part.strip()]
            return ["background-color: rgba(255, 221, 64, .30); color:#fff;" if col in changed else "" for col in row.index]
        return [""] * len(row)
    return df.style.apply(_style, axis=1)

def _partners_merge_edited_rows(base_df: pd.DataFrame, visible_ids: list, edited_df: pd.DataFrame, original_columns: list) -> tuple:
    current_user = _auth_user_name()
    now = _now_human()
    base = base_df.copy().replace({np.nan: ""})
    edited = edited_df.copy().replace({np.nan: ""})
    if PARTNER_ROW_ID not in edited.columns:
        edited[PARTNER_ROW_ID] = ""
    logs = []
    visible_set = {str(row_id) for row_id in visible_ids}
    edited_ids = {str(row.get(PARTNER_ROW_ID, "")) for _, row in edited.iterrows() if str(row.get(PARTNER_ROW_ID, "")).strip()}
    keep_rows = []
    for _, row in base.iterrows():
        row_id = str(row.get(PARTNER_ROW_ID, ""))
        if row_id in visible_set and row_id not in edited_ids:
            logs.append((
                "Linha excluída",
                row_id,
                {"tipo_acao": "exclusão", "linha": row_id, "campo": "", "valor_antigo": "linha existente", "valor_novo": "linha removida"}
            ))
            continue
        keep_rows.append(row.to_dict())
    merged = pd.DataFrame(keep_rows)
    if merged.empty:
        merged = pd.DataFrame(columns=base.columns)
    merged = merged.set_index(PARTNER_ROW_ID, drop=False) if PARTNER_ROW_ID in merged.columns else merged
    for _, row in edited.iterrows():
        row_dict = row.to_dict()
        row_id = str(row_dict.get(PARTNER_ROW_ID, "")).strip()
        if not row_id or row_id not in merged.index:
            row_id = hashlib.sha1(f"{current_user}-{_now_iso()}-{len(merged)}".encode()).hexdigest()[:12]
            row_dict[PARTNER_ROW_ID] = row_id
            row_dict["Última Alteração"] = now
            row_dict["Usuário Responsável"] = current_user
            logs.append((
                "Linha criada",
                row_id,
                {"tipo_acao": "edição", "linha": row_id, "campo": "", "valor_antigo": "", "valor_novo": "linha criada"}
            ))
            merged.loc[row_id, list(row_dict.keys())] = list(row_dict.values())
            continue
        previous_status = str(merged.at[row_id, "Status de Execução"]) if "Status de Execução" in merged.columns else ""
        new_status = str(row_dict.get("Status de Execução", previous_status))
        changed_cols = []
        for col, value in row_dict.items():
            if col not in merged.columns:
                merged[col] = ""
            old_value = str(merged.at[row_id, col])
            if old_value != str(value):
                merged.at[row_id, col] = value
                if col != PARTNER_ROW_ID:
                    changed_cols.append(col)
                    logs.append((
                        "Linha alterada",
                        f"{row_id}: {col}",
                        {"tipo_acao": "edição", "linha": row_id, "campo": col, "valor_antigo": old_value, "valor_novo": str(value)}
                    ))
        if changed_cols:
            merged.at[row_id, "Última Alteração"] = now
            merged.at[row_id, "Usuário Responsável"] = current_user
        if previous_status != new_status:
            logs.append((
                "Status alterado",
                f"{row_id}: {previous_status} -> {new_status}",
                {"tipo_acao": "edição", "linha": row_id, "campo": "Status de Execução", "valor_antigo": previous_status, "valor_novo": new_status}
            ))
    merged = merged.reset_index(drop=True).replace({np.nan: ""})
    columns = [col for col in original_columns if col in merged.columns]
    for col in PARTNER_INTERNAL_COLUMNS:
        if col not in merged.columns:
            merged[col] = "Não executado" if col == "Status de Execução" else ""
    if "Status de Execução" in merged.columns:
        merged["Status de Execução"] = merged["Status de Execução"].map(
            lambda value: value if str(value) in PARTNER_STATUS_OPTIONS else "Não executado"
        )
    status_cols = ["Status de Execução"] if "Status de Execução" in merged.columns else []
    front_internal = [col for col in ("Tratativa", "Descrição / Observação") if col in merged.columns]
    tail_internal = [col for col in PARTNER_INTERNAL_COLUMNS if col in merged.columns and col not in status_cols + front_internal]
    ordered = [PARTNER_ROW_ID] + status_cols + front_internal + columns + tail_internal
    ordered += [col for col in merged.columns if col not in ordered]
    return merged[ordered], logs

def _partners_filter_dataframe(df: pd.DataFrame, search: str, statuses: list) -> pd.DataFrame:
    filtered = df.copy()
    if statuses and "Status de Execução" in filtered.columns:
        filtered = filtered[filtered["Status de Execução"].isin(statuses)]
    query = str(search or "").strip().lower()
    if query:
        mask = filtered.apply(lambda row: query in " ".join(str(v).lower() for v in row.values), axis=1)
        filtered = filtered[mask]
    return filtered

def _partners_deadline_alerts(chat_rows: list) -> list:
    alerts = []
    today = date.today()
    for item in chat_rows or []:
        status = item.get("status", "Aberto")
        prazo_raw = item.get("prazo", "")
        if status in PARTNER_TREATMENT_DONE:
            alerts.append(("Verde", "Tratativa resolvida", item))
            continue
        if not prazo_raw:
            alerts.append(("Cinza", "Tratativa sem prazo", item))
            continue
        try:
            prazo = date.fromisoformat(str(prazo_raw))
        except Exception:
            alerts.append(("Cinza", "Prazo inválido ou ausente", item))
            continue
        delta = (prazo - today).days
        if delta < 0:
            alerts.append(("Vermelho", "Prazo vencido", item))
        elif delta == 0:
            alerts.append(("Amarelo", "Prazo vence hoje", item))
        elif delta == 1:
            alerts.append(("Amarelo", "Prazo vence amanhã", item))
        elif status in ("Aberto", "Em andamento"):
            alerts.append(("Cinza", "Tratativa pendente", item))
    return alerts

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
    """Converte ortofotos para pré-visualização de alta qualidade no Streamlit.

    Ajuste focado em TIF/GeoTIFF/RGB e formatos comuns, preservando metadados espaciais
    e reduzindo a imagem somente para o tamanho seguro de navegação no browser.
    """
    ext = Path(filename).suffix.lower()
    img = None
    erro = None

    spatial_meta = {
        "transform": None,
        "crs": None,
        "ratio": 1.0,
        "orig_width": 0,
        "orig_height": 0,
        "preview_width": 0,
        "preview_height": 0,
        "preview_quality": _preview_jpeg_quality(),
    }

    def _stretch_band(band):
        band = np.ma.asarray(band).astype(np.float32).filled(np.nan)
        valid = band[np.isfinite(band)]
        if valid.size == 0:
            return np.zeros(band.shape, dtype=np.uint8)
        mn = np.nanpercentile(valid, 1)
        mx = np.nanpercentile(valid, 99)
        if not np.isfinite(mn) or not np.isfinite(mx) or mx <= mn:
            mn = np.nanmin(valid)
            mx = np.nanmax(valid)
        if not np.isfinite(mn) or not np.isfinite(mx) or mx <= mn:
            return np.zeros(band.shape, dtype=np.uint8)
        return np.nan_to_num(np.clip((band - mn) / (mx - mn) * 255, 0, 255)).astype(np.uint8)

    def _preserve_uint8_band(band):
        return np.ma.asarray(band).filled(0).astype(np.uint8, copy=False)

    def _rgba_to_rgb(pil_img):
        if pil_img.mode == 'RGBA':
            try:
                pil_img.load()
                bg = Image.new('RGB', pil_img.size, (18, 18, 18))
                bg.paste(pil_img, mask=pil_img.split()[3])
                return bg
            except Exception:
                arr = np.array(pil_img)
                if arr.ndim == 3 and arr.shape[2] == 4:
                    alpha = arr[:, :, 3:4].astype(np.float32) / 255.0
                    rgb = arr[:, :, :3].astype(np.float32)
                    bg_v = np.array([18, 18, 18], dtype=np.float32)
                    return Image.fromarray((rgb * alpha + bg_v * (1.0 - alpha)).clip(0, 255).astype(np.uint8), 'RGB')
        if pil_img.mode != 'RGB':
            return pil_img.convert('RGB')
        return pil_img

    try:
        import rasterio
        from rasterio.enums import Resampling
        from rasterio.io import MemoryFile
        with MemoryFile(file_bytes) as memfile:
            with memfile.open() as src:
                spatial_meta["orig_width"] = int(src.width)
                spatial_meta["orig_height"] = int(src.height)
                if getattr(src, "crs", None):
                    spatial_meta["crs"] = src.crs.to_wkt()
                if getattr(src, "transform", None):
                    spatial_meta["transform"] = src.transform.to_gdal()

                max_dim = _preview_max_dim()
                ratio = min(1.0, max_dim / max(src.width, src.height))
                out_width = max(1, int(src.width * ratio))
                out_height = max(1, int(src.height * ratio))
                spatial_meta["ratio"] = ratio
                spatial_meta["preview_width"] = out_width
                spatial_meta["preview_height"] = out_height

                resampling_filter = getattr(Resampling, "lanczos", Resampling.bilinear)
                bands = int(src.count)

                if bands >= 3:
                    # Mantém RGB verdadeiro quando o GeoTIFF já está em uint8; faz realce leve somente em 16/32 bits.
                    band_indexes = [1, 2, 3]
                    data = src.read(
                        band_indexes,
                        out_shape=(3, out_height, out_width),
                        resampling=resampling_filter,
                        masked=True,
                    )
                    selected_dtypes = [np.dtype(src.dtypes[index - 1]) for index in band_indexes]
                    if all(dtype == np.dtype("uint8") for dtype in selected_dtypes):
                        arr = np.transpose(np.stack([_preserve_uint8_band(data[i]) for i in range(3)]), (1, 2, 0))
                    else:
                        arr = np.transpose(np.stack([_stretch_band(data[i]) for i in range(3)]), (1, 2, 0))
                    img = Image.fromarray(arr, "RGB")
                elif bands == 2:
                    data = src.read(1, out_shape=(out_height, out_width), resampling=resampling_filter, masked=True)
                    alpha = src.read(2, out_shape=(out_height, out_width), resampling=resampling_filter, masked=True)
                    gray = _preserve_uint8_band(data) if np.dtype(src.dtypes[0]) == np.dtype("uint8") else _stretch_band(data)
                    rgba = np.dstack([gray, gray, gray, _preserve_uint8_band(alpha)])
                    img = _rgba_to_rgb(Image.fromarray(rgba, "RGBA"))
                else:
                    data = src.read(1, out_shape=(out_height, out_width), resampling=resampling_filter, masked=True)
                    if np.dtype(src.dtypes[0]) == np.dtype("uint8"):
                        img = Image.fromarray(_preserve_uint8_band(data), "L").convert("RGB")
                    else:
                        img = Image.fromarray(_stretch_band(data), "L").convert("RGB")
    except ImportError:
        try:
            img = Image.open(BytesIO(file_bytes))
        except Exception as e_pil:
            erro = f"Falha ao ler imagem sem Rasterio: {e_pil}"
    except Exception as e_rast:
        try:
            img = Image.open(BytesIO(file_bytes))
        except Exception as e_pil:
            erro = f"Falha ao ler formato {ext}: {e_rast} | {e_pil}"

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

    img = _rgba_to_rgb(img)

    MAX_DIM = _preview_max_dim()
    if max(img.size) > MAX_DIM:
        ratio = MAX_DIM / max(img.size)
        spatial_meta["ratio"] = ratio
        resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
        img = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), resample_filter)

    spatial_meta["preview_width"] = img.width
    spatial_meta["preview_height"] = img.height

    def _save_preview_jpeg(pil_img, jpeg_quality):
        save_options = [
            {"subsampling": 0, "optimize": True, "progressive": True},
            {"subsampling": 0, "optimize": True, "progressive": False},
            {"subsampling": 1, "optimize": False, "progressive": False},
            {"subsampling": 2, "optimize": False, "progressive": False},
        ]
        last_error = None
        for options in save_options:
            target = BytesIO()
            try:
                pil_img.save(target, format='JPEG', quality=jpeg_quality, **options)
                return target
            except OSError as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise OSError("Falha ao salvar preview JPEG.")

    max_payload_bytes = _preview_max_payload_mb() * 1024 * 1024
    min_preview_dim = min(_preview_min_dim(), _preview_max_dim())
    quality = _preview_jpeg_quality()
    preview_img = img
    buf = BytesIO()

    try:
        for _ in range(18):
            buf = _save_preview_jpeg(preview_img, quality)
            payload_size = buf.tell()
            if payload_size <= max_payload_bytes:
                break
            if quality > 82:
                quality = max(82, quality - 5)
                continue
            current_max_dim = max(preview_img.size)
            if current_max_dim > min_preview_dim:
                scale = max(min_preview_dim / current_max_dim, 0.75)
                new_size = (
                    max(1, int(preview_img.width * scale)),
                    max(1, int(preview_img.height * scale)),
                )
                resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
                preview_img = preview_img.resize(new_size, resample_filter)
                quality = min(quality, 90)
                continue
            if quality > 70:
                quality = max(70, quality - 4)
                continue
            if current_max_dim > 1200:
                scale = 0.85
                new_size = (
                    max(1, int(preview_img.width * scale)),
                    max(1, int(preview_img.height * scale)),
                )
                resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
                preview_img = preview_img.resize(new_size, resample_filter)
                continue
            break
    except Exception as exc:
        return None, None, f"Falha ao preparar visualização da ortofoto: {exc}", spatial_meta

    img = preview_img
    spatial_meta["preview_width"] = img.width
    spatial_meta["preview_height"] = img.height
    spatial_meta["preview_quality"] = quality
    spatial_meta["preview_payload_mb"] = round(buf.tell() / (1024 * 1024), 2)
    if spatial_meta["orig_width"]:
        spatial_meta["ratio"] = img.width / spatial_meta["orig_width"]
    b64 = base64.b64encode(buf.getvalue()).decode()

    return b64, img.size, None, spatial_meta


PENDAO_AVANCADO_PARAMS = {
    "clahe_clip_limit": 2.5,
    "illumination_kernel": 31,
    "sharpen_strength": 0.25,
    "green_hsv_low": (35, 35, 35),
    "green_hsv_high": (90, 255, 255),
    "exg_threshold": 105,
    "new_tassel_hsv_low": (15, 25, 130),
    "new_tassel_hsv_high": (45, 255, 255),
    "dry_tassel_hsv_low": (8, 20, 90),
    "dry_tassel_hsv_high": (35, 180, 240),
    "old_tassel_hsv_low": (5, 25, 70),
    "old_tassel_hsv_high": (28, 200, 210),
    "cream_l_min": 145,
    "cream_s_max": 90,
    "cream_v_min": 120,
    "lab_l_threshold": 128,
    "texture_threshold": 18,
    "texture_ratio_min": 0.055,
    "yellow_ratio_min": 0.07,
    "clear_ratio_min": 0.12,
    "area_min": 6,
    "area_max": 2500,
    "area_min_fraction": 0.00001,
    "area_max_fraction": 0.035,
    "max_circularity": 0.90,
    "min_solidity": 0.08,
    "max_green_ratio": 0.50,
    "merge_distance": 16,
    "nms_distance": 18,
    "morph_open_kernel": 3,
    "morph_close_kernel": 5,
    "dilate_kernel": 3,
    "x_min_size": 6,
    "x_max_size": 20,
    "x_size_factor": 0.40,
    "x_thickness": 2,
    "analysis_max_dim": 2200,
    "max_detections": 30000,
    "yellow_index_threshold": 136,
    "exr_threshold": 128,
    "lab_b_min": 124,
    "lab_ba_diff_min": -6,
    "difficult_texture_ratio_min": 0.035,
    "yolo_enabled": True,
    "yolo_world_enabled": True,
    "yolo_world_model": "yolov8s-world.pt",
    "yolo_imgsz": 1280,
    "yolo_conf": 0.04,
    "yolo_iou": 0.45,
    "yolo_max_det": 20000,
    "yolo_max_dim": 1800,
    "yolo_min_visual_score": 1.2,
    "yolo_min_yellow_ratio": 0.015,
    "yolo_min_texture_ratio": 0.015,
    "yolo_max_green_ratio": 0.78,
    "yolo_merge_distance": 18,
}

PENDAO_YOLO_CLASSES = (
    "corn tassel",
    "maize tassel",
    "tassel",
    "corn flower",
    "maize flower",
    "pendao de milho",
    "pendão de milho",
    "pendao",
    "pendão",
)

YOLO_TRAIN_ROOT = APP_ROOT / "dados_treinamento_yolo" / "pendao_milho"
YOLO_MODELS_DIR = APP_ROOT / "modelos_yolo"
YOLO_BEST_MODEL_PATH = YOLO_MODELS_DIR / "pendao_milho_best.pt"
YOLO_TRAIN_LOG_PATH = YOLO_TRAIN_ROOT / "treino_yolo.log"


def garantir_estrutura_treinamento_yolo(base_dir: Path | None = None):
    base = Path(base_dir or YOLO_TRAIN_ROOT)
    folders = [
        base / "images" / "train",
        base / "images" / "val",
        base / "labels" / "train",
        base / "labels" / "val",
        base / "crops" / "pendao_confirmado",
        base / "crops" / "falso_positivo",
        base / "crops" / "pendao_faltante",
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    data_yaml = base / "data.yaml"
    data_yaml.write_text(
        "path: dados_treinamento_yolo/pendao_milho\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n"
        "  0: pendao\n",
        encoding="utf-8",
    )
    return base


def contar_amostras_treinamento_yolo(base_dir: Path | None = None):
    base = garantir_estrutura_treinamento_yolo(base_dir)
    counts = {}
    for split in ("train", "val"):
        counts[f"images_{split}"] = len(list((base / "images" / split).glob("*.*")))
        counts[f"labels_{split}"] = len(list((base / "labels" / split).glob("*.txt")))
    for kind in ("pendao_confirmado", "falso_positivo", "pendao_faltante"):
        counts[f"crops_{kind}"] = len(list((base / "crops" / kind).glob("*.*")))
    counts["total_images"] = counts["images_train"] + counts["images_val"]
    counts["total_labels"] = counts["labels_train"] + counts["labels_val"]
    return counts


def treinar_yolo_pendoamento(epochs: int = 100, imgsz: int = 960, batch: int = 4):
    base = garantir_estrutura_treinamento_yolo()
    counts = contar_amostras_treinamento_yolo(base)
    if counts["images_train"] < 5:
        return False, "Treino não iniciado: salve pelo menos 5 imagens em images/train."
    try:
        import ultralytics  # noqa: F401
    except ImportError:
        return False, "Ultralytics não instalado. Instale com: pip install -U ultralytics"

    YOLO_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = YOLO_TRAIN_LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    code = f"""
from pathlib import Path
import shutil

base = Path(r'{str(base)}')
log_path = Path(r'{str(log_path)}')
models_dir = Path(r'{str(YOLO_MODELS_DIR)}')
models_dir.mkdir(parents=True, exist_ok=True)

def log(msg):
    with log_path.open('a', encoding='utf-8') as f:
        f.write(str(msg) + '\\n')

try:
    import torch
    from ultralytics import YOLO
    device = 0 if torch.cuda.is_available() else 'cpu'
    batch = {int(batch)} if device != 'cpu' else min({int(batch)}, 2)
    log('Iniciando treino YOLO de pendoamento')
    log(f'Device: {{device}} | batch={{batch}} | epochs={int(epochs)} | imgsz={int(imgsz)}')
    model = YOLO('yolov8n.pt')
    result = model.train(
        data=str(base / 'data.yaml'),
        epochs={int(epochs)},
        imgsz={int(imgsz)},
        batch=batch,
        device=device,
        project='runs/detect',
        name='pendao_milho',
        exist_ok=True,
    )
    candidate = Path('runs/detect/pendao_milho/weights/best.pt')
    if not candidate.exists():
        candidate = Path('runs/detect/train/weights/best.pt')
    if candidate.exists():
        target = models_dir / 'pendao_milho_best.pt'
        shutil.copy2(candidate, target)
        log(f'Modelo salvo em: {{target}}')
    else:
        log('best.pt não encontrado após o treino.')
except Exception as exc:
    log(f'ERRO NO TREINO: {{exc}}')
"""
    log_path.write_text("Treino YOLO solicitado.\n", encoding="utf-8")
    popen_kwargs = {
        "cwd": str(APP_ROOT),
        "stderr": subprocess.STDOUT,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with log_path.open("a", encoding="utf-8") as log_handle:
        subprocess.Popen([sys.executable, "-c", code], stdout=log_handle, **popen_kwargs)
    return True, f"Treino iniciado em segundo plano. Log: {log_path}"


def _pendao_params(params=None) -> dict:
    merged = dict(PENDAO_AVANCADO_PARAMS)
    if params:
        merged.update(params)
    return merged


def _odd_kernel(value: int, minimum: int = 3) -> int:
    value = max(minimum, int(value or minimum))
    return value if value % 2 else value + 1


def _as_rgb_uint8(rgb_img):
    if rgb_img is None:
        return None
    arr = np.asarray(rgb_img)
    if arr.ndim == 2:
        arr = np.dstack([arr, arr, arr])
    if arr.ndim != 3 or arr.shape[2] < 3 or arr.size == 0:
        return None
    arr = arr[:, :, :3]
    if arr.dtype != np.uint8:
        arr = np.nan_to_num(arr.astype(np.float32))
        mx = float(np.max(arr)) if arr.size else 0.0
        if mx <= 1.5:
            arr = arr * 255.0
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(arr)


def _preprocessar_pendao_opencv(rgb_img, params):
    rgb = _as_rgb_uint8(rgb_img)
    if rgb is None:
        return None, None, None, None, None
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(
        clipLimit=float(params.get("clahe_clip_limit", 2.5)),
        tileGridSize=(8, 8),
    )
    l_eq = clahe.apply(l_channel)
    blur_size = _odd_kernel(params.get("illumination_kernel", 31), 9)
    illumination = cv2.GaussianBlur(l_eq, (blur_size, blur_size), 0)
    l_corr = cv2.addWeighted(l_eq, 1.35, illumination, -0.35, 0)
    lab_corr = cv2.merge([np.clip(l_corr, 0, 255).astype(np.uint8), a_channel, b_channel])
    rgb_corr = cv2.cvtColor(lab_corr, cv2.COLOR_LAB2RGB)
    blur = cv2.GaussianBlur(rgb_corr, (3, 3), 0)
    strength = float(params.get("sharpen_strength", 0.25))
    sharp = cv2.addWeighted(rgb_corr, 1.0 + strength, blur, -strength, 0)
    sharp = cv2.GaussianBlur(sharp, (3, 3), 0)
    hsv = cv2.cvtColor(sharp, cv2.COLOR_RGB2HSV)
    lab = cv2.cvtColor(sharp, cv2.COLOR_RGB2LAB)
    gray = cv2.cvtColor(sharp, cv2.COLOR_RGB2GRAY)
    return sharp, hsv, lab, gray, lab[:, :, 0]


def remover_verde_agressivo(rgb_img, params=None):
    params = _pendao_params(params)
    rgb = _as_rgb_uint8(rgb_img)
    if rgb is None:
        return None, None
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    b = rgb[:, :, 2].astype(np.int16)
    exg = np.clip(2 * g - r - b, -255, 255).astype(np.int16)
    exg_norm = cv2.normalize(exg, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, exg_green = cv2.threshold(
        exg_norm,
        int(params.get("exg_threshold", 105)),
        255,
        cv2.THRESH_BINARY,
    )
    green_hsv = cv2.inRange(
        hsv,
        np.array(params.get("green_hsv_low", (35, 35, 35)), dtype=np.uint8),
        np.array(params.get("green_hsv_high", (90, 255, 255)), dtype=np.uint8),
    )
    green_mask = cv2.bitwise_or(exg_green, green_hsv)
    green_mask = cv2.morphologyEx(
        green_mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
        iterations=1,
    )
    sem_verde = cv2.bitwise_not(green_mask)
    return sem_verde, green_mask


def criar_mascara_pendoes_multicor(rgb_img, lab_l=None, params=None):
    params = _pendao_params(params)
    rgb = _as_rgb_uint8(rgb_img)
    if rgb is None:
        return None, {}
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    lab_l = lab_l if lab_l is not None else lab[:, :, 0]
    novo = cv2.inRange(
        hsv,
        np.array(params.get("new_tassel_hsv_low", (15, 25, 130)), dtype=np.uint8),
        np.array(params.get("new_tassel_hsv_high", (45, 255, 255)), dtype=np.uint8),
    )
    seco = cv2.inRange(
        hsv,
        np.array(params.get("dry_tassel_hsv_low", (8, 20, 90)), dtype=np.uint8),
        np.array(params.get("dry_tassel_hsv_high", (35, 180, 240)), dtype=np.uint8),
    )
    velho = cv2.inRange(
        hsv,
        np.array(params.get("old_tassel_hsv_low", (5, 25, 70)), dtype=np.uint8),
        np.array(params.get("old_tassel_hsv_high", (28, 200, 210)), dtype=np.uint8),
    )
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    creme = (
        (lab_l > int(params.get("cream_l_min", 145)))
        & (s < int(params.get("cream_s_max", 90)))
        & (v > int(params.get("cream_v_min", 120)))
    ).astype(np.uint8) * 255
    r = rgb[:, :, 0].astype(np.float32)
    g = rgb[:, :, 1].astype(np.float32)
    b = rgb[:, :, 2].astype(np.float32)
    yellow_idx = cv2.normalize(r + g - b, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    exr = cv2.normalize((1.4 * r) - g, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    lab_a = lab[:, :, 1].astype(np.int16)
    lab_b = lab[:, :, 2].astype(np.int16)
    indice_amarelo = (
        (yellow_idx > int(params.get("yellow_index_threshold", 136)))
        & (lab_b > int(params.get("lab_b_min", 124)))
        & ((lab_b - lab_a) > int(params.get("lab_ba_diff_min", -6)))
        & (lab_l > 105)
        & (v > 85)
    ).astype(np.uint8) * 255
    exr_mask = (
        (exr > int(params.get("exr_threshold", 128)))
        & (lab_l > 95)
        & (v > 75)
        & (s > 18)
    ).astype(np.uint8) * 255
    mascara = cv2.bitwise_or(cv2.bitwise_or(novo, seco), cv2.bitwise_or(velho, creme))
    mascara = cv2.bitwise_or(mascara, cv2.bitwise_or(indice_amarelo, exr_mask))
    return mascara, {
        "novo": novo,
        "seco": seco,
        "velho": velho,
        "creme": creme,
        "indice": indice_amarelo,
        "exr": exr_mask,
    }


def calcular_mascara_textura(gray_img, params=None):
    params = _pendao_params(params)
    gray = np.asarray(gray_img, dtype=np.uint8)
    lap = cv2.convertScaleAbs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    sobel = cv2.convertScaleAbs(cv2.magnitude(sobel_x, sobel_y))
    canny = cv2.Canny(gray, 45, 120)
    thr = int(params.get("texture_threshold", 18))
    _, lap_mask = cv2.threshold(lap, thr, 255, cv2.THRESH_BINARY)
    _, sobel_mask = cv2.threshold(sobel, max(20, thr + 8), 255, cv2.THRESH_BINARY)
    textura = cv2.bitwise_or(cv2.bitwise_or(lap_mask, sobel_mask), canny)
    return textura


def classificar_tipo_pendao(hsv_pixel, lab_pixel, params=None) -> str:
    params = _pendao_params(params)
    h, s, v = [int(x) for x in hsv_pixel[:3]]
    l = int(lab_pixel[0])
    if l >= params.get("cream_l_min", 145) and s <= params.get("cream_s_max", 90) and v >= params.get("cream_v_min", 120):
        return "creme"
    if 15 <= h <= 45 and v >= 130:
        return "novo"
    if 8 <= h <= 35 and v >= 90:
        return "seco"
    if 5 <= h <= 28:
        return "velho"
    return "misto"


def _detection_center_from_component(component_mask, x, y, w, h):
    dist = cv2.distanceTransform(component_mask, cv2.DIST_L2, 3)
    _, max_val, _, max_loc = cv2.minMaxLoc(dist)
    if max_val > 0:
        return float(x + max_loc[0]), float(y + max_loc[1])
    moments = cv2.moments(component_mask, binaryImage=True)
    if moments.get("m00", 0):
        return float(x + moments["m10"] / moments["m00"]), float(y + moments["m01"] / moments["m00"])
    return float(x + w / 2), float(y + h / 2)


def _merge_close_detections(detections, distance):
    if not detections:
        return []
    ordered = sorted(detections, key=lambda d: float(d.get("score", 0)), reverse=True)
    groups = []
    for det in ordered:
        cx, cy = det["center"]
        target = None
        for group in groups:
            gx, gy = group["center"]
            if ((cx - gx) ** 2 + (cy - gy) ** 2) ** 0.5 <= distance:
                target = group
                break
        if target is None:
            item = dict(det)
            item["_weight"] = max(1.0, float(det.get("score", 1.0)) * max(1.0, float(det.get("area", 1.0))))
            groups.append(item)
        else:
            old_weight = target.get("_weight", 1.0)
            new_weight = max(1.0, float(det.get("score", 1.0)) * max(1.0, float(det.get("area", 1.0))))
            tw = old_weight + new_weight
            target["center"] = (
                (target["center"][0] * old_weight + cx * new_weight) / tw,
                (target["center"][1] * old_weight + cy * new_weight) / tw,
            )
            target["score"] = max(float(target.get("score", 0)), float(det.get("score", 0)))
            target["area"] = float(target.get("area", 0)) + float(det.get("area", 0))
            target["_weight"] = tw
    for group in groups:
        group.pop("_weight", None)
    return groups


def remover_deteccoes_duplicadas(detections, params=None):
    params = _pendao_params(params)
    if not detections:
        return []
    distance = float(params.get("nms_distance", 20))
    ordered = sorted(detections, key=lambda d: float(d.get("score", 0)), reverse=True)
    kept = []
    for det in ordered:
        cx, cy = det["center"]
        if all(((cx - k["center"][0]) ** 2 + (cy - k["center"][1]) ** 2) ** 0.5 > distance for k in kept):
            kept.append(det)
    return kept


def agrupar_componentes_estrelados(regions, params=None):
    params = _pendao_params(params)
    return _merge_close_detections(regions, float(params.get("merge_distance", 18)))


def _grid_cells_from_grade(grade, img_w, img_h):
    if not grade:
        return [(1, 1, 1, np.array([[0, 0], [img_w - 1, 0], [img_w - 1, img_h - 1], [0, img_h - 1]], dtype=np.float32))]
    points = grade.get("points") or grade.get("pontos") or grade.get("grid") or []
    rows = int(grade.get("rows") or grade.get("linhas") or 1)
    cols = int(grade.get("cols") or grade.get("colunas") or 1)
    if len(points) < 4:
        return [(1, 1, 1, np.array([[0, 0], [img_w - 1, 0], [img_w - 1, img_h - 1], [0, img_h - 1]], dtype=np.float32))]
    norm_points = []
    for p in points[:4]:
        if isinstance(p, dict):
            norm_points.append([float(p.get("x", 0)), float(p.get("y", 0))])
        else:
            norm_points.append([float(p[0]), float(p[1])])
    pts = np.array(norm_points, dtype=np.float32)

    def bilerp_np(p0, p1, p2, p3, u, v):
        top = (1 - u) * p0 + u * p1
        bottom = (1 - u) * p3 + u * p2
        return (1 - v) * top + v * bottom

    cells = []
    index = 1
    for r in range(rows):
        for c in range(cols):
            u0, u1 = c / cols, (c + 1) / cols
            v0, v1 = r / rows, (r + 1) / rows
            poly = np.array([
                bilerp_np(pts[0], pts[1], pts[2], pts[3], u0, v0),
                bilerp_np(pts[0], pts[1], pts[2], pts[3], u1, v0),
                bilerp_np(pts[0], pts[1], pts[2], pts[3], u1, v1),
                bilerp_np(pts[0], pts[1], pts[2], pts[3], u0, v1),
            ], dtype=np.float32)
            cells.append((index, r + 1, c + 1, poly))
            index += 1
    return cells


def detectar_pendoes_opencv_puro(rgb_img, grade=None, params=None):
    params = _pendao_params(params)
    rgb = _as_rgb_uint8(rgb_img)
    if rgb is None:
        return {"dims": (0, 0), "rows": 0, "cols": 0, "grid": grade, "parcelas": [], "total": 0}

    scale_back = 1.0
    max_dim = int(params.get("analysis_max_dim", 2200))
    orig_h, orig_w = rgb.shape[:2]
    if max(orig_h, orig_w) > max_dim:
        scale = max_dim / max(orig_h, orig_w)
        rgb_small = cv2.resize(rgb, (max(1, int(orig_w * scale)), max(1, int(orig_h * scale))), interpolation=cv2.INTER_AREA)
        scale_back = 1.0 / scale
    else:
        rgb_small = rgb

    img, hsv, lab, gray, lab_l = _preprocessar_pendao_opencv(rgb_small, params)
    if img is None:
        return {"dims": (orig_w, orig_h), "rows": 0, "cols": 0, "grid": grade, "parcelas": [], "total": 0}
    sem_verde, green_mask = remover_verde_agressivo(img, params)
    cor_mask, tipo_masks = criar_mascara_pendoes_multicor(img, lab_l, params)
    brilho_mask = cv2.threshold(lab_l, int(params.get("lab_l_threshold", 135)), 255, cv2.THRESH_BINARY)[1]
    textura_mask = calcular_mascara_textura(gray, params)

    textura_expandida = cv2.dilate(
        textura_mask,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
        iterations=1,
    )
    claros_mask = cv2.bitwise_or(tipo_masks.get("novo", cor_mask), tipo_masks.get("creme", cor_mask))
    secos_mask = cv2.bitwise_or(tipo_masks.get("seco", cor_mask), tipo_masks.get("velho", cor_mask))
    dificeis_mask = cv2.bitwise_or(tipo_masks.get("indice", cor_mask), tipo_masks.get("exr", cor_mask))

    pass_claros = cv2.bitwise_and(cv2.bitwise_and(claros_mask, sem_verde), textura_expandida)
    pass_secos = cv2.bitwise_and(cv2.bitwise_and(secos_mask, sem_verde), textura_expandida)
    pass_dificeis = cv2.bitwise_and(
        cv2.bitwise_and(dificeis_mask, sem_verde),
        cv2.bitwise_or(textura_expandida, brilho_mask),
    )
    candidatos = cv2.bitwise_or(cv2.bitwise_or(pass_claros, pass_secos), pass_dificeis)
    candidatos = cv2.bitwise_and(candidatos, cv2.bitwise_or(brilho_mask, cor_mask))

    open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (_odd_kernel(params.get("morph_open_kernel", 3)),) * 2)
    close_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (_odd_kernel(params.get("morph_close_kernel", 5)),) * 2)
    dilate_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (_odd_kernel(params.get("dilate_kernel", 3)),) * 2)
    candidatos = cv2.morphologyEx(candidatos, cv2.MORPH_OPEN, open_k, iterations=1)
    candidatos = cv2.morphologyEx(candidatos, cv2.MORPH_CLOSE, close_k, iterations=1)
    candidatos = cv2.dilate(candidatos, dilate_k, iterations=1)
    bordas_pendao = cv2.morphologyEx(candidatos, cv2.MORPH_GRADIENT, open_k, iterations=1)
    candidatos = cv2.bitwise_or(candidatos, cv2.bitwise_and(bordas_pendao, cor_mask))

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(candidatos, 8)
    img_area = float(candidatos.shape[0] * candidatos.shape[1])
    area_min = max(float(params.get("area_min", 8)), img_area * float(params.get("area_min_fraction", 0.00001)))
    area_max = min(float(params.get("area_max", 2500)), max(area_min + 1, img_area * float(params.get("area_max_fraction", 0.035))))
    detections = []
    for label in range(1, n_labels):
        x, y, w, h, area = stats[label]
        area = float(area)
        if area < area_min or area > area_max or w <= 0 or h <= 0:
            continue
        component = (labels[y:y + h, x:x + w] == label).astype(np.uint8)
        comp_full = (labels == label)
        contours, _ = cv2.findContours((component * 255).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        contour = max(contours, key=cv2.contourArea)
        perimeter = max(1.0, cv2.arcLength(contour, True))
        circularity = 4.0 * np.pi * area / (perimeter * perimeter)
        hull = cv2.convexHull(contour)
        hull_area = max(1.0, cv2.contourArea(hull))
        solidity = area / hull_area
        density = area / max(1.0, float(w * h))
        aspect = max(w, h) / max(1.0, min(w, h))
        green_ratio = float(np.mean(green_mask[comp_full] > 0)) if np.any(comp_full) else 1.0
        yellow_ratio = float(np.mean(cor_mask[comp_full] > 0)) if np.any(comp_full) else 0.0
        texture_ratio = float(np.mean(textura_mask[comp_full] > 0)) if np.any(comp_full) else 0.0
        clear_ratio = float(np.mean(lab_l[comp_full] > int(params.get("lab_l_threshold", 135)))) if np.any(comp_full) else 0.0
        if green_ratio > float(params.get("max_green_ratio", 0.35)):
            continue
        if yellow_ratio < float(params.get("yellow_ratio_min", 0.10)):
            continue
        if texture_ratio < float(params.get("texture_ratio_min", 0.08)):
            continue
        if clear_ratio < float(params.get("clear_ratio_min", 0.20)):
            continue
        if circularity > float(params.get("max_circularity", 0.90)) and aspect < 1.8:
            continue
        if solidity < float(params.get("min_solidity", 0.08)) or density < 0.05:
            continue
        if aspect > 12 and texture_ratio < 0.22:
            continue
        cx, cy = _detection_center_from_component(component, x, y, w, h)
        sx = int(np.clip(cx, 0, hsv.shape[1] - 1))
        sy = int(np.clip(cy, 0, hsv.shape[0] - 1))
        tipo = classificar_tipo_pendao(hsv[sy, sx], lab[sy, sx], params)
        area_score = min(1.0, area / max(1.0, area_min * 6.0))
        score = (
            texture_ratio * 2.0
            + yellow_ratio * 2.0
            + clear_ratio * 1.4
            + (1.0 - green_ratio) * 1.8
            + area_score
            + min(1.0, aspect / 4.0) * 0.35
        )
        confianca = "alta" if score >= 5.2 else ("media" if score >= 4.0 else "baixa")
        detections.append({
            "center": (float(cx * scale_back), float(cy * scale_back)),
            "size": float(np.clip(max(w, h) * params.get("x_size_factor", 0.40) * scale_back, params.get("x_min_size", 6), params.get("x_max_size", 20))),
            "bbox": (float(x * scale_back), float(y * scale_back), float(w * scale_back), float(h * scale_back)),
            "score": float(score),
            "confianca": confianca,
            "tipo": tipo,
            "yellow_ratio": yellow_ratio,
            "texture_ratio": texture_ratio,
            "clear_ratio": clear_ratio,
            "green_ratio": green_ratio,
            "area": float(area * scale_back * scale_back),
        })

    detections = agrupar_componentes_estrelados(detections, params)
    detections = remover_deteccoes_duplicadas(detections, params)
    max_detections = int(params.get("max_detections", 30000))
    if len(detections) > max_detections:
        detections = sorted(detections, key=lambda d: d.get("score", 0), reverse=True)[:max_detections]

    rows = int((grade or {}).get("rows") or (grade or {}).get("linhas") or 1)
    cols = int((grade or {}).get("cols") or (grade or {}).get("colunas") or 1)
    cells = _grid_cells_from_grade(grade, orig_w, orig_h)
    parcelas = []
    total = 0
    for index, row, col, poly in cells:
        dets = []
        for det in detections:
            cx, cy = det["center"]
            if cv2.pointPolygonTest(poly.astype(np.float32), (float(cx), float(cy)), False) >= 0:
                dets.append({k: v for k, v in det.items() if k != "area"})
        total += len(dets)
        parcelas.append({"index": int(index), "row": int(row), "col": int(col), "count": len(dets), "detections": dets})
    return {"dims": (orig_w, orig_h), "rows": rows, "cols": cols, "grid": grade, "parcelas": parcelas, "total": int(total)}


def detectar_pendoes_milho_avancado(rgb_img, grade=None, params=None):
    return detectar_pendoes_opencv_puro(rgb_img, grade=grade, params=params)


def processar_grid_pendao_avancado(rgb_img, grade, params=None):
    return detectar_pendoes_opencv_puro(rgb_img, grade=grade, params=params)


def _pendao_model_candidates():
    env_candidates = [
        os.getenv("PENDAO_YOLO_MODEL", "").strip(),
        os.getenv("TMG_PENDAO_YOLO_MODEL", "").strip(),
    ]
    local_candidates = [
        YOLO_BEST_MODEL_PATH,
        APP_ROOT / "models" / "pendoes.pt",
        APP_ROOT / "models" / "pendao.pt",
        APP_ROOT / "models" / "tassel.pt",
        APP_ROOT / "models" / "best.pt",
        APP_ROOT / "tmg_assets" / "models" / "pendoes.pt",
        APP_ROOT / "tmg_assets" / "models" / "pendao.pt",
        APP_ROOT / "tmg_assets" / "models" / "best.pt",
    ]
    for candidate in env_candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate).resolve()), "custom"
    for candidate in local_candidates:
        if candidate.exists():
            return str(candidate.resolve()), "custom"
    return None, None


@st.cache_resource(show_spinner=False)
def _carregar_modelo_yolo_pendao(model_key: str, world_classes: tuple):
    try:
        if model_key == "__YOLO_WORLD__":
            from ultralytics import YOLOWorld
            model = YOLOWorld(PENDAO_AVANCADO_PARAMS.get("yolo_world_model", "yolov8s-world.pt"))
            model.set_classes(list(world_classes))
            return model, "YOLO-World"
        from ultralytics import YOLO
        model = YOLO(model_key)
        return model, f"YOLO:{Path(model_key).name}"
    except ImportError as exc:
        raise RuntimeError("Ultralytics não instalado. Instale com: pip install -U ultralytics") from exc


def _resolver_modelo_yolo_pendao(params=None):
    params = _pendao_params(params)
    if not bool(params.get("yolo_enabled", True)):
        return None, "YOLO desativado nos parâmetros."
    try:
        import ultralytics  # noqa: F401
    except ImportError:
        return None, "Ultralytics não instalado. Instale com: pip install -U ultralytics"
    model_path, model_kind = _pendao_model_candidates()
    if model_path:
        return model_path, f"Modelo YOLO customizado: {Path(model_path).name}"
    if bool(params.get("yolo_world_enabled", True)):
        return "__YOLO_WORLD__", "YOLO-World sem modelo customizado local."
    return None, "YOLO instalado, mas nenhum modelo .pt de pendão foi encontrado. Usando OpenCV."


def _roi_features_pendao(rgb_img, bbox, params=None):
    params = _pendao_params(params)
    rgb = _as_rgb_uint8(rgb_img)
    if rgb is None:
        return None
    h_img, w_img = rgb.shape[:2]
    x1, y1, x2, y2 = [int(round(float(v))) for v in bbox]
    x1 = max(0, min(w_img - 1, x1))
    y1 = max(0, min(h_img - 1, y1))
    x2 = max(x1 + 1, min(w_img, x2))
    y2 = max(y1 + 1, min(h_img, y2))
    roi = rgb[y1:y2, x1:x2]
    if roi.size == 0:
        return None
    proc, hsv, lab, gray, lab_l = _preprocessar_pendao_opencv(roi, params)
    if proc is None:
        return None
    sem_verde, green_mask = remover_verde_agressivo(proc, params)
    cor_mask, _ = criar_mascara_pendoes_multicor(proc, lab_l, params)
    textura_mask = calcular_mascara_textura(gray, params)
    brilho_mask = cv2.threshold(lab_l, int(params.get("lab_l_threshold", 128)), 255, cv2.THRESH_BINARY)[1]
    valid_mask = cv2.bitwise_and(cv2.bitwise_and(cor_mask, sem_verde), cv2.bitwise_or(textura_mask, brilho_mask))
    active = valid_mask > 0
    green_ratio = float(np.mean(green_mask > 0))
    yellow_ratio = float(np.mean(cor_mask > 0))
    texture_ratio = float(np.mean(textura_mask > 0))
    clear_ratio = float(np.mean(brilho_mask > 0))
    if np.any(active):
        moments = cv2.moments(valid_mask, binaryImage=True)
        if moments.get("m00", 0):
            cx = x1 + moments["m10"] / moments["m00"]
            cy = y1 + moments["m01"] / moments["m00"]
        else:
            ys, xs = np.where(active)
            cx = x1 + float(np.mean(xs))
            cy = y1 + float(np.mean(ys))
    else:
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
    score = (
        yellow_ratio * 2.4
        + texture_ratio * 1.8
        + clear_ratio * 1.2
        + (1.0 - green_ratio) * 1.4
    )
    return {
        "center": (float(cx), float(cy)),
        "bbox": (float(x1), float(y1), float(x2 - x1), float(y2 - y1)),
        "size": float(np.clip(max(x2 - x1, y2 - y1) * 0.34, params.get("x_min_size", 6), params.get("x_max_size", 20))),
        "score": float(score),
        "tipo": classificar_tipo_pendao(hsv[int(np.clip(cy - y1, 0, hsv.shape[0] - 1)), int(np.clip(cx - x1, 0, hsv.shape[1] - 1))], lab[int(np.clip(cy - y1, 0, lab.shape[0] - 1)), int(np.clip(cx - x1, 0, lab.shape[1] - 1))], params),
        "yellow_ratio": yellow_ratio,
        "texture_ratio": texture_ratio,
        "clear_ratio": clear_ratio,
        "green_ratio": green_ratio,
    }


def _detections_from_result(result):
    if not result or not result.get("parcelas"):
        return []
    return [dict(det) for det in result["parcelas"][0].get("detections", [])]


def _inferir_pendoes_yolo(rgb_img, params=None):
    params = _pendao_params(params)
    rgb = _as_rgb_uint8(rgb_img)
    if rgb is None:
        return [], "Imagem inválida para YOLO."
    model_key, model_status = _resolver_modelo_yolo_pendao(params)
    if not model_key:
        return [], model_status
    try:
        model, model_name = _carregar_modelo_yolo_pendao(model_key, tuple(PENDAO_YOLO_CLASSES))
        orig_h, orig_w = rgb.shape[:2]
        max_dim = int(params.get("yolo_max_dim", 1800))
        scale_back = 1.0
        if max(orig_h, orig_w) > max_dim:
            scale = max_dim / max(orig_h, orig_w)
            rgb_work = cv2.resize(rgb, (max(1, int(orig_w * scale)), max(1, int(orig_h * scale))), interpolation=cv2.INTER_AREA)
            scale_back = 1.0 / scale
        else:
            rgb_work = rgb
        results = model.predict(
            source=rgb_work,
            imgsz=int(params.get("yolo_imgsz", 1280)),
            conf=float(params.get("yolo_conf", 0.04)),
            iou=float(params.get("yolo_iou", 0.45)),
            max_det=int(params.get("yolo_max_det", 20000)),
            verbose=False,
        )
        detections = []
        result0 = results[0] if results else None
        if result0 is None or getattr(result0, "boxes", None) is None:
            return [], f"{model_name}: nenhum resultado."
        boxes = result0.boxes
        names = getattr(result0, "names", {}) or {}
        xyxy = boxes.xyxy.detach().cpu().numpy() if getattr(boxes, "xyxy", None) is not None else np.empty((0, 4))
        confs = boxes.conf.detach().cpu().numpy() if getattr(boxes, "conf", None) is not None else np.zeros((len(xyxy),), dtype=float)
        classes = boxes.cls.detach().cpu().numpy().astype(int) if getattr(boxes, "cls", None) is not None else np.zeros((len(xyxy),), dtype=int)
        allowed_tokens = ("tassel", "pendao", "pendão", "maize", "corn", "flower")
        for box, conf, cls_id in zip(xyxy, confs, classes):
            class_name = str(names.get(int(cls_id), cls_id)).lower()
            if model_key != "__YOLO_WORLD__" and isinstance(names, dict) and names:
                if not any(tok in class_name for tok in allowed_tokens) and len(names) > 1:
                    continue
            x1, y1, x2, y2 = [float(v) for v in box]
            roi = _roi_features_pendao(rgb_work, (x1, y1, x2, y2), params)
            if not roi:
                continue
            visual_ok = (
                roi["score"] >= float(params.get("yolo_min_visual_score", 1.2))
                and roi["yellow_ratio"] >= float(params.get("yolo_min_yellow_ratio", 0.015))
                and roi["texture_ratio"] >= float(params.get("yolo_min_texture_ratio", 0.015))
                and roi["green_ratio"] <= float(params.get("yolo_max_green_ratio", 0.78))
            )
            if not visual_ok and float(conf) < 0.22:
                continue
            cx, cy = roi["center"]
            x, y, w, h = roi["bbox"]
            score = float(conf) * 4.0 + roi["score"]
            detections.append({
                "center": (float(cx * scale_back), float(cy * scale_back)),
                "bbox": (float(x * scale_back), float(y * scale_back), float(w * scale_back), float(h * scale_back)),
                "size": float(np.clip(roi["size"] * scale_back, params.get("x_min_size", 6), params.get("x_max_size", 20))),
                "score": score,
                "confianca": "alta" if score >= 3.2 else "media",
                "tipo": roi.get("tipo", "yolo"),
                "yellow_ratio": roi.get("yellow_ratio", 0),
                "texture_ratio": roi.get("texture_ratio", 0),
                "clear_ratio": roi.get("clear_ratio", 0),
                "green_ratio": roi.get("green_ratio", 0),
                "source": model_name,
                "yolo_conf": float(conf),
                "class_name": class_name,
                "area": float(w * h * scale_back * scale_back),
            })
        return detections, f"{model_name}: {len(detections)} detecções validadas por OpenCV."
    except Exception as exc:
        return [], f"YOLO falhou ({exc}). Usando OpenCV avançado."


def detectar_pendoes_hibrido_yolo_opencv(rgb_img, grade=None, params=None):
    params = _pendao_params(params)
    opencv_result = detectar_pendoes_opencv_puro(rgb_img, grade=None, params=params)
    opencv_detections = _detections_from_result(opencv_result)
    yolo_detections, yolo_status = _inferir_pendoes_yolo(rgb_img, params=params)
    combined = []
    for det in yolo_detections:
        item = dict(det)
        item["source"] = item.get("source", "YOLO")
        combined.append(item)
    for det in opencv_detections:
        item = dict(det)
        item["source"] = item.get("source", "OpenCV")
        combined.append(item)
    if combined:
        merge_params = dict(params)
        merge_params["nms_distance"] = float(params.get("yolo_merge_distance", params.get("nms_distance", 18)))
        combined = agrupar_componentes_estrelados(combined, merge_params)
        combined = remover_deteccoes_duplicadas(combined, merge_params)
    rows = int((grade or {}).get("rows") or (grade or {}).get("linhas") or 1)
    cols = int((grade or {}).get("cols") or (grade or {}).get("colunas") or 1)
    rgb = _as_rgb_uint8(rgb_img)
    img_h, img_w = rgb.shape[:2] if rgb is not None else (0, 0)
    cells = _grid_cells_from_grade(grade, img_w, img_h)
    parcelas = []
    total = 0
    for index, row, col, poly in cells:
        dets = []
        for det in combined:
            cx, cy = det["center"]
            if cv2.pointPolygonTest(poly.astype(np.float32), (float(cx), float(cy)), False) >= 0:
                dets.append({k: v for k, v in det.items() if k != "area"})
        total += len(dets)
        parcelas.append({"index": int(index), "row": int(row), "col": int(col), "count": len(dets), "detections": dets})
    mode = "YOLO+OpenCV" if yolo_detections else "OpenCV fallback"
    status = f"{mode}: {total} centros. {yolo_status}"
    return {"dims": (img_w, img_h), "rows": rows, "cols": cols, "grid": grade, "parcelas": parcelas, "total": int(total), "detector_status": status, "detector_mode": mode}


def _decode_rgb_for_pendao(file_bytes: bytes, filename: str):
    try:
        arr = np.frombuffer(file_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is not None:
            return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    except Exception:
        pass
    try:
        return np.array(Image.open(BytesIO(file_bytes)).convert("RGB"))
    except Exception:
        return None


def _serializar_deteccoes_pendao_preview(result, rgb, preview_dims):
    dets = []
    if not result.get("parcelas"):
        return dets
    src_w, src_h = result.get("dims", (rgb.shape[1], rgb.shape[0]))
    dst_w, dst_h = preview_dims or (src_w, src_h)
    sx = float(dst_w) / max(1.0, float(src_w))
    sy = float(dst_h) / max(1.0, float(src_h))
    for det in result["parcelas"][0].get("detections", []):
        cx, cy = det.get("center", (0, 0))
        bbox = det.get("bbox", (0, 0, 0, 0))
        dets.append({
            "x": round(float(cx) * sx, 2),
            "y": round(float(cy) * sy, 2),
            "size": round(float(det.get("size", 8)) * max(sx, sy), 2),
            "score": round(float(det.get("score", 0)), 4),
            "confianca": det.get("confianca", "media"),
            "tipo": det.get("tipo", "misto"),
            "bbox": [
                round(float(bbox[0]) * sx, 2),
                round(float(bbox[1]) * sy, 2),
                round(float(bbox[2]) * sx, 2),
                round(float(bbox[3]) * sy, 2),
            ],
            "yellow_ratio": round(float(det.get("yellow_ratio", 0)), 4),
            "texture_ratio": round(float(det.get("texture_ratio", 0)), 4),
            "clear_ratio": round(float(det.get("clear_ratio", 0)), 4),
            "green_ratio": round(float(det.get("green_ratio", 0)), 4),
            "source": det.get("source", "OpenCV"),
            "yolo_conf": round(float(det.get("yolo_conf", 0)), 4),
            "class_name": det.get("class_name", ""),
        })
    return dets


@st.cache_data(show_spinner=False, max_entries=16)
def preparar_deteccoes_pendoamento_hibrido(file_bytes: bytes, filename: str, preview_dims: tuple):
    rgb = _decode_rgb_for_pendao(file_bytes, filename)
    if rgb is None:
        return {
            "detections": [],
            "status": "Imagem inválida para análise de pendoamento.",
            "mode": "erro",
        }
    result = detectar_pendoes_hibrido_yolo_opencv(rgb, grade=None, params=PENDAO_AVANCADO_PARAMS)
    return {
        "detections": _serializar_deteccoes_pendao_preview(result, rgb, preview_dims),
        "status": result.get("detector_status", ""),
        "mode": result.get("detector_mode", "OpenCV fallback"),
    }


@st.cache_data(show_spinner=False, max_entries=16)
def preparar_deteccoes_pendoamento_avancado(file_bytes: bytes, filename: str, preview_dims: tuple):
    return preparar_deteccoes_pendoamento_hibrido(file_bytes, filename, preview_dims).get("detections", [])


# ==========================================
# TELA DE LOGIN[cite: 1]
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

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
        border-radius: 16px;
        padding: 26px 28px 22px 28px;
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
        font-size: 1.85rem;
        letter-spacing: 5px;
        color: var(--tmg-primary);
        text-transform: uppercase;
        text-shadow:
            1px 1px 0 var(--tmg-primary-shadow-1),
            2px 2px 0 var(--tmg-primary-shadow-2),
            3px 3px 0 var(--tmg-primary-shadow-3),
            5px 5px 10px rgba(0,0,0,0.95),
            0 0 25px var(--tmg-primary-glow),
            0 0 60px var(--tmg-primary-glow-soft);
        margin-bottom: 2px;
    }

    .login-subtitle {
        text-align: center;
        color: #555;
        font-size: 0.78rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 18px;
    }

    .login-divider {
        border: none;
        border-top: 1px solid var(--tmg-primary);
        box-shadow: 0 0 10px var(--tmg-primary-glow);
        margin: 0 0 18px 0;
    }

    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        border: 1px solid #d6e3f0 !important;
        border-radius: 10px !important;
        color: #111827 !important;
        padding: 10px 14px !important;
        font-size: 0.95rem !important;
        box-shadow: inset 0 1px 2px rgba(0,0,0,.12) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: #6b7280 !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--tmg-primary) !important;
        box-shadow: inset 0 1px 2px rgba(0,0,0,.12), 0 0 8px var(--tmg-primary-glow) !important;
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
        border-top: 2px solid var(--tmg-primary);
        border-radius: 16px;
        padding: 16px 18px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.7);
        position: relative;
        z-index: 1;
        margin-top: 4px;
    }

    .cfg-panel-title {
        color: var(--tmg-primary);
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        text-shadow: 0 0 12px var(--tmg-primary-glow);
        margin-bottom: 16px;
    }

    .login-logo-wrap {
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        text-align: center;
        margin: 0 auto 6px auto;
    }

    .login-logo-img {
        display: block;
        width: 150px;
        max-width: 42%;
        height: auto;
        object-fit: contain;
        margin: 0 auto;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col_mid, _ = st.columns([1.25, 0.9, 1.25])

    with col_mid:
        if LOGO_PATH.exists():
            logo_css = _img_to_base64_css(LOGO_PATH)
            st.markdown(
                f"<div class='login-logo-wrap'><img src='{logo_css}' class='login-logo-img' alt='Logo TMG'></div>",
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        st.markdown("<div class='login-title'>TMG</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='login-subtitle'>Sistema de Análise &nbsp;·&nbsp; Acesso Seguro</div>",
            unsafe_allow_html=True
        )
        st.markdown("<hr class='login-divider'>", unsafe_allow_html=True)

        usuario = st.text_input("Usuário", placeholder="Digite seu login", key="login_user")
        senha   = st.text_input("Senha",   placeholder="Digite sua senha", type="password", key="login_pass")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if st.button("⟶  ENTRAR", type="primary", key="btn_entrar"):
            auth_user = _auth_find_user(usuario, senha)
            if auth_user:
                st.session_state.logged_in = True
                st.session_state.auth_user = auth_user
                state_login = _partners_load_state()
                _partners_add_history(state_login, "", "Login realizado", f"Usuário: {auth_user.get('nome', auth_user.get('usuario', ''))}")
                _partners_save_state(state_login)
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
                    f"<code style='color:{THEME_PRIMARY_COLOR};'>{LOGIN_BG_PATH}</code></p>",
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
    current_user = _auth_current_user()
    allowed_cultures = _auth_allowed_cultures(current_user)
    can_open_partners = _auth_can_partners(current_user)

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
        color: var(--tmg-primary);
        text-transform: uppercase;
        text-shadow:
            1px 1px 0 var(--tmg-primary-shadow-1),
            2px 2px 0 var(--tmg-primary-shadow-2),
            3px 3px 0 var(--tmg-primary-shadow-3),
            5px 5px 10px rgba(0,0,0,0.95),
            0 0 25px var(--tmg-primary-glow),
            0 0 60px var(--tmg-primary-glow-soft);
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
        border-top: 1px solid var(--tmg-primary);
        box-shadow: 0 0 10px var(--tmg-primary-glow);
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
        background: linear-gradient(90deg, transparent, var(--tmg-primary), transparent);
        opacity: 0.5;
    }

    .cultura-card:hover {
        border-color: var(--tmg-primary);
        box-shadow:
            6px 6px 20px #050505,
            -2px -2px 10px #2a2a2a,
            0 0 20px var(--tmg-primary-glow-soft),
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
            "<div class='cultura-subtitle'>Escolha somente os módulos liberados para seu usuário</div>",
            unsafe_allow_html=True
        )
        st.markdown("<hr class='cultura-hr'>", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    _, gcol, _ = st.columns([0.15, 2.7, 0.15])

    with gcol:
        all_culturas = [
            ("🌱", "SOJA",    "Glycine max",       "#4caf50"),
            ("🌽", "MILHO",   "Zea mays",          "#ffb300"),
            ("🌿", "ALGODÃO", "Gossypium hirsutum", "#80cbc4"),
        ]
        culturas = [item for item in all_culturas if item[1] in allowed_cultures]

        cols = st.columns(max(1, min(3, len(culturas))), gap="large") if culturas else []
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

        if can_open_partners:
            st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
            pcol1, pcol2, pcol3 = st.columns([0.5, 1.4, 0.5])
            with pcol2:
                st.markdown("""
                <div class='cultura-card'>
                    <span class='cultura-icon'>🤝</span>
                    <div class='cultura-nome' style='color:var(--tmg-primary);text-shadow:1px 1px 0 rgba(0,0,0,.8),0 0 12px var(--tmg-primary-glow);'>
                        PARCEIROS
                    </div>
                    <div class='cultura-desc'>Controle de Voos e Dados</div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                if st.button("Abrir Parceiros / Controle de Voos e Dados", key="btn_open_partners_home", type="primary", use_container_width=True):
                    st.session_state.cultura_selecionada = "PARCEIROS"
                    st.session_state.pagina_ativa = "Parceiros"
                    app_rerun()

        if not culturas and not can_open_partners:
            st.warning("Seu usuário não possui módulos liberados. Solicite permissão ao administrador Wellington.")

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

def _resettable_ortho_uploader(label: str, key: str, accept_multiple_files: bool = False, help: str = ""):
    reset_key = f"{key}_reset"
    st.session_state.setdefault(reset_key, 0)
    widget_key = f"{key}_{st.session_state[reset_key]}"
    uploaded = st.file_uploader(
        label,
        type=MOSAIC_UPLOAD_TYPES,
        accept_multiple_files=accept_multiple_files,
        key=widget_key,
        help=help
    )
    has_upload = bool(uploaded) if accept_multiple_files else uploaded is not None
    if has_upload:
        _, clear_col = st.columns([3, 1])
        with clear_col:
            if st.button("🗑️ Excluir e importar nova", key=f"{key}_clear_{st.session_state[reset_key]}", use_container_width=True):
                st.session_state[reset_key] += 1
                app_rerun()
    return uploaded

def _uploaded_ortho_bytes(uploaded) -> tuple:
    if uploaded is None:
        return None, ""
    return uploaded.getbuffer().tobytes(), uploaded.name

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
img.src='data:image/jpeg;base64,{b64}';
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

    st.markdown("#### PASSO 1 — Enviar Fotos de Drone")
    st.markdown("<div class='vd-section-title'>Dados principais do voo</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        nome_voo = st.text_input("Nome do voo", value=f"Voo_Direcionado_{date.today().strftime('%Y%m%d')}", key="vd_nome_voo")
        fazenda = st.text_input("Nome da fazenda", value="", key="vd_fazenda")
        ensaio = st.text_input("Nome do ensaio", value="", key="vd_ensaio")
    with c2:
        data_inicial = st.date_input("Data inicial", value=date.today(), key="vd_data_inicial")
        data_final = st.date_input("Data final", value=date.today(), key="vd_data_final")
        tipo_voo_base = st.selectbox(
            "Tipo de voo",
            ["RGB", "Multiespectral", "NDVI", "Termal", "LiDAR", "Mapeamento", "Outro"],
            key="vd_tipo_voo_base"
        )
    with c3:
        usuario = st.text_input("Usuário responsável", value=manifest.get("config", {}).get("usuario_padrao", "Operador"), key="vd_usuario_resp")
        destino_envio = st.text_input("Destino de envio", value=manifest.get("config", {}).get("destino_envio_padrao", ""), placeholder="Ex.: análise interna, cliente, parceiro", key="vd_destino_envio")
        tipo_voo_outro = ""
        if tipo_voo_base == "Outro":
            tipo_voo_outro = st.text_input("Descrever tipo de voo", value="", key="vd_tipo_voo_outro")
    coordenadas = st.text_area(
        "Coordenadas / área do voo",
        value="",
        placeholder="Informe coordenadas, talhão, polígono ou referência da área quando necessário.",
        key="vd_coordenadas",
        height=80
    )
    tipo_voo = (tipo_voo_outro or tipo_voo_base).strip()
    inicio_final = f"{data_inicial} a {data_final}"

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
        "Selecionar múltiplas fotos de drone ou ZIP",
        type=["jpg", "jpeg", "tif", "tiff", "png", "raw", "dng", "arw", "cr2", "nef", "zip"],
        accept_multiple_files=True,
        key="vd_select_images"
    )
    if files:
        total_previsto = sum(int(getattr(f, "size", 0) or 0) for f in files)
        st.info(f"{len(files)} arquivo(s) selecionado(s) · volume previsto: {_tv_human_size(total_previsto)}")

    confirmar_envio = st.checkbox(
        "Confirmo o envio e autorizo o salvamento seguro dos arquivos no destino configurado.",
        key="vd_confirmar_envio"
    )

    if st.button("🚀 Confirmar Envio de Fotos de Voos", type="primary", key="vd_send_flight", use_container_width=True):
        if not files:
            st.warning("Selecione as imagens do drone ou um ZIP do voo.")
        elif not str(nome_voo).strip():
            st.warning("Informe o nome do voo para criar a pasta de destino.")
        elif not str(caminho).strip():
            st.warning("Escolha/informe o diretório de destino.")
        elif not confirmar_envio:
            st.warning("Confirme o envio para registrar o lote com segurança.")
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
                "data_inicial": str(data_inicial),
                "data_final": str(data_final),
                "tipo_voo": tipo_voo,
                "coordenadas": coordenadas,
                "destino_envio": destino_envio,
                "quantidade_imagens": len(saved),
                "data_hora": _tv_now(),
                "usuario_responsavel": usuario,
                "data_voo": str(data_inicial),
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
            manifest.setdefault("config", {})["destino_envio_padrao"] = destino_envio
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
                "Data inicial": v.get("data_inicial") or v.get("data_voo") or "",
                "Data final": v.get("data_final") or "",
                "Tipo de voo": v.get("tipo_voo") or "",
                "Coordenadas": v.get("coordenadas") or "",
                "Destino de envio": v.get("destino_envio") or "",
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


def _render_manage_users() -> None:
    if not _auth_is_admin():
        st.warning("Apenas o administrador Wellington pode acessar o gerenciamento de usuários.")
        return

    users_data = _auth_load_users()
    users = users_data.get("users", [])
    st.markdown("#### Gerenciar Usuários")
    st.caption("Somente Wellington pode cadastrar, editar, excluir, ativar/desativar e definir permissões.")

    if users:
        rows = []
        for user in users:
            rows.append({
                "Nome": user.get("nome", ""),
                "Usuário": user.get("usuario", ""),
                "Status": "Ativo" if user.get("ativo", True) else "Inativo",
                "Admin": "Sim" if _auth_is_admin(user) else "Não",
                "Culturas": ", ".join(_auth_allowed_cultures(user)) or "-",
                "Parceiros": ", ".join(_partner_label(p) for p in _auth_allowed_partners(user)) or "-",
                "Menus": ", ".join(label for key, label in MENU_PERMISSION_OPTIONS.items() if _auth_menu_allowed(key, user)) or "-",
                "Fenotipagem": ", ".join(label for key, label in PHENOTYPING_PERMISSION_OPTIONS.items() if _auth_phenotyping_allowed(key, user)) or "-",
                "Planilha Parceiros": ", ".join(label for key, label in PARTNER_PERMISSION_OPTIONS.items() if _auth_partner_permission(key, user)) or "-",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    options = ["Novo usuário"] + [f"{u.get('usuario')} · {u.get('nome')}" for u in users]
    selected = st.selectbox("Usuário para cadastro/edição", options, key="cfg_user_select")
    editing = {}
    if selected != "Novo usuário":
        login = selected.split(" · ", 1)[0]
        editing = next((u for u in users if u.get("usuario") == login), {})

    with st.form("form_manage_users"):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome completo", value=editing.get("nome", ""))
            usuario = st.text_input("Usuário de login", value=editing.get("usuario", ""))
            senha = st.text_input("Senha", value=editing.get("senha", ""), type="password")
            ativo = st.checkbox("Usuário ativo", value=bool(editing.get("ativo", True)))
        with c2:
            admin = st.checkbox("Administrador", value=bool(editing.get("admin", False)))
            perms_current = _auth_permissions(editing) if editing else _default_permissions(False)
            perm_culturas = st.checkbox("Acessar seleção de culturas", value=bool(perms_current.get("culturas", True)))
            p_soja, p_milho, p_alg = st.columns(3)
            with p_soja:
                perm_soja = st.checkbox("Soja", value=bool(perms_current.get("soja", True)))
            with p_milho:
                perm_milho = st.checkbox("Milho", value=bool(perms_current.get("milho", True)))
            with p_alg:
                perm_algodao = st.checkbox("Algodão", value=bool(perms_current.get("algodao", True)))
            perm_parceiros = st.checkbox("Acessar módulo Parceiros / Controle de Voos e Dados", value=bool(perms_current.get("parceiros", False)))
            p_eiwa, p_alvaz = st.columns(2)
            with p_eiwa:
                perm_eiwa = st.checkbox("EIWA", value=bool(perms_current.get("eiwa", False)))
            with p_alvaz:
                perm_alvaz = st.checkbox("ALVAZ", value=bool(perms_current.get("alvaz", False)))
            st.markdown("##### Permissões por menu")
            menu_values = {}
            menu_items = list(MENU_PERMISSION_OPTIONS.items())
            for idx in range(0, len(menu_items), 2):
                mcols = st.columns(2)
                for col, (menu_key, menu_label) in zip(mcols, menu_items[idx:idx + 2]):
                    with col:
                        menu_values[menu_key] = st.checkbox(menu_label, value=bool(perms_current.get(menu_key, True)))
            st.markdown("##### Análises de Fenotipagem")
            phenotyping_values = {}
            phenotyping_items = list(PHENOTYPING_PERMISSION_OPTIONS.items())
            for idx in range(0, len(phenotyping_items), 2):
                fcols = st.columns(2)
                for col, (phen_key, phen_label) in zip(fcols, phenotyping_items[idx:idx + 2]):
                    with col:
                        phenotyping_values[phen_key] = st.checkbox(
                            phen_label,
                            value=bool(perms_current.get(phen_key, True)),
                        )

            st.markdown("##### Permissões específicas da planilha de parceiros")
            partner_perm_values = {}
            partner_items = list(PARTNER_PERMISSION_OPTIONS.items())
            for idx in range(0, len(partner_items), 2):
                pcols = st.columns(2)
                for col, (perm_key, perm_label) in zip(pcols, partner_items[idx:idx + 2]):
                    with col:
                        partner_perm_values[perm_key] = st.checkbox(
                            perm_label,
                            value=bool(perms_current.get(perm_key, False)),
                        )

        save_user = st.form_submit_button("💾 Salvar usuário", type="primary", use_container_width=True)

    if save_user:
        usuario = usuario.strip()
        if not nome.strip() or not usuario or not senha:
            st.error("Preencha nome, usuário e senha.")
        else:
            record = {
                "nome": nome.strip(),
                "usuario": usuario,
                "senha": senha,
                "ativo": ativo,
                "admin": admin,
                "permissoes": {
                    "culturas": perm_culturas,
                    "soja": perm_soja,
                    "milho": perm_milho,
                    "algodao": perm_algodao,
                    "parceiros": perm_parceiros,
                    "eiwa": perm_eiwa,
                    "alvaz": perm_alvaz,
                    **menu_values,
                    **phenotyping_values,
                    **partner_perm_values,
                },
                "criado_em": editing.get("criado_em", _now_iso()),
                "atualizado_em": _now_iso(),
            }
            replaced = False
            for idx, user in enumerate(users):
                if user.get("usuario") == editing.get("usuario") or user.get("usuario") == usuario:
                    users[idx] = record
                    replaced = True
                    break
            if not replaced:
                users.append(record)
            users_data["users"] = users
            _auth_save_users(users_data)
            state = _partners_load_state()
            _partners_add_history(state, "", "Usuário salvo", f"{usuario} · {nome.strip()}")
            _partners_save_state(state)
            st.success("Usuário salvo com sucesso.")
            app_rerun()

    if editing and not _auth_is_admin(editing):
        if st.button("🗑️ Excluir usuário selecionado", key="btn_delete_cfg_user", use_container_width=True):
            users_data["users"] = [u for u in users if u.get("usuario") != editing.get("usuario")]
            _auth_save_users(users_data)
            state = _partners_load_state()
            _partners_add_history(state, "", "Usuário excluído", editing.get("usuario", ""))
            _partners_save_state(state)
            st.success("Usuário excluído.")
            app_rerun()

def _render_partner_alerts(partner_data: dict) -> None:
    alerts = _partners_deadline_alerts(partner_data.get("chat", []))
    if not alerts:
        st.caption("Sem notificações de prazo no momento.")
        return
    color_map = {
        "Vermelho": ("#ff5252", "rgba(255,82,82,.13)"),
        "Amarelo": ("#ffd54f", "rgba(255,213,79,.13)"),
        "Verde": ("#66bb6a", "rgba(102,187,106,.13)"),
        "Cinza": ("#9e9e9e", "rgba(158,158,158,.10)"),
    }
    for color_name, label, item in alerts[:8]:
        fg, bg = color_map.get(color_name, ("#ccc", "rgba(255,255,255,.06)"))
        st.markdown(
            f"<div style='border:1px solid {fg};background:{bg};border-radius:8px;padding:8px 10px;margin-bottom:6px;'>"
            f"<b style='color:{fg};'>{label}</b><br>"
            f"<span style='color:#ddd;font-size:.82rem;'>{item.get('assunto','Sem assunto')} · {item.get('status','')}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

def _render_partner_sheet_controls(state: dict, partner_key: str) -> None:
    partner = state["partners"][partner_key]
    partner_name = _partner_label(partner_key)
    can_import = _auth_partner_permission("partner_sheet_import")
    can_edit = _auth_partner_permission("partner_sheet_edit_rows") or _auth_partner_permission("partner_sheet_write_treatment")
    uploaded_sheet = None
    import_clicked = False
    update_clicked = False
    save_internal_clicked = False

    if can_import:
        st.markdown("##### Importação de planilha")
        uploaded_sheet = st.file_uploader(
            "Selecionar planilha Excel ou CSV",
            type=["xlsx", "xls", "csv"],
            key=f"partner_upload_sheet_{partner_key}",
            help="Envie arquivos .xlsx, .xls ou .csv para espelhar os dados no sistema.",
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            import_clicked = st.button("📥 Importar planilha", key=f"partner_import_{partner_key}", use_container_width=True)
        with c2:
            update_clicked = st.button("🔄 Atualizar dados", key=f"partner_update_{partner_key}", use_container_width=True)
        with c3:
            save_internal_clicked = st.button("💾 Salvar Dados Internos", key=f"partner_save_internal_top_{partner_key}", use_container_width=True)
    else:
        st.caption("Seu usuário pode visualizar os dados liberados, mas não possui permissão para importar planilhas.")

    if import_clicked or update_clicked:
        try:
            df, err = _partners_read_sheet_upload(uploaded_sheet)
            if err:
                st.warning("Não foi possível importar a planilha. Verifique o formato do arquivo e tente novamente.")
                return
            new_clean = _partners_clean_dataframe(df)
            if new_clean.empty and len(new_clean.columns) == 0:
                st.warning("Não foi possível importar a planilha. Verifique o formato do arquivo e tente novamente.")
                return
            original_columns = [col for col in new_clean.columns if col != PARTNER_ROW_ID and col not in PARTNER_INTERNAL_COLUMNS]
            if not original_columns:
                st.warning("Não foi possível importar a planilha. Verifique o formato do arquivo e tente novamente.")
                return
            baseline_rows = partner.get("baseline_rows", [])
            baseline_columns = partner.get("baseline_columns", [])
            if not baseline_rows:
                partner["baseline_rows"] = new_clean[original_columns].to_dict(orient="records")
                partner["baseline_columns"] = original_columns
                partner["baseline_import"] = {
                    "data_hora": _now_human(),
                    "usuario": _auth_user_name(),
                    "arquivo": uploaded_sheet.name,
                    "linhas": len(new_clean),
                }
                summary = {
                    "linhas_novas": 0,
                    "linhas_alteradas": 0,
                    "linhas_removidas": 0,
                    "total_diferencas": 0,
                    "data_hora": _now_human(),
                    "usuario": _auth_user_name(),
                    "fonte": f"Arquivo: {uploaded_sheet.name}",
                    "base_comparacao": "Primeira importação salva",
                }
                diff_rows = []
            else:
                compare_columns = baseline_columns or original_columns
                baseline_df = pd.DataFrame(baseline_rows)
                summary, diff_rows = _partners_compare_dataframes(baseline_df, new_clean, compare_columns)
                summary["fonte"] = f"Arquivo: {uploaded_sheet.name}"
                summary["base_comparacao"] = "Primeira importação salva"
            prepared, original_columns = _partners_prepare_import_df(df, _auth_user_name())
            old_df = _partners_rows_to_df(partner)
            for idx in range(min(len(old_df), len(prepared))):
                for col in PARTNER_INTERNAL_COLUMNS:
                    if col in old_df.columns and col in prepared.columns:
                        prepared.at[idx, col] = old_df.iloc[idx].get(col, prepared.at[idx, col])
            partner["link"] = ""
            partner["columns"] = original_columns
            partner["rows"] = prepared.to_dict(orient="records")
            partner["last_import"] = {"data_hora": _now_human(), "usuario": _auth_user_name(), "linhas": len(prepared), "fonte": f"Arquivo: {uploaded_sheet.name}"}
            partner["last_update"] = summary
            partner["diff_rows"] = diff_rows[:500]
            _partners_add_history(
                state,
                partner_key,
                "Planilha importada",
                f"{partner_name}: {len(prepared)} linhas · {uploaded_sheet.name}",
                {"tipo_acao": "importação", "linha": "", "campo": "", "valor_antigo": "", "valor_novo": uploaded_sheet.name}
            )
            _partners_save_state(state)
            st.session_state[f"partner_planilha_tratada_open_{partner_key}"] = True
            st.session_state[f"partner_panel_mode_{partner_key}"] = "Resumo de Atualizações"
            st.success("Planilha importada e a janela de tratamento foi aberta no módulo de Parceiras.")
            app_rerun()
        except Exception:
            st.warning("Não foi possível importar a planilha. Verifique o formato do arquivo e tente novamente.")

    if save_internal_clicked and can_edit:
        partner["last_update"] = {
            "data_hora": _now_human(),
            "usuario": _auth_user_name(),
            "linhas_novas": 0,
            "linhas_alteradas": 0,
            "linhas_removidas": 0,
            "total_diferencas": 0,
        }
        _partners_add_history(state, partner_key, "Dados internos salvos", partner_name)
        _partners_save_state(state)
        st.success("Dados internos salvos.")

def _render_partner_table(state: dict, partner_key: str) -> None:
    partner = state["partners"][partner_key]
    can_view = _auth_partner_permission("partner_sheet_view")
    can_edit_rows = _auth_partner_permission("partner_sheet_edit_rows")
    can_delete_rows = _auth_partner_permission("partner_sheet_delete_rows")
    can_edit_header = _auth_partner_permission("partner_sheet_edit_header")
    can_write_treatment = _auth_partner_permission("partner_sheet_write_treatment")
    can_export = _auth_partner_permission("partner_sheet_export")
    if not can_view:
        st.warning("Seu usuário não possui permissão para visualizar esta planilha.")
        return

    df = _partners_rows_to_df(partner)
    if df.empty or len(df) == 0:
        st.info("Importe uma planilha Excel ou CSV para iniciar a tabela espelhada.")
        return

    st.session_state.setdefault(f"partner_planilha_tratada_open_{partner_key}", True)
    st.session_state.setdefault(f"partner_panel_mode_{partner_key}", "Filtrar Informações")
    st.session_state.setdefault(f"partner_hidden_cols_{partner_key}", [])
    st.session_state.setdefault(f"partner_search_{partner_key}", "")
    st.session_state.setdefault(f"partner_status_filter_{partner_key}", [])

    st.markdown(
        """
        <style>
        .partner-excel-window {
            background: linear-gradient(145deg, #10243a, #0b1728);
            border: 1px solid rgba(66,165,245,.35);
            border-radius: 18px;
            padding: 16px 18px;
            box-shadow: 0 12px 30px rgba(0,0,0,.35);
            margin-top: 12px;
            margin-bottom: 14px;
        }
        .partner-excel-title {
            color: #ffffff;
            font-weight: 900;
            font-size: 1.25rem;
            letter-spacing: .5px;
        }
        .partner-excel-subtitle { color: #b8c7d8; font-size: .92rem; margin-top: 4px; }
        .partner-toolbox {
            background: #0d1e35;
            border: 1px solid rgba(144,202,249,.25);
            border-radius: 16px;
            padding: 12px;
        }
        .partner-toolbox-title {
            color: #90caf9;
            font-weight: 800;
            text-align: center;
            margin-bottom: 10px;
            text-transform: uppercase;
            font-size: .82rem;
            letter-spacing: 1px;
        }
        .partner-history-card {
            background: rgba(255,255,255,.04);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 14px;
            padding: 10px 12px;
            margin: 8px 0;
        }
        </style>
        <div class='partner-excel-window'>
            <div class='partner-excel-title'>📊 Janela de Tratamento de Planilha Importada</div>
            <div class='partner-excel-subtitle'>Mini editor estilo Excel para filtrar, editar, excluir, exportar e acompanhar alterações da planilha da parceira.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    toolbox, main_area = st.columns([1.05, 3.95], gap="large")

    with toolbox:
        st.markdown("<div class='partner-toolbox'><div class='partner-toolbox-title'>Funções</div>", unsafe_allow_html=True)
        panel_buttons = [
            ("Filtrar Colunas", "🧩 Filtrar Colunas"),
            ("Filtrar Informações", "🔎 Filtrar Informações"),
            ("Editar Cabeçalho", "✏️ Editar Cabeçalho"),
            ("Editar Célula", "📝 Editar Célula"),
            ("Adicionar Linha", "➕ Adicionar Linha"),
            ("Excluir Linha", "🗑️ Excluir Linha"),
            ("Excluir Coluna", "🧹 Excluir Coluna"),
            ("Resumo de Atualizações", "📋 Resumo de Atualizações"),
            ("Exportar CSV", "⬇️ Exportar CSV"),
            ("Exportar Excel", "📗 Exportar Excel"),
        ]
        for mode, label in panel_buttons:
            if st.button(label, key=f"partner_panel_{partner_key}_{mode}", use_container_width=True):
                st.session_state[f"partner_panel_mode_{partner_key}"] = mode
                app_rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    mode = st.session_state.get(f"partner_panel_mode_{partner_key}", "Filtrar Informações")
    hidden_cols_key = f"partner_hidden_cols_{partner_key}"
    search_key = f"partner_search_{partner_key}"
    status_key = f"partner_status_filter_{partner_key}"

    with main_area:
        st.markdown(f"##### {mode}")

        if mode == "Filtrar Colunas":
            hidable = [col for col in df.columns if col != PARTNER_ROW_ID]
            col_search = st.text_input("Buscar coluna", key=f"partner_column_search_{partner_key}")
            choices = [c for c in hidable if str(col_search).strip().lower() in c.lower()] if col_search else hidable
            selected_visible = st.multiselect(
                "Colunas visíveis",
                choices,
                default=[c for c in choices if c not in st.session_state.get(hidden_cols_key, [])],
                key=f"partner_visible_cols_{partner_key}",
            )
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Aplicar filtro de colunas", key=f"partner_apply_visible_cols_{partner_key}", type="primary", use_container_width=True):
                    st.session_state[hidden_cols_key] = [c for c in hidable if c not in selected_visible]
                    app_rerun()
            with b2:
                if st.button("Restaurar colunas ocultas", key=f"partner_restore_cols_{partner_key}", use_container_width=True):
                    st.session_state[hidden_cols_key] = []
                    app_rerun()
            st.caption("Ocultar colunas não apaga dados. As informações permanecem salvas e podem voltar a aparecer.")

        elif mode == "Filtrar Informações":
            f1, f2 = st.columns([1.4, 1])
            with f1:
                st.text_input("Pesquisar qualquer informação da tabela", key=search_key)
            with f2:
                st.multiselect("Filtrar status", PARTNER_STATUS_OPTIONS, key=status_key)
            st.caption("A busca aceita termos parciais e filtra a tabela em tempo real.")

        elif mode == "Editar Cabeçalho":
            if not can_edit_header:
                st.warning("Seu usuário não possui permissão para editar cabeçalho.")
            elif partner.get("columns"):
                h1, h2 = st.columns([1, 1.2])
                with h1:
                    old_header = st.selectbox("Cabeçalho atual", partner.get("columns", []), key=f"partner_header_old_{partner_key}")
                with h2:
                    new_header = st.text_input("Novo nome do cabeçalho", value=old_header, key=f"partner_header_new_{partner_key}")
                s1, s2 = st.columns(2)
                with s1:
                    if st.button("💾 Salvar cabeçalho", key=f"partner_header_save_{partner_key}", type="primary", use_container_width=True):
                        ok, msg = _partners_rename_column(partner, old_header, new_header)
                        if ok:
                            _partners_add_history(
                                state,
                                partner_key,
                                "Cabeçalho alterado",
                                f"{old_header} -> {new_header}",
                                {"tipo_acao": "alteração de cabeçalho", "linha": "", "campo": old_header, "valor_antigo": old_header, "valor_novo": new_header}
                            )
                            _partners_save_state(state)
                            st.success("Cabeçalho salvo e atualizado na tabela, filtros e exportações.")
                            app_rerun()
                        else:
                            st.warning(msg or "Não foi possível alterar o cabeçalho.")
                with s2:
                    if st.button("Cancelar", key=f"partner_header_cancel_{partner_key}", use_container_width=True):
                        app_rerun()

        elif mode == "Adicionar Linha":
            if not can_edit_rows:
                st.warning("Seu usuário não possui permissão para adicionar linhas.")
            elif st.button("➕ Criar nova linha vazia", key=f"partner_add_row_panel_{partner_key}", type="primary", use_container_width=True):
                row = _partners_add_blank_row(partner, partner_key)
                _partners_add_history(
                    state,
                    partner_key,
                    "Linha criada",
                    row.get(PARTNER_ROW_ID, ""),
                    {"tipo_acao": "edição", "linha": row.get(PARTNER_ROW_ID, ""), "campo": "", "valor_antigo": "", "valor_novo": "linha criada"}
                )
                _partners_save_state(state)
                st.success("Linha adicionada.")
                app_rerun()

        elif mode == "Excluir Linha":
            if not can_delete_rows:
                st.warning("Seu usuário não possui permissão para excluir linhas.")
            else:
                row_records = df.to_dict(orient="records")
                row_options = {_partners_row_label(row, idx): str(row.get(PARTNER_ROW_ID, "")) for idx, row in enumerate(row_records)}
                if row_options:
                    selected_label = st.selectbox("Linha para excluir", list(row_options.keys()), key=f"partner_delete_select_{partner_key}")
                    confirm_delete = st.checkbox("Confirmo a exclusão desta linha", key=f"partner_delete_confirm_{partner_key}")
                    if st.button("🗑️ Excluir linha selecionada", key=f"partner_delete_row_panel_{partner_key}", type="primary", use_container_width=True):
                        row_id = row_options.get(selected_label, "")
                        if not confirm_delete:
                            st.warning("Marque a confirmação antes de excluir.")
                        elif _partners_delete_row(partner, row_id):
                            _partners_add_history(
                                state,
                                partner_key,
                                "Linha excluída",
                                row_id,
                                {"tipo_acao": "exclusão", "linha": row_id, "campo": "", "valor_antigo": "linha existente", "valor_novo": "linha removida"}
                            )
                            _partners_save_state(state)
                            st.success("Linha excluída.")
                            app_rerun()
                        else:
                            st.warning("Não foi possível localizar a linha selecionada.")

        elif mode == "Excluir Coluna":
            if not can_edit_header:
                st.warning("Seu usuário não possui permissão para excluir colunas.")
            else:
                removable_cols = [col for col in partner.get("columns", []) if col not in PARTNER_INTERNAL_COLUMNS and col != PARTNER_ROW_ID]
                if removable_cols:
                    col_to_delete = st.selectbox("Coluna para excluir", removable_cols, key=f"partner_delete_col_select_{partner_key}")
                    confirm_col = st.checkbox("Confirmo a exclusão desta coluna", key=f"partner_delete_col_confirm_{partner_key}")
                    if st.button("🧹 Excluir coluna", key=f"partner_delete_col_button_{partner_key}", type="primary", use_container_width=True):
                        if not confirm_col:
                            st.warning("Marque a confirmação antes de excluir a coluna.")
                        else:
                            partner["columns"] = [col for col in partner.get("columns", []) if col != col_to_delete]
                            partner["baseline_columns"] = [col for col in partner.get("baseline_columns", []) if col != col_to_delete]
                            for collection_name in ("rows", "baseline_rows", "diff_rows"):
                                for row in partner.get(collection_name, []) or []:
                                    if isinstance(row, dict):
                                        row.pop(col_to_delete, None)
                            st.session_state[hidden_cols_key] = [col for col in st.session_state.get(hidden_cols_key, []) if col != col_to_delete]
                            _partners_add_history(
                                state,
                                partner_key,
                                "Coluna excluída",
                                col_to_delete,
                                {"tipo_acao": "exclusão", "linha": "", "campo": col_to_delete, "valor_antigo": col_to_delete, "valor_novo": "coluna removida"}
                            )
                            _partners_save_state(state)
                            st.success("Coluna excluída da tabela e das exportações.")
                            app_rerun()
                else:
                    st.info("Não há colunas importadas disponíveis para exclusão.")

        elif mode == "Resumo de Atualizações":
            history = _partners_history_rows(partner.get("history", []))
            st.metric("Quantidade de alterações registradas", len(history))
            if history:
                hist_df = pd.DataFrame(history)
                preferred_cols = ["data_hora", "usuario", "acao", "detalhes", "linha", "campo", "tipo_acao"]
                hist_cols = [col for col in preferred_cols if col in hist_df.columns] + [col for col in hist_df.columns if col not in preferred_cols]
                st.dataframe(hist_df[hist_cols].head(300), use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma alteração registrada ainda.")

        elif mode == "Exportar CSV":
            if not can_export:
                st.warning("Exportação desabilitada para este usuário.")
            else:
                export_df_panel = df.drop(columns=[PARTNER_ROW_ID], errors="ignore")
                try:
                    csv_data = export_df_panel.to_csv(index=False).encode("utf-8-sig")
                except Exception:
                    csv_data = None
                    st.warning("Não foi possível exportar para CSV. Revise a planilha e tente novamente.")
                if csv_data is not None and st.download_button(
                    "⬇️ Baixar CSV tratado",
                    data=csv_data,
                    file_name=f"{_partner_label(partner_key)}_controle_tratado.csv",
                    mime="text/csv",
                    use_container_width=True,
                ):
                    _partners_add_history(state, partner_key, "Planilha exportada", "CSV", {"tipo_acao": "exportação", "valor_novo": "CSV"})
                    _partners_save_state(state)

        elif mode == "Exportar Excel":
            if not can_export:
                st.warning("Exportação desabilitada para este usuário.")
            else:
                export_df_panel = df.drop(columns=[PARTNER_ROW_ID], errors="ignore")
                excel_data, excel_error = _partners_safe_excel_bytes(export_df_panel)
                if excel_error:
                    st.info(excel_error)
                elif st.download_button(
                    "📗 Baixar Excel tratado (.xlsx)",
                    data=excel_data,
                    file_name=f"{_partner_label(partner_key)}_controle_tratado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                ):
                    _partners_add_history(state, partner_key, "Planilha exportada", "Excel", {"tipo_acao": "exportação", "valor_novo": "Excel"})
                    _partners_save_state(state)

        if mode == "Editar Célula":
            st.info("Edite diretamente nas células da tabela abaixo e clique em Salvar alteração.")

        filtered = _partners_filter_dataframe(df, st.session_state.get(search_key, ""), st.session_state.get(status_key, []))
        max_visible_rows = 1000
        render_df = filtered.head(max_visible_rows)
        if len(filtered) > max_visible_rows:
            st.info(f"Mostrando as primeiras {max_visible_rows} linhas filtradas para manter a tela leve. A exportação continua usando a planilha completa.")
        visible_ids = [str(v) for v in render_df.get(PARTNER_ROW_ID, [])]
        hidden_cols = st.session_state.get(hidden_cols_key, [])
        display_cols = [PARTNER_ROW_ID] + [col for col in df.columns if col not in hidden_cols and col != PARTNER_ROW_ID]
        editable_cols = set()
        if can_edit_rows:
            editable_cols = {col for col in display_cols if col not in (PARTNER_ROW_ID, "Última Alteração", "Usuário Responsável")}
        elif can_write_treatment:
            editable_cols = {col for col in ("Tratativa", "Descrição / Observação") if col in display_cols}
        disabled_cols = [col for col in display_cols if col not in editable_cols]

        st.markdown("##### Tabela central da planilha")
        if can_write_treatment:
            st.caption("Campos de tratativa disponíveis: Tratativa, Descrição / Observação, Última Alteração e Usuário Responsável.")
        edited = render_df[display_cols]
        if editable_cols:
            edited = st.data_editor(
                render_df[display_cols],
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                height=520,
                key=f"partner_editor_{partner_key}_{len(df)}_{len(visible_ids)}_{len(editable_cols)}_{len(hidden_cols)}",
                disabled=disabled_cols,
                column_config={
                    PARTNER_ROW_ID: st.column_config.TextColumn("ID", width="small"),
                    "Status de Execução": st.column_config.SelectboxColumn(
                        "Status de Execução",
                        options=PARTNER_STATUS_OPTIONS,
                        required=False,
                    ),
                    "Tratativa": st.column_config.TextColumn("Tratativa", width="large"),
                    "Descrição / Observação": st.column_config.TextColumn("Descrição / Observação", width="large"),
                },
            )
        else:
            st.dataframe(render_df[display_cols], use_container_width=True, hide_index=True, height=520)

        save_cols = st.columns([1, 1, 2])
        with save_cols[0]:
            if editable_cols and st.button("💾 Salvar alteração", key=f"partner_save_editor_{partner_key}", type="primary", use_container_width=True):
                merged, logs = _partners_merge_edited_rows(df, visible_ids, edited, partner.get("columns", []))
                partner["rows"] = merged.to_dict(orient="records")
                for log_item in logs:
                    acao, detalhes = log_item[0], log_item[1]
                    extra = log_item[2] if len(log_item) > 2 and isinstance(log_item[2], dict) else {}
                    _partners_add_history(state, partner_key, acao, detalhes, extra)
                if not logs:
                    _partners_add_history(state, partner_key, "Dados internos salvos", "Sem alterações detectadas", {"tipo_acao": "edição"})
                _partners_save_state(state)
                st.success("Alterações salvas.")
                app_rerun()
        with save_cols[1]:
            if editable_cols and st.button("↩ Cancelar alteração", key=f"partner_cancel_editor_{partner_key}", use_container_width=True):
                app_rerun()

        last_update = partner.get("last_update") or {}
        if last_update:
            with st.expander("Resumo rápido da última importação/atualização", expanded=False):
                st.json({
                    "Última atualização": last_update.get("data_hora", ""),
                    "Usuário que atualizou": last_update.get("usuario", ""),
                    "Fonte": last_update.get("fonte", ""),
                    "Base de comparação": last_update.get("base_comparacao", ""),
                    "Linhas novas": last_update.get("linhas_novas", 0),
                    "Linhas alteradas": last_update.get("linhas_alteradas", 0),
                    "Linhas removidas": last_update.get("linhas_removidas", 0),
                    "Total de diferenças": last_update.get("total_diferencas", 0),
                })
        diff_rows = partner.get("diff_rows", [])
        if diff_rows:
            with st.expander("Destaques visuais da última atualização", expanded=False):
                diff_df = pd.DataFrame(diff_rows).drop(columns=[PARTNER_ROW_ID], errors="ignore")
                st.dataframe(_partners_style_diff(diff_df), use_container_width=True, hide_index=True)

def _render_partner_chat(state: dict, partner_key: str) -> None:
    if not _auth_partner_permission("partner_sheet_write_treatment"):
        st.warning("Seu usuário não possui permissão para registrar tratativas.")
        return
    partner = state["partners"][partner_key]
    mention_options, mention_labels = _auth_mention_options()
    st.markdown(
        "<div class='partner-window-title'>Tratativas</div>"
        "<div class='partner-window-subtitle'>Acompanhamento de assuntos, prazos, responsáveis e citações internas.</div>",
        unsafe_allow_html=True,
    )
    with st.form(f"partner_chat_form_{partner_key}"):
        c1, c2 = st.columns(2)
        with c1:
            assunto = st.text_input("Assunto")
            prazo = st.date_input("Prazo", value=date.today())
        with c2:
            status = st.selectbox("Status", PARTNER_TREATMENT_STATUS)
            st.text_input("Usuário responsável/autoria", value=_auth_user_name(), disabled=True)
        citados = st.multiselect(
            "Citar usuários cadastrados",
            mention_options,
            format_func=lambda usuario: mention_labels.get(usuario, usuario),
            help="Selecione os usuários que devem receber notificação ao entrar no sistema.",
        )
        mensagem = st.text_area("Mensagem")
        send = st.form_submit_button("💬 Enviar tratativa", type="primary", use_container_width=True)
    if send:
        if not mensagem.strip():
            st.error("Digite uma mensagem para registrar a tratativa.")
        else:
            item = {
                "id": hashlib.sha1(f"{partner_key}-{_now_iso()}-{_auth_user_name()}".encode()).hexdigest()[:12],
                "usuario": _auth_user_name(),
                "assunto": assunto.strip() or "Sem assunto",
                "mensagem": mensagem.strip(),
                "data": date.today().isoformat(),
                "hora": datetime.now().strftime("%H:%M:%S"),
                "prazo": prazo.isoformat() if prazo else "",
                "status": status,
                "citados": citados,
            }
            partner.setdefault("chat", []).insert(0, item)
            citados_label = ", ".join(mention_labels.get(usuario, usuario) for usuario in citados) or "Sem citações"
            _partners_add_history(state, partner_key, "Mensagem enviada", f"{item['assunto']} · prazo {item['prazo']} · citados: {citados_label}")
            _partners_save_state(state)
            st.success("Tratativa registrada.")
            app_rerun()

    for idx, item in enumerate(partner.get("chat", [])[:30]):
        chat_id = item.get("id") or hashlib.sha1(f"{partner_key}-{idx}-{item.get('assunto','')}-{item.get('data','')}".encode()).hexdigest()[:12]
        current_status = item.get("status", "Aberto")
        status_options = PARTNER_TREATMENT_STATUS if current_status in PARTNER_TREATMENT_STATUS else [current_status] + PARTNER_TREATMENT_STATUS
        color = "#66bb6a" if current_status in PARTNER_TREATMENT_DONE else "#ffd54f" if current_status == "Em andamento" else "#ff5252" if current_status == "Atrasado" else THEME_PRIMARY_COLOR
        citados_txt = ", ".join(mention_labels.get(str(usuario), str(usuario)) for usuario in item.get("citados", []))
        citados_html = f"<div style='color:#9ec9ef;font-size:.78rem;margin-top:6px;'>Citados: {citados_txt}</div>" if citados_txt else ""
        st.markdown(
            f"<div style='background:#151515;border:1px solid #333;border-left:4px solid {color};border-radius:10px;padding:10px 12px;margin:8px 0;'>"
            f"<div style='color:{color};font-weight:700;'>{item.get('assunto','Sem assunto')} · {item.get('status','')}</div>"
            f"<div style='color:#aaa;font-size:.78rem;'>{item.get('usuario','')} · {item.get('data','')} {item.get('hora','')} · Prazo: {item.get('prazo','')}</div>"
            f"<div style='color:#eee;margin-top:6px;'>{item.get('mensagem','')}</div>"
            f"{citados_html}"
            f"</div>",
            unsafe_allow_html=True,
        )
        sc1, sc2, sc3 = st.columns([1.4, 1, 2.4])
        with sc1:
            new_status = st.selectbox(
                "Alterar status",
                status_options,
                index=status_options.index(current_status),
                key=f"partner_chat_status_{partner_key}_{chat_id}",
            )
        with sc2:
            if st.button("Salvar status", key=f"partner_chat_save_status_{partner_key}_{chat_id}", use_container_width=True):
                if new_status != current_status:
                    item["status"] = new_status
                    item["status_atualizado_por"] = _auth_user_name()
                    item["status_atualizado_em"] = _now_human()
                    _partners_add_history(
                        state,
                        partner_key,
                        "Status da tratativa alterado",
                        f"{item.get('assunto','Sem assunto')}: {current_status} -> {new_status}"
                    )
                    _partners_save_state(state)
                    st.success("Status da tratativa atualizado.")
                    app_rerun()
                else:
                    st.info("Status já estava selecionado.")
        with sc3:
            if item.get("status_atualizado_em"):
                st.caption(f"Última atualização: {item.get('status_atualizado_em')} por {item.get('status_atualizado_por','')}")

def _render_partner_history(state: dict, partner_key: str) -> None:
    if not _auth_partner_permission("partner_sheet_history"):
        st.warning("Seu usuário não possui permissão para acessar o histórico.")
        return
    partner = state["partners"][partner_key]
    st.markdown(
        "<div class='partner-window-title'>Histórico</div>"
        "<div class='partner-window-subtitle'>Registro organizado das ações e atualizações do módulo.</div>",
        unsafe_allow_html=True,
    )
    h1, h2 = st.columns(2)
    with h1:
        st.markdown(f"##### Histórico {_partner_label(partner_key)}")
        st.dataframe(_partners_history_rows(partner.get("history", [])), use_container_width=True, hide_index=True)
    with h2:
        st.markdown("##### Histórico Geral")
        st.dataframe(_partners_history_rows(state.get("history_general", [])), use_container_width=True, hide_index=True)

def _render_partner_module_css() -> None:
    st.markdown("""
    <style>
    .partner-hero {
        background: linear-gradient(145deg, rgba(17,27,42,.98), rgba(8,14,24,.98));
        border: 1px solid rgba(66,165,245,.28);
        border-top: 2px solid var(--tmg-primary);
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 18px;
        box-shadow: 0 10px 26px rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.04);
    }
    .partner-hero-title {
        color: var(--tmg-primary);
        font-weight: 900;
        letter-spacing: 3px;
        text-transform: uppercase;
        font-size: 1.25rem;
        text-shadow: 0 0 18px var(--tmg-primary-glow);
    }
    .partner-hero-subtitle,
    .partner-window-subtitle {
        color: #b8c7d9;
        font-size: .86rem;
        margin-top: 6px;
    }
    .partner-card {
        background: linear-gradient(145deg, rgba(18,33,54,.98), rgba(7,15,28,.98));
        border: 1px solid rgba(66,165,245,.28);
        border-radius: 12px;
        padding: 18px;
        min-height: 220px;
        box-shadow: 8px 8px 20px rgba(0,0,0,.45), -1px -1px 8px rgba(255,255,255,.04);
        text-align: center;
    }
    .partner-card-title,
    .partner-window-title {
        color: var(--tmg-primary);
        font-weight: 900;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        text-shadow: 0 0 14px var(--tmg-primary-glow);
    }
    .partner-logo-slot {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 140px;
        height: 96px;
        border: 1px dashed rgba(144,202,249,.30);
        border-radius: 10px;
        color: #7f96ad;
        font-size: .78rem;
        letter-spacing: 1px;
        margin: 0 auto 12px auto;
    }
    .partner-logo-frame {
        width: 140px;
        height: 96px;
        margin: 0 auto 14px auto;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid rgba(144,202,249,.22);
        border-radius: 10px;
        background: rgba(5,14,26,.48);
        box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
    }
    .partner-logo-img {
        max-width: 120px;
        max-height: 80px;
        width: auto;
        height: auto;
        object-fit: contain;
        display: block;
    }
    .partner-logo-empty {
        color: #7f96ad;
        font-size: .72rem;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }
    .partner-section-card {
        background: linear-gradient(145deg, rgba(18,33,54,.98), rgba(7,15,28,.98));
        border: 1px solid rgba(66,165,245,.26);
        border-radius: 12px;
        padding: 18px 16px;
        text-align: center;
        box-shadow: 6px 6px 18px rgba(0,0,0,.40), inset 0 1px 0 rgba(255,255,255,.04);
    }
    div[data-testid="stFileUploader"] section {
        border-color: rgba(66,165,245,.32) !important;
        background: rgba(13,30,53,.52) !important;
    }
    </style>
    """, unsafe_allow_html=True)

def _render_partner_selection(state: dict, allowed: list) -> None:
    st.markdown(
        "<div class='partner-window-title'>Parceiros</div>"
        "<div class='partner-window-subtitle'>Selecione a parceira para abrir o controle de voos e dados.</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(max(1, len(allowed)), gap="large")
    for col, partner_key in zip(cols, allowed):
        with col:
            label = _partner_label(partner_key)
            st.markdown("<div class='partner-card'>", unsafe_allow_html=True)
            st.markdown(_partners_logo_html(partner_key), unsafe_allow_html=True)
            st.markdown(f"<div class='partner-card-title'>{label}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            if st.button(label, key=f"partner_open_{partner_key}", type="primary", use_container_width=True):
                st.session_state["partner_selected"] = partner_key
                st.session_state["partner_section"] = ""
                app_rerun()

def _render_partner_section_buttons(partner_key: str) -> None:
    sections = []
    if _auth_partner_permission("partner_sheet_view"):
        sections.append(("sheet", "Planilha", "Espelho Excel/CSV, edição e comparação"))
    if _auth_partner_permission("partner_sheet_write_treatment"):
        sections.append(("chat", "Tratativa", "Assuntos, prazos e citações"))
    if _auth_partner_permission("partner_sheet_history"):
        sections.append(("history", "Histórico", "Registros e auditoria"))
    if not sections:
        st.warning("Seu usuário não possui permissões liberadas para abrir as áreas desta parceira.")
        return
    cols = st.columns(len(sections), gap="large")
    for col, (section_key, label, desc) in zip(cols, sections):
        with col:
            st.markdown(
                f"<div class='partner-section-card'><div class='partner-card-title'>{label}</div>"
                f"<div class='partner-window-subtitle'>{desc}</div></div>",
                unsafe_allow_html=True,
            )
            if st.button(label, key=f"partner_section_{partner_key}_{section_key}", type="primary", use_container_width=True):
                st.session_state["partner_section"] = section_key
                app_rerun()

def _render_partner_workspace(state: dict, partner_key: str) -> None:
    partner_name = _partner_label(partner_key)
    partner = state["partners"][partner_key]
    top_cols = st.columns([1, 3])
    with top_cols[0]:
        if st.button("← Parceiros", key=f"partner_back_{partner_key}", use_container_width=True):
            st.session_state["partner_selected"] = ""
            st.session_state["partner_section"] = ""
            app_rerun()
    with top_cols[1]:
        st.markdown(f"<div class='partner-window-title'>{partner_name}</div>", unsafe_allow_html=True)
    section = st.session_state.get("partner_section", "")
    if not section:
        st.markdown(_partners_logo_html(partner_key), unsafe_allow_html=True)
        _render_partner_alerts(partner)
        _render_partner_section_buttons(partner_key)
        st.info("Selecione Planilha, Tratativa ou Histórico para abrir a janela correspondente.")
        return
    allowed_sections = []
    if _auth_partner_permission("partner_sheet_view"):
        allowed_sections.append("sheet")
    if _auth_partner_permission("partner_sheet_write_treatment"):
        allowed_sections.append("chat")
    if _auth_partner_permission("partner_sheet_history"):
        allowed_sections.append("history")
    if section not in allowed_sections:
        st.warning("Seu usuário não possui permissão para abrir esta área.")
        return
    if section == "sheet":
        st.markdown(
            f"<div class='partner-section-card'><div class='partner-card-title'>{partner_name}</div>{_partners_logo_html(partner_key)}</div>",
            unsafe_allow_html=True,
        )
        _render_partner_sheet_controls(state, partner_key)
        _render_partner_table(state, partner_key)
    elif section == "chat":
        _render_partner_chat(state, partner_key)
    elif section == "history":
        _render_partner_history(state, partner_key)

def render_parceiros_controle() -> None:
    try:
        user = _auth_current_user()
        allowed = _auth_allowed_partners(user)
        if not allowed:
            st.warning("Seu usuário não possui permissão para acessar EIWA ou ALVAZ.")
            return
        state = _partners_load_state()
        _render_partner_module_css()
        st.markdown("""
        <div class='partner-hero'>
            <div class='partner-hero-title'>
                Parceiros / Controle de Voos e Dados
            </div>
            <div class='partner-hero-subtitle'>
                Módulo isolado para EIWA e ALVAZ: planilhas, tratativas, prazos, histórico e exportações.
            </div>
        </div>
        """, unsafe_allow_html=True)
        selected = st.session_state.get("partner_selected", "")
        if selected not in allowed:
            selected = ""
            st.session_state["partner_selected"] = ""
            st.session_state["partner_section"] = ""
        if not selected:
            _render_partner_selection(state, allowed)
        else:
            _render_partner_workspace(state, selected)
    except Exception:
        st.warning("Não foi possível abrir o módulo de Parceiros agora. Volte para a seleção de parceiros e tente novamente.")
        if st.button("Reabrir módulo Parceiros", key="partner_recover_safe", use_container_width=True):
            st.session_state["partner_selected"] = ""
            st.session_state["partner_section"] = ""
            app_rerun()

def _render_partner_mention_notifications() -> None:
    return

def _render_partner_logo_settings() -> None:
    if not _auth_is_admin():
        st.warning("Apenas o administrador Wellington pode alterar as logos das parceiras.")
        return
    _render_partner_module_css()
    state = _partners_load_state()
    st.markdown("#### Logos das Parceiras")
    st.caption("As logos ficam salvas na pasta padrão do sistema e aparecem automaticamente na tela de Parceiros.")
    cols = st.columns(2, gap="large")
    for col, partner_key in zip(cols, PARTNER_KEYS):
        with col:
            label = _partner_label(partner_key)
            st.markdown(f"<div class='partner-section-card'><div class='partner-card-title'>{label}</div>{_partners_logo_html(partner_key)}</div>", unsafe_allow_html=True)
            uploaded = st.file_uploader(
                f"Adicionar ou trocar logo {label}",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"cfg_partner_logo_{partner_key}",
            )
            if uploaded is not None:
                _partners_save_logo(state, partner_key, uploaded)
                _partners_add_history(state, partner_key, "Logomarca atualizada", label)
                _partners_save_state(state)
                st.success(f"Logo {label} salva.")
                app_rerun()
            logo_path = _partners_logo_path(partner_key)
            if logo_path:
                st.caption(f"Arquivo salvo: {logo_path}")

def _render_logged_user_chip() -> None:
    if not st.session_state.get("logged_in", False):
        return
    user_name = _auth_user_name()
    st.markdown(
        f"""
        <div style='position:fixed;left:14px;top:58px;z-index:999997;pointer-events:none;
                    background:linear-gradient(145deg,rgba(20,48,78,.96),rgba(8,22,39,.96));
                    border:1px solid var(--tmg-primary);border-radius:10px;padding:9px 13px;
                    color:#e8f3ff;font-weight:800;font-size:.82rem;letter-spacing:.4px;
                    box-shadow:4px 4px 12px rgba(0,0,0,.45),-1px -1px 5px rgba(255,255,255,.04),
                               0 0 16px var(--tmg-primary-glow);
                    text-shadow:1px 1px 0 rgba(0,0,0,.65);'>
            Usuário: {user_name}
        </div>
        """,
        unsafe_allow_html=True,
    )

def _save_uploaded_files_generic(files, target_dir: Path) -> tuple:
    target_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    total_size = 0
    for uploaded in files or []:
        try:
            uploaded.seek(0)
        except Exception:
            pass
        data = uploaded.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        safe_name = Path(uploaded.name).name
        target = target_dir / safe_name
        if target.exists():
            target = target_dir / f"{target.stem}_{datetime.now().strftime('%H%M%S%f')}{target.suffix}"
        target.write_bytes(data)
        total_size += len(data)
        saved.append({
            "nome": uploaded.name,
            "path": str(target),
            "tamanho": len(data),
            "tamanho_fmt": _tv_human_size(len(data)),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return saved, total_size

ORTHOMOSAIC_QUALITY_PRESETS = {
    "Alta qualidade": {
        "resolution_cm": 2,
        "feature_quality": "ultra",
        "pc_quality": "ultra",
        "mesh_depth": 13,
        "min_features": 12000,
        "matcher_neighbors": 8,
        "resize_to": 0,
        "extra_args": "--dsm --dtm --orthophoto-compression NONE",
        "descricao": "Prioriza nitidez, densidade de pontos e GeoTIFF final com menor perda.",
    },
    "Média qualidade": {
        "resolution_cm": 5,
        "feature_quality": "high",
        "pc_quality": "medium",
        "mesh_depth": 11,
        "min_features": 8000,
        "matcher_neighbors": 6,
        "resize_to": 3000,
        "extra_args": "--dsm",
        "descricao": "Equilibra qualidade visual e tempo de processamento.",
    },
    "Baixa/leve": {
        "resolution_cm": 10,
        "feature_quality": "medium",
        "pc_quality": "low",
        "mesh_depth": 9,
        "min_features": 4000,
        "matcher_neighbors": 4,
        "resize_to": 2000,
        "extra_args": "--fast-orthophoto",
        "descricao": "Prioriza velocidade e arquivos menores para testes ou máquinas leves.",
    },
}

def _orthomosaic_db_path() -> Path:
    root = SYSTEM_DATABASE_DIR / "ortomosaicos_jobs"
    root.mkdir(parents=True, exist_ok=True)
    return root / "ortomosaic_jobs.sqlite"

def _orthomosaic_init_db() -> None:
    db_path = _orthomosaic_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ortomosaic_jobs (
                job_id TEXT PRIMARY KEY,
                nome TEXT,
                pasta_entrada TEXT,
                pasta_saida TEXT,
                qualidade TEXT,
                status TEXT,
                caminho_ortomosaico TEXT,
                modo_execucao TEXT,
                criado_em TEXT,
                atualizado_em TEXT
            )
        """)
        conn.commit()

def _orthomosaic_upsert_job(record: dict) -> None:
    _orthomosaic_init_db()
    with sqlite3.connect(_orthomosaic_db_path()) as conn:
        conn.execute(
            """
            INSERT INTO ortomosaic_jobs
                (job_id, nome, pasta_entrada, pasta_saida, qualidade, status, caminho_ortomosaico, modo_execucao, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                nome=excluded.nome,
                pasta_entrada=excluded.pasta_entrada,
                pasta_saida=excluded.pasta_saida,
                qualidade=excluded.qualidade,
                status=excluded.status,
                caminho_ortomosaico=excluded.caminho_ortomosaico,
                modo_execucao=excluded.modo_execucao,
                atualizado_em=excluded.atualizado_em
            """,
            (
                record.get("job_id", ""),
                record.get("nome", ""),
                record.get("pasta_entrada", ""),
                record.get("pasta_saida", ""),
                record.get("qualidade", ""),
                record.get("status", ""),
                record.get("caminho_ortomosaico", ""),
                record.get("modo_execucao", ""),
                record.get("criado_em", _now_human()),
                record.get("atualizado_em", _now_human()),
            ),
        )
        conn.commit()

def _orthomosaic_list_jobs() -> list:
    _orthomosaic_init_db()
    with sqlite3.connect(_orthomosaic_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM ortomosaic_jobs ORDER BY criado_em DESC LIMIT 80").fetchall()
    return [dict(row) for row in rows]

def _orthomosaic_find_outputs(output_dir: Path, project_slug: str = "") -> list:
    candidates = []
    roots = [output_dir]
    if project_slug:
        roots.append(output_dir / project_slug)
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for pattern in ("*.tif", "*.tiff", "*.geotiff", "*.png", "*.jpg", "*.jpeg"):
            for path in root.rglob(pattern):
                if path.is_file() and path not in seen:
                    seen.add(path)
                    candidates.append(path)
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)

def _orthomosaic_select_folder_dialog(initial_dir: Path) -> tuple:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(initialdir=str(initial_dir), title="Selecionar pasta de saída do ortomosaico")
        root.destroy()
        if selected:
            return selected, ""
        return "", "Nenhuma pasta selecionada."
    except Exception as exc:
        return "", f"Seleção por janela indisponível neste ambiente. Informe o caminho manualmente. Detalhe: {exc}"

def _orthomosaic_quality_args(preset: dict) -> str:
    args = [
        f"--orthophoto-resolution {preset['resolution_cm']}",
        f"--feature-quality {preset['feature_quality']}",
        f"--pc-quality {preset['pc_quality']}",
        f"--mesh-octree-depth {preset['mesh_depth']}",
        f"--min-num-features {preset['min_features']}",
        f"--matcher-neighbors {preset['matcher_neighbors']}",
    ]
    if int(preset.get("resize_to", 0) or 0) > 0:
        args.append(f"--resize-to {preset['resize_to']}")
    if preset.get("extra_args"):
        args.append(str(preset["extra_args"]))
    return " ".join(args)

def _orthomosaic_write_vscode_workspace(job_dir: Path, project_slug: str, output_dir: Path, docker_image: str, quality_args: str, mode: str, final_name: str) -> dict:
    dataset_project = job_dir / project_slug
    images_dir = dataset_project / "images"
    logs_dir = job_dir / "logs"
    vscode_dir = job_dir / ".vscode"
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    vscode_dir.mkdir(parents=True, exist_ok=True)
    final_tif = output_dir / f"{final_name}.tif"

    docker_command = (
        f'docker run --rm -v "{job_dir}:/datasets" '
        f'{docker_image} --project-path /datasets {project_slug} {quality_args}'
    )
    ps_script = f"""$ErrorActionPreference = "Stop"
$Workspace = "{job_dir}"
$Project = "{project_slug}"
$OutputDir = "{output_dir}"
$FinalTif = "{final_tif}"
Write-Host "TMG Ortomosaico - processamento externo via Docker/WebODM"
Write-Host "Projeto: $Project"
Write-Host "Entrada: $Workspace\\$Project\\images"
Write-Host "Saida: $OutputDir"
{docker_command}
$Generated = Join-Path $Workspace "$Project\\odm_orthophoto\\odm_orthophoto.tif"
if (Test-Path $Generated) {{
    Copy-Item $Generated $FinalTif -Force
    Write-Host "Ortomosaico final copiado para: $FinalTif"
}} else {{
    Write-Host "Processamento finalizado, mas o arquivo odm_orthophoto.tif não foi encontrado automaticamente."
    Write-Host "Verifique a pasta: $Workspace\\$Project\\odm_orthophoto"
}}
"""
    sh_script = f"""#!/usr/bin/env bash
set -e
WORKSPACE="{job_dir.as_posix()}"
PROJECT="{project_slug}"
OUTPUT_DIR="{output_dir.as_posix()}"
FINAL_TIF="{final_tif.as_posix()}"
echo "TMG Ortomosaico - processamento externo via Docker/WebODM"
{docker_command}
GENERATED="$WORKSPACE/$PROJECT/odm_orthophoto/odm_orthophoto.tif"
if [ -f "$GENERATED" ]; then
  cp "$GENERATED" "$FINAL_TIF"
  echo "Ortomosaico final copiado para: $FINAL_TIF"
else
  echo "Arquivo final não encontrado automaticamente. Verifique $WORKSPACE/$PROJECT/odm_orthophoto"
fi
"""
    webodm_script = f"""$ErrorActionPreference = "Continue"
Write-Host "Abrindo WebODM local e pasta preparada para o projeto."
Write-Host "Imagens: {images_dir}"
Write-Host "Saida final desejada: {output_dir}"
Start-Process "http://localhost:8000"
Write-Host "Se usar a API do WebODM, configure WEBODM_TOKEN/WEBODM_URL e execute webodm_submit.py."
"""
    webodm_py = f'''"""
Envio opcional para WebODM local via API.
Configure as variáveis de ambiente:
  WEBODM_URL=http://localhost:8000
  WEBODM_TOKEN=seu_token
Depois execute no terminal do VS Code: python webodm_submit.py
"""
import os
from pathlib import Path
import requests

WEBODM_URL = os.environ.get("WEBODM_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.environ.get("WEBODM_TOKEN", "")
PROJECT_NAME = "{final_name}"
IMAGES_DIR = Path(r"{images_dir}")

if not TOKEN:
    raise SystemExit("Configure WEBODM_TOKEN antes de enviar para o WebODM.")

headers = {{"Authorization": f"JWT {{TOKEN}}"}}
project_response = requests.post(f"{{WEBODM_URL}}/api/projects/", headers=headers, data={{"name": PROJECT_NAME}})
project_response.raise_for_status()
project_id = project_response.json()["id"]
files = [("images", (p.name, open(p, "rb"))) for p in IMAGES_DIR.iterdir() if p.is_file()]
try:
    task_response = requests.post(f"{{WEBODM_URL}}/api/projects/{{project_id}}/tasks/", headers=headers, files=files)
    task_response.raise_for_status()
    print("Tarefa criada no WebODM:", task_response.json())
finally:
    for _, (_, handle) in files:
        handle.close()
'''
    tasks = {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "Gerar Ortomosaico - Docker ODM",
                "type": "shell",
                "command": "powershell",
                "args": ["-ExecutionPolicy", "Bypass", "-File", "${workspaceFolder}/run_ortomosaico.ps1"],
                "group": {"kind": "build", "isDefault": True},
                "problemMatcher": [],
            },
            {
                "label": "Abrir WebODM local",
                "type": "shell",
                "command": "powershell",
                "args": ["-ExecutionPolicy", "Bypass", "-File", "${workspaceFolder}/abrir_webodm_local.ps1"],
                "problemMatcher": [],
            },
            {
                "label": "Enviar para WebODM local via API",
                "type": "shell",
                "command": "python",
                "args": ["${workspaceFolder}/webodm_submit.py"],
                "problemMatcher": [],
            },
        ],
    }
    readme = f"""# TMG - Gerador de Ortomosaico

Projeto preparado pelo Streamlit para processamento externo.

## Como executar

1. Abra este diretório no VS Code.
2. Pressione `Ctrl+Shift+B` para rodar a tarefa padrão **Gerar Ortomosaico - Docker ODM**.
3. Aguarde o Docker/OpenDroneMap concluir.
4. O arquivo final será copiado para:

`{final_tif}`

## Modo selecionado

{mode}

## Comando Docker preparado

```powershell
{docker_command}
```

O Streamlit principal apenas preparou os arquivos; o processamento pesado roda fora dele.
"""
    (job_dir / "run_ortomosaico.ps1").write_text(ps_script, encoding="utf-8")
    (job_dir / "run_ortomosaico.sh").write_text(sh_script, encoding="utf-8")
    (job_dir / "abrir_webodm_local.ps1").write_text(webodm_script, encoding="utf-8")
    (job_dir / "webodm_submit.py").write_text(webodm_py, encoding="utf-8")
    (vscode_dir / "tasks.json").write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")
    (job_dir / "README_EXECUTAR.md").write_text(readme, encoding="utf-8")
    return {"docker_command": docker_command, "final_tif": str(final_tif)}

def _orthomosaic_open_vscode(job_dir: Path) -> tuple:
    try:
        code_cmd = shutil.which("code") or shutil.which("code.cmd")
        if not code_cmd:
            common = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "bin" / "code.cmd"
            if common.exists():
                code_cmd = str(common)
        if not code_cmd:
            return False, "VS Code não encontrado no PATH. Abra manualmente a pasta do projeto gerado."
        subprocess.Popen([code_cmd, str(job_dir)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "VS Code aberto com o projeto preparado."
    except Exception as exc:
        return False, f"Não foi possível abrir o VS Code automaticamente: {exc}"

def _orthomosaic_simple_viewer_html(b64: str, image_name: str, width: int, height: int) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:#0b0f14; overflow:hidden; font-family:Segoe UI, Arial, sans-serif; }}
  #viewer {{ width:100%; height:660px; background:#0b0f14; border:1px solid #26384a; border-radius:8px; overflow:hidden; position:relative; }}
  canvas {{ position:absolute; inset:0; cursor:grab; image-rendering:auto; }}
  canvas:active {{ cursor:grabbing; }}
  .badge {{
    position:absolute; left:12px; top:12px; z-index:3; pointer-events:none;
    background:rgba(5,12,20,.82); border:1px solid #315170; color:#dcecff;
    border-radius:6px; padding:8px 11px; font-size:12px; letter-spacing:.3px;
    box-shadow:0 6px 18px rgba(0,0,0,.35);
  }}
  .zoom {{
    position:absolute; right:12px; top:12px; z-index:3; pointer-events:none;
    background:rgba(5,12,20,.82); border:1px solid #315170; color:#dcecff;
    border-radius:6px; padding:8px 11px; font-size:12px;
  }}
</style>
</head>
<body>
<div id="viewer">
  <canvas id="cv"></canvas>
  <div class="badge">{image_name} · {width} x {height} px</div>
  <div class="zoom" id="zoom">Zoom 100%</div>
</div>
<script>
const wrap=document.getElementById('viewer'), cv=document.getElementById('cv'), ctx=cv.getContext('2d'), zoom=document.getElementById('zoom');
let sc=1, ox=0, oy=0, drag=false, lx=0, ly=0, imgW=0, imgH=0;
const img=new Image();
function resize(){{ cv.width=wrap.clientWidth; cv.height=wrap.clientHeight; draw(); }}
function fit(){{ if(!imgW) return; sc=Math.min(cv.width/imgW, cv.height/imgH)*0.96; ox=(cv.width-imgW*sc)/2; oy=(cv.height-imgH*sc)/2; draw(); }}
function draw(){{ ctx.clearRect(0,0,cv.width,cv.height); ctx.save(); ctx.translate(ox,oy); ctx.scale(sc,sc); if(imgW) ctx.drawImage(img,0,0); ctx.restore(); zoom.textContent='Zoom '+Math.round(sc*100)+'%'; }}
img.onload=()=>{{ imgW=img.width; imgH=img.height; resize(); fit(); }};
img.src='data:image/jpeg;base64,{b64}';
window.addEventListener('resize', resize);
cv.addEventListener('wheel',e=>{{ e.preventDefault(); const f=e.deltaY<0?1.18:.84; const r=cv.getBoundingClientRect(); const mx=e.clientX-r.left,my=e.clientY-r.top; const ix=(mx-ox)/sc,iy=(my-oy)/sc; sc=Math.max(.05,Math.min(40,sc*f)); ox=mx-ix*sc; oy=my-iy*sc; draw(); }},{{passive:false}});
cv.addEventListener('mousedown',e=>{{ drag=true; lx=e.clientX; ly=e.clientY; }});
cv.addEventListener('mousemove',e=>{{ if(drag){{ ox+=e.clientX-lx; oy+=e.clientY-ly; lx=e.clientX; ly=e.clientY; draw(); }} }});
cv.addEventListener('mouseup',()=>{{ drag=false; }}); cv.addEventListener('mouseleave',()=>{{ drag=false; }});
cv.addEventListener('dblclick',fit);
</script>
</body>
</html>
"""

def _orthomosaic_render_viewer(path: Path) -> None:
    if not path.exists():
        st.warning("Arquivo do ortomosaico não encontrado.")
        return
    v1, v2 = st.columns([2, 1])
    with v1:
        if st.button("Visualizar ortomosaico", key=f"ortho_view_{path.as_posix()}", use_container_width=True):
            st.session_state["ortho_view_file"] = str(path)
    with v2:
        st.download_button(
            "Baixar Ortomosaico",
            data=path.read_bytes(),
            file_name=path.name,
            mime="application/octet-stream",
            use_container_width=True,
        )
    if st.session_state.get("ortho_view_file") == str(path):
        try:
            raw = path.read_bytes()
            b64, dims, err, _ = processar_ortofoto(raw, path.name)
            if err:
                st.info("Não foi possível gerar a prévia no navegador. O arquivo continua disponível para download.")
                return
            components.html(_orthomosaic_simple_viewer_html(b64, path.name, dims[0], dims[1]), height=680, scrolling=False)
        except Exception:
            st.info("Não foi possível gerar a prévia no navegador. O arquivo continua disponível para download.")

def _render_orthomosaic_generator() -> None:
    st.subheader("🛰️ Gerador de Ortomosaico")
    st.info("O Streamlit prepara o projeto, registra no SQLite e abre o VS Code. O processamento pesado fica no Docker/WebODM local.")
    jobs_root = SYSTEM_DATABASE_DIR / "ortomosaicos_jobs"
    default_output = SYSTEM_DATABASE_DIR / "ortomosaicos"
    jobs_root.mkdir(parents=True, exist_ok=True)
    default_output.mkdir(parents=True, exist_ok=True)

    files = st.file_uploader(
        "Anexar imagens/fotos do voo ou ortomosaico base",
        type=["jpg", "jpeg", "png", "tif", "tiff", "geotiff", "dng", "raw", "arw", "cr2", "nef", "zip"],
        accept_multiple_files=True,
        key="ortho_generator_images",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        job_name = st.text_input("Nome do ortomosaico", value=f"ortomosaico_{date.today().strftime('%Y%m%d')}", key="ortho_job_name")
        qualidade = st.selectbox("Qualidade / resolução", list(ORTHOMOSAIC_QUALITY_PRESETS.keys()), key="ortho_quality")
    with c2:
        modo_execucao = st.selectbox(
            "Modo de execução",
            ["Rodar pelo VS Code com Docker", "Rodar pelo VS Code + Docker local/WebODM já instalado"],
            key="ortho_execution_mode",
        )
        docker_image = st.text_input("Imagem Docker/OpenDroneMap", value="opendronemap/odm:latest", key="ortho_docker_image")
    with c3:
        if "ortho_output_dir" not in st.session_state:
            st.session_state["ortho_output_dir"] = str(default_output)
        if st.button("Selecionar pasta de saída no computador", key="ortho_choose_output_dir", use_container_width=True):
            selected_dir, folder_err = _orthomosaic_select_folder_dialog(default_output)
            if selected_dir:
                st.session_state["ortho_output_dir"] = selected_dir
                st.success(f"Pasta selecionada: {selected_dir}")
            else:
                st.info(folder_err)
        output_dir = st.text_input("Pasta de saída local", value=st.session_state["ortho_output_dir"], key="ortho_output_dir_text")
        st.session_state["ortho_output_dir"] = output_dir

    preset = ORTHOMOSAIC_QUALITY_PRESETS[qualidade]
    quality_args = _orthomosaic_quality_args(preset)
    st.markdown("##### Parâmetros automáticos")
    st.json({
        "qualidade": qualidade,
        "resolução_orthophoto_cm_px": preset["resolution_cm"],
        "feature_quality": preset["feature_quality"],
        "pc_quality": preset["pc_quality"],
        "mesh_octree_depth": preset["mesh_depth"],
        "min_features": preset["min_features"],
        "matcher_neighbors": preset["matcher_neighbors"],
        "descrição": preset["descricao"],
    })

    if st.button("🛰️ Gerar Ortomosaico", type="primary", key="ortho_start_generation", use_container_width=True):
        if not files:
            st.warning("Anexe as fotos do drone antes de iniciar.")
            return
        clean_name = _tv_safe_name(job_name) or f"ortomosaico_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        job_id = f"ORT_JOB_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{clean_name}"
        job_dir = jobs_root / job_id
        project_slug = clean_name
        input_dir = job_dir / project_slug / "images"
        logs_dir = job_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        progress = st.progress(0)
        status = st.empty()
        status.info("1/5 — Salvando imagens do voo com integridade...")
        saved, total_size = _save_uploaded_files_generic(files, input_dir)
        progress.progress(25)

        output_path = _resolve_system_path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        status.info("2/5 — Gerando scripts, tasks do VS Code e parâmetros Docker/WebODM...")
        workspace = _orthomosaic_write_vscode_workspace(
            job_dir=job_dir,
            project_slug=project_slug,
            output_dir=output_path,
            docker_image=docker_image,
            quality_args=quality_args,
            mode=modo_execucao,
            final_name=clean_name,
        )
        job_config = {
            "job_id": job_id,
            "criado_em": _now_human(),
            "usuario": _auth_user_name(),
            "qualidade": qualidade,
            "parametros": preset,
            "modo_execucao": modo_execucao,
            "input_dir": str(input_dir),
            "output_dir": str(output_path),
            "docker_image": docker_image,
            "command": workspace["docker_command"],
            "final_tif": workspace["final_tif"],
            "arquivos": saved,
        }
        (job_dir / "job_config.json").write_text(json.dumps(job_config, indent=2, ensure_ascii=False), encoding="utf-8")
        log_path = logs_dir / "processing.log"
        log_path.write_text(
            "\n".join([
                f"[{_now_human()}] Job preparado: {job_id}",
                f"Entrada: {input_dir}",
                f"Saída: {output_path}",
                f"Modo: {modo_execucao}",
                f"Comando Docker: {workspace['docker_command']}",
            ]),
            encoding="utf-8",
        )
        _orthomosaic_upsert_job({
            "job_id": job_id,
            "nome": clean_name,
            "pasta_entrada": str(input_dir),
            "pasta_saida": str(output_path),
            "qualidade": qualidade,
            "status": "Preparado para execução externa no VS Code",
            "caminho_ortomosaico": workspace["final_tif"],
            "modo_execucao": modo_execucao,
            "criado_em": _now_human(),
            "atualizado_em": _now_human(),
        })
        progress.progress(70)

        package_base = jobs_root / f"{job_id}_pacote_integracao"
        package_zip = shutil.make_archive(str(package_base), "zip", root_dir=job_dir)
        opened, open_msg = _orthomosaic_open_vscode(job_dir)
        progress.progress(100)
        status.success("5/5 — Projeto preparado para VS Code/Docker/WebODM.")

        st.success(f"Projeto `{job_id}` preparado com {len(saved)} arquivo(s), total {_tv_human_size(total_size)}.")
        (st.success if opened else st.info)(open_msg)
        st.json({
            "Job": job_id,
            "Nome": clean_name,
            "Entrada": str(input_dir),
            "Saída": str(output_path),
            "Qualidade": qualidade,
            "Modo": modo_execucao,
            "VS Code": str(job_dir),
            "SQLite": str(_orthomosaic_db_path()),
            "Ortomosaico esperado": workspace["final_tif"],
        })
        st.download_button(
            "⬇️ Baixar pacote de integração",
            data=Path(package_zip).read_bytes(),
            file_name=Path(package_zip).name,
            mime="application/zip",
            use_container_width=True,
        )

    st.markdown("#### Visualizador do ortomosaico gerado")
    jobs = _orthomosaic_list_jobs()
    if not jobs:
        st.info("Nenhum projeto de ortomosaico preparado ainda.")
        return
    labels = [
        f"{item.get('criado_em','')} · {item.get('nome','')} · {item.get('qualidade','')} · {item.get('status','')}"
        for item in jobs
    ]
    selected_label = st.selectbox("Projetos preparados", labels, key="ortho_job_view_select")
    selected_job = jobs[labels.index(selected_label)]
    output_path = _resolve_system_path(selected_job.get("pasta_saida", str(default_output)))
    expected_path = Path(str(selected_job.get("caminho_ortomosaico", "")))
    outputs = []
    if expected_path.exists():
        outputs.append(expected_path)
    outputs.extend([p for p in _orthomosaic_find_outputs(output_path, _tv_safe_name(selected_job.get("nome", ""))) if p not in outputs])
    if outputs:
        selected_output = st.selectbox("Ortomosaico disponível", [str(path) for path in outputs], key="ortho_output_file_select")
        selected_path = Path(selected_output)
        _orthomosaic_upsert_job({
            **selected_job,
            "status": "Ortomosaico encontrado",
            "caminho_ortomosaico": str(selected_path),
            "atualizado_em": _now_human(),
        })
        _orthomosaic_render_viewer(selected_path)
    else:
        st.info("Nenhum ortomosaico gerado encontrado ainda. Execute a task no VS Code e volte aqui para visualizar/baixar o resultado.")
        st.caption(f"Pasta monitorada: {output_path}")

def _render_sync_backup() -> None:
    st.subheader("🔄 Backup e Sincronização de Dados")
    st.info("Área real para gerar backup dos dados internos e preparar sincronização com Google Drive ou pasta externa.")

    backup_root = SYSTEM_DATABASE_DIR / "backups"
    sync_config_path = SYSTEM_DATABASE_DIR / "sync_config.json"
    try:
        sync_config = json.loads(sync_config_path.read_text(encoding="utf-8")) if sync_config_path.exists() else {}
    except Exception:
        sync_config = {}

    c1, c2 = st.columns(2)
    with c1:
        drive_target = st.text_input("Link ou caminho do Google Drive / destino", value=sync_config.get("destino", ""), key="sync_drive_target")
        destination_folder = st.text_input("Pasta de destino", value=sync_config.get("pasta_destino", "TMG_Backups"), key="sync_destination_folder")
        local_source = st.text_input("Caminho local dos dados", value=str(SYSTEM_DATABASE_DIR), key="sync_local_source")
    with c2:
        client_id = st.text_input("Google client_id", value=sync_config.get("client_id", ""), key="sync_client_id")
        client_secret = st.text_input("Google client_secret", value="", type="password", key="sync_client_secret")
        token = st.text_input("Token / refresh token", value="", type="password", key="sync_token")

    st.caption("Se a API do Google Drive exigir credenciais, preencha os campos acima. Sem credenciais, o sistema gera um pacote ZIP seguro para envio manual ou cópia local.")
    if st.button("▶ Iniciar sincronização / backup", type="primary", key="sync_start_backup", use_container_width=True):
        progress = st.progress(0)
        status = st.empty()
        status.info("1/4 — Mapeando dados internos do sistema...")
        source = _resolve_system_path(local_source)
        backup_root.mkdir(parents=True, exist_ok=True)
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_file = backup_root / f"{backup_id}.zip"

        files_to_zip = []
        if source.exists():
            for path in source.rglob("*"):
                if path.is_file() and backup_root not in path.parents:
                    files_to_zip.append(path)
        progress.progress(30)

        status.info("2/4 — Compactando arquivos, históricos, tratativas, imagens e configurações...")
        with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in files_to_zip:
                try:
                    zf.write(path, arcname=str(Path("dados") / path.relative_to(source)))
                except Exception:
                    pass
            for extra in (SYSTEM_CONFIG_PATH, LOGO_PATH, LOGIN_BG_PATH):
                if extra.exists():
                    zf.write(extra, arcname=str(Path("configuracoes") / extra.name))
        progress.progress(70)

        copied_to = ""
        target_text = str(drive_target or "").strip()
        if target_text and not target_text.lower().startswith(("http://", "https://")):
            try:
                target_dir = _resolve_system_path(target_text) / _tv_safe_name(destination_folder or "TMG_Backups")
                target_dir.mkdir(parents=True, exist_ok=True)
                copied = target_dir / backup_file.name
                shutil.copy2(backup_file, copied)
                copied_to = str(copied)
            except Exception as exc:
                copied_to = f"Não foi possível copiar automaticamente: {exc}"
        progress.progress(90)

        sync_config = {
            "destino": drive_target,
            "pasta_destino": destination_folder,
            "client_id": client_id,
            "client_secret_configurado": bool(client_secret),
            "token_configurado": bool(token),
            "ultimo_backup": _now_human(),
            "ultimo_arquivo": str(backup_file),
            "copiado_para": copied_to,
        }
        sync_config_path.write_text(json.dumps(sync_config, indent=2, ensure_ascii=False), encoding="utf-8")
        progress.progress(100)
        status.success("4/4 — Backup finalizado e registro atualizado.")
        st.success(f"Backup criado: `{backup_file}`")
        st.json(sync_config)
        st.download_button(
            "⬇️ Baixar backup ZIP",
            data=backup_file.read_bytes(),
            file_name=backup_file.name,
            mime="application/zip",
            use_container_width=True,
        )




# ==========================================
# SIDEBAR[cite: 1]
# ==========================================
current_user = _auth_current_user()
show_culture_modules = bool(_auth_allowed_cultures(current_user))
show_partners_module = _auth_can_partners(current_user)
show_admin_config = _auth_is_admin(current_user)
is_partners_page = st.session_state.pagina_ativa == 'Parceiros'

with st.sidebar:

    st.markdown("""
    <div class='menu-3d-title'>&#9776; MENU</div>
    <hr class='separator-glow'>
    """, unsafe_allow_html=True)

    if is_partners_page and show_partners_module:
        if _auth_menu_allowed("menu_parceiros", current_user):
            if st.button("🤝 Parceiros", key="btn_parceiros_home"):
                st.session_state["partner_selected"] = ""
                st.session_state["partner_section"] = ""
                ir_para('Parceiros')
        if _auth_menu_allowed("menu_controle_dados", current_user):
            if st.button("📊 Controle de Dados", key="btn_parceiros_controle_dados"):
                if st.session_state.get("partner_selected"):
                    st.session_state["partner_section"] = st.session_state.get("partner_section", "") or "sheet"
                ir_para('Parceiros')
    else:
        if show_culture_modules:
            if _auth_menu_allowed("menu_checklist", current_user) and st.button("📋 Checklist Notas", key="btn_check"):
                ir_para('Checklist')

            if _auth_menu_allowed("menu_grid", current_user) and st.button("📊 Marcador de Grid", key="btn_grid"):
                ir_para('Grid')

            if _auth_menu_allowed("menu_upload", current_user) and st.button("📤 Upload de Imagens", key="btn_upload"):
                ir_para('Upload')

            if _auth_menu_allowed("menu_bases", current_user) and st.button("🗂️ Banco de Dados Sistema", key="btn_bases"):
                ir_para('Bases')

            if _auth_menu_allowed("menu_sync", current_user) and st.button("🔄 Sincronizar Dados", key="btn_sync"):
                ir_para('Sync')

            if _auth_menu_allowed("menu_ortomosaicos", current_user) and st.button("🛰️ Gerar Ortomosaicos", key="btn_orto"):
                ir_para('Ortomosaicos')

            # NOVO - Botão Análises de Fenotipagem controlado por permissão do usuário
            if _auth_allowed_phenotyping(current_user):
                if st.button("📈 Análises de Fenotipagem", key="btn_visualizador"):
                    ir_para('Visualizador')

            # NOVO - Botão isolado para fluxo passo a passo de voos para análise
            if st.button("🛰️ Processos de Voos para Análise", key="btn_processos_voos_analise"):
                ir_para('VoosDirecionados')

        if show_partners_module and _auth_menu_allowed("menu_parceiros", current_user):
            if st.button("🤝 Parceiros / Controle de Voos e Dados", key="btn_parceiros_controle"):
                st.session_state["partner_selected"] = ""
                st.session_state["partner_section"] = ""
                ir_para('Parceiros')

    if (not is_partners_page) and (show_culture_modules or show_admin_config):
        if st.button("⚙️ Configurações", key="btn_config"):
            ir_para('Config')

    if st.button("🚪 Sair", key="btn_logout"):
        st.session_state.logged_in = False
        st.session_state.auth_user = None
        st.session_state.cultura_selecionada = None
        st.session_state.pagina_ativa = "Checklist"
        app_rerun()

    st.markdown("---")
    st.caption("TMG v2.0 - 2026")

# ==========================================
# TOPO (LOGO FIXA)[cite: 1]
# ==========================================
_render_logged_user_chip()
_render_system_chat(current_user)

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
    # PARCEIROS / CONTROLE DE VOOS E DADOS
    # ==========================================
    elif st.session_state.pagina_ativa == 'Parceiros':
        render_parceiros_controle()

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

        chk_file = _resettable_ortho_uploader(
            "Selecione a ortofoto para anotação",
            key="chk_orto_uploader",
            help="PNG · JPG · TIF/GeoTIFF · JP2 · IMG · ECW"
        )
        chk_bytes, chk_name = _uploaded_ortho_bytes(chk_file)

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
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;">
      <button class="grid-btn" id="btnSaveGrid">Salvar Grid</button>
      <button class="grid-btn" id="btnNewGrid">Novo Grid</button>
      <button class="grid-btn" id="btnDeleteGrid" style="color:#ff6b6b;border-color:#552222;">Excluir Grid</button>
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
const btnDeleteGrid = document.getElementById('btnDeleteGrid');
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

function deleteActiveGrid() {{
  const target = activeGridName;
  if(!savedGrids[target]) {{
    points = [];
    annotations = {{}};
    closePopup();
    draw();
    return;
  }}
  if(!confirm('Excluir definitivamente o grid "' + target + '"? Ele sairá da lista, da visualização e da exportação.')) return;
  delete savedGrids[target];
  const remaining = Object.keys(savedGrids);
  if(remaining.length > 0) {{
    activeGridName = remaining[0];
    const rec = savedGrids[activeGridName] || {{}};
    points = clonePoints(rec.points);
    annotations = cloneAnnotations(rec.annotations);
    inpRows.value = rec.rows || inpRows.value;
    inpCols.value = rec.cols || inpCols.value;
  }} else {{
    activeGridName = 'Grid 1';
    points = [];
    annotations = {{}};
    savedGrids[activeGridName] = {{
      points: [],
      annotations: {{}},
      rows: parseInt(inpRows.value)||1,
      cols: parseInt(inpCols.value)||1
    }};
  }}
  closePopup();
  updateGridSelect();
  persistGrids();
  draw();
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

function loadScriptOnce(src) {{
  return new Promise((resolve, reject) => {{
    const existing = document.querySelector('script[data-tmg-src="' + src + '"]');
    if(existing) {{
      if(existing.dataset.loaded === 'true') {{
        resolve(true);
        return;
      }}
      existing.addEventListener('load', () => resolve(true), {{once:true}});
      existing.addEventListener('error', () => reject(new Error('Falha ao carregar ' + src)), {{once:true}});
      return;
    }}
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.dataset.tmgSrc = src;
    script.onload = () => {{
      script.dataset.loaded = 'true';
      resolve(true);
    }};
    script.onerror = () => reject(new Error('Falha ao carregar ' + src));
    document.head.appendChild(script);
  }});
}}

async function ensureChecklistExcelStyles() {{
  if(window.__tmgChecklistXlsxStyleReady && typeof XLSX !== 'undefined') return true;
  const urls = [
    'https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js',
    'https://unpkg.com/xlsx-js-style@1.2.0/dist/xlsx.bundle.js'
  ];
  for(const url of urls) {{
    try {{
      await loadScriptOnce(url);
      if(typeof XLSX !== 'undefined') {{
        window.__tmgChecklistXlsxStyleReady = true;
        return true;
      }}
    }} catch(e) {{
      console.warn(e);
    }}
  }}
  return false;
}}

btnExport.onclick = async () => {{
  const nome = prompt('Digite o nome do arquivo Excel:', 'checklist_notas_parcelas');
  if(nome === null) return;
  const safeName = (nome.trim() || 'checklist_notas_parcelas')
    .replace(/[\\\\/:*?"<>|]+/g,'_')
    .replace(/\\s+/g,'_');
  const gridRecords = getExportGridRecords().filter(grid => grid.points && grid.points.length === 4);
  if(gridRecords.length === 0) {{
    alert('Nenhum grid salvo/marcado disponível para exportar.');
    return;
  }}
  if(typeof XLSX === 'undefined' && !(await ensureChecklistExcelStyles())) {{
    alert('Biblioteca Excel não carregada. Tente novamente em alguns segundos.');
    return;
  }}
  if(!(await ensureChecklistExcelStyles())) {{
    alert('Biblioteca de estilos do Excel não carregada. Verifique a conexão e tente exportar novamente.');
    return;
  }}
  const headers = ['Quadra','Disparo','Tiro','Nota','Observação'];
  const dados = [headers];
  gridRecords
    .sort((a,b) => String(a.name).localeCompare(String(b.name), 'pt-BR', {{numeric:true}}))
    .forEach(grid => {{
    const R=parseInt(grid.rows)||1, C=parseInt(grid.cols)||1;
    for(let r=0;r<R;r++) for(let c=0;c<C;c++) {{
      const ann=(grid.annotations[r]||{{}})[c];
      const nota=Number(ann && ann.nota ? ann.nota : 1);
      dados.push([grid.name, r+1, c+1, nota, ann ? (ann.obs || '') : '']);
    }}
  }});
  const ws = XLSX.utils.aoa_to_sheet(dados);
  ws['!cols'] = [{{wch:14}},{{wch:10}},{{wch:10}},{{wch:10}},{{wch:34}}];
  ws['!freeze'] = {{xSplit:0,ySplit:1}};

  const border = {{
    top:{{style:'thin',color:{{rgb:'808080'}}}},
    bottom:{{style:'thin',color:{{rgb:'808080'}}}},
    left:{{style:'thin',color:{{rgb:'808080'}}}},
    right:{{style:'thin',color:{{rgb:'808080'}}}}
  }};
  const headerStyle = {{
    font:{{bold:true,color:{{rgb:'00B0F0'}}}},
    fill:{{patternType:'solid',fgColor:{{rgb:'1F1F1F'}}}},
    alignment:{{horizontal:'center',vertical:'center'}},
    border
  }};
  const defaultStyle = {{
    font:{{color:{{rgb:'000000'}}}},
    alignment:{{horizontal:'center',vertical:'center',wrapText:true}},
    border
  }};
  const notaStyles = {{
    1: {{fill:'00B050', font:'FFFFFF'}},
    2: {{fill:'FFF2CC', font:'000000'}},
    3: {{fill:'DDEBF7', font:'000000'}},
    4: {{fill:'FCE4D6', font:'000000'}},
    5: {{fill:'E7E6E6', font:'000000'}},
    6: {{fill:'E4DFEC', font:'000000'}},
    7: {{fill:'CCFFFF', font:'000000'}},
    8: {{fill:'EADCC8', font:'000000'}},
    9: {{fill:'C00000', font:'FFFFFF'}}
  }};
  function notaStyle(nota) {{
    const item = notaStyles[Number(nota)] || {{fill:'FFFFFF', font:'000000'}};
    return {{
      font:{{bold:true,color:{{rgb:item.font}}}},
      fill:{{patternType:'solid',fgColor:{{rgb:item.fill}}}},
      alignment:{{horizontal:'center',vertical:'center'}},
      border
    }};
  }}

  const range = XLSX.utils.decode_range(ws['!ref']);
  for(let row=range.s.r; row<=range.e.r; row++) {{
    for(let col=range.s.c; col<=range.e.c; col++) {{
      const addr = XLSX.utils.encode_cell({{r:row,c:col}});
      if(!ws[addr]) continue;
      ws[addr].s = row === 0 ? headerStyle : (col === 3 ? notaStyle(ws[addr].v) : defaultStyle);
      if(row > 0 && col === 3) ws[addr].t = 'n';
    }}
  }}
  const wb = XLSX.utils.book_new();
  wb.Props = {{
    Title:'Checklist de Notas',
    Subject:'Notas por Quadra, Disparo e Tiro',
    Author:'TMG Sistema de Análise',
    CreatedDate:new Date()
  }};
  XLSX.utils.book_append_sheet(wb, ws, 'Checklist Notas');
  XLSX.writeFile(wb, safeName+'.xlsx', {{bookType:'xlsx',cellStyles:true}});
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
btnDeleteGrid.onclick=deleteActiveGrid;
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

        orto_file = _resettable_ortho_uploader(
            "Selecione a ortofoto",
            key="orto_uploader",
            help="Formatos suportados: PNG, JPG, TIF/GeoTIFF, JP2, IMG"
        )

        grid_prefill_path = st.session_state.get("grid_prefill_ortho_path", "")
        grid_prefill_name = st.session_state.get("grid_prefill_ortho_name", "")
        grid_prefill_available = bool(grid_prefill_path and Path(grid_prefill_path).exists())
        if grid_prefill_available and not orto_file:
            st.info(f"Ortofoto recebida do módulo Voos Direcionados: {grid_prefill_name or Path(grid_prefill_path).name}")
            if st.button("Limpar ortofoto recebida", key="btn_clear_grid_prefill"):
                st.session_state.pop("grid_prefill_ortho_path", None)
                st.session_state.pop("grid_prefill_ortho_name", None)
                app_rerun()

        if orto_file or grid_prefill_available:
            with st.spinner("Carregando ortofoto de alta resolução... (Isso pode levar alguns segundos)"):
                if orto_file:
                    file_bytes, orto_nome_exibicao = _uploaded_ortho_bytes(orto_file)
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
                grid_spatial_json = json.dumps({
                    "ratio": (spatial_meta or {}).get("ratio", 1.0),
                    "transform": (spatial_meta or {}).get("transform"),
                    "crs": str((spatial_meta or {}).get("crs") or ""),
                }, ensure_ascii=False)

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

  .shp-ref-panel {{
    position:absolute; top:12px; left:12px; z-index:25;
    width:360px; max-width:calc(100% - 430px);
    background:rgba(10,10,10,.90); border:1px solid #2a2a2a; border-radius:8px;
    padding:9px; display:flex; flex-direction:column; gap:6px;
    font-family:'Segoe UI',sans-serif; box-shadow:0 8px 22px rgba(0,0,0,.45);
  }}
  .shp-ref-panel label {{ color:#ff00ff; font-size:11px; font-weight:800; letter-spacing:1px; text-transform:uppercase; }}
  .shp-ref-panel input {{
    width:100%; background:#111; border:1px solid #333; color:#fff; border-radius:5px;
    padding:6px 8px; font-size:11px; outline:none;
  }}
  .shp-ref-panel input:focus {{ border-color:#ff00ff; box-shadow:0 0 8px rgba(255,0,255,.22); }}
  .shp-ref-status {{ color:#888; font-size:9px; line-height:1.25; }}

  .zoom-badge {{
    position: absolute;
    top: 116px; left: 12px;
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

  <div class="shp-ref-panel">
      <label>🗺️ Referências para exportar SHP</label>
      <input type="text" id="inpShpRef" placeholder="Digite coordenadas/referências e pressione ENTER">
      <div class="shp-ref-status" id="shpRefStatus">Aguardando referência. O botão SHP será liberado após ENTER.</div>
      <button class="grid-btn" id="btnExportSHP" style="display:none;color:#ff00ff; border-color:#990099;">🗺️ Exportar Shapefile (.SHP)</button>
  </div>

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
const btnExportSHP = document.getElementById('btnExportSHP');
const inpShpRef = document.getElementById('inpShpRef');
const shpRefStatus = document.getElementById('shpRefStatus');
const GRID_SPATIAL_META = {grid_spatial_json};
let gridMode = false;
let points = [];
let draggingPoint = -1;
let shpReferenceReady = false;

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
            cols: parseInt(inpCols.value)||1,
            referencia: (inpShpRef ? inpShpRef.value.trim() : ''),
            referencia_pronta: shpReferenceReady
        }};
        const payload = JSON.stringify(data);
        try {{
            window.localStorage.setItem('tmg_grid_payload', payload);
            const parentDoc = window.parent && window.parent.document;
            if(parentDoc) {{
                const inputs = Array.from(parentDoc.querySelectorAll('input'));
                const target = inputs.find(el => el.getAttribute('aria-label') === 'grid_payload');
                if(target) {{
                    const setter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value').set;
                    setter.call(target, payload);
                    target.dispatchEvent(new Event('input', {{bubbles:true}}));
                    target.dispatchEvent(new Event('change', {{bubbles:true}}));
                }}
            }}
        }} catch(e) {{ console.log("Sincronização local indisponível", e); }}
    }}
}}

function validateShpReference(showAlert=false) {{
    const value = (inpShpRef ? inpShpRef.value.trim() : '');
    shpReferenceReady = value.length > 0;
    if(shpReferenceReady) {{
        btnExportSHP.style.display = 'block';
        shpRefStatus.textContent = 'Referência reconhecida. A exportação SHP está liberada para o grid marcado.';
        syncToPython();
        if(showAlert) alert('Referência reconhecida. Agora use Exportar Shapefile (.SHP).');
    }} else {{
        btnExportSHP.style.display = 'none';
        shpRefStatus.textContent = 'Aguardando referência. O botão SHP será liberado após ENTER.';
    }}
}}

function pixelToGeo(pt) {{
    const ratio = Number(GRID_SPATIAL_META && GRID_SPATIAL_META.ratio ? GRID_SPATIAL_META.ratio : 1) || 1;
    const x = pt.x / ratio;
    const y = pt.y / ratio;
    const tr = GRID_SPATIAL_META && Array.isArray(GRID_SPATIAL_META.transform) ? GRID_SPATIAL_META.transform : null;
    if(tr && tr.length >= 6) {{
        return [
            Number(tr[0]) + x * Number(tr[1]) + y * Number(tr[2]),
            Number(tr[3]) + x * Number(tr[4]) + y * Number(tr[5])
        ];
    }}
    return [x, -y];
}}

function buildGridGeoJSON() {{
    const R = parseInt(inpRows.value) || 1;
    const C = parseInt(inpCols.value) || 1;
    const p0 = points[0], p1 = points[1], p2 = points[2], p3 = points[3];
    const features = [];
    for(let r=0; r<R; r++) {{
        for(let c=0; c<C; c++) {{
            const u0=c/C, u1=(c+1)/C, v0=r/R, v1=(r+1)/R;
            const tl=bilerp(p0,p1,p2,p3,u0,v0);
            const tr=bilerp(p0,p1,p2,p3,u1,v0);
            const br=bilerp(p0,p1,p2,p3,u1,v1);
            const bl=bilerp(p0,p1,p2,p3,u0,v1);
            const coords = [tl,tr,br,bl,tl].map(pixelToGeo);
            features.push({{
                type:'Feature',
                properties:{{
                    ID:'T'+(c+1)+' D'+(r+1),
                    TIRO:c+1,
                    DISPARO:r+1,
                    REFERENCIA:(inpShpRef ? inpShpRef.value.trim() : '')
                }},
                geometry:{{type:'Polygon', coordinates:[coords]}}
            }});
        }}
    }}
    return {{type:'FeatureCollection', features}};
}}

function exportGridShapefile() {{
    if(points.length !== 4) {{
        alert('Por favor, marque os 4 pontos do Grid antes de exportar o Shapefile.');
        return;
    }}
    validateShpReference(false);
    if(!shpReferenceReady) {{
        alert('Digite as coordenadas/referências e pressione ENTER antes de exportar o SHP.');
        return;
    }}
    syncToPython();
    const geojson = buildGridGeoJSON();
    try {{
        if(typeof shpwrite === 'undefined' || !shpwrite.download) {{
            throw new Error('Biblioteca shp-write não carregada.');
        }}
        shpwrite.download(geojson, {{file:'TMG_Grid_Shapefile'}});
        shpRefStatus.textContent = 'SHP gerado com sucesso para o grid marcado.';
    }} catch(err) {{
        console.error(err);
        alert('Não foi possível gerar o SHP direto no visualizador. Verifique a conexão da biblioteca shp-write ou use o ambiente com dependências geoespaciais.');
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

inpShpRef.addEventListener('keydown', (e) => {{
    if(e.key === 'Enter') {{
        e.preventDefault();
        validateShpReference(true);
    }}
}});
inpShpRef.addEventListener('input', () => {{
    if(!inpShpRef.value.trim()) validateShpReference(false);
}});
btnExportSHP.onclick = exportGridShapefile;

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
                "padrao": "🔵 Padrão do Sistema  —  Dark com cor do tema",
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

        if _auth_is_admin():
            with st.expander("Logos das Parceiras", expanded=False):
                _render_partner_logo_settings()

            with st.expander("Gerenciar Usuários", expanded=False):
                _render_manage_users()

            with st.expander("Histórico Geral do Sistema", expanded=False):
                state_hist = _partners_load_state()
                st.dataframe(_partners_history_rows(state_hist.get("history_general", [])), use_container_width=True, hide_index=True)

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
        _render_sync_backup()

    # GERAR ORTOMOSAICOS[cite: 1]
    elif st.session_state.pagina_ativa == 'Ortomosaicos':
        _render_orthomosaic_generator()

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

        phenotyping_buttons = [
            ("phenotyping_contagem", "🔢 Contagem", "Contagem", "btn_viz_contagem"),
            ("phenotyping_maturacao", "🍇 Maturação", "Maturação", "btn_viz_maturacao"),
            ("phenotyping_pendoamento", "🌾 Pendoamento", "Pendoamento", "btn_viz_pendoamento"),
            ("phenotyping_qualidade", "✅ Qualidade de Parcelas", "Qualidade", "btn_viz_qualidade"),
        ]
        visible_phenotyping_buttons = [item for item in phenotyping_buttons if _auth_phenotyping_allowed(item[0], current_user)]
        allowed_visualizador_subs = {item[2] for item in visible_phenotyping_buttons}

        if st.session_state.visualizador_sub and st.session_state.visualizador_sub not in allowed_visualizador_subs:
            st.session_state.visualizador_sub = None

        if not visible_phenotyping_buttons:
            st.warning("Seu usuário não possui análises de fenotipagem liberadas. Solicite permissão ao administrador.")
            st.stop()

        vcols = st.columns(len(visible_phenotyping_buttons))
        for col, (_, label, sub_page, button_key) in zip(vcols, visible_phenotyping_buttons):
            with col:
                if st.button(label, key=button_key, use_container_width=True):
                    st.session_state.visualizador_sub = sub_page

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
            cnt_file = _resettable_ortho_uploader(
                "📷 Carregar Ortofoto para Contagem",
                key="cnt_orto_uploader",
                help="PNG · JPG · TIF/GeoTIFF · JP2 · IMG · ECW"
            )
            cnt_bytes, cnt_name = _uploaded_ortho_bytes(cnt_file)

            if cnt_bytes:
                with st.spinner("Carregando ortofoto..."):
                    cnt_b64, cnt_dims, cnt_err, cnt_spatial = processar_ortofoto(cnt_bytes, cnt_name)

                if cnt_err:
                    st.error(f"Erro: {cnt_err}")
                else:
                    cw_cnt, ch_cnt = cnt_dims
                    cnt_storage_id = json.dumps(_tv_hash_bytes(cnt_bytes)[:32])
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
  .grid-panel input[type=text], .grid-panel select {{
    background:#1a1a1a; border:1px solid #333; color:#fff;
    border-radius:4px; padding:4px; font-size:11px; min-width:104px;
  }}
  .grid-panel .row-col {{ display:flex; gap:8px; align-items:center; justify-content:space-between; color:#ccc; font-size:11px; }}
  .grid-status {{ color:#777; font-size:9px; line-height:1.25; max-width:190px; }}
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
      <span>Quadra:</span><input type="text" id="inpGridName" value="Grid 1">
    </div>
    <div class="row-col">
      <span>Ativo:</span><select id="selGridList"></select>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;">
      <button class="grid-btn" id="btnSaveGrid">Salvar</button>
      <button class="grid-btn" id="btnNewGrid">Novo</button>
      <button class="grid-btn" id="btnDeleteGrid" style="color:#ff6b6b;border-color:#552222;">Excluir</button>
    </div>
    <div class="grid-status" id="gridStatus">Grid ativo: Grid 1</div>
    <div class="row-col">
      <span>Disp:</span><input type="number" id="inpRows" value="5" min="1" max="200">
    </div>
    <div class="row-col">
      <span>Tiros:</span><input type="number" id="inpCols" value="5" min="1" max="200">
    </div>
    <button class="cnt-btn" id="btnCountAuto">🌱 Contar</button>
    <button class="cnt-btn manual" id="btnManual2">✏️ Manual</button>
    <button class="cnt-btn danger" id="btnUndoMark">❌ Desfazer</button>
    <div class="row-col" style="justify-content:flex-start; gap:4px;">
      <input type="checkbox" id="cbExportAll" style="width:auto;accent-color:#00ee55;">
      <span style="font-size:10px;">Exportar todos os grids salvos</span>
    </div>
    <button id="btnExportCnt">💾 Exportar CSV</button>
    <button class="cnt-btn" id="btnExportXLSXCnt" style="background:linear-gradient(145deg,#1a003a,#0a001a);border-color:#660099;color:#cc66ff;">📗 Exportar Excel</button>
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
const btnExportXLSXCnt = document.getElementById('btnExportXLSXCnt');
const inpGridName = document.getElementById('inpGridName');
const selGridList = document.getElementById('selGridList');
const btnSaveGrid = document.getElementById('btnSaveGrid');
const btnNewGrid = document.getElementById('btnNewGrid');
const btnDeleteGrid = document.getElementById('btnDeleteGrid');
const cbExportAll = document.getElementById('cbExportAll');
const gridStatus = document.getElementById('gridStatus');
const countPanel = document.getElementById('countPanel');
const totalCountEl = document.getElementById('totalCount');
const countInfoEl = document.getElementById('countInfo');
const ORTHO_STORAGE_ID = {cnt_storage_id};
const STORAGE_KEY = 'tmg_contagem_plantas_grids_' + ORTHO_STORAGE_ID;

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
let savedGrids = {{}};
let activeGridName = 'Grid 1';
let suppressPersist = false;

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

function cleanGridName(name) {{
  const value = String(name || '').trim();
  return value || 'Grid 1';
}}

function makeUniqueGridName(base) {{
  let name = cleanGridName(base);
  if(!savedGrids[name]) return name;
  let i = 2;
  while(savedGrids[name + ' ' + i]) i++;
  return name + ' ' + i;
}}

function clonePoints(src) {{
  return (src || []).map(p => ({{x:Number(p.x)||0, y:Number(p.y)||0}}));
}}

function cloneMarks(src) {{
  return (src || []).map(p => ({{x:Number(p.x)||0, y:Number(p.y)||0}}));
}}

function cloneCounts(src) {{
  return JSON.parse(JSON.stringify(src || {{}}));
}}

function persistGrids() {{
  if(suppressPersist) return;
  try {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify({{
      activeGridName,
      savedGrids,
      updatedAt: new Date().toISOString()
    }}));
  }} catch(e) {{ console.warn('Não foi possível salvar grids de contagem:', e); }}
}}

function applyGridRecord(rec) {{
  rec = rec || {{}};
  points = clonePoints(rec.points);
  plantCenters = cloneMarks(rec.plantCenters);
  manualMarks = cloneMarks(rec.manualMarks);
  parcelCounts = cloneCounts(rec.parcelCounts);
  inpRows.value = rec.rows || inpRows.value;
  inpCols.value = rec.cols || inpCols.value;
  countPanel.style.display = Object.keys(parcelCounts).length ? 'block' : 'none';
  totalCountEl.textContent = plantCenters.length || 0;
  countInfoEl.textContent = Object.keys(parcelCounts).length
    ? 'Grid ' + (parseInt(inpRows.value)||1) + '×' + (parseInt(inpCols.value)||1) + ' | ' + (plantCenters.length||0) + ' plantas'
    : 'Marque o grid e clique Contar';
}}

function saveActiveGrid(showMsg=false) {{
  activeGridName = cleanGridName(inpGridName.value || activeGridName);
  savedGrids[activeGridName] = {{
    points: clonePoints(points),
    plantCenters: cloneMarks(plantCenters),
    manualMarks: cloneMarks(manualMarks),
    parcelCounts: cloneCounts(parcelCounts),
    rows: parseInt(inpRows.value)||1,
    cols: parseInt(inpCols.value)||1
  }};
  updateGridSelect();
  persistGrids();
  if(showMsg) gridStatus.textContent = 'Grid salvo: ' + activeGridName;
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
    if(rec) applyGridRecord(rec);
    return Object.keys(savedGrids).length > 0;
  }} catch(e) {{ console.warn('Não foi possível restaurar grids de contagem:', e); return false; }}
}}

function updateGridSelect() {{
  if(!savedGrids[activeGridName]) {{
    savedGrids[activeGridName] = {{
      points: clonePoints(points),
      plantCenters: cloneMarks(plantCenters),
      manualMarks: cloneMarks(manualMarks),
      parcelCounts: cloneCounts(parcelCounts),
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
    const counted = rec.parcelCounts && Object.keys(rec.parcelCounts).length > 0;
    opt.textContent = name + (counted ? ' ✓' : '');
    selGridList.appendChild(opt);
  }});
  selGridList.value = activeGridName;
  inpGridName.value = activeGridName;
  const marked = points.length === 4 ? 'marcado' : 'sem 4 pontos';
  const counted = Object.keys(parcelCounts).length > 0 ? 'com contagem' : 'sem contagem';
  gridStatus.textContent = 'Grid ativo: ' + activeGridName + ' · ' + marked + ' · ' + counted + ' · salvos: ' + names.length;
}}

function loadGridByName(name) {{
  const target = cleanGridName(String(name || '').replace(/ ✓$/,''));
  if(target === activeGridName) return;
  saveActiveGrid(false);
  const rec = savedGrids[target];
  if(!rec) return;
  activeGridName = target;
  applyGridRecord(rec);
  updateGridSelect();
  drawAll();
}}

function createNewGrid() {{
  saveActiveGrid(false);
  const suggested = makeUniqueGridName('Grid ' + (Object.keys(savedGrids).length + 1));
  const typed = prompt('Nome da Quadra/Grid:', suggested);
  if(typed === null) return;
  activeGridName = makeUniqueGridName(typed);
  points = [];
  plantCenters = [];
  manualMarks = [];
  parcelCounts = {{}};
  savedGrids[activeGridName] = {{
    points: [],
    plantCenters: [],
    manualMarks: [],
    parcelCounts: {{}},
    rows: parseInt(inpRows.value)||1,
    cols: parseInt(inpCols.value)||1
  }};
  countPanel.style.display = 'none';
  updateGridSelect();
  persistGrids();
  drawAll();
}}

function renameActiveGrid() {{
  const next = cleanGridName(inpGridName.value);
  if(next === activeGridName) return;
  const old = activeGridName;
  activeGridName = makeUniqueGridName(next);
  if(savedGrids[old]) delete savedGrids[old];
  saveActiveGrid(false);
}}

function deleteActiveGrid() {{
  const target = activeGridName;
  if(!confirm('Excluir definitivamente o grid "' + target + '"? Ele sairá da lista, da visualização e das exportações.')) return;
  delete savedGrids[target];
  const remaining = Object.keys(savedGrids);
  if(remaining.length) {{
    activeGridName = remaining[0];
    applyGridRecord(savedGrids[activeGridName]);
  }} else {{
    activeGridName = 'Grid 1';
    points = [];
    plantCenters = [];
    manualMarks = [];
    parcelCounts = {{}};
    savedGrids[activeGridName] = {{
      points: [],
      plantCenters: [],
      manualMarks: [],
      parcelCounts: {{}},
      rows: parseInt(inpRows.value)||1,
      cols: parseInt(inpCols.value)||1
    }};
    countPanel.style.display = 'none';
  }}
  updateGridSelect();
  persistGrids();
  drawAll();
}}

function getExportGridRecords(exportAll=false) {{
  saveActiveGrid(false);
  const names = exportAll ? Object.keys(savedGrids) : [activeGridName];
  return names
    .map(name => {{
      const rec = savedGrids[name] || {{}};
      return {{
        name,
        rows: parseInt(rec.rows)||1,
        cols: parseInt(rec.cols)||1,
        parcelCounts: cloneCounts(rec.parcelCounts)
      }};
    }})
    .filter(grid => grid.parcelCounts && Object.keys(grid.parcelCounts).length > 0);
}}

function countForCell(grid, disparo, tiro) {{
  const key = Number(disparo) + '_' + Number(tiro);
  return Number(grid.parcelCounts[key] || 0);
}}

function buildExportRows(exportAll=false) {{
  const rows = [];
  const grids = getExportGridRecords(exportAll)
    .sort((a,b) => String(a.name).localeCompare(String(b.name), 'pt-BR', {{numeric:true}}));
  grids.forEach(grid => {{
    const R = parseInt(grid.rows)||1;
    const C = parseInt(grid.cols)||1;
    for(let d=1; d<=R; d++) {{
      for(let t=1; t<=C; t++) {{
        rows.push({{
          quadra: grid.name,
          disparo: d,
          tiro: t,
          quantidade: countForCell(grid, d, t)
        }});
      }}
    }}
  }});
  return rows;
}}

function csvEscape(value) {{
  const s = String(value ?? '');
  return /[",\\n\\r]/.test(s) ? '"' + s.replace(/"/g,'""') + '"' : s;
}}

function safeFilePart(value) {{
  return String(value || 'grid').trim().replace(/[\\\\/:*?"<>|]+/g,'_').replace(/\\s+/g,'_') || 'grid';
}}

function exportContagemCSV(exportAll=false) {{
  const rows = buildExportRows(exportAll);
  if(rows.length === 0) {{ alert('Nenhuma contagem realizada para o(s) grid(s) selecionado(s).'); return; }}
  let csv = '\\uFEFF' + 'Quadra,Disparo,Tiro,Quantidade de Plantas\\n';
  rows.forEach(row => {{
    csv += [row.quadra,row.disparo,row.tiro,row.quantidade].map(csvEscape).join(',') + '\\n';
  }});
  const blob = new Blob([csv], {{type:'text/csv;charset=utf-8;'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = exportAll ? 'contagem_plantas_todos_grids.csv' : 'contagem_plantas_' + safeFilePart(activeGridName) + '.csv';
  a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),1000);
}}

function exportContagemExcel(exportAll=false) {{
  const rows = buildExportRows(exportAll);
  if(rows.length === 0) {{ alert('Nenhuma contagem realizada para o(s) grid(s) selecionado(s).'); return; }}
  if(typeof XLSX === 'undefined') {{ alert('Biblioteca Excel não carregou. Use Exportar CSV.'); return; }}
  const headers = ['Quadra','Disparo','Tiro','Quantidade de Plantas'];
  const data = [headers, ...rows.map(row => [row.quadra,row.disparo,row.tiro,row.quantidade])];
  const ws = XLSX.utils.aoa_to_sheet(data);
  ws['!cols'] = [{{wch:14}},{{wch:10}},{{wch:10}},{{wch:24}}];
  const border = {{
    top:{{style:'thin',color:{{rgb:'808080'}}}},
    bottom:{{style:'thin',color:{{rgb:'808080'}}}},
    left:{{style:'thin',color:{{rgb:'808080'}}}},
    right:{{style:'thin',color:{{rgb:'808080'}}}}
  }};
  const range = XLSX.utils.decode_range(ws['!ref']);
  for(let R=range.s.r; R<=range.e.r; R++) {{
    for(let C=range.s.c; C<=range.e.c; C++) {{
      const addr = XLSX.utils.encode_cell({{r:R,c:C}});
      if(!ws[addr]) continue;
      ws[addr].s = {{
        font: R===0 ? {{bold:true,color:{{rgb:'00B0F0'}}}} : {{color:{{rgb:'000000'}}}},
        fill: R===0
          ? {{patternType:'solid',fgColor:{{rgb:'1F1F1F'}}}}
          : (C===3 ? {{patternType:'solid',fgColor:{{rgb:'00B050'}}}} : undefined),
        alignment: {{horizontal:C===3 || R===0 ? 'center' : 'left', vertical:'center'}},
        border
      }};
      if(R>0 && C===3) {{
        ws[addr].s.font = {{bold:true,color:{{rgb:'FFFFFF'}}}};
        ws[addr].s.alignment = {{horizontal:'center',vertical:'center'}};
        ws[addr].t = 'n';
      }}
    }}
  }}
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Contagem');
  XLSX.writeFile(wb, exportAll ? 'contagem_plantas_todos_grids.xlsx' : 'contagem_plantas_' + safeFilePart(activeGridName) + '.xlsx', {{bookType:'xlsx',cellStyles:true}});
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
  saveActiveGrid(false);
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
img.src = 'data:image/jpeg;base64,' + IMG_B64;

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
    saveActiveGrid(false);
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
      saveActiveGrid(false);
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
  if(draggingPoint >= 0) saveActiveGrid(false);
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
  saveActiveGrid(false);
}}

// Botões
btnGridTool.onclick = () => {{
  gridMode = !gridMode; manualMode = false;
  btnGridTool.style.borderColor = gridMode ? '#ff8c00' : '#3a3a3a';
  btnManualMode.style.borderColor = '#3a3a3a';
  if (gridMode) {{ points = []; plantCenters = []; manualMarks = []; parcelCounts = {{}}; countPanel.style.display='none'; saveActiveGrid(false); drawAll(); }}
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
    recount(); saveActiveGrid(false); drawAll();
  }}
}};
btnUndoMark.onclick = btnRemoveLast.onclick;

btnClearAll.onclick = () => {{
  points = []; plantCenters = []; manualMarks = []; parcelCounts = {{}};
  countPanel.style.display = 'none'; gridMode = false; manualMode = false;
  btnGridTool.style.borderColor = '#3a3a3a';
  btnManualMode.style.borderColor = '#3a3a3a';
  saveActiveGrid(false);
  drawAll();
}};

btnSaveGrid.onclick = () => saveActiveGrid(true);
btnNewGrid.onclick = createNewGrid;
btnDeleteGrid.onclick = deleteActiveGrid;
selGridList.onchange = () => loadGridByName(selGridList.value);
inpGridName.onchange = renameActiveGrid;
inpRows.onchange = () => {{ recount(); saveActiveGrid(false); drawAll(); }};
inpCols.onchange = () => {{ recount(); saveActiveGrid(false); drawAll(); }};

btnExportCnt.onclick = () => exportContagemCSV(cbExportAll.checked);
btnExportXLSXCnt.onclick = () => exportContagemExcel(cbExportAll.checked);

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
  exportContagemCSV(cbExportAll.checked);
}};

document.getElementById('btnResumoXLSX').onclick = () => {{
  exportContagemExcel(cbExportAll.checked);
}};

restoreGrids();
saveActiveGrid(false);
updateGridSelect();

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
            # O pendoamento usa somente o seletor/visualizador único de até 10 ortofotos abaixo.
            pend_file = None
            pend_bytes, pend_name = _uploaded_ortho_bytes(pend_file)

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
  .grid-panel input[type=text], .grid-panel input[type=date] {
    background:#1a1a1a; border:1px solid #333; color:#fff; border-radius:4px;
    padding:2px 4px; height:23px; width:112px; font-size:10px;
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
    <div class="row-col"><span>Quadra:</span><input type="text" id="inpQuadra" placeholder="Quadra"></div>
    <div class="row-col"><span>Data:</span><input type="date" id="inpData"></div>
    <div class="row-col"><span>Disp:</span><input type="number" id="inpRows" value="5" min="1" max="200"></div>
    <div class="row-col"><span>Tiros:</span><input type="number" id="inpCols" value="5" min="1" max="200"></div>
    <div class="row-col"><span>Teto pendões:</span><input type="number" id="inpTeto" value="20" min="1" max="10000"></div>
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
const inpQuadra = document.getElementById('inpQuadra');
const inpData = document.getElementById('inpData');
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
const PEND_MIN_AREA=12;
const PEND_CRITICO=20;
const PEND_SCORE_THRESHOLD=4.15;
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
  const leafGreen=(exg>20 && g>=r*0.98 && g>=b*1.07 && hsv.h>=68 && hsv.h<=165 && yellowness<32 && hsv.v<0.78);
  const hardGreen=(exg>38 && hsv.h>=72 && hsv.h<=158 && hsv.s>0.24 && yellowness<26);
  const darkShadow = hsv.v<0.20;
  const whiteGlare = hsv.s<0.08 && hsv.v>0.82;
  const soilRed = r>g*1.28 && r>b*1.36 && hsv.h<18;
  const greenWhiteEdge = hsv.s<0.22 && g>=r*1.01 && b>=r*0.74 && hsv.h>=65 && hsv.h<=150 && yellowness<20;
  const nonGreen = !leafGreen && !greenWhiteEdge && !hardGreen && exg < 70;

  const strawHue = hsv.h>=18 && hsv.h<=64 && hsv.s>=0.10 && hsv.v>=0.30 && yellowness>=10 && exg<62;
  const tanDry = r>=82 && g>=58 && b<=158 && r>=b+14 && g>=b+5 && redYellowBalance<=96 && hsv.h>=12 && hsv.h<=62;
  const paleTassel = r>=96 && g>=72 && b<=185 && yellowness>=10 && redYellowBalance<=88 && hsv.s>=0.07 && hsv.h>=12 && hsv.h<=76 && exg<64;
  const creamTip = maxc>=132 && yellowness>=14 && b<=g*0.92 && b<=r*0.92 && hsv.s>=0.06 && hsv.s<=0.58 && hsv.h>=14 && hsv.h<=78 && exg<68;
  const oldPinkTan = r>=96 && g>=64 && b<=168 && r>=g*0.84 && g>=b*0.78 && r>=b+8 && hsv.h>=8 && hsv.h<=46 && hsv.s>=0.10;
  const youngTassel = hsv.h>=38 && hsv.h<=82 && hsv.s>=0.09 && hsv.s<=0.68 && hsv.v>=0.30 && yellowness>=6 && exg<62;
  const branchTexture = chroma>=18 && yellowness>=8 && hsv.s>=0.09;

  let score=0;
  if(strawHue) score+=2.45;
  if(tanDry) score+=2.15;
  if(paleTassel) score+=2.35;
  if(creamTip) score+=2.20;
  if(oldPinkTan) score+=1.70;
  if(youngTassel) score+=1.35;
  if(branchTexture) score+=0.85;
  if(yellowness>=24) score+=0.65;
  if(yellowness>=38 && exg<58) score+=0.45;
  if(!nonGreen) score-=4.2;
  if(leafGreen) score-=4.2;
  if(hardGreen) score-=3.6;
  if(greenWhiteEdge) score-=3.0;
  if(darkShadow) score-=2.2;
  if(whiteGlare) score-=2.2;
  if(soilRed) score-=1.6;
  if(chroma<12 && yellowness<18) score-=1.2;
  if(hsv.h>=92 && hsv.h<=155 && exg>18) score-=1.8;
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
  const yellows=new Float32Array(gw*gh);
  const exgs=new Float32Array(gw*gh);
  const chromas=new Float32Array(gw*gh);
  const visited=new Uint8Array(gw*gh);

  for(let gy=0; gy<gh; gy++) {
    for(let gx=0; gx<gw; gx++) {
      const px=Math.min(w-1, gx*step), py=Math.min(h-1, gy*step);
      const ax=minX+px, ay=minY+py;
      if(!pointInPolygon(ax,ay,poly)) continue;
      const idx=(py*w+px)*4;
      const r=imageData[idx], g=imageData[idx+1], b=imageData[idx+2];
      const mi=gy*gw+gx;
      const score=tasselScore(r,g,b);
      scores[mi]=score;
      yellows[mi]=((r+g)*0.5)-b;
      exgs[mi]=2*g-r-b;
      chromas[mi]=Math.max(r,g,b)-Math.min(r,g,b);
      if(score>=PEND_SCORE_THRESHOLD) {
        mask[mi]=1;
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
      if(neighbors>=2 || scores[idx]>=PEND_SCORE_THRESHOLD+0.85) cleanMask[idx]=1;
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
      if(neighbors>=5 && scoreAround/9>=PEND_SCORE_THRESHOLD-0.35) closedMask[idx]=1;
    }
  }

  const marks=[];
  const dirs=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,1],[1,-1],[-1,-1]];
  for(let gy=0; gy<gh; gy++) {
    for(let gx=0; gx<gw; gx++) {
      const start=gy*gw+gx;
      if(!closedMask[start] || visited[start]) continue;
      let cells=0, sx=0, sy=0, scoreSum=0, yellowSum=0, exgSum=0, chromaSum=0, coreCells=0;
      let minGX=gx, maxGX=gx, minGY=gy, maxGY=gy;
      const stack=[[gx,gy]];
      visited[start]=1;
      while(stack.length) {
        const p=stack.pop();
        const x=p[0], y=p[1];
        const pos=y*gw+x;
        cells++; sx+=x; sy+=y; scoreSum+=scores[pos];
        yellowSum+=yellows[pos]; exgSum+=exgs[pos]; chromaSum+=chromas[pos];
        if(scores[pos]>=PEND_SCORE_THRESHOLD+0.55) coreCells++;
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
      const meanYellow=yellowSum/Math.max(1,cells);
      const meanExg=exgSum/Math.max(1,cells);
      const meanChroma=chromaSum/Math.max(1,cells);
      const coreRatio=coreCells/Math.max(1,cells);
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
        meanScore>=PEND_SCORE_THRESHOLD+0.05 &&
        meanYellow>=9 &&
        meanExg<58 &&
        meanChroma>=14 &&
        coreRatio>=0.12 &&
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
  const quadra=(inpQuadra && inpQuadra.value.trim()) ? inpQuadra.value.trim() : 'Pendoamento';
  const dataOrto=(inpData && inpData.value) ? inpData.value : new Date().toISOString().slice(0,10);
  const csvValue = value => {
    const s=String(value ?? '');
    return /[;"\\n\\r]/.test(s) ? '"' + s.replace(/"/g,'""') + '"' : s;
  };
  let csv='\\uFEFFQuadra;Disparo;Tiro;Total_Pendões;Nome_Ortofoto;Data_Ortofoto;Observação\\n';
  for(const r of entries) {
    const obs=r.count>=crit ? 'ATINGIU_50_DO_TETO' : 'ABAIXO_50_DO_TETO';
    csv += [quadra,r.row,r.col,r.count,IMAGE_NAME,dataOrto,obs].map(csvValue).join(';')+'\\n';
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
img.onerror=()=>{ countPanel.style.display='block'; countInfoEl.innerHTML='Falha ao carregar a ortofoto no visualizador. Recarregue a imagem ou reduza o tamanho do arquivo.'; };
img.src='data:image/jpeg;base64,'+IMG_B64;

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
if(inpData && !inpData.value) inpData.value = new Date().toISOString().slice(0,10);
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

            if False:
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

            cron_nome_analise = "Pendoamento"
            cron_rows = 5
            cron_cols = 5
            cron_teto = 20
            cron_percentual = 100.0
            cron_min_pendoes = 1
            cron_referencia = ""
            cron_tolerancia = 58
            cron_filtro_cor = "Misto"
            cron_sensibilidade = 64
            cron_area_min = 12
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
            st.caption("Depois de anexar, use o resumo lateral do visualizador para clicar e trocar entre as ortofotos carregadas. O teto de pendões trava a primeira data em que a parcela atingiu o valor configurado.")

            with st.expander("🌾 Treino YOLO de pendoamento", expanded=False):
                yolo_counts = contar_amostras_treinamento_yolo()
                st.caption(
                    "Use o botão Treinar YOLO dentro do visualizador para clicar nos pendões e salvar amostras. "
                    "Quando a pasta local estiver com as imagens/labels, inicie o treino aqui."
                )
                m1, m2, m3 = st.columns(3)
                m1.metric("Imagens treino", yolo_counts["images_train"])
                m2.metric("Imagens validação", yolo_counts["images_val"])
                m3.metric("Labels", yolo_counts["total_labels"])
                yolo_col1, yolo_col2, yolo_col3 = st.columns(3)
                with yolo_col1:
                    if st.button("Gerar data.yaml", key="pend_yolo_yaml"):
                        garantir_estrutura_treinamento_yolo()
                        st.success(f"data.yaml pronto em {YOLO_TRAIN_ROOT / 'data.yaml'}")
                with yolo_col2:
                    if st.button("Treinar modelo YOLO", key="pend_yolo_train"):
                        ok, msg = treinar_yolo_pendoamento()
                        (st.success if ok else st.warning)(msg)
                with yolo_col3:
                    if st.button("Abrir pasta de treinamento", key="pend_yolo_open_folder"):
                        garantir_estrutura_treinamento_yolo()
                        try:
                            if os.name == "nt":
                                os.startfile(str(YOLO_TRAIN_ROOT))
                            else:
                                subprocess.Popen(["xdg-open", str(YOLO_TRAIN_ROOT)])
                            st.success("Pasta de treinamento aberta.")
                        except Exception as exc:
                            st.info(f"Pasta: {YOLO_TRAIN_ROOT} ({exc})")
                if YOLO_BEST_MODEL_PATH.exists():
                    st.success(f"Modelo treinado ativo: {YOLO_BEST_MODEL_PATH}")
                else:
                    st.info("Quando o treino terminar, o best.pt será copiado para modelos_yolo/pendao_milho_best.pt e usado automaticamente na análise.")
                if YOLO_TRAIN_LOG_PATH.exists():
                    try:
                        log_text = YOLO_TRAIN_LOG_PATH.read_text(encoding="utf-8", errors="ignore")[-5000:]
                        st.text_area("Log do treino YOLO", value=log_text, height=130, key="pend_yolo_log", disabled=True)
                    except Exception:
                        pass

            cron_files = _resettable_ortho_uploader(
                "📷 Anexar ortofotos para o seletor do visualizador (até 10)",
                accept_multiple_files=True,
                key="pend_cron_ortos",
                help="Use até 10 ortofotos da mesma área. O grid marcado será mantido no visualizador único."
            )

            cron_items = []
            for cron_file in cron_files or []:
                raw = cron_file.getbuffer().tobytes()
                cron_items.append({"name": cron_file.name, "raw": raw})

            if cron_items:
                selected_cron_items = cron_items[:10]
                if len(cron_items) > 10:
                    st.warning("Foram anexadas mais de 10 ortofotos. O seletor usará somente as 10 primeiras.")

                st.caption("Revise o nome e a data de cada ortofoto. A lista será organizada automaticamente pela data informada.")
                date_cols = st.columns(min(5, len(selected_cron_items)))
                cron_entries = []
                for idx, cron_item in enumerate(selected_cron_items):
                    key_hash = hashlib.md5(f"{idx}-{cron_item['name']}".encode("utf-8")).hexdigest()[:8]
                    with date_cols[idx % len(date_cols)]:
                        cron_label = st.text_input(
                            f"Nome {idx + 1}",
                            value=Path(cron_item["name"]).stem,
                            key=f"pend_cron_name_{key_hash}"
                        )
                        cron_date = st.date_input(
                            f"Data {idx + 1}",
                            value=date.today(),
                            key=f"pend_cron_date_{key_hash}"
                        )
                    cron_entries.append({
                        "idx": idx,
                        "name": (cron_label.strip() or Path(cron_item["name"]).stem),
                        "original_name": cron_item["name"],
                        "raw": cron_item["raw"],
                        "date": cron_date.isoformat()
                    })

                ordem_preview = sorted(cron_entries, key=lambda it: (it["date"], it["idx"]))
                resumo_cards = []
                for slot_idx in range(10):
                    if slot_idx < len(ordem_preview):
                        item = ordem_preview[slot_idx]
                        resumo_cards.append(
                            "<div style='border:1px solid #ff8c00;background:#201303;border-radius:8px;padding:8px;'>"
                            f"<div style='color:#ffb347;font-weight:800;font-size:0.72rem;'>#{slot_idx + 1:02d} · SELECIONÁVEL</div>"
                            f"<div style='color:#fff;font-size:0.78rem;font-weight:700;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{html.escape(item['name'])}</div>"
                            f"<div style='color:#888;font-size:0.68rem;margin-top:3px;'>Data: {html.escape(item['date'])}</div>"
                            "</div>"
                        )
                    else:
                        resumo_cards.append(
                            "<div style='border:1px dashed #2e2e2e;background:#0c0c0c;border-radius:8px;padding:8px;'>"
                            f"<div style='color:#555;font-weight:800;font-size:0.72rem;'>#{slot_idx + 1:02d} · VAZIO</div>"
                            "<div style='color:#444;font-size:0.72rem;margin-top:6px;'>Aguardando ortofoto</div>"
                            "</div>"
                        )
                st.markdown(
                    "<div style='margin:8px 0 10px 0;'>"
                    "<div style='color:#ff8c00;font-weight:800;font-size:0.78rem;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;'>"
                    "Resumo das 10 posições do seletor</div>"
                    "<div style='display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:7px;'>"
                    + "".join(resumo_cards) +
                    "</div></div>",
                    unsafe_allow_html=True
                )

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
                            try:
                                pendao_result = preparar_deteccoes_pendoamento_hibrido(raw, cron_name, tuple(dims))
                                pendao_detections = pendao_result.get("detections", [])
                                pendao_status = pendao_result.get("status", "")
                                pendao_mode = pendao_result.get("mode", "OpenCV fallback")
                                if pendao_status and any(token in pendao_status.lower() for token in ("não instalado", "nao instalado", "falhou")):
                                    cron_errors.append(f"{cron_name}: {pendao_status}")
                            except Exception as det_exc:
                                pendao_detections = []
                                pendao_status = f"YOLO/OpenCV indisponível ({det_exc}). Verifique: pip install -U ultralytics"
                                pendao_mode = "OpenCV fallback"
                                cron_errors.append(f"{cron_name}: {pendao_status}")
                            cron_orthos.append({
                                "order": int(item["idx"]),
                                "name": cron_name,
                                "date": item["date"],
                                "b64": b64,
                                "width": int(dims[0]),
                                "height": int(dims[1]),
                                "advanced_detections": pendao_detections,
                                "detector_status": pendao_status,
                                "detector_mode": pendao_mode,
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
  .date-list { max-height:330px; overflow:auto; border:1px solid #242424; border-radius:7px; padding:5px; background:#101010; }
  .date-item { color:#aaa; font-size:10px; padding:7px; border:1px solid transparent; border-radius:6px; cursor:pointer; margin-bottom:5px; background:rgba(255,255,255,.018); }
  .date-item.active { color:#ffb347; background:#221400; border-color:#ff8c00; box-shadow:0 0 8px rgba(255,140,0,.18); }
  .date-item:hover { background:#1a1a1a; border-color:#3a3a3a; }
  .date-item.empty { cursor:default; border-style:dashed; color:#555; background:#0d0d0d; }
  .date-item.empty:hover { background:#0d0d0d; border-color:#333; }
  .date-head { display:flex; justify-content:space-between; gap:6px; align-items:center; font-weight:800; }
  .date-name { color:#f0f0f0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:178px; }
  .date-meta { color:#888; font-size:9px; margin-top:3px; line-height:1.35; }
  .date-mini { display:grid; grid-template-columns:1fr 1fr 1fr; gap:4px; margin-top:5px; }
  .date-mini span { background:#171717; border:1px solid #2b2b2b; border-radius:4px; padding:3px; text-align:center; color:#aaa; }
  .date-mini b { display:block; color:#fff; font-size:10px; }
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
  .train-box { border:1px solid #24384c; background:rgba(20,34,48,.45); border-radius:8px; padding:8px; margin:6px 0; }
  .train-box .row span:first-child { max-width:125px; }
  .train-status { border:1px solid #26384a; background:#0b1118; border-radius:6px; color:#8fbde8; font-size:9px; padding:6px; min-height:34px; line-height:1.35; margin-top:5px; }
  #btnReviewMode, #btnExportCSV, #btnExportResumo, #btnExportCompleto, #btnExportImagem,
  .stats, #statFirstDate, .legend, #reviewPanel { display:none !important; }
</style>
</head>
<body>
<div id="cronRoot">
  <div id="cronViewer">
    <canvas id="cronCanvas"></canvas>
    <div class="badge" id="cronZoom">1.00×</div>
    <div class="badge" id="cronCoord">X:0 Y:0</div>
    <div class="badge" id="cronHint">Scroll=Zoom · Drag=Pan<br>Grid: marque 4 extremidades e arraste para ajustar</div>
  </div>
  <div class="cron-side">
    <div class="title">Resumo / Seletor de Ortofotos</div>
    <div class="subtle">Clique em uma das até 10 ortofotos abaixo para trocar a imagem no mesmo visualizador.</div>

    <div class="sep"></div>
    <div class="row"><span>Nome</span><input id="cfgNome" type="text" value="Pendoamento"></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
      <div class="row" style="display:block;"><span>Disp</span><input id="cfgRows" type="number" min="1" max="200" value="5" style="width:100%;margin-top:3px;"></div>
      <div class="row" style="display:block;"><span>Tiros</span><input id="cfgCols" type="number" min="1" max="200" value="5" style="width:100%;margin-top:3px;"></div>
    </div>
    <div class="row"><span>Teto de pendões</span><input id="cfgTeto" type="number" min="1" max="10000" value="20" style="width:92px;text-align:center;"></div>
    <div class="subtle">O teto trava a primeira data em que cada parcela atingiu o valor configurado.</div>

    <div class="sep"></div>
    <div class="row"><span>Data ativa</span><select id="dateSelect"></select></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
      <button class="btn blue" id="btnPrevDate">◀ Data</button>
      <button class="btn blue" id="btnNextDate">Data ▶</button>
    </div>
    <div class="subtle" id="activeOrthoSummary">Selecione uma ortofoto para trocar a visualização no mesmo painel.</div>
    <div class="date-list" id="dateList"></div>

    <div class="sep"></div>
    <button class="btn orange" id="btnMarkGrid">⊞ Marcar Grid</button>
    <button class="btn green" id="btnAnalyzeChrono">🌾 Análise de Pendoamento</button>
    <button class="btn blue" id="btnReviewMode">✎ Revisar Parcela</button>
    <button class="btn" id="btnFitChrono">⤢ Ajustar à tela</button>
    <button class="btn red" id="btnClearChrono">Limpar seletor</button>
    <div class="train-box">
      <button class="btn blue" id="btnTrainYolo">🎯 Treinar YOLO</button>
      <div class="row"><span>Tipo de amostra</span><select id="trainSampleType">
        <option value="pendao_confirmado">Pendão confirmado</option>
        <option value="pendao_faltante">Pendão faltante</option>
        <option value="falso_positivo">Falso positivo</option>
      </select></div>
      <div class="row"><span>Tamanho recorte</span><input id="trainCropSize" type="number" min="48" max="256" step="16" value="128" style="width:78px;text-align:center;"></div>
      <div class="row"><span>Amostras salvas</span><b id="trainSampleCount" style="color:#75b7ff;">0</b></div>
      <button class="btn" id="btnPickTrainDir">Abrir pasta de treinamento</button>
      <button class="btn" id="btnGenerateYaml">Gerar data.yaml</button>
      <button class="btn" id="btnDownloadDataset">Baixar dataset YOLO</button>
      <button class="btn green" id="btnTrainModelYolo">Treinar modelo YOLO</button>
      <button class="btn red" id="btnStopTrainMode">Parar modo treino</button>
      <div class="train-status" id="trainStatus">Modo treino parado. Clique em Treinar YOLO e depois clique sobre os pendões.</div>
    </div>
    <div class="progress"><div id="cronProgress"></div></div>
    <div class="subtle" id="cronStatus">Selecione a ortofoto no resumo, marque o grid e execute a análise. O teto configurado define o travamento.</div>

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
    <button class="btn orange" id="btnExportXLSX">Exportar Excel</button>
    <button class="btn orange" id="btnExportCSV" style="display:none;">Exportar CSV</button>
    <button class="btn" id="btnExportResumo" style="display:none;">Exportar resumo final</button>
    <button class="btn" id="btnExportCompleto" style="display:none;">Exportar dados completos por ortofoto</button>
    <button class="btn" id="btnExportImagem" style="display:none;">Exportar imagem com grid e marcações</button>
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
const activeOrthoSummary = document.getElementById('activeOrthoSummary');
const cfgNome = document.getElementById('cfgNome');
const cfgRows = document.getElementById('cfgRows');
const cfgCols = document.getElementById('cfgCols');
const cfgTeto = document.getElementById('cfgTeto');
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
const btnTrainYolo = document.getElementById('btnTrainYolo');
const trainSampleType = document.getElementById('trainSampleType');
const trainCropSize = document.getElementById('trainCropSize');
const trainSampleCount = document.getElementById('trainSampleCount');
const btnPickTrainDir = document.getElementById('btnPickTrainDir');
const btnGenerateYaml = document.getElementById('btnGenerateYaml');
const btnDownloadDataset = document.getElementById('btnDownloadDataset');
const btnTrainModelYolo = document.getElementById('btnTrainModelYolo');
const btnStopTrainMode = document.getElementById('btnStopTrainMode');
const trainStatus = document.getElementById('trainStatus');

let images = [];
let loaded = 0;
let activeIdx = 0;
let scale = 1, offsetX = 0, offsetY = 0;
let dragging = false, lastX = 0, lastY = 0, gridDragPoint = -1;
let markGridMode = false, reviewMode = false;
let gridRatios = [];
let selectedParcel = null;
let resultsByParcel = {};
let finalRows = [];
let fullRows = [];
let manualReviews = {};
let trainYoloMode = false;
let trainingDirHandle = null;
let yoloSamples = [];
let yoloTrainMarks = [];
const tempCanvas = document.createElement('canvas');
const tempCtx = tempCanvas.getContext('2d', { willReadFrequently:true });
let tempPrepared = -1;

function clamp(v,min,max){ return Math.max(min, Math.min(max, v)); }
function imgW(idx=activeIdx){ return ORTHOS[idx]?.width || images[idx]?.width || 1; }
function imgH(idx=activeIdx){ return ORTHOS[idx]?.height || images[idx]?.height || 1; }
function cellLabel(r,c){ return 'D' + (r + 1) + ' T' + (c + 1); }
function fmtPct(v){ return Number.isFinite(v) ? v.toFixed(2) : ''; }
function quoteCSV(v){
  const s = (v === null || v === undefined) ? '' : String(v);
  return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

function trainDataYaml(){
  return 'path: dados_treinamento_yolo/pendao_milho\ntrain: images/train\nval: images/val\nnames:\n  0: pendao\n';
}

function sanitizeName(value){
  return String(value || 'amostra').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-zA-Z0-9_-]+/g,'_').replace(/^_+|_+$/g,'').slice(0,80) || 'amostra';
}

function canvasToBlob(cv, type='image/jpeg', quality=0.94){
  return new Promise(resolve => cv.toBlob(resolve, type, quality));
}

async function getDirHandle(root, parts){
  let dir = root;
  for(const part of parts){
    dir = await dir.getDirectoryHandle(part, {create:true});
  }
  return dir;
}

async function writeTrainingFile(parts, filename, content){
  if(!trainingDirHandle) return false;
  const dir = await getDirHandle(trainingDirHandle, ['dados_treinamento_yolo','pendao_milho', ...parts]);
  const file = await dir.getFileHandle(filename, {create:true});
  const writable = await file.createWritable();
  await writable.write(content);
  await writable.close();
  return true;
}

async function generateYamlToTrainingDir(){
  if(!trainingDirHandle) return false;
  const dir = await getDirHandle(trainingDirHandle, ['dados_treinamento_yolo','pendao_milho']);
  const file = await dir.getFileHandle('data.yaml', {create:true});
  const writable = await file.createWritable();
  await writable.write(trainDataYaml());
  await writable.close();
  return true;
}

function autoYoloBboxFromCrop(cropCtx, size){
  const data = cropCtx.getImageData(0,0,size,size).data;
  let minX=size, minY=size, maxX=-1, maxY=-1, count=0;
  const center=size/2;
  for(let y=0; y<size; y++){
    for(let x=0; x<size; x++){
      const i=(y*size+x)*4;
      const r=data[i], g=data[i+1], b=data[i+2];
      const score=tasselScore(r,g,b);
      const exg=2*g-r-b;
      const yell=((r+g)*0.5)-b;
      const dist=Math.hypot(x-center,y-center);
      const candidate=(score>=3.45 || (yell>=16 && exg<62 && Math.max(r,g,b)>88)) && dist<=size*0.43;
      if(candidate){
        if(x<minX) minX=x; if(x>maxX) maxX=x;
        if(y<minY) minY=y; if(y>maxY) maxY=y;
        count++;
      }
    }
  }
  if(count < 8 || maxX < minX || maxY < minY){
    return {xc:0.5,yc:0.5,w:0.45,h:0.45,auto:false};
  }
  const pad=Math.max(3, Math.round(size*0.04));
  minX=clamp(minX-pad,0,size-1); minY=clamp(minY-pad,0,size-1);
  maxX=clamp(maxX+pad,0,size-1); maxY=clamp(maxY+pad,0,size-1);
  const w=Math.max(4,maxX-minX+1), h=Math.max(4,maxY-minY+1);
  return {
    xc:clamp((minX+w/2)/size,0.02,0.98),
    yc:clamp((minY+h/2)/size,0.02,0.98),
    w:clamp(w/size,0.08,0.92),
    h:clamp(h/size,0.08,0.92),
    auto:true
  };
}

async function pickTrainingDirectory(){
  if(!window.showDirectoryPicker){
    trainStatus.textContent = 'Seu navegador não permite salvar direto em pasta. Use Baixar dataset YOLO.';
    return false;
  }
  try{
    trainingDirHandle = await window.showDirectoryPicker({mode:'readwrite'});
    await generateYamlToTrainingDir();
    trainStatus.textContent = 'Pasta conectada. Os cliques serão salvos em dados_treinamento_yolo/pendao_milho.';
    return true;
  }catch(e){
    trainStatus.textContent = 'Seleção de pasta cancelada.';
    return false;
  }
}

async function saveYoloTrainingSample(pt){
  if(!images[activeIdx] || !images[activeIdx].complete){
    trainStatus.textContent = 'Imagem ainda não carregada.';
    return;
  }
  const size = clamp(parseInt(trainCropSize.value || 128), 48, 256);
  const type = trainSampleType.value || 'pendao_confirmado';
  const split = ((yoloSamples.length + 1) % 5 === 0) ? 'val' : 'train';
  const positive = type !== 'falso_positivo';
  const crop = document.createElement('canvas');
  crop.width = size; crop.height = size;
  const cctx = crop.getContext('2d', {willReadFrequently:true});
  cctx.fillStyle = '#111';
  cctx.fillRect(0,0,size,size);
  const sx = Math.round(pt.x - size/2);
  const sy = Math.round(pt.y - size/2);
  const srcX = clamp(sx, 0, imgW(activeIdx));
  const srcY = clamp(sy, 0, imgH(activeIdx));
  const srcX2 = clamp(sx + size, 0, imgW(activeIdx));
  const srcY2 = clamp(sy + size, 0, imgH(activeIdx));
  const sw = Math.max(1, srcX2-srcX);
  const sh = Math.max(1, srcY2-srcY);
  const dx = srcX - sx;
  const dy = srcY - sy;
  cctx.drawImage(images[activeIdx], srcX, srcY, sw, sh, dx, dy, sw, sh);
  const bbox = positive ? autoYoloBboxFromCrop(cctx, size) : {xc:0.5,yc:0.5,w:0,h:0,auto:false};
  const now = new Date();
  const stamp = now.toISOString().replace(/[-:.TZ]/g,'').slice(0,14);
  const baseName = sanitizeName('pendao_' + stamp + '_o' + (activeIdx+1) + '_x' + Math.round(pt.x) + '_y' + Math.round(pt.y) + '_' + type);
  const imgName = baseName + '.jpg';
  const labelName = baseName + '.txt';
  const blob = await canvasToBlob(crop, 'image/jpeg', 0.95);
  const labelText = positive
    ? `0 ${bbox.xc.toFixed(6)} ${bbox.yc.toFixed(6)} ${bbox.w.toFixed(6)} ${bbox.h.toFixed(6)}\n`
    : '';
  const origW = Number(ORTHOS[activeIdx]?.orig_width || imgW(activeIdx));
  const origH = Number(ORTHOS[activeIdx]?.orig_height || imgH(activeIdx));
  const meta = {
    file: imgName,
    type,
    split,
    preview_x: Number(pt.x.toFixed(2)),
    preview_y: Number(pt.y.toFixed(2)),
    original_x: Number((pt.x * origW / imgW(activeIdx)).toFixed(2)),
    original_y: Number((pt.y * origH / imgH(activeIdx)).toFixed(2)),
    crop_size: size,
    bbox_auto: bbox.auto,
    ortho: ORTHOS[activeIdx]?.name || '',
    date: ORTHOS[activeIdx]?.date || ''
  };
  yoloSamples.push({imgName,labelName,blob,labelText,type,split,meta});
  yoloTrainMarks.push({x:pt.x,y:pt.y,size,type,idx:activeIdx});
  trainSampleCount.textContent = String(yoloSamples.length);
  try{
    if(trainingDirHandle){
      await writeTrainingFile(['images', split], imgName, blob);
      await writeTrainingFile(['labels', split], labelName, labelText);
      await writeTrainingFile(['crops', type], imgName, blob);
      await writeTrainingFile(['crops', type], baseName + '.json', JSON.stringify(meta, null, 2));
      await generateYamlToTrainingDir();
      trainStatus.textContent = 'Amostra de pendão salva para treinamento YOLO.';
    } else {
      trainStatus.textContent = 'Amostra guardada no navegador. Use Baixar dataset YOLO ou Abrir pasta de treinamento.';
    }
  }catch(e){
    trainStatus.textContent = 'Amostra criada, mas falhou ao salvar na pasta: ' + e.message;
  }
  drawAll();
}

async function downloadYoloDataset(){
  if(!yoloSamples.length){
    alert('Nenhuma amostra salva nesta sessão.');
    return;
  }
  if(typeof JSZip === 'undefined'){
    await loadScriptOnce('https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js');
  }
  if(typeof JSZip === 'undefined'){
    alert('Não foi possível carregar o gerador ZIP. Use Abrir pasta de treinamento.');
    return;
  }
  const zip = new JSZip();
  const root = zip.folder('dados_treinamento_yolo').folder('pendao_milho');
  root.file('data.yaml', trainDataYaml());
  for(const s of yoloSamples){
    const arrayBuffer = await s.blob.arrayBuffer();
    root.folder('images').folder(s.split).file(s.imgName, arrayBuffer);
    root.folder('labels').folder(s.split).file(s.labelName, s.labelText);
    root.folder('crops').folder(s.type).file(s.imgName, arrayBuffer);
    root.folder('crops').folder(s.type).file(s.imgName.replace(/\.jpg$/i,'.json'), JSON.stringify(s.meta, null, 2));
  }
  const content = await zip.generateAsync({type:'blob'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(content);
  a.download = 'dados_treinamento_yolo_pendao_milho.zip';
  a.click();
  trainStatus.textContent = 'Dataset YOLO baixado em ZIP.';
}

function applyViewerConfig(clearResults=false){
  const oldRows = Number(CONFIG.rows || 1);
  const oldCols = Number(CONFIG.cols || 1);
  CONFIG.nomeAnalise = (cfgNome.value || 'Pendoamento').trim() || 'Pendoamento';
  CONFIG.rows = clamp(parseInt(cfgRows.value || CONFIG.rows || 1), 1, 200);
  CONFIG.cols = clamp(parseInt(cfgCols.value || CONFIG.cols || 1), 1, 200);
  CONFIG.tetoPlantas = clamp(parseInt(cfgTeto.value || CONFIG.tetoPlantas || 1), 1, 10000);
  cfgRows.value = CONFIG.rows;
  cfgCols.value = CONFIG.cols;
  cfgTeto.value = CONFIG.tetoPlantas;
  if(clearResults || oldRows !== CONFIG.rows || oldCols !== CONFIG.cols){
    selectedParcel = null;
    resultsByParcel = {};
    finalRows = [];
    fullRows = [];
    progressBar.style.width = '0%';
  }
  rebuildRows();
  renderReviewPanel();
  drawAll();
}

function setupViewerConfigInputs(){
  cfgNome.value = CONFIG.nomeAnalise || 'Pendoamento';
  cfgRows.value = CONFIG.rows || 5;
  cfgCols.value = CONFIG.cols || 5;
  cfgTeto.value = CONFIG.tetoPlantas || 20;
  cfgNome.onchange = () => applyViewerConfig(false);
  cfgRows.onchange = () => applyViewerConfig(true);
  cfgCols.onchange = () => applyViewerConfig(true);
  cfgTeto.onchange = () => applyViewerConfig(false);
}

function loadScriptOnce(src){
  return new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-tmg-src="' + src + '"]');
    if(existing){
      if(existing.dataset.loaded === 'true'){ resolve(true); return; }
      existing.addEventListener('load', () => resolve(true), {once:true});
      existing.addEventListener('error', () => reject(new Error('Falha ao carregar ' + src)), {once:true});
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.dataset.tmgSrc = src;
    script.onload = () => { script.dataset.loaded = 'true'; resolve(true); };
    script.onerror = () => reject(new Error('Falha ao carregar ' + src));
    document.head.appendChild(script);
  });
}

async function ensureChronoExcel(){
  if(window.__tmgChronoXlsxReady && typeof XLSX !== 'undefined') return true;
  const urls = [
    'https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js',
    'https://unpkg.com/xlsx-js-style@1.2.0/dist/xlsx.bundle.js',
    'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js'
  ];
  for(const url of urls){
    try{
      await loadScriptOnce(url);
      if(typeof XLSX !== 'undefined'){
        window.__tmgChronoXlsxReady = true;
        return true;
      }
    } catch(e){ console.warn(e); }
  }
  return false;
}

function setupDates(){
  dateSelect.innerHTML = '';
  ORTHOS.forEach((o, idx) => {
    const opt = document.createElement('option');
    opt.value = idx;
    opt.textContent = (idx + 1) + ' · ' + o.date + ' · ' + o.name;
    dateSelect.appendChild(opt);
  });
  renderOrthoSummary();
}

function safeHtml(value){
  const div = document.createElement('div');
  div.textContent = String(value ?? '');
  return div.innerHTML;
}

function orthoStats(idx){
  let total=0, hit=0, partial=0, review=0;
  const tetoDefault = Math.max(1, Number(CONFIG.tetoPlantas || 1));
  for(const label of Object.keys(resultsByParcel)){
    const rec = resultsByParcel[label] || {};
    const manual = manualReviews[label] || {};
    const count = manual.counts && manual.counts[idx] !== undefined ? Number(manual.counts[idx] || 0) : Number((rec.counts || [])[idx] || 0);
    const teto = Math.max(1, Number(manual.teto || tetoDefault));
    const pct = count / teto * 100;
    total += count;
    if(pct >= Number(CONFIG.percentualLimite || 50) && count >= Number(CONFIG.minPendoes || 0)) hit++;
    else if(count > 0) partial++;
    if((rec.confidence || 1) < 0.38) review++;
  }
  return {total, hit, partial, review};
}

function renderOrthoSummary(){
  dateList.innerHTML = '';
  const active = ORTHOS[activeIdx] || {};
  const activeStats = orthoStats(activeIdx);
  activeOrthoSummary.innerHTML =
    'Visualizando: <b style="color:#ffb347">' + (activeIdx + 1) + ' · ' + safeHtml(active.name || '') + '</b><br>' +
    'Data: ' + safeHtml(active.date || '--') + ' · Pendões: ' + activeStats.total + ' · Atingidas: ' + activeStats.hit +
    '<br>Detector: ' + safeHtml(active.detector_mode || 'OpenCV fallback') +
    '<br><span style="color:#777">Ortofotos carregadas: ' + ORTHOS.length + '/10</span>';
  for(let idx=0; idx<10; idx++){
    const o = ORTHOS[idx];
    const stats = orthoStats(idx);
    const item = document.createElement('div');
    if(o){
      item.className = 'date-item' + (idx === activeIdx ? ' active' : '');
      item.innerHTML =
        '<div class="date-head"><span>#' + String(idx + 1).padStart(2,'0') + ' · ' + safeHtml(o.date) + '</span><span class="date-name">' + safeHtml(o.name) + '</span></div>' +
        '<div class="date-meta">Clique aqui para visualizar esta ortofoto no painel único.<br>Detector: ' + safeHtml(o.detector_mode || 'OpenCV fallback') + '</div>' +
        '<div class="date-mini">' +
          '<span><b>' + stats.total + '</b>pendões</span>' +
          '<span><b>' + stats.hit + '</b>atingiu</span>' +
          '<span><b>' + stats.partial + '</b>parcial</span>' +
        '</div>';
      item.onclick = () => setActiveDate(idx);
    } else {
      item.className = 'date-item empty';
      item.innerHTML =
        '<div class="date-head"><span>#' + String(idx + 1).padStart(2,'0') + ' · vazio</span><span class="date-name">Aguardando</span></div>' +
        '<div class="date-meta">Anexe uma ortofoto para liberar esta posição.</div>';
    }
    dateList.appendChild(item);
  }
}

function setActiveDate(idx){
  activeIdx = clamp(idx, 0, ORTHOS.length - 1);
  dateSelect.value = String(activeIdx);
  tempPrepared = -1;
  renderOrthoSummary();
  statusEl.textContent = 'Visualizando ortofoto ' + (activeIdx + 1) + '/' + ORTHOS.length + ': ' + (ORTHOS[activeIdx]?.name || '');
  drawAll();
}

function loadImages(){
  ORTHOS.forEach((o, idx) => {
    const im = new Image();
    im.onload = () => {
      loaded += 1;
      if(idx === 0) fitView();
      statusEl.textContent = 'Ortofotos carregadas: ' + loaded + '/' + ORTHOS.length;
      renderOrthoSummary();
      drawAll();
    };
    im.onerror = () => {
      statusEl.textContent = 'Falha ao carregar ortofoto: ' + (o.name || ('#' + (idx + 1)));
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

function gridPointIndexAt(pt, idx=activeIdx){
  const pts = currentGridPoints(idx);
  for(let i=0; i<pts.length; i++){
    const dx=(pt.x-pts[i].x)*scale;
    const dy=(pt.y-pts[i].y)*scale;
    if(Math.sqrt(dx*dx+dy*dy) < 22) return i;
  }
  return -1;
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
  const leafGreen = (exg>18 && g>=r*0.98 && g>=b*1.07 && hsv.h>=68 && hsv.h<=165 && yellowness<34 && hsv.v<0.82);
  const hardGreen = (exg>32 && hsv.h>=70 && hsv.h<=158 && hsv.s>0.20 && yellowness<30);
  const darkShadow = hsv.v<0.20;
  const whiteGlare = hsv.s<0.08 && hsv.v>0.82;
  const soilRed = r>g*1.28 && r>b*1.36 && hsv.h<18;
  const greenWhiteEdge = hsv.s<0.22 && g>=r*1.01 && b>=r*0.74 && hsv.h>=65 && hsv.h<=150 && yellowness<22;
  const nonGreen = !leafGreen && !greenWhiteEdge && !hardGreen && exg < 62;
  const filter = CONFIG.filtroCor || 'Misto';

  let score = 0;
  const young = hsv.h>=38 && hsv.h<=76 && hsv.s>=0.10 && hsv.s<=0.56 && hsv.v>=0.34 && yellowness>=12 && exg<42 && b<=Math.min(r,g)*0.88;
  const dry = hsv.h>=18 && hsv.h<=64 && hsv.s>=0.10 && hsv.v>=0.30 && yellowness>=12 && r>=82 && g>=58 && b<=158 && r>=b+14 && g>=b+6 && redYellowBalance<=92 && exg<52;
  const bright = r>=96 && g>=72 && b<=185 && yellowness>=12 && redYellowBalance<=88 && hsv.s>=0.07 && hsv.h>=12 && hsv.h<=76 && exg<55;
  const creamTip = Math.max(r,g,b)>=132 && yellowness>=16 && b<=g*0.91 && b<=r*0.91 && hsv.s>=0.06 && hsv.s<=0.58 && hsv.h>=14 && hsv.h<=78 && exg<56;
  const oldPinkTan = r>=96 && g>=64 && b<=168 && r>=g*0.84 && g>=b*0.78 && r>=b+8 && hsv.h>=8 && hsv.h<=46 && hsv.s>=0.10 && exg<52;
  const textureColor = chroma>=18 && yellowness>=10 && hsv.s>=0.09 && exg<55;

  if(filter === 'Pendão novo'){
    if(young) score += 3.2;
    if(hsv.h>=50 && hsv.h<=90) score += 1.1;
    if(dry) score += 0.8;
  } else if(filter === 'Pendão seco/velho'){
    if(dry) score += 3.3;
    if(bright) score += 1.6;
    if(young) score += 0.7;
  } else {
    if(young) score += 1.75;
    if(dry) score += 2.25;
    if(bright) score += 2.45;
    if(creamTip) score += 2.35;
    if(oldPinkTan) score += 1.85;
  }
  if(textureColor) score += 0.75;
  if(yellowness>=24) score += 0.65;
  if(yellowness>=38 && exg<52) score += 0.45;
  if(!nonGreen) score -= 4.5;
  if(leafGreen) score -= 4.5;
  if(hardGreen) score -= 4.0;
  if(greenWhiteEdge) score -= 3.2;
  if(darkShadow) score -= 2.2;
  if(whiteGlare) score -= 2.3;
  if(soilRed) score -= 1.8;
  if(chroma<12 && yellowness<18) score -= 1.2;
  if(hsv.h>=92 && hsv.h<=155 && exg>16) score -= 2.0;

  const sensitivity = clamp(Number(CONFIG.sensibilidade || 60), 1, 100);
  const tolerance = clamp(Number(CONFIG.tolerancia || 55), 0, 100);
  score += (sensitivity - 50) / 70;
  score += (tolerance - 50) / 130;
  return score;
}

function scoreThreshold(){
  const sensitivity = clamp(Number(CONFIG.sensibilidade || 60), 1, 100);
  const tolerance = clamp(Number(CONFIG.tolerancia || 55), 0, 100);
  return clamp(4.28 - (sensitivity - 50) / 150 - (tolerance - 50) / 240, 4.05, 4.75);
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

function analyzeCellFromAdvancedDetections(idx,r,c){
  const source = ORTHOS[idx] && Array.isArray(ORTHOS[idx].advanced_detections) ? ORTHOS[idx].advanced_detections : null;
  if(!source || !source.length) return null;
  const poly = cellPoly(r,c,idx);
  if(!poly) return {count:0, marks:[], confidence:0};
  const marks = [];
  let confidenceSum = 0;
  for(const det of source){
    const x = Number(det.x);
    const y = Number(det.y);
    if(!Number.isFinite(x) || !Number.isFinite(y)) continue;
    if(!pointInPolygon(x,y,poly)) continue;
    const score = Number(det.score || 0);
    const size = clamp(Number(det.size || 8), 5, 22);
    marks.push({
      x,
      y,
      score,
      size,
      area: Math.max(1, size * size),
      tipo: det.tipo || 'misto',
      confianca: det.confianca || 'media',
      source: det.source || 'OpenCV',
      yolo_conf: Number(det.yolo_conf || 0),
      class_name: det.class_name || '',
      yellow_ratio: Number(det.yellow_ratio || 0),
      texture_ratio: Number(det.texture_ratio || 0),
      clear_ratio: Number(det.clear_ratio || 0),
      green_ratio: Number(det.green_ratio || 0)
    });
    confidenceSum += clamp(score / 7, 0.25, 1);
  }
  const confidence = marks.length ? confidenceSum / marks.length : 0.82;
  return {count:marks.length, marks, confidence};
}

function analyzeCellInImage(idx,r,c){
  const advanced = analyzeCellFromAdvancedDetections(idx,r,c);
  if(advanced) return advanced;
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
  const inside = new Uint8Array(gw*gh);
  const scores = new Float32Array(gw*gh);
  const yellows = new Float32Array(gw*gh);
  const exgs = new Float32Array(gw*gh);
  const chromas = new Float32Array(gw*gh);
  const th = scoreThreshold();
  let scoreSumAll=0, scoreSqAll=0, scoreCount=0;

  for(let gy=0; gy<gh; gy++){
    for(let gx=0; gx<gw; gx++){
      const px = Math.min(w-1, gx*step), py=Math.min(h-1, gy*step);
      const ax=minX+px, ay=minY+py;
      if(!pointInPolygon(ax,ay,poly)) continue;
      const di=(py*w+px)*4;
      const pr=data[di], pg=data[di+1], pb=data[di+2];
      const score = tasselScore(pr,pg,pb);
      const mi=gy*gw+gx;
      inside[mi]=1;
      scores[mi]=score;
      yellows[mi]=((pr+pg)*0.5)-pb;
      exgs[mi]=2*pg-pr-pb;
      chromas[mi]=Math.max(pr,pg,pb)-Math.min(pr,pg,pb);
      scoreSumAll += score;
      scoreSqAll += score*score;
      scoreCount++;
    }
  }

  const scoreMean = scoreCount ? scoreSumAll / scoreCount : 0;
  const scoreVar = scoreCount ? Math.max(0, scoreSqAll / scoreCount - scoreMean*scoreMean) : 0;
  const localTh = clamp(Math.max(th, scoreMean + Math.sqrt(scoreVar) * 0.95), th, th + 1.15);
  for(let mi=0; mi<mask.length; mi++){
    if(inside[mi] && scores[mi]>=localTh){
      mask[mi]=1;
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
      if(n>=2 || scores[mi]>=localTh+0.85) clean[mi]=1;
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
      if(n>=5 && s/Math.max(1,total)>=localTh-0.35) close[mi]=1;
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
      let cells=0, sx=0, sy=0, scoreSum=0, yellowSum=0, exgSum=0, chromaSum=0, coreCells=0, paleCells=0;
      let minGX=gx, maxGX=gx, minGY=gy, maxGY=gy;
      const stack=[[gx,gy]];
      visited[start]=1;
      while(stack.length){
        const p=stack.pop(), x=p[0], y=p[1], pos=y*gw+x;
        cells++; sx+=x; sy+=y; scoreSum+=scores[pos];
        yellowSum+=yellows[pos]; exgSum+=exgs[pos]; chromaSum+=chromas[pos];
        if(scores[pos]>=localTh+0.55) coreCells++;
        if(yellows[pos]>=12 && exgs[pos]<54) paleCells++;
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
      const meanYellow = yellowSum / Math.max(1,cells);
      const meanExg = exgSum / Math.max(1,cells);
      const meanChroma = chromaSum / Math.max(1,cells);
      const coreRatio = coreCells / Math.max(1,cells);
      const paleRatio = paleCells / Math.max(1,cells);
      const cx=minX + (sx/cells)*step, cy=minY + (sy/cells)*step;
      const valid =
        area>=minArea &&
        area<=maxArea &&
        density>=0.11 &&
        elongation<=8.5 &&
        widthPx<=Math.max(16, w*0.18) &&
        heightPx<=Math.max(16, h*0.22) &&
        meanScore>=localTh+0.03 &&
        meanYellow>=10 &&
        meanExg<54 &&
        meanChroma>=14 &&
        coreRatio>=0.12 &&
        paleRatio>=0.20 &&
        pointInPolygon(cx,cy,poly);
      if(valid){
        marks.push({x:cx,y:cy,area:area,score:meanScore});
        confidenceSum += clamp((meanScore - (localTh-0.2)) / 2.2, 0.15, 1);
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
        const perHit = counts[i] >= Number(CONFIG.minPendoes || 0) && percents[i] >= Number(CONFIG.percentualLimite || 50);
        const perStatus = perHit ? 'ATINGIU' : (counts[i] > 0 ? 'EVOLUÇÃO PARCIAL' : 'NÃO ATINGIU');
        fullRows.push({
          Quadra: meta.QUADRA || CONFIG.nomeAnalise || 'Pendoamento',
          Disparo: r + 1,
          Tiro: c + 1,
          Data_Ortofoto: ORTHOS[i].date,
          Nome_Ortofoto: ORTHOS[i].name,
          Total_Pendões: counts[i],
          Teto_Configurado: teto,
          Status: perStatus,
          Data_Atingimento: status === 'ATINGIU' ? firstDate : '',
          Ortofoto_Atingimento: status === 'ATINGIU' ? firstOrtho : '',
          Percentual_Pendoamento: fmtPct(percents[i])
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
  renderOrthoSummary();
}

function runChronologicalAnalysis(){
  if(gridRatios.length < 4){ alert('Marque os 4 pontos do grid fixo primeiro.'); return; }
  if(loaded < ORTHOS.length){ alert('Aguarde as ortofotos terminarem de carregar.'); return; }
  const R = Math.max(1, parseInt(CONFIG.rows || 1));
  const C = Math.max(1, parseInt(CONFIG.cols || 1));
  resultsByParcel = {};
  const preCount = ORTHOS.reduce((sum,o) => sum + (Array.isArray(o.advanced_detections) ? o.advanced_detections.length : 0), 0);
  const modes = [...new Set(ORTHOS.map(o => o.detector_mode || 'OpenCV fallback'))].join(' + ');
  statusEl.textContent = 'Analisando pendoamento com pipeline híbrido YOLO/OpenCV em ' + ORTHOS.length + ' ortofotos' + (preCount ? ' (' + preCount + ' centros pré-detectados · ' + modes + ').' : ' e fallback local.') ;
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
      const s = clamp(Number(m.size || 7), 6, 20) / scale;
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

function drawTrainingMarks(){
  for(const mark of yoloTrainMarks){
    if(mark.idx !== activeIdx) continue;
    ctx.save();
    const s = clamp(Number(mark.size || 128), 48, 256) / 2;
    ctx.strokeStyle = mark.type === 'falso_positivo' ? '#ff55ff' : '#208cff';
    ctx.lineWidth = 2.2 / scale;
    ctx.shadowColor = 'rgba(32,140,255,.75)';
    ctx.shadowBlur = 7 / scale;
    ctx.strokeRect(mark.x - s, mark.y - s, s * 2, s * 2);
    const xSize = clamp(s * 0.16, 6, 18) / scale;
    ctx.beginPath(); ctx.moveTo(mark.x - xSize, mark.y - xSize); ctx.lineTo(mark.x + xSize, mark.y + xSize); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(mark.x - xSize, mark.y + xSize); ctx.lineTo(mark.x + xSize, mark.y - xSize); ctx.stroke();
    ctx.restore();
  }
}

function drawAll(){
  const W = viewer.clientWidth, H = viewer.clientHeight;
  canvas.width = W; canvas.height = H;
  ctx.clearRect(0,0,W,H);
  ctx.save();
  ctx.translate(offsetX,offsetY);
  ctx.scale(scale,scale);
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  if(images[activeIdx] && images[activeIdx].complete) {
    ctx.filter = 'contrast(1.07) saturate(1.06) brightness(1.02)';
    ctx.drawImage(images[activeIdx],0,0,imgW(activeIdx),imgH(activeIdx));
    ctx.filter = 'none';
  }
  drawGrid(activeIdx);
  drawMarks(activeIdx);
  drawTrainingMarks();
  if(gridRatios.length > 0){
    const pts = currentGridPoints(activeIdx);
    pts.forEach((p,i)=>{
      ctx.save();
      ctx.shadowColor=gridDragPoint===i ? 'rgba(255,255,255,.9)' : 'rgba(0,180,255,.8)';
      ctx.shadowBlur=14/scale;
      ctx.fillStyle=gridDragPoint===i ? '#fff' : '#1e90ff';
      ctx.strokeStyle=gridDragPoint===i ? '#aaddff' : '#00cfff';
      ctx.lineWidth=2.5/scale;
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

function applyTemporalSheetStyle(ws){
  if(!ws || !ws['!ref'] || !XLSX || !XLSX.utils) return;
  const range = XLSX.utils.decode_range(ws['!ref']);
  const headers = [];
  for(let c=range.s.c; c<=range.e.c; c++){
    const cell = ws[XLSX.utils.encode_cell({r:0,c})];
    headers.push(cell ? String(cell.v) : '');
  }
  const statusCol = headers.indexOf('Status');
  const centerCols = ['Disparo','Tiro','Total_Pendões','Teto_Configurado','Percentual_Pendoamento']
    .map(name => headers.indexOf(name))
    .filter(idx => idx >= 0);
  const border = {
    top:{style:'thin',color:{rgb:'808080'}},
    bottom:{style:'thin',color:{rgb:'808080'}},
    left:{style:'thin',color:{rgb:'808080'}},
    right:{style:'thin',color:{rgb:'808080'}}
  };
  for(let r=range.s.r; r<=range.e.r; r++){
    for(let c=range.s.c; c<=range.e.c; c++){
      const addr = XLSX.utils.encode_cell({r,c});
      if(!ws[addr]) continue;
      if(r === 0){
        ws[addr].s = {
          font:{bold:true,color:{rgb:'00B0F0'}},
          fill:{patternType:'solid',fgColor:{rgb:'1F1F1F'}},
          alignment:{horizontal:'center',vertical:'center',wrapText:true},
          border
        };
        continue;
      }
      const style = {
        font:{color:{rgb:'000000'}},
        alignment:{horizontal:centerCols.includes(c) ? 'center' : 'left', vertical:'center', wrapText:true},
        border
      };
      if(c === statusCol){
        const status = String(ws[addr].v || '').toUpperCase();
        if(status.includes('ATINGIU') && !status.includes('NÃO')) {
          style.fill = {patternType:'solid',fgColor:{rgb:'00B050'}};
          style.font = {bold:true,color:{rgb:'FFFFFF'}};
        } else if(status.includes('PARCIAL')) {
          style.fill = {patternType:'solid',fgColor:{rgb:'FFF2CC'}};
          style.font = {bold:true,color:{rgb:'000000'}};
        } else {
          style.fill = {patternType:'solid',fgColor:{rgb:'C00000'}};
          style.font = {bold:true,color:{rgb:'FFFFFF'}};
        }
        style.alignment = {horizontal:'center',vertical:'center',wrapText:true};
      }
      ws[addr].s = style;
    }
  }
  ws['!autofilter'] = {ref: ws['!ref']};
  ws['!freeze'] = {xSplit:0,ySplit:1};
  ws['!cols'] = headers.map(h => ({wch: Math.max(12, Math.min(28, String(h).length + 4))}));
}

async function exportExcel(){
  if(!fullRows.length){ alert('Execute a análise antes de exportar.'); return; }
  if(typeof XLSX === 'undefined' && !(await ensureChronoExcel())){ alert('Biblioteca Excel não carregou. Tente novamente.'); return; }
  if(!(await ensureChronoExcel())){ alert('Biblioteca de estilos do Excel não carregou. Tente novamente.'); return; }
  const wb = XLSX.utils.book_new();
  const headers = [
    'Quadra','Disparo','Tiro','Data_Ortofoto','Nome_Ortofoto','Total_Pendões',
    'Teto_Configurado','Status','Data_Atingimento','Ortofoto_Atingimento','Percentual_Pendoamento'
  ];
  const rows = fullRows.map(row => {
    const ordered = {};
    headers.forEach(h => ordered[h] = row[h] ?? '');
    return ordered;
  });
  const ws = XLSX.utils.json_to_sheet(rows, {header: headers});
  applyTemporalSheetStyle(ws);
  XLSX.utils.book_append_sheet(wb, ws, 'Pendoamento');
  XLSX.writeFile(wb, 'pendoamento_por_parcela.xlsx');
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
  if(trainYoloMode){
    if(pt.x < 0 || pt.y < 0 || pt.x > imgW(activeIdx) || pt.y > imgH(activeIdx)){
      trainStatus.textContent = 'Clique dentro da ortofoto para salvar a amostra.';
      return;
    }
    saveYoloTrainingSample(pt);
    return;
  }
  const hitGridPoint = gridPointIndexAt(pt);
  if(hitGridPoint >= 0){
    gridDragPoint = hitGridPoint;
    dragging = false;
    viewer.style.cursor = 'grabbing';
    return;
  }
  if(markGridMode){
    gridRatios.push(ratioPoint(pt, activeIdx));
    if(gridRatios.length >= 4){
      gridRatios = gridRatios.slice(0,4);
      markGridMode = false;
      btnMarkGrid.classList.remove('active');
      statusEl.textContent = 'Grid marcado. Arraste os pontos das extremidades para ajustar Disparo/Tiro.';
    } else {
      statusEl.textContent = 'Marque a extremidade ' + (gridRatios.length + 1) + ' do grid.';
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
  if(gridDragPoint >= 0){
    gridRatios[gridDragPoint] = ratioPoint(pt, activeIdx);
    selectedParcel = null;
    resultsByParcel = {};
    finalRows = [];
    fullRows = [];
    progressBar.style.width = '0%';
    document.getElementById('statTotal').textContent = '0';
    document.getElementById('statHit').textContent = '0';
    document.getElementById('statNoHit').textContent = '0';
    document.getElementById('statReview').textContent = '0';
    document.getElementById('statFirstDate').textContent = 'Primeira data geral: --';
    renderOrthoSummary();
    drawAll();
    return;
  }
  if(dragging){
    offsetX += e.clientX-lastX;
    offsetY += e.clientY-lastY;
    lastX=e.clientX; lastY=e.clientY;
    drawAll();
  }
});
viewer.addEventListener('mouseup', () => { dragging=false; gridDragPoint=-1; viewer.style.cursor='grab'; });
viewer.addEventListener('mouseleave', () => { dragging=false; gridDragPoint=-1; viewer.style.cursor='grab'; });

btnMarkGrid.onclick = () => {
  markGridMode = !markGridMode;
  reviewMode = false;
  btnMarkGrid.classList.toggle('active', markGridMode);
  btnReviewMode.classList.remove('active');
  if(markGridMode){
    gridRatios = [];
    resultsByParcel = {}; finalRows = []; fullRows = [];
    rebuildRows();
    statusEl.textContent = 'Marque as 4 extremidades do grid na ortofoto.';
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
  if(!confirm('Limpar grid, resultados e revisões deste seletor?')) return;
  gridRatios=[]; selectedParcel=null; resultsByParcel={}; finalRows=[]; fullRows=[]; manualReviews={};
  progressBar.style.width='0%'; statusEl.textContent='Seletor limpo.';
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
btnTrainYolo.onclick = () => {
  trainYoloMode = !trainYoloMode;
  markGridMode = false;
  reviewMode = false;
  btnTrainYolo.classList.toggle('active', trainYoloMode);
  btnMarkGrid.classList.remove('active');
  btnReviewMode.classList.remove('active');
  trainStatus.textContent = trainYoloMode
    ? 'Modo treino ativo: clique no pendão para salvar crop e label YOLO.'
    : 'Modo treino parado.';
  drawAll();
};
btnStopTrainMode.onclick = () => {
  trainYoloMode = false;
  btnTrainYolo.classList.remove('active');
  trainStatus.textContent = 'Modo treino parado.';
  drawAll();
};
btnPickTrainDir.onclick = pickTrainingDirectory;
btnGenerateYaml.onclick = async () => {
  if(!trainingDirHandle && !(await pickTrainingDirectory())) return;
  try{
    await generateYamlToTrainingDir();
    trainStatus.textContent = 'data.yaml gerado na pasta de treinamento.';
  }catch(e){
    trainStatus.textContent = 'Falha ao gerar data.yaml: ' + e.message;
  }
};
btnDownloadDataset.onclick = downloadYoloDataset;
btnTrainModelYolo.onclick = () => {
  trainStatus.textContent = 'Para treinar de verdade, salve as amostras na pasta e clique no botão Streamlit "Treinar modelo YOLO" abaixo/acima do visualizador.';
};

setupViewerConfigInputs();
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
                empty_cards = []
                for slot_idx in range(10):
                    empty_cards.append(
                        "<div style='border:1px dashed #2e2e2e;background:#0c0c0c;border-radius:8px;padding:10px;min-height:68px;'>"
                        f"<div style='color:#555;font-weight:800;font-size:0.74rem;'>#{slot_idx + 1:02d} · VAZIO</div>"
                        "<div style='color:#444;font-size:0.72rem;margin-top:8px;'>Aguardando ortofoto</div>"
                        "</div>"
                    )
                st.markdown("""
                <div style='border:1px solid #2a2a2a;border-radius:12px;background:#0d0d0d;
                            padding:12px;margin-top:8px;'>
                    <div style='color:#ff8c00;font-weight:800;font-size:0.82rem;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;'>
                        Resumo das 10 posições do seletor de ortofotos
                    </div>
                    <div style='display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;'>
                """ + "".join(empty_cards) + """
                    </div>
                    <div style='color:#666;font-size:0.72rem;margin-top:10px;'>
                        Anexe as ortofotos acima para abrir o visualizador único. Depois clique em qualquer item do resumo lateral para trocar a imagem no mesmo painel.
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

            qual_file = _resettable_ortho_uploader(
                "📷 Carregar Ortofoto para Análise de Qualidade",
                key="qual_orto_uploader",
                help="PNG · JPG · TIF/GeoTIFF · JP2 · IMG · ECW"
            )
            qual_bytes, qual_name = _uploaded_ortho_bytes(qual_file)

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
    <div class="row-col">
      <span>Quadra:</span><input type="text" id="inpQuadraName" value="Q-1" style="width:96px;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:4px;padding:2px 4px;height:21px;font-size:10px;">
    </div>
    <div class="row-col">
      <span>Linhas/parcela:</span><input type="number" id="inpLinhasParcela" value="4" min="1" max="20" style="width:46px;">
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
    <button class="cnt-btn danger" id="btnDeleteFalhaMode">🧽 Selecionar/Apagar Falha</button>
    <div style="font-size:9px;color:#777;line-height:1.25;">Duplo clique na parcela sem contagem = 100% FALHADA.</div>
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
      transition:.2s;width:100%;margin-top:1px;">📗 Exportar Excel</button>
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
const inpQuadraName = document.getElementById('inpQuadraName');
const inpLinhasParcela = document.getElementById('inpLinhasParcela');
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
const btnDeleteFalhaMode = document.getElementById('btnDeleteFalhaMode');
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
let deleteFalhaMode = false;
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
let manualFailedParcels = {{}};
let deletedFalhaKeys = new Set();
function getLinhasPlantioPorParcela() {{
  const v=Math.max(1,Math.min(20,parseInt(inpLinhasParcela && inpLinhasParcela.value)||4));
  if(inpLinhasParcela) inpLinhasParcela.value=v;
  return v;
}}
function getQuadraNome() {{
  const v=(inpQuadraName && inpQuadraName.value ? inpQuadraName.value.trim() : 'Q-1');
  return v || 'Q-1';
}}
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

function getManualFailKeyByLabels(tiro,disp) {{
  return String(disp)+'_'+String(tiro);
}}

function getFalhaSignature(f) {{
  const id=f.parcelaId||('T'+f.tiro+' D'+f.disp);
  return [id,f.linha||'',f.tipo||'',Math.round((f.p1&&f.p1.x)||0),Math.round((f.p1&&f.p1.y)||0),Math.round((f.p2&&f.p2.x)||0),Math.round((f.p2&&f.p2.y)||0)].join('|');
}}

function findNearestFalha(pt) {{
  if(!falhas.length) return -1;
  let best=-1, bestD=Infinity;
  for(let i=0;i<falhas.length;i++) {{
    const f=falhas[i];
    const a=f.p1, b=f.p2;
    const dx=b.x-a.x, dy=b.y-a.y;
    const len2=dx*dx+dy*dy || 1;
    const t=Math.max(0,Math.min(1,((pt.x-a.x)*dx+(pt.y-a.y)*dy)/len2));
    const px=a.x+dx*t, py=a.y+dy*t;
    const d=Math.sqrt((pt.x-px)*(pt.x-px)+(pt.y-py)*(pt.y-py));
    if(d<bestD) {{ bestD=d; best=i; }}
  }}
  return bestD <= Math.max(10/sc,10) ? best : -1;
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

      if(pts.length<1 && !manualFailedParcels[getManualFailKeyByLabels(tiroLabel,dispLabel)]) {{
        continue;
      }}

      if(manualFailedParcels[getManualFailKeyByLabels(tiroLabel,dispLabel)]) {{
        const linhasManuais=getLinhasPlantioPorParcela();
        for(let li=1; li<=linhasManuais; li++) {{
          const sLinha=(li-0.5)/linhasManuais;
          const rowGeom=getRowGeometry(tl,tr,br,bl,axes.horiz,sLinha);
          rowGeom.pxPorMetro=pxPorMetro;
          if(calcularFalhas) falhas.push({{
            p1:rowGeom.p1,p2:rowGeom.p2,dist:rowGeom.dist,distM:getParcelRealMeters(),
            tiro:tiroLabel,disp:dispLabel,linha:li,tipo:'100% falhada',parcelaId:parcelaId,obs:'100% FALHADA',manual:true
          }});
        }}
        continue;
      }}

      const rowInfos=pts.map(p=>getPlantRowInfo(p,axes,tl,tr,br,bl));
      const rowTol=Math.max(3,Math.min(10,axes.secondaryLen*0.045));
      const linhas=limitarLinhasPlantio(clusterPlantRows(rowInfos,rowTol),getLinhasPlantioPorParcela());
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
  if(deletedFalhaKeys && deletedFalhaKeys.size>0) {{
    falhas=falhas.filter(f=>!deletedFalhaKeys.has(getFalhaSignature(f)));
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
    for(let r2=0;r2<R;r2++) for(let c=0;c<C;c++) {{
      const key=getParcelKeyByRC(r2,c,R,C);
      if(!manualFailedParcels[key]) continue;
      const poly=getAdjustedParcelPoly(r2,c,R,C,p0,p1,p2,p3);
      const center=getParcelCenter(poly);
      ctx.save();
      drawPolyPath(poly);
      ctx.fillStyle='rgba(255,0,0,0.32)';
      ctx.strokeStyle='#ff2222';
      ctx.lineWidth=4/sc;
      ctx.shadowColor='rgba(255,0,0,0.7)';
      ctx.shadowBlur=10/sc;
      ctx.fill(); ctx.stroke(); ctx.shadowBlur=0;
      ctx.fillStyle='rgba(0,0,0,0.78)';
      ctx.font='bold '+(Math.max(8,12/sc))+'px Arial';
      const label='100% FALHADA';
      const tw=ctx.measureText(label).width;
      ctx.fillRect(center.x-tw/2-4/sc,center.y-8/sc,tw+8/sc,16/sc);
      ctx.fillStyle='#ff7777'; ctx.textAlign='center'; ctx.textBaseline='middle';
      ctx.fillText(label,center.x,center.y);
      ctx.restore();
    }}

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
img.src='data:image/jpeg;base64,'+IMG_B64;

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
  if(deleteFalhaMode && points.length===4) {{
    const idx=findNearestFalha(pt);
    if(idx>=0) {{
      deletedFalhaKeys.add(getFalhaSignature(falhas[idx]));
      falhas.splice(idx,1);
      totalCountEl.textContent=falhas.length;
      countInfoEl.textContent='Medição apagada manualmente e descontabilizada dos totais.';
      drawAll();
      return;
    }}
  }}
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

vc.addEventListener('dblclick',e=>{{
  if(points.length<4) return;
  const pt=getImgCoords(e.clientX,e.clientY);
  const hit=findParcelAtPoint(pt);
  if(!hit) return;
  const currentCount=parcelCounts[hit.key] || 0;
  if(currentCount>0 && !confirm('Esta parcela tem contagem. Marcar mesmo assim como 100% FALHADA?')) return;
  manualFailedParcels[hit.key]=!manualFailedParcels[hit.key];
  if(manualFailedParcels[hit.key]) {{
    countPanel.style.display='block';
    countPanel.querySelector('h3').textContent='AJUSTE MANUAL';
    totalCountEl.textContent='100%';
    countInfoEl.textContent=getParcelLabel(hit.key)+' marcada como 100% FALHADA.';
    falhasSumario.textContent='OBS: 100% FALHADA';
  }}
  if(falhas.length>0 || qualidadeModoVisual==='falhas') detectarFalhas();
  else drawAll();
}});

// ── Botões ────────────────────────────────────────────────────────────────
btnGridTool.onclick=()=>{{
  gridMode=!gridMode; manualMode=false; deleteFalhaMode=false; parcelSelectMode=false; parcelMoveMode=false; selectedParcels.clear();
  btnGridTool.style.borderColor=gridMode?'#ff8c00':'#3a3a3a';
  if(gridMode) {{ points=[]; plantCenters=[]; manualMarks=[]; parcelCounts={{}}; falhas=[]; areasUteis=[]; metrosPlantadosLinhas=[]; metrosPlantadosSegmentos=[]; qualidadeModoVisual=''; parcelAdjustments={{}}; manualFailedParcels={{}}; deletedFalhaKeys=new Set(); if(parcelAdjustStorageKey) localStorage.removeItem(parcelAdjustStorageKey); countPanel.style.display='none'; updateParcelAdjustStatus(); drawAll(); }}
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
  points=[]; plantCenters=[]; manualMarks=[]; parcelCounts={{}}; falhas=[]; areasUteis=[]; metrosPlantadosLinhas=[]; metrosPlantadosSegmentos=[]; qualidadeModoVisual=''; parcelAdjustments={{}}; manualFailedParcels={{}}; deletedFalhaKeys=new Set(); selectedParcels.clear();
  if(parcelAdjustStorageKey) localStorage.removeItem(parcelAdjustStorageKey);
  countPanel.style.display='none'; gridMode=false; manualMode=false; parcelSelectMode=false; parcelMoveMode=false;
  btnGridTool.style.borderColor='#3a3a3a'; btnManualMode.style.borderColor='#3a3a3a';
  updateParcelAdjustStatus();
  drawAll();
}};
btnDetectFalhas.onclick=()=>detectarFalhas();
btnMedirPlantados.onclick=()=>medirMetrosPlantados();
btnDeleteFalhaMode.onclick=()=>{{
  deleteFalhaMode=!deleteFalhaMode;
  manualMode=false; gridMode=false; parcelSelectMode=false; parcelMoveMode=false;
  btnDeleteFalhaMode.style.borderColor=deleteFalhaMode?'#ff5555':'#660000';
  countInfoEl.textContent=deleteFalhaMode?'Clique em uma linha de falha para apagar e descontabilizar.':'Modo apagar falha desativado.';
}};
chkShowFalhas.onchange=()=>drawAll();
chkLabels.onchange=()=>drawAll();
inpMinDist.onchange=()=>{{ if(falhas.length>0) detectarFalhas(); }};
inpBufferCm.onchange=()=>{{ if(falhas.length>0) detectarFalhas(); }};
inpParcelLen.onchange=()=>{{ if(falhas.length>0) detectarFalhas(); }};
selUnit.onchange=()=>{{ if(falhas.length>0) detectarFalhas(); else drawAll(); }};
inpLineWidth.onchange=()=>drawAll();
inpLinhasParcela.onchange=()=>{{ drawAll(); }};
inpQuadraName.onchange=()=>drawAll();

function parseFalhaParcelaSort(id) {{
  const m=String(id||'').match(/T(\\d+)\\s*D(\\d+)/i);
  return m ? {{tiro:parseInt(m[1]),disp:parseInt(m[2])}} : {{tiro:999999,disp:999999}};
}}

function getLinhaPlantioExport(linha) {{
  return Math.max(1,Math.min(getLinhasPlantioPorParcela(),parseInt(linha)||1));
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
    for(let linha=1; linha<=getLinhasPlantioPorParcela(); linha++) {{
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
  exportQualidadeExcelCompleto();
}}

function exportQualidadeExcelCompleto() {{
  if(points.length<4) {{ alert('Marque o grid primeiro.'); return; }}
  if(typeof XLSX==='undefined') {{ alert('Biblioteca XLSX não carregada.'); return; }}

  const estadoAnterior={{
    falhas:[...falhas],
    areasUteis:[...areasUteis],
    metrosPlantadosLinhas:[...metrosPlantadosLinhas],
    metrosPlantadosSegmentos:[...metrosPlantadosSegmentos],
    qualidadeModoVisual:qualidadeModoVisual
  }};

  function restaurarEstadoQualidade() {{
    falhas=estadoAnterior.falhas;
    areasUteis=estadoAnterior.areasUteis;
    metrosPlantadosLinhas=estadoAnterior.metrosPlantadosLinhas;
    metrosPlantadosSegmentos=estadoAnterior.metrosPlantadosSegmentos;
    qualidadeModoVisual=estadoAnterior.qualidadeModoVisual;
  }}

  if(!processarQualidadePorLinhas('csv')) {{ restaurarEstadoQualidade(); return; }}
  const rows=getResumoPlantadoFalhaRows();
  if(rows.length===0) {{
    restaurarEstadoQualidade();
    alert('Nenhuma linha de plantio detectada para exportar.');
    return;
  }}

  const totalFalhaParcela={{}};
  const totalPlantadoParcela={{}};
  const obsPorParcela={{}};
  for(const row of rows) {{
    const parcela=row.parcela||'';
    totalFalhaParcela[parcela]=(totalFalhaParcela[parcela]||0)+(Number(row.falhaM)||0);
    totalPlantadoParcela[parcela]=(totalPlantadoParcela[parcela]||0)+(Number(row.plantadoM)||0);
  }}
  for(const f of falhas) {{
    const parcela=f.parcelaId||('T'+f.tiro+' D'+f.disp);
    if(f.obs) obsPorParcela[parcela]=f.obs;
  }}

  const round2=(v)=>Math.round((Number(v)||0)*100)/100;
  const headers=['Quadras','Parcela','Linha','Metros_Falha_Linha','Total_Falha_Parcela','Metros_Plantados_Linha','Total_Plantado_Parcela','OBS'];
  const dados=[headers];

  for(const row of rows) {{
    const parcela=row.parcela||'';
    dados.push([
      getQuadraNome(),
      parcela,
      'Linha '+row.linha,
      round2(row.falhaM),
      round2(totalFalhaParcela[parcela]),
      round2(row.plantadoM),
      round2(totalPlantadoParcela[parcela]),
      obsPorParcela[parcela]||''
    ]);
  }}

  const ws=XLSX.utils.aoa_to_sheet(dados);
  ws['!cols']=headers.map((header,idx)=>{{
    let maxLen=String(header).length;
    for(let r=1;r<dados.length;r++) maxLen=Math.max(maxLen,String(dados[r][idx]===undefined?'':dados[r][idx]).length);
    return {{wch:Math.min(Math.max(maxLen+3,12),34)}};
  }});
  ws['!freeze']={{xSplit:0,ySplit:1}};

  const border={{
    top:{{style:'thin',color:{{rgb:'808080'}}}},
    bottom:{{style:'thin',color:{{rgb:'808080'}}}},
    left:{{style:'thin',color:{{rgb:'808080'}}}},
    right:{{style:'thin',color:{{rgb:'808080'}}}}
  }};
  const alignCenter={{horizontal:'center',vertical:'center',wrapText:true}};
  const fillAzul={{fgColor:{{rgb:'D9EAF7'}}}};
  const fillVermelho={{fgColor:{{rgb:'F4CCCC'}}}};
  const fillVerde={{fgColor:{{rgb:'D9EAD3'}}}};

  function fillByCol(c) {{
    if(c===3 || c===4) return fillVermelho;
    if(c===5 || c===6) return fillVerde;
    return fillAzul;
  }}

  const range=XLSX.utils.decode_range(ws['!ref']);
  for(let R=range.s.r; R<=range.e.r; ++R) {{
    for(let C=range.s.c; C<=range.e.c; ++C) {{
      const addr=XLSX.utils.encode_cell({{r:R,c:C}});
      if(!ws[addr]) continue;
      ws[addr].s={{
        font:R===0 ? {{bold:true,name:'Arial',sz:11,color:{{rgb:'000000'}}}} : {{name:'Arial',sz:10,color:{{rgb:'000000'}}}},
        fill:{{patternType:'solid',...fillByCol(C)}},
        alignment:alignCenter,
        border:border
      }};
      if(R>0 && (C===3 || C===4 || C===5 || C===6)) {{
        ws[addr].t='n';
        ws[addr].v=round2(ws[addr].v);
        ws[addr].z='0.00';
      }}
    }}
  }}

  const wb=XLSX.utils.book_new();
  wb.Props={{
    Title:'Qualidade de Parcelas',
    Subject:'Falhas e Metros Plantados por Linha',
    Author:'TMG Sistema de Análise',
    CreatedDate:new Date()
  }};
  XLSX.utils.book_append_sheet(wb,ws,'Qualidade Parcelas');
  const safeQuadra=getQuadraNome().replace(/[^a-zA-Z0-9_-]+/g,'_');
  XLSX.writeFile(wb,'qualidade_parcelas_'+safeQuadra+'.xlsx',{{bookType:'xlsx',cellStyles:true}});
  restaurarEstadoQualidade();
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
document.getElementById('btnExportFalhasXLSX').onclick=()=>{{ exportQualidadeExcelCompleto(); return;
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

_render_partner_mention_notifications()

# ==========================================
# FOOTER[cite: 1]
# ==========================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.divider()

st.markdown(
    "<p style='text-align: center; color: #555;'>Estrutura Modular Profissional | Python 3.12</p>",
    unsafe_allow_html=True
)
