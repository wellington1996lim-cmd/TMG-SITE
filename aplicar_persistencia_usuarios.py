from pathlib import Path
import re
import shutil
from datetime import datetime

APP_FILE = Path("tmg_app_final.py")

if not APP_FILE.exists():
    raise SystemExit("ERRO: coloque este arquivo na mesma pasta do tmg_app_final.py e execute novamente.")

original = APP_FILE.read_text(encoding="utf-8")
backup = APP_FILE.with_name(f"tmg_app_final_backup_antes_usuarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(APP_FILE, backup)

new_block = """AUTH_USERS_PATH = SYSTEM_DATABASE_DIR / "usuarios_sistema.json"
AUTH_USERS_BACKUP_PATH = SYSTEM_CONFIG_DIR / "usuarios_sistema_backup.json"
AUTH_USERS_LEGACY_PATH = SYSTEM_CONFIG_DIR / "usuarios_sistema.json"
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

def _auth_backup_users_file(path: Path = None, reason: str = "backup") -> None:
    try:
        source = path or AUTH_USERS_PATH
        if source.exists():
            AUTH_USERS_BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            numbered_backup = AUTH_USERS_BACKUP_PATH.with_name(f"usuarios_sistema_backup_{reason}_{timestamp}.json")
            shutil.copy2(source, AUTH_USERS_BACKUP_PATH)
            shutil.copy2(source, numbered_backup)
    except Exception:
        pass

def _auth_normalize_user(user: dict) -> dict:
    if not isinstance(user, dict):
        user = {}

    user.setdefault("nome", user.get("usuario", "Usuário"))
    user.setdefault("usuario", "")
    user.setdefault("senha", "")
    user.setdefault("ativo", True)
    user.setdefault("admin", False)
    user.setdefault("criado_em", _now_iso())
    user["atualizado_em"] = user.get("atualizado_em") or _now_iso()

    if not isinstance(user.get("permissoes"), dict):
        user["permissoes"] = {}

    perms = user["permissoes"]
    legacy_culture_access = bool(perms.get("culturas", False))
    legacy_partner_access = bool(perms.get("parceiros", False))
    defaults = _default_permissions(False)

    for key, value in defaults.items():
        if key in perms:
            perms[key] = bool(perms[key])
            continue

        if key in ("menu_checklist", "menu_grid", "menu_upload", "menu_bases", "menu_sync", "menu_ortomosaicos"):
            perms[key] = legacy_culture_access
        elif key in ("menu_parceiros", "menu_controle_dados"):
            perms[key] = legacy_partner_access
        elif key in PARTNER_PERMISSION_OPTIONS:
            perms[key] = legacy_partner_access
        else:
            perms[key] = bool(value)

    return user

def _auth_merge_users(existing_users: list, default_users: list) -> list:
    merged = []
    seen = set()

    for user in existing_users or []:
        normalized = _auth_normalize_user(user)
        usuario_norm = str(normalized.get("usuario", "")).strip().lower()
        if not usuario_norm or usuario_norm in seen:
            continue
        seen.add(usuario_norm)
        merged.append(normalized)

    for default_user in default_users or []:
        normalized_default = _auth_normalize_user(default_user)
        usuario_norm = str(normalized_default.get("usuario", "")).strip().lower()
        if not usuario_norm:
            continue

        if usuario_norm not in seen:
            seen.add(usuario_norm)
            merged.insert(0, normalized_default)
        elif usuario_norm == "wellington":
            for user in merged:
                if str(user.get("usuario", "")).strip().lower() == "wellington":
                    user["admin"] = True
                    user["ativo"] = True
                    perms = user.setdefault("permissoes", {})
                    perms.update(_default_permissions(True))
                    break

    return merged

def _auth_ensure_users() -> None:
    AUTH_USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SYSTEM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not AUTH_USERS_PATH.exists() and AUTH_USERS_LEGACY_PATH.exists():
        try:
            shutil.copy2(AUTH_USERS_LEGACY_PATH, AUTH_USERS_PATH)
        except Exception:
            pass

    if not AUTH_USERS_PATH.exists():
        data = _auth_default_users()
        _auth_save_users(data)
        return

    data = _auth_load_users()
    users = data.get("users", [])
    merged_users = _auth_merge_users(users, _auth_default_users()["users"])

    if merged_users != users:
        data["users"] = merged_users
        _auth_save_users(data)

def _auth_load_users() -> dict:
    AUTH_USERS_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not AUTH_USERS_PATH.exists():
        return _auth_default_users()

    try:
        raw_text = AUTH_USERS_PATH.read_text(encoding="utf-8").strip()
        if not raw_text:
            _auth_backup_users_file(AUTH_USERS_PATH, "vazio")
            return _auth_default_users()

        data = json.loads(raw_text)
        if not isinstance(data, dict):
            raise ValueError("Arquivo de usuários não é um objeto JSON.")
        if not isinstance(data.get("users"), list):
            data["users"] = []

    except Exception:
        _auth_backup_users_file(AUTH_USERS_PATH, "corrompido")
        data = _auth_default_users()

    data["users"] = _auth_merge_users(data.get("users", []), _auth_default_users()["users"])
    return data

def _auth_save_users(data: dict) -> None:
    AUTH_USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SYSTEM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    incoming_users = data.get("users", []) if isinstance(data, dict) else []

    disk_users = []
    if AUTH_USERS_PATH.exists():
        try:
            current = json.loads(AUTH_USERS_PATH.read_text(encoding="utf-8"))
            if isinstance(current, dict) and isinstance(current.get("users"), list):
                disk_users = current.get("users", [])
        except Exception:
            _auth_backup_users_file(AUTH_USERS_PATH, "antes_salvar_corrompido")

    by_usuario = {}
    for user in disk_users:
        normalized = _auth_normalize_user(user)
        key = str(normalized.get("usuario", "")).strip().lower()
        if key:
            by_usuario[key] = normalized

    for user in incoming_users:
        normalized = _auth_normalize_user(user)
        key = str(normalized.get("usuario", "")).strip().lower()
        if key:
            antigo = by_usuario.get(key, {})
            if antigo and not normalized.get("criado_em"):
                normalized["criado_em"] = antigo.get("criado_em", _now_iso())
            normalized["atualizado_em"] = _now_iso()
            by_usuario[key] = normalized

    merged_users = _auth_merge_users(list(by_usuario.values()), _auth_default_users()["users"])
    final_data = {"users": merged_users}

    _auth_backup_users_file(AUTH_USERS_PATH, "antes_salvar")
    AUTH_USERS_PATH.write_text(json.dumps(final_data, indent=2, ensure_ascii=False), encoding="utf-8")

    try:
        shutil.copy2(AUTH_USERS_PATH, AUTH_USERS_BACKUP_PATH)
    except Exception:
        pass

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
"""

pattern = r'AUTH_USERS_PATH = SYSTEM_DATABASE_DIR / "usuarios_sistema\.json".*?def _auth_current_user\(\) -> dict:'
replacement = new_block + "\n\ndef _auth_current_user() -> dict:"

updated, count = re.subn(pattern, replacement, original, count=1, flags=re.S)

if count != 1:
    raise SystemExit(
        "ERRO: não consegui localizar o bloco de usuários automaticamente. "
        "Confirme se o arquivo tmg_app_final.py está igual ao repositório."
    )

APP_FILE.write_text(updated, encoding="utf-8")

print("OK: tmg_app_final.py ajustado com persistência de usuários.")
print(f"Backup criado em: {backup}")
print("Agora rode o sistema e teste o cadastro de usuários.")
